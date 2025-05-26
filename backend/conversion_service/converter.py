"""
Audio conversion utilities using ffmpeg to convert audio files to MP3.
"""

import os
import time
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import logging

# Import Redis task manager
from shared.redis_client import RedisTaskManager, TaskStatus

# Load environment variables
load_dotenv()

# Configure directories
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/yt-mp3")
STORAGE_DIR = os.getenv("STORAGE_DIR", "/tmp/yt-mp3/output")

# Create directories if they don't exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("converter")

def check_ffmpeg_installed():
    """Check if ffmpeg is installed and accessible"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        return True
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg and make sure it's in your PATH.")
        return False

def convert_to_mp3(task_id: str, input_file: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Convert audio file to MP3 format using ffmpeg.
    
    Args:
        task_id: Task ID for progress tracking
        input_file: Path to the input audio file
        
    Returns:
        tuple: (success, output_path, error_message)
    """
    try:
        # Check if ffmpeg is installed
        if not check_ffmpeg_installed():
            raise RuntimeError("ffmpeg not installed or not in PATH")
        
        # Update task status
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.CONVERTING.value,
            progress=0,
            message="Initializing conversion..."
        )
        
        # Generate output filename
        input_filename = os.path.basename(input_file)
        output_filename = os.path.splitext(input_filename)[0] + ".mp3"
        output_path = os.path.join(STORAGE_DIR, output_filename)
        
        # Make sure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Start time for progress calculation
        start_time = time.time()
        
        # Get audio duration using ffprobe
        duration_cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            input_file
        ]
        
        duration_result = subprocess.run(
            duration_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if duration_result.returncode != 0:
            raise RuntimeError(f"Failed to get audio duration: {duration_result.stderr}")
        
        try:
            total_duration = float(duration_result.stdout.strip())
        except (ValueError, TypeError):
            total_duration = 0
            logger.warning(f"Could not determine audio duration: {duration_result.stdout}")
        
        # Set up ffmpeg command with progress tracking
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-codec:a", "libmp3lame",  # Use MP3 codec
            "-q:a", "2",               # VBR quality setting (0-9, lower is better)
            "-metadata", f"task_id={task_id}",
            "-y",                      # Overwrite output file if it exists
            output_path
        ]
        
        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Track progress
        current_time = 0
        progress_updates = 0
        
        # Process ffmpeg output to track progress
        while True:
            line = process.stderr.readline()
            
            if not line and process.poll() is not None:
                break
                
            # Parse ffmpeg output for progress information
            if "time=" in line:
                # Extract current time in HH:MM:SS format
                time_str = line.split("time=")[1].split()[0].strip()
                
                # Convert time string to seconds
                h, m, s = time_str.split(":")
                current_time = int(h) * 3600 + int(m) * 60 + float(s)
                
                # Calculate progress percentage
                if total_duration > 0:
                    progress = min(100, (current_time / total_duration) * 100)
                else:
                    progress = 50  # Default to 50% if we don't know the duration
                    
                # Only update Redis every 5% or at most every 3 seconds
                if progress_updates % 3 == 0 or progress >= 100:
                    RedisTaskManager.update_task(
                        task_id,
                        status=TaskStatus.CONVERTING.value,
                        progress=progress,
                        message=f"Converting to MP3... {progress:.1f}%"
                    )
                    
                progress_updates += 1
        
        # Wait for process to complete
        process.wait()
        
        # Check if conversion was successful
        if process.returncode != 0:
            stderr = process.stderr.read()
            raise RuntimeError(f"ffmpeg conversion failed with code {process.returncode}: {stderr}")
        
        # Calculate total conversion time
        elapsed = time.time() - start_time
        
        # Update task status
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.COMPLETED.value,
            progress=100,
            message=f"Conversion completed in {elapsed:.1f} seconds",
            file_path=output_path
        )
        
        # Remove the input file to save space
        try:
            os.remove(input_file)
        except Exception as e:
            logger.warning(f"Failed to remove input file {input_file}: {str(e)}")
        
        return True, output_path, None
    
    except Exception as e:
        error_message = f"Conversion error: {str(e)}"
        logger.error(error_message)
        
        # Update task status with error
        RedisTaskManager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            error=error_message
        )
        
        return False, None, error_message
