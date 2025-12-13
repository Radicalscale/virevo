# ChatTTS RunPod Deployment Guide

## Server Specifications
- **GPU**: RTX 4090 (recommended)
- **VRAM**: 10GB+ recommended
- **CUDA**: 11.8 or 12.x
- **Python**: 3.10+

## Quick Start

### 1. SSH into your RunPod instance

```bash
ssh root@<your-runpod-ip>
```

### 2. Install dependencies

```bash
# Update system
apt-get update && apt-get install -y ffmpeg libsndfile1

# Install Python packages
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r RUNPOD_CHATTTS_REQUIREMENTS.txt
```

### 3. Install ChatTTS

```bash
# Option 1: From pip (stable)
pip install ChatTTS

# Option 2: From GitHub (latest)
pip install git+https://github.com/2noise/ChatTTS.git
```

### 4. Upload the server script

Upload `RUNPOD_CHATTTS_SERVER.py` to your RunPod instance or copy-paste the content.

### 5. Start the server

```bash
# Run on port 8000 (or any port you prefer)
python RUNPOD_CHATTTS_SERVER.py

# Or with custom port
PORT=7860 python RUNPOD_CHATTTS_SERVER.py

# Run in background with nohup
nohup python RUNPOD_CHATTTS_SERVER.py > chattts.log 2>&1 &
```

### 6. Expose the port

In RunPod dashboard:
- Go to your pod settings
- Add port mapping: Internal `8000` → External (auto-assigned)
- Note the external URL (e.g., `https://xxxxx-8000.proxy.runpod.net`)

## API Endpoints

### Health Check
```bash
curl https://your-runpod-url/health
```

### List Available Voices
```bash
curl https://your-runpod-url/voices
```

### Generate Speech
```bash
curl -X POST https://your-runpod-url/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is ChatTTS speaking!",
    "voice": "female_1",
    "speed": 1.0,
    "temperature": 0.3,
    "response_format": "wav"
  }' \
  --output test_output.wav
```

## Voice Options

Pre-configured voices with cached embeddings:
- `male_1`, `male_2`, `male_3` - Male voices
- `female_1`, `female_2`, `female_3` - Female voices
- `neutral_1`, `neutral_2` - Neutral voices

Each voice has a unique seed for consistent output.

## Parameters

### Required
- `text`: Text to convert to speech

### Optional
- `voice`: Voice preset (default: "female_1")
- `speed`: Speech speed 0.5-2.0 (default: 1.0)
- `temperature`: Sampling temperature 0.0-1.0 (default: 0.3)
  - Lower = more stable, faster, less variation
  - Higher = more expressive, slower
- `top_p`: Top-p sampling 0.0-1.0 (default: 0.7)
- `top_k`: Top-k sampling 1-50 (default: 20)
- `response_format`: "wav" or "mp3" (default: "wav")

## Performance Optimization Tips

### 1. Use Low Temperature
```json
{
  "temperature": 0.3  // Faster and more stable
}
```

### 2. Optimize Sampling Parameters
```json
{
  "top_p": 0.7,
  "top_k": 20
}
```

### 3. Keep Text Short
- Batch longer texts into smaller chunks
- Ideal: 1-2 sentences per request

### 4. Use Cached Voices
- Stick to pre-defined voices (male_1, female_1, etc.)
- Cached embeddings = faster inference

## Expected Performance

With RTX 4090 and optimizations:
- **First request** (warmup): ~3-5 seconds
- **Subsequent requests**: ~0.5-1.5 seconds
- **Real-Time Factor (RTF)**: ~0.3
- **Latency**: <1 second for short texts

## Monitoring

Check logs for performance metrics:
```bash
tail -f chattts.log
```

Each request logs:
- Processing time
- Audio duration
- Real-Time Factor (RTF)
- Inference time

## Troubleshooting

### Server won't start
```bash
# Check dependencies
pip list | grep -E "ChatTTS|torch|fastapi"

# Check GPU
nvidia-smi

# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### Slow inference
- Ensure `compile=True` is enabled
- Check GPU utilization: `nvidia-smi`
- Reduce temperature and top_k/top_p
- Use shorter text inputs

### Memory issues
- Restart server to clear cache
- Reduce batch size
- Check available VRAM: `nvidia-smi`

## Advanced Configuration

### Custom Voice Seeds

Add more voices by editing the `VOICE_SEEDS` dictionary:
```python
VOICE_SEEDS = {
    "custom_voice": 999,  # Any integer seed
}
```

### Adjust Warmup

Modify the warmup text in `load_chattts_model()` to match your use case.

### Different Model Source

Change in `chat.load()`:
```python
chat.load(compile=True, source="huggingface")  # or "local"
```

## Integration with Main App

Once the server is running, note your RunPod URL and add to your main app's `.env`:

```bash
CHATTTS_API_URL=https://xxxxx-8000.proxy.runpod.net
```

## Cost Optimization

- Use RunPod's Spot instances for lower cost
- Stop pod when not in use
- Consider serverless deployment for occasional use

## Next Steps

1. Test with various voices and parameters
2. Benchmark latency for your use case
3. Integrate into your main application
4. Set up monitoring and alerts

---

**Server Status**: Ready for production use with RTX 4090
**Optimization Level**: Ultra-low latency
**Target Latency**: <1 second
