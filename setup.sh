#!/bin/bash
# Setup script for YouTube to MP3 Converter

echo "🚀 YouTube to MP3 Converter Setup"
echo "================================="
echo

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with your YouTube API key."
    echo "Example:"
    echo "YOUTUBE_API_KEY=your_actual_api_key_here"
    echo
    echo "To get a YouTube API key:"
    echo "1. Go to https://console.developers.google.com/"
    echo "2. Create a new project or select existing"
    echo "3. Enable YouTube Data API v3"
    echo "4. Create credentials (API key)"
    echo "5. Add the key to your .env file"
    exit 1
fi

# Check if YOUTUBE_API_KEY is set in .env
if grep -q "YOUTUBE_API_KEY=YOUR_YOUTUBE_API_KEY_HERE" .env; then
    echo "❌ Please update the YOUTUBE_API_KEY in your .env file"
    echo "Replace 'YOUR_YOUTUBE_API_KEY_HERE' with your actual API key"
    exit 1
fi

# Source the .env file
export $(cat .env | xargs)

if [ -z "$YOUTUBE_API_KEY" ]; then
    echo "❌ YOUTUBE_API_KEY not set in .env file"
    exit 1
fi

echo "✅ Environment variables configured"
echo "✅ YouTube API key found"
echo

echo "🔨 Building and starting containers..."
docker-compose up --build

echo
echo "🎉 Setup complete!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "Backend Health: http://localhost:8000/health"
echo "Backend Debug: http://localhost:8000/debug/env"
