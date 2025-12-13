import asyncio
import json
import logging
import websockets
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

class AssemblyAIStreamingService:
    """
    AssemblyAI Universal Streaming with Turn Detection
    Handles real-time speech-to-text with natural conversation flow
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ASSEMBLYAI_API_KEY
        self.ws = None
        self.session_id = None
        
    async def _wait_for_begin(self):
        """
        Wait for the initial 'Begin' message from AssemblyAI.
        This must be called before starting to send audio.
        """
        try:
            message = await self.ws.recv()
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "Begin":
                self.session_id = data.get("id")
                logger.info(f"✅ AssemblyAI session began: {self.session_id}")
                return True
            else:
                logger.error(f"❌ Expected 'Begin' message, got: {message_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error waiting for 'Begin' message: {e}")
            return False
    
    async def connect(self, 
                     sample_rate: int = 8000,
                     word_boost: list = None,
                     threshold: float = 0.0,
                     disable_partial_transcripts: bool = False,
                     end_of_turn_confidence_threshold: float = 0.8,
                     min_end_of_turn_silence_when_confident: int = 500,
                     max_turn_silence: int = 2000):
        """
        Connect to AssemblyAI Universal Streaming (v3 API)
        
        Args:
            sample_rate: Audio sample rate (8000 or 16000)
            word_boost: List of words to boost recognition
            threshold: Turn detection threshold (0.0-1.0, 0=most responsive)
            disable_partial_transcripts: Disable real-time partial results
            end_of_turn_confidence_threshold: Confidence level for turn detection (0.0-1.0)
            min_end_of_turn_silence_when_confident: Min silence (ms) when confident about turn end
            max_turn_silence: Max silence (ms) before forcing turn end
        """
        # Build URL with query parameters (v3 API format)
        # NOTE: We resample to 16kHz linear PCM before sending, as that's what AssemblyAI expects
        from urllib.parse import urlencode
        
        params = {
            "sample_rate": 16000,  # Resampled from 8kHz to 16kHz in backend
            "encoding": "pcm_s16le",  # 16-bit linear PCM (converted from mulaw)
            "format_turns": "true",  # Enable turn detection (v3 API requirement)
            # Smart Endpointing Parameters for optimized turn detection
            "end_of_turn_confidence_threshold": end_of_turn_confidence_threshold,
            "min_end_of_turn_silence_when_confident": min_end_of_turn_silence_when_confident,
            "max_turn_silence": max_turn_silence,
        }
        
        url = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(params)}"
        
        extra_headers = {
            "Authorization": self.api_key
        }
        
        try:
            self.ws = await websockets.connect(url, extra_headers=extra_headers, ping_interval=30, ping_timeout=10)
            logger.info(f"✅ Connected to AssemblyAI Universal Streaming v3")
            logger.info(f"⚙️  Config: 16kHz pcm_s16le (resampled from 8kHz mulaw)")
            logger.info(f"⚙️  Smart Endpointing: confidence={end_of_turn_confidence_threshold}, min_silence={min_end_of_turn_silence_when_confident}ms, max_silence={max_turn_silence}ms")
            
            # Wait for the 'Begin' message before proceeding
            if not await self._wait_for_begin():
                await self.ws.close()
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to AssemblyAI: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to AssemblyAI (v3 expects raw bytes)"""
        if self.ws and not self.ws.closed:
            try:
                # v3 API expects raw binary audio data
                await self.ws.send(audio_data)
            except Exception as e:
                logger.error(f"❌ Error sending audio to AssemblyAI: {e}")
    
    async def receive_messages(self, 
                               on_partial_transcript: Optional[Callable] = None,
                               on_final_transcript: Optional[Callable] = None,
                               on_turn_end: Optional[Callable] = None):
        """
        Receive and process messages from AssemblyAI v3
        
        Args:
            on_partial_transcript: Callback for partial transcripts
            on_final_transcript: Callback for final transcripts  
            on_turn_end: Callback for turn end events (natural conversation breaks)
        """
        try:
            async for message in self.ws:
                data = json.loads(message)
                message_type = data.get("type")  # v3 uses "type"
                
                # V3 API uses "Turn" message type (not PartialTranscript/FinalTranscript)
                if message_type == "Turn":
                    text = data.get("transcript", "")
                    end_of_turn = data.get("end_of_turn", False)
                    turn_is_formatted = data.get("turn_is_formatted", False)
                    
                    if text:
                        # In-progress turn (like a partial transcript)
                        if not end_of_turn:
                            logger.info(f"🔍 AssemblyAI Turn (partial): {text[:50]}...")
                            if on_partial_transcript:
                                await on_partial_transcript(text, data)
                        
                        # End of turn with formatted transcript (like final transcript)
                        elif end_of_turn and turn_is_formatted:
                            logger.info(f"✅ AssemblyAI Turn (final): {text}")
                            if on_final_transcript:
                                await on_final_transcript(text, data)
                            if on_turn_end:
                                await on_turn_end(text, data)
                
                elif message_type == "SessionInformation":
                    # Contains turn detection events
                    audio_duration_seconds = data.get("audio_duration_seconds", 0)
                    logger.info(f"📊 Session info: {audio_duration_seconds}s processed")
                
                elif message_type == "SessionTerminated":
                    logger.info("🛑 AssemblyAI session terminated")
                    break
                
                else:
                    # Log any unexpected message types for debugging
                    logger.info(f"🔍 AssemblyAI message: type={message_type}")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 AssemblyAI connection closed")
        except Exception as e:
            logger.error(f"❌ Error receiving AssemblyAI messages: {e}")
    
    async def terminate(self):
        """Terminate the session"""
        if self.ws and not self.ws.closed:
            try:
                terminate_message = {"terminate_session": True}
                await self.ws.send(json.dumps(terminate_message))
                await self.ws.close()
                logger.info("✅ AssemblyAI session terminated gracefully")
            except Exception as e:
                logger.error(f"❌ Error terminating AssemblyAI session: {e}")
    
    async def close(self):
        """Close the WebSocket connection"""
        await self.terminate()
