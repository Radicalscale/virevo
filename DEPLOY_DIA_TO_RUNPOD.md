# Dia TTS RunPod Deployment Guide

## Overview
Deploy Dia TTS (1.6B parameter ultra-realistic text-to-speech model) on RunPod with OpenAI-compatible API.

## Prerequisites
- RunPod account with GPU pod access
- At least 16GB GPU RAM (RTX 3090, RTX 4090, A5000, or better)
- Basic understanding of RunPod interface

## Deployment Steps

### 1. Create RunPod Pod
1. Go to RunPod.io and log in
2. Click "Deploy" → "GPU Pods"
3. Select a GPU with at least 16GB VRAM:
   - **Recommended**: RTX 4090 (24GB) or A5000 (24GB)
   - **Minimum**: RTX 3090 (24GB)
4. Choose a template:
   - **Recommended**: PyTorch 2.1+ with CUDA 12.1
   - Or use: `runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel`
5. Set TCP ports:
   - **External Port**: 10230
   - **Internal Port**: 8000
   - This creates the mapping: `203.57.40.158:10230 → container:8000`
6. Deploy the pod

### 2. Connect to Pod
```bash
# SSH into your RunPod instance
ssh root@<your-pod-ip> -p <ssh-port>
```

### 3. Setup Working Directory
```bash
# Create working directory
mkdir -p /workspace/dia_tts_api
cd /workspace/dia_tts_api

# Copy the server files
# Option A: Use the files from this repo
# Option B: Copy manually (see below)
```

### 4. Upload Server Files

**Upload these files to `/workspace/dia_tts_api/`:**

1. `RUNPOD_DIA_SERVER.py` - The FastAPI server
2. `RUNPOD_DIA_REQUIREMENTS.txt` - Python dependencies

**Or create them directly:**

```bash
# Create requirements.txt (copy content from RUNPOD_DIA_REQUIREMENTS.txt)
nano requirements.txt

# Create server.py (copy content from RUNPOD_DIA_SERVER.py)
nano server.py
```

### 5. Install Dependencies
```bash
# Update pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# This will download:
# - FastAPI, Uvicorn
# - PyTorch, Transformers
# - Audio processing libraries
```

### 6. Download Dia TTS Model
```bash
# The model will auto-download on first run, but you can pre-download:
python3 << 'EOF'
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

print("📦 Pre-downloading Dia TTS model...")
model_name = "nari-labs/dia-1.6b"

# Download model (this may take 5-10 minutes for ~3GB model)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)

print("✅ Model downloaded successfully!")
EOF
```

### 7. Start the Server

**Option A: Direct run (foreground)**
```bash
python3 server.py
```

**Option B: Background with screen (recommended)**
```bash
# Install screen if not available
apt-get update && apt-get install -y screen

# Start in screen session
screen -S dia_tts
python3 server.py

# Detach with: Ctrl+A, then D
# Reattach with: screen -r dia_tts
```

**Option C: Background with nohup**
```bash
nohup python3 server.py > dia_tts.log 2>&1 &

# Check logs
tail -f dia_tts.log
```

**Option D: Systemd service (for persistence)**
```bash
# Create service file
cat > /etc/systemd/system/dia-tts.service << 'EOF'
[Unit]
Description=Dia TTS API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/dia_tts_api
ExecStart=/usr/bin/python3 /workspace/dia_tts_api/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable dia-tts
systemctl start dia-tts

# Check status
systemctl status dia-tts

# View logs
journalctl -u dia-tts -f
```

### 8. Test the Server

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda:0",
  "cuda_available": true
}
```

**Test TTS Generation:**
```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "dia-tts",
    "input": "Hello! This is a test of Dia TTS.",
    "voice": "S1",
    "response_format": "wav",
    "speed": 1.0
  }' \
  --output test_output.wav

