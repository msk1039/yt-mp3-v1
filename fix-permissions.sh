#!/bin/bash

# Quick fix for permission issues on VPS deployment
# Run this script on your VPS if you get permission denied errors

echo "🔧 Fixing directory permissions for yt-mp3 deployment..."

# Create directories if they don't exist
mkdir -p backend/temp backend/downloads backend/logs

# Fix ownership and permissions
echo "Setting directory permissions..."
chmod 777 backend/temp backend/downloads backend/logs

echo "✅ Permissions fixed!"
echo ""
echo "Now you can run: ./deploy.sh prod up"
