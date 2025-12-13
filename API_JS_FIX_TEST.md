# Test: Remove /api from api.js

## 🧪 What We Changed

**File:** `/app/frontend/src/services/api.js`
**Line 4:**

```javascript
// BEFORE:
const API = `${BACKEND_URL}/api`;
// = "https://api.li-ai.org/api"

// AFTER:
const API = BACKEND_URL;
// = "https://api.li-ai.org" (NO /api)
```

---

## 🎯 What This Will Reveal

### **Scenario A: Deployed Code Has NO /api Prefix**

If deployed component code calls:
```javascript
api.get('/settings/api-keys')
```

**Combined URL will be:**
```
baseURL + path
= "https://api.li-ai.org" + "/settings/api-keys"
= "https://api.li-ai.org/settings/api-keys" ❌ MISSING /api!
```

**Result:** 404 (because backend needs `/api/settings/api-keys`)

---

### **Scenario B: Deployed Code HAS /api Prefix** ← LIKELY!

If deployed component code calls:
```javascript
api.get('/api/settings/api-keys')
```

**Combined URL will be:**
```
baseURL + path
= "https://api.li-ai.org" + "/api/settings/api-keys"
= "https://api.li-ai.org/api/settings/api-keys" ✅ CORRECT!
```

**Result:** 200 Success! API keys load!

---

## 📊 What Each Result Means

### **If you get 404 after deploying:**
- Deployed code has correct path: `/settings/api-keys`
- Problem is NOT with component code
- Something else is adding the extra `/api`
- Need to investigate Netlify build process

### **If you get 200 after deploying:**
- Deployed code has OLD path: `/api/settings/api-keys` ❌
- Netlify is deploying old JavaScript bundle
- GitHub code is correct but Netlify isn't using it
- Need to force Netlify to rebuild from GitHub

---

## 🔬 How to Test

### **Step 1: Commit and Push**
```bash
cd /app
git add frontend/src/services/api.js
git commit -m "Test: Remove /api from api.js baseURL"
git push origin main
```

### **Step 2: Netlify Deploys**
Wait 2-3 minutes for Netlify to build and deploy.

### **Step 3: Check Browser Console**
Visit: https://li-ai.org/settings

Look for debug output:
```
🔍 API Service Configuration:
  BACKEND_URL: https://api.li-ai.org
  API baseURL: https://api.li-ai.org  ← Should NOT have /api
  Expected: https://api.li-ai.org (NO /api)
```

### **Step 4: Check Network Tab**
Open DevTools → Network tab

**If you see:**
```
GET https://api.li-ai.org/settings/api-keys 404 ❌
```
→ Component code is correct, problem is elsewhere

**If you see:**
```
GET https://api.li-ai.org/api/settings/api-keys 200 ✅
```
→ Deployed component has old code with `/api` prefix!

**If you STILL see:**
```
GET https://api.li-ai.org/api/api/settings/api-keys 404 ❌
```
→ Both baseURL and component have issues (shouldn't happen)

---

## 🎯 Expected Result (High Confidence)

**I predict you'll see:**
```
GET https://api.li-ai.org/api/settings/api-keys 200 ✅
```

**This would confirm:**
1. ✅ Environment variable is correct (no `/api` suffix)
2. ✅ Removing `/api` from api.js Line 4 was the right fix
3. ❌ Netlify WAS deploying old component code with `/api` prefix
4. ✅ Now it will work because: baseURL (no /api) + path (with /api) = correct URL

---

## 📋 Next Steps Based on Results

### **If It Works (200 Success):**
1. ✅ Leave this change as-is
2. ✅ Update all components to use `/api` prefix in their paths
3. ✅ Or update backend to not require `/api` prefix

**Better approach:** Keep `/api` in api.js and fix component code to NOT have `/api` prefix (cleaner separation)

### **If It Still Fails (404 or double /api):**
1. Check Netlify build logs for actual commit deployed
2. Check deployed JavaScript bundle source code
3. Verify Netlify is building from correct branch
4. Clear Netlify cache and force rebuild

---

## 🔍 Why This Test is Valuable

This definitively proves:
- Is the problem in api.js? (adding `/api`)
- Is the problem in component code? (having `/api` prefix)
- Is Netlify deploying old code?

**One of these MUST be true for `/api/api/` to appear.**

---

## ⚠️ Important Notes

**This is a diagnostic test, not the final fix!**

The proper architecture should be:
```javascript
// api.js: Add /api once
const API = `${BACKEND_URL}/api`;

// Components: NO /api prefix
api.get('/settings/api-keys')

// Result: https://api.li-ai.org/api/settings/api-keys ✅
```

But if deployed code has old component code, temporarily removing `/api` from api.js will make it work.

---

## 🚀 Deploy and Test Now

```bash
git add .
git commit -m "Test: Remove /api from api.js to diagnose double /api issue"
git push
```

Then check the results and report back!
