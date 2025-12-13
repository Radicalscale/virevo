# Complete Netlify Deployment Guide

## 📋 Prerequisites

- ✅ Code pushed to GitHub
- ✅ Railway backend deployed at `api.li-ai.org`
- ✅ Netlify account (free tier works)
- ✅ Domain `li-ai.org` accessible

---

## 🚀 Step-by-Step Deployment

### Step 1: Create New Netlify Site (5 minutes)

#### A. Import from GitHub

1. Go to: **https://app.netlify.com/**
2. Click **"Add new site"** (top right)
3. Select **"Import an existing project"**
4. Choose **"Deploy with GitHub"**
5. Authorize Netlify to access your GitHub repos (if first time)
6. Search for and select your repository: `kcbowman88/Re-cop` (or your repo name)

#### B. Configure Build Settings

**CRITICAL: Leave ALL build settings EMPTY in the UI!**

Your repository has a `netlify.toml` file that will handle all configuration automatically.

When you see the "Site settings" screen:

```
Base directory:     [LEAVE EMPTY]
Build command:      [LEAVE EMPTY]  
Publish directory:  [LEAVE EMPTY]
```

**Why?** 
- Your `netlify.toml` file (in repo root) contains:
  ```toml
  [build]
    base = "frontend"
    command = "yarn build"
    publish = "build"
  ```
- Netlify will read this automatically
- Setting values in UI can conflict with netlify.toml

7. Click **"Deploy [your-repo-name]"** (button at bottom)

---

### Step 2: Wait for Initial Build (2-3 minutes)

Netlify will:
1. Clone your repository
2. Read `netlify.toml` from root
3. Navigate to `frontend/` directory
4. Run `yarn install` to install dependencies
5. Run `yarn build` to create production build
6. Deploy the `frontend/build` folder

**Watch the deploy log** for progress. You should see:
```
9:24:00 AM: Build ready to start
9:24:02 AM: Cloning repository...
9:24:05 AM: Installing dependencies
9:24:30 AM: Installing NPM modules using Yarn
9:25:10 AM: "yarn run build" succeeded
9:25:15 AM: Site is live
```

**First deploy will likely FAIL** - this is expected! We need to add environment variables.

---

### Step 3: Add Environment Variable (1 minute)

After the first build attempt:

1. In Netlify, go to your site dashboard
2. Click **"Site configuration"** (left sidebar)
3. Click **"Environment variables"** (under "Build & deploy" section)
4. Click **"Add a variable"** → **"Add a single variable"**

**Add this variable:**

```
Key:   REACT_APP_BACKEND_URL
Value: https://api.li-ai.org
```

5. Click **"Create variable"**

**That's the ONLY environment variable you need!**

**Why?**
- React apps need env vars prefixed with `REACT_APP_`
- This tells the frontend where the backend API is located
- Your Railway backend URL

**Note:** Your `netlify.toml` also has this:
```toml
[build.environment]
  REACT_APP_BACKEND_URL = "https://api.li-ai.org"
```
But the Netlify UI variable takes precedence (which is good for flexibility).

---

### Step 4: Trigger New Deploy (1 minute)

After adding the environment variable:

1. Go to **"Deploys"** tab (left sidebar)
2. Click **"Trigger deploy"** (top right)
3. Select **"Deploy site"**

Netlify will rebuild with the environment variable.

**This build should succeed!**

---

### Step 5: Configure Custom Domain (10 minutes)

#### A. Get Your Netlify Site URL

After successful deploy, Netlify assigns a random URL like:
```
https://gleaming-unicorn-abc123.netlify.app
```

You'll replace this with `li-ai.org`.

#### B. Add Custom Domain in Netlify

1. In your site dashboard, go to **"Domain management"**
2. Click **"Add custom domain"** (or "Add domain")
3. Enter: `li-ai.org`
4. Click **"Verify"**
5. Netlify will ask: "Do you own this domain?" → Click **"Yes, add domain"**

#### C. Add www Subdomain (Optional but Recommended)

1. Still in Domain management, click **"Add domain alias"**
2. Enter: `www.li-ai.org`
3. Click **"Save"**

#### D. Get DNS Configuration from Netlify

Netlify will show you DNS records to add. It typically looks like:

**For Root Domain (li-ai.org):**
```
Type: A
Name: @  (or blank/root)
Value: 75.2.60.5  (Netlify Load Balancer IP - they'll give you the exact IP)
```

**For www Subdomain:**
```
Type: CNAME
Name: www
Value: gleaming-unicorn-abc123.netlify.app  (your Netlify site URL)
```

**Important:** The exact IP and values will be shown in your Netlify dashboard!

---

### Step 6: Configure DNS at Your Domain Registrar (5 minutes)

Go to wherever you registered `li-ai.org` (e.g., Namecheap, GoDaddy, Cloudflare, etc.)

#### A. Add A Record (Root Domain)

```
Type:  A
Name:  @  (or blank, or "li-ai.org" depending on registrar)
Value: [Netlify Load Balancer IP from Step 5D]
TTL:   3600 (or Auto)
```

