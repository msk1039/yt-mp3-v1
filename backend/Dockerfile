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

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/temp /app/downloads /app/logs && \
    chmod 777 /app/temp /app/downloads /app/logs

# Create non-root user for security with specific UID
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app && \
    chmod -R 755 /app

USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use a startup script instead of running commands directly
COPY --chown=app:app start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]