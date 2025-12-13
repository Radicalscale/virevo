import logging
import httpx
import os
from typing import Optional

logger = logging.getLogger(__name__)

class SesameTTSService:
    """
    Sesame TTS Service using custom RunPod endpoint
    
    Connects to hosted Sesame TTS API for speech generation.
    Returns WAV audio (24kHz, 16-bit PCM) compatible with Telnyx.
    """
    
    def __init__(self):
        # Custom RunPod endpoint - read from env or use default
        self.api_endpoint = os.environ.get('SESAME_TTS_API_URL', 'https://6qt2ld98tmdhu2-8000.proxy.runpod.net/generate')
        self.http_client = None
        
    def _get_http_client(self):
        """Get or create HTTP client with connection pooling"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=120.0,  # Increased for model inference time
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self.http_client
    
    async def generate_speech(
        self,
        text: str,
        speaker_id: int = 0,
        output_format: str = "wav"
    ) -> Optional[bytes]:
        """
        Generate speech from text using Sesame TTS
        
        Args:
            text: Text to convert to speech
            speaker_id: Voice ID (0-9) for different voices
            output_format: Output audio format (wav recommended for Telnyx)
        
        Returns:
            Audio data in bytes (WAV format, 24kHz, 16-bit PCM)
        """
        try:
            # Limit text length to avoid excessive processing
            MAX_CHARS = 3000
            if len(text) > MAX_CHARS:
                logger.warning(f"⚠️ Text too long ({len(text)} chars), truncating to {MAX_CHARS}")
                text = text[:MAX_CHARS] + "..."
            
            logger.info(f"🎤 Generating speech with Sesame TTS (RunPod)")
            logger.info(f"   Text: {text[:100]}..." if len(text) > 100 else f"   Text: {text}")
            logger.info(f"   Speaker ID: {speaker_id}")
            
            # Prepare request payload
            payload = {
                "text": text,
                "speaker_id": speaker_id
            }
            
            # Make POST request to custom endpoint
            client = self._get_http_client()
            response = await client.post(
                self.api_endpoint,
                json=payload,
                timeout=120.0  # Increased timeout for model inference
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Sesame API returned status {response.status_code}: {response.text}")
                return None
            
            # Parse response
            response_data = response.json()
            logger.info(f"📥 Sesame API response: {response_data.get('message', 'No message')}")
            
            # Get file information from response
            audio_file = response_data.get("file")
            if not audio_file:
                logger.error("❌ No audio file in Sesame response")
                return None
            
            # Fetch the generated audio file from the server
            # The 'file' field should contain the filename or path
            base_url = os.environ.get('SESAME_TTS_BASE_URL', 'https://6qt2ld98tmdhu2-8000.proxy.runpod.net')
            audio_url = f"{base_url}/{audio_file}"
            logger.info(f"🔗 Fetching audio from: {audio_url}")
            
            audio_response = await client.get(audio_url, timeout=120.0)
            
            if audio_response.status_code != 200:
                logger.error(f"❌ Failed to fetch audio file: {audio_response.status_code}")
                return None
            
            audio_data = audio_response.content
            logger.info(f"✅ Audio fetched successfully ({len(audio_data)} bytes)")
            logger.info(f"📦 Returning WAV audio (24kHz, 16-bit PCM)")
            
            return audio_data
                
        except httpx.TimeoutException:
            logger.error("⏱️ Sesame TTS request timed out")
            return None
        except httpx.RequestError as e:
            logger.error(f"❌ Network error connecting to Sesame: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error generating speech with Sesame: {e}")
            logger.exception(e)
            return None
    
    async def close(self):
        """Close HTTP client connection"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None


# Singleton instance
_sesame_service = None

def get_sesame_tts_service() -> SesameTTSService:
    """Get or create the Sesame TTS service instance"""
    global _sesame_service
    if _sesame_service is None:
        _sesame_service = SesameTTSService()
    return _sesame_service
