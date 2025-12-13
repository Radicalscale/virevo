# Dead Air Feature - Complete Code Map & Analysis

## Expected Behavior (Per User Requirements)
- **7 seconds** silence timeout (normal)
- **25 seconds** if user said "hold on"  
- **Max 2 check-ins** before disconnecting
- Check-in message: "Are you still there?"

---

## 1. DATA MODEL & CONFIGURATION

### File: `backend/models.py`

**Lines 21-26: DeadAirSettings Class**
```python
class DeadAirSettings(BaseModel):
    silence_timeout_normal: int = 7  # ✅ Matches requirement
    silence_timeout_hold_on: int = 25  # ✅ Matches requirement
    max_checkins_before_disconnect: int = 2  # ✅ Matches requirement
    max_call_duration: int = 1500  # 25 minutes max call
    checkin_message: str = "Are you still there?"  # ✅ Matches requirement
```

**Line 123: Integration into AgentSettings**
```python
dead_air_settings: Optional[DeadAirSettings] = Field(default_factory=DeadAirSettings)
```

**⚠️ ISSUE**: When agent is created via UI, `dead_air_settings` may not be included in MongoDB.
If missing, code uses `.get("dead_air_settings", {})` which returns empty dict, then falls back to defaults.

---

## 2. SESSION STATE TRACKING

### File: `backend/calling_service.py`

**Lines 158-167: CallSession Initialization**
```python
def __init__(self, call_id: str, agent_config: dict, ...):
    # Dead air prevention tracking
    self.silence_start_time = None  # When silence started
    self.agent_speaking = False  # Is agent currently speaking?
    self.user_speaking = False  # Is user currently speaking?
    self.checkin_count = 0  # How many check-ins sent this silence period
    self.hold_on_detected = False  # Did user say "hold on"?
    self.call_start_time = time.time()  # Track call start for max duration
    self.last_checkin_time = None  # Last check-in timestamp
    self.max_checkins_reached = False  # Hit max check-ins flag
```

**Lines 330-337: Hold-On Detection**
```python
def _detect_hold_on_phrase(self, text: str) -> bool:
    """Detect if user said 'hold on' or similar phrase"""
    hold_on_phrases = [
        "hold on", "wait", "one moment", "give me a second", 
        "hang on", "just a sec", "one sec", "hold please"
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in hold_on_phrases)
```

**Lines 343-351: Start Silence Tracking**
```python
def start_silence_tracking(self):
    """Start tracking silence after agent stops speaking"""
    if not self.agent_speaking and not self.user_speaking:
        self.silence_start_time = time.time()
        logger.info(f"🔇 Silence tracking started for call {self.call_id}")
```
**STATE**: Only starts if BOTH agent and user are silent.

**Lines 353-357: Agent Speaking Start**
```python
def mark_agent_speaking_start(self):
    """Mark that agent has started speaking"""
    self.agent_speaking = True
    self.silence_start_time = None  # Stop counting silence
    logger.debug(f"🤖 Agent started speaking for call {self.call_id}")
```

**Lines 359-365: Agent Speaking End** ⭐ KEY FUNCTION
```python
def mark_agent_speaking_end(self):
    """Mark that agent has stopped speaking - start silence timer"""
    self.agent_speaking = False
    # Start silence tracking immediately after agent stops
    if not self.user_speaking:
        self.start_silence_tracking()
    logger.debug(f"🤖 Agent stopped speaking for call {self.call_id}")
```
**TRIGGER**: Called by webhook when all playback finishes

**Lines 367-377: User Speaking Tracking**
```python
def mark_user_speaking_start(self):
    """Mark that user has started speaking"""
    self.user_speaking = True
    self.reset_silence_tracking()  # Reset when user starts
    logger.debug(f"👤 User started speaking for call {self.call_id}")

def mark_user_speaking_end(self):
    """Mark that user has stopped speaking"""
    self.user_speaking = False
    # Don't start silence tracking yet - wait for agent to finish responding
    logger.debug(f"👤 User stopped speaking for call {self.call_id}")
```

**Lines 379-383: Calculate Silence Duration**
```python
def get_silence_duration(self) -> float:
    """Get current silence duration in seconds"""
    if self.silence_start_time and not self.agent_speaking and not self.user_speaking:
        return time.time() - self.silence_start_time
    return 0.0
```
**LOGIC**: Only counts silence when both parties silent AND timer started.

