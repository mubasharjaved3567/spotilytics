# ♪ Spotilytics
### Where Spotify Meets Analytics

AI-620 Fundamentals of Data Engineering — Group 6

---

## Project Structure

```
spotilytics/
├── .env.example              ← copy to .env and fill credentials
├── requirements.txt          ← local dependencies
├── requirements-api.txt      ← Render deployment dependencies
├── Dockerfile                ← API Docker image
├── docker-compose.yml        ← all services
├── run.sh                    ← one-command deployment
├── load_tracks_fast.py       ← bulk load tracks into PostgreSQL
│
├── ingestion/
│   └── ingest.py             ← Kaggle API download + checksum
│
├── processing/
│   ├── validate.py           ← Great Expectations checks
│   └── clean.py              ← PySpark cleaning pipeline
│
├── storage/
│   ├── db.py                 ← PostgreSQL table creation
│   └── load.py               ← analytics aggregation + load
│
├── ml/
│   ├── train.py              ← PySpark Random Forest training
│   ├── train_sklearn.py      ← Sklearn model for Render
│   ├── predict.py            ← PySpark inference (local)
│   └── predict_render.py     ← Sklearn inference (Render)
│
├── serving/
│   └── main.py               ← FastAPI 6 endpoints
│
├── orchestration/
│   └── pipeline.py           ← Prefect flow with retry logic
│
└── frontend/
    └── src/
        └── pages/
            ├── MusicTrends.js
            ├── GenreBattle.js
            ├── MoodMap.js
            ├── BopOrFlop.js
            └── ArtistExplorer.js
```

---

## Prerequisites

- Python 3.11+
- Java 17+ — [adoptium.net](https://adoptium.net)
- Docker Desktop — [docker.com](https://docker.com)
- Node.js 18+ — [nodejs.org](https://nodejs.org)
- Kaggle account — [kaggle.com](https://kaggle.com)
- Groq API key (free) — [console.groq.com](https://console.groq.com)

---

## Environment Variables

```bash
cp .env.example .env
```

Fill in `.env`:

```env
# Kaggle — kaggle.com → Settings → API → Create New Token
KAGGLE_USERNAME=<your_kaggle_username>
KAGGLE_KEY=<your_kaggle_api_key>

# PostgreSQL — pick any password
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your_db_password>
POSTGRES_DB=spotilytics
DB_URL=postgresql://postgres:<your_db_password>@localhost:5432/spotilytics

# Groq — console.groq.com → API Keys → Create
GROQ_API_KEY=<your_groq_api_key>

# Spark
SPARK_DRIVER_MEMORY=4g
```

---

## Option 1 — One Command (Docker)

```bash
git clone https://github.com/mubasharjaved3567/spotilytics
cd spotilytics
cp .env.example .env
# fill in .env with your credentials
chmod +x run.sh
./run.sh
```

Then start frontend in a new terminal:

```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Option 2 — Manual (Step by Step)

### 1. Setup Python environment

```bash
python -m venv venv
source venv/bin/activate       # Mac/Linux
# venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Start PostgreSQL

```bash
docker compose up postgres -d
```

### 3. Create database tables

```bash
python -m storage.db
```

### 4. Download dataset

```bash
python -m ingestion.ingest
```

### 5. Clean and validate data

```bash
python -m processing.clean
```

### 6. Load analytics into PostgreSQL

```bash
python -m storage.load
```

### 7. Load tracks table

```bash
python load_tracks_fast.py
```

### 8. Train ML model

```bash
python -m ml.train
```

### 9. Start API

```bash
python -m serving.main
```

### 10. Start frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

---

## Option 3 — Prefect Pipeline

Run the full pipeline in one command with orchestration:

```bash
python -m orchestration.pipeline
```

---

## Live URLs

| Service | URL |
|---|---|
| Dashboard | https://spotilytics.vercel.app |
| API | https://spotilytics-m501.onrender.com |
| API Docs | https://spotilytics-m501.onrender.com/docs |

---

## Troubleshooting

**Java error / PySpark won't start**
```bash
java -version   # must be 17+
# download from adoptium.net if missing
```

**Port 5432 already in use**
```bash
# change in docker-compose.yml
ports:
  - "5433:5432"
# update DB_URL in .env to port 5433
```

**npm install fails**
```bash
npm install --legacy-peer-deps
```

**Render API slow (50+ sec)**
Visit once before demo to wake it up:
`https://spotilytics-m501.onrender.com/`

---

*Group 6 — Sidra Zubair · Nusrat Abeer Hyder · Sadaf Aamer · M. Mubashar Ali*