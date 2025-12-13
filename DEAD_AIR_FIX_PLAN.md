# Dead Air Bug - Root Cause & Fix Plan

## Problem Summary
The "Are you still there?" check-in is not triggering after 7 seconds of user silence.

## Root Cause Analysis

### What We Found:
1. **Soniox packets** are sent continuously (every 1 second) during the entire call - this is NORMAL behavior (streaming microphone audio to STT)
2. These packets do NOT prevent dead air detection - they're unrelated to silence tracking
3. The REAL issue: Silence timer never starts after agent finishes speaking

### Why Silence Timer Doesn't Start:

**Multi-Worker Problem:**
- Worker A handles WebSocket connection → has `session` object in memory
- Worker B receives `playback.ended` webhook → tries to access session
- `active_telnyx_calls` stores call data in Redis (serializable only: agent_id, user_id)
- `session` object lives ONLY in Worker A's memory (not in Redis)
- Worker B's webhook handler tries to access `session` → gets `None` → crashes

**Evidence from logs:**
```
15:05:35.355 - 🔊 All audio finished - interruption window CLOSED
15:05:35.355 - ❌ Error processing webhook: 'NoneType' object has no attribute 'agent_speaking'
```

After this error, silence tracking never starts, so check-in never triggers.

## Solution

### The dead air system has TWO mechanisms:

1. **Webhook-driven** (server.py lines 4569-4586): When `playback.ended` webhook arrives, call `session.mark_agent_speaking_end()`
   - ❌ **Broken in multi-worker**: Session not available in webhook worker
   
2. **Monitor-driven** (dead_air_monitor.py): Background task checks `session.should_checkin()` every 500ms
   - ✅ **Works**: Runs in WebSocket worker where session exists
   - ⚠️ **But depends on #1** to set `silence_start_time`

### Fix Strategy:

The WebSocket worker needs to detect when playback ends **without relying on webhooks**. Options:

**Option A: Track playback end time in session (RECOMMENDED)**
- When playback starts, store `expected_end_time` in session
- Monitor task checks if `current_time >= expected_end_time`
- If yes AND agent was speaking, call `mark_agent_speaking_end()`

**Option B: Use call_states in WebSocket worker**
- The `call_states` dict exists in WebSocket worker
- When `current_playback_ids` becomes empty, start silence tracking
- But this requires checking `call_states` from monitor task

**Option C: Broadcast playback end via Redis**
- When webhook arrives, publish event to Redis
- WebSocket worker subscribes and handles it
- More complex, requires Redis pub/sub

## Recommended Implementation: Option A

### Changes needed:

1. **CallSession (calling_service.py)**:
   - Add `playback_end_time` attribute
   - Method: `set_playback_end_time(duration)`
   - Method: `check_playback_finished()` → returns True if past end time

2. **Server (server.py)**:
   - After starting playback, calculate duration and call `session.set_playback_end_time()`
   
3. **Monitor (dead_air_monitor.py)**:
   - Before checking `should_checkin()`, call `session.check_playback_finished()`
   - If True AND `agent_speaking`, call `session.mark_agent_speaking_end()`

This way, silence tracking starts in the WebSocket worker WITHOUT depending on webhook delivery!

## Why Soniox Packets Are Not The Problem

The "📤 Sent XXX packets to Soniox" logs are just the audio pipeline:
- Telnyx streams audio from phone → WebSocket → Server
- Server forwards to Soniox for STT
- This happens continuously during the ENTIRE call
- These packets have NOTHING to do with silence detection

Silence detection is based on:
- `silence_start_time` (when was it set?)
- `agent_speaking` flag (is agent currently speaking?)
- `user_speaking` flag (is user currently speaking?)

The STT service (Soniox) is what DETECTS user speech and sets `user_speaking=True`. 
When there's NO speech, Soniox doesn't send transcripts, but the audio packets still flow.

## Testing Plan

1. Add diagnostic logging to monitor task
2. Implement Option A
3. Test with real call:
   - Agent speaks
   - User stays silent for 10 seconds
   - Should see check-in trigger at 7 seconds
4. Verify in logs:
   - "🔇 Silence tracking started"
   - "⏰ Check-in triggered after X.Xs silence"
   - "💬 Sending check-in message"
