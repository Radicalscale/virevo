# Sesame TTS Real-Time Streaming Implementation Plan

## Goal
Achieve <2s latency (similar to ElevenLabs) by streaming audio chunks in real-time instead of waiting for complete file generation.

---

## Current Problem
- **REST API**: Generate entire audio → Save file → Download → Play
- **Latency**: 10-30 seconds (unacceptable for conversation)
- **Why slow**: Waiting for full generation before playback starts

---

## Solution: WebSocket Streaming Architecture

### High-Level Flow
```
User speaks → LLM generates text → RunPod WebSocket (Sesame) → Stream audio chunks → Telnyx → User hears (FAST!)
```

---

## Architecture Design

### Option A: True Streaming (If Model Supports It)
**Best case scenario** - Model generates audio iteratively

```python
# RunPod Side
async def generate_streaming(text, speaker_id):
    for audio_chunk in model.generate_stream(text):  # If supported
        yield audio_chunk  # Send immediately over WebSocket
```

**Latency**: 500ms-1s (first chunk)

---

### Option B: Chunk Post-Generation (If Model Generates All at Once)
**Fallback** - Generate full audio, then stream in chunks

```python
# RunPod Side
async def generate_and_chunk(text, speaker_id):
    # Generate full audio (5-10s)
    audio = model.generate(text, speaker_id)
    
    # Immediately split into 0.1s chunks
    chunk_size = 2400  # 0.1s at 24kHz
    for i in range(0, len(audio), chunk_size):
        chunk = audio[i:i+chunk_size]
        yield chunk  # Stream chunk over WebSocket
```

**Latency**: 5-10s (first chunk) - Still better than REST API

---

### Option C: Hybrid - Parallel Generation & Streaming
**Smart approach** - Split text into sentences, generate in parallel

```python
# Split text into sentences
sentences = ["Hello there.", "How are you?", "Let me help you."]

# Generate first sentence immediately
chunk1 = generate(sentences[0])  # 2s
yield chunk1  # User starts hearing

# While playing chunk1, generate chunk2
chunk2 = generate(sentences[1])  # Parallel
yield chunk2

# Continue...
```

**Latency**: 1-3s (first chunk), overlapping generation

---

## Implementation Details

### 1. RunPod WebSocket Server (New)

**File: `sesame_ws_server.py`**

Key features:
- WebSocket endpoint `/ws/generate`
- Accept: `{"text": "...", "speaker_id": 0}`
- Stream: Raw PCM audio chunks (int16, 24kHz, mono)
- End signal: `{"done": true}`

**Pseudocode:**
```python
@app.websocket("/ws/generate")
async def websocket_generate(websocket):
    # Receive text
    data = await websocket.receive_json()
    text = data["text"]
    speaker_id = data["speaker_id"]
    
    # Generate and stream
    audio = model.generate(text, speaker_id)
    
    # Stream in chunks
    CHUNK_SIZE = 4800  # 0.2s at 24kHz (good balance)
    for i in range(0, len(audio), CHUNK_SIZE):
        chunk = audio[i:i+CHUNK_SIZE]
        
        # Send as base64 or raw bytes
        await websocket.send_bytes(chunk.tobytes())
    
    # Signal completion
    await websocket.send_json({"done": true})
```

---

### 2. Backend WebSocket Client (New)

**File: `/app/backend/sesame_ws_service.py`**

Similar to `elevenlabs_ws_service.py`:
- Connect to RunPod WebSocket
- Send text + speaker_id
- Receive audio chunks
- Buffer and stream to Telnyx

**Pseudocode:**
```python
class SesameWebSocketService:
    async def stream_tts(self, text: str, speaker_id: int):
        async with websockets.connect(WS_URL) as ws:
            # Send request
            await ws.send(json.dumps({
                "text": text,
                "speaker_id": speaker_id
            }))
            
            # Stream chunks
            while True:
                chunk = await ws.recv()
                
                if isinstance(chunk, bytes):
                    yield chunk  # Audio chunk
                else:
                    data = json.loads(chunk)
                    if data.get("done"):
                        break
```

---

### 3. Telnyx Integration (Update)

**File: `/app/backend/telnyx_service.py`**

Add Sesame to WebSocket TTS routing:

```python
# Line 379 - Update condition
if use_websocket_tts and tts_provider in ["elevenlabs", "sesame"]:
    if tts_provider == "sesame":
        result = await self._speak_text_websocket_sesame(...)
    else:
        result = await self._speak_text_websocket(...)  # ElevenLabs
```

