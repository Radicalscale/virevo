# Netlify Deployment Debug Guide

## 🔍 Problem
After clearing cache and redeploying, Netlify STILL serves code with `/api/api/` paths.

## 📊 What We Know
✅ GitHub code is correct (`/settings/api-keys` without `/api` prefix)
✅ Netlify env var is correct (`https://api.li-ai.org` without `/api` suffix)  
✅ Cache was cleared
❌ Deployed site still has `/api/api/` in requests

## 🎯 Possible Causes

### 1. Netlify Connected to Wrong Branch
**Check:**
1. Netlify Dashboard → Site Settings → Build & deploy → Build settings
2. Look for "Branch: main" or "Branch: master"
3. Verify it matches your GitHub default branch

**Fix if wrong:**
- Change to correct branch
- Trigger new deploy

---

### 2. Netlify Deploy Preview vs Production
**Check:**
1. Are you testing the Production deployment or a Deploy Preview?
2. Netlify Dashboard → Deploys
3. Find the one marked "Published" (green)
4. Click "Open production deploy"

**Fix:**
- Make sure you're visiting the production URL, not a preview URL

---

### 3. Build Process Not Using Latest Code
**Check Netlify Build Log:**
1. Netlify Dashboard → Deploys → Click latest deploy
2. Scroll to "Build logs"
3. Look for:
   ```
   git clone https://github.com/YOUR_REPO
   Checking out branch: main
   HEAD is now at [commit hash]
   ```
4. Copy that commit hash

**Verify commit hash:**
```bash
cd /app
git log --oneline | head -5
# Does the commit hash match Netlify's?
```

**If hashes don't match:**
- Netlify is building old code
- Check if commits were pushed: `git push origin main --force`

---

### 4. Service Worker Caching (Browser Side)
**Check:**
1. Open DevTools → Application tab
2. Service Workers section
3. Look for any registered service workers

**Fix:**
1. Click "Unregister" for each
2. Clear Application storage
3. Hard reload

---

### 5. CDN/Edge Caching
**Netlify has edge caching that might persist.**

**Fix:**
1. Netlify Dashboard → Deploys
2. Click "Clear cache and deploy site" (not just "Trigger deploy")
3. Wait for build to complete
4. Add query param to URL: `https://li-ai.org?v=2` (bypass cache)

---

### 6. Multiple `api.js` Files
**Check if there are duplicate api service files:**

```bash
cd /app/frontend
find src -name "*api*.js" -o -name "*api*.jsx"
```

**If multiple found:**
- Check which one is being imported
- Ensure all are updated

---

### 7. Environment Variable Precedence Issue
**Netlify has THREE places to set env vars:**
1. `netlify.toml` (in your repo)
2. Netlify Dashboard → Environment variables
3. Netlify CLI config

**Priority:** Dashboard > netlify.toml > CLI

**Check:**
1. Go to Netlify Dashboard → Site Settings → Environment variables
2. Look for `REACT_APP_BACKEND_URL`
3. **Is there a value set?**
4. **Does it have `/api` at the end?**

**Fix:**
- If dashboard has wrong value, UPDATE it there
- Dashboard overrides netlify.toml!

---

### 8. Build Command Issue
**Check build command:**
1. Netlify Dashboard → Site Settings → Build & deploy
2. Verify Build command is: `yarn build`
3. Verify Base directory is: `frontend`
4. Verify Publish directory is: `frontend/build`

**If different:**
- Update to correct values
- Redeploy

---

### 9. React Build Cache
**Sometimes React build cache causes issues.**

**Update build command temporarily:**
```
Netlify Dashboard → Build settings → Build command
Change to: rm -rf node_modules/.cache && yarn build
```

Deploy once, then change back to `yarn build`.

---

### 10. Webpack/Build Configuration Override
**Check if there's a webpack config overriding paths:**

```bash
cd /app/frontend
ls -la | grep -E "webpack|craco|react-app"
```

**If found:**
- Check if they're modifying API URLs
- Temporarily rename and redeploy

---

## 🧪 Diagnostic Tests

### Test 1: Check What's Actually Deployed

Visit your Netlify site and run in browser console:
```javascript
// Check environment variable
console.log('BACKEND_URL:', process.env.REACT_APP_BACKEND_URL);

// Check if it's the old build
console.log('Build info:', document.querySelector('script[src*="main"]')?.src);
```

