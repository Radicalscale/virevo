# Deployment Quick Start - Railway + Netlify

## 🚀 Step-by-Step Deployment Guide

### Step 1: Push Code to GitHub (5 minutes)

```bash
# If you haven't already committed the latest changes:
git add .
git commit -m "Ready for deployment with user API keys"
git push origin main
```

---

### Step 2: Deploy Backend to Railway (15-20 minutes)

#### A. Connect to Railway Project

1. Go to: https://railway.app/project/22ec197d-f1e9-4457-aeb4-97954e5b613d
2. Click **"New"** → **"GitHub Repo"**
3. Select your repository
4. Railway will detect the `Dockerfile` automatically ✓

#### B. Add Environment Variables

Click **"Variables"** tab and add these one by one:

**Database:**
```
MONGO_URL=mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada
DB_NAME=test_database
```

**CORS:**
```
CORS_ORIGINS=https://li-ai.org,https://www.li-ai.org,https://api.li-ai.org
```

**⚠️ DO NOT ADD USER API KEYS HERE!**

The system is designed for **each user to add their own API keys** via the Settings page.

**DO NOT ADD:**
- DEEPGRAM_API_KEY
- OPENAI_API_KEY  
- ELEVEN_API_KEY
- GROK_API_KEY
- HUME_API_KEY
- ASSEMBLYAI_API_KEY
- SONIOX_API_KEY
- TELNYX_API_KEY
- DAILY_API_KEY

**Why?** These would become shared platform keys for all users. Instead, users add their own keys after signup at `/settings`.

**System Settings:**
```
ENABLE_RAG=true
COOKIE_SECURE=true
BACKEND_URL=https://api.li-ai.org
```

**Note:** BACKEND_URL must match your Railway domain (api.li-ai.org)

---

**🚨 IMPORTANT: User API Keys vs Platform Keys**

**DO NOT add API keys (Deepgram, OpenAI, ElevenLabs, Telnyx, etc.) as Railway environment variables!**

**Why?**
- Your system is designed for **multi-tenant** operation
- Each user should use their **own API keys**
- Adding keys to Railway would make them **shared by all users**
- This defeats the purpose of the per-user key system

**How it works:**
1. Users sign up at https://li-ai.org
2. They go to Settings → API Keys
3. They add their own keys (encrypted in MongoDB)
4. Their agents/calls use only their keys
5. Complete isolation between users

**Your keys (kendrickbowman9@gmail.com):**
- Already in MongoDB (encrypted)
- You'll access them after deployment by logging in

---

**🔐 CRITICAL - JWT Secret:**

Run this command on your local machine:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and add to Railway:
```
JWT_SECRET_KEY=[paste your generated secret here]
```

#### C. Configure Custom Domain

1. In Railway, go to **Settings** → **Domains**
2. Click **"Custom Domain"**
3. Enter: `api.li-ai.org`
4. Railway will show a CNAME record like: `xxxxx.railway.app`

**Keep this CNAME value - you'll need it for DNS!**

#### D. Deploy & Monitor

1. Railway will automatically start building
2. Go to **"Deployments"** tab to watch progress
3. Build takes ~5-10 minutes (first time)
4. Check **"Logs"** for any errors

---

### Step 3: Configure DNS for Backend (5 minutes)

Go to your domain registrar (where you registered li-ai.org):

**Add CNAME Record:**
```
Type: CNAME
Name: api
Value: [the CNAME Railway gave you, e.g., xxxxx.railway.app]
TTL: Auto or 3600
```

**Wait for DNS propagation** (5-60 minutes, usually ~10 minutes)

**Test when ready:**
```bash
curl https://api.li-ai.org/api/health
```

Should return: `{"status":"healthy", ...}`

---

### Step 4: Deploy Frontend to Netlify (10 minutes)

#### A. Create New Site

1. Go to: https://app.netlify.com/
2. Click **"Add new site"** → **"Import an existing project"**
3. Choose **"Deploy with GitHub"**
4. Select your repository
5. **Leave build settings EMPTY** - netlify.toml in your repo will configure everything automatically
   - Or if asked, use:
     - **Base directory:** (leave empty)
     - **Build command:** (leave empty)
     - **Publish directory:** (leave empty)
6. Click **"Deploy site"**

#### B. Add Environment Variable

1. Go to **Site configuration** → **Environment variables**
2. Click **"Add a variable"**
3. Add:
   ```
   Key: REACT_APP_BACKEND_URL
   Value: https://api.li-ai.org
   ```
4. Click **"Redeploy"** (trigger new build with env var)

#### C. Configure Custom Domain

1. Go to **Domain management** → **Add custom domain**
2. Enter: `li-ai.org`
3. Netlify will show you DNS records

**Keep these values - you'll need them!**

---

### Step 5: Configure DNS for Frontend (5 minutes)

Go to your domain registrar again:

