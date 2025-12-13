# Complete Voice Agent Interaction Model

## Overview

This document describes the correct behavior for the voice agent's interaction model, including interruption handling, turn-taking, and audio state management. Based on analysis of logs and the working reference implementation.

---

## Current Problem

From the logs, after interruption:
1. `interrupted=True` is set in `clear_audio()`
2. User speaks, endpoint detected, LLM generates response
3. `stream_sentence()` is called
4. BUT: The check `if self.interrupted:` happens BEFORE the reset `if is_first:`
5. **Result: Audio is skipped forever**

Additionally, even when the order is fixed, the `is_first` logic may not work correctly because:
- Multiple sentences from the SAME interrupted response may still be in the queue
- The "new" response's first sentence may not be recognized as `is_first=True`

---

## Required Features (Step by Step)

### Feature 1: Basic Turn-Taking
**What it should do:**
1. Agent speaks → `is_speaking=True`
2. Agent finishes → `is_speaking=False`
3. User speaks → Agent listens
4. User finishes (endpoint) → Agent responds

**Current state:** ✅ Works when no interruption

---

### Feature 2: Interruption Detection
**What it should do:**
1. While agent is speaking (`is_speaking=True`), monitor user's speech
2. If user says ≥2 substantial words during agent speech → INTERRUPTION DETECTED
3. Filter out:
   - Single words (could be "um", "uh")
   - Filler words
   - Echo/garbled transcripts (agent's own voice bleeding through)

**Current state:** ✅ Detection works

---

### Feature 3: Stopping Agent Audio on Interruption
**What it should do:**
1. When interruption detected:
   - IMMEDIATELY stop sending audio chunks to Telnyx
   - Send `clear` event to Telnyx WebSocket to flush buffered audio
   - Cancel any pending TTS tasks
   - Set `is_speaking=False`
2. Log: "Agent stopped, user can continue speaking"

**Current state:** ✅ This works via `clear_audio()`

---

### Feature 4: Processing Interrupted User Input
**What it should do:**
1. After agent stops, continue listening to user
2. Wait for user's complete thought (endpoint detection from Soniox)
3. Once endpoint detected, process the FULL utterance (not just the interruption trigger)
4. Generate response based on what user said

**Current state:** ⚠️ Partially works - endpoint is detected but response may be blocked

---

### Feature 5: CRITICAL - Resuming Agent Speech After Interruption
**What it should do:**
1. When generating a NEW response (after user's endpoint):
   - Reset `interrupted=False` BEFORE trying to stream
   - Mark this as a "new turn" or "new response"
2. The agent should speak the new response normally
3. If user interrupts AGAIN during new response, repeat the cycle

**Current state:** ❌ BROKEN - `interrupted` flag blocks ALL future audio

---

### Feature 6: Filtering During Agent Speech
**What it should do:**
1. While agent IS speaking (`is_speaking=True`):
   - Filter out 1-word utterances (not interruptions)
   - Filter out filler words
   - Filter out echo/garbled transcripts
2. While agent is NOT speaking (`is_speaking=False`):
   - Process ALL user input normally
   - Do NOT filter "hello", "yes", numbers like "4K"

**Current state:** ⚠️ Filtering logic exists but `is_speaking` state is sometimes wrong

---

### Feature 7: Dead Air Handling
**What it should do:**
1. Track when agent stops speaking (`agent_speaking_end_time`)
2. Track when user stops speaking (`user_speaking_end_time`)
3. If no activity for X seconds after agent finishes → send check-in
4. Check-in messages: "Are you still there?", "Can you hear me okay?"

**Current state:** ⚠️ May trigger incorrectly due to state confusion

---

## The Correct State Machine

```
                    ┌──────────────────────────────────────┐
                    │                                      │
                    ▼                                      │
    ┌─────────────────────────────┐                       │
    │       AGENT_IDLE            │                       │
    │  is_speaking=False          │                       │
    │  interrupted=False          │                       │
    │  Ready to listen or speak   │                       │
    └─────────────────────────────┘                       │
                    │                                      │
                    │ (LLM generates response)             │
                    ▼                                      │
    ┌─────────────────────────────┐                       │
    │     AGENT_SPEAKING          │                       │
    │  is_speaking=True           │                       │
    │  interrupted=False          │◄─────────────┐        │
    │  Streaming audio            │              │        │
    └─────────────────────────────┘              │        │
          │                │                     │        │
          │                │ (audio finishes)    │        │
          │                └─────────────────────┼────────┘
          │                                      │
          │ (user interrupts)                    │
          ▼                                      │
    ┌─────────────────────────────┐              │
    │   INTERRUPTED               │              │
    │  is_speaking=False          │              │
    │  interrupted=True           │              │
    │  Audio stopped              │              │
    │  Waiting for user endpoint  │              │
    └─────────────────────────────┘              │
                    │                            │
                    │ (user endpoint detected)   │
                    │ (new response generated)   │
                    │                            │
                    └──────────► RESET interrupted=False
                                 Then → AGENT_SPEAKING
```

---

## The Fix Required

### Location: `/app/backend/persistent_tts_service.py`

#### Problem Code (lines 221-229):
```python
async def stream_sentence(...):
    # CHECK FIRST - blocks everything!
    if self.interrupted:
        logger.info(f"🛑 Skipping sentence - interrupted flag set")
        return False
    
    # RESET SECOND - never reached if interrupted!
    if is_first:
        self.interrupted = False
```

#### Fixed Code:
```python
async def stream_sentence(...):
    # RESET FIRST - always reset on new response
    if is_first:
        self.interrupted = False
        logger.info(f"🔄 New response starting - interrupt flag reset")
    
    # CHECK SECOND - only blocks mid-response sentences
    if self.interrupted:
        logger.info(f"🛑 Skipping sentence - interrupted flag set")
        return False
```

### Additional Safety: Reset in `server.py`

Before calling `process_user_input()` after an interruption, explicitly reset:

```python
# After interruption is handled and user endpoint detected
tts_session = persistent_tts_manager.get_session(call_control_id)
if tts_session:
    tts_session.reset_interrupt_flag()
```

---

## Complete Feature Checklist

| # | Feature | Expected Behavior | Status |
|---|---------|------------------|--------|
| 1 | Basic turn-taking | Agent speaks, user listens, then vice versa | ✅ |
| 2 | Interruption detection | Detect 2+ words during agent speech | ✅ |
| 3 | Stop audio on interrupt | Clear buffer, stop sending chunks | ✅ |
| 4 | Process interrupted input | Wait for endpoint, get full utterance | ⚠️ |
| 5 | **Resume after interrupt** | **Reset flag, speak new response** | ❌ BROKEN |
| 6 | Filter during speech | Skip 1-word/filler while speaking | ⚠️ |
| 7 | Dead air handling | Check-in after silence | ⚠️ |

---

## What The Working Code Does Differently

From `TTS_WEBSOCKET_MASTER_CODE.md`:

1. **No separate `interrupted` flag** - The working code uses `agent_generating_response` and `current_playback_ids` to track state
2. **Clean state reset** - When a new response starts, all state is fresh
3. **Simpler model** - Fewer flags = fewer race conditions

The current implementation added `interrupted` flag to handle mid-sentence cancellation but didn't add proper reset logic.

---

## Summary of Changes Needed

1. **Swap order in `stream_sentence()`** - Reset `interrupted` BEFORE checking it
2. **Explicitly reset flag** - Call `reset_interrupt_flag()` when starting new response
3. **Verify `is_first` detection** - Ensure first sentence of NEW response is marked correctly
4. **Test the cycle**: Speak → Interrupt → User completes thought → Agent responds → Repeat

---

## Testing Checklist

After fix, verify:

1. [ ] Call starts, agent greets → User says "Hello" → Agent responds
2. [ ] Agent speaks, user interrupts mid-sentence → Agent stops immediately
3. [ ] User continues with full thought → Agent responds to that thought
4. [ ] User says short phrase during agent speech → Filtered (not processed)
5. [ ] User says "4K" or numbers → NOT filtered
6. [ ] Cycle repeats: Can interrupt multiple times in same call
