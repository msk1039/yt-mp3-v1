"""
Download utilities using yt-dlp CLI to extract audio from YouTube videos.
Optimized for VPS deployment with anti-bot detection measures.
"""

import os
import time
import tempfile
import subprocess
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available in Docker environment
    pass

# Import Redis task manager
from shared.redis_client import RedisTaskManager, TaskStatus

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
        mhtml_indicators = [
            'MIME-Version:', 'Content-Type: multipart/related',
            'Content-Location:', '--boundary', 'text/html'
        ]
        
        for indicator in mhtml_indicators:
            if indicator in header:
                print(f"Invalid file detected: MHTML content found - {indicator}")
                return False
        
        # Check for HTML content (another sign of failed download)
        html_indicators = ['<html', '<HTML', '<!DOCTYPE', '<head>', '<body>']
        for indicator in html_indicators:
            if indicator in header:
                print(f"Invalid file detected: HTML content found - {indicator}")
                return False
        
        return True
        
    except Exception as e:
        print(f"Error validating file {file_path}: {e}")
        return False


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
            # Update Redis when download finishes
            RedisTaskManager.update_task(
                self.task_id,
                status=TaskStatus.DOWNLOADING.value,
                progress=50,
                message="Download completed, processing..."
            )
            
            # Update Celery task progress if available
            if self.celery_task:
                self.celery_task.update_state(
                    state='PROGRESS',
                    meta={'current': 50, 'total': 100, 'status': 'Download completed, processing...'}
                )
        
        elif d['status'] == 'error':
            # Handle download errors
            error_msg = d.get('error', 'Unknown download error')
            print(f"Download error: {error_msg}")
            
            # Update Redis with error
            RedisTaskManager.update_task(
                self.task_id,
                status=TaskStatus.FAILED.value,
                progress=0,
                message=f"Download failed: {error_msg}",
                error=error_msg
            )
            
            # Update Celery task with error if available
            if self.celery_task:
                self.celery_task.update_state(
                    state='FAILURE',
                    meta={'error': error_msg}
                )


