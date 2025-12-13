# Correct Railway Environment Variables

## ✅ What TO Add to Railway

These are **platform-level configuration** variables that the system needs to function:

### Database Configuration
```
MONGO_URL=mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada
DB_NAME=test_database
```

### CORS Configuration
```
CORS_ORIGINS=https://li-ai.org,https://www.li-ai.org,https://api.li-ai.org
```

### System Settings
```
ENABLE_RAG=true
COOKIE_SECURE=true
BACKEND_URL=https://api.li-ai.org
```

**Note:** BACKEND_URL should match your Railway custom domain

### JWT Authentication
```
JWT_SECRET_KEY=[generate a new random secret - see below]
```

**To generate JWT secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## ❌ What NOT to Add to Railway

**DO NOT add these to Railway environment variables:**

```
❌ DEEPGRAM_API_KEY
❌ OPENAI_API_KEY
❌ ELEVEN_API_KEY
❌ GROK_API_KEY
❌ HUME_API_KEY
❌ ASSEMBLYAI_API_KEY
❌ SONIOX_API_KEY
❌ TELNYX_API_KEY
❌ TELNYX_CONNECTION_ID
❌ DAILY_API_KEY
❌ DAILY_ROOM_URL
```

---

## Why?

### Platform Keys (Railway) vs User Keys (MongoDB)

**If you add API keys to Railway:**
```
User A logs in → Uses platform keys from Railway
User B logs in → Uses same platform keys from Railway
User C logs in → Uses same platform keys from Railway
```
❌ **Result:** All users share your keys, you pay for everything!

**Correct Multi-Tenant Setup:**
```
User A logs in → Uses User A's keys from MongoDB
User B logs in → Uses User B's keys from MongoDB  
User C logs in → Uses User C's keys from MongoDB
```
✅ **Result:** Complete isolation, each user pays for their own usage!

---

## How Users Add Their Keys

After deployment, users:

1. Visit https://li-ai.org
2. Sign up for account
3. Go to **Settings** → **API Keys**
4. Add their own keys:
   - Deepgram (STT)
   - OpenAI or Grok (LLM)
   - ElevenLabs or Hume (TTS)
   - Telnyx (for phone calling)
   - Others as needed

Keys are:
- ✅ Encrypted with Fernet before storage
- ✅ Stored in MongoDB per user
- ✅ Decrypted only when needed
- ✅ Used only for that user's calls

---

## Your Keys (kendrickbowman9@gmail.com)

Your personal API keys are already:
- ✅ In MongoDB (encrypted)
- ✅ Assigned to your user account
- ✅ Will work after deployment

**After deployment:**
1. Login at https://li-ai.org
2. Your keys are already there (from migration)
3. You can update them in Settings if needed

---

## Summary: Railway Environment Variables Checklist

Only add these 7 variables:

- [ ] MONGO_URL
- [ ] DB_NAME
- [ ] CORS_ORIGINS
- [ ] ENABLE_RAG
- [ ] COOKIE_SECURE
- [ ] BACKEND_URL
- [ ] JWT_SECRET_KEY (generate new!)

**Total: 7 variables**

**Do NOT add any API keys for Deepgram, OpenAI, ElevenLabs, Telnyx, etc.**

---

## Testing Multi-Tenant Isolation

After deployment, you can verify it works:

### Test 1: Your Account
1. Login as kendrickbowman9@gmail.com
2. Check Settings → API Keys
3. Should see your keys (encrypted values)
4. Make a call → Uses your keys

### Test 2: New User
1. Create new test account
2. Check Settings → API Keys
3. Should see NO keys initially
4. Try to make call → Should fail with "API key not found"
5. Add their own keys → Call works

### Test 3: Isolation Check
1. User A's calls use User A's keys
2. User B's calls use User B's keys
3. No cross-contamination
4. Each user's usage tracked separately

---

## Common Mistakes to Avoid

❌ **Mistake 1:** "I'll add my keys to Railway so users don't have to add keys"
- **Problem:** All users would use YOUR keys and YOU pay for everything

❌ **Mistake 2:** "I'll add keys to Railway as fallback if user doesn't have keys"
- **Problem:** System currently has NO fallback by design (Option A from earlier)
- **Result:** User without keys = calls fail with clear error

✅ **Correct:** No API keys in Railway, users MUST add their own keys

---

## Benefits of This Architecture

1. **Zero Shared Costs:** Each user pays for their own API usage
2. **Complete Isolation:** User A can't access User B's keys
3. **Scalability:** Support unlimited users without your API costs increasing
4. **Security:** Keys encrypted at rest, user-specific
5. **Compliance:** Each organization uses their own credentials
6. **Transparency:** Users see exactly what they're using

---

## What About Platform API Keys?

**Q:** "Can I add some keys as fallback for easier onboarding?"

**A:** Not with current implementation. System requires user keys (Option A).

**If you want platform fallback (Option B):**
- Would need code changes to calling_service.py
- Add fallback logic: try user key → if not found → try platform key
- Not recommended for SaaS model
- You'd pay for all user calls

**Current approach is better for SaaS:**
- Clear error messages when keys missing
- Forces users to add keys before first call
- No surprise costs for platform owner
