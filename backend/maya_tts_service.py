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
        stream: bool = False
    ) -> Optional[bytes]:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert to speech
            voice_ref: Reference voice ID or description
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

            payload = {
                "text": text,
                "description": voice_ref,  # API requires 'description'
                "stream": stream
            }

            logger.info(f"🎤 Sending TTS request to Maya: {url} (stream={stream})")
            
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
        chunk_size: int = 4096
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream speech audio chunks from Maya TTS.
        
        Args:
            text: Text to convert to speech
            voice_ref: Reference voice ID or description
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

            payload = {
                "text": text,
                "description": voice_ref,  # API requires 'description'
                "stream": True
            }

            logger.info(f"🎤 Starting Maya TTS stream: {url}")
            
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
