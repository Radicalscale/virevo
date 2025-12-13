# Known Issues - Voice Agent Platform

## Issue 1: amPm Variable Extraction Skipped (Agreement Pattern Not Recognized)
**Status:** ✅ FIXED  
**Priority:** P0  
**Component:** Variable Extraction (`calling_service.py`)

### Description
When a node has multiple mandatory variables to extract (e.g., `scheduleTime` and `amPm`), the extraction process may complete after extracting only one variable, leaving the second mandatory variable null/missing.

### Root Cause Analysis
**Two problems identified:**

1. **Timing Issue:** Mandatory variable extraction happens AFTER the agent has already generated and streamed its response. If variables are missing, the reprompt is either lost or causes double-speaking.

2. **Agreement Pattern Not Recognized:** The LLM extraction doesn't understand "implicit agreement" patterns where:
   - Agent proposes: "How about 3 PM tomorrow?"
   - User confirms: "Sure" or "Yeah"
   - The `amPm = PM` value was stated by the AGENT, user just agreed
   - LLM only looks at user's "Sure" and can't extract "PM" from it

### Fix Applied (2025-12-09)
**Part A: Moved mandatory extraction BEFORE response generation**
- Lines 1299-1330: Added pre-response mandatory variable check
- If mandatory variables missing, sends reprompt BEFORE generating normal response
- Prevents agent from speaking when required data is missing

**Part B: Enhanced extraction prompt for agreement patterns**
- Added "AGREEMENT PATTERN RECOGNITION" instructions to extraction prompt
- LLM now looks at Assistant's recent messages when user gives confirmation
- Extracts values from Assistant's proposals that user agreed to
- Added time-related extraction rules (morning=AM, afternoon=PM, etc.)

### Files Modified
- `/app/backend/calling_service.py` - Lines 1299-1330, 2372-2410, 2524-2560

---

## Issue 2: Single-Word Responses Filtered as Filler
**Status:** ✅ FIXED  
**Priority:** P1  
**Component:** Transcript Filtering (`server.py`)

### Description
Valid single-word responses like "Sure." or "Okay." are being filtered out as filler words, causing the system to ignore legitimate user input during their turn.

### Root Cause Analysis
The filtering logic at lines 4469-4480 and 4511-4523 in `server.py` determines `is_agent_active` based on three factors:
1. `has_active_playbacks` - Are there tracked playback IDs?
2. `is_generating` - Is the agent generating a response?
3. `audio_still_playing` - Is `playback_expected_end_time` in the future?

**The Bug:** Even when `playbacks=0` and `generating=False`, if `playback_expected_end_time` is still slightly in the future (e.g., 0.1 seconds), `audio_still_playing=True` causes `is_agent_active=True`, which triggers filtering.

**From the logs:**
```
🔍 FILTER CHECK: words=1, is_filler=True, playbacks=0, generating=False, audio_playing=True, time_until_done=0.1s, is_active=True
🔕 FILTERING 1-word/filler 'Sure.' - NOT calling on_final_transcript
```

### Fix Applied (2025-12-09)
Modified the `is_agent_active` calculation in two locations (lines ~4469 and ~4521) to account for user activity:

```python
# If user is actively speaking and no playbacks/generation,
# don't rely solely on playback_expected_end_time estimate
user_actively_speaking = session and session.user_speaking
if user_actively_speaking and not has_active_playbacks and not is_generating:
    is_agent_active = False  # User speaking = agent turn is over
else:
    is_agent_active = has_active_playbacks or is_generating or audio_still_playing
```

**Logic:** If the user has started speaking AND there are no active playbacks AND the agent is not generating, the user's speech overrides the `playback_expected_end_time` estimate. User actively speaking is a strong signal that the agent's turn is over.

### Files Modified
- `/app/backend/server.py` - Lines ~4469-4490 and ~4521-4550

---

## Issue 3: ElevenLabs WebSocket Timeout Disconnection
**Status:** ✅ FIXED  
**Priority:** P1  
**Component:** Persistent TTS Service (`persistent_tts_service.py`, `elevenlabs_ws_service.py`)

### Description
The persistent WebSocket connection to ElevenLabs disconnects after 20 seconds of inactivity, causing a ~1-1.5 second delay when the next TTS request triggers reconnection.

### Root Cause Analysis
ElevenLabs has a **20-second text input timeout** for streaming connections:
- The TCP WebSocket connection stays alive via `ping_interval=20`
- BUT ElevenLabs requires **actual text input** within 20 seconds
- If no text is sent for 20 seconds, ElevenLabs terminates the stream with error code 1008

