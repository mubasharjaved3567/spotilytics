"""
Run this once to populate the tracks table in PostgreSQL.
This enables the Artist Explorer feature.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from storage.db import get_connection

load_dotenv()

PROCESSED_DIR = Path("data/processed/spotify_clean")
logger = logging.getLogger(__name__)


def load_tracks():
    print("⏳ Loading tracks table — this takes 5-10 minutes...")

    spark = (
        SparkSession.builder
        .appName("Spotilytics-LoadTracks")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    df  = spark.read.parquet(str(PROCESSED_DIR))
    pdf = df.select([
        "track_id", "track_name", "artist_name", "genre", "genre_group",
        "popularity", "popularity_tier", "year", "danceability", "energy",
        "loudness", "tempo", "valence", "acousticness", "speechiness",
        "instrumentalness", "liveness", "duration_ms",
    ]).toPandas()

    print(f"✅ Loaded {len(pdf):,} rows into pandas")

    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM tracks")

    batch_size = 10000
    total      = len(pdf)

    for i in range(0, total, batch_size):
        batch = pdf.iloc[i:i+batch_size]
        rows  = [tuple(r) for r in batch.itertuples(index=False)]
        cols  = ", ".join(pdf.columns)
        placeholders = ", ".join(["%s"] * len(pdf.columns))
        cur.executemany(
            f"INSERT INTO tracks ({cols}) VALUES ({placeholders}) ON CONFLICT (track_id) DO NOTHING",
            rows
        )
        print(f"   Inserted {min(i+batch_size, total):,} / {total:,} rows...")

    cur.close()
    conn.close()
    print(f"\n✅ Tracks table populated — {total:,} rows")
    print("🎵 Artist Explorer is ready!")


if __name__ == "__main__":
    load_tracks()