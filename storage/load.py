import logging
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import avg, count
from dotenv import load_dotenv

from storage.db import get_connection, create_tables

load_dotenv()

PROCESSED_DIR = Path("data/processed/spotify_clean")
logger = logging.getLogger(__name__)


def _get_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("Spotilytics-Load")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def _music_trends(df: DataFrame):
    return df.groupBy("year").agg(
        avg("energy").alias("avg_energy"),
        avg("danceability").alias("avg_danceability"),
        avg("acousticness").alias("avg_acousticness"),
        avg("valence").alias("avg_valence"),
        avg("popularity").alias("avg_popularity"),
        count("*").alias("track_count"),
    ).orderBy("year")


def _genre_stats(df: DataFrame):
    return df.groupBy("genre_group").agg(
        avg("popularity").alias("avg_popularity"),
        avg("danceability").alias("avg_danceability"),
        avg("energy").alias("avg_energy"),
        avg("valence").alias("avg_valence"),
        count("*").alias("track_count"),
    ).orderBy("avg_popularity", ascending=False)


def _mood_map(df: DataFrame):
    return df.groupBy("genre_group").agg(
        avg("energy").alias("avg_energy"),
        avg("valence").alias("avg_valence"),
        count("*").alias("track_count"),
    )


def _load_to_postgres(spark_df: DataFrame, table: str, conn) -> int:
    pdf = spark_df.toPandas()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table}")
    cols        = list(pdf.columns)
    col_str     = ", ".join(cols)
    placeholder = ", ".join(["%s"] * len(cols))
    for _, row in pdf.iterrows():
        cur.execute(f"INSERT INTO {table} ({col_str}) VALUES ({placeholder})", tuple(row))
    cur.close()
    logger.info("Loaded %d rows into %s", len(pdf), table)
    return len(pdf)


def load() -> None:
    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(
            f"Processed data not found at {PROCESSED_DIR}. Run processing/clean.py first."
        )

    create_tables()

    spark = _get_spark()
    spark.sparkContext.setLogLevel("ERROR")
    df = spark.read.parquet(str(PROCESSED_DIR))
    print(f"✅ Loaded {df.count():,} rows from Parquet\n")

    conn    = get_connection()
    queries = [
        ("music_trends", _music_trends(df)),
        ("genre_stats",  _genre_stats(df)),
        ("mood_map",     _mood_map(df)),
    ]

    print("📤 Loading analytics into PostgreSQL...")
    for table, result_df in queries:
        n = _load_to_postgres(result_df, table, conn)
        print(f"   ✅ {table}: {n} rows loaded")

    conn.close()
    print("\n✅ All analytics loaded into PostgreSQL")


if __name__ == "__main__":
    import sys
    try:
        load()
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Load failed: %s", e)
        print(f"\n❌ Load failed: {e}")
        sys.exit(1)