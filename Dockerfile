# Multi-stage build for optimized image size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --default-timeout=1000 --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Install runtime dependencies including FFmpeg for comfort noise generation
RUN apt-get update && apt-get install -y \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set working directory
WORKDIR /app

# Force Rebuild Trigger (Update this to invalidate cache)
ENV REBUILD_TRIGGER_DATE=2025-12-28-MANUAL-FIX

# Copy backend code
COPY backend/ ./backend/

# Copy start script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Create data directory for ChromaDB
RUN mkdir -p /app/data/chromadb

# Make sure scripts are executable
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 8001

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV PORT=8001

# Change to backend directory and start Gunicorn directly
WORKDIR /app/backend

# Use 4 workers for scalability (Redis handles multi-worker state sharing)
# WEB_CONCURRENCY=4 allows Railway to scale efficiently
ENV WEB_CONCURRENCY=4

# Use CMD with shell form to support environment variable expansion
CMD gunicorn server:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8001} --timeout 300 --keep-alive 75 --access-logfile - --error-logfile - --log-level info
