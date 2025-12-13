# Phase 2 Analysis: Streaming Performance Results

**Date:** November 20, 2025  
**Call Recording:** recording_v3_OGYQPsqbBGPQ5TwsF.mp3  
**Log File:** logs.1763607837299.log

---

## 🔴 CRITICAL FINDING: Persistent TTS Was NOT Used

**Issue:** The call fell back to REST API instead of using persistent WebSocket TTS.

**Evidence:**
```
⚠️  No persistent TTS session found for call v3:OGYQPsqbBGPQ5TwsF... (active sessions: [])
🔍 Persistent TTS lookup: call_id=v3:OGYQPsqbBGPQ5TwsF..., session=NOT FOUND
```

**Impact:**
- TTFA (Time To First Audio) metric **could not be measured**
- Performance is WORSE than it should be (using slower REST API)
- No true sentence-by-sentence streaming

**Root Cause:** Persistent TTS session was never initialized for this call.

---

## New Timing Metrics Analysis

### Turn 1: Initial Response
```
TTFS:         Not captured (initial greeting)
LLM_TOTAL:    Not captured
TTS_TOTAL:    Not captured
E2E_TOTAL:    1,540ms
Real Latency: 1,840ms (~1.8s)
```
**Status:** ✅ Good performance

---

### Turn 2: "How so?..."
```
TTFS:         1,555ms  ⚠️  Slow
TTFT_TTS:     1,556ms  (1ms delay - excellent)
TTFA:         N/A (persistent TTS not used)

LLM_TOTAL:    1,876ms
TTS_TOTAL:    1,566ms
E2E_TOTAL:    3,122ms
Real Latency: 3,422ms (~3.4s)
```

**Analysis:**
- ⚠️  First sentence took 1.5 seconds to arrive (83% of total LLM time)
- ✅ TTS started immediately (1ms delay)
- ❌ STREAMING QUESTIONABLE: First sentence at 1,555ms, full LLM only 1,876ms
  - **This means LLM waited 1.5s before starting to stream!**
- If properly streaming, first sentence should arrive at ~300-500ms

---

### Turn 3: "Go ahead...."
```
TTFS:         799ms   ✅ Good
TTFT_TTS:     799ms   (0ms delay - excellent)
TTFA:         N/A (persistent TTS not used)

LLM_TOTAL:    1,080ms
TTS_TOTAL:    2,113ms
E2E_TOTAL:    2,913ms
Real Latency: 3,213ms (~3.2s)
```

**Analysis:**
- ✅ First sentence arrived at 799ms (74% of total LLM time)
- ✅ TTS started immediately
- ⚠️  Still questionable streaming - should be <500ms for first sentence
- Better than Turn 2, but not optimal

---

### Turn 4: "Well, it..." ⚠️ **MAJOR LATENCY SPIKE**
```
TTFS:         6,621ms  ❌ TERRIBLE (6.6 seconds!)
TTFT_TTS:     6,621ms  (0ms delay - excellent)
TTFA:         N/A (persistent TTS not used)

LLM_TOTAL:    6,793ms
TTS_TOTAL:    1,503ms
E2E_TOTAL:    8,125ms
Real Latency: 8,425ms (~8.4 seconds!)
```

**Analysis:**
- ❌ **MASSIVE 6.6 SECOND DELAY** before first sentence
- ❌ LLM took 6.8 seconds total (97% before first sentence!)
- ❌ **LLM NOT STREAMING** - user waited entire generation time
- This is the 4-13 second issue RETURNING in different form!

**Possible Causes:**
1. LLM timeout issue (hitting 3s timeout on transition, retrying?)
2. Complex prompt causing slow generation
3. Grok API slowdown
4. RAG retrieval blocking (logs show 1ms, so probably not this)
5. LLM prefix cache miss

**Evidence from logs:**
```
⏱️ [03:03:31.728] 💬 LLM REQUEST START: 11 conversation turns, 13215 system chars (KB cached)
⏱️ [03:03:32.263] 💬 LLM FIRST TOKEN: 534ms (grok grok-4-fast-non-reasoning)
📤 Sentence arrived from LLM: You filled out a Facebook ad...
⏱️ [TIMING] TTFS (Time To First Sentence): 6621ms
```

**Wait, this is VERY strange:**
- LLM FIRST TOKEN: **534ms** (good!)
- But TTFS: **6,621ms** (terrible!)
- **6,087ms gap between first token and first sentence!**

**This means:**
- ✅ LLM started streaming tokens quickly (534ms)
- ❌ But took 6+ seconds to reach first sentence boundary (period/!/ ?)
- **The response had NO sentence-ending punctuation for 6 seconds!**

---

## Root Cause Analysis

### Issue #1: Persistent TTS Not Initialized ⚠️ HIGH PRIORITY

**Problem:** Agent config doesn't have persistent TTS enabled, or initialization failed

**Solution Needed:**
1. Check agent settings - ensure `use_websocket_tts: true`
2. Verify ElevenLabs API key is configured
3. Check if persistent TTS session is created on call.answered

**Impact if fixed:**
- TTFA metric will be available
- Better TTS performance (WebSocket vs REST)
- True sentence-by-sentence streaming

---

### Issue #2: LLM Token → Sentence Delay 🔴 CRITICAL

**Problem:** Turn 4 took 6 seconds from first token to first sentence

**Root Cause:** LLM generated a very long run-on sentence without punctuation

**Evidence:**
```
First token: 534ms (good)
First sentence: 6,621ms (6.1 seconds of run-on text!)
Response: "You filled out a Facebook ad about creating passive income without 
adding more hours to your day—that's how we got your info."
```

