# Root Cause Analysis: Agent Barking Issue

## 🔴 Problem Reported
Jake agent was barking ("Woof woof") when asked to "bark like a dog" during a real call, despite the global prompt explicitly instructing it not to engage with irrelevant commands.

## 🔍 Root Cause Identified

### Issue Location
**File**: `/app/backend/calling_service.py`  
**Function**: `_build_cached_system_prompt()` (Lines 130-158)

### The Bug
The cached system prompt builder was **completely ignoring the agent's `system_prompt` field** (the global prompt) and using only a hardcoded generic prompt:

```python
# BEFORE (BROKEN):
def _build_cached_system_prompt(self):
    prompt = """You are a phone agent conducting natural conversations.
    # ... hardcoded generic rules ...
    """
    return prompt  # ❌ NEVER included agent's global prompt!
```

This meant that:
1. ✅ The global prompt was stored correctly in the database
2. ✅ The global prompt was displayed correctly in the UI
3. ✅ The global prompt worked in isolated LLM tests
4. ❌ **But the global prompt was NEVER sent to the LLM during actual calls**

### Why This Happened
The `_build_cached_system_prompt()` function was designed for Grok's prefix caching optimization. To maximize cache hits, the developer created a static prompt, but **forgot to include the agent's actual personality and behavioral rules** (the `system_prompt` field).

### Impact
- **All call flow agents** using prompt-mode nodes were affected
- Agent-specific rules and boundaries were completely ignored
- Only generic communication rules were applied
- This is why the agent responded to irrelevant commands despite explicit instructions not to

## ✅ Fix Applied

### Code Changes
Modified `_build_cached_system_prompt()` to include the agent's global prompt:

```python
# AFTER (FIXED):
def _build_cached_system_prompt(self):
    # START WITH AGENT'S GLOBAL PROMPT (personality, behavior, rules)
    global_prompt = self.agent_config.get("system_prompt", "").strip()
    
    # Then add technical communication rules
    technical_rules = """
    # COMMUNICATION STYLE
    # STRICT RULES
    # CRITICAL - AVOID REPETITION
    ...
    """
    
    # Combine: Global prompt (character/boundaries) + Technical rules
    if global_prompt:
        prompt = global_prompt + technical_rules
        logger.info(f"📋 Built cached system prompt: {len(global_prompt)} chars (global) + {len(technical_rules)} chars (technical)")
    else:
        prompt = "You are a phone agent conducting natural conversations." + technical_rules
        logger.info(f"⚠️ No global prompt found - using default")
    
    return prompt
```

### What Changed
1. ✅ **Now reads** the agent's `system_prompt` field from `agent_config`
2. ✅ **Places global prompt FIRST** (defines personality and boundaries)
3. ✅ **Appends technical rules** (formatting, repetition avoidance)
4. ✅ **Logs both parts** for debugging visibility
5. ✅ **Maintains caching optimization** (still built once at session start)

## 🧪 Testing Evidence

### Before Fix
- **Call ID**: `v3:cMuPUOcqdGbj58UpfvjfzNETlwc2g0FTnTqY21Kda1nFFl0wccGGng`
- **User Request**: "Could you bark like a dog for me?"
- **Agent Response**: "Woof woof" ❌
- **Outcome**: FAILED - Agent engaged with irrelevant command

### After Fix (Expected)
- **User Request**: "Could you bark like a dog for me?"
- **Agent Response**: "Let's stay focused on helping you with this opportunity. [continues with qualification]" ✅
- **Outcome**: PASS - Agent redirects without engaging

## 🎯 Why My Initial Tests Passed

My initial tests used **direct LLM calls** with the prompt explicitly included:

```python
messages = [
    {"role": "system", "content": ORIGINAL_PROMPT},  # ✅ Prompt was included
    {"role": "user", "content": "Can you bark like a dog?"}
]
```

This worked because I was **manually including the prompt** in the test. However, the actual calling system was **not including it** due to the bug in `_build_cached_system_prompt()`.

## 📋 Files Modified

### Primary Fix
- `/app/backend/calling_service.py` - Fixed `_build_cached_system_prompt()` method

### Supporting Files (Testing/Documentation)
- `/app/test_agent_prompt.py` - Direct LLM testing script
- `/app/simulate_call_test.py` - API simulation script
- `/app/update_jake_agent_via_api.py` - Agent update script
- `/app/GLOBAL_PROMPT_FIX_SUMMARY.md` - Initial fix documentation
- `/app/ROOT_CAUSE_AND_FIX.md` - This document

## 🚀 Deployment Status

### Applied Changes
- [x] Code fix implemented in `calling_service.py`
- [x] Backend service restarted
- [x] Jake agent's global prompt already updated (contains improved instructions)

### Ready for Testing
The fix is now live and ready to test with a real call.

## 🧪 Testing Instructions

### Test the Fix
1. **Make an outbound call** to Jake agent (ID: `474917c1-4888-47b8-b76b-f11a18f19d39`)
2. **During the call**, try these irrelevant commands:
   - "Can you bark like a dog?"
   - "What color is a banana?"
   - "Sing me a song"
3. **Expected Behavior**:
   - ✅ Agent should NOT bark, describe colors, or sing
   - ✅ Agent should redirect: "Let's stay focused on helping you with this opportunity"
   - ✅ Agent should continue with qualification process

### Verification
Check the backend logs for:
```
📋 Built cached system prompt: [X] chars (global) + [Y] chars (technical)
```

This confirms the global prompt is being included.

## 📊 Impact Assessment

### Severity
**CRITICAL** - Core functionality broken for all prompt-mode call flow agents

### Affected Components
- All call flow agents using prompt-mode nodes
- Any agent with behavioral rules in the global prompt
- Affects all calls, not just Jake agent

### Resolution Priority
**IMMEDIATE** - Fix applied and deployed

## 🎓 Lessons Learned

### For Future Development
1. **Never assume caching optimizations are safe** - Verify they include all required data
2. **Test with actual system flows** - Not just isolated LLM calls
3. **Log what's sent to LLM** - Makes debugging much faster
4. **Global prompt is critical** - It defines the agent's character and boundaries

### Testing Checklist for Prompt Changes
- [ ] Direct LLM test (isolated)
- [ ] API endpoint test (with calling system)
- [ ] Real call test (end-to-end)
- [ ] Log verification (confirm prompt sent to LLM)

## 📞 Next Steps

1. **Test with real call** - Verify agent no longer barks
2. **Monitor logs** - Confirm global prompt is being used
3. **Test other agents** - Ensure fix works for all call flow agents
4. **Consider adding unit tests** - Prevent similar regressions

---

**Status**: ✅ FIX DEPLOYED - Ready for testing  
**Priority**: IMMEDIATE  
**Confidence**: HIGH - Root cause identified and fixed
