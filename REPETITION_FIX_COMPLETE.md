# Jake Agent Repetition Fix - COMPLETE ✅

## Problem Identified

When the Jake agent was at Node 5 ("Introduce Model" - a script node), and the user objected with "What is this? Some kind of marketing scam?", the agent would **REPEAT the exact same "in a nutshell" script** instead of intelligently handling the objection.

### Root Cause

**Script-mode nodes** that didn't match any transition condition would simply return the same script content again, causing robotic repetition. This happened because:

1. Node 5 was configured as "script" mode (not "prompt" mode)
2. The transition condition was: "After answering initial questions"
3. User objection "marketing scam?" didn't match the transition
4. System defaulted to repeating the script

## Solution Implemented

Added **intelligent repetition detection** in `_process_call_flow_streaming` (line 755 in calling_service.py):

### How It Works

1. **Detect Repetition**: Before returning script content, check if it overlaps >60% with the previous agent response
2. **Use Global Prompt**: If repetition detected, build a recovery prompt using:
   - Agent's global prompt (persona/instructions)
   - Node's goal (if available)
   - Context: what was just said + user's response
3. **Generate Intelligent Response**: Use AI to create a contextual, non-repetitive response that addresses the user's input

### Code Changes

```python
# In _process_call_flow_streaming (line ~755)
if prompt_type == "script":
    # CHECK FOR REPETITION
    if len(self.conversation_history) >= 2:
        prev_content = self.conversation_history[-2].get('content', '')
        overlap = calculate_word_overlap(content, prev_content)
        
        if overlap > 0.6:  # 60% overlap = likely repetition
            logger.warning(f"REPETITION DETECTED: {overlap*100:.1f}%")
            
            # Build recovery prompt with global prompt + node goal
            recovery_prompt = build_recovery_context(
                global_prompt, node_goal, prev_content, user_message, content
            )
            
            # Generate intelligent response instead of repeating
            return await self._generate_ai_response_streaming(recovery_prompt, stream_callback)
    
    # No repetition - return script normally
    return content
```

## Test Results

### Before Fix
```
USER: What is this? Some kind of marketing scam?
JAKE: Okay. In a nutshell, we set up passive income websites, 
      and we let them produce income for you. What questions 
      come to mind as soon as you hear something like that?
      [REPEATED EXACTLY - 100% overlap]
```

### After Fix
```
USER: What is this? Some kind of marketing scam?
JAKE: No, not at all—it's a legit business model where we build 
      and optimize niche websites that generate ongoing revenue 
      through ads, affiliates, or sales, all on autopilot once 
      they're live. We've helped hundreds of folks like you create 
      real passive income streams; what part of that sounds off 
      to you, or what questions do you have about how it works?
      [INTELLIGENT RECOVERY - only 35.7% overlap]
```

## Additional Enhancement

Updated Node 5 in database to include a **goal**:
```
Goal: "Explain the business model (passive income websites) and engage 
      their curiosity by asking what questions come to mind. Handle any 
      objections or concerns about legitimacy before moving forward."
```

This ensures the AI has clear guidance even when using the recovery prompt.

## Impact

- ✅ **No More Robotic Repetition**: Script nodes intelligently handle unexpected responses
- ✅ **Natural Objection Handling**: Uses global prompt to maintain persona while recovering
- ✅ **Contextual Responses**: AI considers what was just said and how user responded
- ✅ **Goal-Oriented Recovery**: Uses node goals to guide conversation back on track

## Files Modified

1. **`/app/backend/calling_service.py`**
   - Added repetition detection in `_process_call_flow_streaming` (line ~755)
   - Added repetition detection in `_process_node_content_streaming` (line ~2540)
   - Added repetition detection in `_process_node_content` (line ~2610)

2. **Database: Jake Agent (ID: 474917c1-4888-47b8-b76b-f11a18f19d39)**
   - Added goal to Node 5 (Introduce Model)

## Testing

Run the test script to verify:
```bash
cd /app && python test_repetition_fix.py
```

**Expected Output:**
```
✅ PASSED: Response shows empathy and addresses objection
```

## Production Status

✅ **PRODUCTION READY**

The fix is live and tested. The Jake agent will now:
- Detect when it's about to repeat itself
- Use the global prompt to generate intelligent, contextual responses
- Handle objections naturally without breaking character
- Progress conversations even when transitions don't explicitly match

---

**Fix Completed:** November 4, 2025  
**Agent:** Jake - Income Stacking Qualifier  
**Issue:** Repetition on unmatched transitions  
**Status:** ✅ RESOLVED
