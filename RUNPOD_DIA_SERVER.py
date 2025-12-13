"""
Dia TTS FastAPI Server for RunPod
OpenAI-compatible API endpoint for ultra-realistic text-to-speech
Optimized for low latency with direct audio output
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import torch
import torchaudio
import time
import io
import logging
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dia TTS Server", version="1.0")

# Global model variable
model = None
device = None

class TTSRequest(BaseModel):
    model: str = "dia-tts"  # Required by OpenAI format but ignored
    input: str  # Text to synthesize (can include [S1], [S2] tags and (laughs) etc.)
    voice: str = "S1"  # Voice/Speaker: S1, S2, S3, S4, etc.
    response_format: str = "wav"  # wav, mp3, opus, aac, flac
    speed: float = 1.0  # 0.25 to 4.0


def load_model():
    """Load Dia TTS model on startup"""
    global model, device
    
    try:
        logger.info("🚀 Loading Dia TTS model...")
        start_time = time.time()
        
        # Check CUDA availability
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"📍 Using device: {device}")
        
        # Load Dia model from HuggingFace
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        model_name = "nari-labs/dia-1.6b"
        
        logger.info(f"📦 Loading model: {model_name}")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        )
        
        logger.info("✅ Model loaded successfully")
        
        # Set to eval mode
        model.eval()
        
        elapsed = time.time() - start_time
        logger.info(f"⏱️  Model load time: {elapsed:.2f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """Initialize model on server startup"""
    success = load_model()
    if not success:
        logger.error("⚠️  Server started but model failed to load")
    else:
        logger.info("✅ Server ready to handle requests")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if model is not None else "unhealthy",
        "model_loaded": model is not None,
        "device": str(device) if device else "unknown",
        "cuda_available": torch.cuda.is_available()
    }


@app.post("/v1/audio/speech")
async def generate_speech(request: TTSRequest):
    """
    OpenAI-compatible TTS endpoint
    
    Supports:
    - Multi-speaker tags: [S1], [S2], [S3], [S4] in input text
    - Non-verbal sounds: (laughs), (sighs), (gasps), etc.
    - Speed control: 0.25 to 4.0
    - Multiple formats: wav, mp3, opus, aac, flac
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        gen_start = time.time()
        
        # Validate input
        if not request.input or len(request.input.strip()) == 0:
            raise HTTPException(status_code=400, detail="Input text is required")
        
        if request.speed < 0.25 or request.speed > 4.0:
            raise HTTPException(status_code=400, detail="Speed must be between 0.25 and 4.0")
        
        logger.info(f"🎤 Generating TTS: voice={request.voice}, speed={request.speed}, format={request.response_format}")
        logger.info(f"📝 Input text: {request.input[:100]}..." if len(request.input) > 100 else f"📝 Input text: {request.input}")
        
        # If voice tag not in text, prepend it
        text = request.input
        if f"[{request.voice}]" not in text:
            text = f"[{request.voice}] {text}"
        
        # Generate audio using Dia TTS
        with torch.no_grad():
            # Import Dia inference function
            from transformers import pipeline
            
            # Create TTS pipeline
            synthesizer = pipeline(
                "text-to-speech",
                model=model,
                device=device
            )
            
            # Generate speech
            audio_output = synthesizer(text, speaker=request.voice)
            
            # Get audio data and sample rate
            audio_array = audio_output["audio"]
            sample_rate = audio_output["sampling_rate"]
        
        gen_time = int((time.time() - gen_start) * 1000)
        logger.info(f"⏱️  Generation time: {gen_time}ms")
        
        # Apply speed adjustment if needed
        if request.speed != 1.0:
            speed_start = time.time()
            effects = [["speed", str(request.speed)], ["rate", str(sample_rate)]]
            audio_tensor = torch.from_numpy(audio_array).unsqueeze(0)
            audio_tensor, _ = torchaudio.sox_effects.apply_effects_tensor(
                audio_tensor, sample_rate, effects
            )
            audio_array = audio_tensor.squeeze(0).numpy()
            speed_time = int((time.time() - speed_start) * 1000)
            logger.info(f"⏱️  Speed adjustment time: {speed_time}ms")
        
        # Encode audio to requested format
        encode_start = time.time()
        
        # Convert to tensor for encoding
        audio_tensor = torch.from_numpy(audio_array).unsqueeze(0)
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        
        if request.response_format == "wav":
            torchaudio.save(buffer, audio_tensor, sample_rate, format="wav")
            media_type = "audio/wav"
        elif request.response_format == "mp3":
            torchaudio.save(buffer, audio_tensor, sample_rate, format="mp3")
            media_type = "audio/mpeg"
        elif request.response_format == "opus":
            torchaudio.save(buffer, audio_tensor, sample_rate, format="opus")
            media_type = "audio/opus"
        elif request.response_format == "aac":
            torchaudio.save(buffer, audio_tensor, sample_rate, format="aac")
            media_type = "audio/aac"
        elif request.response_format == "flac":
            torchaudio.save(buffer, audio_tensor, sample_rate, format="flac")
            media_type = "audio/flac"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.response_format}")
        
        audio_bytes = buffer.getvalue()
        encode_time = int((time.time() - encode_start) * 1000)
        
        total_time = int((time.time() - gen_start) * 1000)
        
        logger.info(f"✅ TTS Complete: Gen={gen_time}ms, Enc={encode_time}ms, Total={total_time}ms")
        logger.info(f"📦 Audio size: {len(audio_bytes)} bytes ({request.response_format})")
        
        # Return audio with headers
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
        logger.error(f"❌ TTS generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Dia TTS Server",
        "version": "1.0",
        "model": "nari-labs/dia-1.6b",
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
    
    # Run server
    # Use 0.0.0.0 to allow external connections
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
