# System Functionality Map - Before TTS Latency Fix

## CRITICAL: Features That Must NOT Break

### 1. Dead Air Detection System
**Location:** `backend/dead_air_monitor.py`, `backend/calling_service.py`

**How it works:**
- Monitors silence duration when neither agent nor user is speaking
- Uses `session.agent_speaking` and `session.user_speaking` flags
- Triggers check-ins after configurable timeout (default 7s or 25s if "hold on" detected)
- Sends up to N check-ins (configurable, default 2) before hanging up

**Key Timing Parameters:**
- `silence_timeout_normal`: 7 seconds (default)
- `silence_timeout_hold_on`: 25 seconds (default)
- `max_checkins_before_disconnect`: 2 (default)
- `max_call_duration`: 1500 seconds / 25 minutes (default)

**State Tracking:**
```python
# In CallSession class
self.agent_speaking = False  # Is agent currently speaking?
self.user_speaking = False   # Is user currently speaking?
self.silence_start_time = None  # When did silence start?
self.checkin_count = 0  # How many check-ins sent this silence period
self.last_message_was_checkin = False  # Was last message a check-in?
self.max_checkins_reached = False  # Have we hit max check-ins?
```

**Critical Methods:**
- `mark_agent_speaking_start()` - Called when TTS playback starts
- `mark_agent_speaking_end()` - Called when TTS playback ends
- `mark_user_speaking_start()` - Called when user STT detects speech
- `mark_user_speaking_end()` - Called when user STT detects silence
- `start_silence_tracking()` - Starts silence timer
- `reset_silence_tracking()` - Resets timer and counter on meaningful response
- `should_checkin()` - Returns True if check-in should be sent

**Integration Points:**
1. TTS playback must call `mark_agent_speaking_start()` when audio starts
2. TTS playback must call `mark_agent_speaking_end()` when audio finishes
3. Silence timer starts IMMEDIATELY after agent finishes speaking
4. Check-ins are sent via the same TTS pipeline as regular messages

**HOW TTS CHANGES COULD BREAK THIS:**
- If we don't properly signal when agent speaking starts/ends, silence tracking will be wrong
- If check-in messages don't go through TTS pipeline correctly, they won't be spoken
- If timing changes affect when `mark_agent_speaking_end()` is called, dead air detection breaks
- The `speed` parameter (1.1) may be calibrated to work with silence detection timing

---

### 2. Interruption Handling (Barge-In)
**Location:** `backend/server.py` (Telnyx webhook handler)

**How it works:**
- User speech is detected via Deepgram/Soniox STT
- When user speaks during agent playback, system detects "interruption"
- All active TTS playbacks are stopped immediately
- Agent's speaking flag is cleared
- User's input is processed

**State Tracking:**
```python
# In server.py call_states (now backed by Redis)
call_states[call_control_id] = {
    "agent_speaking": False,
    "user_speaking": False,
    "active_playbacks": [],  # List of active playback_ids
    "interruption_window": True/False,
    # ... other state
}
```

**Critical Flow:**
1. TTS generates audio → Sent to Telnyx for playback
2. Telnyx returns `playback_id` and starts playing
3. System tracks `active_playbacks` list
4. If user speaks while playbacks are active:
   - Stop all active playbacks via Telnyx API
   - Clear agent_speaking flag
   - Process user input

**Integration with Redis (Multi-Worker Fix):**
- `redis_service.increment_playback_count(call_id)` when playback starts
- `redis_service.decrement_playback_count(call_id)` when playback ends
- `redis_service.get_playback_count(call_id)` to check if agent is speaking
- `redis_service.set_checkin_in_progress(call_id)` when check-in is sent
- `redis_service.get_checkin_in_progress(call_id)` to detect check-in playback end

**HOW TTS CHANGES COULD BREAK THIS:**
- If we change how playback tracking works, interruption detection breaks
- If we don't properly increment/decrement playback counts, agent_speaking flag is wrong
- If we change streaming behavior, active_playbacks list might not be accurate
- WebSocket implementation must preserve playback ID tracking

---

### 3. Node Transitioning (Call Flow)
**Location:** `backend/calling_service.py` (`_process_call_flow_streaming()`)

