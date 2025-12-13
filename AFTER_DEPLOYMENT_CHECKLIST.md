# After Deployment - Complete Checklist

## 🎯 Assumption: Both Services Are Deployed

- ✅ Railway backend deployed successfully
- ✅ Netlify frontend deployed successfully
- 🔄 Now: Configure DNS, test, and verify everything works

---

## Step 1: Configure DNS Records (15 minutes)

### Prerequisites
- Access to your domain registrar where `li-ai.org` is registered
- Railway backend URL from Railway dashboard
- Netlify site URL from Netlify dashboard

### A. Get Your URLs

**Railway Backend URL:**
1. Go to Railway project: https://railway.app/project/22ec197d-f1e9-4457-aeb4-97954e5b613d
2. Look for: `Settings → Domains → Custom Domain`
3. You should see something like: `your-app.railway.app` or the CNAME Railway provided

**Netlify Frontend URL:**
1. Go to Netlify site dashboard
2. Look for: `Domain management`
3. Get the Netlify Load Balancer IP (for A record)
4. Get your site URL like: `your-site-123.netlify.app` (for www CNAME)

### B. Add DNS Records at Your Domain Registrar

Go to your domain registrar (Namecheap, GoDaddy, Cloudflare, etc.) and add these records:

#### Record 1: Backend API (api.li-ai.org → Railway)
```
Type:  CNAME
Name:  api
Value: [Your Railway CNAME, e.g., your-app.railway.app]
TTL:   3600 (or Auto)
```

#### Record 2: Root Domain (li-ai.org → Netlify)
```
Type:  A
Name:  @  (or blank, or "li-ai.org" depending on UI)
Value: [Netlify Load Balancer IP, e.g., 75.2.60.5]
TTL:   3600 (or Auto)
```

#### Record 3: WWW Subdomain (www.li-ai.org → Netlify)
```
Type:  CNAME
Name:  www
Value: [Your Netlify site URL, e.g., your-site-123.netlify.app]
TTL:   3600 (or Auto)
```

### C. Save and Wait for Propagation (5-60 minutes)

DNS changes take time. Check propagation:

**Online Tool:**
```
Visit: https://dnschecker.org/
Enter: li-ai.org
Should show Netlify IP

Enter: api.li-ai.org
Should show Railway domain
```

**Command Line:**
```bash
# Check backend
dig api.li-ai.org

# Check frontend
dig li-ai.org
```

---

## Step 2: Enable HTTPS on Netlify (5 minutes)

Once DNS is propagated (Step 1C shows correct results):

1. Go to Netlify Dashboard → Your site
2. Go to **Domain management**
3. Wait for: "Awaiting DNS verification" → "Provisioning certificate"
4. Netlify auto-provisions SSL (1-5 minutes)
5. Once done, enable **"Force HTTPS"**

**Now both domains should be secured with HTTPS! 🔒**

---

## Step 3: Verify Backend is Running (2 minutes)

### Test Health Endpoint

```bash
curl https://api.li-ai.org/api/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "deepgram": "configured",
  "openai": "configured",
  "elevenlabs": "configured"
}
```

**If you get an error:**
- 502 Bad Gateway → Backend not running, check Railway logs
- Connection timeout → DNS not propagated yet, wait longer
- 404 → Wrong URL or routes not configured

**Check Railway Logs:**
1. Railway dashboard → Your service
2. Click on deployment
3. Check logs for errors
4. Look for: "Started server process" and "Application startup complete"

---

## Step 4: Verify Frontend Loads (2 minutes)

### Test Frontend

**Visit:** https://li-ai.org

**You should see:**
- ✅ Login page loads
- ✅ No errors in browser console (press F12)
- ✅ Clean, styled interface

**Check Browser Console (F12):**
- Should NOT see CORS errors
- Should NOT see "Failed to fetch" errors
- Look for any red errors

**If frontend doesn't load:**
- Check Netlify deploy logs
- Verify DNS is pointing to Netlify
- Clear browser cache (Ctrl+Shift+R)
- Try incognito mode

---

## Step 5: Test Authentication Flow (5 minutes)

### A. Create Test Account

1. Visit: https://li-ai.org
2. Click **"Sign Up"**
3. Fill in:
   ```
   Email: test@li-ai.org
   Password: Test123!
   Name: Test User
   ```
4. Click **"Sign Up"**

**Expected:** Account created, redirected to dashboard

**If signup fails:**
- Check browser console for errors
- Verify CORS_ORIGINS in Railway includes `https://li-ai.org`
- Check Railway logs for backend errors

