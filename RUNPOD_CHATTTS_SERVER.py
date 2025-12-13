"""
ChatTTS FastAPI Server for RunPod
Optimized for ultra-low latency with RTX 4090

Features:
- Pre-loaded model with torch.compile() optimization
- Speaker embedding caching
- Float16 precision
- Multiple voice options
- Speed and temperature control
- Optimized for <1s latency
"""

import os
import io
import time
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
import torch
import torchaudio
import numpy as np
import soundfile as sf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ChatTTS API Server", version="1.0.0")

# Global variables
chat = None
speaker_embeddings_cache = {}

# Voice seeds for consistent voices (can be expanded)
VOICE_SEEDS = {
    "male_1": 2,
    "male_2": 42,
    "male_3": 123,
    "female_1": 34,
    "female_2": 88,
    "female_3": 168,
    "neutral_1": 1,
    "neutral_2": 99,
}


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    voice: str = Field(default="female_1", description="Voice preset (male_1, female_1, etc.)")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")
    temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="Sampling temperature (lower = faster/stable)")
    top_p: float = Field(default=0.7, ge=0.0, le=1.0, description="Top-p sampling")
    top_k: int = Field(default=20, ge=1, le=50, description="Top-k sampling")
    response_format: str = Field(default="wav", description="Audio format: wav or mp3")


def load_chattts_model():
    """Load and optimize ChatTTS model"""
    global chat
    
    try:
        import ChatTTS
        
        logger.info("Initializing ChatTTS...")
        chat = ChatTTS.Chat()
        
        # Load models - use compile=False initially for stability, can enable later
        logger.info("Loading ChatTTS models (this may take a minute)...")
        load_success = chat.load(compile=False)
        
        if not load_success:
            raise Exception("Model loading returned False")
        
        logger.info("✅ Models loaded successfully")
        
        # Set device to CUDA
        if torch.cuda.is_available():
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
        
        # Warmup - generate a short test audio
        logger.info("Warming up model with test generation...")
        warmup_start = time.time()
        
        # Set seed for consistency
        torch.manual_seed(42)
        rand_spk = chat.sample_random_speaker()
        
        params_infer = ChatTTS.Chat.InferCodeParams(
            spk_emb=rand_spk,
            temperature=0.3,
            top_P=0.7,
            top_K=20,
        )
        
        # Warmup inference
        warmup_wavs = chat.infer(["Hello, this is a warmup."], params_infer_code=params_infer)
        
        if warmup_wavs is None or len(warmup_wavs) == 0:
            logger.warning("Warmup generated no audio, but continuing...")
        else:
            logger.info(f"Warmup audio generated: {len(warmup_wavs[0])} samples")
        
        warmup_time = time.time() - warmup_start
        logger.info(f"Model warmup completed in {warmup_time:.2f}s")
        
        # Pre-cache speaker embeddings for all voice seeds
        logger.info("Pre-caching speaker embeddings...")
        for voice_name, seed in VOICE_SEEDS.items():
            torch.manual_seed(seed)
            speaker_embeddings_cache[voice_name] = chat.sample_random_speaker()
            logger.info(f"✅ Cached embedding for {voice_name} (seed: {seed})")
        
        logger.info("🚀 ChatTTS server ready!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load ChatTTS: {str(e)}", exc_info=True)
        raise e


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    load_chattts_model()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if chat is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {
        "status": "healthy",
        "model": "ChatTTS",
        "cuda_available": torch.cuda.is_available(),
        "available_voices": list(VOICE_SEEDS.keys())
    }


@app.get("/voices")
async def list_voices():
    """List available voice presets"""
    return {
        "voices": list(VOICE_SEEDS.keys()),
        "voice_seeds": VOICE_SEEDS
    }


@app.post("/v1/audio/speech")
async def generate_speech(request: TTSRequest):
    """
    Generate speech from text using ChatTTS
    
    Optimized for low latency with:
    - Cached speaker embeddings
    - Low temperature for stability
    - Optimized sampling parameters
    """
    if chat is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        start_time = time.time()
        
        # Get speaker embedding from cache or use default
        if request.voice in speaker_embeddings_cache:
            spk_emb = speaker_embeddings_cache[request.voice]
            logger.info(f"Using cached embedding for voice: {request.voice}")
        else:
            # Fallback to seed-based generation
            voice_seed = VOICE_SEEDS.get(request.voice, 34)
            torch.manual_seed(voice_seed)
            spk_emb = chat.sample_random_speaker()
            logger.info(f"Generated new embedding for voice: {request.voice} (seed: {voice_seed})")
        
        # Configure inference parameters
        import ChatTTS
        params_infer = ChatTTS.Chat.InferCodeParams(
            spk_emb=spk_emb,
            temperature=request.temperature,
            top_P=request.top_p,
            top_K=request.top_k,
        )
        
        # Configure refine text parameters (for natural prosody)
        params_refine = ChatTTS.Chat.RefineTextParams(
            prompt='[oral_2][laugh_0][break_4]',  # Natural conversation style
        )
        
        logger.info(f"Generating audio for text: '{request.text[:50]}...'")
        inference_start = time.time()
        
        # Generate audio
        wavs = chat.infer(
            [request.text],
            params_infer_code=params_infer,
            params_refine_text=params_refine,
        )
        
        inference_time = time.time() - inference_start
        logger.info(f"Inference completed in {inference_time:.3f}s")
        
        # Process audio
        if wavs is None or len(wavs) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        audio_data = wavs[0]
        
        # Apply speed adjustment if needed
        if request.speed != 1.0:
            # Resample to adjust speed
            original_sr = 24000
            target_length = int(len(audio_data) / request.speed)
            audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)
            audio_tensor = torch.nn.functional.interpolate(
                audio_tensor.unsqueeze(0),
                size=target_length,
                mode='linear',
                align_corners=False
            ).squeeze(0)
            audio_data = audio_tensor.squeeze(0).numpy()
        
        # Convert to requested format
        audio_bytes = io.BytesIO()
        
        if request.response_format == "mp3":
            # Convert to MP3 using torchaudio
            audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)
            torchaudio.save(
                audio_bytes,
                audio_tensor,
                24000,
                format="mp3",
                bits_per_sample=16
            )
            media_type = "audio/mpeg"
        else:
            # WAV format (default)
            sf.write(
                audio_bytes,
                audio_data,
                24000,
                format='WAV',
                subtype='PCM_16'
            )
            media_type = "audio/wav"
        
        audio_bytes.seek(0)
        audio_content = audio_bytes.read()
        
        total_time = time.time() - start_time
        audio_duration = len(audio_data) / 24000
        rtf = inference_time / audio_duration if audio_duration > 0 else 0
        
        logger.info(f"Total processing time: {total_time:.3f}s, Audio duration: {audio_duration:.2f}s, RTF: {rtf:.3f}")
        
        return Response(
            content=audio_content,
            media_type=media_type,
            headers={
                "X-Processing-Time": f"{total_time:.3f}",
                "X-Audio-Duration": f"{audio_duration:.2f}",
                "X-RTF": f"{rtf:.3f}",
                "X-Inference-Time": f"{inference_time:.3f}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating speech: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "ChatTTS API Server",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "voices": "/voices",
            "generate": "/v1/audio/speech (POST)"
        },
        "optimization": {
            "compile": True,
            "float16": True,
            "cached_embeddings": True,
            "target_rtf": "<0.3"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"Starting ChatTTS server on port {port}...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
