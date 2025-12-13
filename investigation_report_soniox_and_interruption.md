# Investigation Report: Soniox Word Fragmentation & One-Word Response Ignoring

## Overview

**Date:** December 5, 2025  
**Requested By:** User  
**Status:** Investigation in progress - NO FIXES IMPLEMENTED YET (awaiting user approval)

The user requested investigation into two related issues with their voice agent platform:

1. **Soniox Word Fragmentation** - Words are being broken up by the Soniox STT service, causing transcription issues like "Hello" → "Hell o." and "appointment" → "ap point ment"

2. **One-Word Response Ignoring** - Under certain circumstances, the system ignores single-word user responses during the user's turn

---

## Issue 1: Soniox Word Fragmentation

### Problem Description

Soniox's real-time STT model (`stt-rt-preview-v2`) returns subword tokens that cause word fragmentation. This is a known characteristic of their telephony-optimized model.

### Evidence from Logs

From the log file `logs.1764922578404.log`, here are actual examples of fragmented transcriptions:

| User Said (Actual) | Soniox Transcribed |
|-------------------|-------------------|
| "Hello" | `'Hell o.'` |
| "I set up an appointment" | `'I set up an ap point ment.'` |
| "Between 5 and 8" | `'Bet ween, Uh, 5:0 0and 8:0 0.'` |
| "I'll do 8:00" | `'I\'ll do, Uh, 8:0 0.'` |
| "Great" | `'Gre at.'` |
| "Sounds good" | `'Sound sgo od.'` |
| "Awesome" | `'A wes om e.'` |

### Current Mitigation Code

There is already a `clean_transcript()` function in `/app/backend/soniox_service.py` that attempts to fix this:

```python
def clean_transcript(text: str) -> str:
    """
    Clean up Soniox transcript by fixing subword fragmentation.
    
    Soniox's telephony model returns subword tokens which causes patterns like:
    - "th ings" instead of "things"
    - "k ind" instead of "kind"  
    - "Ye ah" instead of "Yeah"
    
    This function intelligently joins fragments while preserving real word boundaries.
    """
```

The function uses:
1. A list of `standalone` words that should never be joined
2. A list of `specific_fixes` - regex patterns for known fragmentations
3. General pattern matching for common suffixes (-ing, -tion, etc.)

### Why Current Fix is Insufficient

The `specific_fixes` list doesn't cover all observed fragmentation patterns. Missing patterns include:

- `'Hell o'` → Should be "Hello" (pattern `r'\bHell o\b'` is missing)
- `'ap point ment'` → Should be "appointment" 
- `'Gre at'` → Should be "Great"
- `'Sound sgo od'` → Should be "Sounds good" (complex multi-word fragmentation)
- `'A wes om e'` → Should be "Awesome"
- `'5:0 0'` → Should be "5:00" (time formatting)
- `'8:0 0'` → Should be "8:00"

### File Location
- **Primary file:** `/app/backend/soniox_service.py`
- **Function:** `clean_transcript()` (starts at line 14)

---

## Issue 2: One-Word Response Being Ignored

### Problem Description

The user reports that "sometimes, not always" single-word responses get ignored during the user's turn. The system has interruption handling infrastructure that may be incorrectly filtering out valid one-word responses.

### Relevant Code Flow

When a user speaks, the system:
1. Receives audio via Telnyx WebSocket
2. Forwards to Soniox for real-time STT
3. Receives transcript with endpoint detection
4. Runs through a **FILTER CHECK** to decide if it should be processed

### The FILTER CHECK Logic

From the logs, we can see filter checks like:
```
🔍 FILTER CHECK: words=1, is_filler=True, is_garbled=False, playbacks=0, generating=False, audio_playing=False, time_until_done=0.0s, is_active=False
```

Key observation: **Single words are sometimes marked as `is_filler=True`**

Examples from logs:
- `'Eastern.'` → `is_filler=True` (but this is a meaningful response!)
- `'Yeah.'` → `is_filler=True` 
- `'No.'` → `is_filler=True`

### The Problem

The system has a **filler word detection** mechanism that incorrectly classifies legitimate one-word responses as "filler" words. Looking at the logs:

```
✅ Agent SILENT - User said 1 word(s): 'Eastern.' - Processing...
```

In this case, "Eastern" (a timezone answer) was marked as `is_filler=True` but still processed. However, the user reports that sometimes these get ignored.

### Conditions When One-Word Responses Might Be Ignored

Based on the filter check parameters, a one-word response might be ignored when:

1. **`is_filler=True`** AND other conditions are met
2. **`audio_playing=True`** - Agent is still speaking
3. **`generating=True`** - LLM is still generating
4. **`playbacks > 0`** - Audio playback is in progress
5. **`is_active=True`** - Some active state flag

### Files to Investigate

