# Kokoro TTS Integration Complete

## Overview

Kokoro TTS (hexgrad/Kokoro-82M) has been integrated as a fast, open-source, real-time TTS solution for the voice agent platform. It's designed to replace slower TTS options (Dia, MeloTTS) with sub-500ms latency for telephony use cases.

## Why Kokoro?

- ✅ **Ultra-fast**: <300ms generation time (flat scaling regardless of text length)
- ✅ **Lightweight**: 82M parameters (vs 1.6B for Dia)
- ✅ **Real-time capable**: Designed for telephony and streaming
- ✅ **Open-source**: Apache 2.0 license, free to use
- ✅ **Stable voices**: No random voice switching like MeloTTS/Sesame
- ✅ **Natural sounding**: Better than robotic TTS like Piper, though not as premium as ElevenLabs
- ✅ **Low resource**: Runs efficiently on GPU

## Server Configuration

### RunPod Setup

**Connection Details:**
- **External URL**: `http://203.57.40.151:10213`
- **Internal Port**: `8000`
- **Port Mapping**: `10213:8000` (RunPod TCP forwarding)

**Server Location**: `/workspace/kokoro-tts/`

### Kokoro Version

- **Package**: `kokoro-tts` v2.3.0 (shows as v0.9.4 in metadata but is actually 2.3.0)
- **Model**: `hexgrad/Kokoro-82M`
- **API Class**: `KPipeline` (from kokoro package)

## Available Voices

Kokoro provides 10 voices across different accents and genders:

### Female Voices
- `af_bella` - American Female - Bella (Default)
- `af_nicole` - American Female - Nicole
- `af_sarah` - American Female - Sarah
- `af_sky` - American Female - Sky
- `bf_emma` - British Female - Emma
- `bf_isabella` - British Female - Isabella

### Male Voices
- `am_adam` - American Male - Adam
- `am_michael` - American Male - Michael
- `bm_george` - British Male - George
- `bm_lewis` - British Male - Lewis

## API Specification

### OpenAI-Compatible Endpoint

**POST** `/v1/audio/speech`

**Request Body:**
```json
{
  "model": "kokoro",
  "input": "Text to synthesize",
  "voice": "af_bella",
  "response_format": "mp3",
  "speed": 1.0
}
```

**Parameters:**
- `model` (string): Always "kokoro"
- `input` (string): Text to convert to speech (required)
- `voice` (string): Voice ID from available voices (default: "af_bella")
- `response_format` (string): "mp3" or "wav" (default: "mp3")
- `speed` (float): Speech rate 0.5-2.0 (default: 1.0)

**Response:**
- Binary audio data (MP3 or WAV)
- Headers include timing information:
  - `X-Generation-Time`: Audio generation time in ms
  - `X-Encode-Time`: Audio encoding time in ms
  - `X-Total-Time`: Total processing time in ms
  - `X-Voice`: Voice used

### Health Check

**GET** `/health`

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda"
}
```

### Server Info

**GET** `/`

**Response:**
```json
{
  "name": "Kokoro TTS Server",
  "version": "2.0",
  "model": "hexgrad/Kokoro-82M",
  "voices": ["af_bella", "af_nicole", ...]
}
```

## Backend Integration

### File: `/app/backend/kokoro_tts_service.py`

**Status**: Needs to be created (not yet implemented in main app)

**Planned Implementation:**
```python
import httpx
import logging

logger = logging.getLogger(__name__)

