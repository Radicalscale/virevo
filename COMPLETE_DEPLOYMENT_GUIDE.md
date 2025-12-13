# Complete Deployment Guide: Railway + Netlify + Custom Domain

## 🎯 Overview

This guide will help you deploy:
- **Backend** → Railway (api.li-ai.org)
- **Frontend** → Netlify (li-ai.org or app.li-ai.org)
- **Database** → MongoDB Atlas (Already set up ✅)
- **Cache** → Railway Redis (To be added)
- **DNS** → Custom domain configuration for cross-domain cookies

---

## Part 1: Railway Backend Deployment

### Step 1: Add Redis to Railway Project

1. Go to your Railway project dashboard
2. Click **"+ New"** → **"Database"** → **"Add Redis"**
3. Wait for Redis to provision (takes ~30 seconds)
4. Click on the Redis service → **"Connect"** tab
5. Copy the **Private URL** (internal connection string)
   - Format: `redis://default:PASSWORD@redis.railway.internal:6379`
   - ⚠️ Use the **PRIVATE/INTERNAL** URL, not the public one

### Step 2: Configure Environment Variables

Go to your backend service → **Variables** tab and add:

#### **Critical Variables** (Required):
```bash
# Database
MONGO_URL=mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada

# Redis (paste your internal URL from Step 1)
REDIS_URL=redis://default:YOUR_PASSWORD@redis.railway.internal:6379

# Backend URL (for Telnyx webhooks - update after custom domain setup)
BACKEND_URL=https://your-app-production.up.railway.app

# Security
JWT_SECRET_KEY=<generate-random-32-char-string>
ENCRYPTION_KEY=<generate-random-32-byte-base64-key>

# CORS - Will update after Netlify deployment
CORS_ORIGINS=https://li-ai.org,https://app.li-ai.org
```

**Important:** After setting up custom domain `api.li-ai.org`, update `BACKEND_URL` to:
```bash
BACKEND_URL=https://api.li-ai.org
```

#### **Generate Secret Keys** (if you don't have them):
```bash
# JWT Secret (run locally or in Railway's terminal):
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption Key (32 bytes base64):
python3 -c "import base64; import os; print(base64.b64encode(os.urandom(32)).decode())"
```

#### **Optional Variables** (Add if using these services):
```bash
TELNYX_API_KEY=your_telnyx_key
SONIOX_API_KEY=your_soniox_key
ELEVENLABS_API_KEY=your_elevenlabs_key
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
```

### Step 3: Deploy Backend

1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Railway deployment with Redis"
   git push
   ```

2. Railway will auto-deploy (takes 2-5 minutes)

3. **Get your backend URL:**
   - Go to backend service → **Settings** → **Networking**
   - Copy the **Public Domain** (e.g., `your-app-production.up.railway.app`)
   - Or click **"Generate Domain"** if none exists

4. **Verify deployment:**
   ```bash
   curl https://your-app-production.up.railway.app/api/health
   # Should return: {"status":"healthy"}
   ```

### Step 4: Set Up Custom Domain for Backend (api.li-ai.org)

1. In Railway → Backend service → **Settings** → **Networking**
2. Under **Custom Domain**, click **"+ Add Custom Domain"**
3. Enter: `api.li-ai.org`
4. Railway will show you DNS records to add

5. **Add DNS Records** (in your domain registrar - GoDaddy, Cloudflare, etc.):
   ```
   Type: CNAME
   Name: api
   Value: your-app-production.up.railway.app
   TTL: Auto (or 3600)
   ```

6. Wait for DNS propagation (2-10 minutes)
7. Verify: `curl https://api.li-ai.org/api/health`

---

## Part 2: Netlify Frontend Deployment

### Step 1: Build Frontend Locally (Test)

1. Update frontend environment variables:
   ```bash
   cd /app/frontend
   ```

2. Create `.env.production` file:
   ```bash
   REACT_APP_BACKEND_URL=https://api.li-ai.org
   ```

