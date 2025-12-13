# Railway Configuration Fix - Deploy Crash Resolution

## Problem
Build succeeded but deploy crashed with:
```
/bin/bash: line 1: /app/start.sh: No such file or directory
```

## Root Cause
Railway was reading configuration from **multiple config files** that were overriding the Dockerfile's ENTRYPOINT:
- `railway.toml` had `startCommand = "/app/start.sh"`
- `nixpacks.toml` had `cmd = "/app/start.sh"`
- `Procfile` had `web: /app/start.sh`

These were all trying to execute `/app/start.sh` **after** the container was built, but Railway's config precedence was causing conflicts.

## Solution
**Disabled all start commands** in config files to let the Dockerfile's ENTRYPOINT handle the startup:

### Files Modified:

1. **`railway.toml`** - Removed `startCommand`
2. **`nixpacks.toml`** - Commented out `[start]` section
3. **`Procfile`** - Commented out `web:` command

The Dockerfile's ENTRYPOINT is now the single source of truth for how to start the application.

## What Railway Will Use Now:

```dockerfile
ENTRYPOINT ["sh", "-c", "gunicorn server:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8001} --timeout 300 --keep-alive 75 --access-logfile - --error-logfile - --log-level info"]
```

## Next Steps:

1. **Push these changes** to your GitHub repository
2. **Railway will auto-redeploy**
3. The container should now start successfully using the Dockerfile's ENTRYPOINT
4. **Monitor the logs** to ensure gunicorn starts correctly

## Expected Startup Logs:

You should see:
```
[INFO] Starting gunicorn 22.0.0
[INFO] Listening at: http://0.0.0.0:8001
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [PID]
[INFO] Application startup complete.
```

## Important Railway Settings to Verify:

In your Railway dashboard:
- **Builder:** Should be set to `DOCKERFILE`
- **Start Command:** Should be **EMPTY** (let Dockerfile handle it)
- **Root Directory:** Should be `.` or empty

## If Deploy Still Fails:

1. **Check Railway Dashboard:**
   - Go to Settings → Build & Deploy
   - Verify "Start Command" override is **EMPTY**
   - If it has a value, delete it and save

2. **Check Environment Variables:**
   - Ensure `PORT` variable is NOT hardcoded (Railway sets it automatically)
   - Verify `REDIS_URL` is set correctly

3. **Check Logs:**
   - Look for any Python import errors
   - Verify all dependencies are installed correctly