#### B. Add CNAME Record (www)

```
Type:  CNAME
Name:  www
Value: [your-netlify-site-name].netlify.app
TTL:   3600 (or Auto)
```

#### C. Add CNAME Record for API (If Not Done Yet)

Your backend should also be configured:

```
Type:  CNAME
Name:  api
Value: [your-railway-domain].railway.app
TTL:   3600 (or Auto)
```

**Save all DNS changes!**

---

### Step 7: Wait for DNS Propagation (5-60 minutes)

DNS changes can take time to propagate globally:
- Minimum: 5 minutes
- Average: 15-30 minutes  
- Maximum: up to 72 hours (rare)

**Check DNS Propagation:**

**Method 1: Online Tool**
- Visit: https://dnschecker.org/
- Enter: `li-ai.org`
- Should show Netlify's IP

**Method 2: Command Line**
```bash
# Check A record
dig li-ai.org

# Check CNAME
dig www.li-ai.org
```

---

### Step 8: Enable HTTPS (Automatic)

Once DNS is propagated:

1. Go back to Netlify → **Domain management**
2. You'll see: "Awaiting DNS verification" → then → "Provisioning certificate"
3. Netlify automatically provisions SSL certificate (Let's Encrypt)
4. Takes 1-5 minutes after DNS propagates

#### Enable Force HTTPS

1. In Domain management, scroll to **HTTPS**
2. Enable: **"Force HTTPS"** (recommended)
3. This redirects all http:// requests to https://

**Your site is now secured! 🔒**

---

### Step 9: Verify Deployment (5 minutes)

#### A. Test Frontend Loads

1. Visit: **https://li-ai.org**
2. Should show your login page
3. Check browser console (F12) for errors

#### B. Test Backend Connection

1. Open browser DevTools (F12) → Network tab
2. Try to sign up or login
3. Check requests - should go to: `https://api.li-ai.org/api/auth/...`
4. Should NOT see CORS errors

#### C. Full Flow Test

1. **Sign up** with new account
2. **Login** successfully
3. Go to **Settings** → **API Keys**
4. Add your API keys:
   - Deepgram (REQUIRED)
   - OpenAI or Grok (REQUIRED)
   - ElevenLabs or Hume (REQUIRED)
   - Telnyx (REQUIRED for calling)
5. Create an **Agent**
6. Make a **test call**

**If all steps work → Deployment successful! 🎉**

---

## 📊 Summary of Configuration

### Netlify Build Settings (in netlify.toml)

```toml
[build]
  base = "frontend"                           # Where package.json is
  command = "yarn build"                      # Build command
  publish = "build"                           # Output directory (relative to base)

[build.environment]
  NODE_VERSION = "20"                         # Node.js version (required for react-router-dom v7)
  REACT_APP_BACKEND_URL = "https://api.li-ai.org"  # Backend API URL
```

### Environment Variables (in Netlify UI)

| Variable | Value | Why |
|----------|-------|-----|
| `REACT_APP_BACKEND_URL` | `https://api.li-ai.org` | Tells frontend where backend is |

**That's it!** Only 1 environment variable needed.

### DNS Records Summary

| Type | Name | Value | Purpose |
|------|------|-------|---------|
| A | @ | [Netlify IP] | Root domain (li-ai.org) |
| CNAME | www | [your-site].netlify.app | www subdomain |
| CNAME | api | [your-railway].railway.app | Backend API |

---

## 🔧 Troubleshooting

### Build Fails: "Cannot find module 'react'"

**Cause:** Dependencies not installing properly

**Fix:**
1. Check `yarn.lock` is committed to repo
2. In Netlify, go to: Site settings → Build & deploy → Build settings
3. Clear build cache: Deploys → Options → Clear cache and deploy site

### Build Fails: "node-sass" or native module errors

**Cause:** Native modules need compilation

**Fix:** Switch to `sass` (pure JS) instead of `node-sass`:
```bash
# In your local frontend directory
yarn remove node-sass
yarn add sass
# Commit and push
```

### CORS Errors in Browser

**Symptoms:**
```
Access to fetch at 'https://api.li-ai.org/api/auth/login' 
from origin 'https://li-ai.org' has been blocked by CORS policy
```

**Fix:**
1. Check Railway backend has: `CORS_ORIGINS=https://li-ai.org,https://www.li-ai.org,https://api.li-ai.org`
2. Restart Railway backend
3. Clear browser cache
4. Try in incognito mode

### Site Shows Netlify 404

**Cause:** DNS not pointed correctly or HTTPS not provisioned

**Fix:**
1. Check DNS records are correct (use dnschecker.org)
2. Wait for SSL certificate (check Domain management in Netlify)
3. Force HTTPS is enabled

### "REACT_APP_BACKEND_URL is undefined"

**Cause:** Environment variable not set properly

**Fix:**
1. Verify variable exists in: Site configuration → Environment variables
2. Variable name must be EXACTLY: `REACT_APP_BACKEND_URL` (case-sensitive)
3. Trigger new deploy after adding variable

### API Calls Go to Wrong URL

**Symptoms:** Requests go to localhost or preview URL instead of api.li-ai.org

**Fix:**
1. Check `REACT_APP_BACKEND_URL=https://api.li-ai.org` in Netlify
2. Rebuild site
3. Clear browser cache
4. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

---

## 🎛️ Advanced Configuration

### Build Environment

**Change Node Version:**

In `netlify.toml`:
```toml
[build.environment]
  NODE_VERSION = "20"  # Required for react-router-dom v7
```

**Note:** Your app requires Node 20+ due to react-router-dom@7.9.5

### Deploy Previews

Netlify automatically creates preview deploys for:
- Pull requests
- Branch deploys

Configure in: Site settings → Build & deploy → Deploy contexts

### Build Hooks

Create webhook URLs to trigger deploys:
1. Site settings → Build & deploy → Build hooks
2. "Add build hook"
3. Copy webhook URL
4. POST to this URL to trigger deploy

### Redirects & Rewrites

Already configured in `netlify.toml`:
```toml
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

This enables client-side routing for React Router.

### Custom Headers

Security headers already configured in `netlify.toml`:
```toml
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "no-referrer"
```

---

## 💰 Cost & Limits

### Netlify Free Tier

- ✅ 100 GB bandwidth/month
- ✅ 300 build minutes/month
- ✅ Unlimited sites
- ✅ Custom domains
- ✅ Free SSL certificates
- ✅ Deploy previews

**For your app:** Free tier is sufficient unless you have massive traffic.

### When to Upgrade?

Upgrade to Pro ($19/month) if you need:
- More bandwidth (>100 GB/month)
- More build minutes
- Priority support
- Team collaboration features

---

## 📈 Monitoring

### Netlify Analytics

**Enable Analytics (Optional, $9/month):**
1. Site settings → Analytics
2. "Enable Analytics"

**Free Alternative:**
- Add Google Analytics to your React app
- Use Netlify's free deploy logs

### Deploy Notifications

**Get notified of deploys:**
1. Site settings → Build & deploy → Deploy notifications
2. Add notification:
   - Email
   - Slack
   - Webhook

---

## 🔄 Auto-Deploy Workflow

Once configured, your workflow is:

```
1. Edit code locally
     ↓
2. git commit & push to GitHub
     ↓
3. Netlify automatically detects push
     ↓
4. Builds and deploys new version
     ↓
5. Live at li-ai.org in ~2-3 minutes
```

**No manual steps needed!**

---

## ✅ Final Checklist

Before considering deployment complete:

- [ ] Netlify build succeeds (green checkmark)
- [ ] REACT_APP_BACKEND_URL environment variable set
- [ ] DNS records configured at registrar
- [ ] li-ai.org resolves to Netlify
- [ ] www.li-ai.org resolves to Netlify
- [ ] api.li-ai.org resolves to Railway
- [ ] HTTPS enabled and working
- [ ] Force HTTPS enabled
- [ ] Can access https://li-ai.org
- [ ] Login page loads
- [ ] Can create account
- [ ] Can login
- [ ] API calls go to https://api.li-ai.org
- [ ] No CORS errors
- [ ] Can add API keys in Settings
- [ ] Can create agents
- [ ] Can make test calls

---

## 🆘 Getting Help

### Netlify Support

- **Docs:** https://docs.netlify.com/
- **Community:** https://answers.netlify.com/
- **Status:** https://www.netlifystatus.com/

### Check Build Logs

Always check the full build log:
1. Netlify → Deploys → [Failed Deploy]
2. Scroll through entire log
3. Look for `npm ERR!` or `error` messages
4. Copy error and search/ask for help

### Common Resources

- **Netlify React Guide:** https://docs.netlify.com/frameworks/react/
- **DNS Propagation:** https://dnschecker.org/
- **SSL Issues:** https://docs.netlify.com/domains-https/troubleshooting-tips/

---

## 📝 Quick Reference

### Netlify Dashboard Links

- **Site Dashboard:** https://app.netlify.com/sites/[your-site-name]
- **Deploys:** .../deploys
- **Domain Settings:** .../settings/domain
- **Environment Variables:** .../configuration/env
- **Build Settings:** .../settings/deploys

### Important Commands

```bash
# Test DNS
dig li-ai.org
dig www.li-ai.org

# Test HTTPS
curl -I https://li-ai.org

# Check response
curl https://li-ai.org
```

---

## 🎉 You're Done!

Your React frontend is now:
- ✅ Deployed on Netlify CDN (global)
- ✅ Accessible at https://li-ai.org
- ✅ Secured with HTTPS
- ✅ Auto-deploys on git push
- ✅ Connected to Railway backend

**Total setup time:** ~30-45 minutes (including DNS wait)

**Next steps:**
- Share your app with users!
- Monitor usage and costs
- Update features and deploy automatically

🚀 **Your voice AI platform is LIVE!**
