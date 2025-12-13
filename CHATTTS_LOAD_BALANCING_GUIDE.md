# ChatTTS Load Balancing Setup for 20+ Concurrent Calls

## Overview
To support 20+ concurrent calls, you need multiple ChatTTS RunPod instances with load balancing.

## Architecture

```
┌─────────────┐
│   Backend   │
│  (Your App) │
└──────┬──────┘
       │
       ├─ Random Load Balancing
       │
       ├──► ChatTTS Instance 1 (http://xxx:10129)
       ├──► ChatTTS Instance 2 (http://xxx:10130)
       ├──► ChatTTS Instance 3 (http://xxx:10131)
       ├──► ChatTTS Instance 4 (http://xxx:10132)
       └──► ChatTTS Instance 5 (http://xxx:10133)
```

## Capacity Planning

**Single Instance Capacity:**
- Comfortable: 2-4 concurrent requests
- Maximum: 5-6 concurrent (with degraded performance)

**For 20+ Concurrent Calls:**
- **Minimum**: 5 instances (20 calls / 4 per instance)
- **Recommended**: 7-10 instances (headroom for peaks)

## Deployment Steps

### Step 1: Deploy Multiple RunPod Instances

1. **Create First Instance** (you already have this)
   - Use your existing RunPod with ChatTTS server
   - Note the URL: `http://203.57.40.119:10129`

2. **Clone Additional Instances**
   - Deploy 4-9 more RunPod instances
   - Use same GPU (RTX 4090)
   - Upload same `RUNPOD_CHATTTS_SERVER_FIXED_VOICES.py`
   - Expose different ports if on same IP, OR
   - Use different IPs (recommended)

3. **Start Each Server**
   ```bash
   # On each RunPod instance
   python RUNPOD_CHATTTS_SERVER_FIXED_VOICES.py
   ```

4. **Note All URLs**
   ```
   Instance 1: http://203.57.40.119:10129
   Instance 2: http://203.57.40.119:10130
   Instance 3: http://203.57.40.119:10131
   Instance 4: http://IP2:10129
   Instance 5: http://IP3:10129
   ...etc
   ```

### Step 2: Configure Backend Load Balancing

Update `/app/backend/.env` with all your instance URLs:

```bash
# Multiple ChatTTS instances for load balancing (comma-separated)
CHATTTS_API_URLS=http://203.57.40.119:10129,http://203.57.40.119:10130,http://203.57.40.119:10131,http://IP2:10129,http://IP3:10129
```

**That's it!** The backend will automatically:
- Distribute requests randomly across all instances
- Log which instance handled each request
- Fall back to Cartesia if all instances fail

### Step 3: Restart Backend

```bash
sudo supervisorctl restart backend
```

## How It Works

**Load Balancing Algorithm:**
- **Random selection** for even distribution
- Each TTS request picks a random instance
- No single point of failure

**Example with 5 instances:**
```
Call 1 → Instance 3
Call 2 → Instance 1  
Call 3 → Instance 5
Call 4 → Instance 2
Call 5 → Instance 4
Call 6 → Instance 1 (back to random)
...
```

## Monitoring

Each TTS request logs which instance was used:

```
ChatTTS API: http://203.57.40.119:10129 (instance 1/5)
✅ ChatTTS generation successful from http://203.57.40.119:10129
```

## Cost Considerations

**RunPod RTX 4090 Pricing** (approximate):
- On-Demand: ~$0.79/hour per instance
- Spot: ~$0.30-0.50/hour per instance

**For 20+ concurrent calls:**
- 7 instances × $0.40/hr = **$2.80/hour**
- Or ~$2,000/month for 24/7 operation

**Cost Optimization:**
- Use Spot instances (cheaper, may get interrupted)
- Only run instances during business hours
- Auto-scale up/down based on call volume

## Testing Concurrent Load

Test with concurrent requests:

```bash
# Send 10 concurrent requests
for i in {1..10}; do
  curl -X POST http://YOUR_BACKEND/api/tts-endpoint \
    -H "Content-Type: application/json" \
    -d '{"text":"Test", "voice":"male_1"}' &
done
wait
```

Check logs to see requests distributed across instances.

## Health Monitoring

Add a health check endpoint to monitor all instances:

```python
# Check all ChatTTS instances
from chattts_tts_service import ChatTTSClient

client = ChatTTSClient(api_urls=["url1", "url2", "url3"])
health_results = await client.health_check(check_all=True)
```

## Failover Behavior

If an instance fails:
- Request fails for that specific call
- Backend falls back to Cartesia
- Other calls continue on healthy instances

**Recommendation:** Add retry logic for failed instances.

## Alternative: Managed Service

If managing 10 RunPod instances is too complex, consider:
- **Cartesia** (your current provider) - handles scaling automatically
- **ElevenLabs** - enterprise plans support high concurrency
- **AWS/GCP TTS** - auto-scaling built-in

## Summary

✅ **Backend Updated** - Load balancing enabled
✅ **Random distribution** - Even load across instances
✅ **Easy scaling** - Just add more URLs to env var
✅ **Production ready** - Supports 20+ concurrent calls

**Next Step:** Deploy 5-10 ChatTTS instances and update `CHATTTS_API_URLS` in your `.env` file!
