# Railway Deployment Fix - Dockerfile Without External Scripts

## Problem

Railway build was failing with error:
```
ERROR: "/start.sh": not found
```

**Root Cause**: The `start.sh` file and other new files were not being pushed to the GitHub repository that Railway monitors, due to Emergent's Git sync issues.

## Solution

**Removed dependency on external files** by embedding the startup command directly in the Dockerfile.

## Changes Made

### 1. Updated Dockerfile

**Removed:**
- `COPY start.sh /app/start.sh` 
- `RUN chmod +x /app/start.sh`
- `ENTRYPOINT ["/bin/bash", "/app/start.sh"]`

**Added:**
- `ENV PORT=8001` - Default port with Railway override capability
- `WORKDIR /app/backend` - Change to backend directory
- Direct `CMD` with Gunicorn command embedded

**New CMD:**
```dockerfile
CMD gunicorn server:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --timeout 300 \
    --keep-alive 75 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

### 2. Simplified railway.json

**Removed:**
- `"startCommand": "/app/start.sh"` (no longer needed)

Now relies entirely on Dockerfile CMD.

## How This Works

1. **Dockerfile builds** with all Python dependencies
2. **WORKDIR changes** to `/app/backend` where `server.py` is located
3. **Gunicorn starts directly** with the embedded command
4. **PORT environment variable** allows Railway to inject its port dynamically
5. **No external files needed** - everything is self-contained

## Key Advantages

✅ **No external file dependencies** - everything in Dockerfile
✅ **Railway PORT override works** - uses `${PORT}` variable
✅ **Self-contained build** - doesn't rely on files that might not sync
✅ **Standard Docker pattern** - uses CMD as intended

## Files Modified

1. `/app/Dockerfile` - Embedded startup command, removed start.sh dependency
2. `/app/railway.json` - Removed startCommand reference

## Files No Longer Needed (But Kept for Reference)

- `/app/start.sh` - Logic moved to Dockerfile
- `/app/railway.toml` - Not needed, using railway.json
- `/app/Procfile` - Not needed, Dockerfile CMD is sufficient
- `/app/nixpacks.toml` - Not needed with explicit Dockerfile

## Next Steps

1. **Push these changes** to GitHub (Dockerfile and railway.json)
2. **Railway will auto-deploy** using the Dockerfile
3. **Should now work** without the "file not found" error

## Expected Success

After pushing and deploying, Railway logs should show:
```
=========================
Using Detected Dockerfile
=========================
[build steps]
[INFO] Starting gunicorn 22.0.0
[INFO] Listening at: http://0.0.0.0:[PORT]
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Started server process [PID]
🚀 Pre-loading RAG service...
✅ RAG service pre-loaded successfully
🌐 CORS configured...
```

## Troubleshooting

If it still fails:
1. Verify `backend/requirements.txt` contains `gunicorn` and `uvicorn`
2. Check Railway environment variables (especially if PORT is overridden)
3. Ensure `backend/server.py` exists and has the FastAPI `app` object
4. Check Railway logs for specific error messages
