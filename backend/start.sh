#!/bin/bash
# Backend startup script — runs migrations then starts the server

set -e

echo "⏳ Waiting for PostgreSQL to be ready..."
while ! python -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('$DATABASE_URL'.replace('+asyncpg', '')))" 2>/dev/null; do
    sleep 1
done
echo "✅ PostgreSQL is ready"

echo "🔄 Running database migrations..."
cd /app && alembic upgrade head

echo "🚀 Starting BugSense AI backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
