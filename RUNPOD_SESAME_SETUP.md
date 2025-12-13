# RunPod Sesame TTS Setup Guide

This guide will help you set up Sesame TTS on RunPod with a FastAPI endpoint.

## Step 1: Create RunPod Instance
1. Go to RunPod and create a GPU pod (recommend RTX 3090 or better)
2. Use a PyTorch template (e.g., `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel`)
3. Open Jupyter Lab or Terminal

## Step 2: Install Dependencies

Run these commands in a terminal cell:

```bash
pip install fastapi uvicorn torch torchaudio transformers accelerate
pip install sesame-csm-tts  # or the specific Sesame package
```

## Step 3: Create FastAPI Server

Create a file `sesame_server.py` with the following code:

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import torch
import torchaudio
import os
import uuid
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Sesame TTS API")

# Directory for storing generated audio
OUTPUT_DIR = Path("/tmp/sesame_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Global model variable
model = None
device = None

class TTSRequest(BaseModel):
    text: str
    speaker_id: int = 0  # 0-9 for different voices

@app.on_event("startup")
async def load_model():
    """Load Sesame TTS model on startup"""
    global model, device
    
    try:
        logger.info("🚀 Loading Sesame TTS model...")
        
        # Set device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"📱 Using device: {device}")
        
        # Load Sesame model - adjust this based on the actual Sesame package
        # Example for different Sesame implementations:
        
        # Option 1: If using Hugging Face transformers
        from transformers import AutoModelForTextToSpeech, AutoProcessor
        model_name = "sesame/csm-1b"  # or your specific model
        model = AutoModelForTextToSpeech.from_pretrained(model_name).to(device)
        processor = AutoProcessor.from_pretrained(model_name)
        
        # Option 2: If using a custom Sesame package
        # from sesame_tts import SesameTTS
        # model = SesameTTS.load_model().to(device)
        
        logger.info("✅ Model loaded successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error loading model: {e}")
        raise

@app.post("/generate")
async def generate_speech(request: TTSRequest):
    """
    Generate speech from text using Sesame TTS
    
    Args:
        text: Text to convert to speech
        speaker_id: Voice ID (0-9)
    
    Returns:
        JSON with message and file path
    """
    try:
        logger.info(f"🎤 Generating speech for text: {request.text[:50]}...")
        logger.info(f"👤 Speaker ID: {request.speaker_id}")
        
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{file_id}.wav"
        
        # Generate audio using Sesame
        # Adjust this based on your actual Sesame API
        with torch.no_grad():
            # Example generation (adjust to your model's API)
            # audio = model.generate(
            #     text=request.text,
            #     speaker_id=request.speaker_id
            # )
            
            # Placeholder - replace with actual model inference
            # For now, create a simple tone for testing
            sample_rate = 24000
            duration = 2.0  # seconds
            frequency = 440.0  # A4 note
            t = torch.linspace(0, duration, int(sample_rate * duration))
            audio = torch.sin(2 * torch.pi * frequency * t).unsqueeze(0)
        
        # Save as WAV (24kHz, 16-bit PCM)
        torchaudio.save(
            str(output_path),
            audio.cpu(),
            sample_rate=24000,
            encoding="PCM_S",
            bits_per_sample=16
        )
        
        logger.info(f"✅ Audio saved to: {output_path}")
        
        # Return response with file reference
        return JSONResponse(content={
            "message": "Audio generated successfully",
            "file": f"audio/{file_id}.wav"
        })
        
    except Exception as e:
        logger.error(f"❌ Error generating speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve generated audio files"""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=filename
    )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Sesame TTS API",
        "model_loaded": model is not None,
        "device": str(device) if device else "unknown"
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy" if model is not None else "unhealthy",
        "gpu_available": torch.cuda.is_available(),
        "device": str(device) if device else "none"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Run server on port 8000 (RunPod will expose this via proxy)
    logger.info("🚀 Starting Sesame TTS Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Step 4: Run the Server

In a terminal:

```bash
python sesame_server.py
```

Or in a Jupyter notebook cell:

```python
!python sesame_server.py &
```

## Step 5: Test the API

Once running, test it:

```bash
# Health check
curl https://qv6z753y20ct59-8000.proxy.runpod.net/

# Generate speech
curl -X POST https://qv6z753y20ct59-8000.proxy.runpod.net/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test", "speaker_id": 0}'
```

## Important Notes:

1. **Model Loading**: The code above has a placeholder for model loading. You need to adjust it based on the actual Sesame TTS package/API you're using.

2. **Port 8000**: RunPod proxies port 8000 to your external URL (`qv6z753y20ct59-8000.proxy.runpod.net`)

3. **Speaker IDs**: The code supports speaker_id 0-9. You can map these to different voices in your model.

4. **Audio Format**: The code generates 24kHz, 16-bit PCM WAV files as required.

5. **Keep Running**: To keep the server running in Jupyter, use the `&` operator or run in a separate terminal.

## Alternative: Quick Test Server

If you just want to test the integration, here's a minimal test server:

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse
import torchaudio
import torch

app = FastAPI()

@app.post("/generate")
async def generate(data: dict):
    # Generate simple test audio
    sample_rate = 24000
    duration = 1.0
    t = torch.linspace(0, duration, int(sample_rate * duration))
    audio = torch.sin(2 * torch.pi * 440 * t).unsqueeze(0)
    
    # Save
    path = "/tmp/test.wav"
    torchaudio.save(path, audio, sample_rate, encoding="PCM_S", bits_per_sample=16)
    
    return {"message": "OK", "file": "audio/test.wav"}

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    return FileResponse("/tmp/test.wav", media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Troubleshooting:

- **Port issues**: Make sure you're running on port 8000
- **Model loading**: Check Sesame documentation for correct model loading
- **GPU memory**: Monitor GPU usage, Sesame models can be large
- **Firewall**: RunPod automatically handles proxy, no firewall config needed
