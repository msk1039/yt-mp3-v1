"""
Shared configuration settings for the application.
This provides a central place for configuration variables.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    # This is mainly for development, Docker will provide env vars directly
    load_dotenv()
except ImportError:
    # dotenv not available, which is fine for production Docker containers
    pass

# API and Service Configuration
API_VERSION = "v1"
SERVICE_NAME = "YouTube to MP3 Converter"

# Directory Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/yt-mp3")
STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.join(TEMP_DIR, "output"))

# Create directories if they don't exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# API Keys
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Worker Configuration
MAX_DOWNLOAD_SIZE = os.getenv("MAX_DOWNLOAD_SIZE", "100M")
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "600"))  # 10 minutes
MAX_CONVERSION_TIME = int(os.getenv("MAX_CONVERSION_TIME", "900"))  # 15 minutes
CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", "3600"))  # 1 hour

# Video Settings
MAX_VIDEO_LENGTH = int(os.getenv("MAX_VIDEO_LENGTH", "600"))  # 10 minutes (for free tier)

# File Retention
FILE_RETENTION_DAYS = int(os.getenv("FILE_RETENTION_DAYS", "1"))  # 1 day

# Headers and MIME Types
MP3_MIME_TYPE = "audio/mpeg"
