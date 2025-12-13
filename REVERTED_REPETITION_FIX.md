# Repetition Fix Reverted

## What Happened

The repetition detection fix I added was causing TTS to hang/timeout in production calls. Even though the logic was correct and tests passed, it introduced an issue where ElevenLabs TTS would not return audio.

## Why It Failed

The repetition detection code was running **inline in the script handling path** before TTS generation. This may have introduced:
1. Async timing issues
2. Interference with the stream_callback mechanism  
3. Blocking behavior from the word overlap calculation
4. Or simply additional latency that caused ElevenLabs to timeout

## What Was Reverted

All repetition detection code from 3 locations:
1. `_process_call_flow_streaming` (line ~755)
2. `_process_node_content_streaming` (line ~2540)  
3. `_process_node_content` (line ~2610)

The code now works exactly as it did before, which means:
- ✅ TTS will work reliably
- ❌ Script nodes will repeat if no transition matches

## Better Approach Needed

Instead of detecting repetition DURING script generation, we should:

### Option 1: Fix at Transition Level
When evaluating transitions for script nodes, if NO transition matches:
- Check if we just delivered this same script
- If yes, force the node into "prompt mode" temporarily to use AI for recovery
- Use global prompt + node goal to generate intelligent response

### Option 2: Convert Problem Nodes to Prompt Mode
Change Node 5 (Introduce Model) from "script" to "prompt" mode with:
- The script as an instruction/guideline
- Built-in objection handling logic
- Natural progression instructions

### Option 3: Add "Default" Transitions
Add a catch-all transition to every script node:
- Condition: "If user response doesn't match other transitions"
- Action: Move to a dedicated "Handle Questions/Objections" node
- This node uses AI to address the input, then returns to main flow

## Current Status

- Backend reverted to pre-fix state
- TTS should work normally again
- Repetition issue unresolved (will occur if user doesn't match transitions)

## Next Steps

Please test a call to confirm TTS works. Then we can implement a better solution that doesn't break TTS.

---

**Reverted:** November 4, 2025  
**Reason:** TTS timeout issues  
**Status:** Back to baseline (repetition not fixed)
