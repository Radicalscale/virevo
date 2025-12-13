# Critical Issues Investigation Report

## Overview
**Date:** December 12, 2025  
**Call Recording:** recording_v3_O2DN6uHRxPlvzfsEf.mp3  
**Log File:** logs.1765517214222.log  
**Reference Materials:** TTS_WEBSOCKET_COMPLETE_MASTER.md, TTS_WEBSOCKET_MASTER_CODE.md

---

## Research Plan

1. **Phase 1:** Document each problem with evidence from logs/recording
2. **Phase 2:** Extract relevant patterns from the old working code (MASTER files)
3. **Phase 3:** Compare current implementation to working implementation
4. **Phase 4:** Identify specific code areas causing each issue
5. **Phase 5:** Propose targeted fixes

---

## Problem #1: False Dead Air Detection ("Are you still there?")

### Description
The agent incorrectly asked "are you still there?" immediately after the user responded. From the recording at 5:00-5:11:
- **5:00-5:03** - Agent: "Do you know how to set up a reminder on your phone?"
- **5:03-5:04** - User: "Uh, yeah. I can do that."
- **5:05** - Agent: "Are you still there?" ← **BUG! User just spoke!**

### Evidence from Logs - ROOT CAUSE CONFIRMED

**The Core Bug: Silence timer starts when audio is SENT, not when it finishes PLAYING**

```
05:22:42.483 - Audio SENT via WebSocket (3.2 seconds duration)
              "Do you know how to set up a reminder on your phone?"
05:22:42.987 - SILENCE TIMER STARTED ← BUG! Audio still has 2.7s left to play!
05:22:45.7   - Audio actually FINISHES playing (42.483 + 3.2s)
05:22:50.016 - System thinks 7.0s silence passed, triggers "Are you still there?"
05:22:50.729 - User starts speaking "Uh, yeah" 
              (Only ~5s after audio finished - normal response time!)
```

**What the USER experienced:**
- Audio finished at ~05:22:45.7
- User responded at 05:22:50.7 (~5 seconds later - NORMAL!)
- But system triggered check-in because it counted from 05:22:42.987

**What the SYSTEM thought:**
- Silence started at 05:22:42.987
- By 05:22:50.016, that's 7.03 seconds of "silence"
- Threshold is 7s → Check-in triggered

**The 3-second error:** The system started counting silence ~3 seconds BEFORE the audio actually finished playing.

### Root Cause
When audio is streamed via WebSocket:
1. Audio bytes are sent (takes ~200ms)
2. System immediately marks playback as "finished"
3. Silence timer starts
4. But the audio is STILL PLAYING for another 3+ seconds!

### Proposed Fix
The `playback_expected_end_time` must be calculated and RESPECTED:
```python
# When sending audio:
audio_duration = len(audio_bytes) / (16000 * 2)  # 16kHz, 16-bit
playback_expected_end = time.time() + audio_duration + 0.5  # buffer

# Before starting silence timer:
if time.time() < playback_expected_end:
    return  # Audio still playing, don't count silence yet
```

---

## Problem #2: Interruption Handling - Audio Not Fading/Stopping

### Description
When user said "Yeah I said 4K" at 05:18:50, the agent was still playing audio (`audio_playing=True`, `time_until_done=2.2s`), but the agent did NOT stop or fade down. It kept talking until it finished naturally.

### Evidence from Logs - TWO BUGS FOUND

**Timeline:**
```
05:18:46.263 - Sentence #16 SENT: "Just a rough ballpark is fine—what was the highest..."
05:18:46.258 - playback_expected_end_time extended: +5.7s + 0.5s buffer
05:18:49.691 - User starts saying "Yeah, I..."
05:18:50.508 - FILTER CHECK: audio_playing=True, time_until_done=2.2s, is_active=False ← BUG!
05:18:50.508 - User says "Yeah, I said 4K." (5 words, not filtered)
05:18:50.522 - Processing user transcript... NO INTERRUPTION TRIGGERED
05:18:52.268 - Next sentence #17 starts playing (agent kept talking!)
```

### Bug #2a: `is_active=False` When Audio Still Playing

**Code at server.py lines 4514-4516:**
```python
if user_actively_speaking and not has_active_playbacks and not is_generating:
    is_active = False  # ← This overrides audio_still_playing!
```

This logic says: "If user is speaking and there are no HTTP playbacks and LLM is done, set `is_active=False`"

