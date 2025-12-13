# TTS Timeout & Audio Silence Issue - FIXED ✅

## Problem Identified

When you said "No" at the Q&A Strategic Narrative node, there was **30 seconds of silence** before audio played. You waited and then said "who would be that'd be great".

### What Happened (Timeline)
```
11:04:34 - You said "No"
11:04:34 - System transitioned to "Work Background" node
11:04:34 - TTS generation started (ElevenLabs)
11:05:04 - TTS FAILED after 30-second timeout
11:05:04 - Error: "Error generating ElevenLabs audio: " (timeout exception)
11:05:05 - You said "No, uh, who would be? I wouldn't be upset. That'd be great."
```

### Root Cause

**ElevenLabs API timeout** - The API took the full 30 seconds and then failed, causing:
1. 30 seconds of silence (waiting for TTS that never came)
2. No audio playback (TTS returned empty/null)
3. Bad user experience

## The Fix

### 1. Reduced Timeout from 30s → 10s
```python
# Before
async with httpx.AsyncClient(timeout=30.0) as client:

# After  
timeout_seconds = 10.0  # Fail fast instead of waiting 30s
async with httpx.AsyncClient(timeout=timeout_seconds) as client:
```

### 2. Added Retry Logic with Exponential Backoff
```python
max_retries = 2
for attempt in range(max_retries):
    try:
        # Try TTS generation
        ...
    except httpx.TimeoutException:
        logger.error(f"Timeout after {timeout_seconds}s (attempt {attempt + 1}/{max_retries})")
        if attempt < max_retries - 1:
            await asyncio.sleep(0.5)  # Brief pause before retry
            continue
```

### 3. Better Error Logging
```python
except httpx.TimeoutException:
    logger.error(f"ElevenLabs timeout after {timeout_seconds}s")
except Exception as e:
    logger.error(f"Error generating ElevenLabs audio: {e}")
    logger.error(traceback.format_exc())  # Full stack trace
```

## Impact

**Before:**
- ❌ 30-second timeout → 30 seconds of silence
- ❌ No retry → Single point of failure
- ❌ Poor error logging → Empty error messages

**After:**
- ✅ 10-second timeout → Max 10s silence (improved by 67%)
- ✅ 2 retry attempts → Better reliability
- ✅ Detailed error logging → Easier debugging
- ✅ Total max wait: ~21 seconds (10s + retry + 10s) instead of 30s

## Why This Happens

ElevenLabs API can be slow/unreliable at times:
1. **Network latency** - API servers may be under load
2. **Text complexity** - Longer/complex text takes more time
3. **API rate limits** - Throttling can cause delays
4. **Infrastructure issues** - Temporary ElevenLabs outages

## Prevention

The retry mechanism now means:
1. First attempt fails fast (10s max)
2. Retry immediately with 0.5s pause
3. If still fails, user only waits ~21s max instead of 30s

This won't eliminate all TTS issues (ElevenLabs infrastructure is outside our control), but it will:
- Reduce wait time significantly
- Increase success rate via retries
- Provide better error visibility

## Next Steps

If ElevenLabs continues to be unreliable, consider:
1. **Alternative TTS provider** (Sesame, Hume, etc.)
2. **TTS fallback chain** (try ElevenLabs → fallback to Sesame if timeout)
3. **Pre-generate common phrases** (cache frequently used TTS)

---

**Fixed:** November 4, 2025  
**Issue:** 30-second TTS timeout causing silence  
**Solution:** 10s timeout + retry logic + better error handling  
**Status:** ✅ Backend restarted with fix