### Test 2: Inspect Deployed JavaScript

1. Visit https://li-ai.org
2. Open DevTools → Sources tab
3. Find `static/js/main.[hash].js`
4. Search for: `api-keys`
5. Look at the URL construction

**If you see:**
```javascript
"/api/settings/api-keys"  // This means old code is deployed!
```

### Test 3: Check Netlify Deploy ID

1. Visit https://li-ai.org
2. Open DevTools → Network tab
3. Look at response headers for any HTML file
4. Find `x-nf-request-id` header
5. Note the deploy ID

Compare with:
1. Netlify Dashboard → Deploys
2. Find deploy with matching ID
3. Check when it was deployed

### Test 4: Force New Deploy with Version Bump

Update `package.json`:
```json
{
  "name": "frontend",
  "version": "0.1.1",  // ← Change this
  ...
}
```

Commit and push:
```bash
git add frontend/package.json
git commit -m "Bump version to force rebuild"
git push
```

---

## 🔧 Nuclear Option: Complete Reset

If nothing else works:

### 1. Delete Netlify Site
1. Netlify Dashboard → Site Settings → General
2. Scroll to "Danger zone"
3. Delete site

### 2. Create New Netlify Site
1. Netlify Dashboard → Add new site
2. Import from Git
3. Connect to your GitHub repo
4. Configure:
   ```
   Base directory: frontend
   Build command: yarn build
   Publish directory: frontend/build
   ```
5. Environment variables:
   ```
   REACT_APP_BACKEND_URL=https://api.li-ai.org
   ```
6. Deploy

### 3. Update Custom Domain
1. After deploy succeeds
2. Add custom domain: li-ai.org
3. Update DNS records

---

## 📋 Step-by-Step Verification Process

### Step 1: Verify GitHub
```bash
cd /app
git log --oneline -1
git show HEAD:frontend/src/components/APIKeyManager.jsx | grep "api.get"
# Should show: api.get('/settings/api-keys')
```

### Step 2: Verify Netlify is Building from GitHub
1. Netlify Dashboard → Deploys → Latest deploy
2. Check "Deploy log"
3. Find git commit hash
4. Compare with Step 1

### Step 3: Check Build Output
In Netlify build logs, search for:
```
Creating an optimized production build...
Compiled successfully!
```

Look for any errors or warnings about environment variables.

### Step 4: Test Deployed Site
1. Visit: https://li-ai.org?v=test
2. Open Console
3. Look for debug output
4. Check Network tab for API call

---

## 🎯 Most Likely Solutions (Ordered by Probability)

### 1. Dashboard Environment Variable (60% probability)
Check Netlify Dashboard → Environment variables
- Variable might have `/api` suffix
- Or might be set differently than netlify.toml

### 2. Wrong Deploy/Branch (20% probability)
- Testing deploy preview instead of production
- Netlify building from wrong branch

### 3. Browser/CDN Cache (15% probability)
- Service worker caching old code
- Edge cache not cleared
- Try incognito mode + query param

### 4. Build Cache (5% probability)
- node_modules/.cache has old build
- Clear with: `rm -rf node_modules/.cache && yarn build`

---

## 🆘 If Nothing Works

**Provide these details:**

1. **Netlify Deploy Log** (last 100 lines)
2. **Git commit hash** from Netlify build log
3. **Your local git log:**
   ```bash
   cd /app && git log --oneline -5
   ```
4. **Netlify Dashboard environment variables** (screenshot)
5. **Browser console output** when visiting site
6. **Deployed JavaScript inspection:**
   - Open site
   - DevTools → Sources
   - Find main.js
   - Search for "api-keys"
   - Screenshot the relevant code

---

## 💡 Quick Sanity Check

Run this to ensure local code is correct:
```bash
cd /app/frontend/src/components
grep -n "api\." APIKeyManager.jsx | grep -E "get|post|delete"
```

**Should output:**
```
86:      const response = await api.get('/settings/api-keys');
119:      await api.post('/settings/api-keys', {
139:      const response = await api.post(`/settings/api-keys/test/${serviceName}`);
160:      await api.delete(`/settings/api-keys/${serviceName}`);
```

**Should NOT contain any `/api/settings` or `/api/api/settings`**

---

**Start with checking the Netlify Dashboard environment variables - that's the most common cause!** 🎯
