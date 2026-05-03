"""
ml/train_sklearn.py — Train lightweight sklearn model for Render deployment.
Run this ONCE locally after ml/train.py has processed the data.
Saves model as ml/models/rf_model_sklearn.pkl
Does NOT affect your existing PySpark model.
"""
import pickle
import logging
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score
from sklearn.preprocessing import LabelEncoder

PROCESSED_DIR = Path("data/processed/spotify_clean")
MODEL_PATH    = Path("ml/models/rf_model_sklearn.pkl")

logger = logging.getLogger(__name__)

GENRE_MAP = {
    "Pop": 0, "Rock": 1, "Hip-Hop": 2,
    "Electronic": 3, "Acoustic": 4,
    "Metal": 5, "Gospel": 6, "Other": 7
}

FEATURES = [
    "danceability", "energy", "loudness", "tempo", "valence",
    "acousticness", "speechiness", "instrumentalness",
    "liveness", "duration_ms", "year", "genre_idx"
]

def train_sklearn():
    print("⏳ Loading cleaned data...")

    from pyspark.sql import SparkSession
    spark = (
        SparkSession.builder
        .appName("Spotilytics-SKLearn")
        .config("spark.driver.memory", "4g")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    df  = spark.read.parquet(str(PROCESSED_DIR))
    pdf = df.select([
        "danceability", "energy", "loudness", "tempo", "valence",
        "acousticness", "speechiness", "instrumentalness",
        "liveness", "duration_ms", "year", "genre_group", "popularity_tier"
    ]).toPandas()

    print(f"✅ Loaded {len(pdf):,} rows")

    # Encode genre
    pdf["genre_idx"] = pdf["genre_group"].map(GENRE_MAP).fillna(7)

    # Features and label
    X = pdf[FEATURES].values
    y = pdf["popularity_tier"].values

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"📂 Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    # Class weights
    classes, counts = np.unique(y_train, return_counts=True)
    max_count = counts.max()
    weights   = {c: max_count / cnt for c, cnt in zip(classes, counts)}
    print(f"\n⚖️  Class weights: {weights}")

    # Train
    print("\n⏳ Training sklearn Random Forest (100 trees)...")
    model = RandomForestClassifier(
        n_estimators=20,
        max_depth=15,
        class_weight=weights,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)
    print("✅ Training complete")

    # Evaluate
    y_pred = model.predict(X_test)
    f1     = f1_score(y_test, y_pred, average="weighted")
    acc    = accuracy_score(y_test, y_pred)
    print(f"\n📈 F1: {f1:.4f}  |  Accuracy: {acc:.4f}")

    # Save
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({
            "model":   model,
            "classes": list(model.classes_),
            "features": FEATURES,
        }, f)

    print(f"\n💾 Sklearn model saved to {MODEL_PATH}")
    print("🎵 Ready for Render deployment!")


if __name__ == "__main__":
    train_sklearn()