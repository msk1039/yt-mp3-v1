"""
Redis client for task storage and queue management.
This module provides Redis connection and helper functions for task management.
"""

import json
import os
import time
from enum import Enum
import redis
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

# Connect to Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

class TaskStatus(Enum):
    """Task status enum for Redis storage"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"  # Added for expired files

class RedisTaskManager:
    """Task manager using Redis for storage"""
    
    @staticmethod
    def create_task(task_id: str, youtube_url: str, title=None, channel=None, thumbnail=None) -> None:
        """
        Create a new task in Redis
        
        Args:
            task_id: Unique task identifier
            youtube_url: YouTube URL to process
            title: Video title
            channel: Channel name
            thumbnail: Thumbnail URL
        """
        task_data = {
            "youtube_url": youtube_url,
            "status": TaskStatus.PENDING.value,
            "progress": 0,
            "message": "Task queued for processing",
            "created_at": int(time.time()),  # Unix timestamp
            "download_count": 0
        }
        
        # Add metadata if provided
        if title:
            task_data["title"] = title
        if channel:
            task_data["channel"] = channel
        if thumbnail:
            task_data["thumbnail"] = thumbnail
        
        # Store task data in Redis
        redis_client.hset(f"task:{task_id}", mapping=task_data)
        
        # Add to tasks list
        redis_client.lpush("tasks:pending", task_id)
        
        # Set expiration (7 days + 1 hour for cleanup)
        redis_client.expire(f"task:{task_id}", 7 * 24 * 3600 + 3600)
    
    @staticmethod
    def update_task(task_id: str, status=None, progress=None, message=None, 
                   file_path=None, error=None, file_metadata=None, download_count=None) -> None:
        """
        Update task status in Redis
        
        Args:
            task_id: Task identifier
            status: New task status
            progress: Progress percentage (0-100)
            message: Status message
            file_path: Path to the converted file
            error: Error message if failed
            file_metadata: Dictionary containing file metadata (size, format, etc)
            download_count: Number of times the file has been downloaded
        """
        update_data = {}
        
        # Only update provided fields
        if status is not None:
            update_data["status"] = status
        if progress is not None:
            update_data["progress"] = progress
        if message is not None:
            update_data["message"] = message
        if file_path is not None:
            update_data["file_path"] = file_path
        if error is not None:
            update_data["error"] = error
        if download_count is not None:
            update_data["download_count"] = download_count
            
        # Handle file metadata as a separate JSON field
        if file_metadata is not None:
            update_data["file_metadata"] = json.dumps(file_metadata)
            
        if update_data:
            redis_client.hset(f"task:{task_id}", mapping=update_data)
            
            # Reset expiration time when task is updated (7 days + 1 hour)
            if status == TaskStatus.COMPLETED.value:
                redis_client.expire(f"task:{task_id}", 7 * 24 * 3600 + 3600)
    
    @staticmethod
    def get_task(task_id: str) -> Dict[str, Any]:
        """
        Get task data from Redis
        
        Args:
            task_id: Task identifier
        
        Returns:
            dict: Task data
        """
        task_data = redis_client.hgetall(f"task:{task_id}")
        
        # Convert progress to float if exists
        if "progress" in task_data:
            task_data["progress"] = float(task_data["progress"])
        
        # Convert download_count to integer if exists
        if "download_count" in task_data:
            try:
                task_data["download_count"] = int(task_data["download_count"])
            except (TypeError, ValueError):
                task_data["download_count"] = 0
                
        # Parse file_metadata from JSON if it exists
        if "file_metadata" in task_data:
            try:
                task_data["file_metadata"] = json.loads(task_data["file_metadata"])
            except json.JSONDecodeError:
                task_data["file_metadata"] = {}
            
        return task_data
    
    @staticmethod
    def get_next_pending_task() -> Optional[str]:
        """
        Get the next pending task from the queue
        
        Returns:
            str: Task ID or None if no pending tasks
        """
        task_id = redis_client.rpop("tasks:pending")
        return task_id
    
    @staticmethod
    def delete_task(task_id: str) -> None:
        """
        Delete a task from Redis
        
        Args:
            task_id: Task identifier
        """
        redis_client.delete(f"task:{task_id}")

# Make sure Redis is working
def check_redis_connection() -> bool:
    """
    Check if Redis connection is working
    
    Returns:
        bool: True if connection works, False otherwise
    """
    try:
        return redis_client.ping()
    except redis.ConnectionError:
        return False
