import logging
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel

logger  = logging.getLogger(__name__)
MODEL_DIR = Path("ml/models/boporflop_model")

TIER_LABELS = {0: "Low", 1: "Mid", 2: "High"}
MESSAGES    = {
    "High": "🔥 This could be a HIT!",
    "Mid":  "🎵 Decent track — mid-tier potential.",
    "Low":  "📉 Probably won't chart.",
}

_model = None


def _get_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("Spotilytics-Predict")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


def get_model() -> PipelineModel:
    global _model
    if _model is None:
        if not MODEL_DIR.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_DIR}. Run ml/train.py first."
            )
        spark = _get_spark()
        spark.sparkContext.setLogLevel("ERROR")
        _model = PipelineModel.load(str(MODEL_DIR))
        logger.info("Model loaded from %s", MODEL_DIR)
    return _model


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
    spark = _get_spark()
    model = get_model()

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
        "popularity_tier":  "Mid",
    }]

    df         = spark.createDataFrame(input_data)
    result     = model.transform(df).collect()[0]
    pred_index = int(result["prediction"])
    tier       = TIER_LABELS.get(pred_index, "Mid")
    probs      = result["probability"].toArray()
    confidence = round(float(probs[pred_index]) * 100, 1)

    return {
        "popularity_tier": tier,
        "confidence":      confidence,
        "message":         MESSAGES[tier],
        "probabilities": {
            "Low":  round(float(probs[0]) * 100, 1),
            "Mid":  round(float(probs[1]) * 100, 1),
            "High": round(float(probs[2]) * 100, 1),
        },
    }


if __name__ == "__main__":
    print("🎵 BopOrFlop — test prediction")
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