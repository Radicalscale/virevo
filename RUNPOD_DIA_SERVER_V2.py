"""
Dia TTS FastAPI Server for RunPod - CORRECTED VERSION
Properly loads Dia TTS with custom architecture
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import torch
import torchaudio
import time
import io
import logging
import numpy as np

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
    response_format: str = "wav"
    speed: float = 1.0


def load_model():
    """Load Dia TTS model with proper architecture"""
    global model, processor, device
    
    try:
        logger.info("Loading Dia TTS model...")
        start_time = time.time()
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {device}")
        
        # Import transformers
        from transformers import AutoModel, AutoProcessor
        
        model_name = "nari-labs/dia-1.6b"
        
        logger.info(f"Loading model: {model_name}")
        
        # Load with trust_remote_code for custom architectures
        model = AutoModel.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Try to load processor if available
        try:
            processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
            logger.info("Processor loaded successfully")
        except Exception as e:
            logger.warning(f"Processor not available: {e}")
            processor = None
        
        logger.info("Model loaded successfully")
        model.eval()
        
        elapsed = time.time() - start_time
        logger.info(f"Model load time: {elapsed:.2f}s")
        
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
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        gen_start = time.time()
        
        if not request.input or len(request.input.strip()) == 0:
            raise HTTPException(status_code=400, detail="Input text is required")
        
        if request.speed < 0.25 or request.speed > 4.0:
            raise HTTPException(status_code=400, detail="Speed must be between 0.25 and 4.0")
        
        logger.info(f"Generating TTS: voice={request.voice}, speed={request.speed}, format={request.response_format}")
        logger.info(f"Input: {request.input[:100]}..." if len(request.input) > 100 else f"Input: {request.input}")
        
        text = request.input
        if f"[{request.voice}]" not in text:
            text = f"[{request.voice}] {text}"
        
        # Generate audio with Dia TTS
        with torch.no_grad():
            try:
                # Method 1: Try using processor if available
                if processor is not None:
                    inputs = processor(text, return_tensors="pt").to(device)
                    audio_values = model.generate(**inputs)
                    
                    # Extract audio array
                    if isinstance(audio_values, torch.Tensor):
                        audio_array = audio_values.cpu().numpy().squeeze()
                    else:
                        audio_array = audio_values
                    
                    sample_rate = 24000  # Dia default sample rate
                    
                else:
                    # Method 2: Direct model inference
                    # Tokenize input
                    from transformers import AutoTokenizer
                    tokenizer = AutoTokenizer.from_pretrained("nari-labs/dia-1.6b", trust_remote_code=True)
                    inputs = tokenizer(text, return_tensors="pt").to(device)
                    
                    # Generate
                    outputs = model.generate(**inputs, max_length=1000)
                    
                    # Extract audio from outputs
                    if hasattr(outputs, 'audio'):
                        audio_array = outputs.audio.cpu().numpy().squeeze()
                    elif isinstance(outputs, dict) and 'audio' in outputs:
                        audio_array = outputs['audio']
                    else:
                        raise Exception("Unable to extract audio from model output")
                    
                    sample_rate = 24000
                    
            except Exception as e:
                logger.error(f"Generation method failed: {e}")
                raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")
        
        gen_time = int((time.time() - gen_start) * 1000)
        logger.info(f"Generation time: {gen_time}ms")
        
        # Convert to torch tensor
        if isinstance(audio_array, np.ndarray):
            audio_tensor = torch.from_numpy(audio_array).float()
        else:
            audio_tensor = audio_array.float()
        
        # Ensure 1D tensor
        if audio_tensor.dim() > 1:
            audio_tensor = audio_tensor.squeeze()
        
        # Add batch dimension for processing
        if audio_tensor.dim() == 1:
            audio_tensor = audio_tensor.unsqueeze(0)
        
        # Apply speed adjustment
        if request.speed != 1.0:
            speed_start = time.time()
            effects = [["speed", str(request.speed)], ["rate", str(sample_rate)]]
            audio_tensor, _ = torchaudio.sox_effects.apply_effects_tensor(
                audio_tensor, sample_rate, effects
            )
            speed_time = int((time.time() - speed_start) * 1000)
            logger.info(f"Speed adjustment: {speed_time}ms")
        
        # Encode to requested format
        encode_start = time.time()
        buffer = io.BytesIO()
        
        format_map = {
            "wav": ("wav", "audio/wav"),
            "mp3": ("mp3", "audio/mpeg"),
            "opus": ("opus", "audio/opus"),
            "aac": ("aac", "audio/aac"),
            "flac": ("flac", "audio/flac")
        }
        
        if request.response_format not in format_map:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.response_format}")
        
        fmt, media_type = format_map[request.response_format]
        torchaudio.save(buffer, audio_tensor, sample_rate, format=fmt)
        
        audio_bytes = buffer.getvalue()
        encode_time = int((time.time() - encode_start) * 1000)
        total_time = int((time.time() - gen_start) * 1000)
        
        logger.info(f"Complete: Gen={gen_time}ms, Enc={encode_time}ms, Total={total_time}ms")
        logger.info(f"Audio size: {len(audio_bytes)} bytes")
        
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
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
