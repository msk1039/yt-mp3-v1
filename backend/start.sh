#!/bin/bash
# filepath: /Users/meow/code/projects/yt-mp3/v2/backend/start.sh

set -e

echo "Starting YouTube to MP3 Converter Backend..."

# Wait for Redis to be available
echo "Waiting for Redis..."
while ! python -c "import redis; r=redis.Redis(host='redis', port=6379); r.ping()" 2>/dev/null; do
    echo "Redis is unavailable - sleeping"
    sleep 2
done

echo "Redis is ready!"

# Test directory write access
echo "Testing directory write permissions..."
if ! touch /app/temp/test-write 2>/dev/null; then
    echo "Error: Cannot write to /app/temp directory"
    echo "This is likely a volume mount permission issue."
    echo ""
    echo "Directory ownership and permissions:"
    ls -la /app/ | grep -E "(temp|downloads|logs)"
    echo ""
    echo "To fix this on your host system, run:"
    echo "  sudo chown -R 1000:1000 ./backend/temp ./backend/downloads ./backend/logs"
    echo "  sudo chmod -R 775 ./backend/temp ./backend/downloads ./backend/logs"
    echo ""
    echo "Then restart the containers with: docker-compose restart"
    exit 1
fi
rm -f /app/temp/test-write 2>/dev/null || true
echo "Directory permissions OK!"

# Start the application
echo "Starting FastAPI server and Celery workers..."
python run_server.py

