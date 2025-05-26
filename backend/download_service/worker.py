"""
Celery worker for download service.
Handles downloading YouTube videos using yt-dlp.
"""

import os
import logging
import time
from celery import current_task
from shared.celery_app import celery_app
from shared.redis_client import RedisTaskManager, TaskStatus
from download_service.utils import download_audio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="download_service.worker.download_audio_task")
def download_audio_task(self, task_id: str, youtube_url: str):
    """
    Celery task to download audio from YouTube video.
    
    Args:
        task_id: Unique task identifier
        youtube_url: YouTube URL to download
        
    Returns:
        dict: Task result with success status and file path or error
    """
    try:
        logger.info(f"Starting download task {task_id} for URL: {youtube_url}")
        
        # Update task status to downloading
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=10,
            message="Starting download..."
        )
        
        # Perform the download
        success, audio_file, error = download_audio(task_id, youtube_url, self)
        
        if not success or not audio_file:
            error_msg = error or "Download failed"
            logger.error(f"Download failed for task {task_id}: {error_msg}")
            
            # Update task status to failed
            RedisTaskManager.update_task(
                task_id,
                status=TaskStatus.FAILED.value,
                error=error_msg
            )
            
            return {"success": False, "error": error_msg}
        
        logger.info(f"Download completed for task {task_id}: {audio_file}")
        
        # Update progress after download
        RedisTaskManager.update_task(
            task_id,
            progress=50,
            message="Download completed, starting conversion..."
        )
        
        # Chain to conversion task
        from conversion_service.worker import convert_to_mp3_task
        convert_to_mp3_task.delay(task_id, audio_file)
        
        return {"success": True, "audio_file": audio_file}
        
    except Exception as e:
        error_msg = f"Download task error: {str(e)}"
        logger.exception(f"Error in download task {task_id}")
        
        # Update task status to failed
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            error=error_msg
        )
        
        return {"success": False, "error": error_msg}

@celery_app.task(bind=True, name="download_service.worker.download_progress_callback")
def download_progress_callback(self, task_id: str, progress_data: dict):
    """
    Callback task to update download progress.
    
    Args:
        task_id: Task identifier
        progress_data: Progress information from yt-dlp
    """
    try:
        # Extract progress percentage
        percentage = progress_data.get("_percent_str", "0%").strip("%")
        
        try:
            progress = int(float(percentage))
            # Scale download progress to 10-50% of total progress
            scaled_progress = 10 + (progress * 0.4)  # 10% to 50%
            
            # Update task with progress
            RedisTaskManager.update_task(
                task_id,
                progress=int(scaled_progress),
                message=f"Downloading... {progress}%"
            )
            
        except (ValueError, TypeError):
            # If we can't parse progress, just update message
            RedisTaskManager.update_task(
                task_id,
                message="Downloading..."
            )
            
    except Exception as e:
        logger.error(f"Error updating download progress for task {task_id}: {str(e)}")
