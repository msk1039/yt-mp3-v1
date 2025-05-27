#!/bin/bash
# filepath: /Users/meow/code/projects/yt-mp3/v2/backend/start.sh

set -e

echo "Starting YouTube to MP3 Converter Backend..."

# Ensure directories exist and have correct permissions
echo "Setting up directories and permissions..."
mkdir -p /app/temp /app/downloads /app/logs

# Try to fix permissions if we have write access
if [ -w /app/temp ]; then
    chmod 755 /app/temp /app/downloads /app/logs 2>/dev/null || true
else
    echo "Warning: Cannot write to /app/temp - checking if directories are accessible..."
    # Test if we can create a test file
    if ! touch /app/temp/test-write 2>/dev/null; then
        echo "Error: Cannot write to /app/temp directory"
        echo "Please fix directory permissions on the host:"
        echo "  sudo chmod 777 ./backend/temp ./backend/downloads ./backend/logs"
        exit 1
    fi
    rm -f /app/temp/test-write 2>/dev/null || true
fi

# Wait for Redis to be available
echo "Waiting for Redis..."
while ! python -c "import redis; r=redis.Redis(host='redis', port=6379); r.ping()" 2>/dev/null; do
    echo "Redis is unavailable - sleeping"
    sleep 1
done
echo "Redis is ready!"

# Start the application
echo "Starting application..."
python run_server.py

