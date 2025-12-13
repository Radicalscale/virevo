# ULTIMATE DETAILED TRACE: `/api/api/settings/api-keys` Request

## 🎬 COMPLETE EXECUTION FLOW WITH EXACT FILES AND LINE NUMBERS

---

## Phase 1: Netlify Build Time (GitHub → Netlify CDN)

### **File: `netlify.toml`**
**Location:** `/app/netlify.toml`

```toml
Line 1:  [build]
Line 2:    base = "frontend"
Line 3:    command = "yarn build"
Line 4:    publish = "build"
Line 5:    
Line 6:  [build.environment]
Line 7:    NODE_VERSION = "20"
Line 8:    REACT_APP_BACKEND_URL = "https://api.li-ai.org"
         ↑
         THIS VALUE IS READ BY NETLIFY BUILD PROCESS
```

**What Happens:**
1. Netlify reads `netlify.toml` OR checks Dashboard environment variables
2. **IMPORTANT:** Dashboard env vars OVERRIDE netlify.toml!
3. Sets `REACT_APP_BACKEND_URL` for webpack build

---

### **Build Process: webpack/Create React App**

**Tool:** `react-scripts build` (called by `yarn build`)

**What It Does:**
1. Reads all environment variables starting with `REACT_APP_`
2. Finds: `REACT_APP_BACKEND_URL = "https://api.li-ai.org"` (or whatever value)
3. Performs string replacement in JavaScript code
4. Replaces ALL instances of `process.env.REACT_APP_BACKEND_URL` with the actual string value

**Example Transformation:**
```javascript
// BEFORE BUILD (source code):
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// AFTER BUILD (bundled JavaScript):
const BACKEND_URL = "https://api.li-ai.org";
```

5. Bundles into `/build/static/js/main.[hash].js`
6. **THIS IS NOW PERMANENT** - can't be changed without rebuilding

---

## Phase 2: Browser Load Time (User Visits Site)

### **Step 1: HTML Load**
**File:** Netlify serves `/build/index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Andromeda AI Calls</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
    <script defer="defer" src="/static/js/main.3eb5b935.js"></script>
    ↑
    THIS CONTAINS ALL YOUR REACT CODE, BUNDLED
  </body>
</html>
```

---

### **Step 2: JavaScript Execution Starts**
**File:** `/build/static/js/main.[hash].js` (minified bundle)

Browser downloads and executes this file.

---

### **Step 3: React Root Render**
**File:** `/app/frontend/src/index.js`

```javascript
Line 1:  import React from "react";
Line 2:  import ReactDOM from "react-dom/client";
Line 3:  import "@/index.css";
Line 4:  import App from "@/App";
         ↑
         IMPORTS THE APP COMPONENT

Line 6:  const root = ReactDOM.createRoot(document.getElementById("root"));
         ↑
         CREATES REACT ROOT AT <div id="root">

Line 7:  root.render(
Line 8:    <React.StrictMode>
Line 9:      <App />
         ↑
         RENDERS APP COMPONENT
Line 10:   </React.StrictMode>,
Line 11: );
```

**What Happens:**
1. React finds `<div id="root">` in HTML
2. Creates React root
3. Calls `App` component's render function

---

### **Step 4: App Component Renders**
**File:** `/app/frontend/src/App.js`

```javascript
Line 1:  import "./App.css";
Line 2:  import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
Line 3:  import { AuthProvider } from "./contexts/AuthContext";
         ↑
         IMPORTS AUTH CONTEXT (checks if user is logged in)

Line 11: import APIKeyManager from "./components/APIKeyManager";
         ↑
         IMPORTS THE API KEY MANAGER COMPONENT

Line 22: function App() {
Line 23:   return (
Line 24:     <div className="App bg-gray-900 min-h-screen">
Line 26:       <BrowserRouter>
         ↑
         INITIALIZES REACT ROUTER (reads URL: https://li-ai.org/settings)

Line 27:         <AuthProvider>
         ↑
         WRAPS APP IN AUTH CONTEXT (provides user authentication state)

Line 53:                       <Route path="/settings" element={<APIKeyManager />} />
         ↑
         REACT ROUTER MATCHES URL "/settings" AND RENDERS APIKeyManager
```

**What Happens:**
1. React Router reads browser URL: `https://li-ai.org/settings`
2. Matches route definition on Line 53
3. Decides to render `<APIKeyManager />` component

---

### **Step 5: APIKeyManager Component Initialization**
**File:** `/app/frontend/src/components/APIKeyManager.jsx`

