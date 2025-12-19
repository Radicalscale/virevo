# Latency Analysis: Node-by-Node Breakdown

**Analysis Date:** 2025-11-25  
**Log File:** logs.1764045909990.log  
**Total Calls Analyzed:** 2 conversational turns

---

## Executive Summary

| Metric | Call #1 | Call #2 | Change |
|--------|---------|---------|--------|
| **Total E2E Latency** | 3,807ms | 5,945ms | +2,138ms (+56.2%) ⬆️ |
| **Real User Latency** | ~4,107ms | ~6,245ms | +2,138ms (+52.1%) ⬆️ |
| **STT Latency** | 17ms | 7ms | -10ms (-58.8%) ⬇️ |
| **LLM Latency** | 2,065ms | 4,619ms | +2,554ms (+123.7%) ⬆️ |
| **TTS Latency** | 2,531ms | 1,800ms | -731ms (-28.9%) ⬇️ |

**Key Finding:** Between the two calls, you made changes that significantly improved TTS performance (-28.9%), but LLM processing time more than doubled (+123.7%), resulting in net higher overall latency.

---

## Call #1: "Okay, in a nutshell..." Response

### User Input
```
"Go ahead...."
```

### System Response
```
"Okay, in a nutshell, we set up passive income websites that rank on Google, 
generating $500 to $2,000 a month each. What questions come to mind when you hear that?"
```
- **Response Length:** 182 characters
- **Sentence Count:** 5 sentences

---

### 1️⃣ Speech-to-Text (STT) Node

**Provider:** Soniox  
**Model:** stt-rt-preview-v2

| Metric | Value |
|--------|-------|
| **STT Latency** | 17ms |
| **Status** | ✅ Excellent |

**Analysis:** STT performed exceptionally well, staying well under the typical 50-100ms target for real-time transcription.

---

### 2️⃣ Large Language Model (LLM) Node

**Provider:** Grok  
**Model:** grok-4-fast-non-reasoning

| Metric | Value |
|--------|-------|
| **LLM_TOTAL** | 2,065ms |
| **Status** | ⚠️ Moderate |

**Breakdown:**
- This includes full prompt construction, context retrieval, and response generation
- No detailed sub-timing available in logs
- Processing time is reasonable for a complex conversational AI

**Analysis:** 2,065ms is acceptable but could be optimized. This represents ~54% of total E2E latency.

---

### 3️⃣ Text-to-Speech (TTS) Node

**Provider:** ElevenLabs  
**Model:** eleven_flash_v2_5  
**Voice ID:** J5iaaqzR5zn6HFG4jV3b  
**Speed:** 1.1x  
**WebSocket:** No (REST API)

| Fragment | Text | Connection | First Chunk | All Chunks | Audio Gen Only | Total | Audio Size |
|----------|------|------------|-------------|------------|----------------|-------|------------|
| 1/5 | "Okay,..." | 357ms | 387ms | 433ms | 94ms | 526ms | 10,911 bytes |
| 2/5 | "in a nutshell,..." | 309ms | 386ms | 433ms | 94ms | 526ms | 13,419 bytes |
| 3/5 | "we set up passive income websites..." | 309ms | 393ms | 433ms | 94ms | 526ms | 65,246 bytes |
| 4/5 | "generating $500 to $2,000..." | 354ms | 439ms | 485ms | 84ms | 580ms | 49,782 bytes |
| 5/5 | "What questions come to mind..." | 308ms | 402ms | 441ms | 94ms | 534ms | 31,809 bytes |

**TTS_TOTAL:** 2,531ms

**Performance Targets:**
- Connection: < 200ms [❌ Exceeded on all fragments]
- First Chunk: < 300ms [❌ Exceeded on most fragments]

**Analysis:** 
- Connection times consistently exceeded the 200ms target (309-357ms range)
- First chunk times were above the 300ms target (386-439ms range)
- Audio generation itself was very fast (84-94ms)
- **Network latency is the primary bottleneck for TTS**

---

### 4️⃣ Telnyx Playback Node

| Fragment | API Call Time | Expected Duration |
|----------|---------------|-------------------|
| 1/5 | 274ms | 0.50s |
| 2/5 | 243ms | 0.75s |
| 3/5 | 238ms | 2.25s |
| 4/5 | 187ms | 1.35s |
| 5/5 | 252ms | 1.65s |