**Lines 385-404: Check If Should Send Check-In** ⭐ CRITICAL
```python
def should_checkin(self) -> bool:
    """Check if we should send a check-in message"""
    settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
    silence_timeout = settings.get("silence_timeout_hold_on", 25) if self.hold_on_detected else settings.get("silence_timeout_normal", 7)
    max_checkins = settings.get("max_checkins_before_disconnect", 2)
    
    # If we've already reached max check-ins, don't send more check-ins
    if self.checkin_count >= max_checkins:
        return False
    
    # Check silence duration
    silence_duration = self.get_silence_duration()
    if silence_duration >= silence_timeout:
        # Prevent rapid check-ins (at least 3 seconds between check-ins)
        if self.last_checkin_time is None or (time.time() - self.last_checkin_time) >= 3:
            logger.info(f"⏰ Check-in triggered after {silence_duration:.1f}s silence (threshold: {silence_timeout}s)")
            return True
    
    return False
```
**DEFAULTS**: If `dead_air_settings` missing, uses hardcoded defaults (7, 25, 2).

**Lines 406-415: Check Max Call Duration**
```python
def should_end_call_max_duration(self) -> bool:
    """Check if call should end due to max duration"""
    settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
    max_duration = settings.get("max_call_duration", 1500)  # 25 minutes default
    
    call_duration = time.time() - self.call_start_time
    if call_duration >= max_duration:
        logger.warning(f"⏱️ Max call duration ({max_duration}s) reached for call {self.call_id}")
        return True
    return False
```

**Lines 417-441: Check Max Check-ins Reached**
```python
def should_end_call_max_checkins(self) -> bool:
    """Check if call should end due to max check-ins
    
    After max check-ins are sent, we wait one more silence period.
    If still no response after that period, end the call.
    """
    settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
    max_checkins = settings.get("max_checkins_before_disconnect", 2)
    silence_timeout = settings.get("silence_timeout_hold_on", 25) if self.hold_on_detected else settings.get("silence_timeout_normal", 7)
    
    # If we've reached max check-ins
    if self.checkin_count >= max_checkins and not self.max_checkins_reached:
        # Set flag - we'll wait one more period before ending
        self.max_checkins_reached = True
        logger.warning(f"⚠️ Max check-ins ({max_checkins}) reached - will end call after one more {silence_timeout}s silence period")
        return False
    
    # If flag is set AND we've waited the additional silence period
    if self.max_checkins_reached:
        silence_duration = self.get_silence_duration()
        if silence_duration >= silence_timeout:
            logger.warning(f"🚫 Call ending - max check-ins reached AND additional {silence_timeout}s timeout expired")
            return True
    
    return False
```
**BEHAVIOR**: Wait one full silence period AFTER max check-ins before ending.

**Lines 443-459: Get Check-In Message**
```python
def get_checkin_message(self) -> str:
    """Get the check-in message to send"""
    settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
    max_checkins = settings.get("max_checkins_before_disconnect", 2)
    message = settings.get("checkin_message", "Are you still there?")
    self.checkin_count += 1
    self.last_checkin_time = time.time()
    
    # If this is the last check-in, set the flag
    if self.checkin_count >= max_checkins:
        self.max_checkins_reached = True
        logger.info(f"💬 Sending FINAL check-in #{self.checkin_count}/{max_checkins}: {message}")
        logger.info(f"⚠️ Will end call if no response after next silence timeout")
    else:
        logger.info(f"💬 Sending check-in #{self.checkin_count}/{max_checkins}: {message}")
    
    return message
```

---

## 3. BACKGROUND MONITORING TASK

### File: `backend/dead_air_monitor.py`

