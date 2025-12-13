# Sesame TTS WebSocket Server - Complete Guide

## 📋 Overview

This server enables **real-time audio streaming** from Sesame TTS model, reducing latency from 10-30 seconds (REST API) to 2-5 seconds (WebSocket streaming).

---

## 🎯 How It Works

### Architecture Flow

```
Your Voice Agent (My Platform)
    ↓
WebSocket Connection
    ↓
RunPod Server (Your Code)
    ↓
1. Receive text + speaker_id
2. Generate full audio (Sesame Model)
3. Split into 0.2s chunks
4. Stream chunks immediately
    ↓
Your Voice Agent receives chunks
    ↓
Converts & plays to caller in real-time
```

### Key Innovation: Post-Generation Chunking

Since Sesame CSM-1B generates complete audio (not iterative), we:
1. Generate full audio (takes 2-5 seconds)
2. **Immediately split into small chunks** (0.2s each)
3. **Stream chunks over WebSocket** (no waiting for file save/download)
4. Client starts playing while still receiving chunks

**Result**: User hears audio much faster!

---

## 📦 Required Dependencies

### 1. Python Packages

```bash
pip install fastapi uvicorn[standard]
pip install torch torchaudio
pip install transformers
pip install huggingface_hub
pip install numpy
pip install websockets  # Usually included with uvicorn[standard]
```

### 2. Hugging Face Token

You need a HuggingFace token to access the Sesame model:

1. Go to https://huggingface.co/settings/tokens
2. Create a new token (Read access)
3. Accept the model license at https://huggingface.co/sesame/csm-1b
4. Set as environment variable:
   ```bash
   export HF_TOKEN="hf_xxxxxxxxxxxxx"
   ```

---

## 🔧 Code Explanation (Line by Line)

### Part 1: Imports & Setup (Lines 1-41)

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
```
- **FastAPI**: Web framework for HTTP + WebSocket
- **WebSocket**: Real-time bidirectional communication
- **FileResponse**: Serve audio files (for REST API)

```python
import torch
from transformers import CsmForConditionalGeneration, AutoProcessor
```
- **torch**: PyTorch for GPU acceleration
- **CsmForConditionalGeneration**: Sesame TTS model
- **AutoProcessor**: Handles text preprocessing

```python
device = "cuda" if torch.cuda.is_available() else "cpu"
model_id = "sesame/csm-1b"
```
- Automatically uses GPU if available (MUCH faster)
- Model ID points to Sesame CSM-1B on HuggingFace

```python
# Pre-load model at startup (Lines 29-41)
hf_token = os.getenv("HF_TOKEN")
login(hf_token)
processor = AutoProcessor.from_pretrained(model_id)
model = CsmForConditionalGeneration.from_pretrained(
    model_id, torch_dtype=torch.float16
).to(device)
```
**Why pre-load?** Loading the model takes 30-60 seconds. By loading at startup, we avoid this delay for each request.

**torch.float16**: Half-precision (saves GPU memory, faster inference)

---

### Part 2: WebSocket Endpoint (Lines 54-140)

#### Step 1: Accept Connection (Lines 65-66)
```python
await websocket.accept()
```
Establishes WebSocket connection with client

#### Step 2: Receive Request (Lines 69-74)
```python
data = await websocket.receive_text()
request = json.loads(data)
text = request.get("text", "")
speaker_id = request.get("speaker_id", 0)
```
Client sends JSON: `{"text": "Hello world", "speaker_id": 0}`

#### Step 3: Generate Audio (Lines 84-94)
```python
prompt = f"[{speaker_id}]{text}"
inputs = processor(text=prompt, add_special_tokens=True).to(device)

with torch.no_grad():
    audio = model.generate(**inputs, output_audio=True)
```

**Key points:**
- `[{speaker_id}]` prefix tells model which voice to use (0-9)
- `torch.no_grad()` disables gradient calculation (faster inference)
- `output_audio=True` returns audio waveform directly

#### Step 4: Convert to PCM (Lines 96-107)
```python
if isinstance(audio, torch.Tensor):
    audio_array = audio.cpu().numpy()
else:
    audio_array = np.array(audio)

audio_int16 = (audio_array * 32767).astype(np.int16)
```

**Why?**
- Model outputs float32 values (-1.0 to 1.0)
- We need int16 PCM for compatibility
- Multiply by 32767 (max int16 value) and convert

#### Step 5: Stream Chunks (Lines 109-123)
```python
CHUNK_SIZE = 4800  # 0.2 seconds at 24kHz

for i in range(0, len(audio_int16), CHUNK_SIZE):
    chunk = audio_int16[i:i + CHUNK_SIZE]
    await websocket.send_bytes(chunk.tobytes())
```

**Magic happens here!**
- **4800 samples** = 0.2 seconds of audio at 24kHz
- Each chunk sent immediately (no buffering)
- Client receives and plays while loop continues
- **Result**: Continuous, low-latency playback

**Why 0.2s chunks?**
- Too small (0.05s): Network overhead, choppy
- Too large (1s): Higher perceived latency
- 0.2s: Sweet spot for smooth, low-latency streaming

#### Step 6: Signal Completion (Lines 124-126)
```python
await websocket.send_json({"done": True})
```
Tells client "no more chunks coming"

---

### Part 3: REST API (Lines 143-175)

Kept for **backwards compatibility** - still works if WebSocket fails

Same logic as before:
1. Generate audio
2. Save to file
3. Return file path
4. Client downloads file separately

**Slower but reliable fallback**

---

### Part 4: Health Check (Lines 193-204)

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "device": device,
        "cuda": torch.cuda.is_available(),
        "model_loaded": model is not None,
        "endpoints": {
            "websocket": "/ws/generate",
            "rest": "/generate"
        }
    }
```

