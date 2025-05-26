#!/usr/bin/env python3
"""
Celery monitoring script for YouTube to MP3 converter.
Provides utilities to monitor task queues, worker status, and task progress.
"""

import os
import sys
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def monitor_queues():
    """Monitor Celery queue status"""
    try:
        from shared.celery_app import celery_app
        from shared.redis_client import redis_client
        
        print("=== Celery Queue Monitor ===")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Get queue lengths
        queues = ['download', 'conversion', 'cleanup']
        
        for queue in queues:
            length = redis_client.llen(queue)
            print(f"{queue.capitalize()} Queue: {length} tasks")
        
        print()
        
        # Get active workers
        inspect = celery_app.control.inspect()
        
        # Get worker stats
        stats = inspect.stats()
        if stats:
            print("=== Active Workers ===")
            for worker, data in stats.items():
                print(f"Worker: {worker}")
                print(f"  Total Tasks: {data.get('total', {})}")
                print(f"  Pool: {data.get('pool', {})}")
                print()
        else:
            print("No active workers found")
        
        # Get active tasks
        active = inspect.active()
        if active:
            print("=== Active Tasks ===")
            for worker, tasks in active.items():
                if tasks:
                    print(f"Worker: {worker}")
                    for task in tasks:
                        print(f"  Task: {task.get('name', 'Unknown')}")
                        print(f"  ID: {task.get('id', 'Unknown')}")
                        print(f"  Args: {task.get('args', [])}")
                        print()
        else:
            print("No active tasks")
        
    except Exception as e:
        print(f"Error monitoring queues: {str(e)}")

def purge_queues():
    """Purge all Celery queues"""
    try:
        from shared.celery_app import celery_app
        
        response = input("Are you sure you want to purge all queues? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled")
            return
        
        print("Purging queues...")
        
        # Purge all queues
        celery_app.control.purge()
        
        print("All queues purged successfully")
        
    except Exception as e:
        print(f"Error purging queues: {str(e)}")

def restart_workers():
    """Restart all Celery workers"""
    try:
        from shared.celery_app import celery_app
        
        response = input("Are you sure you want to restart all workers? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled")
            return
        
        print("Restarting workers...")
        
        # Restart workers
        celery_app.control.broadcast('pool_restart', arguments={'reload': True})
        
        print("Workers restart signal sent")
        
    except Exception as e:
        print(f"Error restarting workers: {str(e)}")

def show_task_details(task_id):
    """Show details for a specific task"""
    try:
        from shared.redis_client import RedisTaskManager
        
        task_data = RedisTaskManager.get_task(task_id)
        
        if not task_data:
            print(f"Task {task_id} not found")
            return
        
        print(f"=== Task Details: {task_id} ===")
        print(f"Status: {task_data.get('status', 'Unknown')}")
        print(f"Progress: {task_data.get('progress', 0)}%")
        print(f"Message: {task_data.get('message', 'No message')}")
        print(f"URL: {task_data.get('youtube_url', 'Unknown')}")
        print(f"Title: {task_data.get('title', 'Unknown')}")
        print(f"Channel: {task_data.get('channel', 'Unknown')}")
        
        created_at = task_data.get('created_at', 0)
        if created_at:
            created_time = datetime.fromtimestamp(created_at)
            print(f"Created: {created_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if task_data.get('status') == 'failed':
            print(f"Error: {task_data.get('error', 'Unknown error')}")
        
        if task_data.get('file_path'):
            print(f"File: {task_data.get('file_path')}")
        
    except Exception as e:
        print(f"Error getting task details: {str(e)}")

def continuous_monitor():
    """Continuously monitor queues"""
    print("Starting continuous monitoring (Ctrl+C to stop)...")
    
    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            monitor_queues()
            print("\nRefreshing in 5 seconds...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description="Celery monitoring utilities")
    parser.add_argument('command', choices=[
        'monitor', 'purge', 'restart', 'watch', 'task'
    ], help='Command to execute')
    parser.add_argument('--task-id', help='Task ID for task command')
    
    args = parser.parse_args()
    
    if args.command == 'monitor':
        monitor_queues()
    elif args.command == 'purge':
        purge_queues()
    elif args.command == 'restart':
        restart_workers()
    elif args.command == 'watch':
        continuous_monitor()
    elif args.command == 'task':
        if not args.task_id:
            print("--task-id required for task command")
            sys.exit(1)
        show_task_details(args.task_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
