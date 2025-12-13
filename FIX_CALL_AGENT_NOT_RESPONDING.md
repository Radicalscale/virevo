# Fix: AI Agent Not Responding During Calls

## 🔍 Root Causes Identified

### 1. Invalid ENCRYPTION_KEY
**Error in logs:**
```
Failed to decrypt key, assuming unencrypted: Fernet key must be 32 url-safe base64-encoded bytes.
```

**Problem:** Your ENCRYPTION_KEY is not in the correct Fernet format. This causes API key decryption to fail.

**Impact:** Agent's Soniox API key (and other keys) can't be decrypted properly.

### 2. Telnyx Webhook Not Configured
**Missing in logs:** No `call.answered` webhook received after call connects.

**Problem:** Telnyx doesn't know where to send webhook events.

**Impact:** Backend never knows the call was answered, so it never creates the AI session.

### 3. Call Flow Breakdown
```
Call Initiated ✅
    ↓
Call Connects ✅
    ↓
Telnyx Webhook (call.answered) ❌ <- BREAKS HERE
    ↓
Backend Creates AI Session ❌
    ↓
WebSocket Connection ❌
    ↓
Soniox STT Initialization ❌
    ↓
AI Responds to Speech ❌
```

---

## 🔧 Fixes (In Order)

### Fix 1: Generate Proper ENCRYPTION_KEY (2 min)

#### Step 1: Generate the key
Run this command locally or in Railway shell:
```bash
python3 << 'EOF'
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
EOF
```

**Output example:**
```
mJ7XzP9kL3nQ8wR2vT5yU6iO0pA1sD4fG7hJ9kL2mN5qR8tU0vW3xY6zA9bC2eF5
```

#### Step 2: Update Railway Environment Variable
```
Railway → Backend service → Variables
Find: ENCRYPTION_KEY
Update with the generated key (44 characters, alphanumeric)
Save
```

Backend will auto-redeploy (30 seconds).

---

### Fix 2: Configure Telnyx Webhook (5 min)

#### Step 1: Get Your Backend Webhook URL
```
Format: https://your-backend-url.up.railway.app/api/webhook/telnyx
OR: https://api.li-ai.org/api/webhook/telnyx (if custom domain set up)
```

#### Step 2: Set Webhook in Telnyx Portal

