from fastapi import APIRouter, HTTPException
import uuid
import os
import time
from typing import Optional
from dotenv import load_dotenv
from shared.models import DownloadRequest, DownloadResponse, TaskStatusResponse
from shared.redis_client import RedisTaskManager, TaskStatus, check_redis_connection
from shared.youtube_api import validate_youtube_url
from file_service.storage import serve_file, cleanup_temp_files, get_file_for_task, get_file_metadata

# Celery task imports
try:
    from download_service.worker import download_audio_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    download_audio_task = None

# Load environment variables
load_dotenv()

router = APIRouter()

# Check Redis connection on startup
if not check_redis_connection():
    print("WARNING: Redis connection failed. Make sure Redis is running.")

@router.post("/download", response_model=DownloadResponse)
async def download_video(request: DownloadRequest):
    """
    Accepts a YouTube URL and returns a task ID.
    Validates the URL using YouTube Data API and creates a task in Redis for processing.
    """
    # Make sure Redis is available
    if not check_redis_connection():
        raise HTTPException(status_code=503, detail="Queue service unavailable")
    
    # Validate URL with YouTube Data API
    is_valid, error_message, video_data = validate_youtube_url(request.url)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message or "Invalid YouTube URL")
    
    # Generate a unique task ID
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    
    # Create task in Redis with video metadata
    task_data = {
        "youtube_url": request.url,
        "video_id": video_data.get("id"),
        "title": video_data.get("title", "Untitled Video"),
        "channel": video_data.get("channel", "Unknown Channel"),
        "thumbnail": video_data.get("thumbnail"),
        "status": TaskStatus.PENDING.value,
        "progress": 0,
        "message": "Task queued for processing",
        "created_at": int(time.time())  # Unix timestamp
    }
    
    # Store task using RedisTaskManager with video metadata
    RedisTaskManager.create_task(
        task_id, 
        request.url,
        title=video_data.get("title", "Untitled Video"),
        channel=video_data.get("channel", "Unknown Channel"),
        thumbnail=video_data.get("thumbnail")
    )
    
    # Start Celery task for processing if available
    if CELERY_AVAILABLE and download_audio_task:
        download_audio_task.delay(task_id, request.url)
    else:
        # Fallback message if Celery is not available
        RedisTaskManager.update_task(
            task_id,
            message="Task queued (Celery worker required for processing)"
        )
    
    return DownloadResponse(taskId=task_id, status=TaskStatus.PENDING.value)

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Check the status of a conversion task.
    Retrieves task data from Redis.
    """
    try:
        # Ensure Redis connection
        if not check_redis_connection():
            raise HTTPException(status_code=503, detail="Queue service unavailable")
        
        # Get task from Redis
        task_data = RedisTaskManager.get_task(task_id)
        
        # If task doesn't exist
        if not task_data:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    except Exception as e:
        # Handle and log any unexpected errors
        import logging
        logging.error(f"Error retrieving task status for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error while retrieving task status: {str(e)}"
        )
    
    # Construct the response
    response = {
        "taskId": task_id,
        "status": task_data.get("status", TaskStatus.PENDING.value),
        "progress": task_data.get("progress", 0),
        "message": task_data.get("message", "Task is queued for processing"),
        "title": task_data.get("title"),
        "channel": task_data.get("channel"),
        "thumbnail": task_data.get("thumbnail")
    }
    
    # If task is completed, add file metadata
    if task_data.get("status") == TaskStatus.COMPLETED.value:
        # Check if we already have file metadata
        file_metadata = task_data.get("file_metadata", {})
        
        # If not, try to get it now
        if not file_metadata:
            file_path = get_file_for_task(task_id)
            if file_path:
                file_metadata = get_file_metadata(file_path)
                # Save metadata for future requests
                if file_metadata:
                    RedisTaskManager.update_task(task_id, file_metadata=file_metadata)
        
        # Add file metadata to response
        response["fileSize"] = file_metadata.get("file_size", 0)
        response["fileSizeFormatted"] = file_metadata.get("file_size_formatted", "Unknown size")
        response["downloadUrl"] = f"/api/download/{task_id}"
        response["downloadCount"] = task_data.get("download_count", 0)
        
        # Add file expiration info (7 days from task creation)
        created_at = int(task_data.get("created_at", int(time.time())))
        expires_at = created_at + (7 * 24 * 3600)  # 7 days in seconds
        expires_in_seconds = expires_at - int(time.time())
        
        if expires_in_seconds > 0:
            # Convert to days/hours
            days = expires_in_seconds // (24 * 3600)
            remaining = expires_in_seconds % (24 * 3600)
            hours = remaining // 3600
            
            if days > 0:
                expires_text = f"File expires in {days} day{'s' if days > 1 else ''}"
                if hours > 0:
                    expires_text += f" and {hours} hour{'s' if hours > 1 else ''}"
            else:
                expires_text = f"File expires in {hours} hour{'s' if hours > 1 else ''}"
            
            response["expiresText"] = expires_text
    
    # Add error if task failed
    if task_data.get("status") == TaskStatus.FAILED.value:
        response["error"] = task_data.get("error", "Unknown error occurred")
    
    return response

@router.get("/download/{task_id}")
async def download_file(task_id: str):
    """
    Download the converted MP3 file.
    Uses file_service to retrieve and serve the MP3 file.
    """
    # Ensure Redis connection
    if not check_redis_connection():
        raise HTTPException(status_code=503, detail="Queue service unavailable")
    
    try:
        # Serve the file using file_service
        return serve_file(task_id)
    except HTTPException:
        # Re-raise HTTPException from file service
        raise
    except Exception as e:
        # Log and return error
        import logging
        logging.error(f"Error serving file for task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving file: {str(e)}"
        )
