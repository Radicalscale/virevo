# 🚀 ONE-SHOT DEPLOYMENT GUIDE

## Critical Fix First!

**You're getting the error because `BACKEND_URL` environment variable is missing.**

---

## 🎯 Quick Fix (2 minutes)

### Go to Railway Dashboard NOW:

1. Click your backend service
2. Go to **Variables** tab
3. Click **"+ New Variable"**
4. Add:
   ```
   BACKEND_URL=https://your-railway-app.up.railway.app
   ```
   ⚠️ Replace with YOUR actual Railway public domain

5. Click **Save**
6. Backend will redeploy automatically

### Get Your Railway URL:
- Go to backend service → **Settings** → **Networking**
- Copy the **Public Domain** (e.g., `andromeda-production-xxxx.up.railway.app`)
- Use that as your BACKEND_URL

---

## 📋 Complete Environment Variables Checklist

Go to Railway → Backend → Variables and add **ALL** of these:

### ✅ Must Have (Critical):
```bash
BACKEND_URL=https://your-railway-app.up.railway.app
MONGO_URL=mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada
REDIS_URL=redis://default:password@redis.railway.internal:6379
JWT_SECRET_KEY=<generate>
ENCRYPTION_KEY=<generate>
CORS_ORIGINS=https://li-ai.org
```

### 🔑 Generate Keys:
```bash
# JWT_SECRET_KEY (copy output):
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# ENCRYPTION_KEY (copy output):
python3 -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"
```

### 📞 If Using Telnyx Calls (Optional):
```bash
TELNYX_API_KEY=your_telnyx_api_key
```

### 🎤 If Using AI Voice Features (Optional):
```bash
SONIOX_API_KEY=your_soniox_key
ELEVENLABS_API_KEY=your_elevenlabs_key
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
```

---

## 🔧 Step-by-Step One-Shot Deployment

### Phase 1: Railway Backend (10 min)

#### 1.1 Add Redis
```
Railway Dashboard → + New → Database → Add Redis
Wait 30 seconds → Click Redis → Connect → Copy PRIVATE URL
Format: redis://default:xxx@redis.railway.internal:6379
```

#### 1.2 Get Railway Public URL
```
Backend service → Settings → Networking → Generate Domain (if needed)
Copy: https://your-app-production-xxxx.up.railway.app
```

#### 1.3 Add ALL Environment Variables
```
Backend service → Variables → Add all from checklist above
Use Railway public URL for BACKEND_URL
```

#### 1.4 Deploy
```bash
git add .
git commit -m "Production deployment"
git push origin main
```
Wait 3-5 minutes for deployment.

#### 1.5 Verify Backend
```bash
curl https://your-railway-app.up.railway.app/api/health
# Should return: {"status":"healthy"}
```

---

### Phase 2: Netlify Frontend (8 min)

#### 2.1 Go to Netlify Dashboard
```
https://app.netlify.com → Add new site → Import from GitHub
```

#### 2.2 Configure Build Settings
```
Repository: Select your repo
Base directory: frontend
Build command: yarn build
Publish directory: frontend/build
```

#### 2.3 Add Environment Variable
```
Site settings → Environment variables → Add
Key: REACT_APP_BACKEND_URL
Value: https://your-railway-app.up.railway.app
```

#### 2.4 Deploy
Click **"Deploy site"** → Wait 3-5 minutes

#### 2.5 Get Netlify URL
```
Copy your site URL: https://your-app-name.netlify.app
```

---

### Phase 3: Update CORS (2 min)

#### 3.1 Update Railway Backend Variable
```
Railway → Backend → Variables → Find CORS_ORIGINS
Update to: https://your-app-name.netlify.app
Save → Backend will redeploy
```

---

### Phase 4: Test (5 min)

#### 4.1 Test Backend
```bash
curl https://your-railway-app.up.railway.app/api/health
# Expected: {"status":"healthy"}
```

#### 4.2 Test Frontend
```
1. Visit: https://your-app-name.netlify.app
2. Register a new account
3. Login
4. Try to access agents page
```

#### 4.3 Test Outbound Call (if using Telnyx)
```
1. Create an agent
2. Add a phone number
3. Try to make an outbound call
4. Should work now! ✅
```

