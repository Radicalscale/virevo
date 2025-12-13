#!/bin/bash
set -e

# Debug: Print script execution
echo "========================================="
echo "🚀 START.SH SCRIPT IS EXECUTING"
echo "========================================="

# Change to backend directory where server.py is located
cd /app/backend

# Use Railway's PORT if provided, otherwise default to 8001
PORT=${PORT:-8001}

echo "📍 Working directory: $(pwd)"
echo "🔍 Python path: $PYTHONPATH"
echo "🌐 Starting Gunicorn on 0.0.0.0:${PORT}..."
echo "========================================="

exec gunicorn server:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind "0.0.0.0:${PORT}" \
     --timeout 300 \
     --keep-alive 75 \
     --access-logfile - \
     --error-logfile - \
     --log-level info
