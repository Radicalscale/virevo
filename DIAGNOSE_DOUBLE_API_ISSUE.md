# Systematic Diagnosis: Double `/api/api/` Issue

## 🔍 Problem
After deployment to Netlify, URLs still show `/api/api/`:
```
https://api.li-ai.org/api/api/settings/api-keys ❌
```

---

## 🎯 Potential Root Causes

### Cause 1: Environment Variable Has `/api` Suffix ⚠️ MOST LIKELY
**What:** Netlify environment variable includes `/api` at the end

**Check:**
```
Netlify Dashboard → Site Settings → Environment Variables
Look for: REACT_APP_BACKEND_URL

Is it set to:
❌ https://api.li-ai.org/api  <- WRONG
✅ https://api.li-ai.org      <- CORRECT
```

**Why this causes the issue:**
```javascript
// If REACT_APP_BACKEND_URL = "https://api.li-ai.org/api"
const API = `${BACKEND_URL}/api`;  // "https://api.li-ai.org/api/api" ❌
```

**Fix:**
1. Go to Netlify Dashboard
2. Site Settings → Environment Variables
3. Find `REACT_APP_BACKEND_URL`
4. Change to: `https://api.li-ai.org` (NO `/api` at end)
5. Trigger new deploy

---

### Cause 2: Old Code Still in GitHub Repo
**What:** Local changes weren't pushed to GitHub, Netlify builds old code

**Check:**
```bash
# In your local repo
cd /app/frontend/src/components
grep "api.get" APIKeyManager.jsx

# Should show:
api.get('/settings/api-keys')    ✅ CORRECT
api.get('/api/settings/api-keys') ❌ WRONG (old code)
```

**Fix:**
```bash
# If local is correct but GitHub is not
git add frontend/src/components/APIKeyManager.jsx
git commit -m "Fix double /api in API key manager"
git push origin main

# Netlify will auto-deploy
```

---

### Cause 3: Netlify Build Cache
**What:** Netlify is serving cached build with old code

**Check:**
In Netlify deploy logs, look for:
```
Using cached node modules
Build script from cache
```

**Fix:**
1. Netlify Dashboard → Deploys
2. Click "Trigger deploy"
3. Select "Clear cache and deploy site"

---

### Cause 4: Multiple Environment Variable Sources Conflict
**What:** `netlify.toml` and Dashboard env vars conflict

**Check:**
1. `/app/netlify.toml` line 8:
   ```toml
   REACT_APP_BACKEND_URL = "https://api.li-ai.org"
   ```

2. Netlify Dashboard → Environment Variables:
   ```
   REACT_APP_BACKEND_URL = ???
   ```

**Priority:** Dashboard env vars override `netlify.toml`

**Fix:**
Ensure both are consistent OR remove from one location

---

## 🔬 Diagnostic Steps (Do in Order)

### Step 1: Check Netlify Environment Variable

**Action:**
1. Go to Netlify Dashboard
2. Your site → Site Settings → Environment Variables
3. Find `REACT_APP_BACKEND_URL`
4. Take a screenshot

**Expected:**
```
Key: REACT_APP_BACKEND_URL
Value: https://api.li-ai.org
Scope: All
```

**If it shows:**
```
Value: https://api.li-ai.org/api  ← THIS IS THE PROBLEM!
```

**Fix immediately:**
- Edit the variable
- Remove `/api` from the end
- Save
- Trigger new deploy

---

### Step 2: Check Current Deployed Code

**Action:**
Visit your Netlify site and check the built JavaScript:

1. Open browser DevTools (F12)
2. Go to Sources tab
3. Find the minified `main.[hash].js` file
4. Search for: `api-keys`
5. Look at the URL construction

**What to look for:**
```javascript
// If you see:
"/api/api/settings/api-keys"     ❌ OLD CODE
"/api/settings/api-keys"         ✅ NEW CODE (after baseURL)
"/settings/api-keys"             ✅ NEW CODE (component)
```

---

### Step 3: Inspect Network Request in Browser

**Action:**
1. Go to your Netlify site: https://li-ai.org
2. Open DevTools → Network tab
3. Go to Settings → API Keys
4. Watch the network request

**Check:**
```
Request URL: https://api.li-ai.org/api/api/settings/api-keys  ❌
OR
Request URL: https://api.li-ai.org/api/settings/api-keys      ✅
```

**Also check the request headers:**
```
Referer: https://li-ai.org
```

---

### Step 4: Check console.log in api.js

**Temporary debug code:**

Add to `/app/frontend/src/services/api.js`:
```javascript
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

console.log('🔍 DEBUG - BACKEND_URL:', BACKEND_URL);
console.log('🔍 DEBUG - API baseURL:', API);

const apiClient = axios.create({
  baseURL: API,
  ...
});
```

**Deploy and check:**
Open browser console on https://li-ai.org

