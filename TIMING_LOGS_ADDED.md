# Comprehensive Timing Logs - Implementation Summary

## Overview

I've added detailed millisecond-level timing logs throughout the entire call flow pipeline to track latency at every stage. All logs use the `⏱️ [TIMING]` prefix for easy filtering and analysis.

---

## 1. STT (Speech-to-Text) Timing Logs

**File:** `server.py` line 2463-2472
**Location:** `on_endpoint_detected()` callback

### Logs Added:
```python
⏱️ [TIMING] STT_START: User last audio packet received
⏱️ [TIMING] STT_END: Endpoint detected at T+{stt_latency_ms}ms
⏱️ [TIMING] STT_LATENCY: {stt_latency_ms}ms (Soniox model: {model})
```

### What It Tracks:
- Time from last audio packet received to endpoint detection
- Which STT model is being used (e.g., en_v2_jumbo, en_v3_lightning)
- Expected range: 200-1000ms

---

## 2. Variable Extraction Timing Logs

**File:** `calling_service.py` line 918-930
**Location:** `_process_call_flow_streaming()` method

### Logs Added:
```python
⏱️ [TIMING] VAR_EXTRACTION: {var_extract_ms}ms for {len(extract_variables)} variables
```

### What It Tracks:
- Time spent extracting variables using separate LLM call
- Number of variables being extracted
- Expected range: 500-1500ms
- **This is a MAJOR latency component when enabled**

---

## 3. Transition Evaluation Timing Logs

**File:** `calling_service.py` line 933-945
**Location:** `_process_call_flow_streaming()` method

### Logs Added:
```python
⏱️ [TIMING] TRANSITION_EVAL: {transition_ms}ms
```

### What It Tracks:
- Time spent evaluating which transition to take (separate LLM call)
- Expected range: 500-1500ms
- **This is another MAJOR latency component when enabled**

---

## 4. LLM TTFT (Time to First Token) Logs

**File:** `calling_service.py` line 3000-3005
**Location:** `_generate_ai_response_streaming()` method

### Logs Added:
```python
⏱️ [{timestamp}] 💬 LLM FIRST TOKEN: {ttft_ms}ms ({llm_provider} {model})
```

### What It Tracks:
- Time from LLM request to first token received
- LLM provider (openai, grok, anthropic)
- LLM model (gpt-4o, gpt-4o-mini, grok-beta, claude-3-5-sonnet)
- Expected range: 200-1000ms depending on model
- **Critical metric for perceived responsiveness**

---

## 5. LLM Total Response Time Logs

**File:** `calling_service.py` line 3054-3056
**Location:** `_generate_ai_response_streaming()` method

### Logs Added:
```python
⏱️ [TIMING] LLM_TOTAL: {llm_total_ms}ms for {len(full_response)} chars ({llm_provider} {model})
```

### What It Tracks:
- Total time from LLM request to completion
- Response length in characters
- LLM provider and model
- Expected range: 800-5000ms depending on response length

---

## 6. TTS WebSocket Timing Logs

**File:** `persistent_tts_service.py` line 129-135
**Location:** `stream_sentence()` method

### Logs Added:
```python
⏱️ [TIMING] TTS_START: Sent to ElevenLabs WebSocket at T+0ms
⏱️ [TIMING] TTS_TTFB: First audio chunk at T+{ttfb:.0f}ms
⏱️ [TIMING] TTS_MODEL: {self.model_id}
⏱️ [TIMING] TTS_COMPLETE: All {chunk_count} chunks received in {total_time:.0f}ms
```

### What It Tracks:
- Time to first audio byte from ElevenLabs
- Total time to receive all audio chunks
- TTS model being used (e.g., eleven_flash_v2_5)
- Number of chunks received
- Expected TTFB: 150-300ms (WebSocket) vs 800-1500ms (REST API)
- **Shows the benefit of persistent WebSocket**

---

## 7. Audio Playback Timing Logs

**File:** `persistent_tts_service.py` line 211-267
**Location:** `_play_audio_chunk()` method

### Logs Added:
```python
⏱️ [TIMING] PLAYBACK_START: Processing sentence #{sentence_num} ({len(audio_pcm)} bytes PCM)
⏱️ [TIMING] PLAYBACK_PCM_SAVE: {pcm_save_ms}ms
⏱️ [TIMING] PLAYBACK_FFMPEG: {conversion_time:.0f}ms
⏱️ [TIMING] PLAYBACK_TELNYX: {telnyx_ms}ms
⏱️ [TIMING] PLAYBACK_TOTAL: {total_time:.0f}ms
⏱️ [TIMING] FIRST_AUDIO_PLAYING: First sentence started playing on phone
```

### What It Tracks:
- PCM file save time (disk I/O)
- ffmpeg PCM→MP3 conversion time
- Telnyx API call time to start playback
- Total playback processing time
- When first audio starts playing (critical metric)
- Expected breakdown:
  - PCM save: 5-20ms
  - ffmpeg: 30-100ms
  - Telnyx: 50-150ms
  - Total: 100-300ms

---

## 8. E2E (End-to-End) Summary Logs

**File:** `server.py` line 2741-2761
**Location:** After LLM processing completes in `on_endpoint_detected()`