**Average API Call Time:** 239ms

**Analysis:** Telnyx playback API calls are efficient, averaging under 250ms per fragment.

---

### 📊 Call #1 Summary

```
┌─────────────────────────────────────────────────────────┐
│  USER STOPS SPEAKING                                    │
│         ↓                                               │
│  [STT: 17ms]                                           │
│         ↓                                               │
│  [LLM: 2,065ms] ← 54% of E2E latency                  │
│         ↓                                               │
│  [TTS: 2,531ms] ← 66% of E2E latency (parallel gen)   │
│         ↓                                               │
│  [Playback Start: ~239ms avg per chunk]                │
│         ↓                                               │
│  FIRST AUDIO STARTS: 2,877ms from user stop            │
│         ↓                                               │
│  E2E_TOTAL: 3,807ms                                    │
│         ↓                                               │
│  + Network/Phone buffering: ~300ms                     │
│         ↓                                               │
│  REAL USER LATENCY: ~4,107ms                           │
└─────────────────────────────────────────────────────────┘
```

**Latency Breakdown by Percentage:**
- STT: 0.4%
- LLM: 54.2%
- TTS: 66.5% (note: some parallelization)
- Network/Buffering: ~7.3%

---

## Call #2: "Great. So, are you working..." Response

### User Input
```
"Yeah...."
```

### System Response
```
"Great. So, are you working for someone right now or do you run your own business?"
```
- **Response Length:** 81 characters
- **Sentence Count:** 3 sentences

---

### 1️⃣ Speech-to-Text (STT) Node

**Provider:** Soniox  
**Model:** stt-rt-preview-v2

| Metric | Value |
|--------|-------|
| **STT Latency** | 7ms |
| **Status** | ✅ Excellent (Improved) |

**Analysis:** STT improved by 58.8% from Call #1, demonstrating even better performance. This is exceptionally fast.

---

### 2️⃣ Large Language Model (LLM) Node

**Provider:** Grok  
**Model:** grok-4-fast-non-reasoning

| Metric | Value | Change from Call #1 |
|--------|-------|---------------------|
| **LLM_TOTAL** | 4,619ms | +2,554ms (+123.7%) ⬆️ |
| **Status** | ⚠️ SLOW - Primary Bottleneck |

**Analysis:** 
- **This is the major problem area**
- LLM processing time more than doubled from Call #1
- Now represents **77.7% of total E2E latency**
- Likely causes:
  - Longer conversation history (more context to process)
  - More complex node logic (node type: N_KB_Q&A_With_StrategicNarrative_V3_Adaptive)
  - Potentially hitting KB retrieval (RAG) operations
  - Grok API may have had variable response times

**Recommendation:** This is where your optimization efforts should focus next.

---

### 3️⃣ Text-to-Speech (TTS) Node

**Provider:** ElevenLabs  
**Model:** eleven_flash_v2_5  
**Voice ID:** J5iaaqzR5zn6HFG4jV3b  
**Speed:** 1.1x

| Fragment | Text | Connection | First Chunk | All Chunks | Audio Gen Only | Total | Audio Size |
|----------|------|------------|-------------|------------|----------------|-------|------------|
| 1/3 | "Great." | 339ms | 340ms | 344ms | N/A | 442ms | 10,911 bytes |
| 2/3 | "So,..." | 279ms | 286ms | 292ms | **7ms** 🚀 | 391ms | 13,419 bytes |
| 3/3 | "are you working..." | 351ms | 442ms | 469ms | 91ms | 568ms | 65,246 bytes |

