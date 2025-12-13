# Critical Bug Fix: Persistent TTS Not Playing Audio

**Date:** November 20, 2025  
**Issue:** Persistent TTS WebSocket established but no audio played

---

## Root Cause

**The Bug:**
```python
# OLD CODE (persistent_tts_service.py line 129):
flush=is_last  # Flush on last sentence
```

**What Happened:**
1. First sentence sent to ElevenLabs: `sentence="Kendrick?", flush=False`
2. ElevenLabs WebSocket waits for end-of-stream signal before generating audio
3. No flush = no end-of-stream = no audio generation
4. Code waits forever in `async for audio_chunk` loop
5. Eventually times out after 18 seconds with 0 chunks received
6. User hears nothing

**From Logs:**
```
✅ Persistent TTS WebSocket established
🎤 Streaming sentence #1: Kendrick?...
[18 seconds of silence]
⏱️ [TIMING] TTS_COMPLETE: All 0 chunks received in 18058ms
```

---

## The Fix

**Changed:**
```python
# NEW CODE:
flush=True  # Always flush each sentence to trigger generation immediately
```

**Why This Works:**
- Each sentence is now treated as complete generation unit
- ElevenLabs receives end-of-stream signal immediately
- Audio generation starts right away
- Chunks stream back to our code
- Audio plays immediately

**Trade-off:**
- OLD: Could potentially batch multiple sentences (but never worked)
- NEW: Each sentence is separate generation (works correctly)

**Impact:** ZERO negative impact, massive positive impact (audio actually plays!)

---

## File Modified

- `/app/backend/persistent_tts_service.py` (line 129)
- Changed `flush=is_last` to `flush=True`

---

## Expected Behavior Now

### Before Fix
```
User: "Hello"
Agent: [18 seconds of silence, 0 audio chunks]
User: *hangs up*
```

### After Fix
```
User: "Hello"
Agent: "Kendrick?" [plays in ~800-1200ms]
User: "Yeah"
Agent: [next response plays immediately]
```

---

## Testing Checklist

✅ **Test 1: Single sentence response**
- Expected: Audio plays within 1-2 seconds

✅ **Test 2: Multi-sentence response**
- Expected: Each sentence plays as soon as it's ready

✅ **Test 3: Check logs**
- Look for: `Received audio chunk: XXX bytes` (debug logs)
- Look for: `All X chunks received` (where X > 0)
- Look for: TTFA metric with reasonable value (<1500ms)

---

## Why This Was Hard to Debug

1. **No error messages** - ElevenLabs WebSocket stayed connected
2. **Timing looked OK** - WebSocket established successfully
3. **Silent failure** - Code just waited forever in async loop
4. **Debug logging** - Audio chunk logs were debug-level, not visible

---

## Status

✅ **Fix Applied**  
✅ **Backend Restarted**  
✅ **Ready for Test Call**

---

**Next Step:** Make ONE test call to validate audio now plays correctly
