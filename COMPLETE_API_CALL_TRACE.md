# Complete API Call Trace: `/api/api/settings/api-keys`

## 🔍 Exact Call Chain (Step by Step)

### **1. User Action (Browser)**
```
User navigates to: https://li-ai.org/settings
```

---

### **2. React Router (Frontend)**
```javascript
// App.js - React Router matches path
<Route path="/settings" element={
  <PrivateRoute>
    <Sidebar />
    <APIKeyManager />  // ← This component renders
  </PrivateRoute>
} />
```

---

### **3. Component Mount (APIKeyManager.jsx)**
```javascript
// /app/frontend/src/components/APIKeyManager.jsx
// Line 80-82
useEffect(() => {
  loadAPIKeys();  // ← Called on component mount
}, []);
```

---

### **4. loadAPIKeys Function Calls Axios**
```javascript
// Line 84-99
const loadAPIKeys = async () => {
  try {
    // THIS LINE MAKES THE API CALL:
    const response = await api.get('/settings/api-keys');
    //                      ↑          ↑
    //                   axios      path
    //                  instance
    
    const keysMap = {};
    response.data.forEach(key => {
      keysMap[key.service_name] = {
        has_key: key.has_key,
        is_active: key.is_active
      };
    });
    setApiKeys(keysMap);
  } catch (error) {
    console.error('Failed to load API keys:', error);
  }
};
```

**Current GitHub code:** `api.get('/settings/api-keys')` ✅
**Old code (if deployed):** `api.get('/api/settings/api-keys')` ❌

---

### **5. Axios Instance Construction (api.js)**
```javascript
// /app/frontend/src/services/api.js
// Lines 1-13

import axios from 'axios';

// STEP 5A: Read environment variable
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
//                  ↑
//                  This is baked into JavaScript during BUILD TIME
//                  NOT read from server at runtime!

// STEP 5B: Construct API base URL
const API = `${BACKEND_URL}/api`;
//          ↑                  ↑
//    e.g. "https://api.li-ai.org" + "/api"
//    Result: "https://api.li-ai.org/api"

// STEP 5C: Create axios instance
const apiClient = axios.create({
  baseURL: API,  // ← Sets the base URL for ALL requests
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

export default apiClient;
```

---

### **6. Axios Combines baseURL + path**
```javascript
// When component calls: api.get('/settings/api-keys')
// Axios internally does:
const finalURL = baseURL + path;
//               ↑          ↑
//     "https://api.li-ai.org/api" + "/settings/api-keys"
//     Result: "https://api.li-ai.org/api/settings/api-keys" ✅

// OR if old code: api.get('/api/settings/api-keys')
const finalURL = baseURL + path;
//     "https://api.li-ai.org/api" + "/api/settings/api-keys"
//     Result: "https://api.li-ai.org/api/api/settings/api-keys" ❌
```

---

### **7. Browser Makes XMLHttpRequest**
```javascript
// Axios creates XMLHttpRequest:
const xhr = new XMLHttpRequest();
xhr.open('GET', 'https://api.li-ai.org/api/api/settings/api-keys');
//                ↑
//                This is what you're seeing in Network tab!
xhr.setRequestHeader('Content-Type', 'application/json');
xhr.withCredentials = true;  // Includes cookies
xhr.send();
```

---

### **8. Request Goes to Railway (Backend)**
```
DNS Resolution:
  api.li-ai.org → 66.33.22.223 (Railway edge server)
  
HTTP Request:
  GET https://api.li-ai.org/api/api/settings/api-keys
  Host: api.li-ai.org
  Origin: https://li-ai.org
  Cookie: access_token=...
```

---

### **9. Railway Backend Receives Request**
```python
# /app/backend/server.py
# FastAPI router setup

app = FastAPI()
router = APIRouter()

# ALL routes are prefixed with /api
app.include_router(router, prefix="/api")

# So this route becomes: /api/settings/api-keys
@router.get("/settings/api-keys")
async def get_api_keys():
    # This handler would respond to:
    # GET /api/settings/api-keys ✅
    
    # But request is for:
    # GET /api/api/settings/api-keys ❌
    # 
    # No route matches! Returns 404
    return {"detail": "Not Found"}
```