# Play the audio (if you have audio tools)
# Or download and play locally
```

**Test with Multi-Speaker Dialogue:**
```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "dia-tts",
    "input": "[S1] Hi there! How are you? [S2] I am doing great, thanks for asking!",
    "voice": "S1",
    "response_format": "wav",
    "speed": 1.0
  }' \
  --output dialogue_test.wav
```

**Test with Non-Verbal Sounds:**
```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "dia-tts",
    "input": "[S1] That is so funny! (laughs) I cannot believe it happened.",
    "voice": "S1",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output laugh_test.mp3
```

### 9. Configure Your Application

Update your backend to use the RunPod endpoint:

```python
# In dia_tts_service.py
def __init__(self, api_url: str = "http://203.57.40.158:10230"):
    self.api_url = api_url
    self.tts_endpoint = f"{api_url}/v1/audio/speech"
```

The mapping is:
- **External**: `http://203.57.40.158:10230` (your app connects here)
- **Internal**: `http://localhost:8000` (server listens here)
- RunPod automatically forwards: `external:10230 → container:8000`

### 10. Verify External Access

From your local machine or application server:
```bash
curl http://203.57.40.158:10230/health
```

If this works, your Dia TTS server is ready! ✅

## Troubleshooting

### Server Won't Start
```bash
# Check if port 8000 is already in use
netstat -tulpn | grep 8000

# Kill existing process if needed
kill -9 $(lsof -t -i:8000)
```

### Model Load Fails
```bash
# Check GPU availability
nvidia-smi

# Check CUDA
python3 -c "import torch; print(torch.cuda.is_available())"

# Check disk space
df -h
```

### Slow Generation
- Ensure you're using GPU (check logs for "Using device: cuda")
- Try using float16 precision (already enabled)
- Monitor GPU usage: `watch -n 1 nvidia-smi`

### Out of Memory
- Reduce batch size (if processing multiple requests)
- Use a larger GPU
- Clear CUDA cache: `torch.cuda.empty_cache()`

## Performance Optimization

### 1. Model Optimization
```python
# In server code, add:
import torch
torch.backends.cudnn.benchmark = True
torch.set_float32_matmul_precision('high')
```

### 2. Caching
The model stays loaded in memory for fast subsequent requests.

### 3. Monitoring
```bash
# Watch server logs
tail -f dia_tts.log

# Monitor GPU
watch -n 1 nvidia-smi
```

## API Reference

### POST /v1/audio/speech

**Request Body:**
```json
{
  "model": "dia-tts",           // Required (any string)
  "input": "Text to speak",     // Required
  "voice": "S1",                // S1, S2, S3, S4 (default: S1)
  "response_format": "wav",     // wav, mp3, opus, aac, flac (default: wav)
  "speed": 1.0                  // 0.25 to 4.0 (default: 1.0)
}
```

**Response:**
- Binary audio data
- Content-Type: audio/wav (or appropriate format)
- Headers include timing information

### Special Features

**Multi-Speaker Dialogue:**
```
[S1] First speaker says this. [S2] Second speaker responds.
```

**Non-Verbal Sounds:**
```
This is amazing! (laughs) I'm so happy. (sighs with relief)
```

**Supported Non-Verbals:**
- (laughs), (sighs), (gasps), (coughs), (clears throat)
- (whispers), (shouts), (whispers)

## Cost Optimization

1. **Use Spot Instances** (if available) for lower costs
2. **Stop Pod When Idle** to save money
3. **Use On-Demand** for production workloads

## Security

1. **Add Authentication** if exposing publicly
2. **Use HTTPS** (set up reverse proxy with nginx)
3. **Rate Limiting** to prevent abuse

## Next Steps

- ✅ Server running on RunPod
- ✅ External access configured (203.57.40.158:10230)
- ✅ Backend integrated (dia_tts_service.py)
- ✅ Frontend UI ready (AgentForm.jsx)

**You're all set! Create an agent with Dia TTS and enjoy ultra-realistic voices!** 🎤✨