**Timeline from logs:**
```
10:16:08 - Last TTS_START (text sent to ElevenLabs)
10:16:19 - Check-in triggered (used REST API, not WebSocket)
10:16:29 - Error: "20 seconds timeout" (21 seconds since last text)
10:16:30 - Reconnected to ElevenLabs WebSocket
10:16:31 - First TTS_START after reconnection (~1.3s delay)
```

### Fix Applied (2025-12-09)
Implemented a **keep-alive mechanism** that sends periodic text to ElevenLabs every 15 seconds to prevent the 20-second timeout.

**Changes in `/app/backend/persistent_tts_service.py`:**

1. Added `_keepalive_task` field to track the keep-alive loop
2. Added `_keepalive_loop()` method that sends a single space every 15 seconds:
   ```python
   async def _keepalive_loop(self):
       while self.connected:
           await asyncio.sleep(15)
           if not self.is_streaming:
               await self.ws_service.send_text(" ", try_trigger_generation=False, flush=False)
   ```
3. Keep-alive starts when connection is established
4. Keep-alive restarts on reconnection
5. Keep-alive is properly cancelled on close

**Log output will show:**
```
💓 [Call xxx] Starting TTS keep-alive loop (every 15s)
💓 [Call xxx] TTS keep-alive sent
```

### Files Modified
- `/app/backend/persistent_tts_service.py` - Added keep-alive loop, updated connect/reconnect/close methods

---

---

## Issue 4: Mandatory Variables Not Extracted Before Transition
**Status:** ✅ FIXED  
**Priority:** P0  
**Component:** Call Flow Processing (`calling_service.py`)

### Description
When a node has mandatory variables (e.g., `employed_yearly_income`, `amount_reference`), and the user provides the required information, the system transitions to the next node WITHOUT extracting the variables first. This causes:
1. Incorrect calculations (e.g., `amount_reference` = 4800 instead of correct value)
2. Wrong logic path taken (15k pricing flow instead of 5k pricing flow)

### Root Cause Analysis
The extraction for mandatory variables was happening AFTER the transition to the NEW node, not on the CURRENT node where the user answered:

**Original flow:**
1. User at Node A (income question)
2. User says "24k"
3. `_follow_transition()` called → transitions to Node B (side hustle question)
4. Mandatory check runs on Node B (wrong node!)
5. `employed_yearly_income` never extracted from "24k"

**The bug:** Lines 1038-1046 called `_follow_transition` BEFORE any mandatory variable extraction on the current node. The mandatory check at line 1305+ only ran on the DESTINATION node.

### Fix Applied (2025-12-09)
Added **PRE-TRANSITION MANDATORY VARIABLE CHECK** at lines 1019-1043:

```python
# PRE-TRANSITION MANDATORY VARIABLE CHECK
# CRITICAL: Extract variables on CURRENT node BEFORE transitioning
if current_node_type == "conversation":
    current_extract_vars = current_node_data.get("extract_variables", [])
    if current_extract_vars and len(current_extract_vars) > 0:
        has_mandatory = any(var.get("mandatory", False) for var in current_extract_vars)
        if has_mandatory:
            extraction_result = await self._extract_variables_realtime(current_extract_vars, user_message)
            
            if not extraction_result.get("success", True):
                # Mandatory variables STILL missing - BLOCK transition
                selected_node = current_node  # Stay on current node
            else:
                # All mandatory vars satisfied - proceed with transition
                pass
```

**Logic:**
1. Before any transition, check if CURRENT node has mandatory variables
2. Run extraction on user's message against CURRENT node's variables
3. If mandatory vars still missing → BLOCK transition, stay on current node
4. If mandatory vars satisfied → proceed with normal transition

### Files Modified
- `/app/backend/calling_service.py` - Lines 1019-1075

---

## Document History
- **2025-12-09:** Initial creation with 3 identified issues
- **2025-12-09:** All 3 issues fixed:
  - Issue 1: amPm extraction - moved mandatory check before response, added agreement pattern recognition
  - Issue 2: Filler filtering - added user_speaking override for is_agent_active
  - Issue 3: ElevenLabs timeout - added 15-second keep-alive loop
- **2025-12-09:** Issue 4 (P0) fixed - Pre-transition mandatory variable extraction

---

## Issue 5: Speech-to-Text Number Parsing Errors
**Status:** ✅ FIXED  
**Priority:** P0  
**Component:** Variable Extraction (`calling_service.py`)

### Description
The LLM was misinterpreting spoken numbers with hesitations/filler words. When user said "I make about 20, Uh, 4,000 a year" (meaning 24,000), the LLM extracted:
- `employed_yearly_income: 204000` (should be 24000)
- `amount_reference: 17000` (calculated from wrong base)