**How it works:**
- Agent follows a visual flow of conversation nodes
- Each node has content (script or prompt) and transitions to next nodes
- Transitions can be:
  - Automatic (goes to next node after speaking)
  - Conditional (based on extracted variables or user response)
  - Manual (press digit nodes, logic split nodes)

**Node Types:**
- `conversation` - Standard dialogue node
- `collect_input` - Gather user input (email, phone, etc.)
- `extract_variable` - Extract specific data from user response
- `function` - Execute webhook/API call
- `ending` - End the call
- `call_transfer` - Transfer to another number
- `press_digit` - DTMF menu
- `logic_split` - Conditional branching

**State Tracking:**
```python
# In CallSession
self.current_node_id = None  # Which node are we on?
self.session_variables = {}  # Variables extracted during call
self.conversation_history = []  # Full conversation with node IDs
```

**Critical Flow:**
1. User speaks → Process input
2. Extract variables if needed
3. Evaluate transition conditions
4. Move to next node
5. Generate response from new node
6. Send response via TTS
7. Wait for user response
8. Repeat

**Content Modes:**
- `script` mode: Return exact text (no LLM processing)
- `prompt` mode: Use LLM to generate response based on instructions

**HOW TTS CHANGES COULD BREAK THIS:**
- Node content must be streamed correctly (sentence by sentence)
- Check-in messages must not interfere with node transitions
- If TTS timing changes, node transitions might happen too early/late
- WebSocket implementation must preserve sentence streaming capability

---

## TTS Integration Points

### Current Implementation (ElevenLabs HTTP Streaming)
**Location:** `backend/server.py` line ~3540

**Configuration:**
```python
data = {
    "text": text,
    "model_id": "eleven_flash_v2_5",
    "voice_settings": {
        "stability": 0.7,
        "similarity_boost": 0.75,
        "use_speaker_boost": True,
        "speed": 1.1  # ⚠️ DO NOT CHANGE - calibrated for dead air
    },
    "apply_text_normalization": "on",
    "enable_ssml_parsing": True,
    "optimize_streaming_latency": 4  # ✅ SAFE TO CHANGE (0-4 scale)
}
```

**Current Flow:**
1. LLM generates sentence
2. `stream_sentence_callback()` is called with sentence text
3. `generate_elevenlabs_audio()` is called
4. Audio chunks are streamed from ElevenLabs
5. Audio is base64-encoded and sent to Telnyx
6. Telnyx returns playback_id
7. `redis_service.increment_playback_count()` is called
8. `session.mark_agent_speaking_start()` is called
9. When Telnyx webhook `call.playback.ended` arrives:
   - `redis_service.decrement_playback_count()`
   - If count reaches 0, `session.mark_agent_speaking_end()`
   - Silence tracking starts

**Critical Hooks:**
- `mark_agent_speaking_start()` must be called when first audio starts
- `mark_agent_speaking_end()` must be called when last audio ends
- Playback count tracking must be accurate for multi-worker coordination

---

## SAFE CHANGES for TTS Latency Optimization

### ✅ SAFE: Change `optimize_streaming_latency` from 4 to 0
- **Why safe:** This is a documented ElevenLabs API parameter
- **What it does:** 0 = lowest latency mode, 4 = highest quality mode
- **Impact:** Should reduce connection establishment time (315-424ms)
- **Does NOT affect:** Dead air timing, interruption handling, node transitions
- **Location:** `backend/server.py` line 3570

### ✅ SAFE: Implement immediate first-chunk streaming
- **Why safe:** Doesn't change overall flow, just reduces perceived latency
- **What it does:** Start Telnyx playback as soon as first audio chunk arrives
- **Impact:** User hears audio faster (reduces "total pause")
- **Does NOT affect:** Dead air timing (silence starts when playback ends)
- **Requires:** Ensure `mark_agent_speaking_start()` is called correctly

### ⚠️ CAREFUL: Switch to ElevenLabs WebSocket API
- **Why careful:** Major architectural change
- **Benefits:** 
  - Eliminates 315-424ms connection overhead per sentence
  - True streaming (no connection handshake per request)
  - Lower latency overall
