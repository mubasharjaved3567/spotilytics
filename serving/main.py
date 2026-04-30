import os
import logging
from contextlib import asynccontextmanager

import psycopg2
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
DB_URL = os.getenv("DB_URL", "postgresql://postgres:postgres@localhost:5432/spotilytics")


def _query(sql: str) -> list[dict]:
    conn = psycopg2.connect(DB_URL)
    df   = pd.read_sql(sql, conn)
    conn.close()
    return df.to_dict(orient="records")


_predict_fn = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _predict_fn
    try:
        from ml.predict import predict
        _predict_fn = predict
        print("✅ ML model loaded")
    except FileNotFoundError:
        print("⚠️  ML model not found — run ml/train.py first. /predict will return 503.")
    yield


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


@app.get("/")
def root():
    return {"message": "Spotilytics API is running", "docs": "/docs"}


@app.get("/analytics/music-trends")
def music_trends():
    """Average audio features per year — powers Music Trends page."""
    try:
        return _query("SELECT * FROM music_trends ORDER BY year")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/genre-battle")
def genre_battle():
    """Avg popularity, danceability, energy per genre — powers Genre Battle page."""
    try:
        return _query("SELECT * FROM genre_stats ORDER BY avg_popularity DESC")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/mood-map")
def mood_map():
    """Energy vs valence per genre — powers Mood Map page."""
    try:
        return _query("SELECT * FROM mood_map")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    """BopOrFlop — predict Low / Mid / High popularity from audio features."""
    if _predict_fn is None:
        raise HTTPException(status_code=503, detail="ML model not loaded. Run ml/train.py first.")
    try:
        return _predict_fn(**req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("serving.main:app", host="0.0.0.0", port=8000, reload=True)