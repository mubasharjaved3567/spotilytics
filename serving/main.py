import os
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

import psycopg2
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger      = logging.getLogger(__name__)
DB_URL      = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5432/spotilytics")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── DB helpers ─────────────────────────────────────────────────────────────
def _query(sql: str, params=None) -> list[dict]:
    conn = psycopg2.connect(DB_URL)
    df   = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df.to_dict(orient="records")


def _execute(sql: str, params=None) -> None:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur  = conn.cursor()
    cur.execute(sql, params)
    cur.close()
    conn.close()


# ── Lifespan ───────────────────────────────────────────────────────────────
_predict_fn = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _predict_fn
    try:
        from ml.predict import predict
        _predict_fn = predict
        print("✅ ML model loaded")
    except FileNotFoundError:
        print("⚠️  ML model not found — run ml/train.py first")
    yield


# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Spotilytics API",
    description="AI-620 Data Engineering — Group 6",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Spotilytics API is running", "docs": "/docs"}


# ── Analytics ──────────────────────────────────────────────────────────────
@app.get("/analytics/music-trends")
def music_trends():
    try:
        return _query("SELECT * FROM music_trends ORDER BY year")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/genre-battle")
def genre_battle():
    try:
        return _query("SELECT * FROM genre_stats ORDER BY avg_popularity DESC")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/mood-map")
def mood_map():
    try:
        return _query("SELECT * FROM mood_map")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── BopOrFlop ──────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    danceability:     float = 0.5
    energy:           float = 0.5
    loudness:         float = -8.0
    tempo:            float = 120.0
    valence:          float = 0.5
    acousticness:     float = 0.3
    speechiness:      float = 0.05
    instrumentalness: float = 0.0
    liveness:         float = 0.1
    duration_ms:      int   = 200_000
    year:             int   = 2023
    genre_group:      str   = "Pop"


