#!/bin/bash

# yt-dlp VPS testing script
# This script tests different strategies to bypass YouTube bot detection on VPS

if [ $# -eq 0 ]; then
    echo "Usage: $0 <youtube_url>"
    echo "Example: $0 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'"
    exit 1
fi

URL=$1
echo "Testing YouTube download strategies for VPS..."
echo "URL: $URL"
echo ""

# Create test directory
TEST_DIR="/tmp/yt-test-$(date +%s)"
mkdir -p "$TEST_DIR"
echo "Test directory: $TEST_DIR"
echo ""

# Strategy 1: iOS client
echo "=== Strategy 1: iOS Client ==="
yt-dlp \
    --extract-flat never \
    --no-playlist \
    --format 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio' \
    --audio-format mp3 \
    --audio-quality 192K \
    --output "$TEST_DIR/ios_%(title)s.%(ext)s" \
    --no-warnings \
    --no-check-certificates \
    --extractor-args 'youtube:player_client=ios' \
    --user-agent 'com.google.ios.youtube/19.16.3 (iPhone15,2; U; CPU iPhone OS 17_5 like Mac OS X)' \
    --add-header 'X-YouTube-Client-Name:5' \
    --add-header 'X-YouTube-Client-Version:19.16.3' \
    --sleep-interval 2 \
    --max-sleep-interval 4 \
    --verbose \
    "$URL"

if [ $? -eq 0 ]; then
    echo "✅ iOS client strategy succeeded!"
    ls -la "$TEST_DIR"
    exit 0
fi

echo "❌ iOS client strategy failed"
echo ""

# Strategy 2: iOS Music client
echo "=== Strategy 2: iOS Music Client ==="
yt-dlp \
    --extract-flat never \
    --no-playlist \
    --format 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio' \
    --audio-format mp3 \
    --audio-quality 192K \
    --output "$TEST_DIR/ios_music_%(title)s.%(ext)s" \
    --no-warnings \
    --no-check-certificates \
    --extractor-args 'youtube:player_client=ios_music' \
    --user-agent 'com.google.ios.youtubemusic/5.21 (iPhone15,2; U; CPU iPhone OS 17_5 like Mac OS X)' \
    --add-header 'X-YouTube-Client-Name:26' \
    --add-header 'X-YouTube-Client-Version:5.21' \
    --sleep-interval 3 \
    --verbose \
    "$URL"

if [ $? -eq 0 ]; then
    echo "✅ iOS Music client strategy succeeded!"
    ls -la "$TEST_DIR"
    exit 0
fi

echo "❌ iOS Music client strategy failed"
echo ""

# Strategy 3: Android TV embedded
echo "=== Strategy 3: Android TV Embedded ==="
yt-dlp \
    --extract-flat never \
    --no-playlist \
    --format 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio' \
    --audio-format mp3 \
    --audio-quality 192K \
    --output "$TEST_DIR/android_tv_%(title)s.%(ext)s" \
    --no-warnings \
    --no-check-certificates \
    --extractor-args 'youtube:player_client=android_embedded' \
    --user-agent 'com.google.android.apps.youtube.leanback/2.37.03 (Linux; U; Android 10)' \
    --add-header 'X-YouTube-Client-Name:85' \
    --add-header 'X-YouTube-Client-Version:2.37.03' \
    --sleep-interval 2 \
    --verbose \
    "$URL"

if [ $? -eq 0 ]; then
    echo "✅ Android TV embedded strategy succeeded!"
    ls -la "$TEST_DIR"
    exit 0
fi

echo "❌ Android TV embedded strategy failed"
echo ""

# Strategy 4: Web embedded
echo "=== Strategy 4: Web Embedded ==="
yt-dlp \
    --extract-flat never \
    --no-playlist \
    --format 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio' \
    --audio-format mp3 \
    --audio-quality 192K \
    --output "$TEST_DIR/web_embedded_%(title)s.%(ext)s" \
    --no-warnings \
    --no-check-certificates \
    --extractor-args 'youtube:player_client=web_embedded' \
    --user-agent 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15' \
    --add-header 'X-YouTube-Client-Name:56' \
    --add-header 'X-YouTube-Client-Version:1.0' \
    --sleep-interval 4 \
    --verbose \
    "$URL"

if [ $? -eq 0 ]; then
    echo "✅ Web embedded strategy succeeded!"
    ls -la "$TEST_DIR"
    exit 0
fi

echo "❌ Web embedded strategy failed"
echo ""

# Strategy 5: Basic test
echo "=== Strategy 5: Basic Test ==="
yt-dlp \
    --format 'worst[ext=webm]/worst' \
    --output "$TEST_DIR/basic_%(title)s.%(ext)s" \
    --no-check-certificate \
    --ignore-errors \
    --sleep-interval 5 \
    --verbose \
    "$URL"

if [ $? -eq 0 ]; then
    echo "✅ Basic strategy succeeded!"
    ls -la "$TEST_DIR"
    exit 0
fi

echo "❌ All strategies failed"
echo ""
echo "This suggests your VPS IP is heavily blocked by YouTube."
echo "Possible solutions:"
echo "1. Use a different VPS provider"
echo "2. Set up a proxy/VPN"
echo "3. Use a different video source"
echo "4. Contact your VPS provider about the IP reputation"

# Cleanup
rm -rf "$TEST_DIR"
