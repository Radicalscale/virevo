"""
ElevenLabs WebSocket TTS Service
Handles real-time streaming text-to-speech via WebSocket API
"""
import asyncio
import websockets
import json
import base64
import logging
from typing import AsyncGenerator, Optional, Dict, Any

logger = logging.getLogger(__name__)

class ElevenLabsWebSocketService:
    """
    Manages WebSocket connection to ElevenLabs for streaming TTS
    
    Voice Settings Guide:
    - stability (0.0-1.0): Lower = more expressive/variable, Higher = more consistent/monotone
      * 0.3-0.5 = Natural, expressive delivery (recommended for sales)
      * 0.7-1.0 = Flat, robotic delivery (avoid for conversational use)
    
    - similarity_boost (0.0-1.0): How closely to match the original voice
      * 0.5-0.75 = Good balance
      * 1.0 = Maximum similarity but can sound artificial
    
    - style (0.0-1.0): Exaggeration of voice style (v2 models only)
      * 0.0 = No style exaggeration
      * 0.3-0.5 = Natural enhancement
      * Higher values can cause artifacts
    
    - use_speaker_boost: Enhances clarity and presence
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.voice_id: Optional[str] = None
        self.model_id: str = "eleven_flash_v2_5"  # Default to Flash v2.5
        self.connected = False
        self.bos_sent = False  # Track if Beginning of Stream message was sent
        
    async def connect(
        self,
        voice_id: str,
        model_id: str = "eleven_flash_v2_5",
        output_format: str = "pcm_16000",
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Establish WebSocket connection to ElevenLabs
        
        Args:
            voice_id: ElevenLabs voice ID
            model_id: TTS model to use (eleven_flash_v2_5, eleven_turbo_v2, etc.)
            output_format: Audio output format (pcm_16000, mp3_44100, etc.)
            voice_settings: Optional dict with stability, similarity_boost, style, use_speaker_boost
            
        Returns:
            bool: True if connected successfully
        """
        try:
            self.voice_id = voice_id
            self.model_id = model_id
            self.bos_sent = False
            
            # Store voice settings for BOS message
            self.voice_settings = voice_settings or {
                "stability": 0.4,  # More expressive (lower = more variation)
                "similarity_boost": 0.75,
                "style": 0.2,  # Slight style enhancement
                "use_speaker_boost": True
            }
            
            # Construct WebSocket URL with SSML parsing enabled
            uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}&output_format={output_format}&enable_ssml_parsing=true"
            
            logger.info(f"🔌 Connecting to ElevenLabs WebSocket: voice={voice_id}, model={model_id}")
            logger.info(f"🎙️ Voice settings: stability={self.voice_settings.get('stability')}, similarity={self.voice_settings.get('similarity_boost')}, style={self.voice_settings.get('style')}")
            
            # Connect with API key in header
            self.websocket = await websockets.connect(
                uri,
                extra_headers={"xi-api-key": self.api_key},
                ping_interval=20,  # Keep connection alive
                ping_timeout=10
            )
            
            self.connected = True
            logger.info("✅ Connected to ElevenLabs WebSocket")
            
            # Send BOS (Beginning of Stream) message with voice settings
            await self._send_bos_message()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to ElevenLabs WebSocket: {e}")
            self.connected = False
            return False
    
    async def _send_bos_message(self) -> bool:
        """
        Send Beginning of Stream message with voice settings
        This MUST be sent before any text to configure the voice
        """
        if not self.websocket or self.bos_sent:
            return False
        
        try:
            bos_message = {
                "text": " ",  # Required, can be empty or space
                "voice_settings": {
                    "stability": self.voice_settings.get("stability", 0.4),
                    "similarity_boost": self.voice_settings.get("similarity_boost", 0.75),
                    "style": self.voice_settings.get("style", 0.2),
                    "use_speaker_boost": self.voice_settings.get("use_speaker_boost", True)
                },
                "generation_config": {
                    "chunk_length_schedule": [120, 160, 250, 290]  # Optimize for streaming
                },
                "xi_api_key": self.api_key  # Can also be sent here
            }
            
            await self.websocket.send(json.dumps(bos_message))
            self.bos_sent = True
            logger.info(f"📤 Sent BOS message with voice settings")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending BOS message: {e}")
            return False
    
    async def send_text(
        self,
        text: str,
        try_trigger_generation: bool = True,
        flush: bool = False
    ) -> bool:
        """
        Send text chunk to ElevenLabs for synthesis
        
        Args:
            text: Text to synthesize
            try_trigger_generation: Attempt to trigger audio generation immediately
            flush: Flush any buffered text and finalize generation
            
        Returns:
            bool: True if sent successfully
        """
        if not self.connected or not self.websocket:
            logger.error("❌ WebSocket not connected")
            return False
        
        try:
            message = {
                "text": text,
                "try_trigger_generation": try_trigger_generation
            }
            
            if flush:
                message["flush"] = True
            
            await self.websocket.send(json.dumps(message))
            logger.debug(f"📤 Sent text to ElevenLabs: {text[:50]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending text to ElevenLabs: {e}")
            self.connected = False
            return False
    
    async def receive_audio_chunks(self) -> AsyncGenerator[bytes, None]:
        """
        Receive audio chunks from ElevenLabs WebSocket
        
        Yields:
            bytes: Raw audio data (PCM format)
        """
        if not self.connected or not self.websocket:
            logger.error("❌ WebSocket not connected")
            return
        
        try:
            # ElevenLabs streams audio in chunks, then waits for more input
            # After flush, we get audio chunks, then silence (no isFinal signal)
            # Use a short timeout (0.5s) to detect when audio stream ends
            while True:
                try:
                    # Short timeout - if no message in 0.5s after flush, assume done
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=0.5
                    )
                    
                    data = json.loads(message)
                    
                    # Check for audio data
                    if "audio" in data and data["audio"]:
                        # Audio is base64-encoded
                        audio_base64 = data["audio"]
                        audio_bytes = base64.b64decode(audio_base64)
                        
                        logger.debug(f"🎵 Received audio chunk: {len(audio_bytes)} bytes")
                        yield audio_bytes
                    
                    # Check for alignment data (word timestamps)
                    if "alignment" in data:
                        logger.debug(f"📊 Received alignment data")
                    
                    # Check for server messages
                    if "message" in data:
                        logger.info(f"💬 ElevenLabs message: {data['message']}")
                    
                    # Check for errors (including input_timeout_exceeded)
                    if "error" in data:
                        logger.debug(f"📍 ElevenLabs signal: {data['error']}")
                        # Don't mark as disconnected - this is expected end signal
                        break
                    
                    # Check for completion (rarely sent, but handle it)
                    if data.get("isFinal", False) == True:
                        logger.debug("✅ ElevenLabs isFinal=True")
                        break
                
                except asyncio.TimeoutError:
                    # No more audio coming - generation complete for this sentence
                    logger.info("⏱️  [TIMING] ElevenLabs audio stream complete (0.5s timeout reached) - End of Sentence")
                    break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON from ElevenLabs: {e}")
                    continue
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"⚠️  ElevenLabs WebSocket connection closed unexpectedly: {e}")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ Error receiving audio from ElevenLabs: {e}")
            self.connected = False
    
    async def send_end_of_stream(self) -> bool:
        """
        Send end-of-stream message to finalize generation
        
        Returns:
            bool: True if sent successfully
        """
        if not self.connected or not self.websocket:
            return False
        
        try:
            # Send empty text with flush to signal end
            await self.websocket.send(json.dumps({"text": "", "flush": True}))
            logger.info("📤 Sent end-of-stream to ElevenLabs")
            return True
        except Exception as e:
            logger.error(f"❌ Error sending end-of-stream: {e}")
            return False
    
    async def close(self):
        """
        Close the WebSocket connection
        """
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("🔌 Closed ElevenLabs WebSocket connection")
            except Exception as e:
                logger.error(f"❌ Error closing WebSocket: {e}")
        
        self.connected = False
        self.websocket = None
    
    async def stream_text_to_audio(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_flash_v2_5"
    ) -> AsyncGenerator[bytes, None]:
        """
        High-level method: Connect, stream text, and receive audio chunks
        
        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID
            model_id: TTS model to use
            
        Yields:
            bytes: Audio chunks
        """
        try:
            # Connect
            connected = await self.connect(voice_id, model_id)
            if not connected:
                logger.error("❌ Failed to establish connection")
                return
            
            # Send text
            await self.send_text(text, try_trigger_generation=True)
            
            # Send end-of-stream
            await self.send_end_of_stream()
            
            # Receive and yield audio chunks
            async for audio_chunk in self.receive_audio_chunks():
                yield audio_chunk
                
        finally:
            # Always close the connection
            await self.close()
