# Investigation: Agent Stops Speaking Forever After Interruption

## Problem Statement
After a user interrupts the agent, the agent stops speaking permanently. Even when the user provides new input and the LLM generates new responses, no audio is played.

## Root Cause (Quick Summary)
The `interrupted` flag in `PersistentTTSSession` is set to `True` during interruption but **never reset** before the next response attempt. The reset only happens when `is_first=True` is passed to `stream_sentence()`, but the logic for determining `is_first` is flawed.

---

## All Code Paths Involved

### File 1: `/app/backend/persistent_tts_service.py`

#### 1.1 Flag Initialization (Line 67)
```python
# In PersistentTTSSession.__init__()
self.interrupted = False
```

#### 1.2 The Check That Blocks Audio (Lines 221-224)
```python
async def stream_sentence(...):
    # 🔥 If interrupted, don't start new sentences
    if self.interrupted:
        logger.info(f"🛑 [Call {self.call_control_id}] Skipping sentence '{sentence[:30]}...' - interrupted flag set")
        return False  # <-- THIS IS WHY AUDIO STOPS FOREVER
```
**Problem:** If `interrupted=True`, ALL subsequent sentences are skipped.

#### 1.3 The Reset That Should Happen (Lines 226-229)
```python
    # 🔥 If this is the first sentence of a new response, reset interrupt flag
    if is_first:
        self.interrupted = False
        logger.info(f"🔄 [Call {self.call_control_id}] First sentence - interrupt flag reset")
```
**Problem:** This reset ONLY happens when `is_first=True`. If `is_first=False`, the flag stays `True` forever.

#### 1.4 Where `interrupted` Gets Set to True (Lines 632-637)
```python
async def clear_audio(self):
    # 🔥 Set interrupted flag FIRST to stop any ongoing audio sending loops
    self.interrupted = True
    
    # 🔊 SINGLE SOURCE OF TRUTH: Agent is no longer speaking
    self.is_speaking = False
    logger.info(f"🛑 [Call {self.call_control_id}] INTERRUPT - is_speaking=False, interrupted=True")
```
**This is called when user interrupts. It correctly stops current audio but incorrectly blocks ALL future audio.**

#### 1.5 The Unused Reset Function (Lines 680-682)
```python
def reset_interrupt_flag(self):
    """Reset the interrupted flag when starting a new response"""
    self.interrupted = False
```
**Problem:** This function EXISTS but is NEVER CALLED from server.py after an interruption!

---

### File 2: `/app/backend/server.py`

#### 2.1 Where `is_first` is Calculated (Lines 3795-3806)
```python
async def stream_sentence_to_tts(sentence):
    # ... (sentence is added to queue)
    sentence_queue.append(sentence)
    
    if persistent_tts_session:
        is_first = len(sentence_queue) == 1  # <-- PROBLEM HERE
        is_last = False
        
        tts_task = asyncio.create_task(
            persistent_tts_session.stream_sentence(sentence, is_first=is_first, is_last=is_last)
        )
```
**Critical Bug:** `is_first` is calculated based on `len(sentence_queue) == 1`.

**The Problem Flow:**
1. Response #1: First sentence added → `sentence_queue = [s1]` → `len == 1` → `is_first=True` ✅
2. Response #1: Second sentence → `sentence_queue = [s1, s2]` → `len == 2` → `is_first=False`
3. **User interrupts** → `interrupted = True`
4. **Response #2 starts**: First sentence of NEW response added → But `sentence_queue` may still have old items or be cleared elsewhere
5. If `sentence_queue` is NOT cleared → `len > 1` → `is_first=False` → **Flag never resets!**

#### 2.2 Where `sentence_queue` is Initialized (Line 3706)
```python
# Inside on_endpoint_detected():
sentence_queue = []
```
This is INSIDE the function, so a NEW `sentence_queue` is created for each endpoint. But...

#### 2.3 The Closure Problem
The `stream_sentence_to_tts` callback is defined inside `on_endpoint_detected()`. Each call to `on_endpoint_detected()` creates:
- A NEW `sentence_queue = []`
- A NEW `stream_sentence_to_tts` function

**So `is_first` SHOULD work correctly for new responses.**

But wait - let's check what happens after interruption...

#### 2.4 Where Interruption is Triggered (Lines 3506-3543)
```python
# Inside the Soniox handler
logger.info(f"🛑 INTERRUPTION TRIGGERED - User said {word_count} words: '{partial_transcript}'")
logger.info(f"🛑 Stopping agent IMMEDIATELY...")

# Clear current playbacks
from persistent_tts_service import persistent_tts_manager
persistent_tts_session = persistent_tts_manager.get_session(call_control_id)
if persistent_tts_session:
    await persistent_tts_session.clear_audio()  # <-- Sets interrupted=True
    persistent_tts_session.cancel_pending_sentences()
```
**After this, `interrupted=True` and is NEVER explicitly reset.**

