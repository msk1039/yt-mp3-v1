"""
Scheduled cleanup script for file service.
This script can be run as a cron job to clean up old files.
Also provides Celery tasks for cleanup operations.
"""

import os
import sys
import time
import logging
import argparse
import threading
from typing import Dict, Any
from dotenv import load_dotenv

# Add the parent directory to the path so we can import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import schedule
except ImportError:
    print("Schedule package not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "schedule"])
    import schedule

from file_service.storage import cleanup_temp_files, scheduled_cleanup
from shared.redis_client import check_redis_connection

# Celery imports (conditional)
try:
    from shared.celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cleanup")

# Load environment variables
load_dotenv()

# Celery tasks (only if Celery is available)
if CELERY_AVAILABLE:
    @celery_app.task(name="file_service.cleanup.cleanup_task")
    def cleanup_task(task_id: str, file_path: str):
        """
        Celery task to clean up temporary files.
        
        Args:
            task_id: Task identifier
            file_path: Path to file to clean up
        """
        try:
            logger.info(f"Cleaning up temporary file for task {task_id}: {file_path}")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Successfully removed temporary file: {file_path}")
                return {"success": True, "file_removed": file_path}
            else:
                logger.warning(f"File not found for cleanup: {file_path}")
                return {"success": True, "message": "File not found (already cleaned up)"}
                
        except Exception as e:
            error_msg = f"Error cleaning up file {file_path}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    @celery_app.task(name="file_service.cleanup.scheduled_cleanup_task")
    def scheduled_cleanup_task():
        """
        Celery task for scheduled cleanup operations.
        Can be run periodically using Celery beat.
        """
        try:
            logger.info("Running scheduled cleanup via Celery task")
            result = run_scheduled_cleanup()
            return result
        except Exception as e:
            error_msg = f"Error in scheduled cleanup task: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

def run_scheduled_cleanup() -> Dict[str, Any]:
    """
    Run scheduled cleanup of files
    
    Returns:
        dict: Results of cleanup operations
    """
    logger.info("Running scheduled file cleanup...")
    
    # Make sure Redis is available
    if not check_redis_connection():
        logger.warning("Redis connection failed, cannot update task statuses")
    
    # Run both cleanups
    temp_results = cleanup_temp_files()
    output_results = scheduled_cleanup()
    
    # Combine results
    results = {
        "temp_files_removed": temp_results[0],
        "temp_bytes_freed": temp_results[1],
        "output_files_removed": output_results[0],
        "output_bytes_freed": output_results[1],
    }
    
    # Log results
    temp_mb = results["temp_bytes_freed"] / (1024 * 1024) if results["temp_bytes_freed"] > 0 else 0
    output_mb = results["output_bytes_freed"] / (1024 * 1024) if results["output_bytes_freed"] > 0 else 0
    
    logger.info(f"Cleanup complete: "
               f"Removed {results['temp_files_removed']} temp files ({temp_mb:.2f} MB) "
               f"and {results['output_files_removed']} output files ({output_mb:.2f} MB)")
    
    return results

def run_scheduler():
    """Run the scheduler loop"""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="File cleanup service")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as a daemon process with scheduled cleanup"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Cleanup interval in hours (default: 24)"
    )
    args = parser.parse_args()
    
    if args.daemon:
        # Run as a scheduled service
        logger.info(f"Starting scheduled cleanup service (interval: {args.interval} hours)")
        
        # Schedule cleanup
        schedule.every(args.interval).hours.do(run_scheduled_cleanup)
        
        # Run scheduler in a separate thread
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # Run once at start
        run_scheduled_cleanup()
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(3600)  # Sleep for an hour
        except KeyboardInterrupt:
            logger.info("Cleanup service stopped")
            sys.exit(0)
    else:
        # Run once
        results = run_scheduled_cleanup()
        
        # Print results in a readable format
        print(f"Cleanup results:")
        print(f"- Removed {results['temp_files_removed']} temporary files ({results['temp_bytes_freed'] / (1024 * 1024):.2f} MB)")
        print(f"- Removed {results['output_files_removed']} output files ({results['output_bytes_freed'] / (1024 * 1024):.2f} MB)")
