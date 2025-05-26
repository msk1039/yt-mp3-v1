#!/usr/bin/env python3
"""
Celery worker startup script for YouTube to MP3 converter.
This script starts the Celery worker processes for handling background tasks.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("celery_worker")

def main():
    """Main function to start Celery worker"""
    try:
        # Import Celery app
        from shared.celery_app import celery_app
        from shared.redis_client import check_redis_connection
        
        # Check Redis connection
        if not check_redis_connection():
            logger.error("Redis connection failed. Make sure Redis is running.")
            sys.exit(1)
        
        logger.info("Starting Celery worker...")
        logger.info("Available queues: download, conversion, cleanup")
        
        # Start the Celery worker
        # This will process tasks from all queues by default
        celery_app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=2',  # Number of concurrent worker processes
            '--queues=download,conversion,cleanup',  # Listen to all queues
            '--hostname=worker@%h'
        ])
        
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
