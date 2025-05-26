# Celery Integration - Step 9

This document explains the Celery integration implemented in Step 9 of the YouTube to MP3 converter project.

## Overview

Celery has been integrated to replace the basic queue system with a proper distributed task queue. This allows for:

- Better task management and monitoring
- Scalable worker processes
- Fault tolerance and retries
- Progress tracking
- Task chaining for complex workflows

## Architecture

### Task Flow
1. **API Request** → FastAPI receives download request
2. **Task Creation** → Celery task is queued for processing
3. **Download Task** → Worker downloads audio using yt-dlp
4. **Conversion Task** → Automatically chained conversion to MP3
5. **Cleanup Task** → Removes temporary files after conversion

### Queues
- `download` - Handles YouTube video downloads
- `conversion` - Handles audio format conversion
- `cleanup` - Handles file cleanup tasks

## Files Structure

```
backend/
├── shared/
│   └── celery_app.py          # Celery configuration
├── download_service/
│   └── worker.py              # Download tasks
├── conversion_service/
│   └── worker.py              # Conversion tasks
├── file_service/
│   └── cleanup.py             # Cleanup tasks (updated)
├── celery_worker.py           # Single worker startup
├── start_workers.py           # Multi-worker startup
├── celery_monitor.py          # Monitoring utilities
└── run_server.py              # Updated server startup
```

## Installation

Celery is already added to `requirements.txt`. Install it with:

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Application

#### Option 1: Start everything together
```bash
python run_server.py
```

This starts both the FastAPI server and Celery workers.

#### Option 2: Start components separately
```bash
# Terminal 1: Start API server only
python run_server.py --api-only

# Terminal 2: Start Celery workers
python celery_worker.py
```

#### Option 3: Start specialized workers
```bash
# Start workers for different queues with different concurrency
python start_workers.py
```

### Monitoring

#### Monitor queue status
```bash
python celery_monitor.py monitor
```

#### Watch queues continuously
```bash
python celery_monitor.py watch
```

#### Check specific task
```bash
python celery_monitor.py task --task-id task-12345678
```

#### Purge all queues
```bash
python celery_monitor.py purge
```

#### Restart workers
```bash
python celery_monitor.py restart
```

## Task Types

### Download Task
- **Queue**: `download`
- **Function**: `download_service.worker.download_audio_task`
- **Purpose**: Downloads audio from YouTube using yt-dlp
- **Progress**: Updates Redis and Celery state with download progress
- **Chains to**: Conversion task

### Conversion Task
- **Queue**: `conversion`
- **Function**: `conversion_service.worker.convert_to_mp3_task`
- **Purpose**: Converts downloaded audio to MP3 format
- **Progress**: Updates task status during conversion
- **Chains to**: Cleanup task

### Cleanup Task
- **Queue**: `cleanup`
- **Function**: `file_service.cleanup.cleanup_task`
- **Purpose**: Removes temporary files after processing

## Configuration

### Celery Settings
The Celery app is configured in `shared/celery_app.py` with:

- **Broker**: Redis
- **Backend**: Redis
- **Serializer**: JSON
- **Time limits**: 30 minutes per task
- **Queues**: Separate queues for different task types

### Environment Variables
```bash
REDIS_URL=redis://localhost:6379
TEMP_DIR=/tmp/yt-mp3
STORAGE_DIR=/tmp/yt-mp3/output
```

## Progress Tracking

### Enhanced Progress Updates
- Download progress: 10% - 50% of total
- Conversion progress: 60% - 90% of total
- Completion: 100%

### Real-time Updates
- Redis stores task state for frontend polling
- Celery provides additional task metadata
- Progress includes speed, ETA, and detailed messages

## Scaling

### Worker Scaling
```bash
# Start more download workers
celery -A shared.celery_app worker --queues=download --concurrency=4

# Start more conversion workers  
celery -A shared.celery_app worker --queues=conversion --concurrency=2

# Start cleanup workers
celery -A shared.celery_app worker --queues=cleanup --concurrency=1
```

### Queue Management
Different task types can be scaled independently:
- Downloads: I/O intensive, can handle more concurrency
- Conversions: CPU intensive, limited by CPU cores
- Cleanup: Lightweight, minimal resources needed

## Error Handling

### Task Retries
Tasks automatically retry on failure with exponential backoff.

### Dead Letter Queue
Failed tasks are logged and can be inspected for debugging.

### Graceful Degradation
If Celery workers are not running, tasks are queued and will be processed when workers come online.

## Development vs Production

### Development
- Single worker process handling all queues
- Auto-reload enabled
- Detailed logging

### Production
- Separate worker processes for each queue type
- Process supervision (systemd, supervisor)
- Log aggregation
- Monitoring and alerting

## Troubleshooting

### Common Issues

#### Redis Connection Failed
```bash
# Start Redis
redis-server

# Check Redis is running
redis-cli ping
```

#### Workers Not Processing Tasks
```bash
# Check worker status
python celery_monitor.py monitor

# Check queue lengths
python celery_monitor.py watch
```

#### High Memory Usage
- Limit worker concurrency
- Enable task cleanup
- Monitor temp directory usage

### Logs
Workers log to stdout/stderr. In production, configure proper log management.

## Next Steps

With Celery integration complete, the application now has:
- ✅ Proper distributed task processing
- ✅ Progress tracking and monitoring
- ✅ Scalable worker architecture
- ✅ Task chaining and error handling

Ready for Step 10: Enhanced UI & Error Handling improvements.
