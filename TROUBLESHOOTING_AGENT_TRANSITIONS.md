# Agent Transition Troubleshooting Guide

## CONTEXT SUMMARY

### What We're Building
A Retell AI-like voice assistant platform with real-time WebSocket streaming between Telnyx (telephony) and Deepgram (STT), using OpenAI for conversation flow management.

### Current Status - What's Working ✅
1. **Real-time WebSocket Streaming** - FULLY WORKING
   - Telnyx → WebSocket → Deepgram STT → AI → TTS → User
   - Sub-2 second latency
   - Using Nova-3 model
   - Inbound track only (no echo)
   - Stream parameters passed in `dial()` command correctly

2. **Basic Features**
   - Variable substitution (e.g., `{{customer_name}}` → "Kendrick") ✅
   - "User speaks first" vs "AI speaks first" setting ✅
   - Simple transitions work ✅

### Current Problem - What's NOT Working ❌

**Agent being tested:** `a44acb0d-938c-4ddd-96b6-778056448731` (name: "Call flow")

**Specific Issue:**
The agent gets stuck on node `N_Opener_StackingIncomeHook_V3_CreativeTactic`. When user says "yeah go ahead" or similar:

1. ✅ Transition evaluation DOES work - AI correctly chooses transition 0
2. ✅ System DOES move to next node: `N_IntroduceModel_And_AskQuestions_V3_Adaptive`
3. ❌ But the AI returns EMPTY response ""
4. ❌ Call freezes - no speech output

**Root Cause Identified:**
The `N_IntroduceModel` node contains 6986 characters of INSTRUCTIONS (prompt for AI), not a script to speak directly. The node's `promptType` is `None`, so the system defaults to "script" mode and tries to speak the instructions literally, which fails.

## THE TROUBLESHOOTING PROCESS (FOLLOW THIS)

### Rule 1: DON'T INTERRUPT THE USER
- Make test calls and READ THE LOGS/TRANSCRIPTS yourself
- Look for `📝 User said:` and `🤖 AI response:` in logs
- Check transition decisions and node switches
- Only ask user for feedback if logs don't show what happened

### Rule 2: Iterative Testing Process
```
1. Make test call to user
2. Read logs after call completes
3. Identify specific failure point
4. Fix the code
5. Create Python test to verify the fix
6. If test passes, make another call to user
7. Repeat until working
```

### Rule 3: Never Hardcode - Stay Flexible
- Don't hardcode model names - use `agent_config.get("model")`
- Don't hardcode keywords for transitions - use AI reasoning
- Let users write ANY transition conditions in natural language
- Auto-detect script vs prompt mode, don't assume

## KEY FILES AND LOCATIONS

### 1. `/app/backend/calling_service.py`
**Main conversation flow logic**

**Key sections:**
- Line 35: `CallSession.__init__` - Takes (call_id, agent_config)
- Line 255-275: Node processing and mode detection
- Line 440-560: `_evaluate_transitions_with_ai()` - Transition logic
- Line 957-1050: `_process_node_content()` - Handles script vs prompt mode

**Current mode detection (Line ~258):**
```python
prompt_type = node_data.get("mode") or node_data.get("promptType")

# Auto-detect if not set
if not prompt_type:
    if len(content) > 500 or "##" in content or "instructions:" in content.lower():
        prompt_type = "prompt"
    else:
        prompt_type = "script"
```

**Issue:** Auto-detection not working - still treating 6986-char instructions as "script"

### 2. `/app/backend/server.py`
**WebSocket streaming and call handling**

- Line 843: Generic WebSocket endpoint `/api/telnyx/audio-stream`
- Line 1443-1550: `call.answered` webhook handler
- Line 1475-1495: "Who speaks first" logic
- Line 1518-1530: Greeting speech (only if not empty)

### 3. `/app/backend/telnyx_service.py`
**Telnyx API interactions**

- Line 24: `initiate_outbound_call()` - Includes streaming params
- Line 54: Uses `inbound_track` only (not `both_tracks`) to avoid echo

## SPECIFIC ISSUES TO FIX

### Issue 1: Mode Detection Not Working
**File:** `calling_service.py` Line ~258

**Problem:** 
```python
prompt_type = node_data.get("mode") or node_data.get("promptType")
```
This returns `None` (falsy), so the `or` doesn't help. Need to explicitly check for None.