- **Risks:**
  - Must preserve playback count tracking
  - Must preserve interruption handling
  - Must preserve sentence-by-sentence streaming for flow logic
  - Must ensure `mark_agent_speaking_start/end()` are called correctly
- **Implementation:**
  - Open WebSocket connection at call start
  - Keep connection alive during call
  - Stream text chunks to WebSocket
  - Receive audio chunks back
  - Still send to Telnyx with playback tracking

---

## UNSAFE CHANGES That Would Break System

### ❌ UNSAFE: Change `speed` from 1.1
- **Why:** Dead air timing may be calibrated for this speed
- **Risk:** Check-ins might fire too early/late
- **User said:** "Don't touch the speed that has nothing to do with dead-air"
- **Conclusion:** The user knows this is important, leave it alone

### ❌ UNSAFE: Remove playback count tracking
- **Why:** Multi-worker coordination depends on Redis playback counts
- **Risk:** Dead air detection and interruption handling break completely

### ❌ UNSAFE: Skip `mark_agent_speaking_start/end()` calls
- **Why:** Dead air detection depends on these flags
- **Risk:** Silence tracking starts at wrong time, check-ins fire incorrectly

### ❌ UNSAFE: Batch all sentences into one TTS request without streaming
- **Why:** Breaks sentence-by-sentence interruption handling
- **Risk:** User can't interrupt during long responses
- **Also breaks:** Flow logic that depends on per-sentence streaming

---

## IMPLEMENTATION PLAN

### Phase 1: Quick Wins (SAFE, 30 mins)
1. ✅ Change `optimize_streaming_latency` from 4 to 0
2. ✅ Add timing logs to measure actual API latency vs. total latency
3. ✅ Test to ensure dead air, interruption, and flow still work

### Phase 2: WebSocket Implementation (CAREFUL, 2-3 hours)
1. ✅ Create ElevenLabs WebSocket connection at call start
2. ✅ Stream sentences to WebSocket as they arrive from LLM
3. ✅ Receive audio chunks and send to Telnyx with playback tracking
4. ✅ Ensure `mark_agent_speaking_start/end()` are called at correct times
5. ✅ Test all three systems:
   - Dead air detection (silence timer, check-ins, hangup)
   - Interruption handling (barge-in during playback)
   - Node transitions (flow logic, variable extraction)

### Testing Checklist:
- [ ] Dead air: Silence for 7s → Check-in message plays
- [ ] Dead air: 2 check-ins with no response → Call hangs up
- [ ] Dead air: User says "hold on" → 25s timeout instead of 7s
- [ ] Interruption: User speaks during agent → Agent stops immediately
- [ ] Interruption: User's words are processed correctly
- [ ] Flow: Nodes transition correctly
- [ ] Flow: Variables are extracted correctly
- [ ] Flow: Check-in doesn't break flow state
- [ ] Latency: Total pause reduced by 50%+

---

## KEY FILES TO MODIFY

1. **`backend/server.py`** line 3570
   - Change `optimize_streaming_latency: 4` → `optimize_streaming_latency: 0`

2. **`backend/server.py`** TTS function (create new WebSocket version)
   - Implement `generate_elevenlabs_audio_websocket()`
   - Maintain same hooks: playback tracking, agent_speaking flags

3. **`backend/server.py`** call initialization
   - Open WebSocket connection when call starts
   - Close WebSocket when call ends

---

## REDIS STATE KEYS (Multi-Worker Coordination)

```python
# Playback count (how many audios are currently playing)
redis_service.increment_playback_count(call_control_id)
redis_service.decrement_playback_count(call_control_id)
redis_service.get_playback_count(call_control_id)

# Check-in flag (is a check-in currently being played?)
redis_service.set_checkin_in_progress(call_control_id)
redis_service.get_checkin_in_progress(call_control_id)
redis_service.clear_checkin_in_progress(call_control_id)

# Agent done speaking flag (for multi-worker webhook coordination)
redis_service.set_flag(call_control_id, "agent_done_speaking")
redis_service.get_flag(call_control_id, "agent_done_speaking")
redis_service.delete_flag(call_control_id, "agent_done_speaking")
```

These must all be preserved in any TTS implementation changes.
