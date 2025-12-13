# Quick Start Deployment Checklist

## 🚀 Railway Backend (15 minutes)

### 1. Add Redis (2 min)
```
Railway Dashboard → + New → Database → Add Redis
Copy the internal URL: redis://default:xxx@redis.railway.internal:6379
```

### 2. Set Environment Variables (3 min)
Go to backend service → Variables:
```bash
MONGO_URL=mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada
REDIS_URL=redis://default:xxx@redis.railway.internal:6379
BACKEND_URL=https://api.li-ai.org
JWT_SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
ENCRYPTION_KEY=<generate with: python3 -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())">
CORS_ORIGINS=https://li-ai.org
```

**Note:** Set BACKEND_URL to your Railway public URL first, then update to `https://api.li-ai.org` after custom domain is configured.

### 3. Deploy (5 min)
```bash
git add .
git commit -m "Add Redis support"
git push
```
Wait for Railway to build and deploy.

### 4. Add Custom Domain (5 min)
```
Railway → Backend → Settings → Networking → Add Custom Domain: api.li-ai.org
Add DNS record: CNAME api → your-app.railway.app
```

**Test:** `curl https://api.li-ai.org/api/health`

---

## 🎨 Netlify Frontend (10 minutes)

### 1. Create .env.production (1 min)
```bash
cd /app/frontend
echo "REACT_APP_BACKEND_URL=https://api.li-ai.org" > .env.production
```

### 2. Deploy to Netlify (5 min)
```
Netlify Dashboard → Add new site → Import from GitHub
Base directory: frontend
Build command: yarn build
Publish directory: frontend/build

Environment variables:
REACT_APP_BACKEND_URL=https://api.li-ai.org
```

### 3. Add Custom Domain (4 min)
```
Netlify → Site settings → Domain management → Add custom domain: li-ai.org
Add DNS record: CNAME @ → your-app.netlify.app (or A record to Netlify IP)
Enable HTTPS (automatic after DNS propagation)
```

**Test:** Visit `https://li-ai.org`

---

## 🌐 DNS Configuration (Your Domain Registrar)

Add these records:

```
Type: A        Name: @      Value: 75.2.60.5              (Netlify IP for li-ai.org)
Type: CNAME    Name: api    Value: your-app.railway.app   (Railway backend)
Type: CNAME    Name: www    Value: your-app.netlify.app   (Optional redirect)
```

**Wait:** 5-30 minutes for DNS propagation

---

## ✅ Final Verification

### Backend Health:
```bash
curl https://api.li-ai.org/api/health
# Expected: {"status":"healthy"}
```

### Frontend Loading:
```
Visit: https://li-ai.org
# Should load React app
```

### Test Login:
```
1. Register a new user
2. Check browser DevTools → Application → Cookies
3. Verify "access_token" cookie exists with domain=.li-ai.org
```

### Check Logs:
```
Railway: Check for any errors in deployment logs
Netlify: Check deploy logs for build errors
Browser: Check console for CORS or network errors
```

---

## 🆘 Quick Fixes

### CORS Error?
```bash
# Update Railway backend variable:
CORS_ORIGINS=https://li-ai.org,https://www.li-ai.org
# Redeploy
```

### Redis Connection Error?
```bash
# Verify REDIS_URL is INTERNAL Railway URL:
redis://default:password@redis.railway.internal:6379
# NOT the public URL
```

### Cookie Not Set?
```bash
# Verify both frontend and backend are HTTPS ✅
# Check cookie domain in DevTools matches .li-ai.org
# Clear cookies and try again
```

### MongoDB Error?
```bash
# Check MongoDB Atlas IP whitelist (allow 0.0.0.0/0 for Railway)
# Verify connection string is correct
```

---

## 📊 Architecture Overview

```
User Browser (https://li-ai.org)
    ↓
Netlify Frontend (React App)
    ↓ API Calls
Railway Backend (https://api.li-ai.org)
    ↓ ← Redis (session state)
    ↓ ← MongoDB Atlas (data storage)
```

---

## 🎯 Success Criteria

✅ Both services deployed and accessible via HTTPS
✅ Custom domains configured (li-ai.org and api.li-ai.org)
✅ Can register and login without errors
✅ Cookies work across domains
✅ No CORS errors in browser console
✅ Backend logs show successful Redis connection

**Total Time:** ~30-45 minutes (including DNS propagation)

---

For detailed troubleshooting, see: `/app/COMPLETE_DEPLOYMENT_GUIDE.md`
