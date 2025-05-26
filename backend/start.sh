#!/bin/bash
# filepath: /Users/meow/code/projects/yt-mp3/v1/backend/start.sh

set -e

echo "Starting YouTube to MP3 Converter Backend..."

# Wait for Redis to be available
echo "Waiting for Redis..."
while ! python -c "import redis; r=redis.Redis(host='redis', port=6379); r.ping()" 2>/dev/null; do
    echo "Redis is unavailable - sleeping"
    sleep 1
done
echo "Redis is ready!"

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A shared.celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

# Start FastAPI server
echo "Starting FastAPI server..."
exec uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --workers 1