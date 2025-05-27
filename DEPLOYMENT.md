# Multi-Platform Deployment Guide

This project supports building for different architectures and uses **server-side API calls** for better security and deployment flexibility:
- **Development (Mac ARM)**: `linux/arm64`
- **Production (VPS x86)**: `linux/amd64`

## Architecture

**NEW**: The frontend now uses Next.js API routes for server-side communication:
- Frontend → Next.js API routes → Backend (Docker internal network)
- No more client-side direct API calls to localhost:8000
- Works seamlessly in production environments

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

## Fixed Issues

✅ **Client-side API calls**: Replaced direct `fetch('http://localhost:8000')` with Next.js API routes  
✅ **Cross-origin issues**: Server-side API calls eliminate CORS problems  
✅ **Production deployment**: Frontend now works on any domain/IP  
✅ **Multi-platform builds**: ARM for development, x86 for production  

## API Architecture

### Before (Broken in production)
```
Client Browser → http://localhost:8000/api/download (❌ Points to user's machine)
```

### After (Works everywhere)  
```
Client Browser → /api/download → Next.js API Route → http://backend:8000/api/download
```

## Environment Variables

### Backend Communication
- `BACKEND_URL=http://backend:8000` - Internal Docker network communication
- `NEXT_PUBLIC_API_URL` - Only used for legacy fallbacks (can be removed)

## Manual Setup

### Development Environment
```bash
# Copy development environment
cp .env.development .env

# Set platform manually
export PLATFORM=linux/arm64
export BACKEND_URL=http://backend:8000

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
export BACKEND_URL=http://backend:8000

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
3. Backend URL configuration
4. Docker container building
5. Service management

Run `./deploy.sh` without arguments to see usage instructions.