**Solution Options:**

**Option A: Force Sentence Boundaries**
- Modify sentence detection regex to split on commas or dashes
- Current: `([.!?]\s+)`
- Improved: `([.!?,—]\s+)` or `([.!?]\s+|,\s+|—\s+)`
- Risk: Choppy audio with too many pauses

**Option B: Stream on Partial Completion**
- Don't wait for sentence boundary
- Stream every N tokens (e.g., 10-15 tokens)
- Use punctuation as preferred boundaries, but timeout if none found
- Risk: More complex logic

**Option C: Prompt Engineering**
- Add to system prompt: "Use short, punchy sentences. End sentences frequently."
- Least intrusive
- May not always work

**Recommendation:** Combination of A + C
1. Update prompt to encourage short sentences
2. Expand sentence detection to include commas/dashes as weak boundaries

---

### Issue #3: LLM Not Streaming Properly (Turns 2-3)

**Problem:** Even on "good" turns, first sentence takes 74-83% of total LLM time

**Expected Behavior:**
- Total response: 1,876ms
- First sentence: ~300-500ms (25-30%)
- Remaining: 1,376ms

**Actual Behavior:**
- Total response: 1,876ms
- First sentence: 1,555ms (83%!)
- Remaining: 321ms

**Possible Causes:**
1. LLM not streaming at token level (batching tokens before sending)
2. Grok API buffering tokens before streaming
3. Long prompt causing slow start
4. Network latency between backend and Grok API

**Solution:**
1. Verify Grok streaming is enabled (`stream=True`) ✅ Already set
2. Check if we're correctly consuming stream
3. Add token-level timing to see when tokens arrive vs when sentences detected

---

## Performance Comparison

### Before Fixes (Previous Session)
```
Turn 1: 2.0s
Turn 2: 1.9s
Turn 3: 4.4s
Turn 4: 3.7s
Average: 3.0s
```

### After Phase 1 (Current Session)
```
Turn 1: 1.8s  ✅ Improved
Turn 2: 3.4s  ❌ Worse
Turn 3: 3.2s  ✅ Similar
Turn 4: 8.4s  ❌ MUCH WORSE
Average: 4.2s  ❌ Worse overall
```

**Conclusion:** Performance REGRESSED in this call!

**Why?**
1. Persistent TTS not used (slower REST API)
2. Turn 4 had massive 6.6s delay (run-on sentence)
3. Other turns also slower than previous session

---

## Recommendations for Phase 3

### Priority 1: Fix Persistent TTS Initialization 🔥

**Action Items:**
1. Check agent configuration for `use_websocket_tts` setting
2. Verify persistent TTS session is created on call start
3. Add logging to show why session wasn't found
4. Test with persistent TTS enabled

**Expected Impact:** 500-1000ms improvement per turn

---

### Priority 2: Fix Run-on Sentence Issue 🔥

**Action Items:**
1. Expand sentence boundary detection:
   ```python
   # Current:
   sentence_endings = re.compile(r'([.!?]\s+)')
   
   # Improved:
   sentence_endings = re.compile(r'([.!?]\s+|,\s+(?=\w{3,})|—\s+)')
   ```
2. Add timeout: If no sentence boundary after 2 seconds, force split
3. Update system prompt to encourage short sentences

**Expected Impact:** Prevent 6+ second delays on long responses

---

### Priority 3: Investigate LLM Streaming Efficiency

**Action Items:**
1. Add token-level timing logs
2. Verify Grok API is streaming at token-level
3. Check network latency to Grok API
4. Consider switching to faster model if available

**Expected Impact:** 300-500ms improvement on first sentence arrival

---

## Next Steps

**Option A: Fix Persistent TTS First (Recommended)**
- Simplest fix
- Biggest immediate impact
- Enables TTFA measurement
- Then retest to get clean data

**Option B: Fix All Three Issues**
- More complex
- Risk of introducing bugs
- But addresses all problems at once

**Option C: Retest with Different Agent/Settings**
- Verify if persistent TTS works with another agent
- Isolate configuration issue

---

## Key Metrics to Watch

After fixes, we want to see:

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| TTFS | 799-6621ms | <500ms | ❌ Needs work |
| TTFT_TTS | 0-1ms | <100ms | ✅ Excellent |
| TTFA | N/A | <1500ms | ⚠️  Can't measure |
| E2E Total | 1.8-8.4s | <2.5s | ❌ Too variable |

---

## Summary

### What We Learned

1. ✅ TTS starts immediately after first sentence (0-1ms delay) - working perfectly
2. ❌ Persistent TTS not used - major performance loss
3. ❌ LLM takes too long to reach first sentence (1.5-6.6s)
4. ❌ Run-on sentences cause massive delays (6.6s in Turn 4)
5. ⚠️  LLM streaming exists but is inefficient (first sentence = 74-97% of total time)

### Critical Path Forward

**Must Fix:**
1. Enable persistent TTS (500-1000ms improvement)
2. Fix run-on sentence handling (prevent 6+ second spikes)

**Should Fix:**
3. Improve LLM streaming efficiency (300-500ms improvement)

**Nice to Have:**
4. Add token-level streaming (100-200ms improvement)

---

**Total Potential Improvement:** 1,000-2,200ms per turn  
**Target Latency:** 0.8-1.5s (down from current 1.8-8.4s)

---

**Status:** Phase 2 analysis complete - Ready for targeted Phase 3 fixes