**Lines 12-79: monitor_dead_air() - Main Loop** ⭐ THE HEART OF THE SYSTEM
```python
async def monitor_dead_air(session, websocket, call_control_id, stream_sentence_callback, telnyx_service):
    """
    Background task to monitor dead air and trigger check-ins
    
    Args:
        session: CallSession instance
        websocket: WebSocket connection to send messages
        call_control_id: Telnyx call control ID  
        stream_sentence_callback: Callback to stream check-in message to TTS
        telnyx_service: TelnyxService instance to hangup call
    """
    logger.info(f"🔇 Dead air monitoring started for call {call_control_id}")
    
    try:
        while session.is_active:
            # Check max call duration first
            if session.should_end_call_max_duration():
                logger.warning(f"⏱️ Max call duration reached - hanging up call {call_control_id}")
                session.should_end_call = True
                try:
                    await asyncio.sleep(1)  # Brief pause
                    result = await telnyx_service.hangup_call(call_control_id)
                    logger.info(f"📞 Call hung up - result: {result}")
                except Exception as e:
                    logger.error(f"❌ Error hanging up call: {e}")
                break
            
            # Check if we've waited long enough after max check-ins
            if session.should_end_call_max_checkins():
                logger.warning(f"🚫 Max check-ins + timeout reached - hanging up call {call_control_id}")
                session.should_end_call = True
                try:
                    await asyncio.sleep(1)  # Brief pause
                    result = await telnyx_service.hangup_call(call_control_id)
                    logger.info(f"📞 Call hung up - result: {result}")
                except Exception as e:
                    logger.error(f"❌ Error hanging up call: {e}")
                break
            
            # Check if we need to send a check-in
            if session.should_checkin():
                # Send check-in message
                checkin_msg = session.get_checkin_message()
                logger.info(f"💬 Sending check-in message: {checkin_msg}")
                
                # Mark agent as speaking
                session.mark_agent_speaking_start()
                
                # Stream the check-in message through TTS
                if stream_sentence_callback:
                    try:
                        await stream_sentence_callback(checkin_msg)
                        logger.info(f"✅ Check-in message sent")
                    except Exception as e:
                        logger.error(f"❌ Error sending check-in: {e}")
                
                # Mark agent as finished speaking (this will restart silence timer)
                session.mark_agent_speaking_end()
            
            # Check every 500ms for responsiveness
            await asyncio.sleep(0.5)
            
    except asyncio.CancelledError:
        logger.info(f"🔇 Dead air monitoring cancelled for call {call_control_id}")
    except Exception as e:
        logger.error(f"❌ Error in dead air monitoring: {e}")
    finally:
        logger.info(f"🔇 Dead air monitoring stopped for call {call_control_id}")
```

**FLOW**:
1. Loops every 500ms while call active
2. Checks max duration → hangs up if exceeded
3. Checks max check-ins → hangs up if exceeded AND silence timeout passed
4. Checks should_checkin() → sends check-in if True
5. When sending check-in:
   - Marks agent as speaking (stops silence timer)
   - Calls stream_sentence_callback() to play TTS
   - Marks agent as finished (restarts silence timer)

---

## 4. INTEGRATION WITH SERVER

### File: `backend/server.py`

**Lines 1954-2065: Task Initialization in handle_soniox_streaming()**

```python
from dead_air_monitor import monitor_dead_air

# ... inside handle_soniox_streaming() ...

# Lines 2019-2059: Define check_in_callback
async def check_in_callback(message):
    """Callback for sending check-in messages through TTS"""
    nonlocal current_playback_ids
    try:
        telnyx_service = get_telnyx_service()
        agent_config = session.agent_config
        
        settings = agent_config.get("settings", {})
        tts_provider = settings.get("tts_provider")
        
        # TTS provider is REQUIRED
        if not tts_provider:
            logger.error("❌ No TTS provider configured for agent")
            return
        
        use_websocket_tts = False
        if tts_provider == "sesame":
            use_websocket_tts = True
        elif tts_provider == "elevenlabs":
            use_websocket_tts = settings.get("elevenlabs_settings", {}).get("use_websocket_tts", False)
        
        result = await telnyx_service.speak_text(
            call_control_id,
            message,
            agent_config=agent_config,
            use_websocket_tts=use_websocket_tts
        )
        
        if isinstance(result, dict) and "playback_id" in result:
            playback_id = result["playback_id"]
            current_playback_ids.add(playback_id)
            call_states[call_control_id]["current_playback_ids"].add(playback_id)
            
            # Calculate expected duration for check-in message
            word_count = len(message.split())
            estimated_duration = max(0.5, (word_count * 0.15) + 0.3)
            call_states[call_control_id]["playback_expected_end_time"] = time.time() + estimated_duration
            
            logger.info(f"🎬 Check-in playback ID: {playback_id} (expected duration: {estimated_duration:.2f}s)")
    except Exception as e:
        logger.error(f"Error in check-in callback: {e}")

# Lines 2061-2065: Start monitoring task
telnyx_svc = get_telnyx_service()
dead_air_task = asyncio.create_task(
    monitor_dead_air(session, websocket, call_control_id, check_in_callback, telnyx_svc)
)
```

**CRITICAL**: This task starts ONCE at the beginning of the call and runs continuously.

