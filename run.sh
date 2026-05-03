#!/bin/bash

echo ""
echo "🎵 =================================="
echo "   Spotilytics — AI-620 Group 6"
echo "   Where Spotify Meets Analytics"
echo "=================================="
echo ""

# Check .env exists
if [ ! -f .env ]; then
  echo "❌ .env file not found."
  echo "   Create .env with DB_URL, GROQ_API_KEY, KAGGLE_USERNAME, KAGGLE_KEY"
  exit 1
fi

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker Desktop."
  exit 1
fi

echo "🐳 Step 1 — Starting PostgreSQL..."
docker compose up postgres -d
echo "⏳ Waiting for PostgreSQL to be healthy..."
sleep 15

echo ""
echo "🔄 Step 2 — Running Prefect pipeline..."
echo "   ingest → validate → clean → load → train"
docker compose up pipeline
echo "✅ Pipeline complete"

echo ""
echo "🚀 Step 3 — Starting API + Frontend..."
docker compose up api frontend -d

echo ""
echo "=================================="
echo "✅ Spotilytics is live!"
echo ""
echo "  🌐 Dashboard : http://localhost:3000"
echo "  ⚡ API       : http://localhost:8000"
echo "  📖 API Docs  : http://localhost:8000/docs"
echo "=================================="
echo ""
echo "Press Ctrl+C to stop all services"
echo "Or run: docker compose down"