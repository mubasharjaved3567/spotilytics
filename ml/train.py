import json
import logging
from datetime import datetime
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.feature import StringIndexer, VectorAssembler
from dotenv import load_dotenv

load_dotenv()

PROCESSED_DIR = Path("data/processed/spotify_clean")
MODEL_DIR     = Path("ml/models/boporflop_model")
LOG_DIR       = Path("logs")
REPORT_PATH   = LOG_DIR / "ml_report.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)

NUMERIC_FEATURES = [
    "danceability", "energy", "loudness", "tempo", "valence",
    "acousticness", "speechiness", "instrumentalness",
    "liveness", "duration_ms", "year",
]
LABEL_COL        = "popularity_tier"
ALL_FEATURE_COLS = NUMERIC_FEATURES + ["genre_idx"]


def _get_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("Spotilytics-ML")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def load_cleaned_data(spark: SparkSession) -> DataFrame:
    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(
            f"Processed data not found at {PROCESSED_DIR}. Run processing/clean.py first."
        )
    df = spark.read.parquet(str(PROCESSED_DIR))
    print(f"✅ Loaded {df.count():,} rows")
    return df


def _log_label_distribution(df: DataFrame) -> None:
    total = df.count()
    print("\n📊 Label distribution:")
    for row in df.groupBy(LABEL_COL).count().orderBy("count", ascending=False).collect():
        pct = row["count"] / total * 100
        print(f"   {row[LABEL_COL]:<6}  {row['count']:>8,}  ({pct:.1f}%)")


def build_pipeline() -> Pipeline:
    genre_indexer = StringIndexer(inputCol="genre_group", outputCol="genre_idx",  handleInvalid="keep")
    label_indexer = StringIndexer(inputCol=LABEL_COL,     outputCol="label",      handleInvalid="keep")
    assembler     = VectorAssembler(inputCols=ALL_FEATURE_COLS, outputCol="features", handleInvalid="keep")
    rf = RandomForestClassifier(
        labelCol="label", featuresCol="features",
        numTrees=100, maxDepth=10, seed=42,
    )
    return Pipeline(stages=[genre_indexer, label_indexer, assembler, rf])


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
            val = next((r["count"] for r in matrix if r["actual"] == actual and r["predicted"] == p), 0)
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


def _save_report(metrics, importances, confusion, train_rows, test_rows) -> None:
    report = {
        "timestamp":          datetime.now().isoformat(),
        "model":              "RandomForestClassifier",
        "num_trees":          100,
        "max_depth":          10,
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


def train() -> PipelineModel:
    spark = _get_spark()
    spark.sparkContext.setLogLevel("ERROR")

    df = load_cleaned_data(spark)
    _log_label_distribution(df)

    df = df.dropna(subset=NUMERIC_FEATURES + ["genre_group", LABEL_COL])

    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
    train_rows = train_df.count()
    test_rows  = test_df.count()
    print(f"\n📂 Train: {train_rows:,}  |  Test: {test_rows:,}")

    pipeline = build_pipeline()
    print("\n⏳ Training Random Forest (100 trees, depth 10) — 3-5 minutes...")
    model = pipeline.fit(train_df)
    print("✅ Training complete")

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

    _save_report(metrics, importances, confusion, train_rows, test_rows)
    return model


if __name__ == "__main__":
    import sys
    try:
        train()
        print(f"\n🎵 BopOrFlop model ready at {MODEL_DIR}")
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Training failed: %s", e)
        print(f"\n❌ Training failed: {e}")
        sys.exit(1)