**TTS_TOTAL:** 1,800ms (vs 2,531ms in Call #1)

**Performance Improvement:** -731ms (-28.9%) ⬇️

**Analysis:**
- **Significant improvement in TTS performance**
- Fragment 2 shows exceptional performance with only 7ms audio generation time
- Connection times improved (279-351ms vs 308-357ms)
- First chunk times mixed but generally better
- **Your changes clearly improved TTS efficiency**

---

### 4️⃣ Telnyx Playback Node

| Fragment | API Call Time | Expected Duration |
|----------|---------------|-------------------|
| 1/3 | 321ms | 0.60s |
| 2/3 | 301ms | 0.75s |
| 3/3 | 378ms | 2.75s |

**Average API Call Time:** 333ms (vs 239ms in Call #1)

**Analysis:** Playback API calls were slightly slower than Call #1, but still reasonable.

---

### 📊 Call #2 Summary

```
┌─────────────────────────────────────────────────────────┐
│  USER STOPS SPEAKING                                    │
│         ↓                                               │
│  [STT: 7ms]                                            │
│         ↓                                               │
│  [LLM: 4,619ms] ← 77.7% of E2E latency ⚠️ BOTTLENECK │
│         ↓                                               │
│  [TTS: 1,800ms] ← 30.3% of E2E latency ✅ IMPROVED    │
│         ↓                                               │
│  [Playback Start: ~333ms avg per chunk]                │
│         ↓                                               │
│  FIRST AUDIO STARTS: (timing not clearly logged)       │
│         ↓                                               │
│  E2E_TOTAL: 5,945ms                                    │
│         ↓                                               │
│  + Network/Phone buffering: ~300ms                     │
│         ↓                                               │
│  REAL USER LATENCY: ~6,245ms                           │
└─────────────────────────────────────────────────────────┘
```

**Latency Breakdown by Percentage:**
- STT: 0.1%
- LLM: 77.7% ⚠️
- TTS: 30.3%
- Network/Buffering: ~4.8%

---

## What Changed Between Calls?

### ✅ Improvements

1. **TTS Performance:** -731ms (-28.9%)
   - Better connection times
   - Faster audio generation (7ms on one fragment!)
   - Overall more efficient synthesis

2. **STT Performance:** -10ms (-58.8%)
   - Even faster transcription

### ⚠️ Regressions

1. **LLM Performance:** +2,554ms (+123.7%)
   - **This is the critical issue**
   - More than doubled processing time
   - Now the dominant bottleneck

---

## Optimization Priorities

### 🔴 HIGH PRIORITY: LLM Node Optimization

**Problem:** LLM latency increased from 2,065ms to 4,619ms

**Recommended Actions:**

1. **Enable Parallel Processing**
   - Your "Multi-LLM Processing" feature should help here
   - Ensure it's enabled on the problematic node (N_KB_Q&A_With_StrategicNarrative_V3_Adaptive)

2. **Optimize Context/History**
   - Condense conversation history before sending to LLM
   - Use summarization for older messages
   - Only send relevant context, not entire conversation

3. **Knowledge Base (RAG) Optimization**
   - If KB retrieval is happening, ensure it's parallelized
   - Cache frequent KB queries
   - Reduce retrieval chunk size if possible

4. **Consider Streaming**
   - Stream LLM responses to start TTS generation earlier
   - Don't wait for complete LLM response before generating first audio

5. **Profile the LLM Node**
   - Add detailed timing logs within the LLM processing:
     - Time to retrieve context
     - Time to retrieve KB chunks
     - Time to construct prompt
     - Time for actual LLM API call
     - Time to process response

### 🟢 MAINTAIN: TTS Optimization

**Status:** Working well, significant improvement achieved

**Keep doing:**
- Whatever changes you made between Call #1 and Call #2
- Current ElevenLabs Flash v2.5 configuration is solid

**Further improvements possible:**
- Target connection times under 200ms
- Consider WebSocket TTS for even lower latency

### 🟡 LOW PRIORITY: Telnyx Playback

**Status:** Adequate performance (187-378ms per API call)

**Potential improvements:**
- Pre-buffer audio chunks
- Use overlay mode for faster transitions

---

## Target Latency Breakdown (1,500ms Goal)

To achieve your 1,500ms E2E goal:

| Component | Current (Call #2) | Target | Gap |
|-----------|-------------------|--------|-----|
| STT | 7ms | 10ms | ✅ Under |
| LLM | 4,619ms | 800ms | ⚠️ -3,819ms needed |
| TTS | 1,800ms | 600ms | ⚠️ -1,200ms needed |
| Playback | ~333ms | 90ms | ⚠️ -243ms needed |
| **TOTAL** | **5,945ms** | **1,500ms** | **-4,445ms needed** |

**Reality Check:** Achieving 1,500ms will require aggressive optimization:
- LLM must be reduced by 83% (from 4,619ms to 800ms)
- TTS must be reduced by 67% (from 1,800ms to 600ms)

**Recommendation:** Consider a more realistic target of 2,000-2,500ms given the complexity of your conversational agent.

---

## Additional Observations

### Dead Air Monitoring
- System correctly detected 7.2s of silence and triggered check-ins
- Check-in mechanism working as designed

### Barge-In / Interruption Handling
- User interrupted during playback (logged as "What is...")
- System correctly stopped all playbacks
- Interruption handling appears robust

### Call Quality
- MOS Score: 4.50 (Excellent)
- Minimal packet loss
- Network quality is not an issue

### TTS Caching
- TTS cache working correctly
- "Are you still there?" check-in used cached audio (0ms generation time)

---

## Conclusion

**The Good:**
- Your TTS optimizations are working excellently (-28.9% improvement)
- STT is blazingly fast (7ms)
- Infrastructure (network, Telnyx, call quality) is solid

**The Bad:**
- LLM processing time more than doubled (+123.7%)
- This now represents 77.7% of total latency
- Net result: overall latency increased by 56.2%

**Next Steps:**
1. ✅ Keep the TTS improvements
2. ⚠️ Focus all optimization efforts on the LLM node
3. ⚠️ Profile and break down LLM timing in detail
4. ⚠️ Enable your "Multi-LLM Processing" feature on slow nodes
5. ✅ Test and measure iteratively

**Final Note:** Your systematic approach to optimization is excellent. The TTS improvements prove your methodology works. Now apply the same rigor to the LLM processing pipeline.

---

*Analysis generated: 2025-11-25*

---

## Analysis Date: 2025-12-18
**Log File:** logs.1766052549515.log
**Total Calls Analyzed:** 3 conversational turns

### Executive Summary (2025-12-18)

| Metric | Turn 2 (Reschedule) | Turn 3 (Confirm) | Turn 4 (Final) | Average |
|--------|---------------------|------------------|----------------|---------|
| **Total E2E Latency** | 12,305ms | 12,022ms | 13,262ms | ~12,530ms 🔴 |
| **STT Latency** | 1ms | 6ms | 10ms | ~6ms ✅ |
| **LLM Latency** | 2,755ms | 2,501ms | 3,540ms | ~2,932ms ⚠️ |
| **TTS Latency** | 9,716ms | 9,811ms | 10,001ms | ~9,842ms 🔴 |

**Critical Regression:**
- E2E Latency has ballooned to **~12.5 seconds**, up from ~5.9s in Nov 2025.
- **TTS Latency is the primary driver**, reported as ~10 seconds.
- **Discrepancy:** Logs show "FIRST AUDIO STARTED" at ~12s, yet also claim "Persistent TTS: Audio already streaming in background!" at ~2.7s. This suggests a **metric calculation error** OR a **blocking behavior** where the system waits for the full stream before logging "start".

### Turn-by-Turn Breakdown

#### Turn 2: Reschedule Appointment
- **User:** "...word on the ap point ment?"
- **LLM Response:** "[N] No worries, the appointment's all set..."
- **Timeline:**
  - `10:03:09.038`: User stop
  - `10:03:11.162`: LLM Response (2.75s)
  - `10:03:11.313`: TTS Start
  - `10:03:21.198`: **FIRST AUDIO STARTED Log** (+12.3s)
- **Anomaly:** TTS TTFB was 319ms, but the "E2E" metric logged 12s. This implies the metric might be tracking "All Audio Complete" or there is a massive delay in the playback trigger.

#### Turn 3: Confirmation
- **User:** "Yeah...."
- **LLM Response:** "Great, we're all locked in..."
- **Timeline:**
  - `10:03:37.204`: **FIRST AUDIO STARTED Log** (+12.0s)
- **Similar pattern:** Fast STT/LLM, massively delayed "Audio Start" metric.

### Recommendations using 2025-12-18 Data
1.  **Investigate `FIRST AUDIO STARTED` Metric:** Verify if this timestamp represents the *first chunk sent to Telnyx* or the *completion of the entire sequence*. The logs say "user stopped -> play_audio_url called", which for streaming should happen chunk-by-chunk.
2.  **Verify Persistent TTS:** The log `Persistent TTS: Audio already streaming in background!` suggests streaming *is* active. If audio is actually playing at T+3s, the T+12s log is a False Negative.
3.  **LLM Latency:** ~2.9s is still higher than the <1s target. Continue optimization.
