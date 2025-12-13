# Dead Air System - Flow Diagram

## CALL LIFECYCLE WITH DEAD AIR MONITORING

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. CALL START (handle_soniox_streaming)                            │
│    - Create CallSession                                             │
│    - Initialize state: agent_speaking=False, user_speaking=False   │
│    - silence_start_time=None, checkin_count=0                      │
│    - Start background task: monitor_dead_air()                     │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. BACKGROUND TASK STARTS (dead_air_monitor.py)                    │
│    Loop every 500ms:                                                │
│      - Check should_end_call_max_duration()                         │
│      - Check should_end_call_max_checkins()                         │
│      - Check should_checkin()  ◄── THIS IS KEY                     │
│    If should_checkin() == True:                                     │
│      - Get message from get_checkin_message()                       │
│      - Mark agent speaking (stops silence timer)                    │
│      - Send TTS via check_in_callback()                            │
│      - Mark agent finished (restarts silence timer)                 │
└─────────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. NORMAL CONVERSATION FLOW                                         │
└─────────────────────────────────────────────────────────────────────┘
                     │
    ┌────────────────┴────────────────┐
    │                                  │
    ▼                                  ▼
┌──────────────────────┐    ┌──────────────────────┐
│ USER SPEAKS          │    │ AGENT RESPONDS       │
│ on_final_transcript()│    │ process_user_input() │
│                      │    │                      │
│ • STT detects end    │    │ • LLM generates text │
│ • Set user_speaking  │    │ • TTS creates audio  │
│   = False            │    │ • Playback starts    │
│ • DON'T start        │    │ • Set agent_speaking │
│   silence yet        │    │   = True             │
│   (wait for agent)   │    │ • playback_ids added │
└──────────────────────┘    └──────────┬───────────┘
                                       │
                                       ▼
                     ┌─────────────────────────────────┐
                     │ 4. MULTIPLE AUDIO CHUNKS PLAY   │
                     │    (sentences streamed to TTS)  │
                     │                                 │
                     │    Playback IDs: [id1, id2,...] │
                     └─────────────────┬───────────────┘
                                       │
                                       ▼
             ┌─────────────────────────────────────────────────┐
             │ 5. WEBHOOKS: call.playback.ended               │
             │    (One webhook per audio chunk)                │
             └─────────────────────┬───────────────────────────┘
                                   │
                      ┌────────────┴────────────┐
                      │  Remove playback_id     │
                      │  from current_playback_ │
                      │  ids set                │
                      └────────────┬────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │ Is set EMPTY?       │
                        │ (All audio done?)   │
                        └──────────┬──────────┘
                                   │
                     YES ◄─────────┴──────────► NO
                      │                         │
                      ▼                         └──► Wait for more webhooks
   ┌─────────────────────────────────────┐
   │ 6. ALL PLAYBACK FINISHED            │
   │    session.mark_agent_speaking_end()│ ⭐ CRITICAL TRIGGER
   │                                     │
   │    IF user_speaking == False:       │
   │      start_silence_tracking()       │
   │      silence_start_time = now()     │
   └─────────────────┬───────────────────┘
                     │
                     ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ 7. SILENCE TRACKING ACTIVE                                  │
   │    - Background task checks every 500ms                     │
   │    - should_checkin() evaluates:                            │
   │        • silence_duration = now() - silence_start_time      │
   │        • threshold = 7s (or 25s if hold_on_detected)        │
   │        • checkin_count < max_checkins (2)                   │
   │        • 3s+ since last check-in                            │
   │                                                              │
   │    IF silence_duration >= threshold:                        │
   │      → should_checkin() returns TRUE                        │
   └─────────────────────────┬───────────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │ Duration >= 7 seconds?      │
              └──────────────┬──────────────┘
                             │
                   YES ◄─────┴──────► NO
                    │                 │
                    ▼                 └──► Continue waiting
   ┌─────────────────────────────────────────────┐
   │ 8. SEND CHECK-IN (First Time)              │
   │    - Get message: "Are you still there?"   │
   │    - checkin_count = 1                      │
   │    - mark_agent_speaking_start()            │
   │    - Send TTS via check_in_callback()       │
   │    - mark_agent_speaking_end()              │
   │    - silence_start_time RESET               │
   └─────────────────┬───────────────────────────┘
                     │
                     ▼
   ┌─────────────────────────────────────────────┐
   │ 9. WAIT FOR USER RESPONSE                   │
   │    Two possible outcomes:                   │
   └─────────────────┬───────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐         ┌──────────────────┐
│ USER RESPONDS │         │ STILL SILENT     │
│               │         │ (7 more seconds) │
│ • User speaks │         │                  │
│ • Reset       │         │ Duration >= 7s?  │
│   silence     │         │   YES            │
│   tracking    │         └────────┬─────────┘
│ • checkin_    │                  │
│   count = 0   │                  ▼
│ • Continue    │         ┌──────────────────┐
│   call        │         │ SEND CHECK-IN #2 │
└───────────────┘         │ checkin_count=2  │
                          │ (FINAL)          │
                          └────────┬─────────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │ WAIT 7 SECONDS   │
                          │ (One more period)│
                          └────────┬─────────┘
                                   │
                      ┌────────────▼─────────────┐
                      │ User responds?           │
                      └────────────┬─────────────┘
                                   │
                        ┌──────────┴──────────┐
                        │                     │
                        ▼                     ▼
                ┌───────────────┐    ┌──────────────────┐
                │ USER RESPONDS │    │ STILL SILENT     │
                │ Continue call │    │                  │
                └───────────────┘    │ should_end_call_ │
                                     │ max_checkins()   │
                                     │   returns TRUE   │
                                     └────────┬─────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │ 10. END CALL     │
                                     │ telnyx_service.  │
                                     │ hangup_call()    │
                                     └──────────────────┘