---

## 🎯 Where the `/api/api/` Comes From

### **Possibility 1: Environment Variable Has `/api` Suffix**

**During Netlify Build:**
```javascript
// If Netlify env var is:
REACT_APP_BACKEND_URL = "https://api.li-ai.org/api"  // ❌ WRONG!

// Then api.js creates:
const API = `${BACKEND_URL}/api`;
//        = "https://api.li-ai.org/api" + "/api"
//        = "https://api.li-ai.org/api/api"  // ❌ DOUBLE /api!

// Component calls:
api.get('/settings/api-keys')

// Axios combines:
// "https://api.li-ai.org/api/api" + "/settings/api-keys"
// = "https://api.li-ai.org/api/api/settings/api-keys"  // ❌
```

---

### **Possibility 2: Deployed Code is Old**

**If Netlify deployed OLD JavaScript bundle:**
```javascript
// Old code in APIKeyManager.jsx:
api.get('/api/settings/api-keys')  // ❌ Has /api prefix

// Combined with correct baseURL:
// "https://api.li-ai.org/api" + "/api/settings/api-keys"
// = "https://api.li-ai.org/api/api/settings/api-keys"  // ❌
```

---

## 🔬 Exact Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ NETLIFY BUILD TIME (GitHub → Netlify)                       │
│                                                              │
│ 1. Netlify reads environment variable:                      │
│    Source: Dashboard > netlify.toml                         │
│    Value: REACT_APP_BACKEND_URL = ???                      │
│                                                              │
│ 2. webpack/Create React App builds JavaScript:              │
│    - Replaces process.env.REACT_APP_BACKEND_URL with value │
│    - Bundles into main.[hash].js                            │
│    - THIS IS PERMANENT until next build!                    │
│                                                              │
│ 3. Deploys to Netlify CDN:                                  │
│    - JavaScript contains hardcoded URL                      │
│    - No way to change without rebuilding                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ BROWSER RUNTIME (User visits site)                          │
│                                                              │
│ 1. Browser downloads main.[hash].js from Netlify CDN        │
│                                                              │
│ 2. JavaScript executes:                                     │
│    const BACKEND_URL = "https://api.li-ai.org/api";  // ❌? │
│    const API = BACKEND_URL + "/api";                        │
│    // = "https://api.li-ai.org/api/api"                     │
│                                                              │
│ 3. Component calls: api.get('/settings/api-keys')           │
│                                                              │
│ 4. Axios creates URL:                                       │
│    baseURL + path                                           │
│    = "https://api.li-ai.org/api/api/settings/api-keys"  ❌ │
│                                                              │
│ 5. XMLHttpRequest sent to Railway                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ RAILWAY BACKEND (FastAPI)                                   │
│                                                              │
│ 1. Receives: GET /api/api/settings/api-keys                │
│                                                              │
│ 2. Checks registered routes:                                │
│    ✅ /api/settings/api-keys (exists)                       │
│    ❌ /api/api/settings/api-keys (doesn't exist)            │
│                                                              │
│ 3. Returns 404 Not Found                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ BROWSER (Error handling)                                    │
│                                                              │
│ 1. Axios receives 404 response                              │
│                                                              │
│ 2. Throws AxiosError                                        │
│                                                              │
│ 3. Caught in APIKeyManager catch block:                     │
│    console.error('Failed to load API keys:', error);        │
│                                                              │
│ 4. User sees error in console                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ What MongoDB/Redis Have to Do With This

**SHORT ANSWER: NOTHING!**

This is purely a frontend URL construction issue:
- ❌ Not related to MongoDB (database not even queried)
- ❌ Not related to Redis (backend not reached)
- ❌ Not related to Railway backend logic (404 before handler runs)

The request **never reaches** the backend handler that would query MongoDB/Redis.

**Timeline:**
```
1. Browser constructs URL ❌ (Wrong here!)
2. Sends request to Railway
3. Railway routing: No matching route
4. Returns 404
5. MongoDB/Redis never touched
```

---

## 🎯 Exact Source of the Problem

The `_url: "https://api.li-ai.org/api/api/settings/api-keys"` you see is created by:

### **Line-by-Line Trace:**

```javascript
// FILE: frontend/src/components/APIKeyManager.jsx
// LINE: 86 (in your deployed bundle)

const response = await api.get('/api/settings/api-keys');
//                      ↑          ↑
//                   (from)    (contains /api ❌)
//                   api.js

// FILE: frontend/src/services/api.js
// LINE: 4

const API = `${BACKEND_URL}/api`;
//          ↑
//    Value at build time: "https://api.li-ai.org/api"
//    (if BACKEND_URL = "https://api.li-ai.org/api", then API = ".../api/api")

// FILE: frontend/src/services/api.js
// LINE: 7-10

const apiClient = axios.create({
  baseURL: API,  // ← "https://api.li-ai.org/api" or "https://api.li-ai.org/api/api"
});

// AXIOS INTERNAL (node_modules/axios):
function request(url) {
  const fullURL = this.baseURL + url;
  //              ↑               ↑
  //    "https://api.li-ai.org/api/api" + "/settings/api-keys"
  //    = "https://api.li-ai.org/api/api/settings/api-keys" ❌
  
  return new XMLHttpRequest().open('GET', fullURL);
}
```

---

## 🔧 How to Find the Exact Problem

### **Step 1: Check What Was Built**

Run in browser console on https://li-ai.org:
```javascript
// This will show what value was baked into the build
console.log('BACKEND_URL:', process.env.REACT_APP_BACKEND_URL);
```

**If it shows:**
- `https://api.li-ai.org` ✅ Correct
- `https://api.li-ai.org/api` ❌ Environment variable is wrong!
- `undefined` ❌ Variable not set!

---

### **Step 2: Inspect Deployed JavaScript**

1. Visit https://li-ai.org
2. Open DevTools → Sources
3. Find: `static/js/main.[hash].js`
4. Press Ctrl+F, search for: `settings/api-keys`
5. Look at the surrounding code

**If you see:**
```javascript
api.get('/api/settings/api-keys')  // ❌ OLD CODE
```

**Should see:**
```javascript
api.get('/settings/api-keys')  // ✅ NEW CODE
```

---

### **Step 3: Check Netlify Build**

1. Netlify Dashboard → Deploys → Latest
2. Click "Build log"
3. Search for: `REACT_APP_BACKEND_URL`
4. See what value was used during build

**Should see:**
```
Environment variables:
  REACT_APP_BACKEND_URL: https://api.li-ai.org
```

**Should NOT see:**
```
  REACT_APP_BACKEND_URL: https://api.li-ai.org/api
```

---

### **Step 4: Compare Git Commits**

```bash
# Your local repo
cd /app
git log --oneline -1

# Check Netlify build log for commit hash
# They should match!
```

---

## ✅ Definitive Answer

**The line `_url: "https://api.li-ai.org/api/api/settings/api-keys"` is generated by:**

1. **Primary Source:** JavaScript bundle deployed on Netlify CDN
2. **Built from:** GitHub repository at specific commit
3. **Using:** Environment variable `REACT_APP_BACKEND_URL` from Netlify Dashboard or netlify.toml
4. **Executed by:** Axios library combining `baseURL` + `path`

**MongoDB/Redis/Railway backend have ZERO involvement** - the URL is wrong before the request even leaves the browser.

**The fix MUST happen at BUILD TIME on Netlify, not at runtime.**

---

## 🎯 Action Items

1. **Check Netlify Dashboard → Environment variables**
   - Is `REACT_APP_BACKEND_URL` listed?
   - Does it have `/api` at the end?

2. **Check Netlify build logs**
   - What commit hash was used?
   - What was the `REACT_APP_BACKEND_URL` value during build?

3. **Inspect deployed JavaScript**
   - What does the built code actually contain?
   - Old code or new code?

**These 3 checks will definitively identify where the `/api/api/` is coming from!** 🎯