```javascript
Line 1:  import React, { useState, useEffect } from 'react';
Line 2:  import api from '../services/api';
         ↑
         IMPORTS THE AXIOS INSTANCE FROM api.js
         THIS IS CRITICAL - IT CONTAINS THE baseURL!

Line 72: function APIKeyManager() {
Line 73:   const [apiKeys, setApiKeys] = useState({});
Line 74:   const [editingKey, setEditingKey] = useState(null);
Line 75:   const [keyValue, setKeyValue] = useState('');
Line 76:   const [loading, setLoading] = useState(false);
Line 77:   const [testing, setTesting] = useState({});
Line 78:   const [message, setMessage] = useState({ type: '', text: '' });
         ↑
         COMPONENT STATE INITIALIZATION

Line 80:   useEffect(() => {
Line 81:     loadAPIKeys();
         ↑
         REACT useEffect HOOK - RUNS AFTER COMPONENT MOUNTS
         THIS TRIGGERS THE API CALL!
Line 82:   }, []);
         ↑
         EMPTY DEPENDENCY ARRAY = RUN ONLY ONCE ON MOUNT
```

**What Happens:**
1. Component renders for the first time
2. React calls the `useEffect` hook (Line 80-82)
3. `useEffect` calls `loadAPIKeys()` function

---

### **Step 6: loadAPIKeys Function Execution**
**File:** `/app/frontend/src/components/APIKeyManager.jsx`

```javascript
Line 84:  const loadAPIKeys = async () => {
Line 85:    try {
Line 86:      const response = await api.get('/settings/api-keys');
         ↑
         THIS IS THE CRITICAL LINE THAT MAKES THE API CALL!
         
         BREAKDOWN:
         - `api` is the imported axios instance from '../services/api'
         - `.get()` is axios method for HTTP GET request
         - '/settings/api-keys' is the PATH (NOT full URL)
         
         AT THIS POINT, EXECUTION JUMPS TO api.js TO CONSTRUCT FULL URL

Line 87:      const keysMap = {};
Line 88:      response.data.forEach(key => {
Line 89:        keysMap[key.service_name] = {
Line 90:          has_key: key.has_key,
Line 91:          is_active: key.is_active
Line 92:        };
Line 93:      });
Line 94:      setApiKeys(keysMap);
         ↑
         IF REQUEST SUCCEEDS, UPDATE COMPONENT STATE

Line 95:    } catch (error) {
Line 96:      console.error('Failed to load API keys:', error);
         ↑
         IF REQUEST FAILS (404), THIS ERROR IS LOGGED
Line 97:      showMessage('error', 'Failed to load API keys');
Line 98:    }
Line 99:  };
```

---

### **Step 7: Axios Instance Configuration**
**File:** `/app/frontend/src/services/api.js`

**EXECUTION FLOW:**

```javascript
Line 1:  import axios from 'axios';
         ↑
         IMPORTS AXIOS LIBRARY FROM node_modules

Line 3:  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
         ↑
         CRITICAL LINE!
         
         AT BUILD TIME, webpack replaced this with actual value:
         
         OPTION A (CORRECT):
         const BACKEND_URL = "https://api.li-ai.org";
         
         OPTION B (WRONG - causes /api/api/):
         const BACKEND_URL = "https://api.li-ai.org/api";
         
         THIS VALUE WAS BAKED IN DURING NETLIFY BUILD!
         CAN'T BE CHANGED AT RUNTIME!

Line 4:  const API = `${BACKEND_URL}/api`;
         ↑
         CONSTRUCTS API BASE URL BY ADDING /api
         
         OPTION A (CORRECT):
         const API = "https://api.li-ai.org" + "/api"
                   = "https://api.li-ai.org/api" ✅
         
         OPTION B (WRONG):
         const API = "https://api.li-ai.org/api" + "/api"
                   = "https://api.li-ai.org/api/api" ❌

Line 7:  console.log('🔍 API Service Configuration:');
Line 8:  console.log('  BACKEND_URL:', BACKEND_URL);
Line 9:  console.log('  API baseURL:', API);
         ↑
         DEBUG OUTPUT - CHECK BROWSER CONSOLE FOR THESE LOGS!

Line 13: const apiClient = axios.create({
Line 14:   baseURL: API,
         ↑
         SETS THE BASE URL FOR ALL AXIOS REQUESTS
         
         IF API = "https://api.li-ai.org/api/api" ❌
         THEN ALL REQUESTS WILL START WITH THIS!

Line 15:   headers: {
Line 16:     'Content-Type': 'application/json',
Line 17:   },
Line 18:   withCredentials: true,
         ↑
         INCLUDES COOKIES IN REQUESTS (for auth token)
Line 19: });

Line 76: export default apiClient;
         ↑
         EXPORTS THE CONFIGURED AXIOS INSTANCE
         THIS IS WHAT WAS IMPORTED AS `api` IN APIKeyManager.jsx Line 2
```

