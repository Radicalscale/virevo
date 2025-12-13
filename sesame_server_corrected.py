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

# Create output directory for generated audio files
OUTPUT_DIR = Path("/tmp/sesame_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Pre-load model at startup for fast inference
logging.info("Pre-loading full model...")
login(os.getenv("HF_TOKEN"))
processor = AutoProcessor.from_pretrained(model_id)
model = CsmForConditionalGeneration.from_pretrained(
    model_id, torch_dtype=torch.float16
).to(device)
logging.info("Model pre-loaded.")

@app.get("/")
async def root():
    return {"status": "ok", "device": device, "model_loaded": True}

class InputData(BaseModel):
    text: str
    speaker_id: int = 0  # 0-9 for different voices

@app.post("/generate")
async def generate_audio(data: InputData):
    """
    Generate audio and return a reference to download it
    
    CRITICAL FIXES:
    1. Use unique filename (UUID) to avoid overwriting concurrent requests
    2. Save to dedicated output directory
    3. Return path that can be fetched via GET endpoint
    4. Add proper error handling
    """
    try:
        logging.info(f"🎤 Generating audio for: {data.text[:50]}...")
        logging.info(f"👤 Speaker ID: {data.speaker_id}")
        
        # Generate unique filename to avoid conflicts
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{file_id}.wav"
        
        # Format prompt with speaker ID
        prompt = f"[{data.speaker_id}]{data.text}"
        
        # Generate audio
        inputs = processor(text=prompt, add_special_tokens=True).to(device)
        with torch.no_grad():
            audio = model.generate(**inputs, output_audio=True)
        
        # Save with unique filename
        processor.save_audio(audio, str(output_path))
        
        logging.info(f"✅ Audio saved to: {output_path}")
        
        # Return the path that can be fetched via GET /audio/{filename}
        return {
            "message": "Audio generated successfully",
            "file": f"audio/{file_id}.wav"  # This is the path to GET the file
        }
        
    except Exception as e:
        logging.error(f"❌ Error generating audio: {e}")
        return {"error": str(e)}, 500

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """
    Serve the generated audio file
    
    THIS WAS MISSING - Critical for the integration to work!
    The backend will call this endpoint to fetch the generated WAV file.
    """
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        logging.error(f"❌ File not found: {file_path}")
        return {"error": "Audio file not found"}, 404
    
    logging.info(f"📤 Serving audio file: {filename}")
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=filename
    )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "device": device,
        "cuda_available": torch.cuda.is_available(),
        "model_loaded": model is not None
    }

if __name__ == "__main__":
    import uvicorn
    logging.info("🚀 Starting Sesame TTS Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
