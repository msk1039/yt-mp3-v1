FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp globally
RUN pip install --no-cache-dir yt-dlp

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user first with specific UID
RUN useradd --create-home --shell /bin/bash --uid 1000 app

# Create necessary directories as root first
RUN mkdir -p /app/temp /app/downloads /app/logs

# Change ownership of directories to app user
RUN chown -R app:app /app

# Copy application code
COPY . .

# Ensure app user owns all files
RUN chown -R app:app /app

# Make start script executable
RUN chmod +x /app/start.sh

# Switch to non-root user AFTER setting up directories and permissions
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/start.sh"]