New method for Sesame WebSocket:
```python
async def _speak_text_websocket_sesame(self, call_control_id, text, agent_config):
    from sesame_ws_service import stream_sesame_tts
    
    speaker_id = agent_config.get("sesame_settings", {}).get("speaker_id", 0)
    
    async for audio_chunk in stream_sesame_tts(text, speaker_id):
        # Stream to Telnyx immediately
        await self.stream_audio_to_telnyx(call_control_id, audio_chunk)
```

---

## Optimization Strategies

### Strategy 1: Sentence-Level Chunking
- Split text by sentences using regex
- Generate first sentence → Play immediately
- Generate next sentence in parallel
- **Latency**: 1-2s for first sentence

### Strategy 2: Model Quantization
- Use `torch.float16` or `torch.int8` quantization
- Reduces inference time by 30-50%
- **Implementation**: Already using `torch.float16` ✅

### Strategy 3: Batch Processing (If Multiple Utterances)
- Generate multiple chunks in parallel
- Use GPU efficiently
- **Benefit**: Better throughput for longer conversations

### Strategy 4: Pre-warming
- Keep model loaded and warm
- Use model caching
- **Implementation**: Already pre-loading model ✅

---

## Expected Latency Breakdown

### Current REST API (SLOW)
```
Text ready: 0s
├─ Generate full audio: 10s
├─ Save to file: 0.5s
├─ Download file: 1s
└─ Start playback: 11.5s ❌
```

### WebSocket Streaming (FAST)
```
Text ready: 0s
├─ Generate first chunk: 1-2s
├─ Stream chunk: 0.1s
└─ Start playback: 1-2s ✅
(Continue streaming while user hears)
```

### Sentence-Level Chunking (OPTIMAL)
```
Text ready: 0s
├─ First sentence: 0.8s
├─ Stream: 0.1s
└─ Start playback: 0.9s ✅✅
```

---

## Implementation Priority

### Phase 1: Basic WebSocket Streaming (1-2 hours)
1. ✅ Create RunPod WebSocket server
2. ✅ Create backend WebSocket client
3. ✅ Integrate with telnyx_service.py
4. ✅ Test with simple text

**Expected Result**: 2-3s latency

---

### Phase 2: Sentence Chunking (30 mins)
1. Split text by sentences
2. Generate and stream per sentence
3. Overlap generation and playback

**Expected Result**: 1-2s latency

---

### Phase 3: Advanced Optimization (Optional)
1. Experiment with model streaming (if supported)
2. Implement predictive pre-generation
3. Fine-tune chunk sizes

**Expected Result**: <1s latency

---

## Critical Questions

### Q1: Does Sesame CSM-1B support iterative/streaming generation?
**Need to check**: 
```python
# Try this in RunPod
audio = model.generate(**inputs, output_audio=True, streamer=...)
```

If YES → True streaming (Option A) → 500ms latency
If NO → Chunk post-generation (Option B) → 2-3s latency

### Q2: What's the optimal chunk size?
- Too small (0.05s): Network overhead
- Too large (1s): Increased latency
- **Sweet spot**: 0.1-0.2s (2400-4800 samples at 24kHz)

### Q3: Should we use raw PCM or compressed format?
- **PCM**: Simple, no encoding delay
- **Opus**: Smaller bandwidth, slight encoding delay
- **Recommendation**: Start with PCM, optimize later

---

## Next Steps

1. **I implement backend WebSocket client** (`sesame_ws_service.py`)
2. **You implement RunPod WebSocket server** (I'll provide complete code)
3. **I integrate with telnyx_service.py**
4. **We test together** and measure latency
5. **Iterate and optimize** based on results

---

## Code to Provide

I will create:
1. ✅ `/app/backend/sesame_ws_service.py` - WebSocket client
2. ✅ `/app/sesame_ws_server.py` - RunPod WebSocket server (for you to copy)
3. ✅ Updated `/app/backend/telnyx_service.py` - Integration
4. ✅ Test script to measure latency

You will:
1. Copy `sesame_ws_server.py` to your RunPod
2. Install `websockets` library
3. Run the WebSocket server
4. Test with me

---

## Success Criteria

- ✅ First audio chunk plays within 2 seconds
- ✅ Continuous streaming (no gaps)
- ✅ Total latency < 3s for full utterance
- ✅ Audio quality maintained (24kHz, 16-bit PCM)
- ✅ Handles interruptions gracefully

Ready to implement?
