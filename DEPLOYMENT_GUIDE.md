# Deployment Guide: Railway + Netlify

This guide covers deploying the Andromeda Voice AI Platform to production using Railway (backend) and Netlify (frontend) with custom domain li-ai.org.

## Architecture Overview

```
┌─────────────────┐
│   li-ai.org     │  ← Frontend (Netlify)
│   (React SPA)   │
└────────┬────────┘
         │
         │ API Calls
         ↓
┌─────────────────┐
│ api.li-ai.org   │  ← Backend (Railway)
│  (FastAPI)      │
└────────┬────────┘
         │
         │ Database
         ↓
┌─────────────────┐
│  MongoDB Atlas  │  ← Database (Already configured)
└─────────────────┘
```

## Prerequisites

- GitHub account (for connecting repos)
- Railway account (https://railway.app/)
- Netlify account (https://netlify.com/)
- Domain li-ai.org registered and accessible
- MongoDB Atlas already configured ✅

## Part 1: Backend Deployment (Railway)

### Step 1: Prepare Repository

1. **Ensure all files are committed to GitHub**
   - The Dockerfile, railway.json, and .env.production.template should be in your repo
   - Push all changes to your main branch

### Step 2: Connect Railway to GitHub

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will detect the Dockerfile automatically

### Step 3: Configure Environment Variables

1. In Railway project, go to "Variables" tab
2. Add ALL environment variables from `.env.production.template`:

```bash
MONGO_URL=mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada
DB_NAME=test_database
CORS_ORIGINS=https://li-ai.org,https://www.li-ai.org,https://api.li-ai.org
DEEPGRAM_API_KEY=d2e699e2ead45364e75b5ad08cf706702f537ae4
OPENAI_API_KEY=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
ELEVEN_API_KEY=sk_fd288b72abe95953baafcfbf561d6fe9d2af4dabf5458e12
GROK_API_KEY=xai-mDonAg7JKMuTnRm6k6NF9SxSNTrLpnENRyU5Y0CWzG82NBzKcr5y3eUGnC5Yxu7yZTRpG98ax2ZmE8GL
HUME_API_KEY=VCZyy20cdgXA34BrJRv6S5GhFFGg2cbRzxVvXC9S1RCGX1Dv
ASSEMBLYAI_API_KEY=0a0917bc03da4126860415b1e1accbcc
SONIOX_API_KEY=b999f22d7b6989eb2d1f1b7badfd0f77a1d110d238906afee7b6dab97ada01d7
TELNYX_API_KEY=KEY0199EBFE1BCD21C2E7B0F316A3E980CC_vM9JBdNR3gZ1qlUiqziXCN
TELNYX_CONNECTION_ID=2777245537294877821
DAILY_ROOM_URL=https://aqlyf.daily.co/FHtaAicX69yXGlHz3O1r
DAILY_API_KEY=a05b2cc4358554dd2c1e7fbc19c399506d33fa7326a7f97fe66ee66e84ce379f
ENABLE_RAG=true
COOKIE_SECURE=true
JWT_SECRET_KEY=generate-a-new-secret-key-here
```

3. **IMPORTANT:** Generate a new JWT_SECRET_KEY:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

### Step 4: Configure Custom Domain

1. In Railway project, go to "Settings" → "Domains"
2. Click "Add Domain"
3. Enter: `api.li-ai.org`
4. Railway will provide DNS records (CNAME)
5. Go to your domain registrar and add the CNAME record:
   ```
   Type: CNAME
   Name: api
   Value: [Railway provided domain]
   ```
6. Wait for DNS propagation (can take 5-60 minutes)

### Step 5: Deploy

1. Railway will automatically build and deploy
2. Monitor the "Deployments" tab for build progress
3. Check logs for any errors
4. Once deployed, test: `https://api.li-ai.org/api/health`

## Part 2: Frontend Deployment (Netlify)

### Step 1: Connect Netlify to GitHub

1. Go to [Netlify Dashboard](https://app.netlify.com/)
2. Click "Add new site" → "Import an existing project"
3. Choose GitHub and select your repository
4. Configure build settings:
   - **Base directory:** `frontend`
   - **Build command:** `yarn build`
   - **Publish directory:** `frontend/build`

### Step 2: Configure Environment Variables

1. In Netlify site settings, go to "Site configuration" → "Environment variables"
2. Add:
   ```
   REACT_APP_BACKEND_URL=https://api.li-ai.org
   ```

### Step 3: Configure Custom Domain

1. In Netlify site settings, go to "Domain management"
2. Click "Add custom domain"
3. Enter: `li-ai.org`
4. Netlify will provide DNS records
5. Go to your domain registrar and add:
   ```
   Type: A
   Name: @
   Value: [Netlify Load Balancer IP]
   
   Type: CNAME
   Name: www
   Value: [Your Netlify site].netlify.app
   ```

### Step 4: Enable HTTPS

1. Netlify will automatically provision SSL certificate
2. Enable "Force HTTPS" in domain settings

### Step 5: Deploy

1. Netlify will automatically build and deploy
2. Monitor build logs
3. Once deployed, visit: `https://li-ai.org`

## Part 3: Testing Deployment

### Backend Tests

```bash
# Health check
curl https://api.li-ai.org/api/health

# Create test user
curl -X POST https://api.li-ai.org/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "name": "Test User"
  }'

# Login
curl -X POST https://api.li-ai.org/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!"}' \
  -c cookies.txt

# Get agents (with authentication)
curl https://api.li-ai.org/api/agents \
  -b cookies.txt
```

### Frontend Test

1. Visit `https://li-ai.org`
2. Should see login page
3. Create account and login
4. Test creating an agent
5. Test making a call

## Part 4: Monitoring & Scaling

### Railway Monitoring

1. View logs in Railway dashboard
2. Monitor resource usage (CPU, Memory)
3. For 20+ concurrent calls, Railway auto-scales
4. If needed, manually increase resources:
   - Go to Settings → Resources
   - Increase memory/CPU allocation

### Scaling Configuration

The Dockerfile is configured with 4 Gunicorn workers:
- Each worker can handle ~100 concurrent WebSocket connections
- Total capacity: ~400 concurrent calls
- If you need more, update Dockerfile `--workers` parameter

### Performance Optimization

1. **RAG Performance:**
   - ChromaDB persists in Railway volume
   - First query per session: ~100-200ms
   - Cached queries: <50ms

2. **Database Connection Pooling:**
   - Motor (MongoDB) uses connection pooling automatically
   - Max pool size: 100 connections

3. **Cookie Security:**
   - `COOKIE_SECURE=true` enforces HTTPS-only cookies
   - SameSite=None for cross-origin requests

## Troubleshooting

### Backend Issues

**Issue: 502 Bad Gateway**
- Check Railway logs for errors
- Verify all environment variables are set
- Check MongoDB Atlas IP whitelist (0.0.0.0/0 for Railway)

**Issue: CORS errors**
- Verify CORS_ORIGINS includes https://li-ai.org
- Check frontend is using https://api.li-ai.org

**Issue: WebSocket connection fails**
- Railway supports WebSocket by default
- Check logs for connection errors
- Verify Deepgram/Telnyx API keys

### Frontend Issues

**Issue: API calls fail**
- Check REACT_APP_BACKEND_URL is set correctly
- Verify CORS on backend
- Check browser console for errors

**Issue: Login not working**
- Check cookies are being set (browser DevTools → Application → Cookies)
- Verify COOKIE_SECURE=true in production
- Check JWT_SECRET_KEY is set

### Database Issues

**Issue: Can't connect to MongoDB**
- Verify MONGO_URL is correct
- Check MongoDB Atlas IP whitelist
- Railway IPs change, use 0.0.0.0/0 (allow all)

## Security Checklist

- [ ] Changed JWT_SECRET_KEY to new random value
- [ ] All API keys are in environment variables (not hardcoded)
- [ ] COOKIE_SECURE=true in production
- [ ] HTTPS enabled on both domains
- [ ] MongoDB Atlas IP whitelist configured
- [ ] CORS_ORIGINS set to specific domains
- [ ] Railway environment variables are private
- [ ] Netlify environment variables are private

## Cost Estimates

### Railway (Backend)
- Free tier: $5 credit/month (limited)
- Hobby plan: $5/month + usage
- Pro plan: $20/month + usage
- Estimated cost for 20+ concurrent calls: $20-50/month

### Netlify (Frontend)
- Free tier: 100GB bandwidth/month (usually sufficient)
- Pro plan: $19/month (if needed)
- Estimated cost: $0-19/month

### MongoDB Atlas
- Already configured ✅
- Current tier: [Check your Atlas dashboard]

### Total Estimated Cost: $20-70/month

## Maintenance

### Updates

1. Push changes to GitHub
2. Railway auto-deploys backend
3. Netlify auto-deploys frontend

### Backups

1. MongoDB Atlas: Configure automated backups in Atlas dashboard
2. Code: Already backed up in GitHub

### Monitoring

1. Set up Railway notifications for deployment failures
2. Set up Netlify notifications for build failures
3. Monitor MongoDB Atlas metrics
4. Set up uptime monitoring (e.g., UptimeRobot)

## Support

If you encounter issues:

1. Check Railway logs: `railway logs`
2. Check Netlify deploy logs
3. Check browser console for frontend errors
4. Review this guide for configuration issues

---

**Deployment Checklist:**

- [ ] Backend deployed to Railway
- [ ] Frontend deployed to Netlify  
- [ ] api.li-ai.org pointing to Railway
- [ ] li-ai.org pointing to Netlify
- [ ] All environment variables configured
- [ ] HTTPS working on both domains
- [ ] MongoDB connection working
- [ ] Authentication working
- [ ] Agents can be created
- [ ] Calls can be initiated
- [ ] WebSocket connections working
- [ ] RAG system operational

**Ready for production! 🚀**