**Add A Record (for root domain):**
```
Type: A
Name: @ (or blank)
Value: [Netlify Load Balancer IP - they'll give you this]
TTL: Auto or 3600
```

**Add CNAME Record (for www):**
```
Type: CNAME
Name: www
Value: [your-site-name].netlify.app
TTL: Auto or 3600
```

**Wait for DNS propagation** (5-60 minutes)

#### D. Enable HTTPS

1. Back in Netlify, go to **Domain management**
2. Wait for DNS to propagate (Netlify shows status)
3. Netlify will auto-provision SSL certificate
4. Enable **"Force HTTPS"** in HTTPS settings

**Test when ready:**
- Visit: https://li-ai.org
- Should show your login page

---

## Step 6: Test Everything (10 minutes)

### Backend Test
```bash
# Health check
curl https://api.li-ai.org/api/health

# Create test user
curl -X POST https://api.li-ai.org/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@li-ai.org","password":"Test123!","name":"Test User"}'
```

### Frontend Test
1. Visit https://li-ai.org
2. Sign up with new account
3. **CRITICAL:** Go to Settings → API Keys
4. **Add YOUR API keys for:**
   - Deepgram (STT) - REQUIRED
   - OpenAI or Grok (LLM) - REQUIRED
   - ElevenLabs or Hume (TTS) - REQUIRED
   - Telnyx (Calling) - REQUIRED
5. Create an agent
6. Make a test call

**⚠️ Without adding your API keys in Settings, calls will fail!**

---

## Troubleshooting

### Backend Issues

**"502 Bad Gateway"**
- Check Railway logs in Deployments tab
- Verify all environment variables are set
- Check MongoDB Atlas IP whitelist: needs 0.0.0.0/0 for Railway

**"CORS Error"**
- Verify CORS_ORIGINS includes https://li-ai.org
- Check frontend uses https://api.li-ai.org

### Frontend Issues

**"API calls fail"**
- Check REACT_APP_BACKEND_URL is https://api.li-ai.org
- Verify backend is accessible
- Check browser console for errors

**"Login not working"**
- Verify JWT_SECRET_KEY is set in Railway
- Check cookies in browser DevTools
- Ensure COOKIE_SECURE=true

### DNS Issues

**"Can't reach api.li-ai.org"**
- Check CNAME is correct: `dig api.li-ai.org`
- Wait for DNS propagation (can take up to 1 hour)
- Try from different network/device

**"Can't reach li-ai.org"**
- Check A record is correct: `dig li-ai.org`
- Verify Netlify shows domain as active
- Clear browser cache

---

## MongoDB Atlas - Important!

**IP Whitelist for Railway:**

1. Go to MongoDB Atlas → Network Access
2. Click **"Add IP Address"**
3. Add: `0.0.0.0/0` (allow all)
4. Why? Railway uses dynamic IPs that change

---

## Cost Estimates

- **Railway:** $20-50/month (includes hosting + usage for 20+ concurrent calls)
- **Netlify:** $0-19/month (likely free tier sufficient)
- **MongoDB Atlas:** Already configured ✓
- **Total:** ~$20-70/month

---

## What Happens After Deployment?

### Auto-Deploy Workflow
```
Push to GitHub → Railway auto-deploys backend
              → Netlify auto-deploys frontend
```

Every time you push code, both services will automatically build and deploy!

### Monitoring
- **Railway:** Monitor logs and metrics in dashboard
- **Netlify:** View build logs and bandwidth usage
- **MongoDB Atlas:** Check database metrics

---

## Summary Checklist

Before you start:
- [ ] Code pushed to GitHub
- [ ] Railway account ready
- [ ] Netlify account ready
- [ ] Domain li-ai.org accessible
- [ ] MongoDB Atlas IP whitelist configured

Backend (Railway):
- [ ] GitHub repo connected
- [ ] All environment variables added
- [ ] JWT_SECRET_KEY generated and added
- [ ] Custom domain api.li-ai.org configured
- [ ] DNS CNAME added
- [ ] Deployment successful
- [ ] Health check passes

Frontend (Netlify):
- [ ] Site imported from GitHub
- [ ] REACT_APP_BACKEND_URL set
- [ ] Build successful
- [ ] Custom domain li-ai.org configured
- [ ] DNS records added (A + CNAME)
- [ ] HTTPS enabled
- [ ] Site loads correctly

Testing:
- [ ] Backend health check works
- [ ] Can create user account
- [ ] Can login
- [ ] Can create agent
- [ ] Can add API keys
- [ ] Can make test call

---

## Need Help?

Refer to detailed guides:
- **RAILWAY_NETLIFY_DEPLOYMENT.md** - Complete guide
- **DEPLOYMENT_GUIDE.md** - Comprehensive walkthrough
- **LOCAL_DOCKER_TEST.md** - Test locally first

---

**Ready to deploy? Start with Step 1! 🚀**

Estimated total time: **60-90 minutes** (including DNS propagation waits)