The filter check logic is in `/app/backend/server.py`. Need to find:
1. Where `is_filler` is determined
2. What conditions cause the message to be ignored vs processed
3. Why the behavior is intermittent

### Log Evidence of One-Word Processing

From the extracted logs, here are examples where one-word responses WERE processed:

```
✅ Agent SILENT - User said 1 word(s): 'Eastern.' - Processing...
✅ Agent SILENT - User said 1 word(s): 'Yeah.' - Processing...
✅ Agent SILENT - User said 1 word(s): 'No.' - Processing...
✅ Agent SILENT - User said 1 word(s): 'Hello?' - Processing...
```

All of these show `is_filler=True` but were still processed. The intermittent nature suggests the issue depends on timing/state conditions.

---

## Related Code Already Modified (in this session)

Before this investigation, I made one change to `/app/backend/calling_service.py`:

**Changed conversation history window from 5 to 10 turns** in multiple places:
- Line ~2142: Real-time variable extraction
- Line ~2241: Background variable extraction  
- Line ~1931: Transition evaluation context
- Line ~2614: Default webhook body

This was per user request to match what the webhook extraction uses.

---

## Key Files for Investigation

| File | Purpose | Relevant Functions |
|------|---------|-------------------|
| `/app/backend/soniox_service.py` | Soniox STT integration | `clean_transcript()`, WebSocket handling |
| `/app/backend/server.py` | Main server, filter logic | Filter check logic, endpoint processing |
| `/app/backend/calling_service.py` | Call flow processing | `process_user_input()`, interruption handling |

---

## Log File Locations

User provided these log files for analysis:
1. `logs.1764921253181.log` - Shorter log, tail end of calls
2. `logs.1764922578404.log` - Larger log with multiple calls (primary analysis source)

---

## Questions That Need Answering

### For Soniox Fragmentation:
1. Should we expand the `specific_fixes` list with more patterns?
2. Should we implement a more intelligent algorithm (e.g., using a dictionary lookup)?
3. Should we switch to a different Soniox model?
4. Is there a Soniox configuration that reduces fragmentation?

### For One-Word Response Ignoring:
1. Where exactly is the `is_filler` flag set?
2. What is the complete condition that causes a message to be ignored?
3. Is there a race condition with playback state?
4. Should one-word responses be exempt from filler filtering when agent is silent?

---

## Proposed Solutions (Not Yet Implemented)

### Solution Ideas for Soniox Fragmentation:

**Option A: Expand Pattern List**
- Add all observed fragmentation patterns to `specific_fixes`
- Pros: Simple, targeted fixes
- Cons: Whack-a-mole approach, new patterns will appear

**Option B: Intelligent Reassembly Algorithm**
- Use a dictionary/spell-checker to identify when fragments should be joined
- Join fragments if the result is a valid word
- Pros: More comprehensive
- Cons: More complex, potential false positives

**Option C: Soniox Configuration Change**
- Research if Soniox has settings to reduce fragmentation
- May need to use a different model
- Pros: Fixes at source
- Cons: May not be available, may affect latency

**Option D: Post-Processing with LLM**
- Send fragmented transcript through a quick LLM cleanup
- Pros: Very accurate
- Cons: Adds latency, costs

### Solution Ideas for One-Word Response Ignoring:

**Option A: Disable Filler Detection When Agent Silent**
- If `agent_speaking=False`, don't apply filler filtering
- Pros: Simple fix for the main use case
- Cons: May allow actual fillers through

**Option B: Whitelist Meaningful One-Word Responses**
- Create a list of valid one-word responses (Yes, No, Yeah, Sure, Eastern, etc.)
- These bypass filler detection
- Pros: Targeted fix
- Cons: Need to maintain list

**Option C: Context-Aware Filtering**
- Only filter fillers when they occur mid-agent-speech (interruption context)
- When agent is done speaking and waiting for user, accept all input
- Pros: Most intelligent approach
- Cons: More complex logic

---

## Next Steps

1. **User approval needed** before implementing any fixes
2. Need to locate the exact filler detection logic in `server.py`
3. Need to understand the complete filter check flow
4. May need more log examples of when one-word responses ARE ignored (vs just marked as filler but still processed)

---

## Session Context Variables

The system uses a `{{now}}` variable that contains the current date/time:
```
🔧 Replaced {{now}} with Friday, December 5, 2025 at 2:46 AM EST in content
```

This is set in `/app/backend/calling_service.py` and can be used in the global node prompt.

---

## Appendix: Soniox Configuration

From logs:
```
⚙️  Config: model=stt-rt-preview-v2, format=mulaw, rate=8000Hz, channels=1
⚙️  Endpoint detection: True, Speaker diarization: False
```

The model `stt-rt-preview-v2` is Soniox's real-time preview model optimized for telephony.
