"""
Background worker to process tasks from Redis.
This worker handles downloading and converting YouTube videos to MP3 format.
In future steps, this will be replaced by proper Celery workers.
"""

import time
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the path so we can import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.redis_client import RedisTaskManager, TaskStatus, check_redis_connection
from download_service.utils import download_audio
from conversion_service.converter import convert_to_mp3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("worker")

# Load environment variables
load_dotenv()

# Configure directories
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/yt-mp3")
STORAGE_DIR = os.getenv("STORAGE_DIR", "/tmp/yt-mp3/output")

# Create directories if they don't exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)

def process_task(task_id: str) -> bool:
    """
    Process a single task from the queue
    Download and convert a YouTube video to MP3
    
    Args:
        task_id: Task identifier
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get task data
        task_data = RedisTaskManager.get_task(task_id)
        if not task_data:
            logger.error(f"Task {task_id} not found")
            return False
        
        youtube_url = task_data.get("youtube_url")
        if not youtube_url:
            logger.error(f"No URL found for task {task_id}")
            RedisTaskManager.update_task(
                task_id, 
                status=TaskStatus.FAILED.value, 
                error="Invalid task data: No YouTube URL provided"
            )
            return False
        
        logger.info(f"Processing task {task_id} for URL: {youtube_url}")
        
        # Step 1: Download audio
        success, audio_file, error = download_audio(task_id, youtube_url)
        
        if not success or not audio_file:
            logger.error(f"Download failed: {error}")
            RedisTaskManager.update_task(
                task_id, 
                status=TaskStatus.FAILED.value, 
                error=error or "Download failed"
            )
            return False
        
        logger.info(f"Download complete: {audio_file}")
        
        # Step 2: Convert audio to MP3
        success, mp3_file, error = convert_to_mp3(task_id, audio_file)
        
        if not success or not mp3_file:
            logger.error(f"Conversion failed: {error}")
            RedisTaskManager.update_task(
                task_id, 
                status=TaskStatus.FAILED.value, 
                error=error or "Conversion failed"
            )
            return False
        
        logger.info(f"Conversion complete: {mp3_file}")
        
        # Task completed successfully
        RedisTaskManager.update_task(
            task_id, 
            status=TaskStatus.COMPLETED.value,
            progress=100,
            message="Conversion completed successfully!",
            file_path=mp3_file
        )
        
        logger.info(f"Task {task_id} completed successfully")
        return True
        
    except Exception as e:
        logger.exception(f"Error processing task {task_id}")
        # Update task status to failed
        try:
            RedisTaskManager.update_task(
                task_id, 
                status=TaskStatus.FAILED.value,
                error=str(e)
            )
        except Exception as inner_e:
            logger.error(f"Error updating task status: {str(inner_e)}")
        return False

def main():
    """Main worker function that processes tasks from the queue"""
    print("Starting background worker...")
    
    if not check_redis_connection():
        print("ERROR: Redis connection failed. Make sure Redis is running.")
        return
    
    print("Connected to Redis. Waiting for tasks...")
    
    try:
        # Simple polling loop
        # In a real implementation, this would be replaced by Celery
        while True:
            # Get next task from the queue
            task_id = RedisTaskManager.get_next_pending_task()
            
            if task_id:
                print(f"Found task {task_id}")
                process_task(task_id)
            else:
                # No tasks, sleep for a bit
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("Worker stopped by user")
    except Exception as e:
        print(f"Worker error: {str(e)}")

if __name__ == "__main__":
    main()
