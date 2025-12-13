# JWT_SECRET and Environment Variables Setup

## Problem

Getting 401 Unauthorized errors after logging in successfully. This happens when `JWT_SECRET_KEY` is missing or different between environments.

## Root Cause

The backend code looks for `JWT_SECRET_KEY` (not `JWT_SECRET`) in environment variables:
- `auth_utils.py` uses it to sign/verify JWT tokens
- `key_encryption.py` uses it for API key encryption

When missing, it falls back to default values, which are different on each restart.

## Solution

### 1. Local Environment (/app/backend/.env)

Added these lines to `/app/backend/.env`:

```env
# Authentication & Encryption Keys
JWT_SECRET_KEY="andromeda-jwt-secret-key-2024-production-secure"
ENCRYPTION_KEY="andromeda-encryption-key-2024-production-secure-32bytes"
```

### 2. Railway Environment

**CRITICAL:** You must add these SAME values to Railway:

1. Go to your Railway project dashboard
2. Click on your backend service
3. Go to **Variables** tab
4. Add these variables:

```
JWT_SECRET_KEY=andromeda-jwt-secret-key-2024-production-secure
ENCRYPTION_KEY=andromeda-encryption-key-2024-production-secure-32bytes
```

5. **Redeploy** Railway service

### 3. Netlify Frontend (if using environment variables)

Frontend doesn't need JWT_SECRET_KEY (backend only).

## Why This Matters

### JWT_SECRET_KEY
- Used to **sign** JWT tokens when you log in
- Used to **verify** JWT tokens on protected API calls
- **Must be the same** across all backend instances
- If different: login works but all other API calls get 401

### ENCRYPTION_KEY
- Used to encrypt API keys in database
- Must be consistent to decrypt existing keys
- If changed: existing encrypted keys become unusable

## Current Setup

### Local (Emergent)
✅ JWT_SECRET_KEY set in `/app/backend/.env`
✅ Backend restarted with new key

### Railway (Production)
❌ **NEEDS TO BE SET** - Add JWT_SECRET_KEY to Railway Variables
❌ **NEEDS REDEPLOY** after adding variable

## Testing After Fix

1. **Clear your browser cookies** (important!)
2. Go to https://li-ai.org/login
3. Log in with kendrickbowman9@gmail.com
4. Try accessing:
   - Dashboard
   - Agents page
   - Test Caller
   - Saving agent updates

All should work without 401 errors.

## If Still Getting 401 Errors

### Check 1: Cookie Settings
The backend sends JWT in httpOnly cookies. Check in browser DevTools:
- Application > Cookies > https://api.li-ai.org
- Should see a cookie named `access_token`

### Check 2: CORS Settings
Verify in Railway logs that CORS shows your frontend URL:
```
🌐 CORS configured for origins: ['https://li-ai.org', 'https://www.li-ai.org', ...]
```

### Check 3: JWT Token Format
In browser console, check network request headers:
```
Cookie: access_token=<jwt-token>
```

## Complete Environment Variables List

### Required for Authentication
- `JWT_SECRET_KEY` - For signing/verifying JWT tokens
- `ENCRYPTION_KEY` - For encrypting API keys
- `MONGO_URL` - Database connection
- `BACKEND_URL` - Backend URL for CORS and webhooks

### Required for AI Features  
- `OPENAI_API_KEY` - OpenAI GPT models
- `ELEVEN_API_KEY` - ElevenLabs TTS
- `GROK_API_KEY` - Grok LLM (optional)
- `SONIOX_API_KEY` - Speech-to-text

### Required for Calling Features
- `TELNYX_API_KEY` - Phone service
- `TELNYX_CONNECTION_ID` - Telnyx connection

### Optional
- `DEEPGRAM_API_KEY` - Alternative STT
- `HUME_API_KEY` - Emotion detection
- `ASSEMBLYAI_API_KEY` - Alternative STT
- `CHATTTS_API_URL` - ChatTTS server
- `ENABLE_RAG` - Enable RAG features (true/false)

## Security Best Practices

1. **Use strong, random secrets** in production
2. **Never commit secrets** to Git
3. **Use different secrets** for different environments
4. **Rotate secrets periodically**
5. **Set secrets via Railway UI**, not in code

## Generate New Secrets (if needed)

In Python:
```python
import secrets
print(f"JWT_SECRET_KEY={secrets.token_urlsafe(32)}")
print(f"ENCRYPTION_KEY={secrets.token_urlsafe(32)}")
```

Or in bash:
```bash
openssl rand -base64 32
```