def download_audio(task_id: str, url: str, celery_task=None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Download audio from a YouTube URL using yt-dlp CLI with VPS-optimized anti-bot strategies.
    
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
        
        # Base command for all strategies
        base_cmd = [
            'yt-dlp',
            '--extract-flat', 'never',
            '--no-playlist',
            '--format', 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio',
            '--audio-format', 'mp3',
            '--audio-quality', '192K',
            '--output', output_template,
            '--no-warnings',
            '--no-check-certificates',
        ]
        
        # VPS-specific anti-bot strategies (ordered by effectiveness for data center IPs)
        vps_strategies = [
            # Strategy 1: iOS client emulation (most effective for VPS/data center IPs)
            {
                'name': 'iOS Client',
                'args': [
                    '--extractor-args', 'youtube:player_client=ios',
                    '--user-agent', 'com.google.ios.youtube/17.33.2 (iPhone14,3; U; CPU iPhone OS 15_6 like Mac OS X)',
                    '--add-header', 'X-YouTube-Client-Name:5',
                    '--add-header', 'X-YouTube-Client-Version:17.33.2',
                    '--sleep-interval', '1',
                    '--max-sleep-interval', '2',
                ]
            },
            
            # Strategy 2: Android TV client (often bypasses restrictions)
            {
                'name': 'Android TV Client',
                'args': [
                    '--extractor-args', 'youtube:player_client=android_tv',
                    '--user-agent', 'com.google.android.apps.youtube.leanback/2.37.03 (Linux; U; Android 10)',
                    '--add-header', 'X-YouTube-Client-Name:29',
                    '--add-header', 'X-YouTube-Client-Version:2.37.03',
                    '--sleep-interval', '2',
                ]
            },
            
            # Strategy 3: Android client with mobile user agent
            {
                'name': 'Android Mobile',
                'args': [
                    '--extractor-args', 'youtube:player_client=android',
                    '--user-agent', 'com.google.android.youtube/17.31.35 (Linux; U; Android 11) gzip',
                    '--add-header', 'X-YouTube-Client-Name:3',
                    '--add-header', 'X-YouTube-Client-Version:17.31.35',
                    '--sleep-interval', '2',
                ]
            },
            
            # Strategy 4: Basic fallback with minimal detection
            {
                'name': 'Basic Fallback',
                'args': [
                    '--no-check-certificate',
                    '--ignore-errors',
                    '--sleep-interval', '3',
                    '--retries', '2',
                ]
            }
        ]

        # Update progress
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=20,
            message="Starting VPS-optimized download..."
        )

        # Try each strategy until one succeeds
        download_success = False
        last_error = None
        
        for strategy_num, strategy in enumerate(vps_strategies, 1):
            try:
                # Build command with current strategy
                cmd = base_cmd + strategy['args'] + [url]
                
                # Update progress
                RedisTaskManager.update_task(
                    task_id,
                    status=TaskStatus.DOWNLOADING.value,
                    progress=15 + (strategy_num * 8),
                    message=f"Trying {strategy['name']} strategy ({strategy_num}/4)..."
                )
                
                print(f"VPS Strategy {strategy_num} ({strategy['name']}): Starting download...")
                
                process = subprocess.run(
                    cmd,
                    cwd=task_dir,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if process.returncode == 0:
                    print(f"VPS Strategy {strategy_num} ({strategy['name']}) succeeded!")
                    download_success = True
                    break
                else:
                    last_error = process.stderr
                    print(f"VPS Strategy {strategy_num} ({strategy['name']}) failed: {process.stderr[:200]}...")
                    
            except subprocess.TimeoutExpired:
                last_error = f"Strategy {strategy_num} timed out after 5 minutes"
                print(f"VPS Strategy {strategy_num} ({strategy['name']}) timed out")
                continue
            except Exception as e:
                last_error = str(e)
                print(f"VPS Strategy {strategy_num} ({strategy['name']}) exception: {e}")
                continue
        
        if not download_success:
            error_msg = f"All VPS download strategies failed. YouTube may be blocking this video for data center IPs. Last error: {last_error}"
            print(error_msg)
            RedisTaskManager.update_task(
                task_id,
                status=TaskStatus.FAILED.value,
                progress=0,
                message="Download failed: All anti-bot strategies exhausted",
                error=error_msg
            )
            return False, None, error_msg

        # Update progress - download successful
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=60,
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
                    error_msg = f"Downloaded file appears to be invalid (likely MHTML): {largest_file}"
                    print(error_msg)
                    RedisTaskManager.update_task(
                        task_id,
                        status=TaskStatus.FAILED.value,
                        progress=0,
                        message="Download failed: Invalid file format",
                        error=error_msg
                    )
                    return False, None, error_msg
            else:
                error_msg = "No files were downloaded"
                print(error_msg)
                RedisTaskManager.update_task(
                    task_id,
                    status=TaskStatus.FAILED.value,
                    progress=0,
                    message="Download failed: No output files",
                    error=error_msg
                )
                return False, None, error_msg
        
        # Use the first (or only) downloaded file
        downloaded_file = downloaded_files[0]
        
        # Final validation
        if not is_valid_audio_file(downloaded_file):
            error_msg = f"Downloaded file failed validation: {downloaded_file}"
            print(error_msg)
            RedisTaskManager.update_task(
                task_id,
                status=TaskStatus.FAILED.value,
                progress=0,
                message="Download failed: File validation failed",
                error=error_msg
            )
            return False, None, error_msg
        
        # Update progress
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=80,
            message="Download completed successfully!"
        )
        
        print(f"Download successful: {downloaded_file}")
        return True, downloaded_file, None
    
    except subprocess.TimeoutExpired:
        error_message = "Download timeout: Process took longer than 5 minutes"
        print(error_message)
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            progress=0,
            message="Download timed out",
            error=error_message
        )
        return False, None, error_message
    
    except Exception as e:
        error_message = f"Download error: {str(e)}"
        print(error_message)
        
        # Update task status with error
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            progress=0,
            message="Download failed due to unexpected error",
            error=error_message
        )
        
        return False, None, error_message
