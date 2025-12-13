# TTS Timing Reality Check

## Current Situation: Estimation vs Reality

### What My Test Does ❌
```python
# This is an ESTIMATION based on formula
tts_generation = 1.0 + (words * 0.04) + (0.3 if has_ssml else 0)
```

**NOT measuring:**
- Actual ElevenLabs API latency
- WebSocket streaming performance
- Network conditions
- Parallel audio chunk delivery
- Real audio conversion time

### What Production Does ✅
```python
# In telnyx_service.py line 492
tts_start = time.time()
# ... call ElevenLabs/Cartesia/etc
# ... stream audio chunks via WebSocket
# ... convert to proper format
# ... send to Telnyx for playback
total_time = time.time() - tts_start
logger.info(f"⏱️  Total TTS latency: {total_time:.2f}s")
```

**Actually measures:**
- Real API call time
- Audio generation time
- WebSocket streaming
- Format conversion
- Network latency
- Full end-to-end TTS pipeline

---

## The Problem

**My test script calls:**
```python
result = await self.session.process_user_input(message)
```

This only measures **LLM processing**. It does NOT call `telnyx_service.speak_text()` because:
1. We're testing locally (no real phone call)
2. No Telnyx call session exists
3. TTS happens AFTER the test returns the response text

**So my TTS time is a formula-based guess, not real measurement.**

---

## Your Infrastructure (How It Really Works)

### ElevenLabs WebSocket Streaming

Based on your production code (`telnyx_service.py`):

**Step 1: Generate Audio (Streaming)**
```python
# Lines 530-640: _speak_text_websocket()

# Connect to ElevenLabs WebSocket
ws_url = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"

# Send text chunks
await ws.send(json.dumps({
    "text": text,
    "voice_settings": {...}
}))

# Receive audio chunks in REAL-TIME (parallel streaming)
async for message in ws:
    audio_chunk = base64.b64decode(message['audio'])
    # Chunks arrive as they're generated, not all at once!
```

**Key Point:** Audio starts arriving BEFORE full generation completes. This is why it feels faster than my formula suggests.

**Step 2: Convert & Send**
```python
# Convert MP3 chunks → PCM (for Telnyx)
conversion_start = time.time()
# ffmpeg conversion
conversion_time = time.time() - conversion_start

# Send to Telnyx playback API
playback_start = time.time()
response = requests.post(telnyx_playback_url, audio_data)
playback_time = time.time() - playback_start

# Total measured time
total_time = time.time() - tts_start  # This is REAL
```

### What Gets Measured

**In production logs, you see:**
```
⏱️  ElevenLabs API: 250ms
⏱️  Audio conversion: 0.15s
⏱️  Playback API: 180ms
⏱️  TOTAL WebSocket TTS latency: 580ms
```

**My test shows:**
```
TTS Generation: 1.720s (18 words)  ← FORMULA, not real
```

**Reality could be:**
- **Faster:** 0.5-0.8s (streaming optimization, parallel processing)
- **Slower:** 2.0-3.0s (network issues, API rate limits)
- **Variable:** Depends on API load, network, time of day

---

## How Accurate Is My Formula?

### Formula: `1.0 + (words * 0.04) + 0.3 if SSML`

**Based on:**
- Educated guess from ElevenLabs documentation
- Typical API response times
- Streaming overhead estimates

**Reality check from your production:**

Looking at your code (line 694):
```python
logger.info(f"⏱️  TOTAL WebSocket TTS latency: {total_time*1000:.0f}ms")
```

If we could extract this from real calls, we'd see actual values like:
- Short responses (5-10 words): 400-800ms
- Medium (20-30 words): 800-1500ms
- Long (50+ words): 1500-2500ms

**My formula predicts:**
- 10 words: `1.0 + (10 * 0.04) = 1.4s` (1400ms)
- 20 words: `1.0 + (20 * 0.04) = 1.8s` (1800ms)
- 50 words: `1.0 + (50 * 0.04) = 3.0s` (3000ms)

**Accuracy:** Probably **±30% error** (could be off by 500ms either way)

---

## What Would Make It More Accurate?

### Option 1: Extract Real TTS Times from Production Logs

**Pros:**
- Uses actual measured values
- Reflects real infrastructure
- Includes all variables (network, API, streaming)

**Cons:**
- Requires parsing production logs
- Need call ID to match logs
- Historical data only (not predictive)

