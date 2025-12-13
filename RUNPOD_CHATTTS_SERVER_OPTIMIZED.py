"""
ChatTTS FastAPI Server for RunPod - ULTRA LOW LATENCY VERSION
Optimized for RTX 4090 to achieve RTF < 0.3 (sub-second latency)

Key Optimizations:
- torch.compile enabled for 20-40% speedup
- Minimal inference parameters for speed
- Simplified text processing
- Multiple warmup runs
- Optimized for short conversational utterances
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

app = FastAPI(title="ChatTTS API Server - Ultra Low Latency", version="2.0.0")

# Global variables
chat = None
speaker_embeddings_cache = {}

# Voice seeds for consistent voices
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
    voice: str = Field(default="female_1", description="Voice preset")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed")
    temperature: float = Field(default=0.3, ge=0.1, le=1.0, description="Lower = faster/stable")
    top_p: float = Field(default=0.7, ge=0.5, le=1.0, description="Top-p sampling")
    top_k: int = Field(default=20, ge=10, le=30, description="Top-k sampling")
    response_format: str = Field(default="wav", description="Audio format: wav or mp3")
    use_refine: bool = Field(default=False, description="Use text refinement (slower but more natural)")


def load_chattts_model():
    """Load and optimize ChatTTS model for ultra-low latency"""
    global chat
    
    try:
        import ChatTTS
        
        logger.info("=" * 60)
        logger.info("Initializing ChatTTS with ULTRA LOW LATENCY settings")
        logger.info("=" * 60)
        
        chat = ChatTTS.Chat()
        
        # CRITICAL: Enable torch.compile for 20-40% speedup
        logger.info("Loading with compile=True for maximum performance...")
        load_start = time.time()
        load_success = chat.load(compile=True)
        
        if not load_success:
            raise Exception("Model loading returned False")
        
        load_time = time.time() - load_start
        logger.info(f"✅ Models loaded in {load_time:.2f}s")
        
        # GPU info
        if torch.cuda.is_available():
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA Memory: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
        
        # Multiple warmup runs for optimal performance
        logger.info("Running multiple warmup iterations...")
        
        warmup_texts = [
            "Hello.",
            "Testing the system.",
            "This is a warmup run."
        ]
        
        for i, warmup_text in enumerate(warmup_texts):
            warmup_start = time.time()
            torch.manual_seed(42)
            rand_spk = chat.sample_random_speaker()
            
            # Minimal parameters for speed
            params_infer = ChatTTS.Chat.InferCodeParams(
                spk_emb=rand_spk,
                temperature=0.3,
                top_P=0.7,
                top_K=20,
            )
            
            warmup_wavs = chat.infer([warmup_text], params_infer_code=params_infer)
            warmup_time = time.time() - warmup_start
            
            if warmup_wavs and len(warmup_wavs) > 0:
                audio_duration = len(warmup_wavs[0]) / 24000
                rtf = warmup_time / audio_duration if audio_duration > 0 else 0
                logger.info(f"  Warmup {i+1}: {warmup_time:.3f}s, RTF: {rtf:.3f}")
            else:
                logger.warning(f"  Warmup {i+1}: No audio generated")
        
        # Pre-cache all speaker embeddings
        logger.info("Caching speaker embeddings...")
        for voice_name, seed in VOICE_SEEDS.items():
            torch.manual_seed(seed)
            speaker_embeddings_cache[voice_name] = chat.sample_random_speaker()
            logger.info(f"  ✅ {voice_name} (seed: {seed})")
        
        logger.info("=" * 60)
        logger.info("🚀 ChatTTS READY - Ultra Low Latency Mode")
        logger.info("   Target: RTF < 0.3, Latency < 1 second")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load ChatTTS: {str(e)}", exc_info=True)
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
        "mode": "ultra_low_latency",
        "compile": True,
        "cuda_available": torch.cuda.is_available(),
        "available_voices": list(VOICE_SEEDS.keys()),
        "target_rtf": "<0.3"
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
    Generate speech from text using ChatTTS - OPTIMIZED FOR SPEED
    
    Ultra-low latency optimizations:
    - Cached speaker embeddings (no regeneration)
    - Minimal inference parameters
    - Optional text refinement (disabled by default)
    - Optimized for short utterances
    """
    if chat is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        start_time = time.time()
        
        # Get cached speaker embedding (FAST)
        if request.voice in speaker_embeddings_cache:
            spk_emb = speaker_embeddings_cache[request.voice]
        else:
            voice_seed = VOICE_SEEDS.get(request.voice, 34)
            torch.manual_seed(voice_seed)
            spk_emb = chat.sample_random_speaker()
        
        # Minimal inference parameters for SPEED
        import ChatTTS
        params_infer = ChatTTS.Chat.InferCodeParams(
            spk_emb=spk_emb,
            temperature=request.temperature,
            top_P=request.top_p,
            top_K=request.top_k,
        )
        
        inference_start = time.time()
        
        # Generate audio (with optional text refinement)
        if request.use_refine:
            # Use text refinement for more natural speech (slower)
            params_refine = ChatTTS.Chat.RefineTextParams(
                prompt='[oral_2][laugh_0][break_4]',
            )
            wavs = chat.infer(
                [request.text],
                params_infer_code=params_infer,
                params_refine_text=params_refine,
            )
        else:
            # Fast mode - no text refinement
            wavs = chat.infer(
                [request.text],
                params_infer_code=params_infer,
            )
        
        inference_time = time.time() - inference_start
        
        # Process audio
        if wavs is None or len(wavs) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        audio_data = wavs[0]
        
        # Speed adjustment (if needed)
        if request.speed != 1.0:
            target_length = int(len(audio_data) / request.speed)
            audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)
            audio_tensor = torch.nn.functional.interpolate(
                audio_tensor.unsqueeze(0),
                size=target_length,
                mode='linear',
                align_corners=False
            ).squeeze(0)
            audio_data = audio_tensor.squeeze(0).numpy()
        
        # Convert to format
        audio_bytes = io.BytesIO()
        
        if request.response_format == "mp3":
            audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)
            torchaudio.save(audio_bytes, audio_tensor, 24000, format="mp3")
            media_type = "audio/mpeg"
        else:
            sf.write(audio_bytes, audio_data, 24000, format='WAV', subtype='PCM_16')
            media_type = "audio/wav"
        
        audio_bytes.seek(0)
        audio_content = audio_bytes.read()
        
        total_time = time.time() - start_time
        audio_duration = len(audio_data) / 24000
        rtf = inference_time / audio_duration if audio_duration > 0 else 0
        
        logger.info(
            f"Generated: '{request.text[:30]}...' | "
            f"Total: {total_time:.3f}s | "
            f"Inference: {inference_time:.3f}s | "
            f"Duration: {audio_duration:.2f}s | "
            f"RTF: {rtf:.3f}"
        )
        
        return Response(
            content=audio_content,
            media_type=media_type,
            headers={
                "X-Processing-Time": f"{total_time:.3f}",
                "X-Audio-Duration": f"{audio_duration:.2f}",
                "X-RTF": f"{rtf:.3f}",
                "X-Inference-Time": f"{inference_time:.3f}",
                "X-Compile-Enabled": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "ChatTTS API Server",
        "version": "2.0.0",
        "mode": "ultra_low_latency",
        "optimizations": [
            "torch.compile enabled",
            "Cached speaker embeddings",
            "Minimal inference parameters",
            "Multiple warmup runs",
            "Optimized for RTX 4090"
        ],
        "endpoints": {
            "health": "/health",
            "voices": "/voices",
            "generate": "/v1/audio/speech (POST)"
        },
        "target_performance": {
            "rtf": "<0.3",
            "latency": "<1 second",
            "gpu": "RTX 4090"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"Starting ChatTTS Ultra Low Latency Server on port {port}...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
