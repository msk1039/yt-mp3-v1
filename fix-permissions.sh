#!/bin/bash

# Quick fix for Docker volume permission issues
# Run this script if you get "Cannot write to directory" errors

set -e

echo "🔧 Fixing Docker volume permissions for yt-mp3 converter..."

# Create directories if they don't exist
mkdir -p backend/temp backend/downloads backend/logs

# Set ownership to UID 1000 (matches container user)
echo "Setting ownership to UID 1000..."
if sudo chown -R 1000:1000 backend/temp backend/downloads backend/logs 2>/dev/null; then
    echo "✅ Successfully set ownership to UID 1000"
else
    echo "⚠️  Could not set UID 1000, using current user..."
    chown -R $(id -u):$(id -g) backend/temp backend/downloads backend/logs
fi

# Set proper permissions (775 = rwxrwxr-x)
echo "Setting permissions to 775..."
chmod -R 775 backend/temp backend/downloads backend/logs

# Verify the changes
echo ""
echo "✅ Permissions fixed! Current status:"
ls -la backend/ | grep -E "(temp|downloads|logs)"

echo ""
echo "🚀 You can now restart your containers:"
echo "   docker-compose restart"
echo "   or"
echo "   ./deploy.sh [env] restart"