**Should see:**
```
🔍 DEBUG - BACKEND_URL: https://api.li-ai.org
🔍 DEBUG - API baseURL: https://api.li-ai.org/api
```

**If you see:**
```
🔍 DEBUG - BACKEND_URL: https://api.li-ai.org/api  ← PROBLEM!
🔍 DEBUG - API baseURL: https://api.li-ai.org/api/api  ← DOUBLE /api!
```

---

### Step 5: Check Netlify Deploy Logs

**Action:**
1. Netlify Dashboard → Deploys
2. Click on latest deploy
3. View deploy logs

**Look for:**
```
Build environment variables:
  REACT_APP_BACKEND_URL: https://api.li-ai.org
```

**If it shows:**
```
  REACT_APP_BACKEND_URL: https://api.li-ai.org/api  ← FIX THIS!
```

---

### Step 6: Verify Git Repository

**Action:**
```bash
# Check what's in GitHub
cd /app
git log --oneline -5

# Check if APIKeyManager.jsx changes are committed
git log --oneline --follow frontend/src/components/APIKeyManager.jsx | head -5

# Check current content
git show HEAD:frontend/src/components/APIKeyManager.jsx | grep "api.get"
```

**Should show:**
```javascript
api.get('/settings/api-keys')  ✅
```

**If shows:**
```javascript
api.get('/api/settings/api-keys')  ❌ Need to commit and push
```

---

## 🎯 Most Likely Solution (90% confidence)

Based on the error pattern, **the Netlify environment variable probably has `/api` at the end**.

### Quick Fix:

1. **Go to Netlify Dashboard**
   - Site Settings → Environment Variables

2. **Check `REACT_APP_BACKEND_URL`**
   - Is it: `https://api.li-ai.org/api` ❌

3. **Update to:**
   - `https://api.li-ai.org` (NO `/api`)

4. **Save and redeploy:**
   - Deploys → Trigger deploy

5. **Test:**
   - Visit https://li-ai.org
   - Go to Settings → API Keys
   - Check Network tab: should be `/api/settings/api-keys` ✅

---

## 🔧 Complete Fix Instructions

### Option A: Environment Variable Fix (Most Likely)

```bash
# 1. Check Netlify environment variable
#    Dashboard → Environment Variables → REACT_APP_BACKEND_URL
#    Remove /api from the end if present

# 2. Trigger new deploy
#    Dashboard → Deploys → Trigger deploy → Clear cache and deploy

# 3. Wait 2-3 minutes for build

# 4. Test
#    Visit https://li-ai.org/settings
#    Check Network tab for correct URL
```

### Option B: Code Update + Push

```bash
# If local code is already fixed but not on GitHub:
cd /app
git add frontend/src/components/APIKeyManager.jsx
git commit -m "Fix: Remove double /api prefix in API key manager"
git push origin main

# Netlify auto-deploys in 2-3 minutes
```

### Option C: Nuclear Option (If All Else Fails)

```bash
# 1. Clear everything
cd /app/frontend
rm -rf node_modules build

# 2. Reinstall
yarn install

# 3. Build locally to test
REACT_APP_BACKEND_URL=https://api.li-ai.org yarn build

# 4. Check build output
grep -r "api/api/settings" build/ || echo "✅ No double /api found"

# 5. If local build is clean, push to GitHub
cd /app
git add .
git commit -m "Clean build - fix double API path"
git push

# 6. Force new Netlify deploy
#    Dashboard → Deploys → Clear cache and deploy site
```

---

## ✅ Success Indicators

After fix is applied:

### Browser Network Tab:
```
✅ GET https://api.li-ai.org/api/settings/api-keys 200 OK
❌ NOT: https://api.li-ai.org/api/api/settings/api-keys 404
```

### Browser Console:
```
✅ No 404 errors
✅ API keys load successfully
```

### Netlify Deploy Logs:
```
✅ Build succeeded
✅ Environment: REACT_APP_BACKEND_URL=https://api.li-ai.org
```

---

## 📊 Verification Checklist

- [ ] Netlify env var `REACT_APP_BACKEND_URL` has NO `/api` suffix
- [ ] netlify.toml has correct URL
- [ ] Local code uses `/settings/api-keys` (not `/api/settings/api-keys`)
- [ ] Code is pushed to GitHub
- [ ] Netlify deploy completed successfully
- [ ] Browser shows `/api/settings/api-keys` (not `/api/api/`)
- [ ] API keys load without 404 error

---

## 🆘 If Still Not Working

Share these details:

1. **Screenshot of Netlify environment variables**
2. **Netlify deploy log** (last 50 lines)
3. **Browser console output** (all errors)
4. **Network tab screenshot** showing the failing request
5. **Output of:**
   ```bash
   cd /app/frontend/src/components
   grep -n "api\." APIKeyManager.jsx | head -10
   ```

---

**Start with Step 1: Check Netlify Environment Variable!** That's almost certainly the issue. 🎯