#### 4.4 Check Logs
```
Railway → Backend → Logs
Look for:
✅ "Application startup complete"
✅ No Redis connection errors
✅ No BACKEND_URL errors
```

---

## 🌐 Phase 5: Custom Domain (Optional - 15 min)

### 5.1 Railway Custom Domain (api.li-ai.org)
```
Railway → Backend → Settings → Networking → Add Custom Domain
Enter: api.li-ai.org
Copy DNS record shown (CNAME)
```

### 5.2 Netlify Custom Domain (li-ai.org)
```
Netlify → Site settings → Domain management → Add custom domain
Enter: li-ai.org
Copy DNS records shown
```

### 5.3 Update DNS (Your Domain Registrar)
```
Add records:
CNAME: api → your-railway-app.up.railway.app
A or CNAME: @ → Netlify (as shown in Netlify dashboard)
```

### 5.4 Wait for DNS Propagation (5-30 min)
```bash
# Check when ready:
dig api.li-ai.org
curl https://api.li-ai.org/api/health
```

### 5.5 Update Environment Variables
```
Railway → BACKEND_URL → https://api.li-ai.org
Railway → CORS_ORIGINS → https://li-ai.org
Netlify → REACT_APP_BACKEND_URL → https://api.li-ai.org
```

### 5.6 Enable HTTPS
Both Railway and Netlify auto-provision SSL certificates after DNS is configured.

---

## ✅ Success Checklist

- [ ] Redis added to Railway project
- [ ] All environment variables set (especially BACKEND_URL!)
- [ ] Railway backend deployed and accessible
- [ ] Netlify frontend deployed and accessible
- [ ] CORS_ORIGINS includes frontend URL
- [ ] Can register and login
- [ ] Can view agents
- [ ] Can make outbound calls (no 500 error)
- [ ] No errors in Railway logs
- [ ] No errors in browser console

---

## 🐛 Common Issues & Instant Fixes

### Error: "BACKEND_URL environment variable must be set"
**Fix:**
```
Railway → Backend → Variables → Add:
BACKEND_URL=https://your-railway-app.up.railway.app
```

### Error: "CORS policy" in browser
**Fix:**
```
Railway → Backend → Variables → Update CORS_ORIGINS:
CORS_ORIGINS=https://your-netlify-app.netlify.app
```

### Error: "Cannot connect to Redis"
**Fix:**
```
Verify REDIS_URL is INTERNAL Railway URL:
redis://default:xxx@redis.railway.internal:6379
NOT the public URL!
```

### Error: "MongoDB connection failed"
**Fix:**
```
MongoDB Atlas → Network Access → Add IP:
0.0.0.0/0 (allow all - Railway uses dynamic IPs)
```

### Error: 401 Unauthorized
**Fix:**
```
Check JWT_SECRET_KEY is set
Clear browser cookies
Try login again
```

### Error: 500 Internal Server Error (other than BACKEND_URL)
**Fix:**
```
Railway → Logs → Check error message
Usually missing API key or env variable
```

---

## 📊 Architecture After Deployment

```
User Browser
    ↓
Netlify (Frontend: React App)
    ↓ HTTPS API Calls
Railway Backend (FastAPI)
    ├── Redis (Session State)
    ├── MongoDB Atlas (Data Storage)
    └── Telnyx API (Phone Calls)
```

---

## 🎯 Current Status Fix

Based on your error, you need to:

1. **Add BACKEND_URL immediately:**
   ```
   Go to Railway → Backend service → Variables
   Add: BACKEND_URL=https://your-railway-domain.up.railway.app
   ```

2. **Wait 30 seconds for redeploy**

3. **Try making a call again** - Should work! ✅

---

## 🆘 Still Having Issues?

Share:
1. Complete Railway logs (last 50 lines)
2. Browser console errors
3. Network tab showing failed request
4. Screenshot of Railway environment variables (hide sensitive values)

---

**Total Time:** 25-40 minutes (without custom domain) or 45-60 minutes (with custom domain)

**Most Important:** Make sure `BACKEND_URL` is set! This is what you're missing right now. 🎯