### Root Cause
Speech-to-text transcripts include spacing and filler words that made "24,000" appear as "20, Uh, 4,000". The LLM concatenated "20" + "4000" = "204000" instead of understanding "twenty-four thousand".

### Fix Applied (2025-12-09)
Added **CRITICAL - SPEECH-TO-TEXT NUMBER PARSING** instructions to the extraction prompt:
- Explicit examples: "20, Uh, 4,000" = 24000 (NOT 204000)
- Pattern recognition for filler words and pauses
- Sanity check: "Most incomes are $20k-$200k, so 24000 is more likely than 204000"
- Applied to both `_extract_variables_realtime()` and `_extract_variables_background()` methods

### Files Modified
- `/app/backend/calling_service.py` - Lines ~2420-2440 and ~2570-2590

---

---

## Issue 6: Function Node Chain Not Updating Current Node Tracking
**Status:** ✅ FIXED  
**Priority:** P1  
**Component:** Call Flow Processing (`calling_service.py`)

### Description
When function/webhook nodes chain through multiple transitions (e.g., Time-Converter → Calendar-check → N206_AskAboutPartners), the `current_node_id` and `current_node_label` were not being updated correctly. This caused:
1. Transitions being evaluated from the WRONG node (e.g., Calendar-check instead of N206)
2. "FAST PATH" cached transitions being applied incorrectly
3. Agent revisiting the wrong nodes in the flow

### Root Cause
When function nodes recursively call `_process_node_content_streaming()` to process the next node:
1. `current_node_id` was being updated, but `current_node_label` was NOT
2. The separate `_process_node_content_streaming()` method (line 3932) also had recursive calls that didn't update `current_node_label`

### Fix Applied (2025-12-09)
Updated all recursive function node transitions to also update `current_node_label`:

1. **Inline function node handling** (lines 1191-1193): Added `current_node_label` update
2. **Collect input node** (line 1244): Added `current_node_label` update  
3. **Send SMS node** (line 1267): Added `current_node_label` update
4. **Logic split node** (lines 1283, 1300): Added `current_node_label` update
5. **Extract variable node** (line 1328): Added `current_node_label` update
6. **Separate `_process_node_content_streaming()` method** (lines 3980, 3993): Added `current_node_id` AND `current_node_label` updates

### Files Modified
- `/app/backend/calling_service.py` - Multiple locations where recursive node transitions occur

---

---

## Issue 7: Function Node FAST PATH Bypassing Webhook Response Evaluation
**Status:** ✅ FIXED  
**Priority:** P0  
**Component:** Transition Logic (`calling_service.py`)

### Description
When transitioning from function/webhook nodes, the "FAST PATH" optimization was incorrectly being triggered by user affirmative responses ("Yeah", "OK") even though function node transitions should ALWAYS be evaluated based on webhook responses, not user messages.

### Root Cause
The FAST PATH check at line 2004 was:
```python
if is_function_node and webhook_response:
```
This only skipped FAST PATH if we had an active webhook_response. But when user speaks and triggers a new processing cycle, `webhook_response` is None, so FAST PATH was incorrectly used.

### Fix Applied (2025-12-09)
Changed the check to ALWAYS skip FAST PATH for function nodes:
```python
if is_function_node:
    # ALWAYS skip cached response for function nodes
```

---

## Issue 8: Race Condition - User Speaking During Webhook Chain Execution
**Status:** ✅ FIXED  
**Priority:** P0  
**Component:** User Input Processing (`calling_service.py`)

### Description
When a user speaks while a webhook chain is executing (e.g., Time-Converter → Calendar-check → conversation node), a NEW `process_user_input()` call would be triggered using the STALE `current_node_id` from the middle of the webhook chain, not the final node.

### Root Cause
No guard existed to prevent processing user input during webhook execution. The flow was:
1. Webhook chain starts, updates `current_node_id` to intermediate nodes
2. User speaks, triggers `process_user_input()`
3. `current_node_id` is still at intermediate webhook node
4. Transition evaluation uses wrong node, causing incorrect routing

### Fix Applied (2025-12-09)
Added **WEBHOOK EXECUTION GUARD** at the start of `process_user_input()`:
```python
if self.executing_webhook:
    logger.info("⏳ WEBHOOK GUARD: Webhook executing, waiting for completion...")
    while self.executing_webhook and (time.time() - wait_start) < max_wait:
        await asyncio.sleep(0.1)
```

This ensures user input is queued until any executing webhook chain completes, preventing stale node state from being used.

---
