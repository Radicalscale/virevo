# Railway 502 Error Fix - November 11, 2025

## Problem Diagnosis

The Railway deployment was failing with a 502 Bad Gateway error. Analysis of the deployment logs revealed:

1. ✅ FastAPI application startup events were executing successfully (RAG pre-loading, CORS config)
2. ❌ Gunicorn server process never started - no "Started server process" message in logs
3. ❌ Logs stopped abruptly after startup events completed

## Root Cause

The Dockerfile CMD was using an incorrect module path for Gunicorn:

```dockerfile
# ❌ INCORRECT - This was failing
CMD ["gunicorn", "backend.server:app", ...]
```

Since `PYTHONPATH` was set to `/app/backend`, the correct module path should be just `server:app`, not `backend.server:app`.

## Solution Applied

### 1. Fixed Module Path in Gunicorn Command

Changed from `backend.server:app` to `server:app` to match the PYTHONPATH configuration.

### 2. Created Dynamic Startup Script

Created `/app/start.sh` to handle Railway's PORT environment variable dynamically:

```bash
#!/bin/bash

# Use Railway's PORT if provided, otherwise default to 8001
PORT=${PORT:-8001}

echo "Starting Gunicorn on 0.0.0.0:${PORT}..."

exec gunicorn server:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind "0.0.0.0:${PORT}" \
     --timeout 300 \
     --keep-alive 75 \
     --access-logfile - \
     --error-logfile - \
     --log-level info
```

### 3. Updated Dockerfile

**Key changes:**
- Copy and make `start.sh` executable
- Use `CMD ["/app/start.sh"]` instead of inline Gunicorn command
- This allows the app to bind to Railway's dynamic PORT if provided

### 4. Fixed Railway Auto-Detection Override (CRITICAL)

**Problem:** Railway was auto-detecting the Python app and ignoring the Dockerfile CMD, which is why the startup script wasn't running.

**Solution:** Added explicit `startCommand` to `railway.json`:

```json
{
  "deploy": {
    "startCommand": "/app/start.sh"
  }
}
```

Also created `/app/Procfile` as a backup:
```
web: /app/start.sh
```

This forces Railway to use our startup script instead of auto-detecting the Python app.

## Files Modified

1. `/app/Dockerfile` - Fixed CMD and added startup script
2. `/app/start.sh` - New file for dynamic port handling
3. `/app/railway.json` - Added explicit `startCommand` to override auto-detection
4. `/app/Procfile` - Added as backup for Railway startup

## Testing Recommendations

After redeploying to Railway:

1. Check logs for the message: `Starting Gunicorn on 0.0.0.0:[PORT]...`
2. Verify you see: `Started server process` from Gunicorn
3. Confirm the service responds to health checks
4. Test a complete API call flow

## Expected Log Output

After this fix, you should see logs like:

```
Starting Gunicorn on 0.0.0.0:8001...
[INFO] Starting gunicorn 22.0.0
[INFO] Listening at: http://0.0.0.0:8001
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [PID]
[INFO] Started server process [PID]
[INFO] Waiting for application startup.
🚀 Pre-loading RAG service and KB router to avoid cold start...
[RAG loading logs...]
✅ RAG service pre-loaded successfully
🌐 CORS configured for origins: [...]
[INFO] Application startup complete.
```

## Next Steps

1. Commit these changes to your repository
2. Push to Railway (it will auto-deploy)
3. Monitor the deployment logs
4. Test the deployed backend API endpoints

## Prevention

For future Docker deployments:
- Always ensure module paths match PYTHONPATH configuration
- Use dynamic PORT handling for cloud platforms
- Test Docker builds locally before deploying
- Check logs immediately after deployment for startup confirmation