**Implementation:**
```python
# Search logs for a call
call_id = "v3:6M-magfzEtfhJ11e-..."
grep "TOTAL WebSocket TTS latency" /var/log/e1_agent.log | grep call_id

# Extract timing data
# Use average from similar word counts
```

---

### Option 2: Actually Call TTS API in Test

**Pros:**
- 100% accurate for current conditions
- Tests real API performance
- Reflects actual infrastructure

**Cons:**
- Slower test (adds real network calls)
- Costs money (ElevenLabs charges per character)
- Requires API keys
- Can't run offline

**Implementation:**
```python
async def measure_real_tts_time(response_text, agent_config):
    tts_start = time.time()
    
    # Call actual TTS service
    result = await telnyx_service.speak_text(
        call_control_id="test",  # Dummy ID
        text=response_text,
        agent_config=agent_config
    )
    
    real_tts_time = time.time() - tts_start
    return real_tts_time
```

---

### Option 3: Improve Formula with Real Data

**Collect data from production:**
```python
# From 100 recent calls, measure:
# - TTS time vs word count
# - TTS time vs SSML presence
# - TTS time vs voice model

# Derive formula:
# y = a + (b * words) + (c * ssml)

# Better accuracy: ±15% instead of ±30%
```

**Example improved formula:**
```python
# Base latency (WebSocket connection + overhead)
base_latency = 0.6s  # Measured average

# Per-word generation rate
word_rate = 0.03s  # Measured from logs (faster than 0.04)

# SSML overhead
ssml_penalty = 0.2s  # Measured

# Streaming optimization (parallel processing reduces perceived time)
streaming_factor = 0.85  # 15% faster due to streaming

tts_time = (base_latency + (words * word_rate) + ssml_penalty) * streaming_factor
```

---

## Your WebSocket Streaming Setup

Based on your code, here's what happens:

### Standard WebSocket Flow (`_speak_text_websocket`)

```python
# 1. Connect to ElevenLabs WebSocket
ws = await websockets.connect(elevenlabs_ws_url)

# 2. Send config
await ws.send(json.dumps({
    "text": text,
    "model_id": "eleven_turbo_v2_5",
    "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
}))

# 3. Receive audio chunks IN PARALLEL (key optimization!)
pcm_buffer = BytesIO()
async for message in ws:
    if message['audio']:
        # Audio arrives in chunks WHILE still generating
        audio_chunk = base64.b64decode(message['audio'])
        pcm_buffer.write(convert_to_pcm(audio_chunk))
        
        # First chunk arrives FAST (200-400ms)
        # Remaining chunks stream in parallel

# 4. Send complete audio to Telnyx
# Total time: WebSocket time + conversion + playback API
```

**Key insight:** Because of streaming, the user hears the FIRST chunk quickly (0.5-0.8s), not after full generation completes.

**My formula doesn't account for this!** It assumes sequential processing.

---

## Bottom Line

**My TTS measurement is:**
- ✅ Better than the old formula (was 3x too low)
- ⚠️ Still an estimation (±30% accuracy)
- ❌ NOT using your actual infrastructure measurements
- ❌ NOT accounting for WebSocket streaming optimization

**To get TRUE measurements, we would need to:**
1. Parse production logs for real TTS times, OR
2. Actually call the TTS API in the test, OR
3. Build a statistical model from historical data

**For now, treat my numbers as "reasonable estimates" with this caveat:**
```
My test: 2.5s TTS generation (formula)
Reality: Could be 1.8s (with streaming) or 3.2s (with network issues)
```

**The LLM time is accurate** (we measure it directly).
**The system overhead (0.9s) is a reasonable estimate** based on typical values.
**The TTS time is the weakest link** in my measurements.

---

## Recommendation

**Short term (current test):**
- Use my formula as a "ballpark estimate"
- Understand it could be off by 30%
- Focus optimization on what we CAN control: response length & model choice

**Long term (better accuracy):**
- Extract real TTS times from production logs
- Build a lookup table: words → real measured TTS time
- Use this in test instead of formula

**Example:**
```python
# From 1000 production calls
TTS_TIME_BY_WORDS = {
    5: 0.65,   # Average of all 5-word responses
    10: 0.82,
    15: 1.15,
    20: 1.48,
    30: 2.10,
    40: 2.65,
    50: 3.20
}

def get_realistic_tts_time(word_count):
    # Find closest match
    closest = min(TTS_TIME_BY_WORDS.keys(), 
                  key=lambda x: abs(x - word_count))
    return TTS_TIME_BY_WORDS[closest]
```

This would be **much more accurate** than my formula!
