"""
Dia TTS FastAPI Server for RunPod - FIXED VERSION
Uses correct checkpoint and model class
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import torch
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dia TTS Server", version="1.0")

model = None
processor = None
device = None

class TTSRequest(BaseModel):
    model: str = "dia-tts"
    input: str
    voice: str = "S1"
    response_format: str = "mp3"
    speed: float = 1.0


def load_model():
    """Load Dia TTS model with correct checkpoint"""
    global model, processor, device
    
    try:
        logger.info("Loading Dia TTS model...")
        start_time = time.time()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        from transformers import AutoProcessor, DiaForConditionalGeneration
        
        # Use the correct checkpoint
        model_checkpoint = "nari-labs/Dia-1.6B-0626"
        
        logger.info(f"Loading model: {model_checkpoint}")
        
        # Load processor
        processor = AutoProcessor.from_pretrained(model_checkpoint)
        logger.info("Processor loaded")
        
        # Load model with correct class
        model = DiaForConditionalGeneration.from_pretrained(
            model_checkpoint,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto"
        )
        
        model.to(device)
        model.eval()
        
        elapsed = time.time() - start_time
        logger.info(f"Model loaded successfully in {elapsed:.2f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


@app.on_event("startup")
async def startup_event():
    success = load_model()
    if not success:
        logger.error("Server started but model failed to load")
    else:
        logger.info("Server ready to handle requests")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if model is not None else "unhealthy",
        "model_loaded": model is not None,
        "processor_loaded": processor is not None,
        "device": str(device) if device else "unknown",
        "cuda_available": torch.cuda.is_available()
    }


@app.post("/v1/audio/speech")
async def generate_speech(request: TTSRequest):
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        gen_start = time.time()
        
        if not request.input or len(request.input.strip()) == 0:
            raise HTTPException(status_code=400, detail="Input text is required")
        
        logger.info(f"Generating TTS for: {request.input[:80]}...")
        
        # Prepare text with speaker tags
        text = request.input
        if f"[{request.voice}]" not in text:
            text = f"[{request.voice}] {text}"
        
        # Process input
        inputs = processor(
            text=[text],
            padding=True,
            return_tensors="pt"
        ).to(device)
        
        # Generate audio
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=3072,
                guidance_scale=3.0,
                temperature=1.8,
                top_p=0.90,
                top_k=45
            )
        
        gen_time = int((time.time() - gen_start) * 1000)
        logger.info(f"Generation time: {gen_time}ms")
        
        # Decode audio
        encode_start = time.time()
        audio_list = processor.batch_decode(outputs)
        
        # Save to bytes
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            processor.save_audio(audio_list, tmp_path)
        
        # Read the audio file
        with open(tmp_path, 'rb') as f:
            audio_bytes = f.read()
        
        # Cleanup
        os.unlink(tmp_path)
        
        encode_time = int((time.time() - encode_start) * 1000)
        total_time = int((time.time() - gen_start) * 1000)
        
        logger.info(f"Complete: Gen={gen_time}ms, Enc={encode_time}ms, Total={total_time}ms")
        logger.info(f"Audio size: {len(audio_bytes)} bytes")
        
        # Determine media type
        media_type_map = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac"
        }
        media_type = media_type_map.get(request.response_format, "audio/mpeg")
        
        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={
                "X-Generation-Time": str(gen_time),
                "X-Encoding-Time": str(encode_time),
                "X-Total-Time": str(total_time),
                "X-Voice": request.voice,
                "X-Speed": str(request.speed),
                "X-Format": request.response_format
            }
        )
        
    except Exception as e:
        logger.error(f"TTS generation failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.get("/")
async def root():
    return {
        "name": "Dia TTS Server",
        "version": "1.0",
        "model": "nari-labs/Dia-1.6B-0626",
        "endpoints": {
            "health": "/health",
            "tts": "/v1/audio/speech (POST)"
        },
        "features": [
            "Multi-speaker dialogue ([S1], [S2], [S3], [S4])",
            "Non-verbal sounds ((laughs), (sighs), (gasps))",
            "Speed control (0.25 - 4.0x)",
            "Multiple formats (wav, mp3, opus, aac, flac)",
            "Ultra-realistic 1.6B parameter model"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
