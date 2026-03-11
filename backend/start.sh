#!/bin/bash
# Backend startup script — runs migrations then starts the server

set -e

HOST="${BACKEND_HOST:-0.0.0.0}"
PORT="${PORT:-${BACKEND_PORT:-8000}}"

echo "⏳ Waiting for PostgreSQL to be ready..."
while ! python -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('$DATABASE_URL'.replace('+asyncpg', '')))" 2>/dev/null; do
    sleep 1
done
echo "✅ PostgreSQL is ready"

echo "🔄 Running database migrations..."
cd /app && alembic upgrade head

echo "🚀 Starting BugSense AI backend..."
if [ "${APP_ENV}" = "development" ]; then
    exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
fi

exec uvicorn app.main:app --host "$HOST" --port "$PORT"
