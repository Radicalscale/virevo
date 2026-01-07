import os
import logging
import httpx
import json
import base64
from typing import Optional, Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)

class MayaTTSService:
    """
    Service for interacting with Maya TTS model hosted on RunPod.
    Supports both standard generation and streaming.
    
    Maya TTS Features:
    - Natural language voice descriptions
    - 20+ emotion tags (<laugh>, <sarcastic>, etc.)
    - Voice cloning via reference audio (speaker_wav)
    - Temperature control for consistency (0.3-0.7)
    - Seed for reproducibility
    """
    
    def __init__(self, api_url: str = None, api_key: str = None):
        """
        Initialize the Maya TTS service.
        
        Args:
            api_url: Base URL for the Maya API (e.g., "https://<RUNPOD_ID>-8000.proxy.runpod.net")
            api_key: Optional API key if the endpoint is protected
        """
        self.api_url = api_url or os.environ.get("MAYA_TTS_API_URL")
        self.api_key = api_key or os.environ.get("MAYA_TTS_API_KEY")
        
        if not self.api_url:
            logger.warning("MAYA_TTS_API_URL not set. Maya TTS service will not function.")
            
        # Clean up URL trailing slash
        if self.api_url and self.api_url.endswith("/"):
            self.api_url = self.api_url[:-1]
            
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )

    async def generate_speech(
        self, 
        text: str, 
        voice_ref: str = "default",
        temperature: float = 0.35,
        seed: int = 0,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
        max_tokens: int = 2000,
        speaker_wav: bytes = None,
        output_format: str = "wav",
        stream: bool = False
    ) -> Optional[bytes]:
        """
        Generate speech from text with full parameter control.
        
        Args:
            text: Text to convert to speech (can include emotion tags like <laugh>)
            voice_ref: Natural language voice description (e.g., "Female, mid-30s, American accent")
            temperature: Controls randomness (0.3-0.7). Lower = more consistent. Default 0.35
            seed: Random seed for reproducibility. 0 = random, specific int = reproducible
            top_p: Nucleus sampling diversity (0.0-1.0). Default 0.9
            repetition_penalty: Prevents audio loops/artifacts. Default 1.1
            max_tokens: Maximum acoustic tokens to generate. Default 2000
            speaker_wav: Optional reference audio bytes for voice cloning (5-30 sec WAV)
            output_format: Output format - "wav", "mp3", or "pcm"
            stream: Whether to stream the response (not used for single byte return)
            
        Returns:
            Audio bytes (WAV/MP3) or None on failure
        """
        if not self.api_url:
            logger.error("Cannot generate speech: MAYA_TTS_API_URL not configured")
            return None

        try:
            url = f"{self.api_url}/v1/tts/generate"
            headers = {
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Build payload with all parameters
            payload = {
                "text": text,
                "description": voice_ref,
                "temperature": temperature,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
                "max_tokens": max_tokens,
                "stream": stream,
                "output_format": output_format
            }
            
            # Add seed only if non-zero (0 means random)
            if seed != 0:
                payload["seed"] = seed
            
            # Add speaker_wav for voice cloning (base64 encoded)
            if speaker_wav:
                payload["speaker_wav"] = base64.b64encode(speaker_wav).decode('utf-8')
                logger.info(f"🎭 Using voice cloning with {len(speaker_wav)} byte reference audio")

            logger.info(f"🎤 Maya TTS request: temp={temperature}, seed={seed}, format={output_format}")
            logger.info(f"📝 Voice description: {voice_ref[:80]}...")
            
            response = await self.http_client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Maya TTS generation successful ({len(response.content)} bytes)")
                return response.content
            else:
                logger.error(f"❌ Maya TTS failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Error calling Maya TTS: {e}")
            return None

    async def stream_speech(
        self, 
        text: str, 
        voice_ref: str = "default",
        temperature: float = 0.35,
        seed: int = 0,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
        max_tokens: int = 2000,
        speaker_wav: bytes = None,
        chunk_size: int = 4096
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream speech audio chunks from Maya TTS with full parameter control.
        
        Args:
            text: Text to convert to speech (can include emotion tags)
            voice_ref: Natural language voice description
            temperature: Controls randomness (0.3-0.7). Lower = more consistent
            seed: Random seed for reproducibility. 0 = random
            top_p: Nucleus sampling diversity (0.0-1.0)
            repetition_penalty: Prevents audio loops/artifacts
            max_tokens: Maximum acoustic tokens to generate
            speaker_wav: Optional reference audio bytes for voice cloning
            chunk_size: Size of chunks to yield
            
        Yields:
            Audio bytes chunks
        """
        if not self.api_url:
            logger.error("Cannot stream speech: MAYA_TTS_API_URL not configured")
            return

        try:
            url = f"{self.api_url}/v1/tts/generate"
            headers = {
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Build payload with all parameters
            payload = {
                "text": text,
                "description": voice_ref,
                "temperature": temperature,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            # Add seed only if non-zero
            if seed != 0:
                payload["seed"] = seed
            
            # Add speaker_wav for voice cloning
            if speaker_wav:
                payload["speaker_wav"] = base64.b64encode(speaker_wav).decode('utf-8')
                logger.info(f"🎭 Streaming with voice cloning ({len(speaker_wav)} byte reference)")

            logger.info(f"🎤 Maya TTS stream: temp={temperature}, seed={seed}")
            
            async with self.http_client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code == 200:
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        if chunk:
                            yield chunk
                    logger.info("✅ Maya TTS stream completed")
                else:
                    error_text = await response.aread()
                    logger.error(f"❌ Maya TTS stream failed: {response.status_code} - {error_text}")

        except Exception as e:
            logger.error(f"❌ Error streaming Maya TTS: {e}")


# Convenience function for creating default service instance
def get_maya_tts_service() -> MayaTTSService:
    """Get a configured Maya TTS service instance."""
    return MayaTTSService()
