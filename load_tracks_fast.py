"""
Fast bulk insert using copy_from — much faster than row by row.
"""
import io
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from pyspark.sql import SparkSession

load_dotenv()

PROCESSED_DIR = Path("data/processed/spotify_clean")
DB_URL = os.getenv("DB_URL")

def load_tracks_fast():
    print("⏳ Loading tracks table (fast bulk insert)...")

    spark = (
        SparkSession.builder
        .appName("Spotilytics-LoadTracks")
        .config("spark.driver.memory", "4g")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    df = spark.read.parquet(str(PROCESSED_DIR))
    pdf = df.select([
        "track_id", "track_name", "artist_name", "genre", "genre_group",
        "popularity", "popularity_tier", "year", "danceability", "energy",
        "loudness", "tempo", "valence", "acousticness", "speechiness",
        "instrumentalness", "liveness", "duration_ms",
    ]).toPandas()

    print(f"✅ Loaded {len(pdf):,} rows into pandas")

    # Clean data
    pdf = pdf.fillna('')
    pdf['popularity']  = pdf['popularity'].astype(int)
    pdf['year']        = pdf['year'].astype(int)
    pdf['duration_ms'] = pdf['duration_ms'].astype(int)

    # Connect and bulk insert
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    # Clear existing
    cur.execute("DELETE FROM tracks")
    conn.commit()
    print("🗑️  Cleared existing tracks")

    # Build CSV in memory
    print("📦 Building bulk insert buffer...")
    buffer = io.StringIO()
    pdf.to_csv(buffer, index=False, header=False, sep='\t',
               na_rep='\\N', escapechar='\\')
    buffer.seek(0)

    # Bulk copy
    print("🚀 Bulk inserting into Supabase...")
    cols = ["track_id","track_name","artist_name","genre","genre_group",
            "popularity","popularity_tier","year","danceability","energy",
            "loudness","tempo","valence","acousticness","speechiness",
            "instrumentalness","liveness","duration_ms"]

    cur.copy_from(buffer, 'tracks', sep='\t', null='\\N', columns=cols)
    conn.commit()

    cur.close()
    conn.close()

    print(f"\n✅ Tracks table populated — {len(pdf):,} rows")
    print("🎵 Artist Explorer is ready!")


if __name__ == "__main__":
    load_tracks_fast()