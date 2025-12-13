import httpx
import logging
import os

logger = logging.getLogger(__name__)

class DiaTTSService:
    def __init__(self, api_url: str = None):
        if api_url is None:
            api_url = os.environ.get('DIA_TTS_API_URL', 'http://203.57.40.158:10230')
        self.api_url = api_url
        # Dia uses OpenAI-compatible endpoint
        self.tts_endpoint = f"{api_url}/v1/audio/speech"
    
    async def generate_audio(
        self,
        text: str,
        voice: str = "S1",
        speed: float = 1.0,
        response_format: str = "wav"
    ) -> bytes:
        """
        Generate audio using Dia TTS API (OpenAI-compatible endpoint)
        
        Args:
            text: Text to synthesize (can include speaker tags like [S1], [S2] and non-verbal sounds like (laughs))
            voice: Voice/Speaker ID (S1, S2, S3, etc.)
            speed: Speech rate (0.25 to 4.0, default 1.0)
            response_format: Audio format (wav, mp3, opus, aac, flac)
        
        Returns:
            bytes: Audio data in requested format
        """
        try:
            import time
            start_time = time.time()
            
            # OpenAI-compatible request format
            request_body = {
                "model": "dia-tts",  # Required by OpenAI format
                "input": text,
                "voice": voice,
                "response_format": response_format,
                "speed": speed
            }
            
            logger.info(f"🎤 Dia TTS: Sending request → voice='{voice}', speed={speed}, format={response_format}, text_length={len(text)}")
            logger.info(f"📤 Request body: {request_body}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.tts_endpoint,
                    json=request_body,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                # Get raw audio bytes directly
                audio_bytes = response.content
                
                if not audio_bytes:
                    raise ValueError("No audio data in response")
                
                # Log generation time and audio info
                elapsed = int((time.time() - start_time) * 1000)
                content_type = response.headers.get("Content-Type", "unknown")
                
                logger.info(f"✅ Dia TTS: Generated {len(audio_bytes)} bytes in {elapsed}ms")
                logger.info(f"📥 Content-Type: {content_type}, Voice: {voice}")
                return audio_bytes
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Dia TTS API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Dia TTS error: {str(e)}")
            raise
    
    async def health_check(self) -> dict:
        """Check if Dia TTS API is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try to hit the base URL or a health endpoint if available
                response = await client.get(f"{self.api_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"❌ Dia TTS health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