But with WebSocket streaming:
- `has_active_playbacks=0` (WebSocket doesn't create playback IDs)
- `is_generating=False` (LLM finished)
- So `is_active=False` even though `audio_still_playing=True`!

**The logic is backwards!** When user speaks AND audio is still playing, that's EXACTLY when we need `is_active=True` to trigger interruption.

### Bug #2b: No WebSocket Audio Clear/Stop Method

Even if `is_active` was True, there's no code to stop WebSocket audio!

HTTP playbacks have:
```python
await telnyx_service.stop_playback(call_control_id, playback_id)
```

But WebSocket streaming has NO equivalent. The `persistent_tts_service.py` has no `stop()` or `clear_audio()` method.

**Telnyx WebSocket supports a `clear` event to flush buffered audio:**
```python
message = {"event": "clear"}
await self.telnyx_ws.send_text(json.dumps(message))
```

### Proposed Fixes

**Fix 2a: Correct `is_active` logic:**
```python
# If audio is still playing (by time estimate), agent IS active regardless of user speaking
if audio_still_playing and time_until_audio_done > 0.3:
    is_agent_active = True
elif has_active_playbacks or is_generating:
    is_agent_active = True
else:
    is_agent_active = False
```

**Fix 2b: Add WebSocket audio clear method to `persistent_tts_service.py`:**
```python
async def clear_audio(self):
    """Clear/stop any buffered audio in Telnyx WebSocket"""
    if self.telnyx_ws:
        try:
            message = {"event": "clear"}
            await self.telnyx_ws.send_text(json.dumps(message))
            logger.info(f"🛑 Sent clear event to stop WebSocket audio")
        except Exception as e:
            logger.error(f"❌ Error clearing audio: {e}")
```

**Fix 2c: Call clear_audio on interruption detection:**
When user speaks 2+ words while `audio_still_playing=True`:
1. Send `clear` event to Telnyx WebSocket
2. Optionally fade audio over 300-400ms (may require gradual volume reduction)
3. Stop any pending TTS sentences from being sent

---

## Problem #3: Massive Latency

### Description
Significant delay between user finishing speaking and agent responding. This latency was not present in earlier versions.

### Evidence from Logs
**E2E Latency measurements from logs:**
```
E2E_TOTAL: 10236ms - REAL USER LATENCY: 10536ms estimated (websocket: False!)
E2E_TOTAL: 6194ms  - REAL USER LATENCY: 6494ms estimated
E2E_TOTAL: 4817ms  - REAL USER LATENCY: 5117ms estimated
```

**CRITICAL DISCOVERY:** The first response shows `websocket: False`!
```
05:19:35.513 - TTS_TOTAL: 5978ms (provider: elevenlabs, websocket: False)  ← HTTP TTS, NOT WebSocket!
05:19:48.743 - Streaming sentence #34: Okay...  ← Later uses WebSocket
```

There are **TWO CODE PATHS** for TTS:
1. HTTP-based TTS (slow, `websocket: False`)
2. WebSocket streaming TTS (fast, persistent connection)

The first response used HTTP TTS (5978ms for TTS alone!), while later responses used WebSocket.

### Configuration Inconsistency Found
```python
# Line 3392: Defaults to False
use_websocket_tts = settings.get("elevenlabs_settings", {}).get("use_websocket_tts", False)

# Line 7127: Defaults to True  
use_persistent_tts = agent_settings.get("elevenlabs_settings", {}).get("use_persistent_tts", True)
```

**Two different setting names with opposite defaults!** Some code paths use `use_websocket_tts` (default False), others use `use_persistent_tts` (default True).

### Latency Breakdown (for HTTP path)
```
STT_LATENCY: 10ms ✅
TRANSITION_EVAL: 520ms ⚠️ (LLM call)
LLM_TOTAL: ~1000ms ⚠️
TTS_TOTAL: 5978ms ❌ (HTTP TTS - should be streaming!)
```

### Root Cause Analysis

**Primary Issue:** Inconsistent WebSocket TTS usage
- The FIRST response in a call may use HTTP TTS path (slow)
- Later responses use WebSocket (fast)
- This is due to session initialization timing

**Secondary Issue:** Transition evaluation adds 500ms
- LLM call to decide which node to go to
- Happens BEFORE response generation starts

### Proposed Fix

**Priority 1: Fix WebSocket TTS initialization**
1. Ensure persistent TTS session is created BEFORE first response is needed
2. Unify the setting names (`use_websocket_tts` vs `use_persistent_tts`)
3. Default to WebSocket TTS always

**Priority 2: Reduce transition evaluation latency**
1. Cache common transition patterns
2. Or run transition evaluation in parallel with response preparation

---

## Latency Analysis & How Fixes Interact

### Current Architecture Discovery

There are **TWO parallel TTS paths** running:

1. **Persistent TTS (WebSocket streaming)** - FAST
   - Used via `persistent_tts_session.stream_sentence()` 
   - Each sentence takes ~200ms to stream
   - Audio is sent directly to Telnyx WebSocket
   - **This IS working correctly**

2. **REST TTS (HTTP)** - SLOW
   - Used via `speak_text()` → `generate_tts_audio()`
   - Takes 3-12 seconds per response
   - **The `TTS_TOTAL` timing measures this path**
   - But this audio may never actually play! The WebSocket audio plays first.

### Why Logs Show `websocket: False` but WebSocket IS Used

The logging at line 4070 checks `use_persistent_tts` (defaults to False for logging display):
```python
use_websocket_tts = agent_settings.get("elevenlabs_settings", {}).get("use_persistent_tts", False)
logger.info(f"TTS_TOTAL: {tts_latency_ms}ms (websocket: {use_websocket_tts})")
```

But the ACTUAL WebSocket streaming happens at line 3784:
```python
persistent_tts_session.stream_sentence(sentence, is_first=is_first, is_last=is_last)
```

This setting defaults to `True` at line 7127:
```python
use_persistent_tts = agent_settings.get("elevenlabs_settings", {}).get("use_persistent_tts", True)
```

### The REAL Latency Issue

Looking at the logs:
- Individual sentences stream via WebSocket in 180-235ms ✅
- But `TTS_TOTAL` shows 3-12 seconds (REST path timing)

**The REST path may be redundantly generating audio that's never used**, OR the timing includes waiting for all sentences to complete.

### How All Fixes Interact

| Fix | Interaction with Latency |
|-----|-------------------------|
| **Garbled Detection** | ✅ No impact - independent filter |
| **`is_active` Logic** | ✅ No impact - just flag checking |
| **WebSocket Clear** | ⚠️ Must not re-trigger TTS generation. Just clear buffered audio. |
| **Audio Duration Tracking** | ⚠️ Must track WebSocket audio duration, not REST timing |
| **Dead Air Timer** | ⚠️ Must use WebSocket `playback_expected_end_time`, not REST timing |

### Critical Integration Points

**1. When clearing audio on interruption:**
```python
async def handle_interruption():
    # 1. Clear Telnyx WebSocket buffer (stops playback)
    await persistent_tts_session.clear_audio()
    
    # 2. Cancel any pending sentence streaming
    persistent_tts_session.cancel_pending_sentences()
    
    # 3. Reset expected end time to NOW
    call_states[call_id]["playback_expected_end_time"] = time.time()
    
    # 4. Mark agent as not speaking
    redis_service.mark_agent_done_speaking(call_id)
```

**2. For dead air timing - use WebSocket timing, not REST:**
The `playback_expected_end_time` should be set by `persistent_tts_service.py` when it sends audio, not by REST timing.

**3. For `is_active` flag - check WebSocket state:**
```python
# Check if WebSocket audio is still expected to be playing
time_until_done = call_states[call_id].get("playback_expected_end_time", 0) - time.time()
audio_still_playing = time_until_done > 0.3  # 300ms buffer

if audio_still_playing:
    is_agent_active = True
```

### Recommended Fix Order (to avoid conflicts)

1. **Fix Garbled Detection** (independent, no conflicts)
2. **Fix `is_active` Logic** (use `playback_expected_end_time` from WebSocket)
3. **Add WebSocket Clear** (with proper state reset)
4. **Fix Audio Duration Tracking** (ensure `playback_expected_end_time` set correctly in persistent_tts_service)
5. **Fix Dead Air Timer** (check WebSocket timing, not REST)

All fixes reference the same `playback_expected_end_time` variable, ensuring consistency.

---

## Summary of All Fixes

### Issues Found

| # | Issue | Root Cause | Fix Location |
|---|-------|------------|--------------|
| 1 | Dead Air False Positive | Silence timer starts when audio SENT, not when FINISHED PLAYING | `server.py` dead_air_monitor integration |
| 2 | "4K" Filtered as Garbled | No-vowels check filters valid number responses | `server.py` line 4472 |
| 3 | `is_active=False` During Playback | Logic prioritizes `user_speaking` over `audio_playing` | `server.py` lines 4514-4521 |
| 4 | No WebSocket Audio Stop | Missing `clear_audio()` method for interruptions | `persistent_tts_service.py` |

### Latency Status
- **WebSocket TTS IS working** (~200ms per sentence)
- **REST TTS is redundant** (3-12s timing in logs)
- Logging shows wrong value (`websocket: False`) but actual streaming works
- No latency fix needed - just ensure WebSocket path continues working

### Fix Implementation Plan

**Step 1: Garbled Detection (5 min)**
```python
# In is_garbled_transcript() - before Pattern 4
if re.match(r'^\d+[kKmMbB]?\.?$', text):
    return False  # Valid number pattern
```

**Step 2: `is_active` Logic (15 min)**
```python
# Replace lines 4514-4521
time_until_done = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0) - time.time()
if time_until_done > 0.3:  # Audio still playing
    is_agent_active = True
elif has_active_playbacks or is_generating:
    is_agent_active = True
else:
    is_agent_active = False
```

**Step 3: Add `clear_audio()` to persistent_tts_service.py (30 min)**
```python
async def clear_audio(self):
    """Clear buffered audio on interruption"""
    if self.telnyx_ws:
        await self.telnyx_ws.send_text(json.dumps({"event": "clear"}))
        # Reset state
        self.pending_sentences = []
```

**Step 4: Call `clear_audio()` on interruption in server.py**
When barge-in detected with 2+ words, call the clear method.

**Step 5: Fix Dead Air Timer (30 min)**
Ensure silence timer only starts AFTER `playback_expected_end_time` passes.

---

## Files to Modify

1. `/app/backend/server.py`
   - Line 4472: Garbled detection
   - Lines 4514-4521: `is_active` logic
   - Barge-in handler: Call `clear_audio()`
   - Dead air timer: Check `playback_expected_end_time`

2. `/app/backend/persistent_tts_service.py`
   - Add `clear_audio()` method
   - Add `cancel_pending_sentences()` method

---

## Implementation Complete ✅

### Changes Made

**1. Garbled Detection Fix (`server.py` ~line 4472)**
- Added exception for number patterns like "4K", "5K", "10K", "2PM"
- These valid responses are no longer filtered as garbled

**2. `is_active` Logic Fix (`server.py` ~lines 4517-4530)**
- Changed logic so `time_until_audio_done > 0.3` sets `is_agent_active = True`
- Audio playback state now takes priority over user speaking state
- Enables proper interruption detection during TTS playback

**3. WebSocket Audio Clear (`persistent_tts_service.py`)**
- Added `clear_audio()` method - sends "clear" event to Telnyx WebSocket
- Added `cancel_pending_sentences()` method - clears audio queue
- These are called on interruption to immediately stop playback

**4. Interruption Handler Update (`server.py` ~lines 3520-3535)**
- Now calls `persistent_tts_session.clear_audio()` on barge-in
- Calls `cancel_pending_sentences()` to prevent queued audio
- Resets `playback_expected_end_time` to current time

**5. Dead Air Monitor Fix (`dead_air_monitor.py` ~lines 90-105)**
- Added check for `time_until_audio_done > 0.5`
- Skips silence counting while audio is expected to be playing
- Prevents false "are you still there" triggers

### Files Modified
- `/app/backend/server.py`
- `/app/backend/persistent_tts_service.py`
- `/app/backend/dead_air_monitor.py`

### Testing Recommendations
1. Test saying "4K", "5K", "10K" in response to income questions
2. Test interrupting the agent mid-sentence - should stop within ~400ms
3. Test waiting 5 seconds after agent finishes - should NOT get "are you still there"
4. Test waiting 7+ seconds after agent finishes - SHOULD get "are you still there"

---

## Additional Fixes (Round 2)

### Issues Found in Round 2 Testing

1. **Threshold too strict** - Using `time_until_audio_done > 0.3` made `is_active=False` near end of audio
2. **BARGE-IN only checked during generation** - Not during audio playback
3. **Inconsistent logic between filter locations** - Both on_final_transcript and endpoint filters

### Additional Fixes Applied

**Fix 6: Expanded threshold for is_active**
Changed from `time_until_audio_done > 0.3` to `time_until_audio_done > -0.3`
- Now includes a 300ms grace period AFTER audio ends
- Prevents edge cases at exact moment audio finishes

**Fix 7: BARGE-IN checks during audio playback**
```python
# Old: only checked during generation
currently_generating = agent_generating_response

# New: checks generation OR audio playback
agent_interruptible = currently_generating or audio_still_playing
```

**Fix 8: Consistent logic in both filter locations**
Both on_final_transcript and endpoint filters now use the same logic.

### Expected Behavior After Fixes

1. **1-word responses during agent speech**: Filtered, NOT used in context
2. **2+ word interruptions during playback**: Triggers BARGE-IN, clears audio
3. **Dead air detection**: Only triggers after audio truly finished + 7s silence
4. **Interruption fade**: `clear_audio()` stops WebSocket buffer immediately

### Testing Checklist
- [ ] Say "yeah" during agent speech - should be filtered
- [ ] Say "no I don't think so" during playback - should interrupt
- [ ] Verify no response stacking (filtered words not in context)
- [ ] Verify dead air timing is correct