**What Happens:**
1. This file executes ONCE when first imported
2. Reads `BACKEND_URL` (already replaced by webpack with actual value)
3. Constructs `API` base URL by adding `/api`
4. Creates axios instance with this base URL
5. Exports it

---

### **Step 8: Axios Request Construction**
**File:** `node_modules/axios/lib/core/Axios.js` (Axios library internal)

**When you call:** `api.get('/settings/api-keys')`

**Axios internally does this:**

```javascript
// Pseudo-code showing Axios internals
class Axios {
  constructor(config) {
    this.defaults = config;  // { baseURL: "https://api.li-ai.org/api/api" }
  }
  
  get(url, config) {
    return this.request({
      method: 'GET',
      url: url,  // "/settings/api-keys"
      ...config
    });
  }
  
  request(config) {
    // Merge baseURL with url
    const fullURL = this.buildURL(this.defaults.baseURL, config.url);
    //              ↓
    //              buildURL("https://api.li-ai.org/api/api", "/settings/api-keys")
    //              = "https://api.li-ai.org/api/api/settings/api-keys" ❌
    
    // Create XMLHttpRequest
    const xhr = new XMLHttpRequest();
    xhr.open(config.method, fullURL);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.withCredentials = true;
    xhr.send();
    
    return new Promise((resolve, reject) => {
      xhr.onload = () => resolve(xhr.response);
      xhr.onerror = () => reject(new Error('Request failed'));
    });
  }
  
  buildURL(baseURL, url) {
    // If url is absolute (starts with http), use it
    if (url.startsWith('http')) return url;
    
    // Otherwise, combine baseURL + url
    return baseURL + url;
    //     ↑          ↑
    //     "https://api.li-ai.org/api/api" + "/settings/api-keys"
    //     = "https://api.li-ai.org/api/api/settings/api-keys" ❌
  }
}
```

**What Happens:**
1. Axios receives path: `/settings/api-keys`
2. Reads configured `baseURL`: `"https://api.li-ai.org/api/api"` (if wrong)
3. Concatenates: `baseURL + path`
4. Result: `"https://api.li-ai.org/api/api/settings/api-keys"` ❌
5. Creates XMLHttpRequest with this URL

---

### **Step 9: XMLHttpRequest Creation**
**Browser API:** `XMLHttpRequest` (native browser object)

```javascript
// Axios creates this internally:
const xhr = new XMLHttpRequest();

xhr.open('GET', 'https://api.li-ai.org/api/api/settings/api-keys');
//       ↑      ↑
//       method  FULL URL (WRONG!)

xhr.setRequestHeader('Content-Type', 'application/json');
xhr.setRequestHeader('Origin', 'https://li-ai.org');

// Include cookies (access_token for authentication)
xhr.withCredentials = true;

xhr.send();
```

**What You See in Network Tab:**
```
Request URL: https://api.li-ai.org/api/api/settings/api-keys
Request Method: GET
Status Code: 404 Not Found

Request Headers:
  :authority: api.li-ai.org
  :method: GET
  :path: /api/api/settings/api-keys  ← THIS IS THE PROBLEM!
  :scheme: https
  accept: application/json, text/plain, */*
  content-type: application/json
  cookie: access_token=eyJhbGciOiJIUz...
  origin: https://li-ai.org
```

---

## Phase 3: Network Request (Browser → Railway)

### **Step 10: DNS Resolution**

```
Browser asks: "What IP is api.li-ai.org?"
DNS responds: "66.33.22.223" (Railway edge server)
```

---

### **Step 11: HTTP Request Sent**

```http
GET /api/api/settings/api-keys HTTP/1.1
Host: api.li-ai.org
Origin: https://li-ai.org
Content-Type: application/json
Cookie: access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: application/json, text/plain, */*
Referer: https://li-ai.org/settings
User-Agent: Mozilla/5.0...
```

**What Happens:**
1. TCP connection established to 66.33.22.223:443
2. TLS/SSL handshake (HTTPS)
3. HTTP request sent

---

## Phase 4: Railway Backend Processing

### **Step 12: Railway Edge Server**

**Server:** Railway edge server (reverse proxy)

```
Railway Edge (66.33.22.223)
  ↓
Checks domain: api.li-ai.org ✅
  ↓
Routes to your backend container
```

---