3. Test build locally:
   ```bash
   yarn build
   # Should complete without errors
   ```

### Step 2: Deploy to Netlify

#### Option A: Deploy via Netlify UI (Recommended)

1. Go to [Netlify Dashboard](https://app.netlify.com/)
2. Click **"Add new site"** → **"Import an existing project"**
3. Connect to your GitHub repository
4. Configure build settings:
   ```
   Base directory: frontend
   Build command: yarn build
   Publish directory: frontend/build
   ```

5. **Add Environment Variables** (before deploying):
   - Click **"Site settings"** → **"Environment variables"**
   - Add:
     ```
     REACT_APP_BACKEND_URL=https://api.li-ai.org
     ```

6. Click **"Deploy site"**

#### Option B: Deploy via Netlify CLI

```bash
cd /app/frontend

# Install Netlify CLI
npm install -g netlify-cli

# Login to Netlify
netlify login

# Deploy
netlify deploy --prod --dir=build
```

### Step 3: Get Netlify URL

After deployment:
1. Netlify will give you a URL like: `your-app-name.netlify.app`
2. Copy this URL

### Step 4: Set Up Custom Domain for Frontend

#### If using root domain (li-ai.org):

1. In Netlify → **Site settings** → **Domain management**
2. Click **"Add custom domain"**
3. Enter: `li-ai.org`
4. Netlify will provide DNS records

5. **Add DNS Records** (in your domain registrar):
   ```
   Type: A
   Name: @
   Value: 75.2.60.5 (Netlify's IP)
   
   Type: CNAME
   Name: www
   Value: your-app-name.netlify.app
   ```

#### If using subdomain (app.li-ai.org):

1. In Netlify → **Site settings** → **Domain management**
2. Click **"Add custom domain"**
3. Enter: `app.li-ai.org`

4. **Add DNS Record**:
   ```
   Type: CNAME
   Name: app
   Value: your-app-name.netlify.app
   TTL: Auto
   ```

### Step 5: Enable HTTPS

1. In Netlify → **Site settings** → **Domain management** → **HTTPS**
2. Click **"Verify DNS configuration"**
3. Click **"Provision certificate"** (takes 2-5 minutes)
4. ✅ Wait for certificate to be active

---

## Part 3: Update CORS Settings

### After Both Deployments Are Live:

1. Go to Railway → Backend service → **Variables**
2. Update `CORS_ORIGINS` to include your frontend URL:

   **If using root domain:**
   ```bash
   CORS_ORIGINS=https://li-ai.org,https://www.li-ai.org
   ```

   **If using subdomain:**
   ```bash
   CORS_ORIGINS=https://app.li-ai.org,https://li-ai.org
   ```

3. Save and redeploy backend

---

## Part 4: DNS Configuration for Cross-Domain Cookies

### Current Cookie Configuration (Already in your code):
```javascript
domain: ".li-ai.org"
secure: true
httponly: true
samesite: "none"
```

### DNS Setup Required:

Your DNS should look like this:

```
Type: A        Name: @      Value: 75.2.60.5           (Netlify - for li-ai.org)
Type: CNAME    Name: www    Value: your-app.netlify.app (Redirect to root)
Type: CNAME    Name: api    Value: your-app.railway.app (Railway backend)
Type: CNAME    Name: app    Value: your-app.netlify.app (If using app subdomain)
```

### Cookie Flow:
1. User visits: `https://li-ai.org` (or `https://app.li-ai.org`)
2. Frontend calls: `https://api.li-ai.org/api/auth/login`
3. Backend sets cookie with `domain=.li-ai.org`
4. Cookie works across all `*.li-ai.org` subdomains ✅

---

## Part 5: Testing & Verification

### Test Backend:
```bash
# Health check
curl https://api.li-ai.org/api/health

# Should return: {"status":"healthy"}
```

### Test Frontend:
1. Visit: `https://li-ai.org` (or your configured domain)
2. Should load the React app
3. Check browser console for errors

### Test Authentication:
1. Try to register/login
2. Open **Browser DevTools** → **Application** → **Cookies**
3. Verify `access_token` cookie is set with:
   - Domain: `.li-ai.org`
   - Secure: ✅
   - HttpOnly: ✅
   - SameSite: `None`

### Test API Calls:
1. After login, navigate around the app
2. All API calls to `https://api.li-ai.org/api/*` should work
3. Check Network tab in DevTools for any CORS errors

---

## Part 6: Troubleshooting

### Issue: "CORS Error"
**Solution:**
1. Verify `CORS_ORIGINS` in Railway includes your frontend URL
2. Check frontend is using HTTPS (not HTTP)
3. Redeploy backend after changing CORS_ORIGINS

### Issue: "Cookie not being set"
**Solution:**
1. Verify both frontend and backend are on HTTPS ✅
2. Check domain in cookie settings matches your domain
3. Verify `samesite="none"` is set
4. Clear browser cookies and try again

### Issue: "Cannot connect to Redis"
**Solution:**
1. Verify `REDIS_URL` is the **internal/private** Railway URL
2. Check Redis service is running in Railway
3. Format: `redis://default:password@redis.railway.internal:6379`

### Issue: "MongoDB connection failed"
**Solution:**
1. Verify MongoDB Atlas allows Railway IPs (set to 0.0.0.0/0 for testing)
2. Check connection string has correct username/password
3. Ensure database user has read/write permissions

### Issue: "Build fails on Railway"
**Solution:**
1. Check Railway logs for specific error
2. Verify all dependencies are in `requirements.txt`
3. Ensure `railway.json` has correct builder settings

### Issue: "DNS not resolving"
**Solution:**
1. Wait 10-30 minutes for DNS propagation
2. Use `dig api.li-ai.org` to check DNS records
3. Verify CNAME records are correct (no trailing dots)

---

## Part 7: Environment Variables Summary

### Railway Backend Variables:
```bash
# Required
MONGO_URL=mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada
REDIS_URL=redis://default:PASSWORD@redis.railway.internal:6379
JWT_SECRET_KEY=<your-secret>
ENCRYPTION_KEY=<your-base64-key>
CORS_ORIGINS=https://li-ai.org,https://www.li-ai.org

# Optional (based on features used)
TELNYX_API_KEY=...
SONIOX_API_KEY=...
ELEVENLABS_API_KEY=...
OPENAI_API_KEY=...
DEEPGRAM_API_KEY=...
```

### Netlify Frontend Variables:
```bash
REACT_APP_BACKEND_URL=https://api.li-ai.org
```

---

## Part 8: Post-Deployment Checklist

- [ ] Railway Redis added and connected
- [ ] Railway backend deployed successfully
- [ ] Backend health endpoint working: `https://api.li-ai.org/api/health`
- [ ] Custom domain `api.li-ai.org` pointing to Railway
- [ ] Netlify frontend deployed successfully
- [ ] Frontend accessible at `https://li-ai.org` (or your domain)
- [ ] Custom domain configured for frontend
- [ ] HTTPS certificates provisioned (both Railway and Netlify)
- [ ] CORS_ORIGINS updated with frontend URL
- [ ] Test user registration/login working
- [ ] Cookies being set correctly (check DevTools)
- [ ] API calls from frontend to backend working
- [ ] Telnyx webhook configured (if using calls): `https://api.li-ai.org/api/webhook/telnyx`

---

## 🎉 Success Indicators

When everything is working:
1. ✅ Frontend loads at `https://li-ai.org`
2. ✅ Backend responds at `https://api.li-ai.org/api/health`
3. ✅ Can register and login successfully
4. ✅ Cookies are set with domain `.li-ai.org`
5. ✅ All API calls work without CORS errors
6. ✅ No errors in browser console or Railway logs

---

## Need Help?

If you encounter issues:
1. Share Railway deployment logs
2. Share browser console errors
3. Share Network tab showing failed requests
4. Verify all environment variables are set correctly
