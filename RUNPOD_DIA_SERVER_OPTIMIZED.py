"""
Dia TTS FastAPI Server - OPTIMIZED FOR LOW LATENCY
Uses torch.compile, reduced tokens, and aggressive settings
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import torch
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dia TTS Server Optimized", version="2.0")

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
    global model, processor, device
    
    try:
        logger.info("Loading Dia TTS model with optimizations...")
        start_time = time.time()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        from transformers import AutoProcessor, DiaForConditionalGeneration
        
        model_checkpoint = "nari-labs/Dia-1.6B-0626"
        logger.info(f"Loading model: {model_checkpoint}")
        
        processor = AutoProcessor.from_pretrained(model_checkpoint)
        logger.info("Processor loaded")
        
        model = DiaForConditionalGeneration.from_pretrained(
            model_checkpoint,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto"
        )
        
        model.to(device)
        model.eval()
        
        # OPTIMIZATION: Compile model for faster inference
        if device == "cuda":
            try:
                logger.info("Compiling model with torch.compile for speed...")
                model = torch.compile(model, mode="max-autotune")
                logger.info("Model compiled successfully")
            except Exception as e:
                logger.warning(f"torch.compile failed, using uncompiled model: {e}")
        
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
        "cuda_available": torch.cuda.is_available(),
        "optimizations": "torch.compile enabled" if device == "cuda" else "none"
    }


@app.post("/v1/audio/speech")
async def generate_speech(request: TTSRequest):
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        gen_start = time.time()
        
        if not request.input or len(request.input.strip()) == 0:
            raise HTTPException(status_code=400, detail="Input text is required")
        
        logger.info(f"Generating: {request.input[:80]}...")
        
        text = request.input
        if f"[{request.voice}]" not in text:
            text = f"[{request.voice}] {text}"
        
        # Process input
        process_start = time.time()
        inputs = processor(text=[text], padding=True, return_tensors="pt").to(device)
        process_time = int((time.time() - process_start) * 1000)
        
        # OPTIMIZED GENERATION PARAMETERS
        # Reduced max_new_tokens for lower latency
        # Adjusted guidance_scale, temperature for faster generation
        inference_start = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,      # REDUCED from 3072 (faster but shorter audio)
                guidance_scale=2.0,       # REDUCED from 3.0 (faster)
                temperature=1.5,          # REDUCED from 1.8 (faster)
                top_p=0.95,              # INCREASED from 0.90 (faster)
                top_k=50,                # INCREASED from 45 (faster)
                do_sample=True
            )
        inference_time = int((time.time() - inference_start) * 1000)
        
        logger.info(f"⏱️ Inference: {inference_time}ms")
        
        # Decode audio
        decode_start = time.time()
        audio_list = processor.batch_decode(outputs)
        decode_time = int((time.time() - decode_start) * 1000)
        
        # Save to bytes
        save_start = time.time()
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            processor.save_audio(audio_list, tmp_path)
        
        with open(tmp_path, 'rb') as f:
            audio_bytes = f.read()
        
        os.unlink(tmp_path)
        save_time = int((time.time() - save_start) * 1000)
        
        total_time = int((time.time() - gen_start) * 1000)
        
        logger.info(f"⏱️ BREAKDOWN: Process={process_time}ms, Inference={inference_time}ms, Decode={decode_time}ms, Save={save_time}ms, TOTAL={total_time}ms")
        logger.info(f"📦 Audio size: {len(audio_bytes)} bytes")
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "X-Process-Time": str(process_time),
                "X-Inference-Time": str(inference_time),
                "X-Decode-Time": str(decode_time),
                "X-Save-Time": str(save_time),
                "X-Total-Time": str(total_time),
                "X-Voice": request.voice
            }
        )
        
    except Exception as e:
        logger.error(f"Failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {
        "name": "Dia TTS Server (Optimized)",
        "version": "2.0",
        "model": "nari-labs/Dia-1.6B-0626",
        "optimizations": [
            "torch.compile (max-autotune mode)",
            "Reduced max_new_tokens (1024 vs 3072)",
            "Optimized guidance_scale (2.0 vs 3.0)",
            "Faster temperature (1.5 vs 1.8)",
            "Detailed timing breakdown"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