@app.post("/predict")
def predict(req: PredictRequest):
    if _predict_fn is None:
        raise HTTPException(status_code=503, detail="ML model not loaded.")
    try:
        return _predict_fn(**req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Artist search ──────────────────────────────────────────────────────────
@app.get("/artist/search")
def search_artists(q: str = ""):
    """Search artists by name — returns matching artists with real stats."""
    try:
        sql = """
            SELECT
                artist_name,
                genre_group,
                ROUND(AVG(popularity)::numeric, 1)       AS avg_popularity,
                COUNT(*)                                  AS track_count,
                MIN(year)                                 AS first_year,
                MAX(year)                                 AS last_year,
                ROUND(AVG(danceability)::numeric, 3)     AS avg_danceability,
                ROUND(AVG(energy)::numeric, 3)            AS avg_energy,
                ROUND(AVG(valence)::numeric, 3)           AS avg_valence,
                ROUND(AVG(acousticness)::numeric, 3)      AS avg_acousticness,
                ROUND(AVG(tempo)::numeric, 1)             AS avg_tempo,
                ROUND(AVG(loudness)::numeric, 2)          AS avg_loudness,
                ROUND(AVG(instrumentalness)::numeric, 3)  AS avg_instrumentalness,
                ROUND(AVG(speechiness)::numeric, 3)       AS avg_speechiness,
                ROUND(AVG(liveness)::numeric, 3)          AS avg_liveness,
                ROUND(AVG(duration_ms)::numeric, 0)       AS avg_duration_ms,
                MAX(popularity)                           AS peak_popularity
            FROM tracks
            WHERE LOWER(artist_name) LIKE LOWER(%s)
            GROUP BY artist_name, genre_group
            ORDER BY avg_popularity DESC
            LIMIT 10
        """
        return _query(sql, params=(f"%{q}%",))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Artist insight (Groq LLM + PostgreSQL cache) ───────────────────────────
@app.get("/artist/insight")
def artist_insight(name: str):
    """
    Get LLM-generated artist intelligence.
    1st search  → generates via Groq → stores in artist_profiles table
    2nd search  → reads from artist_profiles table (no Groq call)
    """
    try:
        # ── Step 1: Check cache first ──────────────────────────────────────
        cached = _query(
            "SELECT * FROM artist_profiles WHERE LOWER(artist_name) = LOWER(%s)",
            params=(name,)
        )

        # Get real data from tracks table
        sql = """
            SELECT
                artist_name,
                genre_group,
                ROUND(AVG(popularity)::numeric, 1)       AS avg_popularity,
                COUNT(*)                                  AS track_count,
                MIN(year)                                 AS first_year,
                MAX(year)                                 AS last_year,
                ROUND(AVG(danceability)::numeric, 3)     AS avg_danceability,
                ROUND(AVG(energy)::numeric, 3)            AS avg_energy,
                ROUND(AVG(valence)::numeric, 3)           AS avg_valence,
                ROUND(AVG(acousticness)::numeric, 3)      AS avg_acousticness,
                ROUND(AVG(tempo)::numeric, 1)             AS avg_tempo,
                ROUND(AVG(speechiness)::numeric, 3)       AS avg_speechiness,
                ROUND(AVG(instrumentalness)::numeric, 3)  AS avg_instrumentalness,
                MAX(popularity)                           AS peak_popularity
            FROM tracks
            WHERE LOWER(artist_name) = LOWER(%s)
            GROUP BY artist_name, genre_group
        """
        rows = _query(sql, params=(name,))
        if not rows:
            raise HTTPException(status_code=404, detail=f"Artist '{name}' not found")

        artist = rows[0]

        # Get top tracks
        top_tracks = _query(
            """SELECT track_name, popularity, year
               FROM tracks
               WHERE LOWER(artist_name) = LOWER(%s)
               ORDER BY popularity DESC LIMIT 5""",
            params=(name,)
        )

        # ── Step 2: Return cached if exists ────────────────────────────────
        if cached:
            profile = cached[0]
            print(f"✅ Cache hit for {name}")
            return {
                **{k: artist[k] for k in artist},
                "top_tracks":        top_tracks,
                "origin_country":    profile["origin_country"],
                "career_start":      profile["career_start"],
                "style_description": profile["style_description"],
                "fun_fact":          profile["fun_fact"],
                "audio_analysis":    profile["audio_analysis"],
                "career_insight":    profile["career_insight"],
                "similar_artists":   json.loads(profile["similar_artists"]),
                "signature_sound":   profile["signature_sound"],
                "cached":            True,
                "generated_at":      str(profile["generated_at"]),
            }

        # ── Step 3: Generate via Groq ──────────────────────────────────────
        print(f"🤖 Generating Groq insight for {name}...")

        prompt = f"""
You are a music data analyst. Based on REAL Spotify audio data, 
generate an artist intelligence report for {artist['artist_name']}.

REAL DATA:
- Genre: {artist['genre_group']}
- Avg popularity: {artist['avg_popularity']}/100
- Peak popularity: {artist['peak_popularity']}/100
- Tracks in dataset: {artist['track_count']}
- Active: {artist['first_year']} to {artist['last_year']}
- Danceability: {artist['avg_danceability']} (0-1)
- Energy: {artist['avg_energy']} (0-1)
- Valence: {artist['avg_valence']} (0-1)
- Acousticness: {artist['avg_acousticness']} (0-1)
- Tempo: {artist['avg_tempo']} BPM
- Speechiness: {artist['avg_speechiness']} (0-1)
- Instrumentalness: {artist['avg_instrumentalness']} (0-1)
TOP TRACKS: {', '.join([t['track_name'] for t in top_tracks])}

Return ONLY this JSON (no extra text):
{{
  "origin_country": "country",
  "career_start": year_number,
  "style_description": "2-3 sentences about musical style based on audio data",
  "fun_fact": "one interesting fact",
  "audio_analysis": "2-3 sentences analyzing what audio features reveal",
  "career_insight": "2 sentences about career trajectory",
  "similar_artists": ["artist1", "artist2", "artist3"],
  "signature_sound": "short phrase"
}}
"""
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
        )

        llm_text = response.choices[0].message.content.strip()
        if "```json" in llm_text:
            llm_text = llm_text.split("```json")[1].split("```")[0].strip()
        elif "```" in llm_text:
            llm_text = llm_text.split("```")[1].split("```")[0].strip()

        llm_data = json.loads(llm_text)

        # ── Step 4: Store in artist_profiles table ─────────────────────────
        _execute("""
            INSERT INTO artist_profiles
                (artist_name, origin_country, career_start, style_description,
                 fun_fact, audio_analysis, career_insight, similar_artists,
                 signature_sound, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (artist_name) DO UPDATE SET
                origin_country    = EXCLUDED.origin_country,
                career_start      = EXCLUDED.career_start,
                style_description = EXCLUDED.style_description,
                fun_fact          = EXCLUDED.fun_fact,
                audio_analysis    = EXCLUDED.audio_analysis,
                career_insight    = EXCLUDED.career_insight,
                similar_artists   = EXCLUDED.similar_artists,
                signature_sound   = EXCLUDED.signature_sound,
                generated_at      = EXCLUDED.generated_at
        """, params=(
            artist["artist_name"],
            llm_data.get("origin_country", "Unknown"),
            llm_data.get("career_start", artist["first_year"]),
            llm_data.get("style_description", ""),
            llm_data.get("fun_fact", ""),
            llm_data.get("audio_analysis", ""),
            llm_data.get("career_insight", ""),
            json.dumps(llm_data.get("similar_artists", [])),
            llm_data.get("signature_sound", ""),
            datetime.now(),
        ))

        print(f"💾 Stored profile for {name} in artist_profiles table")

        return {
            **{k: artist[k] for k in artist},
            "top_tracks":        top_tracks,
            "origin_country":    llm_data.get("origin_country", "Unknown"),
            "career_start":      llm_data.get("career_start", artist["first_year"]),
            "style_description": llm_data.get("style_description", ""),
            "fun_fact":          llm_data.get("fun_fact", ""),
            "audio_analysis":    llm_data.get("audio_analysis", ""),
            "career_insight":    llm_data.get("career_insight", ""),
            "similar_artists":   llm_data.get("similar_artists", []),
            "signature_sound":   llm_data.get("signature_sound", ""),
            "cached":            False,
            "generated_at":      datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Artist insight failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("serving.main:app", host="0.0.0.0", port=8000, reload=True)