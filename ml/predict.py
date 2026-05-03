import logging
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import col, floor, log1p

# Import the shared feature engineering function from train.py
from ml.train import add_engineered_features, FEATURE_RANGES

logger    = logging.getLogger(__name__)
MODEL_DIR = Path("ml/models/boporflop_model")

MESSAGES = {
    "High": "🔥 This could be a HIT!",
    "Mid":  "🎵 Decent track — mid-tier potential.",
    "Low":  "📉 Probably won't chart.",
}

# ── Singletons ─────────────────────────────────────────────────────────────
_spark: SparkSession | None = None
_model: PipelineModel | None = None
_label_map: dict[int, str] | None = None  # index → tier, extracted from trained StringIndexer


def _get_spark() -> SparkSession:
    """Return a cached SparkSession (one per process)."""
    global _spark
    if _spark is None:
        _spark = (
            SparkSession.builder
            .appName("Spotilytics-Predict")
            .config("spark.driver.memory", "2g")
            .getOrCreate()
        )
    return _spark


def get_model() -> tuple[PipelineModel, dict[int, str]]:
    """
    Load and cache the trained pipeline + extract the real label mapping
    from the StringIndexer stage so index → tier is always correct.
    """
    global _model, _label_map
    if _model is None:
        if not MODEL_DIR.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_DIR}. Run ml/train.py first."
            )
        spark = _get_spark()
        spark.sparkContext.setLogLevel("ERROR")
        _model = PipelineModel.load(str(MODEL_DIR))
        logger.info("Model loaded from %s", MODEL_DIR)

        # FIX: extract label mapping from the trained StringIndexer (stage index 1)
        # StringIndexer stores labels in order — index 0 = most frequent class
        label_indexer_model = _model.stages[1]
        _label_map = {i: label for i, label in enumerate(label_indexer_model.labels)}
        logger.info("Label map from model: %s", _label_map)

    return _model, _label_map


# ── Input validation ───────────────────────────────────────────────────────
def _validate_inputs(**kwargs) -> None:
    """
    Raise ValueError if any numeric feature is outside its valid range.
    Uses FEATURE_RANGES defined in train.py as the single source of truth.
    """
    errors = []
    for feature, value in kwargs.items():
        if feature in FEATURE_RANGES:
            lo, hi = FEATURE_RANGES[feature]
            if not (lo <= float(value) <= hi):
                errors.append(
                    f"  {feature} = {value} is out of range [{lo}, {hi}]"
                )
    if errors:
        raise ValueError("Invalid input features:\n" + "\n".join(errors))


# ── Prediction ─────────────────────────────────────────────────────────────
def predict(
    danceability:     float = 0.5,
    energy:           float = 0.5,
    loudness:         float = -8.0,
    tempo:            float = 120.0,
    valence:          float = 0.5,
    acousticness:     float = 0.3,
    speechiness:      float = 0.05,
    instrumentalness: float = 0.0,
    liveness:         float = 0.1,
    duration_ms:      int   = 200_000,
    year:             int   = 2023,
    genre_group:      str   = "Pop",
) -> dict:
    # Validate inputs before touching Spark
    _validate_inputs(
        danceability=danceability,
        energy=energy,
        loudness=loudness,
        tempo=tempo,
        valence=valence,
        acousticness=acousticness,
        speechiness=speechiness,
        instrumentalness=instrumentalness,
        liveness=liveness,
        duration_ms=duration_ms,
        year=year,
    )

    spark        = _get_spark()
    model, label_map = get_model()

    # Build raw input row — no fake label needed
    input_data = [{
        "danceability":     float(danceability),
        "energy":           float(energy),
        "loudness":         float(loudness),
        "tempo":            float(tempo),
        "valence":          float(valence),
        "acousticness":     float(acousticness),
        "speechiness":      float(speechiness),
        "instrumentalness": float(instrumentalness),
        "liveness":         float(liveness),
        "duration_ms":      float(duration_ms),
        "year":             float(year),
        "genre_group":      genre_group,
        # FIX: supply a real placeholder that matches training schema.
        # The label indexer stage requires this column to exist.
        # We use "Low" (the majority class) as a harmless default —
        # it never affects the prediction output, only the internal indexing.
        "popularity_tier":  "Low",
    }]

    df = spark.createDataFrame(input_data)

    # FIX: apply the same feature engineering used during training
    df = add_engineered_features(df)

    result     = model.transform(df).collect()[0]
    pred_index = int(result["prediction"])

    # FIX: use the label map extracted from the trained model, not a hardcoded dict
    tier       = label_map.get(pred_index, "Low")
    probs      = result["probability"].toArray()
    confidence = round(float(probs[pred_index]) * 100, 1)

    return {
        "popularity_tier": tier,
        "confidence":      confidence,
        "message":         MESSAGES[tier],
        "probabilities": {
            label_map.get(i, str(i)): round(float(p) * 100, 1)
            for i, p in enumerate(probs)
        },
    }


# ── CLI test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    print("🎵 BopOrFlop — test prediction")
    try:
        result = predict(
            danceability=0.8, energy=0.9, loudness=-4.0,
            tempo=128.0, valence=0.7, acousticness=0.05,
            speechiness=0.08, instrumentalness=0.0,
            liveness=0.12, duration_ms=210_000,
            year=2023, genre_group="Pop",
        )
        print(f"\n  Tier       : {result['popularity_tier']}")
        print(f"  Confidence : {result['confidence']}%")
        print(f"  Message    : {result['message']}")
        print(f"  Probs      : {result['probabilities']}")
    except ValueError as e:
        print(f"\n❌ Validation error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Prediction failed: %s", e)
        sys.exit(1)