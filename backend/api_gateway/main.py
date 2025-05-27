from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import os
from dotenv import load_dotenv
from api_gateway.routers import download
from shared.models import DownloadRequest, DownloadResponse
from shared.redis_client import check_redis_connection

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="YouTube to MP3 Converter API",
    description="API for converting YouTube videos to MP3 format",
    version="1.0.0"
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    try:
        # Check if Redis is accessible
        redis_status = check_redis_connection()
        return {
            "status": "healthy",
            "redis": "connected" if redis_status else "disconnected",
            "service": "api_gateway"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "api_gateway"
        }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "YouTube to MP3 Converter API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Debug endpoint to check environment variables
@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables (remove in production)"""
    youtube_key_set = bool(os.getenv('YOUTUBE_API_KEY'))
    return {
        "youtube_api_key_configured": youtube_key_set,
        "youtube_api_key_length": len(os.getenv('YOUTUBE_API_KEY', '')) if youtube_key_set else 0,
        "redis_url": os.getenv('REDIS_URL', 'not set'),
        "temp_dir": os.getenv('TEMP_DIR', 'not set'),
        "storage_dir": os.getenv('STORAGE_DIR', 'not set')
    }

# Check Redis connection on startup
@app.on_event("startup")
async def startup_event():
    if not check_redis_connection():
        print("WARNING: Redis connection failed. Make sure Redis is running.")
    else:
        print("Redis connection successful.")

# Configure CORS for frontend - ensure * is allowed during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(download.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
