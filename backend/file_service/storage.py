"""
File management utilities for storing and serving files.
This includes functions for retrieving, serving, and cleaning up files.
"""

import os
import time
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from fastapi import HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import datetime

# Import Redis task manager
from shared.redis_client import RedisTaskManager, TaskStatus

# Load environment variables
load_dotenv()

# Configure directories
STORAGE_DIR = os.getenv("STORAGE_DIR", "/tmp/yt-mp3/output")
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/yt-mp3")

# Create directories if they don't exist
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("file_service")

def get_file_for_task(task_id: str) -> Optional[str]:
    """
    Get the file path for a task
    
    Args:
        task_id: Task identifier
        
    Returns:
        str: File path or None if not found
    """
    # Get task data from Redis
    task_data = RedisTaskManager.get_task(task_id)
    
    if not task_data:
        return None
    
    # Check if file path is stored in task data
    file_path = task_data.get("file_path")
    
    if not file_path or not os.path.exists(file_path):
        # If not, try to find in storage directory
        logger.info(f"File path not found in task data, searching in storage directory")
        
        # Look for files with task_id in name
        potential_files = [
            os.path.join(STORAGE_DIR, f) for f in os.listdir(STORAGE_DIR)
            if task_id in f and f.endswith(".mp3")
        ]
        
        if potential_files:
            file_path = potential_files[0]
            
            # Update task data with file path
            RedisTaskManager.update_task(task_id, file_path=file_path)
    
    return file_path if file_path and os.path.exists(file_path) else None