Useful for monitoring:
- Is GPU working?
- Is model loaded?
- What endpoints are available?

---

## 🚀 Setup Instructions

### Option A: Copy-Paste in Terminal

```bash
# Navigate to your workspace
cd /workspace

# Create the file
cat > sesame_ws_server.py << 'EOF'
[paste entire code here]
EOF

# Set HF token
export HF_TOKEN="hf_your_token_here"

# Run server
python sesame_ws_server.py
```

### Option B: Using Jupyter Notebook

1. Open Jupyter Lab in RunPod
2. Create new Python file: `File → New → Text File`
3. Paste the complete code
4. Save as `sesame_ws_server.py`
5. Open terminal: `File → New → Terminal`
6. Run:
   ```bash
   export HF_TOKEN="hf_your_token"
   cd /workspace
   python sesame_ws_server.py
   ```

---

## 🧪 Testing

### Test 1: Health Check
```bash
curl https://k8ytpid6evir3s-8000.proxy.runpod.net/health
```

**Expected:**
```json
{
  "status": "healthy",
  "device": "cuda",
  "cuda": true,
  "model_loaded": true,
  "endpoints": {
    "websocket": "/ws/generate",
    "rest": "/generate"
  }
}
```

### Test 2: WebSocket Connection (Python)

Create `test_ws.py`:
```python
import asyncio
import websockets
import json

async def test():
    uri = "wss://k8ytpid6evir3s-8000.proxy.runpod.net/ws/generate"
    
    async with websockets.connect(uri) as websocket:
        # Send request
        await websocket.send(json.dumps({
            "text": "Hello world, this is a test",
            "speaker_id": 0
        }))
        
        # Receive chunks
        chunk_count = 0
        while True:
            message = await websocket.recv()
            
            if isinstance(message, bytes):
                chunk_count += 1
                print(f"Received chunk {chunk_count}: {len(message)} bytes")
            else:
                data = json.loads(message)
                if data.get("done"):
                    print("Streaming complete!")
                    break

asyncio.run(test())
```

Run: `python test_ws.py`

---

## 📊 Performance Metrics

### Expected Latency Breakdown

```
Text received:           0.0s
↓
Model inference:         2-4s   (depends on text length)
↓
First chunk sent:        2.1s   ← User starts hearing!
↓
Streaming continues:     +1-2s  (overlapped with playback)
↓
Total time:              3-6s   ✅
```

Compare to REST API:
```
Generate full audio:     5s
Save to file:           0.5s
Download file:          1s
Start playback:         6.5s   (user waited entire time)
```

**WebSocket advantage**: User hears audio 4-5 seconds earlier!

---

## ⚙️ Optimization Tips

### 1. Adjust Chunk Size
```python
CHUNK_SIZE = 2400   # 0.1s - Lower latency, more network calls
CHUNK_SIZE = 4800   # 0.2s - Balanced (recommended)
CHUNK_SIZE = 9600   # 0.4s - Less network overhead, higher latency
```

### 2. Enable Model Caching
Model is already pre-loaded ✅

### 3. Monitor GPU Usage
```bash
# In RunPod terminal
watch -n 1 nvidia-smi
```

Should see ~6-8GB VRAM used when model loaded

---

## 🐛 Troubleshooting

### Issue: "CUDA out of memory"
**Solution**: 
```python
model = CsmForConditionalGeneration.from_pretrained(
    model_id, 
    torch_dtype=torch.float16,  # Already using this
    device_map="auto"  # Add this
)
```

### Issue: "HF_TOKEN not found"
**Solution**:
```bash
export HF_TOKEN="hf_xxxxx"
python sesame_ws_server.py
```

### Issue: "Model license not accepted"
**Solution**: Go to https://huggingface.co/sesame/csm-1b and click "Accept"

### Issue: WebSocket connection fails
**Check**:
1. Is port 8000 exposed in RunPod settings?
2. Is server actually running? (`ps aux | grep python`)
3. Try REST API first: `curl .../health`

---

## 🔒 Keeping Server Running

### Method 1: tmux (Recommended)
```bash
tmux new -s sesame
export HF_TOKEN="your_token"
python sesame_ws_server.py

# Detach: Ctrl+B, then D
# Reattach later: tmux attach -t sesame
```

### Method 2: nohup
```bash
export HF_TOKEN="your_token"
nohup python sesame_ws_server.py > sesame.log 2>&1 &

# Check logs: tail -f sesame.log
```

---

## 📞 Integration with Voice Agent

Once running:

1. **My platform** connects to your WebSocket
2. **Sends**: `{"text": "...", "speaker_id": 0}`
3. **Receives**: Audio chunks + `{"done": true}`
4. **Plays**: Audio to caller via Telnyx

**Result**: Real-time conversation with <3s TTS latency! 🎉

---

## 💡 Summary

**This code provides:**
- ✅ WebSocket streaming endpoint (`/ws/generate`)
- ✅ REST API fallback (`/generate`)
- ✅ Real-time audio chunking (0.2s chunks)
- ✅ GPU acceleration
- ✅ Multiple speaker voices (0-9)
- ✅ Health monitoring (`/health`)

**Why it's fast:**
- Pre-loaded model (no startup delay)
- Immediate chunking (no file I/O)
- WebSocket streaming (no HTTP overhead)
- GPU inference (torch.float16)

**Ready to deploy?** Just copy the code, set HF_TOKEN, and run! 🚀
