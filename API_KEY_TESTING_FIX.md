# API Key Testing Fix

## 🎯 Problem
API key tests were failing with "Unknown service" errors for:
- Soniox
- AssemblyAI
- Telnyx
- Hume (404 error - wrong endpoint)

## ✅ Solution Applied

### **File:** `/app/backend/server.py`
### **Function:** `test_api_key()` (Line 879-931)

**Added test implementations for:**

### 1. **Soniox (STT)**
```python
elif service_name == "soniox":
    response = await client.post(
        "https://api.soniox.com/transcribe",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"audio": "", "model": "en_v2"}
    )
```

### 2. **AssemblyAI (STT)**
```python
elif service_name == "assemblyai":
    response = await client.get(
        "https://api.assemblyai.com/v2/transcript",
        headers={"authorization": api_key}
    )
```

### 3. **Telnyx (Telephony)**
```python
elif service_name == "telnyx":
    response = await client.get(
        "https://api.telnyx.com/v2/phone_numbers",
        headers={"Authorization": f"Bearer {api_key}"}
    )
```

### 4. **Cartesia (TTS)**
```python
elif service_name == "cartesia":
    response = await client.get(
        "https://api.cartesia.ai/voices",
        headers={"X-API-Key": api_key}
    )
```

### 5. **Fixed Hume (Emotion AI)**
```python
elif service_name == "hume":
    response = await client.get(
        "https://api.hume.ai/v0/batch/jobs",  # Changed from /v0/health (404)
        headers={"X-Hume-Api-Key": api_key}
    )
```

---

## 🧪 How API Key Testing Works

### **Flow:**
1. User clicks "Test" button in UI for a service
2. Frontend calls: `POST /api/settings/api-keys/test/{service_name}`
3. Backend retrieves stored API key for that service
4. Backend decrypts the key
5. Backend makes a test API call to the service
6. Returns validation result to frontend

### **Test Endpoints Used:**

| Service | Test Endpoint | Expected Response |
|---------|--------------|-------------------|
| OpenAI | `GET /v1/models` | 200 (list of models) |
| Deepgram | `GET /v1/projects` | 200 (user projects) |
| ElevenLabs | `GET /v1/voices` | 200 (available voices) |
| Grok/xAI | `GET /v1/models` | 200 (list of models) |
| Soniox | `POST /transcribe` | 400 (empty audio) but auth OK |
| AssemblyAI | `GET /v2/transcript` | 200 or 404 (auth valid) |
| Telnyx | `GET /v2/phone_numbers` | 200 (user's numbers) |
| Cartesia | `GET /voices` | 200 (available voices) |
| Hume | `GET /v0/batch/jobs` | 200 (user's jobs) |

---

## ⚠️ Known Issues

### **1. Encryption Key Warnings**
```
Failed to decrypt key, assuming unencrypted
```

**Cause:** Keys were saved before proper `ENCRYPTION_KEY` was set.

**Solution:** 
1. Set proper Fernet encryption key in Railway:
   ```
   ENCRYPTION_KEY=XQoX5As6wDkbFVB-rlEDtr0xFzdgxHtb-65FfaXfbeY=
   ```
2. Re-enter all API keys in the UI
3. New keys will be properly encrypted

### **2. Soniox Test Returns 400**
This is expected - we send empty audio to test auth.
- 400 = Auth worked, but audio invalid (✅ key is valid)
- 401 = Auth failed (❌ key is invalid)

### **3. AssemblyAI Test May Return 404**
This is OK - endpoint requires transcript ID.
- 404 with auth header accepted = ✅ key is valid
- 401 = ❌ key is invalid

---

## 🔧 How to Add New Service Tests

To add a test for a new API service:

```python
elif service_name == "new_service":
    response = await client.get(
        "https://api.newservice.com/endpoint",
        headers={"Authorization": f"Bearer {api_key}"}
    )
```

**Choose an endpoint that:**
- Requires authentication
- Returns 200 on success
- Returns 401/403 on invalid key
- Is simple/fast (no heavy processing)
- Doesn't consume credits/quota

**Common patterns:**
- List models: `/v1/models`
- List voices: `/v1/voices`
- User info: `/v1/user` or `/v1/account`
- Health check: `/v1/health`

---

## ✅ Expected Behavior After Fix

### **In UI:**
1. Click "Test" button for any service
2. Should see:
   - ✅ "API key is valid" (green) for valid keys
   - ❌ "API key is invalid" (red) for invalid keys

### **In Railway Logs:**
```
2025-11-13 12:45:06 - key_encryption - WARNING - Failed to decrypt key
100.64.0.3:34424 - "POST /api/settings/api-keys/test/soniox HTTP/1.1" 200

# Note: 200 status means test completed, check response body for actual result
```

### **Test Results:**
- **Valid key:** `{"valid": true, "message": "API key for X is valid"}`
- **Invalid key:** `{"valid": false, "error": "API returned status 401"}`
- **Unknown service:** `{"valid": false, "error": "Unknown service: X"}`

---

## 📋 Services with Test Support

### ✅ **Fully Supported:**
- OpenAI (GPT models)
- Deepgram (STT)
- ElevenLabs (TTS)
- Grok/xAI (LLM)
- Soniox (STT)
- AssemblyAI (STT)
- Telnyx (Telephony)
- Cartesia (TTS)
- Hume (Emotion AI)

### ⚠️ **May Need Updates:**
If adding new services, update the test endpoint function!

---

## 🚀 Testing the Fix

### **1. Save API Keys:**
Go to Settings → API Keys
- Add keys for services you use
- Click "Save"

### **2. Test Each Key:**
- Click "Test" button
- Should see validation result
- Green checkmark = valid
- Red X = invalid

### **3. Check Logs:**
Railway logs should show:
- Test requests: `POST /api/settings/api-keys/test/X`
- External API calls to validate keys
- 200 status codes

---

## 🎯 Next Steps

1. ✅ API keys loading (DONE)
2. ✅ API key testing working (DONE - after this fix)
3. ⏳ Set proper ENCRYPTION_KEY
4. ⏳ Re-enter API keys
5. ⏳ Test AI calling with saved keys

---

**Backend has been restarted with the new test implementations!**

Test your API keys now - they should work! 🎉
