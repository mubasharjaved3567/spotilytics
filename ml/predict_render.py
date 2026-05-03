"""
ml/predict_render.py — Lightweight predict for Render deployment.
Uses scikit-learn instead of PySpark. Trained model saved as pickle.
Does NOT affect local ml/predict.py or ml/train.py
"""
import os
import json
import logging
import pickle
from pathlib import Path

logger   = logging.getLogger(__name__)
MODEL_PATH = Path("ml/models/rf_model_sklearn.pkl")

TIER_LABELS = {0: "Low", 1: "Mid", 2: "High"}
MESSAGES    = {
    "High": "🔥 This could be a HIT!",
    "Mid":  "🎵 Decent track — mid-tier potential.",
    "Low":  "📉 Probably won't chart.",
}

GENRE_MAP = {
    "Pop": 0, "Rock": 1, "Hip-Hop": 2,
    "Electronic": 3, "Acoustic": 4,
    "Metal": 5, "Gospel": 6, "Other": 7
}

_model = None
_classes = None


def get_model():
    global _model, _classes
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        _model   = data["model"]
        _classes = data["classes"]
        logger.info("Sklearn model loaded from %s", MODEL_PATH)
    return _model, _classes


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
    model, classes = get_model()

    genre_idx = GENRE_MAP.get(genre_group, 7)

    features = [[
        danceability, energy, loudness, tempo, valence,
        acousticness, speechiness, instrumentalness,
        liveness, float(duration_ms), float(year), float(genre_idx)
    ]]

    pred_idx   = int(model.predict(features)[0])
    proba      = model.predict_proba(features)[0]
    tier       = classes[pred_idx]
    confidence = round(float(proba[pred_idx]) * 100, 1)

    return {
        "popularity_tier": tier,
        "confidence":      confidence,
        "message":         MESSAGES.get(tier, ""),
        "probabilities": {
            classes[i]: round(float(p) * 100, 1)
            for i, p in enumerate(proba)
        },
    }