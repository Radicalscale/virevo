"""
Sesame TTS WebSocket Server for RunPod
Real-time audio streaming implementation
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
import torch
from transformers import CsmForConditionalGeneration, AutoProcessor
import logging
import os
import uuid
import json
import numpy as np
from pathlib import Path
from huggingface_hub import login

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

device = "cuda" if torch.cuda.is_available() else "cpu"
model_id = "sesame/csm-1b"

# Create output directory
OUTPUT_DIR = Path("/tmp/sesame_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Pre-load model at startup
logger.info("🚀 Pre-loading Sesame model...")
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    login(hf_token)
else:
    logger.warning("⚠️ No HF_TOKEN found")

processor = AutoProcessor.from_pretrained(model_id)
model = CsmForConditionalGeneration.from_pretrained(
    model_id, torch_dtype=torch.float16
).to(device)
logger.info(f"✅ Model loaded on {device}")


@app.get("/")
async def root():
    return {
        "status": "ok",
        "device": device,
        "model_loaded": True,
        "websocket_endpoint": "/ws/generate"
    }


@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    """
    WebSocket endpoint for real-time TTS streaming
    
    Protocol:
    1. Client connects
    2. Client sends: {"text": "...", "speaker_id": 0}
    3. Server streams: Raw PCM audio chunks (bytes)
    4. Server sends: {"done": true} when complete
    """
    await websocket.accept()
    logger.info("🔗 WebSocket client connected")
    
    try:
        # Receive generation request
        data = await websocket.receive_text()
        request = json.loads(data)
        
        text = request.get("text", "")
        speaker_id = request.get("speaker_id", 0)
        
        logger.info(f"📝 Generating for: {text[:50]}...")
        logger.info(f"🎤 Speaker ID: {speaker_id}")
        
        if not text:
            await websocket.send_json({"error": "No text provided"})
            await websocket.close()
            return
        
        # Format prompt
        prompt = f"[{speaker_id}]{text}"
        
        # Generate audio
        inputs = processor(text=prompt, add_special_tokens=True).to(device)
        
        with torch.no_grad():
            # Generate complete audio
            audio = model.generate(**inputs, output_audio=True)
        
        logger.info(f"✅ Audio generated: {audio.shape}")
        
        # Convert to numpy array if needed
        if isinstance(audio, torch.Tensor):
            audio_array = audio.cpu().numpy()
        else:
            audio_array = np.array(audio)
        
        # Flatten if needed
        if len(audio_array.shape) > 1:
            audio_array = audio_array.flatten()
        
        # Convert to int16 PCM
        audio_int16 = (audio_array * 32767).astype(np.int16)
        
        # Stream in chunks for low latency
        CHUNK_SIZE = 4800  # 0.2 seconds at 24kHz (good balance)
        total_chunks = (len(audio_int16) + CHUNK_SIZE - 1) // CHUNK_SIZE
        
        logger.info(f"📤 Streaming {total_chunks} chunks...")
        
        for i in range(0, len(audio_int16), CHUNK_SIZE):
            chunk = audio_int16[i:i + CHUNK_SIZE]
            
            # Send raw bytes
            await websocket.send_bytes(chunk.tobytes())
            
            if i == 0:
                logger.info(f"🎵 First chunk sent ({len(chunk)} samples)")
        
        # Signal completion
        await websocket.send_json({"done": True})
        logger.info("✅ Streaming complete")
        
    except WebSocketDisconnect:
        logger.info("🔌 Client disconnected")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


# Keep REST API for backwards compatibility
class InputData(BaseModel):
    text: str
    speaker_id: int = 0


@app.post("/generate")
async def generate_audio(data: InputData):
    """REST API endpoint (legacy)"""
    try:
        logger.info(f"🎤 REST API: Generating audio for: {data.text[:50]}...")
        logger.info(f"👤 Speaker ID: {data.speaker_id}")
        
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{file_id}.wav"
        
        prompt = f"[{data.speaker_id}]{data.text}"
        inputs = processor(text=prompt, add_special_tokens=True).to(device)
        
        with torch.no_grad():
            audio = model.generate(**inputs, output_audio=True)
        
        processor.save_audio(audio, str(output_path))
        logger.info(f"✅ Audio saved to: {output_path}")
        
        return {
            "message": "Audio generated successfully",
            "file": f"audio/{file_id}.wav"
        }
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {"error": str(e)}, 500


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve audio files"""
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
        "cuda": torch.cuda.is_available(),
        "model_loaded": model is not None,
        "endpoints": {
            "websocket": "/ws/generate",
            "rest": "/generate"
        }
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Sesame TTS Server (WebSocket + REST) on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
