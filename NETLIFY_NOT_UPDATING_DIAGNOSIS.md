# CRITICAL ISSUE: Netlify Not Deploying Latest Code

## 🚨 Problem Confirmed

Railway logs show requests STILL coming in as:
```
GET /api/api/settings/api-keys
```

Even though we:
1. ✅ Removed `/api` from api.js (GitHub confirmed)
2. ✅ Pushed to GitHub
3. ✅ Cleared Netlify cache
4. ✅ Triggered new deploy

**Conclusion:** Netlify is serving OLD JavaScript bundle, not building from latest GitHub code!

---

## 🔍 Possible Causes

### 1. Wrong Branch Being Built
**Check:**
- Netlify Dashboard → Site Settings → Build & deploy → Continuous Deployment
- Look for "Branch deploy" or "Production branch"
- Is it set to `main` or `master`?

**Your local branch:**
```bash
cd /app && git branch --show-current
```

If Netlify builds `master` but you're pushing to `main` (or vice versa), it won't update!

---

### 2. Deploy Preview vs Production
**Check:**
- Are you testing the **Production** deploy URL?
- Or a **Deploy Preview** URL (branch preview)?

Deploy previews don't auto-update production!

**Production URL:** Should be your custom domain (li-ai.org)
**Deploy Preview:** Usually has a random subdomain

---

### 3. Netlify Connected to Wrong Repository
**Check:**
- Netlify Dashboard → Site Settings → Build & deploy → Link repository
- Is it pointing to YOUR GitHub repo?
- Or someone else's fork?

---

### 4. Build Command Not Running
**Check Netlify deploy logs:**
1. Netlify Dashboard → Deploys → Latest deploy
2. Click to expand logs
3. Search for: "yarn build" or "npm run build"
4. Did it actually run?
5. What files were generated?

**Look for:**
```
Creating an optimized production build...
Compiled successfully!
```

If missing, build might be failing silently.

---

### 5. CDN/Edge Caching Beyond Netlify
**Even after clearing Netlify cache:**
- Browser cache
- Service workers
- Netlify's edge CDN
- Cloudflare (if using)

---

## 🧪 Definitive Tests

### Test 1: Check What Netlify Actually Built

Visit your site and run in console:
```javascript
// Check the actual deployed code
fetch('/static/js/main.js')
  .then(r => r.text())
  .then(code => {
    console.log('Searching for api.js baseURL construction...');
    if (code.includes('BACKEND_URL}/api')) {
      console.log('❌ OLD CODE: Found ${BACKEND_URL}/api');
    } else if (code.includes('BACKEND_URL;')) {
      console.log('✅ NEW CODE: Found BACKEND_URL without /api');
    } else {
      console.log('⚠️ Could not find the code (might be minified differently)');
    }
  });
```

---

### Test 2: Check Build Timestamp

Create a version file:

**File:** `/app/frontend/public/version.txt`
```
Build: 2025-11-13 12:30:00
Commit: [latest-commit-hash]
Change: Removed /api from api.js Line 4
```

After deploy, visit: `https://li-ai.org/version.txt`

If it's old or doesn't exist, Netlify isn't deploying latest!

---

### Test 3: Check Netlify Deploy Commit Hash

1. Netlify Dashboard → Deploys → Latest deploy
2. Look for "Deploy summary" or "Git info"
3. Note the commit hash

Compare with:
```bash
cd /app && git log --oneline -1
```

Do they match?

---

### Test 4: Force Redeploy with Dummy Change

Sometimes Netlify doesn't detect changes. Force it:

**File:** `/app/frontend/package.json`
```json
{
  "name": "frontend",
  "version": "0.1.2",  // ← Change this (was 0.1.1 or 0.1.0)
  ...
}
```

Commit and push. This ALWAYS triggers a rebuild.

---

## 🎯 Immediate Actions

### Action 1: Verify Netlify Is Building from Correct Commit

```bash
# Get your latest commit hash
cd /app && git log --oneline -1

# Output: abc1234 auto-commit for xxx-xxx
```

Then check Netlify deploy logs - does it show the same commit hash?

---

### Action 2: Add Build Verification File

```bash
# Create version file
cd /app
echo "Build Time: $(date)" > frontend/public/version.txt
echo "Commit: $(git log --oneline -1)" >> frontend/public/version.txt

git add frontend/public/version.txt
git commit -m "Add build verification file"
git push
```

After deploy, visit: `https://li-ai.org/version.txt`

If you see your current timestamp/commit, Netlify IS building latest.
If you see old timestamp or 404, Netlify is NOT building latest.

---

### Action 3: Check Netlify Build Settings

**Go to:** Netlify Dashboard → Site Settings → Build & deploy

**Verify:**
```
Repository: [Your GitHub repo URL]
Base directory: frontend
Build command: yarn build
Publish directory: frontend/build
Production branch: main (or master)
```

If ANY of these are wrong, Netlify won't build correctly!

---

### Action 4: Manual Deploy from CLI

Bypass Netlify's GitHub integration:

```bash
cd /app/frontend

# Build locally
REACT_APP_BACKEND_URL=https://api.li-ai.org yarn build

# Install Netlify CLI (if not installed)
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --prod --dir=build
```

This uploads your LOCAL build directly to Netlify.

If this works but GitHub deploys don't, the problem is Netlify's GitHub integration!

---

## 🔥 Nuclear Option: Delete & Recreate Netlify Site

If nothing works:

1. Note your custom domain settings
2. Delete the Netlify site
3. Create new site from GitHub
4. Re-add custom domain
5. Set environment variables
6. Deploy

Sometimes Netlify's internal state gets corrupted.

---

## 📊 Diagnostic Checklist

Run through these and report findings:

- [ ] Check Netlify is building from correct branch
- [ ] Check Netlify deploy logs show latest commit hash
- [ ] Check Netlify build command is running
- [ ] Check browser console shows debug output from api.js
- [ ] Check Network tab shows actual request URL
- [ ] Try incognito mode (rules out browser cache)
- [ ] Try different browser (rules out browser issues)
- [ ] Check service worker is unregistered
- [ ] Check `version.txt` file shows latest build time
- [ ] Try manual deploy from CLI

---

## 🎯 Most Likely Issue

Based on the symptoms, I believe:

**Netlify is connected to the WRONG repository or WRONG branch.**

Or:

**Netlify's GitHub webhook is broken and not triggering builds on push.**

---

## 🚀 Quick Fix Attempt

Create a VERY obvious change that can't be missed:

**File:** `/app/frontend/src/App.js`

Add at the top of the render:
```javascript
function App() {
  return (
    <div className="App bg-gray-900 min-h-screen">
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        background: 'red',
        color: 'white',
        padding: '10px',
        zIndex: 9999
      }}>
        BUILD TEST: {new Date().toISOString()}
      </div>
      ...
```

If you deploy and DON'T see this red banner on https://li-ai.org, Netlify is definitely not deploying your code!

---

Please check:
1. What branch is Netlify building from?
2. What commit hash does the latest Netlify deploy show?
3. What is your latest local commit hash?
4. Are these the same?
