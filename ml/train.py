import json
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pyspark.sql import SparkSession, DataFrame
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler
from pyspark.sql.functions import col, when, floor, log1p

load_dotenv()

PROCESSED_DIR = Path("data/processed/spotify_clean")
MODEL_DIR     = Path("ml/models/boporflop_model")
LOG_DIR       = Path("logs")
REPORT_PATH   = LOG_DIR / "ml_report.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "train.log"),
    ],
)
logger = logging.getLogger(__name__)

NUMERIC_FEATURES = [
    # Original features
    "danceability", "energy", "loudness", "tempo", "valence",
    "acousticness", "speechiness", "instrumentalness",
    "liveness", "duration_ms", "year",
    # Engineered features
    "decade",
    "tempo_energy",
    "dance_valence",
    "acoustic_energy",
    "loudness_energy",
    "speech_instrument",
    "duration_min",
    "log_duration",
]
LABEL_COL        = "popularity_tier"
ALL_FEATURE_COLS = NUMERIC_FEATURES + ["genre_idx"]

# Valid input ranges — shared with predict.py
FEATURE_RANGES = {
    "danceability":     (0.0, 1.0),
    "energy":           (0.0, 1.0),
    "loudness":         (-60.0, 0.0),
    "tempo":            (0.0, 300.0),
    "valence":          (0.0, 1.0),
    "acousticness":     (0.0, 1.0),
    "speechiness":      (0.0, 1.0),
    "instrumentalness": (0.0, 1.0),
    "liveness":         (0.0, 1.0),
    "duration_ms":      (1_000.0, 3_600_000.0),
    "year":             (1900.0, 2100.0),
}


# ── Spark ──────────────────────────────────────────────────────────────────
_spark: SparkSession | None = None

def _get_spark() -> SparkSession:
    """Return a cached SparkSession (one per process)."""
    global _spark
    if _spark is None:
        _spark = (
            SparkSession.builder
            .appName("Spotilytics-ML-Optimized")
            .config("spark.driver.memory", "6g")
            .config("spark.sql.shuffle.partitions", "16")
            .getOrCreate()
        )
    return _spark


# ── Feature engineering ────────────────────────────────────────────────────
def add_engineered_features(df: DataFrame) -> DataFrame:
    """
    Add 8 interaction / transform features.
    Extracted as a standalone function so predict.py can reuse it.
    """
    logger.info("Engineering features...")

    df = df.withColumn("decade",
        (floor(col("year") / 10) * 10).cast("double")
    )
    df = df.withColumn("tempo_energy",      col("tempo")          * col("energy"))
    df = df.withColumn("dance_valence",     col("danceability")   * col("valence"))
    df = df.withColumn("acoustic_energy",   col("acousticness")   * (1 - col("energy")))
    df = df.withColumn("loudness_energy",   (col("loudness") + 60) * col("energy"))
    df = df.withColumn("speech_instrument", col("speechiness")    + col("instrumentalness"))
    df = df.withColumn("duration_min",      col("duration_ms") / 60000)
    df = df.withColumn("log_duration",      log1p(col("duration_ms")))

    logger.info("8 engineered features added")
    return df


# ── Class weights ──────────────────────────────────────────────────────────
def _add_class_weights(df: DataFrame) -> tuple[DataFrame, dict]:
    """
    Weights inversely proportional to class frequency.
    Low ≈ 77.5 %, Mid ≈ 21.3 %, High ≈ 1.2 %
    weight = max_freq / class_freq
    """
    logger.info("Computing class weights from real distribution...")
    total = df.count()
    dist  = {r[LABEL_COL]: r["count"] / total
             for r in df.groupBy(LABEL_COL).count().collect()}

    max_freq = max(dist.values())
    weights  = {k: round(max_freq / v, 2) for k, v in dist.items()}

    logger.info("Weights — Low: %.2f  Mid: %.2f  High: %.2f",
                weights.get("Low", 1.0),
                weights.get("Mid", 1.0),
                weights.get("High", 1.0))

    df = df.withColumn("class_weight",
        when(col(LABEL_COL) == "High", float(weights.get("High", 60.0)))
        .when(col(LABEL_COL) == "Mid",  float(weights.get("Mid",  3.0)))
        .otherwise(1.0)
    )
    return df, weights


# ── Data loader ────────────────────────────────────────────────────────────
def load_cleaned_data(spark: SparkSession) -> DataFrame:
    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(
            f"Processed data not found at {PROCESSED_DIR}. "
            "Run processing/clean.py first."
        )
    df = spark.read.parquet(str(PROCESSED_DIR))
    logger.info("Loaded %s rows", f"{df.count():,}")
    return df


def _log_label_distribution(df: DataFrame) -> None:
    total = df.count()
    logger.info("Real label distribution:")
    for row in df.groupBy(LABEL_COL).count().orderBy("count", ascending=False).collect():
        pct = row["count"] / total * 100
        bar = "█" * int(pct / 2)
        logger.info("  %-6s  %8s  (%.1f%%)  %s",
                    row[LABEL_COL], f"{row['count']:,}", pct, bar)


