# Complete RunPod Sesame TTS Setup Guide
## Step-by-Step Instructions

---

## PART 1: Setting Up RunPod Environment

### Step 1: Create RunPod Pod
1. Go to https://www.runpod.io/
2. Click "Deploy" → "GPU Pods"
3. Select a GPU (recommend: RTX 3090, RTX 4090, or A5000)
4. Choose template: **PyTorch 2.x** (or any Python 3.10+ image)
5. Set **Expose HTTP Ports**: `8000` (CRITICAL!)
6. Start the pod

### Step 2: Get Your Pod's Public URL
Once the pod is running:
1. Click on your pod
2. Look for **"Connect"** button
3. Find the **TCP Port Mappings** section
4. Your URL will look like: `https://xxxxx-8000.proxy.runpod.net`
5. **Save this URL** - you'll need to update my backend with it

---

## PART 2: Access Jupyter Lab

1. Click **"Connect"** on your pod
2. Select **"Jupyter Lab"** or **"Web Terminal"**
3. If using Jupyter, open a **Terminal** (File → New → Terminal)

---

## PART 3: Install Dependencies

In the terminal, run these commands **one by one**:

```bash
# Update pip
pip install --upgrade pip

# Install required packages
pip install fastapi uvicorn[standard]
pip install transformers torch torchaudio
pip install huggingface_hub
pip install accelerate

# Verify installations
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import transformers; print('Transformers:', transformers.__version__)"
```

**Expected output:** Version numbers for each package

---

## PART 4: Set Up Hugging Face Token (CRITICAL!)

Sesame model requires authentication:

```bash
# Set your Hugging Face token
export HF_TOKEN="your_huggingface_token_here"

# Verify it's set
echo $HF_TOKEN
```

**To get your HF token:**
1. Go to https://huggingface.co/settings/tokens
2. Create a token with "Read" access
3. Copy and paste it in the command above

---

## PART 5: Create Server File

### Option A: Using Terminal (Recommended)

```bash
# Create the server file
cat > /workspace/sesame_server.py << 'EOF'
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import torch
from transformers import CsmForConditionalGeneration, AutoProcessor
import logging
import os
import uuid
from pathlib import Path
from huggingface_hub import login

app = FastAPI()
logging.basicConfig(level=logging.INFO)

device = "cuda" if torch.cuda.is_available() else "cpu"
model_id = "sesame/csm-1b"

# Create output directory
OUTPUT_DIR = Path("/workspace/sesame_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Pre-load model at startup
logging.info("🚀 Pre-loading Sesame model...")
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    login(hf_token)
else:
    logging.warning("⚠️ No HF_TOKEN found, trying without auth...")

processor = AutoProcessor.from_pretrained(model_id)
model = CsmForConditionalGeneration.from_pretrained(
    model_id, torch_dtype=torch.float16
).to(device)
logging.info(f"✅ Model loaded on {device}")

@app.get("/")
async def root():
    return {
        "status": "ok", 
        "device": device, 
        "model_loaded": True,
        "cuda_available": torch.cuda.is_available()
    }

class InputData(BaseModel):
    text: str
    speaker_id: int = 0

@app.post("/generate")
async def generate_audio(data: InputData):
    try:
        logging.info(f"🎤 Generating: {data.text[:50]}... (Speaker {data.speaker_id})")
        
        # Unique filename
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{file_id}.wav"
        
        # Generate audio
        prompt = f"[{data.speaker_id}]{data.text}"
        inputs = processor(text=prompt, add_special_tokens=True).to(device)
        
        with torch.no_grad():
            audio = model.generate(**inputs, output_audio=True)
        
        # Save audio
        processor.save_audio(audio, str(output_path))
        logging.info(f"✅ Saved: {output_path}")
        
        return {
            "message": "Audio generated successfully",
            "file": f"audio/{file_id}.wav"
        }
        
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return {"error": str(e)}, 500

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        return {"error": "File not found"}, 404
    
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=filename
    )

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "device": device,
        "cuda": torch.cuda.is_available()
    }

if __name__ == "__main__":
    import uvicorn
    logging.info("🚀 Starting server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF
```

### Option B: Using Jupyter Notebook