def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get metadata for a file
    
    Args:
        file_path: Path to file
        
    Returns:
        dict: File metadata including size, creation time, etc.
    """
    if not file_path or not os.path.exists(file_path):
        return {}
    
    try:
        stat_info = os.stat(file_path)
        file_size = stat_info.st_size
        created_time = datetime.datetime.fromtimestamp(stat_info.st_ctime)
        
        # Format file size for human readability
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        
        if size_mb >= 1:
            size_str = f"{size_mb:.2f} MB"
        else:
            size_str = f"{size_kb:.2f} KB"
        
        metadata = {
            "file_size": file_size,
            "file_size_formatted": size_str,
            "created_at": created_time.isoformat(),
            "filename": os.path.basename(file_path),
        }
        
        return metadata
    except Exception as e:
        logger.error(f"Error getting file metadata: {str(e)}")
        return {}

def serve_file(task_id: str) -> FileResponse:
    """
    Serve a file for a task
    
    Args:
        task_id: Task identifier
        
    Returns:
        FileResponse: FastAPI file response
    
    Raises:
        HTTPException: If task or file not found
    """
    # Get task data from Redis
    task_data = RedisTaskManager.get_task(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check task status
    status = task_data.get("status")
    if status != TaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400, 
            detail=f"Task {task_id} is not completed (status: {status})"
        )
    
    # Get file path
    file_path = get_file_for_task(task_id)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found for task {task_id}")
    
    # Get filename for download
    filename = os.path.basename(file_path)
    
    # Use video title if available, fallback to filename
    title = task_data.get("title", "").strip()
    if title:
        try:
            # Clean up title for use as filename
            title = title.replace("/", "_").replace("\\", "_").replace(":", "_")
            # Replace other problematic characters
            for char in ['?', '*', '"', '<', '>', '|', '「', '」', ''', ''', '"', '"']:
                title = title.replace(char, '_')
                
            # Remove any other non-ASCII characters
            import re
            title = re.sub(r'[^\x00-\x7F]+', '_', title)
            
            # Ensure the title is not too long
            if len(title) > 100:
                title = title[:97] + "..."
                
            download_filename = f"{title}.mp3"
            
            # Final check - if the filename is still not ASCII-safe
            download_filename.encode('ascii')
            
        except Exception as e:
            logger.warning(f"Error creating safe filename from title '{title}': {str(e)}")
            # Fall back to a simple filename with task ID
            download_filename = f"audio_{task_id}.mp3"
    else:
        download_filename = filename
    
    # Get file metadata to update task in Redis
    file_metadata = get_file_metadata(file_path)
    if file_metadata:
        RedisTaskManager.update_task(task_id, file_metadata=file_metadata)
    
    # Mark file as accessed (for cleanup tracking)
    try:
        # Update last access time
        os.utime(file_path, None)
        # Record download in Redis
        download_count = task_data.get("download_count", 0) + 1
        RedisTaskManager.update_task(task_id, download_count=download_count)
    except Exception as e:
        logger.error(f"Error updating file access time: {str(e)}")
    
    # Prepare safe Content-Disposition header with filename
    try:
        import urllib.parse
        # URL encode the filename for the Content-Disposition header
        encoded_filename = urllib.parse.quote(download_filename)
        content_disposition = f'attachment; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}'
    except Exception as e:
        logger.error(f"Error encoding filename for Content-Disposition: {str(e)}")
        # Fallback to a simple ASCII filename
        content_disposition = f'attachment; filename="audio_{task_id}.mp3"'
    
    # Serve file with appropriate headers
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        # Don't use the filename parameter as it doesn't handle encoding properly
        # We'll set Content-Disposition ourselves
        headers={
            "Content-Disposition": content_disposition,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=31536000",  # Cache for 1 year
            "Access-Control-Allow-Origin": "*",  # Allow cross-origin requests
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

def cleanup_temp_files(task_id: str = None) -> Tuple[int, int]:
    """
    Clean up temporary files for a task or all tasks
    
    Args:
        task_id: Optional task ID to clean up
    
    Returns:
        tuple: (number of files deleted, number of bytes freed)
    """
    files_removed = 0
    bytes_freed = 0
    
    if task_id:
        # Clean up specific task
        task_temp_dir = os.path.join(TEMP_DIR, task_id)
        if os.path.exists(task_temp_dir):
            try:
                # Get size before deletion
                dir_size = sum(os.path.getsize(os.path.join(task_temp_dir, f)) 
                              for f in os.listdir(task_temp_dir) 
                              if os.path.isfile(os.path.join(task_temp_dir, f)))
                
                # Remove the directory
                shutil.rmtree(task_temp_dir)
                
                files_removed = 1
                bytes_freed = dir_size
                
                logger.info(f"Removed temp directory for task {task_id}, freed {bytes_freed} bytes")
                
            except Exception as e:
                logger.error(f"Error cleaning up temp directory for task {task_id}: {str(e)}")
    else:
        # Clean up all files older than 24 hours
        current_time = time.time()
        cutoff_time = current_time - (24 * 3600)  # 24 hours ago
        
        for root, dirs, files in os.walk(TEMP_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < cutoff_time:
                        # Get file size before deletion
                        file_size = os.path.getsize(file_path)
                        
                        # Remove file
                        os.remove(file_path)
                        
                        files_removed += 1
                        bytes_freed += file_size
                        
                        logger.info(f"Removed old file {file_path}, freed {file_size} bytes")
                
                except Exception as e:
                    logger.error(f"Error cleaning up file {file_path}: {str(e)}")
    
    return files_removed, bytes_freed

def scheduled_cleanup() -> Tuple[int, int]:
    """
    Run scheduled cleanup of output files
    
    Returns:
        tuple: (number of files deleted, number of bytes freed)
    """
    files_removed = 0
    bytes_freed = 0
    
    try:
        # Clean up output files older than 7 days
        current_time = time.time()
        cutoff_time = current_time - (7 * 24 * 3600)  # 7 days ago
        
        for file in os.listdir(STORAGE_DIR):
            file_path = os.path.join(STORAGE_DIR, file)
            
            if not os.path.isfile(file_path):
                continue
                
            try:
                # Use the most recent of creation or modification time
                file_ctime = os.path.getctime(file_path)
                file_mtime = os.path.getmtime(file_path)
                last_access = max(file_ctime, file_mtime)
                
                if last_access < cutoff_time:
                    # Get file size before deletion
                    file_size = os.path.getsize(file_path)
                    
                    # Extract task_id from filename if possible
                    task_id = None
                    if file.startswith("task-") and "_" in file:
                        task_id = file.split("_")[0]
                    
                    # Remove file
                    os.remove(file_path)
                    
                    files_removed += 1
                    bytes_freed += file_size
                    
                    logger.info(f"Removed old output file {file_path}, freed {file_size} bytes")
                    
                    # Update task status if task_id was found
                    if task_id:
                        try:
                            RedisTaskManager.update_task(task_id, status=TaskStatus.EXPIRED.value, 
                                                       message="File expired and was removed from server")
                        except Exception:
                            pass
                        
            except Exception as e:
                logger.error(f"Error cleaning up file {file_path}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error during scheduled cleanup: {str(e)}")
        
    return files_removed, bytes_freed
