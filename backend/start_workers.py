#!/usr/bin/env python3
"""
Script to start specialized Celery workers for different task types.
This allows scaling different types of tasks independently.
"""

import os
import sys
import subprocess
import time
import signal
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("celery_workers")

class WorkerManager:
    """Manages multiple Celery worker processes"""
    
    def __init__(self):
        self.workers = []
        self.running = False
    
    def start_worker(self, queue_name: str, concurrency: int = 1):
        """Start a worker for a specific queue"""
        try:
            cmd = [
                sys.executable, '-m', 'celery',
                '-A', 'shared.celery_app',
                'worker',
                '--loglevel=info',
                f'--concurrency={concurrency}',
                f'--queues={queue_name}',
                f'--hostname={queue_name}_worker@%h'
            ]
            
            logger.info(f"Starting {queue_name} worker with concurrency {concurrency}")
            process = subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
            self.workers.append((queue_name, process))
            return process
            
        except Exception as e:
            logger.error(f"Failed to start {queue_name} worker: {str(e)}")
            return None
    
    def start_all_workers(self):
        """Start all worker types"""
        logger.info("Starting all Celery workers...")
        
        # Start download workers (can handle multiple concurrent downloads)
        self.start_worker("download", concurrency=2)
        
        # Start conversion workers (CPU intensive, lower concurrency)
        self.start_worker("conversion", concurrency=1)
        
        # Start cleanup workers (lightweight tasks)
        self.start_worker("cleanup", concurrency=1)
        
        self.running = True
        logger.info(f"Started {len(self.workers)} worker processes")
    
    def stop_all_workers(self):
        """Stop all worker processes"""
        logger.info("Stopping all workers...")
        self.running = False
        
        for queue_name, process in self.workers:
            try:
                logger.info(f"Stopping {queue_name} worker (PID: {process.pid})")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {queue_name} worker")
                    process.kill()
                    
            except Exception as e:
                logger.error(f"Error stopping {queue_name} worker: {str(e)}")
        
        self.workers.clear()
        logger.info("All workers stopped")
    
    def wait_for_workers(self):
        """Wait for all workers to finish"""
        try:
            while self.running and self.workers:
                # Check if any worker has died
                for i, (queue_name, process) in enumerate(self.workers):
                    if process.poll() is not None:
                        logger.error(f"{queue_name} worker died with return code {process.returncode}")
                        # Could implement auto-restart here
                        del self.workers[i]
                        break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            self.stop_all_workers()

def main():
    """Main function to manage workers"""
    manager = WorkerManager()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        manager.stop_all_workers()
        sys.exit(0)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Check Redis connection
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from shared.redis_client import check_redis_connection
        
        if not check_redis_connection():
            logger.error("Redis connection failed. Make sure Redis is running.")
            sys.exit(1)
        
        # Start all workers
        manager.start_all_workers()
        
        # Wait for workers
        manager.wait_for_workers()
        
    except Exception as e:
        logger.error(f"Worker manager error: {str(e)}")
        manager.stop_all_workers()
        sys.exit(1)

if __name__ == "__main__":
    main()