# ── Pipeline ───────────────────────────────────────────────────────────────
def build_pipeline() -> Pipeline:
    genre_indexer = StringIndexer(
        inputCol="genre_group", outputCol="genre_idx", handleInvalid="keep"
    )
    label_indexer = StringIndexer(
        inputCol=LABEL_COL, outputCol="label", handleInvalid="keep"
    )
    assembler = VectorAssembler(
        inputCols=ALL_FEATURE_COLS, outputCol="features_raw", handleInvalid="keep"
    )
    scaler = StandardScaler(
        inputCol="features_raw", outputCol="features",
        withMean=True, withStd=True
    )
    rf = RandomForestClassifier(
        labelCol="label",
        featuresCol="features",
        weightCol="class_weight",
        numTrees=300,
        maxDepth=15,
        minInstancesPerNode=3,
        featureSubsetStrategy="sqrt",
        impurity="gini",
        subsamplingRate=0.8,
        seed=42,
    )
    return Pipeline(stages=[genre_indexer, label_indexer, assembler, scaler, rf])


# ── Evaluation ─────────────────────────────────────────────────────────────
def _evaluate(predictions: DataFrame) -> dict:
    def _m(name):
        return round(MulticlassClassificationEvaluator(
            labelCol="label", predictionCol="prediction", metricName=name
        ).evaluate(predictions), 4)
    return {
        "f1":                 _m("f1"),
        "accuracy":           _m("accuracy"),
        "weighted_precision": _m("weightedPrecision"),
        "weighted_recall":    _m("weightedRecall"),
    }


def _confusion_matrix(predictions: DataFrame) -> list:
    rows = (
        predictions
        .groupBy("label", "prediction")
        .count()
        .orderBy("label", "prediction")
        .collect()
    )
    matrix = [
        {"actual": int(r["label"]), "predicted": int(r["prediction"]), "count": r["count"]}
        for r in rows
    ]
    preds = sorted(set(r["predicted"] for r in matrix))
    logger.info("Confusion matrix (Low=0, Mid=1, High=2):")
    header = "  actual/pred   " + "".join(f"  {p:>8}" for p in preds)
    logger.info(header)
    for actual in sorted(set(r["actual"] for r in matrix)):
        row_str = f"  {actual:<14}" + "".join(
            f"  {next((r['count'] for r in matrix if r['actual'] == actual and r['predicted'] == p), 0):>8,}"
            for p in preds
        )
        logger.info(row_str)
    return matrix


def _feature_importance(model: PipelineModel) -> list:
    importances = model.stages[-1].featureImportances.toArray()
    ranked = sorted(zip(ALL_FEATURE_COLS, importances), key=lambda x: x[1], reverse=True)
    logger.info("Feature importance:")
    results = []
    for feat, imp in ranked:
        bar = "█" * int(imp * 40)
        logger.info("  %-22s  %.4f  %s", feat, imp, bar)
        results.append({"feature": feat, "importance": round(float(imp), 6)})
    return results


def _save_report(metrics, importances, confusion, train_rows, test_rows, weights) -> None:
    """Save JSON report — called BEFORE model.write() so it's never lost."""
    report = {
        "timestamp":          datetime.now().isoformat(),
        "model":              "RandomForestClassifier — Optimized",
        "approach":           "Class weights + Feature engineering + StandardScaler",
        "class_weights":      weights,
        "improvements": [
            "8 engineered features (interactions + log transforms)",
            "Class weights from real distribution",
            "StandardScaler on features",
            "300 trees, depth 15, subsampling 0.8",
            "Gini impurity",
        ],
        "num_trees":          300,
        "max_depth":          15,
        "subsampling_rate":   0.8,
        "features":           ALL_FEATURE_COLS,
        "label":              LABEL_COL,
        "train_rows":         train_rows,
        "test_rows":          test_rows,
        "metrics":            metrics,
        "confusion_matrix":   confusion,
        "feature_importance": importances,
        "model_path":         str(MODEL_DIR),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    logger.info("ML report saved to %s", REPORT_PATH)


# ── Main ───────────────────────────────────────────────────────────────────
def train() -> PipelineModel:
    spark = _get_spark()
    spark.sparkContext.setLogLevel("ERROR")

    df = load_cleaned_data(spark)
    _log_label_distribution(df)

    required = [
        "danceability", "energy", "loudness", "tempo", "valence",
        "acousticness", "speechiness", "instrumentalness",
        "liveness", "duration_ms", "year", "genre_group", LABEL_COL
    ]
    df = df.dropna(subset=required)

    # Feature engineering
    df = add_engineered_features(df)

    # Class weights — computed from real distribution
    df, weights = _add_class_weights(df)

    # Split
    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
    train_rows = train_df.count()
    test_rows  = test_df.count()
    logger.info("Train: %s  |  Test: %s", f"{train_rows:,}", f"{test_rows:,}")

    # Train
    pipeline = build_pipeline()
    logger.info("Training optimized Random Forest — 300 trees | depth 15 | class weights | 8 engineered features")
    logger.info("This takes 8-12 minutes...")
    model = pipeline.fit(train_df)
    logger.info("Training complete")

    # Evaluate
    predictions = model.transform(test_df)
    metrics     = _evaluate(predictions)

    logger.info("Evaluation metrics:")
    for k, v in metrics.items():
        logger.info("  %-22s  %.4f", k, v)

    confusion   = _confusion_matrix(predictions)
    importances = _feature_importance(model)

    # FIX: save report BEFORE model.write() so report is never lost if save fails
    _save_report(metrics, importances, confusion, train_rows, test_rows, weights)

    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    model.write().overwrite().save(str(MODEL_DIR))
    logger.info("Model saved to %s", MODEL_DIR)

    return model


# ── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    try:
        train()
        logger.info("BopOrFlop model ready at %s", MODEL_DIR)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception("Training failed: %s", e)
        sys.exit(1)