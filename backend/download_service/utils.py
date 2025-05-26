"""
Download utilities using yt-dlp to extract audio from YouTube videos.
"""

import os
import time
import tempfile
import subprocess
import yt_dlp
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Import Redis task manager
from shared.redis_client import RedisTaskManager, TaskStatus

# Load environment variables
load_dotenv()

# Configure temporary directory for downloads
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/yt-mp3")
STORAGE_DIR = os.getenv("STORAGE_DIR", "/tmp/yt-mp3/output")

# Create directories if they don't exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)

# yt-dlp progress callback for updating Redis task status
class ProgressHook:
    """Progress hook for yt-dlp to update Redis task status"""
    
    def __init__(self, task_id: str, celery_task=None):
        self.task_id = task_id
        self.start_time = time.time()
        self.celery_task = celery_task  # Celery task instance for progress updates
    
    def __call__(self, d: Dict[str, Any]):
        if d['status'] == 'downloading':
            # Calculate download progress
            if 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes'] > 0:
                progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif 'downloaded_bytes' in d and 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            else:
                progress = 0
                
            # Calculate speed and ETA
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            
            if speed and speed > 0:
                speed_str = f"{speed/1024/1024:.2f} MB/s"
            else:
                speed_str = "calculating..."
                
            if eta:
                eta_str = f"{eta} seconds"
            else:
                eta_str = "calculating..."
            
            # Scale progress to 10-50% of total task progress
            scaled_progress = 10 + (progress * 0.4)
            
            # Update Redis with progress
            message = f"Downloading... {progress:.1f}% at {speed_str}, ETA: {eta_str}"
            RedisTaskManager.update_task(
                self.task_id,
                status=TaskStatus.DOWNLOADING.value,
                progress=int(scaled_progress),
                message=message
            )
            
            # Update Celery task progress if available
            if self.celery_task:
                self.celery_task.update_state(
                    state='PROGRESS',
                    meta={'current': int(scaled_progress), 'total': 100, 'status': message}
                )
        
        elif d['status'] == 'finished':
            # Download completed, update Redis
            elapsed = time.time() - self.start_time
            RedisTaskManager.update_task(
                self.task_id,
                status=TaskStatus.DOWNLOADING.value,
                progress=50,
                message=f"Download completed in {elapsed:.1f} seconds. Preparing for conversion..."
            )
            
            # Update Celery task progress if available
            if self.celery_task:
                self.celery_task.update_state(
                    state='PROGRESS',
                    meta={'current': 50, 'total': 100, 'status': 'Download completed'}
                )
        
        elif d['status'] == 'error':
            # Download error, update Redis
            error_msg = d.get('error', 'Unknown download error')
            RedisTaskManager.update_task(
                self.task_id,
                status=TaskStatus.FAILED.value,
                error=error_msg
            )
            
            # Update Celery task if available
            if self.celery_task:
                self.celery_task.update_state(
                    state='FAILURE',
                    meta={'error': error_msg}
                )


def download_audio(task_id: str, url: str, celery_task=None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Download audio from a YouTube URL using yt-dlp.
    
    Args:
        task_id: Task ID for progress tracking
        url: YouTube URL to download
        celery_task: Celery task instance for progress updates (optional)
        
    Returns:
        tuple: (success, output_path, error_message)
    """
    try:
        # Update task status
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=0,
            message="Initializing download..."
        )
        
        # Create a unique directory for this download
        task_dir = os.path.join(TEMP_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # Set up output filename template
        output_template = os.path.join(task_dir, "%(title)s.%(ext)s")
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'progress_hooks': [ProgressHook(task_id, celery_task)],
            'restrictfilenames': True,  # Restrict filenames to ASCII
            'noplaylist': True,  # Only download single video, not playlist
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
        }
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
            # The file extension might be different than what's in the filename template
            # Find the actual file
            if not os.path.exists(downloaded_file):
                # If the prepared filename doesn't exist, find the actual file
                for file in os.listdir(task_dir):
                    if file.startswith(os.path.basename(downloaded_file).split('.')[0]):
                        downloaded_file = os.path.join(task_dir, file)
                        break
            
            if not os.path.exists(downloaded_file):
                raise FileNotFoundError(f"Downloaded file not found: {downloaded_file}")
            
            # Return the downloaded file path
            return True, downloaded_file, None
    
    except Exception as e:
        error_message = f"Download error: {str(e)}"
        
        # Update task status with error
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            error=error_message
        )
        
        return False, None, error_message
