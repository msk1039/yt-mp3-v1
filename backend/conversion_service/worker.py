"""
Celery worker for conversion service.
Handles converting downloaded audio files to MP3 format using ffmpeg.
"""

import os
import logging
from celery import current_task
from shared.celery_app import celery_app
from shared.redis_client import RedisTaskManager, TaskStatus
from conversion_service.converter import convert_to_mp3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="conversion_service.worker.convert_to_mp3_task")
def convert_to_mp3_task(self, task_id: str, audio_file: str):
    """
    Celery task to convert audio file to MP3 format.
    
    Args:
        task_id: Unique task identifier
        audio_file: Path to the downloaded audio file
        
    Returns:
        dict: Task result with success status and MP3 file path or error
    """
    try:
        logger.info(f"Starting conversion task {task_id} for file: {audio_file}")
        
        # Update task status to converting
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.CONVERTING.value,
            progress=60,
            message="Converting to MP3..."
        )
        
        # Perform the conversion
        success, mp3_file, error = convert_to_mp3(task_id, audio_file)
        
        if not success or not mp3_file:
            error_msg = error or "Conversion failed"
            logger.error(f"Conversion failed for task {task_id}: {error_msg}")
            
            # Update task status to failed
            RedisTaskManager.update_task(
                task_id,
                status=TaskStatus.FAILED.value,
                error=error_msg
            )
            
            return {"success": False, "error": error_msg}
        
        logger.info(f"Conversion completed for task {task_id}: {mp3_file}")
        
        # Update task status to completed
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.COMPLETED.value,
            progress=100,
            message="Conversion completed successfully!",
            file_path=mp3_file
        )
        
        # Chain to cleanup task to remove temporary files
        from file_service.cleanup import cleanup_task
        cleanup_task.delay(task_id, audio_file)  # Clean up the original downloaded file
        
        return {"success": True, "mp3_file": mp3_file}
        
    except Exception as e:
        error_msg = f"Conversion task error: {str(e)}"
        logger.exception(f"Error in conversion task {task_id}")
        
        # Update task status to failed
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            error=error_msg
        )
        
        return {"success": False, "error": error_msg}

@celery_app.task(bind=True, name="conversion_service.worker.conversion_progress_callback")
def conversion_progress_callback(self, task_id: str, progress_data: dict):
    """
    Callback task to update conversion progress.
    
    Args:
        task_id: Task identifier
        progress_data: Progress information from ffmpeg
    """
    try:
        # Extract progress information from ffmpeg output
        # ffmpeg progress is typically provided as frame numbers or time
        percentage = progress_data.get("percentage", 0)
        
        try:
            # Scale conversion progress to 60-90% of total progress
            scaled_progress = 60 + (percentage * 0.3)  # 60% to 90%
            
            # Update task with progress
            RedisTaskManager.update_task(
                task_id,
                progress=int(scaled_progress),
                message=f"Converting... {percentage}%"
            )
            
        except (ValueError, TypeError):
            # If we can't parse progress, just update message
            RedisTaskManager.update_task(
                task_id,
                message="Converting to MP3..."
            )
            
    except Exception as e:
        logger.error(f"Error updating conversion progress for task {task_id}: {str(e)}")
