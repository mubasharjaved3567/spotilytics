import os
import logging
from dotenv import load_dotenv
import psycopg2

load_dotenv()

logger = logging.getLogger(__name__)
DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5432/spotilytics")


def get_connection():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    return conn


TABLES = {
    "music_trends": """
        CREATE TABLE IF NOT EXISTS music_trends (
            year             INTEGER PRIMARY KEY,
            avg_energy       FLOAT,
            avg_danceability FLOAT,
            avg_acousticness FLOAT,
            avg_valence      FLOAT,
            avg_popularity   FLOAT,
            track_count      INTEGER
        )
    """,
    "genre_stats": """
        CREATE TABLE IF NOT EXISTS genre_stats (
            genre_group      VARCHAR(50) PRIMARY KEY,
            avg_popularity   FLOAT,
            avg_danceability FLOAT,
            avg_energy       FLOAT,
            avg_valence      FLOAT,
            track_count      INTEGER
        )
    """,
    "mood_map": """
        CREATE TABLE IF NOT EXISTS mood_map (
            genre_group  VARCHAR(50) PRIMARY KEY,
            avg_energy   FLOAT,
            avg_valence  FLOAT,
            track_count  INTEGER
        )
    """,
    "tracks": """
        CREATE TABLE IF NOT EXISTS tracks (
            track_id          VARCHAR(100) PRIMARY KEY,
            track_name        TEXT,
            artist_name       TEXT,
            genre             VARCHAR(100),
            genre_group       VARCHAR(50),
            popularity        INTEGER,
            popularity_tier   VARCHAR(10),
            year              INTEGER,
            danceability      FLOAT,
            energy            FLOAT,
            loudness          FLOAT,
            tempo             FLOAT,
            valence           FLOAT,
            acousticness      FLOAT,
            speechiness       FLOAT,
            instrumentalness  FLOAT,
            liveness          FLOAT,
            duration_ms       INTEGER
        )
    """,
    "artist_profiles": """
        CREATE TABLE IF NOT EXISTS artist_profiles (
            artist_name       VARCHAR(200) PRIMARY KEY,
            origin_country    VARCHAR(100),
            career_start      INTEGER,
            style_description TEXT,
            fun_fact          TEXT,
            audio_analysis    TEXT,
            career_insight    TEXT,
            similar_artists   TEXT,
            signature_sound   VARCHAR(200),
            generated_at      TIMESTAMP DEFAULT NOW()
        )
    """,
}


def create_tables() -> None:
    print("🗄️  Connecting to PostgreSQL...")
    conn = get_connection()
    cur  = conn.cursor()
    for table_name, ddl in TABLES.items():
        cur.execute(ddl)
        print(f"   ✅ Table ready: {table_name}")
        logger.info("Table ready: %s", table_name)
    cur.close()
    conn.close()
    print("✅ All tables ready\n")


if __name__ == "__main__":
    try:
        create_tables()
    except Exception as e:
        print(f"\n❌ DB setup failed: {e}")
        print("   Make sure PostgreSQL is running: docker compose up postgres -d")
        raise SystemExit(1)