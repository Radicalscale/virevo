# SYSTEMATIC DEBUGGING PLAN - Dead Air Check-In Feature
## Using "Cracking Creativity" Problem-Solving Framework

---

## EXECUTIVE SUMMARY

**Problem:** Dead air check-in feature fails to trigger when user is silent for 7+ seconds  
**Root Cause (Hypothesis):** `call_states` dictionary is empty when webhooks arrive, causing session lookup failures  
**Impact:** Calls never check in on silent users, never hang up after max check-ins  
**Solution Approach:** Multi-layered fix addressing state management, flag tracking, and diagnostic logging

---

## PHASE 1: PROBLEM IDENTIFICATION (5 WHYS)

### 5 Whys Analysis:
1. **Why don't check-ins trigger?** → Monitor loop condition never passes
2. **Why doesn't condition pass?** → `agent_speaking` or `user_speaking` flags stuck True
3. **Why are flags stuck?** → Methods to reset flags not called properly
4. **Why aren't methods called?** → Webhook handler can't find session in `call_states`
5. **Why can't it find session?** → `call_states` dictionary is EMPTY (`[]`)

### Evidence from Logs:
```
05:01:40,974 - ERROR - ❌ No state found in call_states for v3:86pydBuN8k3_qfy1e4Qt7htDTQuFWFVUgRLd8xPvievVr4sE-RhkEw
05:01:40,974 - ERROR - ❌ Available keys: []
05:01:40,974 - INFO - ✅ Found session in active_telnyx_calls as fallback
05:01:40,975 - INFO - ⏱️ Silence timer STARTED (fallback, agent wasn't marked as speaking)
```

Key observation: "agent wasn't marked as speaking" - the `agent_speaking` flag was never set!

### Evidence from Recording:
- 00:50-01:34: **44 SECONDS OF SILENCE** with NO check-in
- Expected: Check-in at 00:57 (7 seconds after silence start)
- Expected: Check-in at 01:04 (another 7 seconds)
- Expected: Hang up at 01:11 (max 2 check-ins reached)
- Actual: Nothing happened

---

## PHASE 2: ROOT CAUSE ANALYSIS (Fishbone Diagram)

### EFFECT: Dead Air Check-in Not Triggering

### CAUSES BY CATEGORY:

#### 1. STATE MANAGEMENT ISSUES ⚠️ **PRIMARY SUSPECT**
- `call_states` is empty when webhooks arrive
- Session stored in `active_telnyx_calls` during WebSocket init
- Session stored in `call_states` during main flow init
- Two different initialization paths creating state split

#### 2. FLAG MANAGEMENT ISSUES
- `agent_speaking` flag never set to True when playback starts
- No `mark_agent_speaking_start()` call when audio begins
- Fallback logic doesn't set flags properly

#### 3. TIMING/RACE CONDITIONS
- Webhooks arrive before `call_states` is fully initialized
- Multiple async operations completing out of order
- Session created twice in different contexts

#### 4. MONITOR LOGIC ISSUES
- Condition `if not session.agent_speaking and not session.user_speaking` always False
- Monitor accessing stale session object
- No diagnostic logging to show flag states

---

## PHASE 3: CODE ANALYSIS

### Key Discovery 1: Dual Initialization
**Line 1980-1985 (server.py):** Session stored in `call_states` during WebSocket handler
```python
call_states[call_control_id] = {
    "agent_generating_response": False,
    "current_playback_ids": set(),
    "session": session
}
```

But logs show this dictionary is EMPTY later!

### Key Discovery 2: Missing Flag Management
**Problem:** No code sets `session.agent_speaking = True` when playback STARTS
**Location to fix:** Around line 2000-2100 where playback begins

### Key Discovery 3: Fallback Logic Flaw
**Line 4576-4581:** Fallback finds session but says "agent wasn't marked as speaking"
```python
if session.agent_speaking:
    session.mark_agent_speaking_end()
elif not session.user_speaking:
    session.start_silence_tracking()
    logger.info(f"⏱️ Silence timer STARTED (fallback, agent wasn't marked as speaking)")
```

This reveals the flag was NEVER set to True!

---

## PHASE 4: SOLUTION GENERATION & PRIORITIZATION

### Solution 1: Fix `call_states` Persistence ⭐ **HIGH PRIORITY**
**Problem:** Dictionary becomes empty  
**Fix:** Investigate WHERE it's being cleared or why initialization fails  
**Hypothesis:** Session might be created before `call_states` is initialized  
**Action:** Add logging at every point `call_states` is accessed

### Solution 2: Add `mark_agent_speaking_start()` Call ⭐ **HIGH PRIORITY**  
**Problem:** `agent_speaking` flag never set to True  
**Fix:** Call `session.mark_agent_speaking_start()` when playback begins  
**Location:** After line 2050 where playback_start API is called  
**Impact:** Enables proper flag management for the entire flow

### Solution 3: Add Diagnostic Logging ⭐ **CRITICAL FOR DEBUGGING**
**Problem:** Can't see what's happening in the monitor loop  
**Fix:** Add periodic logging as suggested by previous engineer  
**Location:** `dead_air_monitor.py` line 62-65  
**Output:** Show flag states, silence duration, and check-in status

