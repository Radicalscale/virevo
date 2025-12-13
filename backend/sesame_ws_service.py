"""
Sesame TTS WebSocket Service
Real-time audio streaming for low-latency voice synthesis
"""
import asyncio
import logging
import websockets
import json
import base64
import os
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

class SesameWebSocketService:
    """
    WebSocket client for streaming Sesame TTS
    Similar to ElevenLabs WebSocket for real-time audio
    """
    
    def __init__(self):
        # Read WebSocket URL from environment variable
        self.ws_url = os.environ.get('SESAME_WS_URL', 'wss://6qt2ld98tmdhu2-8000.proxy.runpod.net/ws/generate')
        if 'SESAME_WS_URL' not in os.environ:
            logger.warning("⚠️ SESAME_WS_URL not set in environment, using default RunPod endpoint")
        
    async def stream_tts(
        self,
        text: str,
        speaker_id: int = 0
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS audio chunks in real-time
        
        Args:
            text: Text to convert to speech
            speaker_id: Voice ID (0-9)
            
        Yields:
            Audio chunks as bytes (PCM 24kHz 16-bit mono)
        """
        try:
            logger.info(f"🔗 Connecting to Sesame WebSocket: {self.ws_url}")
            logger.info(f"📝 Text: {text[:100]}...")
            logger.info(f"🎤 Speaker ID: {speaker_id}")
            
            async with websockets.connect(
                self.ws_url,
                ping_interval=60,  # Increase ping interval to 60s
                ping_timeout=60     # Increase ping timeout to 60s
            ) as websocket:
                
                # Send generation request
                request = {
                    "text": text,
                    "speaker_id": speaker_id
                }
                await websocket.send(json.dumps(request))
                logger.info("✅ Request sent, streaming audio chunks...")
                
                chunk_count = 0
                total_bytes = 0
                
                # Receive and yield audio chunks
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Raw audio chunk
                        chunk_count += 1
                        total_bytes += len(message)
                        
                        if chunk_count == 1:
                            logger.info(f"🎵 First chunk received ({len(message)} bytes)")
                        
                        yield message
                        
                    elif isinstance(message, str):
                        # JSON control message
                        try:
                            data = json.loads(message)
                            
                            if data.get("done"):
                                logger.info(f"✅ Streaming complete: {chunk_count} chunks, {total_bytes} bytes")
                                break
                            
                            if data.get("error"):
                                logger.error(f"❌ Server error: {data['error']}")
                                break
                                
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️ Invalid JSON message: {message}")
                
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"❌ WebSocket error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            logger.exception(e)
            raise


# Singleton instance
_sesame_ws_service = None

def get_sesame_ws_service() -> SesameWebSocketService:
    """Get or create the Sesame WebSocket service instance"""
    global _sesame_ws_service
    if _sesame_ws_service is None:
        _sesame_ws_service = SesameWebSocketService()
    return _sesame_ws_service


async def stream_sesame_tts(text: str, speaker_id: int = 0) -> AsyncGenerator[bytes, None]:
    """
    Convenience function to stream Sesame TTS
    
    Args:
        text: Text to synthesize
        speaker_id: Voice ID (0-9)
        
    Yields:
        Audio chunks
    """
    service = get_sesame_ws_service()
    async for chunk in service.stream_tts(text, speaker_id):
        yield chunk
