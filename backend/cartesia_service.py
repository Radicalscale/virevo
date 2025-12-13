"""
Cartesia TTS Service - Ultra-low latency text-to-speech
Uses Cartesia Sonic models for real-time voice generation
"""
import logging
import asyncio
from typing import Optional
from cartesia import Cartesia
import io

logger = logging.getLogger(__name__)

class CartesiaService:
    """Service for generating speech using Cartesia Sonic TTS"""
    
    def __init__(self, api_key: str):
        """
        Initialize Cartesia service
        
        Args:
            api_key: Cartesia API key
        """
        self.api_key = api_key
        self.client = Cartesia(api_key=api_key)
        logger.info("✅ Cartesia service initialized")
    
    async def generate_speech(
        self,
        text: str,
        voice_id: str = "a0e99841-438c-4a64-b679-ae501e7d6091",  # Default: Friendly Reading Man
        model: str = "sonic-2",  # Sonic 2 (stable)
        language: str = "en",
        output_format: dict = None,
        **kwargs
    ) -> bytes:
        """
        Generate speech from text using Cartesia TTS
        
        Args:
            text: Text to synthesize
            voice_id: Cartesia voice ID
            model: Model to use (sonic-2, sonic-turbo, sonic)
            language: Language code (en, es, fr, etc.)
            output_format: Audio format configuration
            
        Returns:
            Audio bytes in requested format
        """
        try:
            logger.info(f"🎙️ Cartesia TTS: Generating speech for text: {text[:50]}...")
            
            # Default format: 8kHz PCM μ-law for telephony
            if output_format is None:
                output_format = {
                    "container": "raw",
                    "encoding": "pcm_mulaw",
                    "sample_rate": 8000
                }
            
            # Call Cartesia TTS API - returns generator
            output_generator = self.client.tts.bytes(
                model_id=model,
                transcript=text,
                voice={
                    "mode": "id",
                    "id": voice_id
                },
                language=language,
                output_format=output_format,
            )
            
            # Consume the generator to get actual bytes
            output = b"".join(output_generator)
            
            logger.info(f"✅ Cartesia TTS: Generated {len(output)} bytes")
            return output
            
        except Exception as e:
            logger.error(f"❌ Cartesia TTS error: {e}")
            raise
    
    async def generate_speech_streaming(
        self,
        text: str,
        voice_id: str = "a0e99841-438c-4a64-b679-ae501e7d6091",
        model: str = "sonic-english",
        language: str = "en",
        output_format: dict = None,
    ):
        """
        Generate speech with streaming (WebSocket) for lower latency
        
        Args:
            text: Text to synthesize
            voice_id: Cartesia voice ID
            model: Model to use
            language: Language code
            output_format: Audio format configuration
            
        Yields:
            Audio chunks as they're generated
        """
        try:
            logger.info(f"🎙️ Cartesia Streaming TTS: {text[:50]}...")
            
            # Default format
            if output_format is None:
                output_format = {
                    "container": "raw",
                    "encoding": "pcm_mulaw",
                    "sample_rate": 8000
                }
            
            # Use WebSocket for streaming
            ws = self.client.tts.websocket()
            
            try:
                # Send synthesis request
                for output in ws.send(
                    model_id=model,
                    transcript=text,
                    voice={
                        "mode": "id",
                        "id": voice_id
                    },
                    language=language,
                    output_format=output_format,
                    stream=True
                ):
                    yield output["audio"]
                
                logger.info("✅ Cartesia streaming TTS complete")
                
            finally:
                ws.close()
                
        except Exception as e:
            logger.error(f"❌ Cartesia streaming TTS error: {e}")
            raise
    
    def list_voices(self) -> list:
        """
        Get list of available Cartesia voices
        
        Returns:
            List of voice dictionaries
        """
        try:
            voices = self.client.voices.list()
            return list(voices)
        except Exception as e:
            logger.error(f"❌ Error listing Cartesia voices: {e}")
            return []
    
    def get_voice(self, voice_id: str) -> dict:
        """
        Get details for a specific voice
        
        Args:
            voice_id: Voice ID to look up
            
        Returns:
            Voice details dictionary
        """
        try:
            voice = self.client.voices.get(id=voice_id)
            return voice
        except Exception as e:
            logger.error(f"❌ Error getting Cartesia voice {voice_id}: {e}")
            return {}
