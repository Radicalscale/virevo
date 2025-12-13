# IMMEDIATE FIX: Get Calls Working

## 🚨 Problem
Call connects but AI doesn't respond to your speech.

## 🔍 What's Happening
```
✅ Call initiated
✅ Telnyx dials number
✅ You answer
❌ No webhook received by backend
❌ AI session never created
❌ Soniox never initialized
❌ No transcription
❌ No AI response
```

## ✅ Required Fixes (15 minutes)

### **Fix 1: Set ENCRYPTION_KEY (5 min)**

**Why:** Keys can't be decrypted properly (logs show warnings)

**How:**
1. Go to Railway Dashboard
2. Your backend service → **Variables**
3. Add or update:
   ```
   ENCRYPTION_KEY=XQoX5As6wDkbFVB-rlEDtr0xFzdgxHtb-65FfaXfbeY=
   ```
4. Click **Save**
5. Wait 30 seconds for redeploy

---

### **Fix 2: Configure Telnyx Webhook (10 min)** ⚠️ CRITICAL

**Why:** Backend never receives `call.answered` event

**Your webhook URL:**
```
https://api.li-ai.org/api/webhook/telnyx
```

**Steps:**

#### Option A: Via Telnyx Portal (Easiest)

1. **Go to:** https://portal.telnyx.com/
2. **Navigate to:** Call Control → Applications
3. **Find your application** (or create one if needed)
4. **Set "Webhook URL":**
   ```
   https://api.li-ai.org/api/webhook/telnyx
   ```
5. **HTTP Method:** POST
6. **Click:** Save

#### Option B: Via Connection Settings

1. **Go to:** https://portal.telnyx.com/
2. **Navigate to:** Numbers → Connections
3. **Click your connection** (should be ID: 2777245537294877821 from logs)
4. **Settings tab**
5. **Webhook URL:**
   ```
   https://api.li-ai.org/api/webhook/telnyx
   ```
6. **Save**

#### Option C: Via API (Advanced)

```bash
curl -X PATCH \
  https://api.telnyx.com/v2/connections/2777245537294877821 \
  -H "Authorization: Bearer YOUR_TELNYX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_event_url": "https://api.li-ai.org/api/webhook/telnyx",
    "webhook_timeout_secs": 25
  }'
```

---

### **Fix 3: Re-enter API Keys (Optional but Recommended)**

**After setting ENCRYPTION_KEY:**

1. Go to https://li-ai.org/settings
2. Delete and re-enter:
   - Soniox API key
   - Telnyx API key
   - Any other keys you're using
3. Test each key
4. Should now be properly encrypted

---

## 🧪 Test After Fixes

### **1. Check Railway Logs**

Look for these after fixes:
```
✅ 🎯 Webhook received: call.answered for v3:xxxxx
✅ 🔧 Creating AI session for agent: [agent_name]
✅ 🎤 Initializing Soniox STT service
✅ 🔗 WebSocket connection established
✅ 🎙️ Audio streaming started
✅ 📝 Transcription: [your speech]
✅ 🤖 AI Response: [agent response]
```

### **2. Make Test Call**

1. Go to Dashboard
2. Select agent with Soniox STT
3. Click "Call" button
4. Answer phone
5. Say "Hello, can you hear me?"
6. **Should hear AI respond!** ✅

### **3. Monitor Railway Logs**

Watch for:
- Webhook events
- Session creation
- Soniox initialization
- Transcriptions
- AI responses

---

## 🎯 Expected Log Flow (After Fixes)

```
1. 📞 Outbound call initiated: v3:xxxxx
2. 📦 Call data stored in Redis
3. [30 seconds later...]
4. 🎯 Webhook received: call.answered
5. 🔧 Loading agent configuration
6. 🔑 Decrypting API keys (Soniox, LLM, TTS)
7. 🎤 Initializing Soniox STT service
8. 🔊 Initializing TTS service
9. 🧠 Initializing LLM
10. 🔗 WebSocket connection established
11. 🎙️ Audio streaming started
12. [You speak...]
13. 📝 Transcription: "Hello"
14. 🤖 AI processing...
15. 🔊 TTS generating...
16. 📡 Audio sent to caller
```

---

## 🚨 If Still Doesn't Work

### **Check Telnyx Webhook Logs:**

1. Telnyx Portal → Developer → Webhooks
2. Look for recent webhook attempts
3. Check if any failed to deliver
4. Status should be 200 OK

### **Check Railway Logs:**

1. Look for webhook POST requests
2. Should see: `POST /api/webhook/telnyx`
3. Should return 200 status

### **Common Issues:**

**Issue: "No webhook received"**
- Telnyx webhook URL not set correctly
- URL has typo
- Telnyx connection not associated with phone number

**Issue: "401 on webhook"**
- Webhooks don't need auth (check CORS)
- Backend should accept all webhook POSTs

**Issue: "Soniox initialization fails"**
- API key invalid or expired
- Key not decrypted properly (ENCRYPTION_KEY issue)
- Soniox account has no credits

---

## 📋 Quick Verification Checklist

Before making a call, verify:

- [ ] ENCRYPTION_KEY is set in Railway
- [ ] Telnyx webhook URL configured: `https://api.li-ai.org/api/webhook/telnyx`
- [ ] Telnyx webhook HTTP method is POST
- [ ] Phone number is assigned to Telnyx connection
- [ ] Soniox API key is valid (test it)
- [ ] Agent is configured with Soniox STT
- [ ] Agent has LLM and TTS configured
- [ ] All API keys are re-entered after encryption key update

---

## 🎯 Priority Order

1. **Set ENCRYPTION_KEY** (5 min) ← Do this FIRST
2. **Configure Telnyx webhook** (10 min) ← Do this SECOND
3. **Re-enter API keys** (5 min) ← Do this THIRD
4. **Test call** (2 min) ← Then test

**Total time: ~22 minutes to get calls working!**

---

## 🆘 Still Need Help?

After completing all fixes, if still not working, provide:

1. **Railway logs** (last 100 lines after making a call)
2. **Telnyx webhook logs** (screenshot from portal)
3. **Screenshot** of Telnyx webhook configuration
4. **Confirmation** that ENCRYPTION_KEY is set

I can then help debug the specific issue!

---

**The main blocker is the Telnyx webhook not being configured.** 

**Without it, backend never knows the call was answered!** 🎯
