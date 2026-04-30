import logging
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when
from dotenv import load_dotenv

from processing.validate import validate_raw, validate_cleaned

load_dotenv()

RAW_CSV       = Path("data/raw/spotify_data.csv")
PROCESSED_DIR = Path("data/processed/spotify_clean")

logger = logging.getLogger(__name__)


def _get_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("Spotilytics-Clean")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def _remove_duplicates(df: DataFrame) -> DataFrame:
    before = df.count()
    df     = df.dropDuplicates(["track_id"])
    print(f"   Duplicates removed  : {before - df.count():,}")
    return df


def _drop_nulls(df: DataFrame) -> DataFrame:
    before = df.count()
    df     = df.dropna(subset=["popularity", "genre", "artist_name", "track_name"])
    print(f"   Null rows dropped   : {before - df.count():,}")
    return df


def _fix_bad_values(df: DataFrame) -> DataFrame:
    return df.withColumn("key", when(col("key") == -1, None).otherwise(col("key")))


def _apply_filters(df: DataFrame) -> DataFrame:
    before = df.count()
    df = df.filter(
        (col("duration_ms") > 30_000) &
        (col("tempo") > 0) &
        (col("loudness") < 0) &
        (col("popularity") >= 0) &
        (col("popularity") <= 100)
    )
    print(f"   Outlier rows removed: {before - df.count():,}")
    return df


def _add_genre_group(df: DataFrame) -> DataFrame:
    return df.withColumn("genre_group",
        when(col("genre").contains("pop"),        "Pop")
        .when(col("genre").contains("rock"),       "Rock")
        .when(col("genre").contains("hip-hop"),    "Hip-Hop")
        .when(col("genre").contains("acoustic"),   "Acoustic")
        .when(col("genre").contains("electronic"), "Electronic")
        .when(col("genre").contains("metal"),      "Metal")
        .when(col("genre").contains("gospel"),     "Gospel")
        .otherwise("Other")
    )


def _add_popularity_tier(df: DataFrame) -> DataFrame:
    return df.withColumn("popularity_tier",
        when(col("popularity") <= 30, "Low")
        .when(col("popularity") <= 60, "Mid")
        .otherwise("High")
    )


def clean() -> DataFrame:
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"Raw CSV not found at {RAW_CSV}. Run ingestion first.")

    validate_raw(RAW_CSV)

    spark = _get_spark()
    spark.sparkContext.setLogLevel("ERROR")

    import pandas as pd
    pdf = pd.read_csv(str(RAW_CSV))
    if "Unnamed: 0" in pdf.columns:
        pdf = pdf.drop(columns=["Unnamed: 0"])

    df = spark.createDataFrame(pdf)
    print(f"\n🧹 Cleaning started — {df.count():,} raw rows")

    print("\n   Running cleaning steps...")
    df = _remove_duplicates(df)
    df = _drop_nulls(df)
    df = _fix_bad_values(df)
    df = _apply_filters(df)

    print("\n   Applying transformations...")
    df = _add_genre_group(df)
    df = _add_popularity_tier(df)

    final_count = df.count()
    print(f"\n✅ Cleaning complete — {final_count:,} clean rows")

    print("\n📊 Genre group distribution:")
    df.groupBy("genre_group").count().orderBy("count", ascending=False).show()

    validate_cleaned(df)

    PROCESSED_DIR.parent.mkdir(parents=True, exist_ok=True)
    df.write.mode("overwrite").partitionBy("year").parquet(str(PROCESSED_DIR))
    print(f"💾 Saved to Parquet — {PROCESSED_DIR}")
    logger.info("Saved %d rows to %s", final_count, PROCESSED_DIR)

    return df


if __name__ == "__main__":
    import sys
    try:
        clean()
        print("\n🎵 Ready for aggregations: data/processed/spotify_clean")
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Cleaning failed: %s", e)
        print(f"\n❌ Cleaning failed: {e}")
        sys.exit(1)