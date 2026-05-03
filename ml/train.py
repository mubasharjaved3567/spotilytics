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
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.sql.functions import col, when, floor, log1p

load_dotenv()

PROCESSED_DIR = Path("data/processed/spotify_clean")
MODEL_DIR     = Path("ml/models/boporflop_model")
LOG_DIR       = Path("logs")
REPORT_PATH   = LOG_DIR / "ml_report.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)
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


# ── Spark ──────────────────────────────────────────────────────────────────
def _get_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("Spotilytics-ML-Optimized")
        .config("spark.driver.memory", "6g")
        .config("spark.sql.shuffle.partitions", "16")
        .getOrCreate()
    )


# ── Feature engineering ────────────────────────────────────────────────────
def _add_engineered_features(df: DataFrame) -> DataFrame:
    print("\n   🔧 Engineering features...")

    # Era grouping
    df = df.withColumn("decade",
        (floor(col("year") / 10) * 10).cast("double")
    )

    # Interaction features — music domain knowledge
    df = df.withColumn("tempo_energy",      col("tempo")          * col("energy"))
    df = df.withColumn("dance_valence",     col("danceability")   * col("valence"))
    df = df.withColumn("acoustic_energy",   col("acousticness")   * (1 - col("energy")))
    df = df.withColumn("loudness_energy",   (col("loudness") + 60) * col("energy"))
    df = df.withColumn("speech_instrument", col("speechiness")    + col("instrumentalness"))

    # Duration features
    df = df.withColumn("duration_min",  col("duration_ms") / 60000)
    df = df.withColumn("log_duration",  log1p(col("duration_ms")))

    cols = ["decade","tempo_energy","dance_valence","acoustic_energy",
            "loudness_energy","speech_instrument","duration_min","log_duration"]
    print(f"   ✅ {len(cols)} engineered features added")
    return df


# ── Class weights ──────────────────────────────────────────────────────────
def _add_class_weights(df: DataFrame) -> DataFrame:
    """
    Weights inversely proportional to class frequency.
    Low=77.5%, Mid=21.3%, High=1.2%
    Weight = max_freq / class_freq
    """
    print("\n   ⚖️  Computing class weights from real distribution...")
    total = df.count()
    dist  = {r[LABEL_COL]: r["count"] / total
             for r in df.groupBy(LABEL_COL).count().collect()}

    max_freq = max(dist.values())
    weights  = {k: round(max_freq / v, 2) for k, v in dist.items()}

    print(f"   Low  → {weights.get('Low',  1.0)}x")
    print(f"   Mid  → {weights.get('Mid',  1.0)}x")
    print(f"   High → {weights.get('High', 1.0)}x")

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
    print(f"✅ Loaded {df.count():,} rows")
    return df


def _log_label_distribution(df: DataFrame) -> None:
    total = df.count()
    print("\n📊 Real label distribution:")
    for row in df.groupBy(LABEL_COL).count().orderBy("count", ascending=False).collect():
        pct = row["count"] / total * 100
        bar = "█" * int(pct / 2)
        print(f"   {row[LABEL_COL]:<6}  {row['count']:>8,}  ({pct:.1f}%)  {bar}")


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
    print("\n📊 Confusion matrix (Low=0, Mid=1, High=2):")
    print(f"   {'actual/pred':<14}", end="")
    for p in preds:
        print(f"  {p:>8}", end="")
    print()
    for actual in sorted(set(r["actual"] for r in matrix)):
        print(f"   {actual:<14}", end="")
        for p in preds:
            val = next(
                (r["count"] for r in matrix
                 if r["actual"] == actual and r["predicted"] == p), 0
            )
            print(f"  {val:>8,}", end="")
        print()
    return matrix


def _feature_importance(model: PipelineModel) -> list:
    importances = model.stages[-1].featureImportances.toArray()
    ranked = sorted(zip(ALL_FEATURE_COLS, importances), key=lambda x: x[1], reverse=True)
    print("\n🏆 Feature importance:")
    results = []
    for feat, imp in ranked:
        bar = "█" * int(imp * 40)
        print(f"   {feat:<22}  {imp:.4f}  {bar}")
        results.append({"feature": feat, "importance": round(float(imp), 6)})
    return results


def _save_report(metrics, importances, confusion, train_rows, test_rows, weights) -> None:
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
    print(f"\n📄 ML report saved to {REPORT_PATH}")


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
    df = _add_engineered_features(df)

    # Class weights — computed from real distribution
    df, weights = _add_class_weights(df)

    # Split
    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
    train_rows = train_df.count()
    test_rows  = test_df.count()
    print(f"\n📂 Train: {train_rows:,}  |  Test: {test_rows:,}")

    # Train
    pipeline = build_pipeline()
    print("\n⏳ Training optimized Random Forest")
    print("   300 trees | depth 15 | class weights | 8 engineered features")
    print("   This takes 8-12 minutes on M1...")
    model = pipeline.fit(train_df)
    print("✅ Training complete")

    # Evaluate
    predictions = model.transform(test_df)
    metrics     = _evaluate(predictions)

    print("\n📈 Evaluation metrics:")
    for k, v in metrics.items():
        print(f"   {k:<22}  {v:.4f}")

    confusion   = _confusion_matrix(predictions)
    importances = _feature_importance(model)

    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    model.write().overwrite().save(str(MODEL_DIR))
    print(f"\n💾 Model saved to {MODEL_DIR}")

    _save_report(metrics, importances, confusion, train_rows, test_rows, weights)
    return model


# ── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    try:
        train()
        print(f"\n🎵 Optimized BopOrFlop model ready at {MODEL_DIR}")
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Training failed: %s", e)
        print(f"\n❌ Training failed: {e}")
        sys.exit(1)