**Fix needed:**
```python
# Check multiple possible field names
prompt_type = node_data.get("mode")
if prompt_type is None:
    prompt_type = node_data.get("promptType")

# If still None, auto-detect
if prompt_type is None:
    if len(content) > 500 or any(marker in content.lower() for marker in [
        "## ", "### ", "instructions:", "goal:", "your task", "**important**"
    ]):
        prompt_type = "prompt"
        logger.info(f"🔍 Auto-detected PROMPT mode (length: {len(content)})")
    else:
        prompt_type = "script"
        logger.info(f"🔍 Auto-detected SCRIPT mode")
```

### Issue 2: Empty AI Response
**File:** `calling_service.py` Line ~1010-1040

**Problem:** When in prompt mode, AI might be getting confused by the instruction format

**Check:**
1. Is the AI getting the full 6986-char prompt?
2. Is temperature too low/high?
3. Is max_tokens too small?
4. Are the instructions properly formatted?

**Debug by adding:**
```python
logger.info(f"📋 Prompt length: {len(prompt_with_vars)} chars")
logger.info(f"📋 First 200 chars: {prompt_with_vars[:200]}")
logger.info(f"🎯 Model: {self.agent_config.get('model')}")
logger.info(f"🌡️  Temperature: 0.7, Max tokens: 300")
```

### Issue 3: Transition Logic
**File:** `calling_service.py` Line ~440-560

**Current status:** Working correctly - AI chooses right transition

**No changes needed here** - transitions are evaluating properly

## TEST AGENT DETAILS

**Agent ID:** `a44acb0d-938c-4ddd-96b6-778056448731`
**Model:** `gpt-4.1-2025-04-14` (set in agent, DON'T override)

**Flow Structure:**
```
Node 0: Start (whoSpeaksFirst: "user")
Node 1: Greeting → says "{{customer_name}}?"
  - Transition: "wrong number" → End
  - Default: → Next node
Node 2: Ending
Node 3: N_Opener_StackingIncomeHook_V3_CreativeTactic
  - Transition 0: "yes/sure/okay" → IntroduceModel ✅
  - Transition 1: "no time/busy" → End
  - Transition 2: "no + objection" → DeframeObjection
Node 4: N_IntroduceModel_And_AskQuestions_V3_Adaptive ⚠️ PROBLEM NODE
  - Content: 6986 chars of instructions
  - promptType: None
  - Mode detection failing
```

**Custom variables to use in test:**
```json
{
  "customer_name": "Kendrick"
}
```

## HOW TO TEST

### Make Outbound Call:
```bash
curl -X POST "$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)/api/telnyx/call/outbound" \
-H "Content-Type: application/json" \
-d '{
  "agent_id": "a44acb0d-938c-4ddd-96b6-778056448731",
  "to_number": "+17708336397",
  "from_number": "+14048000152",
  "custom_variables": {
    "customer_name": "Kendrick"
  }
}'
```

### Check Logs:
```bash
# See conversation flow
tail -n 200 /var/log/supervisor/backend.err.log | grep -E "(📝|🤖|transition decision|Auto-detected|mode:)"

# See specific node processing
tail -n 300 /var/log/supervisor/backend.err.log | grep -A 10 "N_IntroduceModel"
```

### Expected Flow:
1. Call connects (no greeting - user speaks first)
2. User: "hello" → AI: "Kendrick?"
3. User: "yeah" → Continue
4. AI reads opener script (25 seconds question)
5. User: "yeah go ahead" → Transition to IntroduceModel ✅
6. AI should explain the model (NOT return empty response) ❌

## IMPORTANT RULES

1. **Never hardcode model names** - Always use `self.agent_config.get("model", "gpt-4")`
2. **Read logs, don't ask user** - User will tell you when something fails, you investigate
3. **Test before calling** - Write Python tests to verify logic before making real calls
4. **Respect agent settings** - Don't override temperature, model, or other configs
5. **Auto-detect intelligently** - If mode/promptType is missing, detect based on content

## NEXT STEPS

1. Fix mode detection to properly identify prompt vs script
2. Add extensive logging to see what's being sent to AI
3. Test with Python to verify mode detection works
4. Make test call to user
5. Check logs - does AI now generate proper response?
6. If not, check: prompt format, token limits, model response
7. Iterate until working

## SUCCESS CRITERIA

When this works correctly, the call flow should be:
- User answers
- User: "hello"
- AI: "Kendrick?"
- User: "yeah"
- AI: "Do you have 25 seconds for me to share something with you?"
- User: "yeah go ahead"
- AI: [Explains the business model naturally based on instructions]
- Flow continues naturally

No freezing, no empty responses, smooth transitions throughout.
