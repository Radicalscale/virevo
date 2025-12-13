import httpx
import logging
import os

logger = logging.getLogger(__name__)

class KokoroTTSService:
    def __init__(self, api_url: str = None):
        if api_url is None:
            api_url = os.environ.get('KOKORO_TTS_API_URL', 'http://203.57.40.151:10213')
        self.api_url = api_url
        self.tts_endpoint = f"{api_url}/v1/audio/speech"
    
    async def generate_audio(
        self,
        text: str,
        voice: str = "af_bella",
        speed: float = 1.0,
        response_format: str = "mp3"
    ) -> bytes:
        """Generate audio using Kokoro TTS API"""
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
            
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    self.tts_endpoint,
                    json=request_body,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                audio_bytes = response.content
                elapsed = int((time.time() - start_time) * 1000)
                
                logger.info(f"✅ Kokoro TTS: {len(audio_bytes)} bytes in {elapsed}ms")
                return audio_bytes
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Kokoro TTS API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Kokoro TTS error: {str(e)}")
            raise
    
    async def health_check(self) -> dict:
        """Check if Kokoro TTS API is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"❌ Kokoro TTS health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
