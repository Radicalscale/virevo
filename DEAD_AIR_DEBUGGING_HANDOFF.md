# Dead Air Check-In System - Debugging Handoff Document

## Problem Statement

**Goal**: Implement a dead air check-in system that:
1. Detects when user is silent for 7+ seconds after AI finishes speaking
2. Sends "Are you still there?" check-in messages
3. Tracks check-in count and ends call after max check-ins (default: 2)
4. Resets counter only when user gives meaningful response (not just "yeah/okay")

**Current Status (LATEST UPDATE - BROKEN AGAIN)**: 
- ❌ **Check-ins DO NOT trigger at all - REGRESSION**
- ❌ Previous fix removed too much logging, can't diagnose
- ❌ Likely issue: `agent_speaking` or `user_speaking` stuck True
- ❌ Or: `get_silence_duration()` returning 0
- ✅ Latency is acceptable (fixed)
- ✅ Recording works properly (fixed)

**PREVIOUS STATUS (before latest changes):**
- ✅ Check-ins triggered after 7 seconds of silence
- ✅ Multiple check-ins sent during a call
- ❌ Check-in counter did NOT increment properly - stayed at 0 or reset to 1
- ❌ Call never ended after reaching max check-ins

---

## Architecture Overview

### Key Components

1. **`CallSession` (calling_service.py)**
   - Manages call state, variables, conversation history
   - Tracks `checkin_count`, `agent_speaking`, `user_speaking`, `silence_start_time`
   - Methods: `should_checkin()`, `get_checkin_message()`, `mark_agent_speaking_end()`, etc.

2. **`dead_air_monitor` (dead_air_monitor.py)**
   - Background asyncio task that runs every 500ms
   - Checks if silence duration exceeds threshold
   - Calls `session.should_checkin()` and sends check-in via `get_checkin_message()`

3. **Webhook Handler (server.py)**
   - Receives `playback.ended` webhooks from Telnyx
   - Uses Redis to track when ALL playbacks finish
   - Calls `session.mark_agent_speaking_end()` to start silence timer