### B. Login

1. Use same credentials
2. Click **"Login"**

**Expected:** Successfully logged in, see dashboard

### C. Check Cookies

1. Press F12 → Application tab → Cookies
2. Should see cookies for `li-ai.org`
3. Should include authentication token

**If login fails:**
- Verify JWT_SECRET_KEY is set in Railway
- Check COOKIE_SECURE=true in Railway
- Verify backend logs for JWT errors

---

## Step 6: Add Your API Keys (5 minutes)

**CRITICAL:** Users must add their own API keys!

### Navigate to Settings

1. After login, go to **Settings** → **API Keys**
2. You should see 8 services listed

### Add REQUIRED Keys (Minimum)

Add these keys to make calls work:

#### 1. Deepgram (STT - Speech to Text)
```
Service: deepgram
Key: [Your Deepgram API key]
```
Get from: https://console.deepgram.com/

#### 2. OpenAI (LLM - Language Model)
```
Service: openai
Key: sk-proj-...
```
Get from: https://platform.openai.com/api-keys

OR use Grok instead:
```
Service: grok
Key: xai-...
```
Get from: https://x.ai/

#### 3. ElevenLabs (TTS - Text to Speech)
```
Service: elevenlabs
Key: sk_...
```
Get from: https://elevenlabs.io/app/settings/api-keys

OR use Hume instead:
```
Service: hume
Key: [Your Hume key]
```
Get from: https://platform.hume.ai/

#### 4. Telnyx (Phone Calling)
```
Service: telnyx
Key: KEY...
```
Get from: https://portal.telnyx.com/#/app/api-keys

**You need your own Telnyx account with:**
- Phone number purchased
- Connection ID configured
- Webhook pointing to: https://api.li-ai.org/api/telnyx/webhook

### Add OPTIONAL Keys (For Alternatives)

- Soniox (Alternative STT)
- AssemblyAI (Alternative STT)
- Hume (Alternative TTS)

### Test Each Key

After adding each key, click **"Test Key"** button to verify it works.

---

## Step 7: Create Your First Agent (3 minutes)

### A. Create Agent

1. Go to **Dashboard**
2. Click **"Create Agent"** or **"New Agent"**
3. Fill in:
   ```
   Name: Test Agent
   Type: Call Flow (or Single Prompt)
   Voice: Choose from ElevenLabs voices
   ```
4. Configure settings:
   - LLM Provider: OpenAI or Grok
   - STT Provider: Deepgram
   - TTS Provider: ElevenLabs
5. Save agent

### B. Configure Agent (If Call Flow)

If using Call Flow type:
1. Add nodes (Start, AI Response, etc.)
2. Connect nodes
3. Set prompts for each node
4. Save flow

---

## Step 8: Make Your First Test Call (5 minutes)

### Using Web Caller

1. Go to your agent
2. Click **"Test Call"** or **"Web Call"**
3. Allow microphone access
4. Click **"Start Call"**
5. Speak to the agent
6. Verify:
   - Agent responds
   - Voice is clear
   - Flow works correctly

### Using Phone Call

1. Go to your Telnyx dashboard
2. Configure your phone number:
   - Connection: Your Telnyx connection
   - Webhooks: `https://api.li-ai.org/api/telnyx/webhook`
3. Call your Telnyx number
4. Agent should answer and respond

**If call fails:**
- Check browser console for errors
- Verify all 4 required API keys are added
- Check Railway logs for errors
- Verify Telnyx webhook is configured correctly

---

## Step 9: Verify Multi-Tenant Isolation (3 minutes)

### Test User Isolation

**A. Create Second Test Account**
1. Logout
2. Sign up with different email: `test2@li-ai.org`
3. Login

**B. Verify Isolation**
1. Go to Settings → API Keys
2. Should be EMPTY (no keys)
3. This proves keys are per-user, not shared!

**C. Test Call Without Keys**
1. Try to create agent or make call
2. Should fail with: "API key not found"
3. This confirms system requires user keys

**Perfect!** Multi-tenant isolation working ✓

---

## Step 10: Monitor Your Deployment (Ongoing)

### A. Railway Backend Monitoring

**Check Service Health:**
1. Railway Dashboard → Your service
2. Monitor:
   - CPU usage
   - Memory usage
   - Request count
   - Logs

**Set Up Alerts:**
1. Railway → Notifications
2. Add email or Slack notifications
3. Get alerted if service goes down

### B. Netlify Frontend Monitoring