1. Go to [Telnyx Portal](https://portal.telnyx.com/)
2. Navigate to **"Messaging" → "TeXML Applications"** OR **"Voice" → "Connections"**
3. Find your connection/application
4. Look for **"Webhook URL"** or **"Status Callback URL"**
5. Set it to: `https://your-backend-url.up.railway.app/api/webhook/telnyx`
6. **HTTP Method:** POST
7. **Failover URL:** (optional) same URL
8. Click **"Save"**

#### Alternative: Set Webhook via Telnyx API
```bash
curl -X PATCH \
  https://api.telnyx.com/v2/connections/YOUR_CONNECTION_ID \
  -H "Authorization: Bearer YOUR_TELNYX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_event_url": "https://your-backend-url.up.railway.app/api/webhook/telnyx",
    "webhook_event_failover_url": "",
    "webhook_timeout_secs": 25
  }'
```

---

### Fix 3: Re-encrypt Your API Keys (3 min)

After fixing ENCRYPTION_KEY, your existing API keys need to be re-encrypted.

#### Option A: Re-add Keys via UI
1. Go to your frontend: Settings → API Keys
2. Delete old keys
3. Re-add them (they'll be encrypted with the new key)

#### Option B: Migration Script (if you have many keys)

Create `/app/reencrypt_keys.py`:
```python
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from key_encryption import encrypt_api_key

async def reencrypt_all_keys():
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client.andromeda
    
    # Get all API keys
    keys = await db.api_keys.find({}).to_list(length=None)
    
    for key in keys:
        # Re-encrypt the key value
        if 'key_value' in key:
            encrypted = encrypt_api_key(key['key_value'])
            await db.api_keys.update_one(
                {'_id': key['_id']},
                {'$set': {'key_value': encrypted}}
            )
            print(f"✅ Re-encrypted key: {key.get('key_name', 'unknown')}")
    
    print(f"✅ Re-encrypted {len(keys)} keys")
    client.close()

if __name__ == '__main__':
    asyncio.run(reencrypt_all_keys())
```

Run it:
```bash
cd /app
python3 reencrypt_keys.py
```

---

## ✅ Testing the Full Call Flow

### Step 1: Verify Backend Setup
```bash
# Check health
curl https://your-backend-url.up.railway.app/api/health
# Expected: {"status":"healthy"}

# Check encryption (should not show warnings in logs anymore)
```

### Step 2: Test Webhook Reception

#### Make a test call and monitor Railway logs:
```
Railway → Backend service → Logs (expand)
```

#### You should see (in order):
```
✅ 📞 Outbound call initiated: v3:xxxxx
✅ 📦 Call data stored in Redis
✅ 🎯 Webhook received: call.answered for v3:xxxxx
✅ 🔧 Creating AI session for agent: [agent_name]
✅ 🎤 Initializing Soniox STT service
✅ 🔊 WebSocket connection established: v3:xxxxx
✅ 🎙️ Audio streaming started
✅ 📝 Transcription: [user speech]
✅ 🤖 AI Response: [agent response]
```

### Step 3: Test Agent Configuration Loading

Check logs for these indicators:

**Agent Config Loaded:**
```
🔧 Agent settings loaded: [agent_name]
📋 Agent prompt: [first 50 chars]
🧠 LLM: [provider/model]
🎤 STT: Soniox
🔊 TTS: [provider]
```

**Tools Loaded:**
```
🛠️ Agent tools: [list of enabled tools]
📚 Knowledge base: [enabled/disabled]
🎯 Goal: [agent goal if set]
⚡ Interruption: [enabled/disabled]
```

**Soniox Specific:**
```
🎤 Initializing Soniox STT service
🔑 Soniox API key loaded (decrypted)
🌐 Connecting to Soniox WebSocket
✅ Soniox STT ready
```

### Step 4: Test During Live Call

#### Frontend Console Logs:
Open browser DevTools → Console during call:

**You should see:**
```
✅ Call initiated
✅ Call status: ringing
✅ Call status: active
✅ Transcription: "Hello, is anyone there?"
✅ AI Response: "Hi! Yes, I'm here..."
```

#### Backend Logs (Real-time):
```
✅ Audio packet received (8000 Hz, mulaw)
✅ STT: Processing audio chunk
✅ Transcription: "Hello, is anyone there?"
✅ LLM: Generating response
✅ TTS: Synthesizing speech
✅ Sending audio to caller
```

---

## 🧪 Comprehensive Testing Checklist

### Test 1: Basic Call Flow
- [ ] Make outbound call
- [ ] Call connects (you hear ringing)
- [ ] Call answers
- [ ] Agent speaks greeting (if configured)
- [ ] You speak
- [ ] Agent responds appropriately
- [ ] Conversation flows naturally

### Test 2: STT Provider (Soniox)
- [ ] Agent configuration shows Soniox as STT
- [ ] Backend logs show Soniox initialization
- [ ] Your speech is transcribed (check logs)
- [ ] Transcription is accurate
- [ ] Low latency (< 1 second from speech to response)

### Test 3: Agent Tools
- [ ] If agent has knowledge base: Ask a KB question
- [ ] If agent has tools: Trigger a tool (e.g., "book an appointment")
- [ ] Check logs for tool invocation
- [ ] Verify tool executes correctly

### Test 4: Interruption Handling
- [ ] Agent starts speaking
- [ ] Interrupt the agent mid-sentence
- [ ] Agent stops and listens
- [ ] Agent responds to your interruption
- [ ] No audio overlap or echo

### Test 5: Multi-Agent Test
- [ ] Create 2+ agents with different configs
- [ ] Agent A: Deepgram STT + ElevenLabs TTS
- [ ] Agent B: Soniox STT + Cartesia TTS
- [ ] Call both agents
- [ ] Verify each uses their own settings
- [ ] No config bleeding between agents

### Test 6: Error Handling
- [ ] Try calling with invalid phone number
- [ ] Try calling without STT API key
- [ ] Try calling with invalid agent ID
- [ ] Verify proper error messages
- [ ] No backend crashes

---

## 🔍 Debug Mode: Verbose Logging

If issues persist, enable verbose logging:

### Railway Environment Variables:
```bash
LOG_LEVEL=DEBUG
ENABLE_CALL_LOGGING=true
```

This will show detailed logs:
```
🔍 DEBUG: Received audio packet (payload_length: 160 bytes)
🔍 DEBUG: Decoded mulaw to PCM (320 bytes)
🔍 DEBUG: Sent to Soniox STT
🔍 DEBUG: Soniox response: {"transcript": "hello", "is_final": true}
🔍 DEBUG: Sending to LLM...
🔍 DEBUG: LLM response received (tokens: 45)
🔍 DEBUG: Sending to TTS...
```

---

## 🆘 Still Not Working?

### Collect This Information:

1. **Railway Backend Logs (last 100 lines):**
   ```
   Railway → Backend → Logs → Copy all
   ```

2. **Frontend Console Logs:**
   ```
   Browser DevTools → Console → Copy all errors
   ```

3. **Agent Configuration:**
   ```
   Settings → Agents → [Your Agent] → Copy config
   ```

4. **Environment Variables (HIDE SENSITIVE VALUES):**
   ```
   BACKEND_URL=✅
   MONGO_URL=✅
   REDIS_URL=✅
   ENCRYPTION_KEY=✅ (first 10 chars only)
   TELNYX_API_KEY=✅ (first 10 chars only)
   SONIOX_API_KEY=✅ (first 10 chars only)
   CORS_ORIGINS=✅
   ```

5. **Telnyx Webhook Config:**
   ```
   Screenshot of webhook URL in Telnyx portal
   ```

---

## 📊 Expected Logs for Successful Call

### Complete Log Flow:
```
1. [INFO] 📞 Outbound call initiated: v3:xxxxx
2. [INFO] 📦 Call data stored in Redis
3. [INFO] 🎯 Webhook received: call.answered for v3:xxxxx
4. [INFO] 🔧 Loading agent configuration: [agent_id]
5. [INFO] 🔑 Decrypting API keys (Soniox, LLM, TTS)
6. [INFO] 🎤 Initializing Soniox STT service
7. [INFO] 🔊 Initializing TTS service: [provider]
8. [INFO] 🧠 Initializing LLM: [provider/model]
9. [INFO] 📚 Loading knowledge base (if enabled)
10. [INFO] 🛠️ Loading agent tools: [list]
11. [INFO] 🔗 WebSocket connection established
12. [INFO] 🎙️ Audio streaming started (8000 Hz, mulaw)
13. [INFO] 📝 Transcription received: "Hello"
14. [INFO] 🤖 AI processing response...
15. [INFO] 🔊 TTS generated, streaming to caller
16. [INFO] ✅ Audio sent successfully
```

---

## 🎯 Quick Fix Summary

1. **Generate proper ENCRYPTION_KEY** (Fernet format)
2. **Add to Railway environment variables**
3. **Configure Telnyx webhook URL** (point to your BACKEND_URL/api/webhook/telnyx)
4. **Re-encrypt API keys** (via UI or script)
5. **Test call** and monitor logs

**After these fixes, your AI agent should respond properly with full tool, KB, and interruption support!** 🚀