```

## STATE MACHINE DIAGRAM

```
                    ┌─────────────────────────────────────┐
                    │         CALL ACTIVE                 │
                    │  (Background task monitoring)       │
                    └────────────────┬────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
    ┌──────────┐              ┌──────────┐              ┌──────────┐
    │  AGENT   │              │   BOTH   │              │   USER   │
    │ SPEAKING │              │  SILENT  │              │ SPEAKING │
    └────┬─────┘              └────┬─────┘              └────┬─────┘
         │                         │                         │
         │ playback.ended          │ silence_duration >= 7s  │ STT endpoint
         │ (all chunks)            │                         │ detected
         │                         │                         │
         ▼                         ▼                         ▼
    ┌──────────┐              ┌──────────┐              ┌──────────┐
    │   BOTH   │──────────────►│ CHECK-IN │              │   BOTH   │
    │  SILENT  │   7 seconds   │ TRIGGERED│              │  SILENT  │
    │          │◄──────────────│          │              │          │
    │ Timer    │   Response/   └──────────┘              │ Timer    │
    │ Started  │   Timeout                               │ WAITING  │
    └──────────┘                                         │ (no start│
                                                         │  yet)    │
                                                         └──────────┘

States:
• AGENT SPEAKING: agent_speaking=True, silence_start_time=None
• USER SPEAKING: user_speaking=True, silence_start_time=None  
• BOTH SILENT: agent_speaking=False, user_speaking=False, silence_start_time=SET
• CHECK-IN TRIGGERED: Send message, becomes AGENT SPEAKING briefly, then BOTH SILENT again

Transitions:
• agent finishes → BOTH SILENT (start timer)
• user starts speaking → USER SPEAKING (reset timer)
• 7s silence → CHECK-IN TRIGGERED
• check-in sent → brief AGENT SPEAKING → back to BOTH SILENT (timer reset)
```

## KEY VARIABLES STATE TABLE

| Variable | Initial | Agent Generates | Playback Starts | Playback Ends (All) | User Speaks | Silence 7s | Check-in Sent |
|----------|---------|-----------------|-----------------|---------------------|-------------|------------|---------------|
| `agent_speaking` | False | False | True | **False** | False | False | True→False |
| `user_speaking` | False | False | False | False | **True**→False | False | False |
| `silence_start_time` | None | None | None | **now()** | **None** | now()+7s | **now()** |
| `checkin_count` | 0 | 0 | 0 | 0 | **0** (reset) | 0 | **1** |
| `current_playback_ids` | [] | [] | [id1,id2] | **[]** | [] | [] | [id] |

**CRITICAL POINTS**:
1. Timer only starts when `agent_speaking=False AND user_speaking=False`
2. Timer is reset (set to None) when either party starts speaking
3. Check-in increments `checkin_count` and resets timer
4. After 2 check-ins, must wait ONE MORE silence period before hangup

## CONFIGURATION FLOW

```
MongoDB Agent Document
    └── settings: {}
         └── dead_air_settings: {
                 silence_timeout_normal: 7,
                 silence_timeout_hold_on: 25,
                 max_checkins_before_disconnect: 2,
                 max_call_duration: 1500,
                 checkin_message: "Are you still there?"
             }
              │
              │ Loaded into CallSession.__init__()
              │
              ▼
         agent_config.get("settings", {}).get("dead_air_settings", {})
              │
              │ If missing: defaults used via .get(key, default)
              │
              ▼
         Used by:
           • should_checkin()
           • should_end_call_max_duration()
           • should_end_call_max_checkins()
           • get_checkin_message()
```

## DEBUGGING POINTS

Add logging at these critical points to diagnose:

1. **CallSession initialization**: Log `dead_air_settings` loaded
2. **mark_agent_speaking_end()**: Confirm it's called, log speaking states
3. **start_silence_tracking()**: Log timestamp when timer starts
4. **should_checkin() every call**: Log current silence duration and threshold
5. **get_silence_duration()**: Log why returning 0 vs actual duration
6. **check_in_callback()**: Confirm message is actually being sent via TTS

## COMMON FAILURE MODES

1. **Task Never Starts**: `monitor_dead_air()` not called
   - Fix: Verify task creation in `handle_soniox_streaming()`

2. **Timer Never Starts**: `silence_start_time` stays None
   - Cause: `agent_speaking` or `user_speaking` stuck True
   - Fix: Review state management in webhooks and STT callbacks

3. **should_checkin() Always False**: Conditions not met
   - Check: `silence_duration < threshold`
   - Check: `checkin_count >= max_checkins`
   - Check: `last_checkin_time` within 3 seconds

4. **Callback Fails Silently**: TTS error not logged
   - Fix: Add try/except logging in `check_in_callback()`

5. **Settings Not Loaded**: `dead_air_settings` missing from agent
   - Fix: Ensure agent creation includes settings object
   - Fallback: Code has defaults, should still work
