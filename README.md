# 🎵 YouTube to MP3 Converter

A modern, containerized YouTube to MP3 converter with a beautiful web interface. Built with Next.js frontend, FastAPI backend, and Redis for task management.

## ✨ Features

- 🎵 Convert YouTube videos to high-quality MP3 files
- 🌐 Modern, responsive web interface
- ⚡ Real-time download progress tracking
- 🔄 Background processing with Celery workers
- 📊 Task status monitoring
- 🐳 Fully containerized with Docker
- 🚀 One-click setup and deployment

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- 4GB+ RAM recommended
- Internet connection

### One-Click Run (Recommended)

```bash
# Get your free youtube api key
1. Get a YouTube API key for enhanced metadata
    - Go to https://console.developers.google.com/
    - Create a project and enable YouTube Data API v3
    - Create credentials (API key)
    - Copy the key to .env.example as YOUTUBE_API_KEY=your-key-here
    - change the file name of .env.example to .env 


# Clone the repository
2.  git clone https://github.com/msk1039/yt-mp3-v1.git
    cd yt-mp3-v1

# Run the one-click setup script
3. Run the setup script
./run.sh
```

That's it! The script will:
- ✅ Check all dependencies
- ✅ Set up environment variables
- ✅ Create necessary directories
- ✅ Build and start all containers
- ✅ Wait for services to be ready
- ✅ Open the application in your browser

### Manual Setup

If you prefer manual control:

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables (optional)
nano .env

# Build and start services
docker-compose up --build -d

# Check status
docker-compose ps
```

## 🌐 Usage

1. Open your browser to `http://localhost:3000`
2. Paste a YouTube URL into the input field
3. Click "Download MP3"
4. Wait for the conversion to complete
5. Download your MP3 file!

## 🔧 Development

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │     Redis       │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Task Queue)  │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 6379    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Project Structure

```
├── frontend/          # Next.js web application
├── backend/           # FastAPI backend services
│   ├── api_gateway/   # Main API endpoints
│   ├── download_service/  # YouTube download logic
│   ├── conversion_service/  # Audio conversion
│   └── shared/        # Shared utilities
├── docker-compose.yaml  # Container orchestration
├── run.sh            # One-click setup script
└── deploy.sh         # Production deployment
```

### Local Development

```bash
# View logs
docker-compose logs -f

# Restart a specific service
docker-compose restart backend

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up --build -d
```

## 🚀 Deployment

### VPS Deployment

```bash
# Copy files to your VPS
scp -r . user@your-vps:/path/to/app

# SSH into your VPS
ssh user@your-vps

# Navigate to app directory
cd /path/to/app

# Run production deployment
./deploy.sh prod up
```

### Environment Variables

Key environment variables in `.env`:

```bash
# Optional: YouTube API key for metadata
YOUTUBE_API_KEY=your_youtube_api_key_here

# Application settings
MAX_CONCURRENT_DOWNLOADS=3
CLEANUP_INTERVAL=3600

# Automatically configured by run.sh
PLATFORM=linux/arm64  # or linux/amd64
BACKEND_URL=http://backend:8000
```

## 📊 API Endpoints

- `GET /health` - Health check
- `POST /api/download` - Start download task
- `GET /api/status/{task_id}` - Check task status
- `GET /api/download/{task_id}` - Download completed file

## 🛠️ Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Check what's using the ports
lsof -i :3000,:8000,:6379

# Kill processes if needed
sudo kill -9 <PID>
```

**Permission issues:**
```bash
# Fix directory permissions
./fix-permissions.sh
```

**Container issues:**
```bash
# Reset everything
docker-compose down -v
docker system prune -f
./run.sh
```

### Logs and Debugging

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs redis

# Follow logs in real-time
docker-compose logs -f --tail=50
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `./run.sh`
5. Submit a pull request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## ⚠️ Important Notes

- This tool is for personal use only
- Respect YouTube's Terms of Service
- Only download content you have permission to download
- Some videos may be geo-restricted or require authentication

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. View the logs: `docker-compose logs`
3. Open an issue with detailed information
4. Include your OS, Docker version, and error messages

---

Made with ❤️ for the open source community
