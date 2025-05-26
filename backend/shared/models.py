from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Import TaskStatus from redis_client
from shared.redis_client import TaskStatus

class DownloadRequest(BaseModel):
    url: str
    
class DownloadResponse(BaseModel):
    taskId: str
    status: str
    
class TaskStatusResponse(BaseModel):
    taskId: str
    status: str
    progress: Optional[float] = 0
    message: Optional[str] = None
    downloadUrl: Optional[str] = None
    error: Optional[str] = None
    title: Optional[str] = None
    channel: Optional[str] = None
    thumbnail: Optional[str] = None
    fileSize: Optional[int] = None
    fileSizeFormatted: Optional[str] = None
    downloadCount: Optional[int] = None
    expiresText: Optional[str] = None
