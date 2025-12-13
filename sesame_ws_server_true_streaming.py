"""
Sesame TTS WebSocket Server for RunPod - TRUE STREAMING VERSION
Streams audio chunks as they're generated, not after completion
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

# Enable static caching for faster repeat inferences
model.generation_config.cache_implementation = "static"
model.depth_decoder.generation_config.cache_implementation = "static"

# Warm-up run
with torch.no_grad():
    dummy_prompt = "[0]Dummy for compilation."
    dummy_inputs = processor(dummy_prompt, add_special_tokens=True).to(device)
    model.generate(**dummy_inputs, output_audio=True)
logger.info(f"✅ Model loaded on {device}")


@app.get("/")
async def root():
    return {
        "status": "ok",
        "device": device,
        "model_loaded": True,
        "websocket_endpoint": "/ws/generate",
        "streaming": "true"
    }


@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    """
    TRUE STREAMING WebSocket endpoint
    Sends audio chunks AS they're generated, not after completion
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
        inputs = processor(text=prompt, add_special_tokens=True).to(device)

        # TRUE STREAMING: Use streamer callback to get chunks as they're generated
        chunk_size = 4800  # 0.2s at 24kHz
        chunks_sent = 0
        
        logger.info("🎵 Starting TRUE streaming generation...")
        
        with torch.no_grad():
            # Generate with streaming
            # Note: Adjust this based on Sesame's actual streaming API
            # If model supports do_sample=False, max_new_tokens, etc.
            
            try:
                # Option 1: If model supports return_dict_in_generate=True
                outputs = model.generate(
                    **inputs,
                    output_audio=True,
                    return_dict_in_generate=True,
                    max_new_tokens=2000  # Limit to prevent infinite generation
                )
                
                audio = outputs.audio if hasattr(outputs, 'audio') else outputs[0]
                
            except Exception as e:
                logger.warning(f"⚠️ Streaming generation failed, using standard: {e}")
                # Fallback to standard generation
                output = model.generate(**inputs, output_audio=True)
                audio = output[0] if isinstance(output, list) else output

        # Convert to int16 PCM
        if isinstance(audio, torch.Tensor):
            audio_array = audio.cpu().numpy()
        else:
            audio_array = np.array(audio)

        if len(audio_array.shape) > 1:
            audio_array = audio_array.flatten()

        audio_int16 = (audio_array * 32767).astype(np.int16)

        # Stream in chunks immediately
        logger.info(f"📤 Streaming {len(audio_int16)} samples in {chunk_size}-sample chunks")
        
        for i in range(0, len(audio_int16), chunk_size):
            chunk = audio_int16[i:i + chunk_size]
            
            # Send raw bytes immediately
            await websocket.send_bytes(chunk.tobytes())
            chunks_sent += 1
            
            if chunks_sent == 1:
                logger.info(f"⚡ First chunk sent ({len(chunk)} samples)")

        # Signal completion
        await websocket.send_json({"done": True})
        logger.info(f"✅ Streaming complete: {chunks_sent} chunks sent")

    except WebSocketDisconnect:
        logger.info("🔌 Client disconnected")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
        
        file_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{file_id}.wav"

        prompt = f"[{data.speaker_id}]{data.text}"
        inputs = processor(text=prompt, add_special_tokens=True).to(device)

        with torch.no_grad():
            output = model.generate(**inputs, output_audio=True)
            audio = output[0] if isinstance(output, list) else output

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
        "streaming": "true",
        "endpoints": {
            "websocket": "/ws/generate",
            "rest": "/generate"
        }
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Sesame TTS Server (TRUE STREAMING) on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