**Check Deploy Status:**
1. Netlify Dashboard → Deploys
2. See recent deployments
3. Monitor build times

**Check Bandwidth:**
1. Netlify Dashboard → Analytics (free basic metrics)
2. See page views and bandwidth usage

### C. MongoDB Atlas Monitoring

**Check Database:**
1. MongoDB Atlas Dashboard
2. Monitor:
   - Connections
   - Storage used
   - Queries per second

**Set Up Alerts:**
1. Atlas → Alerts
2. Configure alerts for:
   - High CPU
   - High connections
   - Storage limits

---

## Step 11: Document Your Setup (10 minutes)

### Create Internal Documentation

Document these for your reference:

**Credentials & URLs:**
```
Frontend: https://li-ai.org
Backend: https://api.li-ai.org
Railway Project: [Your Railway URL]
Netlify Site: [Your Netlify URL]
MongoDB: [Your Atlas cluster]
```

**Environment Variables:**
- List all Railway env vars
- List Netlify env var
- Document where to find them

**API Keys:**
- Where to get each key
- How to regenerate if needed
- Which services require which keys

**Monitoring:**
- Railway dashboard URL
- Netlify dashboard URL
- MongoDB Atlas dashboard URL

---

## Step 12: Set Up Auto-Deploy Workflow (Already Done!)

### Your Workflow Now

```
1. Edit code locally
     ↓
2. git commit & push to GitHub
     ↓
3. Railway auto-deploys backend (if backend changed)
     ↓
4. Netlify auto-deploys frontend (if frontend changed)
     ↓
5. Changes live in ~5 minutes
```

**No manual deployment needed!**

---

## Step 13: Cost Monitoring Setup (5 minutes)

### Railway

**Check Usage:**
1. Railway → Project → Usage
2. See current month usage
3. Estimated cost

**Set Budget Alert:**
- Railway doesn't have built-in alerts
- Check manually weekly

**Expected Cost:** $20-50/month

### Netlify

**Check Bandwidth:**
1. Netlify → Site analytics
2. See bandwidth usage
3. Free tier: 100GB/month

**Expected Cost:** $0 (unless exceed free tier)

### MongoDB Atlas

**Check Usage:**
1. Atlas → Metrics
2. See storage and operations
3. Your current plan: [Check your tier]

**Expected Cost:** [Your current plan cost]

**Total Estimated:** $20-70/month

---

## Step 14: Backup Strategy (5 minutes)

### Code Backup

✅ **Already backed up in GitHub!**
- All code in GitHub repository
- Every push creates a backup
- Can rollback to any commit

### Database Backup

**MongoDB Atlas:**
1. Atlas → Backup
2. Enable automated backups (if not already)
3. Configure backup schedule
4. Test restore process

**Backup Frequency:**
- Continuous backups (Atlas handles this)
- Point-in-time recovery available
- Keep at least 7 days of backups

### Configuration Backup

**Document and save:**
1. Railway environment variables (save in password manager)
2. Netlify environment variables
3. DNS records configuration
4. API keys (encrypted, secure location)

---

## Step 15: Share Your Platform! (Ongoing)

### Your Platform is Live!

**Share with users:**
1. Send them: https://li-ai.org
2. Users sign up
3. Users add their own API keys
4. Users create agents
5. Users make calls

### User Onboarding

**Create user guide:**
- How to sign up
- How to add API keys (where to get them)
- How to create first agent
- How to make first call

**Support Resources:**
- FAQ document
- Video tutorial (optional)
- Support email/contact

---

## 🎉 You're Done! Deployment Complete Checklist

Go through this final checklist:

### DNS & HTTPS
- [ ] api.li-ai.org points to Railway
- [ ] li-ai.org points to Netlify
- [ ] www.li-ai.org points to Netlify
- [ ] HTTPS enabled on all domains
- [ ] Force HTTPS enabled

### Backend (Railway)
- [ ] Backend health check passes
- [ ] All 7 environment variables set
- [ ] Service running without errors
- [ ] Logs show no critical errors
- [ ] Can connect to MongoDB

### Frontend (Netlify)
- [ ] Site loads at li-ai.org
- [ ] No console errors
- [ ] Login page displays correctly
- [ ] REACT_APP_BACKEND_URL set correctly

### Authentication
- [ ] Can sign up new account
- [ ] Can login
- [ ] Can logout
- [ ] Cookies work correctly
- [ ] JWT authentication functioning

### Multi-Tenant System
- [ ] API keys page loads
- [ ] Can add API keys
- [ ] Keys are encrypted in MongoDB
- [ ] Different users have different keys
- [ ] User isolation verified