#### 2.5 What Happens After Interruption
After interruption, user's speech continues to be processed. Eventually:
1. Endpoint is detected
2. `on_endpoint_detected()` is called (creates new sentence_queue)
3. LLM generates response
4. `stream_sentence_to_tts()` is called with first sentence
5. `len(sentence_queue) == 1` → `is_first=True`
6. `stream_sentence(sentence, is_first=True)` is called
7. **BUT WAIT**: The check `if self.interrupted:` happens BEFORE `if is_first:` reset!

---

## The ACTUAL Bug (Critical Finding)

Looking at `stream_sentence()` again:

```python
async def stream_sentence(...):
    # 🔥 If interrupted, don't start new sentences
    if self.interrupted:                          # <-- Line 222: CHECK FIRST
        logger.info(f"🛑 ... Skipping sentence ... - interrupted flag set")
        return False                              # <-- RETURNS BEFORE RESET!
    
    # 🔥 If this is the first sentence of a new response, reset interrupt flag
    if is_first:                                  # <-- Line 227: RESET SECOND
        self.interrupted = False
```

**THE BUG: The `interrupted` check comes BEFORE the `is_first` reset!**

So even when `is_first=True`:
1. Check: `if self.interrupted:` → TRUE (from previous interruption)
2. Return False immediately
3. **The `if is_first:` block NEVER RUNS because we already returned!**

---

## The Fix

### Option A: Swap the order (Simple)
```python
async def stream_sentence(...):
    # 🔥 If this is the first sentence of a new response, reset interrupt flag FIRST
    if is_first:
        self.interrupted = False
        logger.info(f"🔄 [Call {self.call_control_id}] First sentence - interrupt flag reset")
    
    # Now check if still interrupted (only true if this isn't the first sentence)
    if self.interrupted:
        logger.info(f"🛑 [Call {self.call_control_id}] Skipping sentence '{sentence[:30]}...' - interrupted flag set")
        return False
```

### Option B: Reset before calling stream_sentence (In server.py)
Before streaming the first sentence of a new response, explicitly call:
```python
persistent_tts_session.reset_interrupt_flag()
```

### Option C: Reset after interruption processing completes (In server.py)
After the user's interrupted message is fully processed and before generating a response, reset the flag.

---

## Additional Code Locations to Review

### Where `clear_audio` is called (server.py line 3542)
```python
await persistent_tts_session.clear_audio()
```

### Where responses are generated after interruption (server.py line 3911)
```python
response = await session.process_user_input(accumulated_transcript, stream_callback=stream_sentence_to_tts)
```

### The `reset_interrupt_flag` function that's never used (persistent_tts_service.py line 680)
```python
def reset_interrupt_flag(self):
    """Reset the interrupted flag when starting a new response"""
    self.interrupted = False
```

---

## Recommended Fix

**Fix in `/app/backend/persistent_tts_service.py` lines 221-229:**

Change from:
```python
    # 🔥 If interrupted, don't start new sentences
    if self.interrupted:
        logger.info(f"🛑 [Call {self.call_control_id}] Skipping sentence '{sentence[:30]}...' - interrupted flag set")
        return False
    
    # 🔥 If this is the first sentence of a new response, reset interrupt flag
    if is_first:
        self.interrupted = False
        logger.info(f"🔄 [Call {self.call_control_id}] First sentence - interrupt flag reset")
```

To:
```python
    # 🔥 If this is the first sentence of a new response, ALWAYS reset interrupt flag first
    if is_first:
        self.interrupted = False
        logger.info(f"🔄 [Call {self.call_control_id}] First sentence - interrupt flag reset")
    
    # Now check if still interrupted (only blocks non-first sentences during active interruption)
    if self.interrupted:
        logger.info(f"🛑 [Call {self.call_control_id}] Skipping sentence '{sentence[:30]}...' - interrupted flag set")
        return False
```

This single change swaps the order so that:
1. First sentence of any response ALWAYS resets the flag
2. Only subsequent sentences (during same response) can be blocked by interruption

---

## Summary

| Component | File | Lines | Issue |
|-----------|------|-------|-------|
| Flag check before reset | persistent_tts_service.py | 221-229 | Check happens before reset, so reset never runs |
| Flag set on interrupt | persistent_tts_service.py | 632-633 | Sets `interrupted=True` correctly |
| Flag reset function | persistent_tts_service.py | 680-682 | Exists but never called |
| `is_first` calculation | server.py | 3795 | Correct, but doesn't matter due to order bug |
| Interruption trigger | server.py | 3506-3543 | Sets flag but doesn't reset after |
