# Railway Deployment Fix Summary

## Issues Fixed

### 1. Missing `start.sh` File in Docker Container
**Problem:** Railway was trying to execute `/app/start.sh` but the file wasn't copied into the Docker container during build.

**Root Cause:** The Dockerfile only copied the `backend/` directory but not the `start.sh` script.

**Fix:** Updated Dockerfile to copy `start.sh` and make it executable:
```dockerfile
# Copy start script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh
```

### 2. Deprecated `audioop` Module Error
**Problem:** Python's `audioop` module was deprecated in 3.11 and removed in 3.13, causing `ModuleNotFoundError` for recording features.

**Root Cause:** `audio_resampler.py` was importing and using `audioop.ulaw2lin()` for μ-law to PCM conversion.

**Fix:** Replaced `audioop` with a pure Python/NumPy implementation of μ-law decompression algorithm.

## Files Modified

1. **`/app/Dockerfile`**
   - Added lines to copy and make `start.sh` executable

2. **`/app/backend/audio_resampler.py`**
   - Removed `audioop` import
   - Implemented pure Python μ-law to linear PCM conversion using NumPy

## Deployment Steps for Railway

### Fresh Deployment to New Railway Project:

1. **Create Railway Project:**
   - Go to Railway dashboard
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Add Redis Service:**
   - In your project, click "New" → "Database" → "Add Redis"
   - Copy the internal Redis URL (format: `redis://default:password@redis.railway.internal:6379`)

3. **Configure Backend Service:**
   - Click on your backend service
   - Go to "Settings" tab:
     - Set "Root Directory" to `.` (leave empty or set to root)
     - Set "Builder" to `DOCKERFILE`

4. **Set Environment Variables:**
   
   **Critical Variables:**
   ```
   REDIS_URL=redis://default:password@redis.railway.internal:6379
   MONGO_URL=<your-mongodb-connection-string>
   JWT_SECRET_KEY=<generate-random-secret>
   ENCRYPTION_KEY=<32-byte-base64-key>
   ```

   **Core Variables:**
   ```
   CORS_ORIGINS=https://your-frontend-url.netlify.app
   SONIOX_API_KEY=<if-using-soniox>
   TELNYX_API_KEY=<if-using-telnyx>
   ```

5. **Deploy:**
   - Railway will automatically build and deploy
   - Check logs for successful startup
   - Get your backend public URL

6. **Configure Frontend:**
   - Deploy frontend to Netlify
   - Set `REACT_APP_BACKEND_URL` to your Railway backend URL

7. **Update CORS:**
   - Go back to Railway
   - Update `CORS_ORIGINS` with your Netlify URL
   - Redeploy if needed

8. **Configure Telnyx Webhook:**
   - Go to Telnyx dashboard
   - Set webhook URL to: `https://your-backend.railway.app/api/webhook/telnyx`

9. **Verify Deployment:**
   ```bash
   # Check health endpoint
   curl https://your-backend.railway.app/api/health
   
   # Should return: {"status": "healthy"}
   ```

10. **Test Call:**
    - Make a test call to verify all features work
    - Monitor Railway logs for any errors

## What's Working Now:

✅ Multi-worker deployment with 4 Gunicorn workers
✅ Redis-based state management across workers
✅ μ-law audio recording/conversion (no more audioop errors)
✅ WebSocket and webhook handlers coordinated properly
✅ Session creation without race conditions

## If You Encounter Issues:

1. **Check Redis Connection:**
   - Ensure `REDIS_URL` uses the internal Railway URL
   - Format: `redis://default:password@redis.railway.internal:6379`

2. **Check Logs:**
   - Go to Railway dashboard → Your service → Logs tab
   - Look for startup messages and any errors

3. **Environment Variables:**
   - Verify all critical variables are set correctly
   - Use Railway's dashboard to manage env vars

4. **Build Issues:**
   - Ensure `railway.json` has `"builder": "DOCKERFILE"`
   - Check that Dockerfile builds successfully locally

## Need Help?

If deployment still fails:
1. Share the exact error message from Railway logs
2. Verify all environment variables are set
3. Check if Redis service is running in your Railway project