### Core Functionality
- [ ] Can create agents
- [ ] Can configure agent settings
- [ ] Can make web calls
- [ ] Can make phone calls (if Telnyx configured)
- [ ] Calls use user's API keys
- [ ] No shared platform keys

### Monitoring
- [ ] Railway monitoring set up
- [ ] Netlify monitoring set up
- [ ] MongoDB monitoring set up
- [ ] Can access all dashboards

### Documentation
- [ ] Credentials documented
- [ ] Environment variables documented
- [ ] Backup strategy in place
- [ ] User guide created

---

## 🚨 Common Post-Deployment Issues

### "502 Bad Gateway" on api.li-ai.org

**Causes:**
- Backend crashed
- MongoDB connection failed
- Railway service down

**Fix:**
1. Check Railway logs
2. Verify all environment variables
3. Check MongoDB Atlas IP whitelist (should be 0.0.0.0/0)
4. Restart Railway service

### CORS Errors in Browser

**Cause:** CORS_ORIGINS doesn't include your domain

**Fix:**
1. Railway → Environment variables
2. Verify: `CORS_ORIGINS=https://li-ai.org,https://www.li-ai.org,https://api.li-ai.org`
3. Restart Railway service
4. Clear browser cache

### Calls Fail with "API Key Not Found"

**Cause:** User hasn't added their API keys

**Expected Behavior!** This is correct - users must add keys.

**Fix:**
1. User goes to Settings → API Keys
2. Adds all required keys
3. Tests each key
4. Tries call again

### WebSocket Connection Fails

**Causes:**
- Wrong BACKEND_URL
- Railway doesn't support WebSocket (it does!)
- Firewall blocking WebSocket

**Fix:**
1. Verify BACKEND_URL in Railway
2. Check browser console for exact error
3. Try different network
4. Check Railway logs during call

---

## 📞 Need Help?

### Resources

- **Railway Docs:** https://docs.railway.app/
- **Netlify Docs:** https://docs.netlify.com/
- **MongoDB Atlas:** https://www.mongodb.com/docs/atlas/

### Checking Logs

**Railway:**
```
Dashboard → Service → Deployments → [Latest] → Logs
```

**Netlify:**
```
Dashboard → Deploys → [Latest Deploy] → Deploy log
```

**Browser:**
```
F12 → Console tab (for frontend errors)
F12 → Network tab (for API call errors)
```

---

## 🎯 Success Metrics

Your deployment is successful if:

✅ **Uptime:** Services running 99%+ of the time
✅ **Response Time:** Backend responds in < 500ms
✅ **Calls Work:** Users can make successful calls
✅ **Multi-Tenant:** Each user uses their own keys
✅ **Auto-Deploy:** Code changes deploy automatically
✅ **Cost:** Within budget ($20-70/month)

---

## 📈 Next Steps After Launch

### Week 1: Monitor Closely
- Check logs daily
- Monitor for errors
- Test all features
- Get user feedback

### Week 2-4: Optimize
- Review performance metrics
- Optimize slow endpoints
- Improve user experience
- Fix any reported bugs

### Month 2+: Scale
- Add more features
- Optimize costs
- Scale Railway if needed
- Add monitoring/alerting

---

## 🎊 Congratulations!

Your multi-tenant voice AI platform is:
- ✅ Deployed at https://li-ai.org
- ✅ Backend running on Railway
- ✅ Frontend on Netlify CDN
- ✅ Secured with HTTPS
- ✅ Auto-deploying from GitHub
- ✅ Using per-user API keys
- ✅ Handling 20+ concurrent calls
- ✅ Ready for users!

**You did it! 🚀**

---

## Quick Reference URLs

**Your App:**
- Frontend: https://li-ai.org
- Backend API: https://api.li-ai.org
- Health Check: https://api.li-ai.org/api/health

**Dashboards:**
- Railway: https://railway.app/project/22ec197d-f1e9-4457-aeb4-97954e5b613d
- Netlify: https://app.netlify.com/
- MongoDB Atlas: https://cloud.mongodb.com/

**Your Repo:**
- GitHub: https://github.com/kcbowman88/Re-cop

**Tools:**
- DNS Checker: https://dnschecker.org/
- Railway Docs: https://docs.railway.app/
- Netlify Docs: https://docs.netlify.com/

---

**Time to complete all steps:** ~1-2 hours (including DNS propagation)

**Ready? Let's go! 🚀**
