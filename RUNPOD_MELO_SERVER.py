from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from melo.api import TTS
import base64
import io
import torch
import numpy as np
import soundfile as sf

app = FastAPI()

# Initialize MeloTTS models
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Load English models
models = {
    'EN-US': TTS(language='EN', device=device),
    'EN-BR': TTS(language='EN', device=device),
    'EN-INDIA': TTS(language='EN', device=device),
    'EN-AU': TTS(language='EN', device=device),
    'EN-Default': TTS(language='EN_NEWEST', device=device),
}

# Available speaker IDs for each model
speaker_ids = {
    'EN-US': 'EN-US',
    'EN-BR': 'EN-BR',
    'EN-INDIA': 'EN-INDIA',
    'EN-AU': 'EN-AU',
    'EN-Default': 'EN-Default',
}

class TTSRequest(BaseModel):
    text: str
    voice: str = 'EN-US'
    speed: float = 1.2
    clone_wav: str = None

@app.post("/tts")
async def generate_tts(request: TTSRequest):
    try:
        # Validate voice
        if request.voice not in models:
            raise HTTPException(status_code=400, detail=f"Invalid voice. Available: {list(models.keys())}")
        
        # Get the appropriate model
        model = models[request.voice]
        speaker_id = speaker_ids[request.voice]
        
        # Generate audio
        audio_array = model.tts_to_file(
            text=request.text,
            speaker_id=speaker_id,
            speed=request.speed,
            output_path=None,  # Return audio array instead of file
            format='wav',
            quiet=True
        )
        
        # Convert audio array to WAV bytes
        buffer = io.BytesIO()
        sf.write(buffer, audio_array, samplerate=44100, format='WAV')
        buffer.seek(0)
        wav_bytes = buffer.read()
        
        # Encode to base64
        audio_base64 = base64.b64encode(wav_bytes).decode('utf-8')
        
        return JSONResponse(content={"audio": audio_base64})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "device": device, "voices": list(models.keys())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