### Logs Added:
```python
⏱️  [TIMING] ==== E2E LATENCY SUMMARY ====
⏱️  [TIMING] STT: {stt_latency_ms}ms (provider: {stt_provider}, model: {model})
⏱️  [TIMING] LLM_TOTAL: {llm_latency_ms}ms (provider: {llm_provider}, model: {llm_model})
⏱️  [TIMING] TTS_TOTAL: {tts_latency_ms}ms (provider: {tts_provider}, websocket: {use_websocket_tts})
⏱️  [TIMING] E2E_TOTAL: {total_pause_ms}ms (user stopped → agent speaking)
⏱️  [TIMING] RESPONSE_TEXT: {len(response_text)} chars, {len(sentence_queue)} sentences
⏱️  [TIMING] USER_INPUT: '{accumulated_transcript[:60]}...'
⏱️  [TIMING] AI_RESPONSE: '{response_text[:60]}...'
⏱️  [TIMING] ==========================
```

### What It Tracks:
- Complete breakdown of all latency components
- All provider and model information
- Total pause from user stopping to agent speaking
- Response metadata (length, sentence count)
- User input and AI response preview
- **This is the master summary log to check first**

---

## How to Use These Logs

### 1. Filter by Timing Logs Only
```bash
grep "\[TIMING\]" /var/log/supervisor/backend.*.log
```

### 2. Track a Single Call's Latency
```bash
grep "call_control_id_here" /var/log/supervisor/backend.*.log | grep "\[TIMING\]"
```

### 3. Find E2E Summary for Recent Calls
```bash
grep "E2E LATENCY SUMMARY" /var/log/supervisor/backend.*.log | tail -10
```

### 4. Check TTFT Performance
```bash
grep "LLM FIRST TOKEN" /var/log/supervisor/backend.*.log | tail -20
```

### 5. Monitor TTS WebSocket Performance
```bash
grep "TTS_TTFB\|TTS_COMPLETE" /var/log/supervisor/backend.*.log | tail -20
```

---

## Expected Latency Breakdown

### Best Case (Optimized)
```
STT:              300ms
VAR_EXTRACTION:   0ms    (disabled/skipped)
TRANSITION_EVAL:  0ms    (disabled/skipped)
LLM_TTFT:         250ms
LLM_TOTAL:        600ms
TTS_TTFB:         180ms
TTS_TOTAL:        330ms
PLAYBACK:         150ms
----------------------------
E2E_TOTAL:        ~1380ms ✅
```

### Typical Case (Current User Issue)
```
STT:              600ms
VAR_EXTRACTION:   800ms  ⚠️ Extra LLM call
TRANSITION_EVAL:  700ms  ⚠️ Extra LLM call
LLM_TTFT:         500ms
LLM_TOTAL:        1100ms
TTS_TTFB:         220ms
TTS_TOTAL:        400ms
PLAYBACK:         180ms
----------------------------
E2E_TOTAL:        ~3680ms ❌ (matches 4-second report)
```

### Worst Case
```
STT:              1000ms
VAR_EXTRACTION:   1500ms ❌ Extra LLM call
TRANSITION_EVAL:  1000ms ❌ Extra LLM call
LLM_TTFT:         800ms
LLM_TOTAL:        1800ms
TTS_TTFB:         1200ms (REST API fallback)
TTS_TOTAL:        1500ms
PLAYBACK:         200ms
----------------------------
E2E_TOTAL:        ~7650ms ❌ (unacceptable)
```

---

## What to Look For

### 1. **If STT > 800ms:**
- Check Soniox model (switch to en_v3_lightning for speed)
- Check audio quality/noise levels
- Check network latency to Soniox

### 2. **If VAR_EXTRACTION > 0ms:**
- **This is a major bottleneck!**
- Consider disabling variable extraction if not needed
- Or implement conditional extraction (only when needed)

### 3. **If TRANSITION_EVAL > 0ms:**
- **Another major bottleneck!**
- Consider simplifying flow to reduce transitions
- Or cache common transition evaluations

### 4. **If LLM_TTFT > 800ms:**
- Switch to faster model (gpt-4o-mini, grok-beta, claude-haiku)
- Reduce context size (conversation history)
- Check if KB context is too large

### 5. **If TTS_TTFB > 500ms:**
- Check if WebSocket TTS is actually enabled
- If not, enable persistent WebSocket (saves 500-1200ms!)
- Check network latency to ElevenLabs

### 6. **If PLAYBACK_FFMPEG > 150ms:**
- Consider async ffmpeg or streaming approach
- Check server CPU load

---

## Next Steps

1. **Make a test call** with your agent
2. **Collect the logs** from the call
3. **Look at the E2E LATENCY SUMMARY** log first
4. **Identify the bottleneck** (which component has highest ms)
5. **Review optimization recommendations** in `/app/CALL_FLOW_ANALYSIS.md`
6. **Apply targeted optimizations** based on findings

---

## Log Location

All backend logs are in:
```
/var/log/supervisor/backend.out.log  (stdout)
/var/log/supervisor/backend.err.log  (stderr + logs)
```

To monitor in real-time during a call:
```bash
tail -f /var/log/supervisor/backend.err.log | grep "\[TIMING\]"
```

---

## Summary

✅ **Added comprehensive timing logs** at 8 critical stages
✅ **All logs use consistent `⏱️ [TIMING]` prefix** for easy filtering
✅ **E2E summary provides complete breakdown** for each turn
✅ **Model and provider information included** for context
✅ **Expected latency ranges documented** for comparison
✅ **Ready to identify and fix the 4-second delay bottleneck**

The next call will generate detailed timing data showing exactly where the latency is coming from!
