import httpx
import base64
import logging
import os

logger = logging.getLogger(__name__)

class MeloTTSService:
    def __init__(self, api_url: str = None):
        if api_url is None:
            api_url = os.environ.get('MELO_TTS_API_URL', 'http://203.57.40.160:10162')
        self.api_url = api_url
        self.tts_endpoint = f"{api_url}/tts"
    
    async def generate_audio(
        self,
        text: str,
        voice: str = "EN-US",
        speed: float = 1.2,
        clone_wav: str = None
    ) -> bytes:
        """
        Generate audio using MeloTTS API
        
        Args:
            text: Text to synthesize
            voice: Voice ID (EN-US, EN-BR, EN-INDIA, EN-AU, EN-Default)
            speed: Speech rate (0.5 to 2.0)
            clone_wav: Optional path to WAV file for voice cloning
        
        Returns:
            bytes: WAV audio data
        """
        try:
            import time
            start_time = time.time()
            
            request_body = {
                "text": text,
                "voice": voice,
                "speed": speed
            }
            
            if clone_wav:
                request_body["clone_wav"] = clone_wav
            
            logger.info(f"🎤 MeloTTS: Sending request → voice='{voice}', speed={speed}, text_length={len(text)}")
            logger.info(f"📤 Request body: {request_body}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.tts_endpoint,
                    json=request_body
                )
                response.raise_for_status()
                
                # Get raw WAV bytes directly (no base64)
                audio_bytes = response.content
                
                if not audio_bytes:
                    raise ValueError("No audio data in response")
                
                # Log generation time and speaker info from headers
                gen_time = response.headers.get("X-Generation-Time", "unknown")
                speaker_id = response.headers.get("X-Speaker-ID", "unknown")
                elapsed = int((time.time() - start_time) * 1000)
                
                logger.info(f"✅ MeloTTS: Generated {len(audio_bytes)} bytes in {gen_time}ms (total: {elapsed}ms)")
                logger.info(f"📥 RunPod used speaker_id: {speaker_id}")
                return audio_bytes
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ MeloTTS API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ MeloTTS error: {str(e)}")
            raise
    
    async def health_check(self) -> dict:
        """Check if MeloTTS API is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"❌ MeloTTS health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