### Solution 4: Simplify State Management 🔄 **FUTURE REFACTOR**
**Problem:** Dual storage creating confusion  
**Fix:** Use single source of truth  
**Complexity:** Requires architectural change  
**Priority:** Lower (do after immediate fixes work)

---

## PHASE 5: IMPLEMENTATION PLAN

### STEP 1: Add Comprehensive Diagnostic Logging (DO FIRST)
**Files:** `dead_air_monitor.py`, `calling_service.py`  
**Purpose:** Make the invisible visible - see what's actually happening

**Changes:**
1. In `dead_air_monitor.py` (line 62):
   ```python
   # Log every 5 seconds to avoid spam
   current_time = time.time()
   if int(current_time) % 5 == 0:
       silence_dur = session.get_silence_duration()
       logger.info(f"🔍 MONITOR: agent_speaking={session.agent_speaking}, user_speaking={session.user_speaking}, silence={silence_dur:.1f}s, checkin_count={session.checkin_count}")
   ```

2. In `calling_service.py` `should_checkin()` method (line ~400):
   ```python
   # Log when silence is building up
   if silence_duration >= 5:
       logger.info(f"🔍 SHOULD_CHECKIN: silence={silence_duration:.1f}s, threshold={silence_timeout}s, checkins={self.checkin_count}/{max_checkins}, would_trigger={silence_duration >= silence_timeout}")
   ```

### STEP 2: Fix Agent Speaking Flag Management
**File:** `server.py`  
**Line:** Around 2050-2100 (where playback starts)

**Add:**
```python
# Mark agent as speaking when playback starts
if call_control_id in active_telnyx_calls:
    call_data = active_telnyx_calls[call_control_id]
    if "session" in call_data and call_data["session"]:
        call_data["session"].mark_agent_speaking_start()
        logger.info(f"🎤 MARKED AGENT AS SPEAKING (playback started)")
```

Also add the method to `CallSession` if it doesn't exist:
```python
def mark_agent_speaking_start(self):
    """Mark that agent started speaking"""
    self.agent_speaking = True
    logger.info(f"🔊 Agent speaking flag SET TO TRUE")
```

### STEP 3: Fix call_states Initialization
**File:** `server.py`  
**Line:** 1980-1985

**Add defensive logging:**
```python
# Store in global state
call_states[call_control_id] = {
    "agent_generating_response": False,
    "current_playback_ids": set(),
    "session": session
}
logger.info(f"✅ STORED in call_states: {call_control_id}, total keys now: {len(call_states)}")
logger.info(f"✅ Session ID: {id(session)}")
```

**Add verification in webhook handler (line 4565):**
```python
state = call_states.get(call_control_id)
logger.info(f"🔍 WEBHOOK: Looking for {call_control_id} in call_states")
logger.info(f"🔍 WEBHOOK: call_states has {len(call_states)} keys: {list(call_states.keys())[:3]}")
```

### STEP 4: Test with New Logs
**Run a test call and collect logs to see:**
1. Is `call_states` being populated?
2. Is `agent_speaking` being set to True?
3. What's happening in the monitor loop?
4. Why isn't `should_checkin()` returning True?

---

## PHASE 6: EXPECTED OUTCOMES

### After Step 1 (Logging):
- See real-time flag states in monitor loop
- Identify exactly which condition is failing
- Understand timing of state changes

### After Step 2 (Flag Fix):
- `agent_speaking` flag properly set when audio plays
- `mark_agent_speaking_end()` called when audio finishes
- Silence timer starts correctly

### After Step 3 (State Fix):
- `call_states` remains populated throughout call
- Webhook handler finds session reliably
- No more fallback to `active_telnyx_calls`

### Final Success Criteria:
✅ Check-in sent after 7 seconds of user silence  
✅ Second check-in sent after another 7 seconds  
✅ Call hangs up after max check-ins (2) with no response  
✅ Counter resets only on meaningful user input  
✅ Logs show clear state transitions

---

## PHASE 7: RISK ASSESSMENT

### HIGH RISK:
- Adding `mark_agent_speaking_start()` calls might break interruption detection
- Mitigation: Test carefully with user interruptions

### MEDIUM RISK:
- Logging every 5 seconds might still be too verbose
- Mitigation: Use `int(current_time) % 10 == 0` for 10-second intervals

### LOW RISK:
- Diagnostic logging is read-only
- State initialization fixes are defensive

---

## APPENDIX: Key Code Locations

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Monitor loop | dead_air_monitor.py | 60-70 | Check-in trigger logic |
| Flag check | dead_air_monitor.py | 64 | `if not agent_speaking and not user_speaking` |
| should_checkin | calling_service.py | 388-417 | Determines if check-in needed |
| Silence timer start | calling_service.py | 343-361 | Manages silence tracking |
| Webhook handler | server.py | 4550-4596 | Receives playback.ended |
| State init | server.py | 1980-1985 | Creates call_states entry |
| Playback start | server.py | 2000-2100 | Triggers audio playback |

---

**Next Step:** Implement Step 1 (Logging) and run a test call to validate hypotheses.