### **Step 13: FastAPI Backend Receives Request**
**File:** `/app/backend/server.py`

**FastAPI Router Configuration:**

```python
Line ~50:  app = FastAPI()
Line ~51:  router = APIRouter()

Line ~100: app.include_router(router, prefix="/api")
           ↑
           ALL ROUTES ARE PREFIXED WITH /api
           
           This means:
           - @router.get("/settings/api-keys") 
           - Becomes: /api/settings/api-keys ✅

Line ~500: @router.get("/settings/api-keys")
           async def get_api_keys(
               current_user: User = Depends(get_current_user)
           ):
           ↑
           THIS HANDLER WOULD RESPOND TO:
           GET /api/settings/api-keys ✅
           
           BUT REQUEST IS FOR:
           GET /api/api/settings/api-keys ❌
```

**What Happens:**
1. FastAPI receives request: `GET /api/api/settings/api-keys`
2. Checks registered routes:
   - `/api/settings/api-keys` ✅ EXISTS
   - `/api/agents` ✅ EXISTS
   - `/api/calls` ✅ EXISTS
   - `/api/api/settings/api-keys` ❌ DOESN'T EXIST!
3. No route matches
4. FastAPI returns 404 Not Found

**Response:**
```python
# FastAPI automatically generates this response:
return JSONResponse(
    status_code=404,
    content={"detail": "Not Found"}
)
```

---

### **Step 14: HTTP Response Sent Back**

```http
HTTP/1.1 404 Not Found
Content-Type: application/json
Content-Length: 22
Access-Control-Allow-Origin: https://li-ai.org
Access-Control-Allow-Credentials: true

{"detail":"Not Found"}
```

---

## Phase 5: Browser Response Handling

### **Step 15: XMLHttpRequest Receives Response**

```javascript
// Axios internal code:
xhr.onload = function() {
  if (xhr.status >= 200 && xhr.status < 300) {
    resolve(xhr.response);  // Success
  } else {
    reject(new AxiosError(
      'Request failed with status code ' + xhr.status,
      xhr
    ));  // ← THIS HAPPENS (404 error)
  }
};
```

---

### **Step 16: Error Caught in APIKeyManager**
**File:** `/app/frontend/src/components/APIKeyManager.jsx`

```javascript
Line 84:  const loadAPIKeys = async () => {
Line 85:    try {
Line 86:      const response = await api.get('/settings/api-keys');
           // ... (would execute if successful)
Line 95:    } catch (error) {
           ↑
           EXECUTION JUMPS HERE BECAUSE REQUEST FAILED

Line 96:      console.error('Failed to load API keys:', error);
           ↑
           LOGS ERROR TO BROWSER CONSOLE
           
           error = AxiosError {
             message: 'Request failed with status code 404',
             code: 'ERR_BAD_REQUEST',
             config: { url: '/settings/api-keys', baseURL: 'https://api.li-ai.org/api/api', ... },
             request: XMLHttpRequest { _url: 'https://api.li-ai.org/api/api/settings/api-keys', ... },
             response: { status: 404, data: {detail: 'Not Found'}, ... }
           }

Line 97:      showMessage('error', 'Failed to load API keys');
           ↑
           SHOWS ERROR MESSAGE TO USER
Line 98:    }
Line 99:  };
```

---

### **Step 17: Error Displayed in Browser**

**Console Output:**
```
Failed to load API keys: AxiosError
  code: "ERR_BAD_REQUEST"
  message: "Request failed with status code 404"
  request: XMLHttpRequest
    _url: "https://api.li-ai.org/api/api/settings/api-keys" ← THE PROBLEM URL!
    status: 404
```

**UI:**
```
[!] Failed to load API keys
```

---

## 🎯 MongoDB/Redis Role: NONE!

**Why MongoDB/Redis Are NOT Involved:**

```
REQUEST PATH:
Browser → Constructs URL ❌ (ERROR HAPPENS HERE)
       → Sends to Railway
       → Railway routes to FastAPI
       → FastAPI checks routes → No match
       → Returns 404
       
MongoDB/Redis would only be accessed if:
1. Request reaches correct route ✅
2. Authentication passes ✅
3. Handler function executes ✅
   
None of this happens because request fails at routing!
```

**MongoDB Query (Never Executed):**
```python
# This code in server.py is NEVER reached:
@router.get("/settings/api-keys")
async def get_api_keys(current_user: User = Depends(get_current_user)):
    # Would query MongoDB:
    keys = await db.api_keys.find({"user_id": current_user.id}).to_list(100)
    # ↑ NEVER EXECUTES because route doesn't match
```