**Lines 4557-4576: Webhook Handler for playback.ended** ⭐ KEY TRIGGER
```python
@api_router.post("/telnyx/webhook")
async def handle_telnyx_webhook(request: Request):
    # ... lots of webhook handling code ...
    
    if event_type == "call.playback.ended":
        playback_id = payload.get("data", {}).get("payload", {}).get("playback_id")
        
        # ... comfort noise handling ...
        
        # Remove this playback from active set (but not comfort noise)
        if playback_id in state["current_playback_ids"]:
            state["current_playback_ids"].remove(playback_id)
            logger.info(f"🔊 Playback {playback_id} ended, {len(state['current_playback_ids'])} remaining")
        
        # If NO more playbacks active, close interruption window
        if len(state["current_playback_ids"]) == 0:
            # Clear agent speaking flags
            state["agent_generating_response"] = False
            state["is_agent_speaking"] = False
            logger.info(f"🔊 All audio finished - interruption window CLOSED")
            
            # Dead air prevention: Mark agent as finished speaking and start silence tracking
            # CRITICAL: Do this regardless of agent_generating_response flag state
            if call_control_id in active_telnyx_calls:
                call_data = active_telnyx_calls[call_control_id]
                if "session" in call_data:
                    session = call_data["session"]
                    session.mark_agent_speaking_end()  # ⭐ THIS STARTS SILENCE TRACKING
                    logger.info(f"🔇 Agent finished speaking - silence tracking started")
```

**TRIGGER FLOW**:
1. Agent finishes generating response → multiple audio chunks queued
2. Each chunk plays → Telnyx sends `call.playback.ended` webhook
3. Each webhook removes playback_id from set
4. When LAST playback ends (set becomes empty):
   - Calls `session.mark_agent_speaking_end()`
   - This calls `start_silence_tracking()`
   - `silence_start_time` is set
5. Background task checks `should_checkin()` every 500ms
6. After 7 seconds, `should_checkin()` returns True
7. Check-in message is sent

---

## 5. DIAGNOSIS: WHY IT'S NOT WORKING

### Possible Issues:

1. **Agent Configuration Missing dead_air_settings**
   - **Evidence**: Database query shows no agents exist
   - **Impact**: Code uses empty dict `{}`, then falls back to defaults
   - **Verdict**: Should still work with defaults (7, 25, 2)

2. **silence_start_time Never Set**
   - **Check**: Is `mark_agent_speaking_end()` being called?
   - **Evidence**: Log shows "🔇 Agent finished speaking - silence tracking started"
   - **Verdict**: ✅ This IS being called

3. **Background Task Not Running**
   - **Check**: Is `monitor_dead_air()` task started?
   - **Evidence**: Log shows "🔇 Dead air monitoring started for call"
   - **Verdict**: ✅ Task IS running

4. **should_checkin() Returning False**
   - **Possible causes**:
     - `silence_start_time` is None
     - `agent_speaking` or `user_speaking` is True
     - `silence_duration < threshold`
     - `checkin_count >= max_checkins`
   - **Most likely**: One of the speaking flags is stuck True

5. **Callback Function Failing Silently**
   - **Check**: Is `check_in_callback()` actually executing?
   - **Evidence**: No "💬 Sending check-in message" in logs
   - **Verdict**: `should_checkin()` is returning False, never reaches callback

### Root Cause Hypothesis:

The `agent_speaking` or `user_speaking` flag is getting stuck in True state, preventing silence detection.

**Test needed**: Add logging to `get_silence_duration()` to see actual values:
```python
def get_silence_duration(self) -> float:
    """Get current silence duration in seconds"""
    if self.silence_start_time and not self.agent_speaking and not self.user_speaking:
        duration = time.time() - self.silence_start_time
        logger.debug(f"🔇 Silence duration: {duration:.1f}s")
        return duration
    else:
        logger.debug(f"🔇 Not counting silence - start_time={self.silence_start_time}, agent_speaking={self.agent_speaking}, user_speaking={self.user_speaking}")
        return 0.0
```

---

## 6. RECOMMENDED FIX

### Option 1: Add Debug Logging (Diagnostic)
Add extensive logging to track state transitions and identify where the system fails.

### Option 2: Ensure Agent Config Has dead_air_settings (Database)
Update existing agents in MongoDB to include proper `dead_air_settings` object.

### Option 3: Fix State Management (If flags stuck)
Review where `agent_speaking` and `user_speaking` are set/cleared to ensure they're not stuck.

### Option 4: Simplify Dead Air Logic (Rebuild)
Remove Redis dependency, use purely local session state with webhook triggers.

---

## 7. TESTING CHECKLIST

Once fixed, verify:
- [ ] Background task starts on call initiation
- [ ] Silence tracking starts when agent finishes speaking
- [ ] Check-in message triggers after 7 seconds of silence
- [ ] Second check-in triggers after another 7 seconds
- [ ] Call ends after 2 check-ins + 7 more seconds of silence
- [ ] "Hold on" detection extends timeout to 25 seconds
- [ ] Max call duration (25 min) triggers hangup

---

## NEXT STEPS

1. **Add diagnostic logging** to `should_checkin()` and `get_silence_duration()`
2. **Run test call** and capture full logs
3. **Identify** which condition is failing
4. **Implement fix** based on findings
5. **Test** with real call to verify behavior