class KokoroTTSService:
    def __init__(self, api_url: str = "http://203.57.40.151:10213"):
        self.api_url = api_url
        self.tts_endpoint = f"{api_url}/v1/audio/speech"
    
    async def generate_audio(
        self,
        text: str,
        voice: str = "af_bella",
        speed: float = 1.0,
        response_format: str = "mp3"
    ) -> bytes:
        """Generate audio using Kokoro TTS"""
        try:
            import time
            start_time = time.time()
            
            request_body = {
                "model": "kokoro",
                "input": text,
                "voice": voice,
                "response_format": response_format,
                "speed": speed
            }
            
            logger.info(f"🎤 Kokoro TTS: voice={voice}, speed={speed}, text_len={len(text)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.tts_endpoint,
                    json=request_body,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                audio_bytes = response.content
                elapsed = int((time.time() - start_time) * 1000)
                
                logger.info(f"✅ Kokoro: {len(audio_bytes)} bytes in {elapsed}ms")
                return audio_bytes
        
        except Exception as e:
            logger.error(f"❌ Kokoro TTS error: {e}")
            raise
```

### File: `/app/backend/models.py`

**Status**: Needs to be added

**Add to models.py:**
```python
class KokoroSettings(BaseModel):
    voice: str = "af_bella"  # Voice ID
    speed: float = 1.0  # Speech rate (0.5 to 2.0)
    response_format: str = "mp3"  # Audio format (mp3, wav)

class AgentSettings(BaseModel):
    # ... existing fields ...
    tts_provider: str = "cartesia"  # "elevenlabs", "cartesia", "hume", "kokoro"
    
    # ... existing provider settings ...
    kokoro_settings: Optional[KokoroSettings] = Field(default_factory=KokoroSettings)
```

### File: `/app/backend/server.py`

**Status**: Needs integration in `generate_tts_audio` function

**Add to generate_tts_audio:**
```python
elif tts_provider == "kokoro":
    try:
        from kokoro_tts_service import KokoroTTSService
        
        kokoro_settings = settings.get("kokoro_settings", {})
        voice = kokoro_settings.get("voice", "af_bella")
        speed = kokoro_settings.get("speed", 1.0)
        response_format = kokoro_settings.get("response_format", "mp3")
        
        logger.info(f"🎤 Generating Kokoro TTS (Voice: {voice}, Speed: {speed})")
        
        kokoro_service = KokoroTTSService()
        audio_bytes = await kokoro_service.generate_audio(
            text=text,
            voice=voice,
            speed=speed,
            response_format=response_format
        )
        
        logger.info(f"✅ Kokoro TTS generated {len(audio_bytes)} bytes")
        return audio_bytes
        
    except Exception as e:
        logger.error(f"❌ Kokoro TTS error: {e}")
        logger.warning("⚠️ Falling back to Cartesia")
        return await generate_audio_cartesia(text, settings)
```

## Frontend Integration

### File: `/app/frontend/src/components/AgentForm.jsx`

**Status**: Needs to be added to UI

**Add to TTS Provider Dropdown:**
```jsx
<SelectItem value="kokoro">Kokoro TTS - Fast & Free</SelectItem>
```

**Add Kokoro Settings Section:**
```jsx
{formData.settings?.tts_provider === 'kokoro' && (
  <div className="space-y-4 border-t border-gray-700 pt-4">
    <div className="bg-green-900/20 border border-green-700 rounded-lg p-3 mb-4">
      <p className="text-green-400 text-sm font-semibold">🎤 Kokoro TTS - Fast & Free</p>
      <p className="text-green-300 text-xs mt-1">Ultra-fast 82M parameter open-source model</p>
    </div>
    
    <Label className="text-gray-300 font-semibold block">Kokoro TTS Settings</Label>
    
    <div>
      <Label className="text-gray-400 text-sm">Voice</Label>
      <Select
        value={formData.settings?.kokoro_settings?.voice || 'af_bella'}
        onValueChange={(value) => setFormData({
          ...formData,
          settings: {
            ...formData.settings,
            kokoro_settings: {
              ...formData.settings?.kokoro_settings,
              voice: value
            }
          }
        })}
      >
        <SelectTrigger className="bg-gray-900 border-gray-700 text-white mt-1">
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="bg-gray-900 border-gray-700">
          <SelectItem value="af_bella">Bella - American Female</SelectItem>
          <SelectItem value="af_nicole">Nicole - American Female</SelectItem>
          <SelectItem value="af_sarah">Sarah - American Female</SelectItem>
          <SelectItem value="af_sky">Sky - American Female</SelectItem>
          <SelectItem value="bf_emma">Emma - British Female</SelectItem>
          <SelectItem value="bf_isabella">Isabella - British Female</SelectItem>
          <SelectItem value="am_adam">Adam - American Male</SelectItem>
          <SelectItem value="am_michael">Michael - American Male</SelectItem>
          <SelectItem value="bm_george">George - British Male</SelectItem>
          <SelectItem value="bm_lewis">Lewis - British Male</SelectItem>
        </SelectContent>
      </Select>
    </div>

    <div>
      <Label className="text-gray-400 text-sm">Speed: {formData.settings?.kokoro_settings?.speed || 1.0}x</Label>
      <input
        type="range"
        min="0.5"
        max="2.0"
        step="0.1"
        value={formData.settings?.kokoro_settings?.speed || 1.0}
        onChange={(e) => setFormData({
          ...formData,
          settings: {
            ...formData.settings,
            kokoro_settings: {
              ...formData.settings?.kokoro_settings,
              speed: parseFloat(e.target.value)
            }
          }
        })}
        className="w-full mt-1"
      />
    </div>
  </div>
)}
```

## RunPod Server Files

### Location: `/workspace/kokoro-tts/`

**Files:**
1. `server.py` - FastAPI server using KPipeline
2. `test_kokoro.py` - Latency testing script
3. `check_kokoro_v2.py` - Package version checker

### Server.py Key Implementation Details

**Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `kokoro-tts==2.3.0` - TTS model
- `soundfile` - Audio I/O
- `numpy` - Array processing
- `torch` - PyTorch for GPU acceleration

**Model Loading:**
```python
from kokoro import KPipeline
pipeline = KPipeline(lang_code='a')  # 'a' for American English
```

**Generation:**
```python
result = pipeline(text, voice=voice, speed=speed)
audio_data = result.audio if hasattr(result, 'audio') else result
```

**Audio Format Conversion:**
- Native: 24kHz WAV
- Telephony: 8kHz MP3 (using ffmpeg)

## Testing

### Quick Test Script: `/workspace/kokoro-tts/test_kokoro.py`

Tests:
1. Health check
2. Basic TTS generation
3. Latency scaling (short/medium/long text)

**Run test:**
```bash
cd /workspace/kokoro-tts
python test_kokoro.py
```

**Expected Results:**
- Health: Server responds with model_loaded=true
- Latency: <500ms per generation (target for real-time)
- Audio: MP3/WAV files saved to `/tmp/`

### Manual Test from Main App

```bash
curl -X POST http://203.57.40.151:10213/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model": "kokoro", "input": "Hello world", "voice": "af_bella", "speed": 1.0}' \
  --output test.mp3
```

## Performance Expectations

### Latency Targets

| Text Length | Target Latency | Kokoro Expected |
|-------------|----------------|-----------------|
| Short (10 words) | <300ms | ~150-250ms |
| Medium (30 words) | <500ms | ~200-400ms |
| Long (100 words) | <800ms | ~300-600ms |

**Key Advantage**: Kokoro maintains flat latency regardless of text length (unlike Dia which scales linearly).

### Comparison with Other TTS

| Provider | Latency | Quality | Cost | Voice Consistency |
|----------|---------|---------|------|-------------------|
| **Kokoro** | 150-400ms | Good | Free | ✅ Stable |
| Cartesia Sonic | 40-90ms | Excellent | Paid | ✅ Stable |
| ElevenLabs | 200-500ms | Excellent | Paid | ✅ Stable |
| Dia TTS | 5-10s | Excellent | Free | ⚠️ Slow |
| MeloTTS | 1-3s | Good | Free | ❌ Unstable |
| Piper | 100-300ms | Fair/Robotic | Free | ✅ Stable |

## Deployment Checklist

- [x] Kokoro server running on RunPod
- [x] Port 10213 accessible externally
- [x] Health check endpoint working
- [x] TTS generation tested
- [ ] Backend service (`kokoro_tts_service.py`) created
- [ ] Models updated with `KokoroSettings`
- [ ] Server.py integrated with Kokoro branch
- [ ] Frontend UI added for Kokoro selection
- [ ] End-to-end testing with live calls

## Troubleshooting

### Server Won't Start

**Check:**
```bash
# Check if port in use
lsof -i :8000

# Check model loading
tail -f /var/log/kokoro.log
```

### Model Load Failed

**Solution:**
```bash
pip uninstall kokoro kokoro-tts -y
pip install git+https://github.com/hexgrad/kokoro.git
```

### Slow Generation

**Check:**
- GPU available: `nvidia-smi`
- CUDA working: `python -c "import torch; print(torch.cuda.is_available())"`
- Model on GPU: Check server logs for "Device: cuda"

### Audio Quality Issues

**Try:**
- Different voice: Some voices sound more natural
- Adjust speed: 0.9-1.1 range usually best
- Check format: WAV for highest quality, MP3 for smaller size

## Next Steps

1. **Complete Backend Integration**
   - Create `kokoro_tts_service.py`
   - Update `models.py`
   - Add Kokoro branch to `server.py`

2. **Add Frontend UI**
   - Add Kokoro to TTS provider dropdown
   - Create Kokoro settings panel
   - Update help text

3. **Testing**
   - Latency benchmarks
   - Voice quality comparison
   - Live call testing
   - Load testing (multiple concurrent requests)

4. **Optimization** (if needed)
   - Enable ONNX runtime for 2x speed
   - Implement audio caching
   - Add streaming support

## References

- **Kokoro GitHub**: https://github.com/hexgrad/kokoro
- **Kokoro HuggingFace**: https://huggingface.co/hexgrad/Kokoro-82M
- **RunPod Server**: http://203.57.40.151:10213
- **Test Script**: `/app/test_kokoro.py`
- **Documentation**: This file

## Summary

Kokoro TTS provides a fast, free, stable alternative to commercial TTS for real-time telephony. With <500ms latency and consistent voice quality, it's suitable for production voice agent calls where cost is a concern but natural-sounding voice is still important.

**Status**: RunPod server deployed and functional. Backend/Frontend integration pending.
