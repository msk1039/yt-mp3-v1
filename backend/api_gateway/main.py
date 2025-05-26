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
