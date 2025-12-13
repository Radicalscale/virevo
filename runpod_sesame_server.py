from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
import torch
import logging
import os
import uuid
import json
from pathlib import Path
from huggingface_hub import login
from generator import load_csm_1b

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("/tmp/sesame_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

hf_token = os.getenv("HF_TOKEN")
if hf_token:
    login(hf_token)

logger.info("Loading CSM-1B with streaming support...")
generator = load_csm_1b("cuda")
logger.info("Model loaded")

@app.get("/")
async def root():
    return {"status": "ok", "streaming": "true_realtime"}

@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")
    try:
        data = await websocket.receive_text()
        request = json.loads(data)
        text = request.get("text", "")
        speaker_id = request.get("speaker_id", 0)
        if not text:
            await websocket.send_json({"error": "No text"})
            return
        logger.info(f"Generating: {text[:50]}...")
        chunks_sent = 0
        for audio_chunk in generator.generate_stream(text=text, speaker=speaker_id, context=[], max_audio_length_ms=30_000):
            chunks_sent += 1
            if torch.is_tensor(audio_chunk):
                audio_chunk = audio_chunk.cpu()
                if audio_chunk.dtype in [torch.float32, torch.float16]:
                    audio_chunk = (audio_chunk * 32767).to(torch.int16)
                audio_bytes = audio_chunk.numpy().tobytes()
            else:
                audio_bytes = audio_chunk.tobytes()
            await websocket.send_bytes(audio_bytes)
            if chunks_sent == 1:
                logger.info("First chunk sent")
        await websocket.send_json({"done": True})
        logger.info(f"Complete: {chunks_sent} chunks")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.get("/health")
async def health():
    return {"status": "healthy", "streaming": "true"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
