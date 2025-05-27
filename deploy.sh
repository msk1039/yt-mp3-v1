#!/bin/bash

# Platform deployment script for yt-mp3 converter
# This script helps you deploy for different platforms

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo -e "${BLUE}Usage: $0 [dev|prod] [build|up|down|restart]${NC}"
    echo ""
    echo -e "${YELLOW}Environments:${NC}"
    echo "  dev   - Development (Mac ARM - linux/arm64)"
    echo "  prod  - Production (VPS x86 - linux/amd64)"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  build   - Build containers only"
    echo "  up      - Build and start all services"
    echo "  down    - Stop and remove all services"
    echo "  restart - Stop, rebuild, and start all services"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 dev up      # Start development environment"
    echo "  $0 prod build  # Build for production"
    echo "  $0 dev restart # Restart development environment"
}

if [ $# -lt 2 ]; then
    print_usage
    exit 1
fi

ENVIRONMENT=$1
COMMAND=$2

# Validate environment
case $ENVIRONMENT in
    dev|development)
        ENV_FILE=".env.development"
        PLATFORM="linux/arm64"
        echo -e "${GREEN}🍎 Setting up for Development (Mac ARM)${NC}"
        ;;
    prod|production)
        ENV_FILE=".env.production"
        PLATFORM="linux/amd64"
        echo -e "${GREEN}🚀 Setting up for Production (VPS x86)${NC}"
        ;;
    *)
        echo -e "${RED}❌ Invalid environment: $ENVIRONMENT${NC}"
        print_usage
        exit 1
        ;;
esac

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Environment file $ENV_FILE not found!${NC}"
    exit 1
fi

# Copy the appropriate environment file
echo -e "${BLUE}📋 Using environment file: $ENV_FILE${NC}"
cp "$ENV_FILE" ".env"

# Create and fix permissions for mounted directories
echo -e "${BLUE}📁 Setting up directories and permissions...${NC}"
mkdir -p backend/temp backend/downloads backend/logs

# Fix permissions for VPS deployment
if [ "$ENVIRONMENT" = "prod" ] || [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${BLUE}🔧 Setting production permissions for UID 1000 (container user)...${NC}"
    # Set ownership to UID 1000 (matches container user) and make directories writable
    sudo chown -R 1000:1000 backend/temp backend/downloads backend/logs 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Could not set ownership to UID 1000. Trying current user...${NC}"
        sudo chown -R $(id -u):$(id -g) backend/temp backend/downloads backend/logs 2>/dev/null || true
    }
    # Make directories writable by the container user (UID 1000)
    chmod -R 755 backend/temp backend/downloads backend/logs
else
    # For development, use current user and make directories accessible
    chmod -R 755 backend/temp backend/downloads backend/logs
fi

# Export platform for docker-compose
export PLATFORM=$PLATFORM

# Export backend URL for docker-compose
export BACKEND_URL="http://backend:8000"

echo -e "${BLUE}🏗️  Platform: $PLATFORM${NC}"

# Execute the requested command
case $COMMAND in
    build)
        echo -e "${BLUE}🔨 Building containers...${NC}"
        docker-compose build --no-cache
        ;;
    up)
        echo -e "${BLUE}🚀 Starting services...${NC}"
        docker-compose up --build -d
        echo -e "${GREEN}✅ Services started! Check status with: docker-compose ps${NC}"
        ;;
    down)
        echo -e "${BLUE}🛑 Stopping services...${NC}"
        docker-compose down
        echo -e "${GREEN}✅ Services stopped!${NC}"
        ;;
    restart)
        echo -e "${BLUE}🔄 Restarting services...${NC}"
        docker-compose down
        docker-compose up --build -d
        echo -e "${GREEN}✅ Services restarted!${NC}"
        ;;
    *)
        echo -e "${RED}❌ Invalid command: $COMMAND${NC}"
        print_usage
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Done!${NC}"