**Redis (Never Accessed):**
- Redis is only used for call session state
- Not involved in API key retrieval at all

---

## 🔬 Where the `/api/api/` Originates

### **Scenario A: Environment Variable Has `/api` Suffix**

```javascript
// During Netlify build:
REACT_APP_BACKEND_URL = "https://api.li-ai.org/api"  ❌ WRONG!

// In api.js Line 3:
const BACKEND_URL = "https://api.li-ai.org/api";  // (from env var)

// In api.js Line 4:
const API = `${BACKEND_URL}/api`;
          = "https://api.li-ai.org/api" + "/api"
          = "https://api.li-ai.org/api/api"  ❌ DOUBLE /api!

// Axios combines:
baseURL + path = "https://api.li-ai.org/api/api" + "/settings/api-keys"
               = "https://api.li-ai.org/api/api/settings/api-keys"  ❌
```

---

### **Scenario B: Old Code Deployed**

```javascript
// If Netlify deployed old version of APIKeyManager.jsx:

// OLD CODE (Line 86):
const response = await api.get('/api/settings/api-keys');  ❌ Has /api prefix

// Combined with correct baseURL:
baseURL + path = "https://api.li-ai.org/api" + "/api/settings/api-keys"
               = "https://api.li-ai.org/api/api/settings/api-keys"  ❌
```

---

## 📊 Summary Table

| Step | File | Line | What Happens | Output |
|------|------|------|-------------|---------|
| 1 | `netlify.toml` | 8 | Sets `REACT_APP_BACKEND_URL` | `"https://api.li-ai.org"` or `"https://api.li-ai.org/api"` |
| 2 | webpack build | N/A | Replaces env var in code | Permanent value in bundle |
| 3 | `index.js` | 9 | Renders App | React starts |
| 4 | `App.js` | 53 | Routes to `/settings` | APIKeyManager renders |
| 5 | `APIKeyManager.jsx` | 81 | useEffect calls loadAPIKeys | API call triggered |
| 6 | `APIKeyManager.jsx` | 86 | `api.get('/settings/api-keys')` | Axios request |
| 7 | `api.js` | 3 | Reads BACKEND_URL | `"https://api.li-ai.org/api"` ❌? |
| 8 | `api.js` | 4 | Adds `/api` | `"https://api.li-ai.org/api/api"` ❌? |
| 9 | `api.js` | 14 | Sets baseURL | Axios configured |
| 10 | Axios lib | N/A | Combines baseURL + path | `"https://api.li-ai.org/api/api/settings/api-keys"` ❌ |
| 11 | Browser | N/A | Creates XMLHttpRequest | HTTP request |
| 12 | Network | N/A | DNS + TCP + TLS | Connection established |
| 13 | Railway | N/A | Routes to backend | Request received |
| 14 | `server.py` | ~100 | Checks routes | No match for `/api/api/settings/api-keys` |
| 15 | FastAPI | N/A | Returns 404 | `{"detail":"Not Found"}` |
| 16 | Axios | N/A | Throws AxiosError | Promise rejected |
| 17 | `APIKeyManager.jsx` | 96 | Catches error | Logs to console |
| 18 | `APIKeyManager.jsx` | 97 | Shows error message | User sees error |

---

## 🎯 Definitive Answer

**The line `_url: "https://api.li-ai.org/api/api/settings/api-keys"` is generated at:**

**File:** `node_modules/axios/lib/core/Axios.js` (Axios library)
**Triggered by:** `/app/frontend/src/components/APIKeyManager.jsx` Line 86
**Using values from:** `/app/frontend/src/services/api.js` Lines 3-4
**Which were set at:** Netlify build time from environment variable

**The source value comes from:**
1. **Netlify Dashboard → Environment variables → `REACT_APP_BACKEND_URL`** (if set)
2. **OR:** `/app/netlify.toml` Line 8

**MongoDB/Redis/Railway backend logic:** NOT involved (error happens before reaching backend handler)

---

## ✅ How to Fix

**Check these exact locations:**

1. **Netlify Dashboard:**
   - Site Settings → Environment variables
   - Look for: `REACT_APP_BACKEND_URL`
   - Should be: `https://api.li-ai.org` (NO `/api` at end)

2. **GitHub:**
   - `/app/frontend/src/components/APIKeyManager.jsx` Line 86
   - Should be: `api.get('/settings/api-keys')` (NO `/api` prefix)

3. **Netlify Build Logs:**
   - Check what commit was deployed
   - Check what `REACT_APP_BACKEND_URL` value was used

**The fix must happen at BUILD TIME, not runtime!**