4. **State Management**
   - `call_states[call_control_id]` = dict with `current_playback_ids`, `session` reference
   - `active_telnyx_calls[call_control_id]` = dict with WebSocket, session, etc.
   - Redis tracks playback counts for multi-worker coordination (but we're single worker)

---

## What We've Tried (Chronologically)

### Attempt 1: Variable Extraction Order Bug
- **Problem**: Variables were checked BEFORE extraction
- **Fix**: Extract variables BEFORE calling `_follow_transition()`
- **Result**: ✅ WORKED - Variables now extract properly

### Attempt 2-5: Dead Air Timer Not Starting
- **Problem**: Silence timer only started once per call
- **Root Cause**: `call_states[call_control_id]` was being lost between webhook arrivals
- **Attempted Fixes**:
  1. Store session in `call_states` dict
  2. Check `active_telnyx_calls` as fallback
  3. Use Redis playback count instead of local state
  4. Add extensive logging to trace state lifecycle
- **Result**: ✅ WORKED - Silence timer now starts after EVERY agent response

### Attempt 6: Check-in Counter Not Incrementing
- **Problem**: Logs show `checkins=0/2` or `checkins=1/2` repeatedly, never reaching 2
- **Root Cause**: Counter was being reset when user started speaking (even for "yeah")
- **Attempted Fix**: 
  1. Created `reset_silence_timer_only()` to avoid resetting counter
  2. Modified `mark_user_speaking_start()` to use new function
  3. Added acknowledgment detection in `process_user_input()`
  4. Only reset counter for meaningful responses (>2 words, not acknowledgments)
- **Result**: ❌ **DID NOT WORK** - Counter still not incrementing properly

---

## Current Code State

### Key Files Modified

**`calling_service.py` (lines 343-390)**
```python
def reset_silence_tracking(self):
    """Reset silence tracking when user gives meaningful response"""
    if self.silence_start_time:
        logger.info(f"⏱️ SILENCE TIMER RESET (user gave meaningful response)")
    self.silence_start_time = None
    self.checkin_count = 0  # Reset check-in count
    self.hold_on_detected = False
    self.max_checkins_reached = False

def reset_silence_timer_only(self):
    """Reset only the silence timer when user starts speaking (don't reset checkin_count)"""
    if self.silence_start_time:
        logger.info(f"⏱️ SILENCE TIMER RESET (user started speaking)")
    self.silence_start_time = None

def mark_user_speaking_start(self):
    """Mark that user started speaking"""
    self.user_speaking = True
    # DON'T reset checkin_count here - only reset when user gives meaningful response
    self.reset_silence_timer_only()

def get_checkin_message(self) -> str:
    """Get check-in message and increment counter"""
    settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
    message = settings.get("checkin_message", "Are you still there?")
    
    self.checkin_count += 1  # INCREMENT COUNTER HERE
    self.last_checkin_time = time.time()
    
    max_checkins = settings.get("max_checkins_before_disconnect", 2)
    if self.checkin_count >= max_checkins:
        self.max_checkins_reached = True
        logger.info(f"💬 Sending FINAL check-in #{self.checkin_count}/{max_checkins}: {message}")
    else:
        logger.info(f"💬 Sending check-in #{self.checkin_count}/{max_checkins}: {message}")
    
    return message
```

**`calling_service.py` (process_user_input, lines 561-577)**
```python
# Check if user gave meaningful response (not just acknowledgment)
acknowledgment_words = ['yeah', 'yes', 'okay', 'ok', 'yep', 'sure', 'uh-huh', 'mhm', 'go ahead']
user_words = user_text.lower().strip().split()
is_acknowledgment = (
    len(user_words) <= 2 and 
    any(word in acknowledgment_words for word in user_words)
)

if not is_acknowledgment:
    # User gave meaningful response - reset check-in tracking
    self.reset_silence_tracking()
    logger.info(f"✅ User gave meaningful response, resetting check-in counter")
else:
    logger.info(f"⚠️ User gave acknowledgment only, keeping check-in counter at {self.checkin_count}")
```

**`server.py` (webhook handler, lines 4550-4596)**
```python
# Use Redis playback count to determine if all audio finished
redis_svc = redis_service
remaining_playbacks = redis_svc.remove_playback_id(call_control_id, playback_id)

if remaining_playbacks == 0:
    logger.info(f"🔊 ALL PLAYBACKS FINISHED (via Redis) - attempting to start silence timer")
    
    # Try to get session from call_states
    state = call_states.get(call_control_id)
    
    if state and "session" in state and state["session"] is not None:
        session = state["session"]
        if session.agent_speaking:
            session.mark_agent_speaking_end()
            logger.info(f"⏱️ Agent done speaking, silence timer STARTED")
```

---

## Lessons Learned

### What Works ✅

1. **Redis playback tracking is reliable**
   - Redis correctly shows "0 remaining" when all audio finishes
   - Using `remaining_playbacks == 0` as trigger works well

2. **Session reference in `call_states` works**
   - Storing `session` in `call_states[call_control_id]["session"]` allows webhook handler to access it
   - This works even though we're single worker

3. **Silence timer starts reliably now**
   - After using Redis count, timer starts after EVERY agent response
   - `mark_agent_speaking_end()` is being called properly

4. **User speaking detection works**
   - `mark_user_speaking_start()` called when user starts speaking
   - `mark_user_speaking_end()` called when `speech_final` received from Deepgram

### What Doesn't Work ❌

1. **Check-in counter logic is fundamentally broken**
   - Counter increments in `get_checkin_message()` (line 459)
   - But logs show it stays at 0 or resets to 1
   - This suggests the session object is being replaced or reset somehow

2. **Acknowledgment detection may not be working**
   - Even with the new logic, counter still resets
   - Possible issues:
     - `process_user_input()` is called multiple times per user response?
     - Session object is being recreated?
     - Counter is being reset elsewhere?

3. **State management is fragile**
   - `call_states[call_control_id]` sometimes disappears
   - Multiple places create/modify this dict
   - Hard to track when/where it gets cleared

### Key Insights

1. **Single Worker Architecture**
   - We confirmed `--workers 1` in supervisor config
   - Redis connection fails, falls back to in-memory
   - All webhooks and WebSockets go to same process
   - **So multi-worker code is unnecessary complexity**

2. **The Counter Increment is NOT the Problem**
   - Line 459 `self.checkin_count += 1` IS being executed (logs show "Sending check-in #1/2")
   - The problem is it's being RESET somewhere between check-ins

3. **Timing Flow**
   ```
   1. Agent finishes speaking → silence timer starts
   2. 7 seconds pass → should_checkin() returns True
   3. dead_air_monitor calls get_checkin_message() → counter = 1
   4. Check-in is sent via TTS
   5. User says "yeah" → mark_user_speaking_start() called → reset_silence_timer_only()
   6. User finishes speaking → mark_user_speaking_end() called
   7. process_user_input() called → checks if acknowledgment
   8. If acknowledgment → should NOT reset counter
   9. But somehow counter is back to 0 before next check-in
   ```

4. **The Session Object May Be Getting Replaced**
   - If `CallSession` is being recreated, counter would reset to 0
   - Need to verify session object identity persists across check-ins

---

## Debugging Strategy for Next Agent

### Step 1: Verify Session Object Persistence

Add logging to track session object ID:

```python
# In calling_service.py __init__
self.session_id = id(self)
logger.info(f"🆔 Created CallSession with ID: {self.session_id}")

# In get_checkin_message
logger.info(f"🆔 get_checkin_message called on session {self.session_id}, counter BEFORE: {self.checkin_count}")
self.checkin_count += 1
logger.info(f"🆔 get_checkin_message session {self.session_id}, counter AFTER: {self.checkin_count}")

# In reset_silence_tracking
logger.info(f"🆔 reset_silence_tracking called on session {self.session_id}, counter BEFORE: {self.checkin_count}")
self.checkin_count = 0
logger.info(f"🆔 reset_silence_tracking session {self.session_id}, counter AFTER: {self.checkin_count}")
```

**If session ID changes between check-ins**: Session is being recreated → Find where and why

**If session ID stays same but counter resets**: Something else is calling `reset_silence_tracking()` or directly setting `checkin_count = 0`

### Step 2: Search for All Places Counter is Modified

```bash
grep -n "checkin_count" /app/backend/calling_service.py
grep -n "checkin_count" /app/backend/server.py
grep -n "reset_silence_tracking\|checkin_count = 0" /app/backend/*.py
```

Look for:
- Direct assignment: `self.checkin_count = 0`
- Method calls: `reset_silence_tracking()` 
- Object recreation: `session = CallSession(...)`

### Step 3: Check if `process_user_input()` is Called Multiple Times

Add counter in `process_user_input()`:

```python
async def process_user_input(self, user_text: str, stream_callback=None):
    logger.info(f"🔢 process_user_input ENTRY #{id(self)} - checkin_count={self.checkin_count}, text='{user_text}'")
    # ... rest of code
    logger.info(f"🔢 process_user_input EXIT #{id(self)} - checkin_count={self.checkin_count}")
```

If this is called multiple times for one user utterance, that could be resetting the counter.

### Step 4: Alternative Approach - Store Counter Externally

Instead of storing counter in session object, store in `call_states`:

```python
# When initializing call_states
call_states[call_control_id] = {
    "checkin_count": 0,  # Store here instead
    "session": session,
    # ...
}

# In get_checkin_message
state = call_states.get(self.call_id)  # Assuming call_id = call_control_id
if state:
    state["checkin_count"] += 1
    logger.info(f"💬 Sending check-in #{state['checkin_count']}/2")
    return message

# In should_checkin
state = call_states.get(self.call_id)
if state:
    checkin_count = state.get("checkin_count", 0)
    if checkin_count >= max_checkins:
        return False
```

This way, even if session object is replaced, counter persists.

---

## Recommended Next Steps

### Priority 1: Find Why Counter Resets

1. Add session ID logging (Step 1 above)
2. Run test call with user staying silent for 2+ check-ins
3. Analyze logs to see if:
   - Session ID changes (→ session replaced)
   - Session ID stays same but counter resets (→ find where)

### Priority 2: Consider Architectural Change

If session object is being recreated (likely culprit), either:
- **Option A**: Fix session recreation (harder, need to find root cause)
- **Option B**: Move counter to external storage like `call_states` (easier, more reliable)

### Priority 3: Simplify State Management

The current code has too many places tracking state:
- `CallSession` object (in memory)
- `call_states` dict (in memory)
- `active_telnyx_calls` dict (in memory)
- Redis (external, but connection failing)

Consider consolidating to ONE source of truth.

---

## Test Case for Verification

**Scenario**: User stays completely silent

**Expected Behavior**:
1. AI speaks
2. Wait 7 seconds → Check-in #1: "Are you still there?" (counter = 1)
3. User stays silent
4. Wait 7 more seconds → Check-in #2: "Are you still there?" (counter = 2)
5. User stays silent
6. Max reached → Call ends

**Log Patterns to Look For**:
```
💬 Sending check-in #1/2: Are you still there?
[7 seconds pass]
💬 Sending check-in #2/2: Are you still there?  ← Should show #2, not #1!
🚫 Max check-ins + timeout reached - hanging up call
```

**Current Bug**:
```
💬 Sending check-in #1/2: Are you still there?
[7 seconds pass]
💬 Sending check-in #1/2: Are you still there?  ← WRONG! Shows #1 again
[repeats forever, never hangs up]
```

---

## Code Locations Reference

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| CallSession class | calling_service.py | 121-500 | Main session management |
| Counter increment | calling_service.py | 459 | `self.checkin_count += 1` |
| Counter reset | calling_service.py | 350 | In `reset_silence_tracking()` |
| Timer reset only | calling_service.py | 355-361 | `reset_silence_timer_only()` |
| User speaking start | calling_service.py | 376-383 | Calls `reset_silence_timer_only()` |
| Acknowledgment check | calling_service.py | 564-580 | In `process_user_input()` |
| Check-in trigger | calling_service.py | 388-417 | `should_checkin()` method |
| Check-in send | dead_air_monitor.py | 52-69 | Calls `get_checkin_message()` |
| Silence timer start | server.py | 4550-4596 | Webhook handler |
| Call states init | server.py | 1980-1985 | Creates session reference |

---

## Environment Info

- Single worker: `--workers 1`
- Redis: Fails to connect, falls back to in-memory
- Python: 3.11
- FastAPI + Uvicorn
- Async/await throughout

---

## CRITICAL UPDATE - Latest Regression

### What Broke in Latest Attempt

**Problem**: Removed too much logging trying to fix latency. Now check-ins don't trigger at all.

**Root Cause**: Can't diagnose because no logs show:
- Whether `agent_speaking` or `user_speaking` is True/False
- What `get_silence_duration()` returns
- Whether `should_checkin()` is even being called

**The Code That's Failing**:
```python
# In dead_air_monitor.py line 64-65
if not session.agent_speaking and not session.user_speaking:
    if session.should_checkin():
```

If either flag is stuck True, this never executes.

**Immediate Fix Needed**:

Add back minimal logging in `dead_air_monitor.py` around line 62:

```python
silence_duration = session.get_silence_duration()

# ADD THIS LOGGING (only every 5 seconds to avoid spam)
if int(time.time()) % 5 == 0:
    logger.info(f"🔍 Monitor: agent_speaking={session.agent_speaking}, user_speaking={session.user_speaking}, silence={silence_duration:.1f}s")

if not session.agent_speaking and not session.user_speaking:
    if session.should_checkin():
        # ... rest of code
```

Also add back logging in `should_checkin()`:

```python
def should_checkin(self) -> bool:
    settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
    silence_timeout = settings.get("silence_timeout_hold_on", 25) if self.hold_on_detected else settings.get("silence_timeout_normal", 7)
    max_checkins = settings.get("max_checkins_before_disconnect", 2)
    
    if self.checkin_count >= max_checkins:
        return False
    
    silence_duration = self.get_silence_duration()
    
    # ADD THIS BACK
    if silence_duration >= 5:  # Only log when getting close
        logger.info(f"🔍 should_checkin: silence={silence_duration:.1f}s, threshold={silence_timeout}s, checkins={self.checkin_count}/{max_checkins}")
    
    if silence_duration >= silence_timeout:
        # ...
```

### Most Likely Culprits

1. **`user_speaking` is stuck True**
   - `mark_user_speaking_end()` not being called
   - Was added recently at line 3289 in server.py
   - Might not be executing

2. **`agent_speaking` is stuck True**
   - `mark_agent_speaking_end()` not being called reliably
   - Webhook handler finding session but flag not updating

3. **`silence_start_time` is None**
   - `get_silence_duration()` returns 0 if `silence_start_time` is None
   - Timer not starting even though logs say it is

### Quick Test

Add this at top of dead_air_monitor loop:

```python
while session.is_active:
    logger.info(f"🔍 Loop: agent={session.agent_speaking}, user={session.user_speaking}, silence_start={session.silence_start_time}, checkin_count={session.checkin_count}")
    
    # ... rest of loop
```

This will spam logs but immediately show what's stuck.

---

## Good Luck!

The core logic SHOULD work based on the code. The counter increments in `get_checkin_message()`, and we've protected against resets on acknowledgments. But something is still resetting it between check-ins.

Focus on **session object identity** and **call state lifecycle**. Those are the most likely culprits.

If you get stuck, consider the "store counter in `call_states`" approach as a pragmatic workaround.
