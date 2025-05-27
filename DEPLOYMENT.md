# Multi-Platform Deployment Guide

This project supports building for different architectures:
- **Development (Mac ARM)**: `linux/arm64`
- **Production (VPS x86)**: `linux/amd64`

## Quick Start

### Development (Mac)
```bash
# Start development environment
./deploy.sh dev up

# Restart development environment
./deploy.sh dev restart

# Stop development environment
./deploy.sh dev down
```

### Production (VPS)
```bash
# Build for production
./deploy.sh prod build

# Deploy to production
./deploy.sh prod up

# Restart production
./deploy.sh prod restart
```

## Manual Setup

### Development Environment
```bash
# Copy development environment
cp .env.development .env

# Set platform manually
export PLATFORM=linux/arm64

# Build and run
docker-compose up --build -d
```

### Production Environment
```bash
# Copy production environment
cp .env.production .env

# Update your YouTube API key in .env
# YOUTUBE_API_KEY=your_actual_api_key_here

# Set platform manually
export PLATFORM=linux/amd64

# Build and run
docker-compose up --build -d
```

## Environment Files

- `.env.development` - Mac ARM development settings
- `.env.production` - VPS x86 production settings
- `.env` - Active environment (auto-copied by deploy script)

## Platform Detection

The platform is set via the `PLATFORM` environment variable:
- `linux/arm64` - For Apple Silicon Macs
- `linux/amd64` - For Intel/AMD x86 systems

## Deployment Script

The `deploy.sh` script automates:
1. Environment file copying
2. Platform configuration  
3. Docker container building
4. Service management

Run `./deploy.sh` without arguments to see usage instructions.
