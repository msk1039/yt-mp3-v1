"""
Download utilities using yt-dlp CLI to extract audio from YouTube videos.
"""

import os
import time
import tempfile
import subprocess
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


def is_valid_audio_file(file_path: str) -> bool:
    """
    Validate that a file is a proper audio file and not an MHTML or other invalid format.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        bool: True if valid audio file, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        # Check file size (should be > 1KB for audio)
        if os.path.getsize(file_path) < 1024:
            return False
        
        # Read first few bytes to check for MHTML markers
        with open(file_path, 'rb') as f:
            header = f.read(1024).decode('utf-8', errors='ignore')
        
        # Check for MHTML indicators
        mhtml_markers = [
            'MIME-Version:',
            'multipart/related',
            'From: <nowhere@yt-dlp',
            'Content-Type: multipart',
            '--ytdlp',
            'boundary='
        ]
        
        for marker in mhtml_markers:
            if marker.lower() in header.lower():
                return False
        
        # Check for common audio file signatures
        with open(file_path, 'rb') as f:
            magic_bytes = f.read(16)
        
        # Common audio file magic numbers
        audio_signatures = [
            b'ID3',  # MP3 with ID3
            b'\xff\xfb',  # MP3
            b'\xff\xf3',  # MP3
            b'\xff\xf2',  # MP3
            b'ftyp',  # M4A/MP4
            b'RIFF',  # WAV
            b'OggS',  # OGG
            b'OpusHead',  # OPUS
        ]
        
        for signature in audio_signatures:
            if magic_bytes.startswith(signature) or signature in magic_bytes:
                return True
        
        # If no clear audio signature, but file extension suggests audio and no MHTML markers
        audio_extensions = ['.mp3', '.m4a', '.wav', '.ogg', '.opus', '.webm']
        if any(file_path.lower().endswith(ext) for ext in audio_extensions):
            return True
        
        return False
        
    except Exception as e:
        print(f"Error validating file {file_path}: {e}")
        return False


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
    Download audio from a YouTube URL using yt-dlp CLI.
    
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
            progress=10,
            message="Initializing download..."
        )
        
        # Create a unique directory for this download
        task_dir = os.path.join(TEMP_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # Set up output filename template
        output_template = os.path.join(task_dir, "%(title)s.%(ext)s")
        
        # Use yt-dlp CLI instead of Python library to avoid "Precondition check failed" errors
        cmd = [
            'yt-dlp',
            '--format', 'bestaudio/best',
            '--output', output_template,
            '--restrict-filenames',  # Restrict filenames to ASCII
            '--no-playlist',  # Only download single video, not playlist
            '--extract-audio',  # Extract audio only
            '--audio-format', 'mp3',  # Convert to MP3
            '--audio-quality', '192',  # Set audio quality
            '--embed-metadata',  # Embed metadata
            '--add-metadata',  # Add metadata
            '--no-check-certificates',  # Skip SSL certificate checks
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            '--referer', 'https://www.youtube.com/',
            url
        ]
        
        # Update progress
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=20,
            message="Starting download with yt-dlp..."
        )
        
        # Run yt-dlp command
        process = subprocess.run(
            cmd,
            cwd=task_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if process.returncode != 0:
            error_msg = f"yt-dlp failed: {process.stderr}"
            raise Exception(error_msg)
        
        # Update progress
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=40,
            message="Download completed, locating file..."
        )
        
        # Find the downloaded file
        downloaded_files = []
        for file in os.listdir(task_dir):
            if file.endswith(('.mp3', '.m4a', '.webm', '.opus', '.wav')):
                downloaded_files.append(os.path.join(task_dir, file))
        
        if not downloaded_files:
            # Check for any files that might have been downloaded
            all_files = os.listdir(task_dir)
            if all_files:
                # Look for the largest file (likely the audio)
                largest_file = max([os.path.join(task_dir, f) for f in all_files], key=os.path.getsize)
                
                # Validate it's not an MHTML file
                if is_valid_audio_file(largest_file):
                    downloaded_files.append(largest_file)
                else:
                    raise Exception(f"Downloaded file appears to be invalid: {largest_file}")
            else:
                raise Exception("No files were downloaded")
        
        # Use the first (or only) downloaded file
        downloaded_file = downloaded_files[0]
        
        # Final validation
        if not is_valid_audio_file(downloaded_file):
            raise Exception(f"Downloaded file failed validation: {downloaded_file}")
        
        # Update progress
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=50,
            message="Download completed successfully!"
        )
        
        return True, downloaded_file, None
    
    except subprocess.TimeoutExpired:
        error_message = "Download timeout: Process took longer than 5 minutes"
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            error=error_message
        )
        return False, None, error_message
    
    except Exception as e:
        error_message = f"Download error: {str(e)}"
        
        # Update task status with error
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            error=error_message
        )
        
        return False, None, error_message