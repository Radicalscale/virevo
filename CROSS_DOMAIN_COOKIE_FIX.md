# Cross-Domain Cookie Fix for Authentication

## Problem

Getting 401 Unauthorized errors after successful login. Cookies visible in DevTools but not being sent with API requests.

## Root Cause

**Cross-domain cookie issue:**
- Frontend: `https://li-ai.org`
- Backend: `https://api.li-ai.org`
- Cookies set with `samesite="lax"` 
- Cookies stored on `li-ai.org` domain
- **Browsers block cookies from being sent to `api.li-ai.org` (different subdomain)**

## Why This Happens

`SameSite=Lax` cookies are only sent:
- ✅ When URL in browser matches cookie domain
- ❌ When making cross-domain/subdomain API requests

Since frontend (`li-ai.org`) and backend (`api.li-ai.org`) are different subdomains, cookies weren't being sent with fetch requests.

## Solution

Changed cookie settings in `/app/backend/server.py` (both signup and login endpoints):

### Before (❌ Broken):
```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=is_production,
    samesite="lax",  # ❌ Blocks cross-subdomain
    max_age=max_age
)
```

### After (✅ Fixed):
```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,  # Always secure for HTTPS
    samesite="none",  # ✅ Allow cross-domain cookies
    max_age=max_age,
    domain=".li-ai.org"  # ✅ Share across all *.li-ai.org subdomains
)
```

## Key Changes

1. **`samesite="none"`** - Allows cookies to be sent cross-domain/subdomain
2. **`secure=True`** - Required when using `samesite="none"` (HTTPS only)
3. **`domain=".li-ai.org"`** - Sets cookie for entire `.li-ai.org` domain tree
   - Cookie accessible from `li-ai.org`, `api.li-ai.org`, `www.li-ai.org`, etc.

## How It Works Now

1. User logs in at `https://li-ai.org/login`
2. Backend (`api.li-ai.org`) sets cookie with `domain=.li-ai.org`
3. Browser stores cookie as:
   ```
   Domain: .li-ai.org (includes all subdomains)
   Path: /
   Secure: Yes
   HttpOnly: Yes
   SameSite: None
   ```
4. When frontend makes request to `https://api.li-ai.org/api/agents`:
   - ✅ Cookie IS sent (same parent domain)
   - ✅ Backend can verify JWT
   - ✅ Request succeeds

## Testing

### After Backend Restart:

1. **Clear ALL cookies** for li-ai.org:
   - DevTools → Application → Cookies → Right-click → Clear

2. **Log in again** at https://li-ai.org/login

3. **Check cookies** in DevTools:
   - Should see `access_token` cookie
   - Domain should show `.li-ai.org` (with leading dot)
   - SameSite should show `None`
   - Secure should be checked

4. **Test API calls:**
   - Dashboard should load
   - Agents should load
   - Test Caller should work
   - No 401 errors

### Expected Network Behavior

In DevTools → Network tab, check any API request:
```
Request Headers:
  Cookie: access_token=eyJ0eXAiOiJKV1QiLCJhbGc...
```

Cookie WILL be sent because:
- Both domains share `.li-ai.org` parent
- `SameSite=None` allows cross-subdomain
- `Secure` flag matches HTTPS

## Railway Deployment

**IMPORTANT:** Push this change to Railway!

The same fix needs to be deployed to Railway for production to work.

After deploying:
1. Clear cookies on production frontend
2. Log in again
3. Test all features

## Security Notes

### Is `SameSite=None` Secure?

YES, when combined with:
- ✅ `secure=True` - HTTPS only
- ✅ `httponly=True` - No JavaScript access
- ✅ `domain=.li-ai.org` - Limited to your domain
- ✅ CORS properly configured

### Why Not Use Authorization Header Instead?

Cookie-based auth is actually MORE secure:
- ✅ `httpOnly` prevents XSS attacks
- ✅ Browser handles cookie automatically
- ❌ Authorization header requires storing token in localStorage (vulnerable to XSS)

## Alternative Solutions (if needed)

If `SameSite=None` doesn't work:

### Option 1: Same Domain
- Frontend at `li-ai.org`
- Backend at `li-ai.org/api` (reverse proxy)
- No cross-domain issues

### Option 2: Authorization Header
- Return token in response body
- Frontend stores in memory/state
- Send as `Authorization: Bearer <token>`
- Less secure (if stored in localStorage)

### Option 3: Separate Auth Domain
- Auth service at `auth.li-ai.org`
- Issues tokens for both domains
- More complex architecture

## Browser Compatibility

`SameSite=None` + `Secure` supported by:
- ✅ Chrome 80+
- ✅ Firefox 69+
- ✅ Safari 13+
- ✅ Edge 80+
- ❌ IE11 (not supported)

For older browsers, fallback to Authorization header.

## Debugging Tips

If still getting 401 errors:

1. **Check cookie in DevTools:**
   - Is cookie present?
   - What's the Domain value?
   - Is SameSite = None?

2. **Check Network tab:**
   - Are cookies being sent in request?
   - Look for `Cookie:` header

3. **Check CORS headers:**
   - Backend must send: `Access-Control-Allow-Credentials: true`
   - Frontend must set: `credentials: 'include'` in fetch

4. **Check Railway logs:**
   - Any JWT verification errors?
   - Any cookie parsing errors?

## Related Files Modified

- `/app/backend/server.py` - Lines 177-188 (signup), 227-238 (login)