1. Create a new Python file (File → New → Text File)
2. Copy the code from `/app/sesame_server_corrected.py` (I created this for you)
3. Save as `sesame_server.py`

---

## PART 6: Run the Server

```bash
# Make sure HF_TOKEN is set
export HF_TOKEN="your_token_here"

# Run the server
cd /workspace
python sesame_server.py
```

**What you should see:**
```
🚀 Pre-loading Sesame model...
✅ Model loaded on cuda
🚀 Starting server on port 8000...
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal running!** Don't close it.

---

## PART 7: Test Your Server

Open a **NEW terminal** (or notebook cell) and test:

### Test 1: Health Check
```bash
curl http://localhost:8000/
```

**Expected:** `{"status":"ok","device":"cuda","model_loaded":true}`

### Test 2: Generate Audio
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "speaker_id": 0}'
```

**Expected:** `{"message":"Audio generated successfully","file":"audio/xxxxx.wav"}`

### Test 3: Get Audio File
```bash
# Use the filename from previous response
curl http://localhost:8000/audio/xxxxx.wav --output test.wav
ls -lh test.wav
```

**Expected:** WAV file with size > 0 bytes

---

## PART 8: Test From External URL

Get your RunPod public URL (e.g., `https://xxxxx-8000.proxy.runpod.net`)

Test from **outside RunPod**:

```bash
# Health check
curl https://your-runpod-url-here.proxy.runpod.net/

# Generate speech
curl -X POST https://your-runpod-url-here.proxy.runpod.net/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Testing from outside", "speaker_id": 0}'
```

---

## PART 9: Update My Backend

Once your server is running and tested:

1. Get your full RunPod URL (e.g., `https://abc123-8000.proxy.runpod.net`)
2. Tell me the URL
3. I'll update my backend's `sesame_tts_service.py` with your URL

---

## TROUBLESHOOTING

### Issue: "ModuleNotFoundError: No module named 'transformers'"
**Fix:** Run `pip install transformers`

### Issue: "HF_TOKEN not set"
**Fix:** 
```bash
export HF_TOKEN="hf_xxxxxxxxxxxxx"
python sesame_server.py
```

### Issue: "Model loading fails"
**Fix:** Check if you accepted the model license at https://huggingface.co/sesame/csm-1b

### Issue: "Port 8000 already in use"
**Fix:** 
```bash
# Kill existing process
pkill -f "sesame_server.py"
# Or use a different port
uvicorn sesame_server:app --host 0.0.0.0 --port 8001
```

### Issue: "404 when accessing from external URL"
**Fix:** 
- Verify port 8000 is exposed in RunPod settings
- Check server is actually running: `ps aux | grep sesame_server`
- Try accessing `/health` endpoint first

### Issue: "CUDA out of memory"
**Fix:** Use smaller model or restart pod with more VRAM

---

## QUICK START CHECKLIST

- [ ] RunPod pod created with GPU
- [ ] Port 8000 exposed
- [ ] Dependencies installed
- [ ] HF_TOKEN set
- [ ] Server file created
- [ ] Server running (don't close terminal!)
- [ ] Local test works (curl localhost:8000)
- [ ] External test works (curl https://xxx.proxy.runpod.net)
- [ ] Got public URL and shared with me

---

## KEEPING SERVER RUNNING

The server will stop if you close the terminal. To keep it running:

### Option 1: Use tmux (Recommended)
```bash
tmux new -s sesame
export HF_TOKEN="your_token"
python sesame_server.py

# Detach: Press Ctrl+B, then D
# Reattach later: tmux attach -t sesame
```

### Option 2: Use nohup
```bash
export HF_TOKEN="your_token"
nohup python sesame_server.py > server.log 2>&1 &

# Check logs: tail -f server.log
```

### Option 3: Use screen
```bash
screen -S sesame
export HF_TOKEN="your_token"
python sesame_server.py

# Detach: Press Ctrl+A, then D
# Reattach: screen -r sesame
```

---

## WHAT TO SEND ME

Once everything works, send me:

1. ✅ Confirmation that local tests work
2. ✅ Your RunPod public URL (e.g., `https://xxxxx-8000.proxy.runpod.net`)
3. ✅ Response from: `curl https://your-url/health`

Then I'll update my backend to use your endpoint!
