#!/usr/bin/env python3
"""
Enhanced startup script for the FastAPI server with Celery workers.
Run this script to start both the API server and background workers.
"""
import os
import sys
import subprocess
import time
import signal
import logging
import uvicorn
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("server")

class ServerManager:
    """Manages FastAPI server and Celery workers"""
    
    def __init__(self):
        self.celery_workers = None
        self.running = False
    
    def start_celery_workers_background(self):
        """Start Celery workers in background"""
        try:
            cmd = [sys.executable, 'celery_worker.py']
            
            logger.info("Starting Celery workers in background...")
            self.celery_workers = subprocess.Popen(
                cmd, 
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give workers time to start
            time.sleep(2)
            
            # Check if workers are still running
            if self.celery_workers.poll() is None:
                logger.info("Celery workers started successfully")
                return True
            else:
                logger.error("Celery workers failed to start")
                return False
            
        except Exception as e:
            logger.error(f"Failed to start Celery workers: {str(e)}")
            return False
    
    def stop_celery_workers(self):
        """Stop Celery workers"""
        if self.celery_workers:
            try:
                logger.info("Stopping Celery workers...")
                self.celery_workers.terminate()
                self.celery_workers.wait(timeout=10)
                logger.info("Celery workers stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Force killing Celery workers")
                self.celery_workers.kill()
            except Exception as e:
                logger.error(f"Error stopping Celery workers: {str(e)}")
            finally:
                self.celery_workers = None
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop_celery_workers()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

def run_with_celery():
    """Run the server with Celery workers"""
    manager = ServerManager()
    manager.setup_signal_handlers()
    
    try:
        # Check Redis connection
        from shared.redis_client import check_redis_connection
        if not check_redis_connection():
            logger.error("Redis connection failed. Make sure Redis is running.")
            logger.error("Start Redis with: redis-server")
            return
    except ImportError as e:
        logger.error(f"Failed to import Redis client: {str(e)}")
        return
    
    # Start Celery workers in background
    if not manager.start_celery_workers_background():
        logger.error("Failed to start Celery workers")
        return
    
    # Start API server (this will block)
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    logger.info(f"Starting FastAPI server on http://{host}:{port}")
    logger.info("API Documentation: http://localhost:8000/docs")
    
    try:
        uvicorn.run(
            "api_gateway.main:app",
            host=host,
            port=port,
            reload=debug  # Enable hot-reloading for development
        )
    finally:
        manager.stop_celery_workers()

def run_api_only():
    """Run only the API server without Celery workers"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    logger.info("Starting API server only (no background workers)")
    logger.info("Note: Tasks will be queued but not processed without workers")
    
    uvicorn.run(
        "api_gateway.main:app",
        host=host,
        port=port,
        reload=debug
    )

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--api-only":
        run_api_only()
    else:
        run_with_celery()
