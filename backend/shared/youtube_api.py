"""
YouTube Data API integration for URL validation and metadata retrieval.
"""

import os
import re
from typing import Optional, Dict, Any, Tuple
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Get API key from environment
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

def get_youtube_client():
    """
    Create and return a YouTube API client.
    
    Returns:
        googleapiclient.discovery.Resource: YouTube API client
    """
    if not YOUTUBE_API_KEY:
        raise ValueError("YouTube API key not found. Please add it to your .env file.")
    
    return build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def extract_video_id(url: str) -> Optional[str]:
    """
    Extract the video ID from a YouTube URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        str: Video ID or None if not found
    """
    # Check for youtube.com URLs
    if 'youtube.com' in url:
        # Handle ?v= format
        if 'v=' in url:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        # Handle /v/ format
        elif '/v/' in url:
            match = re.search(r'/v/([^/\?]+)', url)
            return match.group(1) if match else None
    
    # Check for youtu.be URLs
    elif 'youtu.be' in url:
        path = urlparse(url).path
        return path.strip('/') if path else None
    
    return None

def validate_youtube_url(url: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate a YouTube URL using the YouTube Data API.
    
    Args:
        url: YouTube URL to validate
        
    Returns:
        tuple: (is_valid, error_message, video_data)
    """
    # Basic URL format validation
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string", None
    
    if not ('youtube.com' in url or 'youtu.be' in url):
        return False, "Not a valid YouTube URL", None
    
    # Extract video ID
    video_id = extract_video_id(url)
    
    if not video_id:
        return False, "Could not extract video ID from URL", None
    
    try:
        # Create YouTube API client
        youtube = get_youtube_client()
        
        # Request video details from API
        response = youtube.videos().list(
            part='snippet,contentDetails,status',
            id=video_id
        ).execute()
        
        # Check if the video exists
        if not response.get('items'):
            return False, "Video not found or is unavailable", None
        
        video = response['items'][0]
        
        # Check if video is embeddable
        if not video['status'].get('embeddable'):
            return False, "This video does not allow embedding", None
        
        # Check if video is playable (not private)
        if video['status'].get('privacyStatus') == 'private':
            return False, "This video is private", None
            
        # Get metadata for the video
        metadata = {
            'title': video['snippet'].get('title'),
            'channel': video['snippet'].get('channelTitle'),
            'duration': video['contentDetails'].get('duration'),
            'id': video_id,
            'thumbnail': video['snippet'].get('thumbnails', {}).get('medium', {}).get('url')
        }
        
        return True, None, metadata
            
    except HttpError as e:
        error_message = f"YouTube API error: {str(e)}"
        return False, error_message, None
    
    except Exception as e:
        error_message = f"Error validating YouTube URL: {str(e)}"
        return False, error_message, None
