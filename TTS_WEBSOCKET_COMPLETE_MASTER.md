# TTS WebSocket System - Complete Master Code Reference

## Overview

This document contains the complete, working code for the ElevenLabs WebSocket TTS streaming system. This system enables ultra-low latency text-to-speech with real-time audio streaming.

**Last Updated:** November 29, 2025
**Status:** WORKING - Tested and verified

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     VOICE AGENT TTS ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [User Speech]                                                          │
│       │                                                                 │
│       ▼                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐           │
│  │   Telnyx     │────▶│   Soniox     │────▶│   LLM        │           │
│  │  WebSocket   │     │    STT       │     │ (Streaming)  │           │
│  │  (Audio In)  │     │              │     │              │           │
│  └──────────────┘     └──────────────┘     └──────────────┘           │
│                                                  │                     │
│                                                  │ Sentences           │
│                                                  ▼                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐           │
│  │   Telnyx     │◀────│  Persistent  │◀────│  ElevenLabs  │           │
│  │  WebSocket   │     │ TTS Session  │     │  WebSocket   │           │
│  │ (Audio Out)  │     │              │     │              │           │
│  └──────────────┘     └──────────────┘     └──────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
/app/backend/
├── elevenlabs_ws_service.py    # ElevenLabs WebSocket client
├── persistent_tts_service.py   # Persistent session management
├── soniox_service.py           # STT (Speech-to-Text) service
├── telnyx_service.py           # Telnyx call control & audio
├── server.py                   # Main server with handlers
└── calling_service.py          # Call flow processing
```

---

## Core Files

### 1. ElevenLabs WebSocket Service

**File:** `/app/backend/elevenlabs_ws_service.py`

This service handles the WebSocket connection to ElevenLabs for streaming TTS.

```python
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
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.voice_id: Optional[str] = None
        self.model_id: str = "eleven_flash_v2_5"  # Default to Flash v2.5
        self.connected = False
        
    async def connect(
        self,
        voice_id: str,
        model_id: str = "eleven_flash_v2_5",
        output_format: str = "pcm_16000"
    ) -> bool:
        """
        Establish WebSocket connection to ElevenLabs
        
        Args:
            voice_id: ElevenLabs voice ID
            model_id: TTS model to use (eleven_flash_v2_5, eleven_turbo_v2, etc.)
            output_format: Audio output format (pcm_16000, mp3_44100, etc.)
            
        Returns:
            bool: True if connected successfully
        """
        try:
            self.voice_id = voice_id
            self.model_id = model_id
            
            # Construct WebSocket URL with SSML parsing enabled
            # CRITICAL: enable_ssml_parsing=true allows SSML tags like <break time="300ms"/>
            uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}&output_format={output_format}&enable_ssml_parsing=true"
            
            logger.info(f"🔌 Connecting to ElevenLabs WebSocket: voice={voice_id}, model={model_id}")
            
            # Connect with API key in header
            self.websocket = await websockets.connect(
                uri,
                extra_headers={"xi-api-key": self.api_key},
                ping_interval=20,  # Keep connection alive
                ping_timeout=10
            )
            
            self.connected = True
            logger.info("✅ Connected to ElevenLabs WebSocket")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to ElevenLabs WebSocket: {e}")
            self.connected = False
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
                    logger.debug("✅ ElevenLabs audio stream complete (timeout)")
                    break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON from ElevenLabs: {e}")
                    continue
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️  ElevenLabs WebSocket connection closed")
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
```

---

### 2. Persistent TTS Service

**File:** `/app/backend/persistent_tts_service.py`

This service maintains persistent WebSocket connections for ultra-low latency TTS.

```python
"""
Persistent TTS Service with WebSocket Streaming
Maintains persistent ElevenLabs WebSocket connections per call for ultra-low latency
Streams audio chunks immediately to eliminate batching delays
"""
import asyncio
import logging
import time
import hashlib
import subprocess
import os
from typing import Optional, Dict, Callable, Any
from elevenlabs_ws_service import ElevenLabsWebSocketService

logger = logging.getLogger(__name__)


class PersistentTTSSession:
    """
    Manages a persistent TTS WebSocket connection for a single call
    Streams audio chunks immediately as they arrive from ElevenLabs
    """
    
    def __init__(
        self,
        call_control_id: str,
        api_key: str,
        voice_id: str,
        model_id: str = "eleven_flash_v2_5",
        telnyx_service=None,
        agent_config: dict = None,
        telnyx_ws=None
    ):
        self.call_control_id = call_control_id
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.telnyx_service = telnyx_service
        self.agent_config = agent_config or {}
        self.telnyx_ws = telnyx_ws  # WebSocket connection to Telnyx for streaming audio
        
        # WebSocket connection
        self.ws_service: Optional[ElevenLabsWebSocketService] = None
        self.connected = False
        
        # Streaming state
        self.is_streaming = False
        self.sentence_counter = 0
        self.context_id = None
        
        # Audio queue for seamless playback
        self.audio_queue = asyncio.Queue()
        self.playback_task: Optional[asyncio.Task] = None
        
        # 🔒 Lock to serialize WebSocket access (prevents concurrent recv() calls)
        self._stream_lock = asyncio.Lock()
        
        # ⏱️ Timing tracking
        self.first_audio_chunk_time = None
        self.request_start_time = None
        
    async def connect(self) -> bool:
        """
        Establish persistent WebSocket connection to ElevenLabs
        Connection stays open for entire call duration
        """
        try:
            logger.info(f"🔌 [Call {self.call_control_id}] Establishing persistent TTS WebSocket...")
            
            # Create WebSocket service
            self.ws_service = ElevenLabsWebSocketService(self.api_key)
            
            # Connect with optimized settings for streaming
            connected = await self.ws_service.connect(
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format="pcm_16000"  # 16kHz PCM for fast conversion
            )
            
            if connected:
                self.connected = True
                logger.info(f"✅ [Call {self.call_control_id}] Persistent TTS WebSocket established")
                
                # Start playback consumer
                self.playback_task = asyncio.create_task(self._playback_consumer())
                
                return True
            else:
                logger.error(f"❌ [Call {self.call_control_id}] Failed to establish TTS WebSocket")
                return False
                
        except Exception as e:
            logger.error(f"❌ [Call {self.call_control_id}] Error establishing TTS WebSocket: {e}")
            return False
    
    async def _reconnect(self) -> bool:
        """
        Attempt to reconnect the TTS WebSocket after disconnection
        """
        try:
            logger.info(f"🔄 [Call {self.call_control_id}] Attempting TTS WebSocket reconnection...")
            
            # Close existing connection if any
            if self.ws_service:
                try:
                    await self.ws_service.close()
                except:
                    pass
            
            # Create new WebSocket service
            self.ws_service = ElevenLabsWebSocketService(self.api_key)
            
            # Reconnect with same settings
            connected = await self.ws_service.connect(
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format="pcm_16000"
            )
            
            if connected:
                self.connected = True
                logger.info(f"✅ [Call {self.call_control_id}] TTS WebSocket reconnected")
                return True
            else:
                self.connected = False
                logger.error(f"❌ [Call {self.call_control_id}] TTS WebSocket reconnection failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ [Call {self.call_control_id}] Error during TTS reconnection: {e}")
            self.connected = False
            return False
    
    async def stream_sentence(
        self,
        sentence: str,
        is_first: bool = False,
        is_last: bool = False
    ) -> bool:
        """
        Stream a sentence through the persistent WebSocket
        Audio chunks are received and played immediately (no batching)
        
        Args:
            sentence: Text to synthesize
            is_first: If True, this is the first sentence of the response
            is_last: If True, this is the last sentence and should flush
            
        Returns:
            bool: True if streaming started successfully
        """
        # 🔒 CRITICAL: Acquire lock to serialize WebSocket access
        # This prevents concurrent recv() calls which cause errors
        async with self._stream_lock:
            # Check if reconnection is needed
            if not self.connected or not self.ws_service or not self.ws_service.connected:
                logger.warning(f"⚠️ [Call {self.call_control_id}] TTS WebSocket disconnected, attempting reconnection...")
                reconnected = await self._reconnect()
                if not reconnected:
                    logger.error(f"❌ [Call {self.call_control_id}] TTS WebSocket reconnection failed")
                    return False
                logger.info(f"✅ [Call {self.call_control_id}] TTS WebSocket reconnected successfully")
            
            try:
                self.sentence_counter += 1
                sentence_num = self.sentence_counter
                
                # ⏱️ Track first sentence start time
                if sentence_num == 1 and self.request_start_time is None:
                    self.request_start_time = time.time()
                
                logger.info(f"🎤 [Call {self.call_control_id}] Streaming sentence #{sentence_num}: {sentence[:50]}...")
                
                stream_start = time.time()
                
                # Send text to ElevenLabs for synthesis
                await self.ws_service.send_text(
                    text=sentence,
                    try_trigger_generation=True,
                    flush=False
                )
                
                # Send empty string to signal end of input and trigger final generation
                # This is required by ElevenLabs to prevent 20-second timeout
                await self.ws_service.send_text(
                    text="",
                    try_trigger_generation=False,
                    flush=True
                )
                
                # Receive audio chunks and queue for immediate playback
                chunk_count = 0
                first_chunk_time = None
                audio_chunks = []
                
                async for audio_chunk in self.ws_service.receive_audio_chunks():
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        ttfb = (first_chunk_time - stream_start) * 1000
                        logger.info(f"⏱️ [TIMING] TTS_START: Sent to ElevenLabs WebSocket at T+0ms")
                        logger.info(f"⏱️ [TIMING] TTS_TTFB: First audio chunk at T+{ttfb:.0f}ms")
                        logger.info(f"⏱️ [TIMING] TTS_MODEL: {self.model_id}")
                    
                    chunk_count += 1
                    audio_chunks.append(audio_chunk)
                    
                    # Log every few chunks
                    if chunk_count % 5 == 0:
                        logger.debug(f"📦 [Call {self.call_control_id}] Sentence #{sentence_num}: received {chunk_count} chunks...")
                
                # Generation complete for this sentence
                total_time = (time.time() - stream_start) * 1000
                logger.info(f"⏱️ [TIMING] TTS_COMPLETE: All {chunk_count} chunks received in {total_time:.0f}ms")
                logger.info(f"✅ [Call {self.call_control_id}] Sentence #{sentence_num} complete: {chunk_count} chunks in {total_time:.0f}ms")
                
                # Combine chunks and queue for playback
                if audio_chunks:
                    full_audio = b''.join(audio_chunks)
                    
                    # Queue for immediate playback
                    await self.audio_queue.put({
                        'sentence': sentence,
                        'audio_pcm': full_audio,
                        'sentence_num': sentence_num,
                        'is_first': is_first,
                        'is_last': is_last
                    })
                    
                    logger.info(f"📤 [Call {self.call_control_id}] Queued sentence #{sentence_num} for playback ({len(full_audio)} bytes)")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ [Call {self.call_control_id}] Error streaming sentence: {e}")
                return False
    
    async def _playback_consumer(self):
        """
        Background task that consumes audio from queue and plays immediately
        This ensures seamless playback without gaps between sentences
        """
        logger.info(f"🎵 [Call {self.call_control_id}] Playback consumer started")
        
        try:
            while True:
                # Wait for next audio chunk
                audio_item = await self.audio_queue.get()
                
                if audio_item is None:
                    # Shutdown signal
                    logger.info(f"🛑 [Call {self.call_control_id}] Playback consumer shutting down")
                    break
                
                # Play immediately
                await self._play_audio_chunk(
                    sentence=audio_item['sentence'],
                    audio_pcm=audio_item['audio_pcm'],
                    sentence_num=audio_item['sentence_num'],
                    is_first=audio_item['is_first']
                )
                
                self.audio_queue.task_done()
                
        except Exception as e:
            logger.error(f"❌ [Call {self.call_control_id}] Error in playback consumer: {e}")
    
    async def _play_audio_chunk(
        self,
        sentence: str,
        audio_pcm: bytes,
        sentence_num: int,
        is_first: bool
    ):
        """
        Convert PCM audio to MP3 and play via Telnyx
        This is the actual playback that happens immediately per sentence
        """
        try:
            play_start = time.time()
            
            # ⏱️ [TIMING] Track first audio chunk playback (TTFA)
            if self.first_audio_chunk_time is None and self.request_start_time is not None:
                self.first_audio_chunk_time = play_start
                ttfa_ms = int((self.first_audio_chunk_time - self.request_start_time) * 1000)
                logger.info(f"⏱️ [TIMING] TTFA (Time To First Audio Playback): {ttfa_ms}ms")
            
            logger.info(f"⏱️ [TIMING] PLAYBACK_START: Processing sentence #{sentence_num} ({len(audio_pcm)} bytes PCM)")
            
            # Generate unique filename
            audio_hash = hashlib.md5(f"{sentence_num}_{sentence}".encode()).hexdigest()
            pcm_path = f"/tmp/tts_persistent_{self.call_control_id}_{audio_hash}.pcm"
            mp3_path = f"/tmp/tts_persistent_{self.call_control_id}_{audio_hash}.mp3"
            
            # Save PCM
            pcm_save_start = time.time()
            with open(pcm_path, 'wb') as f:
                f.write(audio_pcm)
            pcm_save_ms = int((time.time() - pcm_save_start) * 1000)
            logger.info(f"⏱️ [TIMING] PLAYBACK_PCM_SAVE: {pcm_save_ms}ms")
            
            # Convert PCM to MP3 (fast - ~50ms)
            conversion_start = time.time()
            subprocess.run([
                'ffmpeg',
                '-f', 's16le',
                '-ar', '16000',
                '-ac', '1',
                '-i', pcm_path,
                '-b:a', '64k',
                '-y',
                mp3_path
            ], check=True, capture_output=True, timeout=5)
            
            conversion_time = (time.time() - conversion_start) * 1000
            logger.info(f"⏱️ [TIMING] PLAYBACK_FFMPEG: {conversion_time:.0f}ms")
            
            # Clean up PCM
            os.remove(pcm_path)
            
            # Play via Telnyx
            # Check if using WebSocket streaming (preferred) or REST API
            if self.telnyx_ws:
                # 🚀 WebSocket streaming mode - send audio via WebSocket
                logger.info(f"🔌 Using WebSocket streaming for audio playback")
                
                telnyx_start = time.time()
                success = await self._send_audio_via_websocket(mp3_path)
                telnyx_ms = int((time.time() - telnyx_start) * 1000)
                logger.info(f"⏱️ [TIMING] PLAYBACK_TELNYX_WS: {telnyx_ms}ms")
                
                total_time = (time.time() - play_start) * 1000
                logger.info(f"⏱️ [TIMING] PLAYBACK_TOTAL: {total_time:.0f}ms")
                
                if success:
                    logger.info(f"🔊 [Call {self.call_control_id}] Sentence #{sentence_num} SENT VIA WEBSOCKET ({total_time:.0f}ms total): {sentence[:50]}...")
                    
                    if is_first:
                        logger.info(f"⏱️ [TIMING] FIRST_AUDIO_PLAYING: First sentence started playing on phone")
                        logger.info(f"⏱️  [Call {self.call_control_id}] 🚀 FIRST SENTENCE STARTED PLAYING")
                else:
                    logger.error(f"❌ [Call {self.call_control_id}] Failed to send sentence #{sentence_num} via WebSocket")
                    
            elif self.telnyx_service:
                # 🔄 REST API mode - use play_audio_url (legacy)
                logger.info(f"🔄 Using REST API for audio playback")
                backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8001')
                audio_url = f"{backend_url}/api/tts-audio/{os.path.basename(mp3_path)}"
                
                telnyx_start = time.time()
                playback_result = await self.telnyx_service.play_audio_url(
                    call_control_id=self.call_control_id,
                    audio_url=audio_url
                )
                telnyx_ms = int((time.time() - telnyx_start) * 1000)
                logger.info(f"⏱️ [TIMING] PLAYBACK_TELNYX_REST: {telnyx_ms}ms")
                
                total_time = (time.time() - play_start) * 1000
                logger.info(f"⏱️ [TIMING] PLAYBACK_TOTAL: {total_time:.0f}ms")
                
                if playback_result.get('success'):
                    logger.info(f"🔊 [Call {self.call_control_id}] Sentence #{sentence_num} PLAYING ({total_time:.0f}ms total): {sentence[:50]}...")
                    
                    if is_first:
                        logger.info(f"⏱️ [TIMING] FIRST_AUDIO_PLAYING: First sentence started playing on phone")
                        logger.info(f"⏱️  [Call {self.call_control_id}] 🚀 FIRST SENTENCE STARTED PLAYING")
                else:
                    logger.error(f"❌ [Call {self.call_control_id}] Failed to play sentence #{sentence_num}")
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ [Call {self.call_control_id}] ffmpeg timeout for sentence #{sentence_num}")
        except Exception as e:
            logger.error(f"❌ [Call {self.call_control_id}] Error playing sentence #{sentence_num}: {e}")
    
    async def _send_audio_via_websocket(self, mp3_path: str) -> bool:
        """
        Send audio file via Telnyx WebSocket
        Converts MP3 to 8kHz mulaw and sends as media packets
        
        Args:
            mp3_path: Path to MP3 file to send
            
        Returns:
            bool: True if successful
        """
        try:
            import base64
            import json
            
            # Convert MP3 to 8kHz mulaw for Telnyx
            mulaw_path = mp3_path.replace('.mp3', '.mulaw')
            
            conversion_result = subprocess.run([
                'ffmpeg',
                '-i', mp3_path,
                '-ar', '8000',        # 8kHz sample rate
                '-ac', '1',           # Mono
                '-f', 'mulaw',        # mulaw codec
                '-y',
                mulaw_path
            ], check=True, capture_output=True, timeout=5)
            
            logger.info(f"✅ Converted MP3 to mulaw: {mulaw_path}")
            
            # Read mulaw audio data
            with open(mulaw_path, 'rb') as f:
                mulaw_data = f.read()
            
            # Clean up files
            os.remove(mp3_path)
            os.remove(mulaw_path)
            
            # Send audio in chunks (Telnyx expects ~20ms chunks = 160 bytes at 8kHz)
            chunk_size = 160  # 20ms at 8kHz mulaw
            total_chunks = (len(mulaw_data) + chunk_size - 1) // chunk_size
            
            logger.info(f"📤 Sending {len(mulaw_data)} bytes of audio ({total_chunks} chunks) via WebSocket")
            
            for i in range(0, len(mulaw_data), chunk_size):
                chunk = mulaw_data[i:i+chunk_size]
                
                # Encode chunk as base64
                payload = base64.b64encode(chunk).decode('utf-8')
                
                # Send via Telnyx WebSocket in their expected format
                message = {
                    "event": "media",
                    "media": {
                        "payload": payload
                    }
                }
                
                await self.telnyx_ws.send_text(json.dumps(message))
            
            logger.info(f"✅ Sent {total_chunks} audio chunks via WebSocket")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ ffmpeg timeout converting to mulaw")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending audio via WebSocket: {e}")
            return False
    
    async def send_keepalive(self):
        """
        Send keepalive message to maintain persistent connection during pauses
        """
        if self.connected and self.ws_service:
            try:
                # Send empty text to keep connection alive
                await self.ws_service.send_text(text="", try_trigger_generation=False)
                logger.debug(f"💓 [Call {self.call_control_id}] Sent keepalive")
            except Exception as e:
                logger.error(f"❌ [Call {self.call_control_id}] Keepalive failed: {e}")
    
    async def close(self):
        """
        Close the persistent WebSocket connection
        """
        logger.info(f"🔌 [Call {self.call_control_id}] Closing persistent TTS WebSocket...")
        
        # Stop playback consumer
        if self.playback_task:
            await self.audio_queue.put(None)  # Shutdown signal
            try:
                await asyncio.wait_for(self.playback_task, timeout=2.0)
            except asyncio.TimeoutError:
                self.playback_task.cancel()
        
        # Close WebSocket
        if self.ws_service:
            await self.ws_service.close()
        
        self.connected = False
        logger.info(f"✅ [Call {self.call_control_id}] Persistent TTS WebSocket closed")


class PersistentTTSManager:
    """
    Manages persistent TTS sessions across multiple calls
    One session per active call
    """
    
    def __init__(self):
        self.sessions: Dict[str, PersistentTTSSession] = {}
    
    async def create_session(
        self,
        call_control_id: str,
        api_key: str,
        voice_id: str,
        model_id: str = "eleven_flash_v2_5",
        telnyx_service=None,
        agent_config: dict = None,
        telnyx_ws=None
    ) -> Optional[PersistentTTSSession]:
        """
        Create and connect a new persistent TTS session for a call
        """
        if call_control_id in self.sessions:
            logger.warning(f"⚠️  Session already exists for call {call_control_id}")
            return self.sessions[call_control_id]
        
        session = PersistentTTSSession(
            call_control_id=call_control_id,
            api_key=api_key,
            voice_id=voice_id,
            model_id=model_id,
            telnyx_service=telnyx_service,
            agent_config=agent_config,
            telnyx_ws=telnyx_ws
        )
        
        connected = await session.connect()
        
        if connected:
            self.sessions[call_control_id] = session
            logger.info(f"✅ Created persistent TTS session for call {call_control_id}")
            return session
        else:
            logger.error(f"❌ Failed to create persistent TTS session for call {call_control_id}")
            return None
    
    def get_session(self, call_control_id: str) -> Optional[PersistentTTSSession]:
        """
        Get existing persistent TTS session for a call
        """
        session = self.sessions.get(call_control_id)
        if session:
            logger.debug(f"✅ Found persistent TTS session for call {call_control_id[:20]}...")
        else:
            logger.warning(f"⚠️  No persistent TTS session found for call {call_control_id[:20]}... (active sessions: {list(self.sessions.keys())})")
        return session
    
    def update_websocket(self, call_control_id: str, telnyx_ws):
        """
        Update an existing session with Telnyx WebSocket connection
        Called when WebSocket connection is established
        """
        session = self.sessions.get(call_control_id)
        if session:
            session.telnyx_ws = telnyx_ws
            logger.info(f"✅ Updated persistent TTS session with Telnyx WebSocket for call {call_control_id}")
            return True
        else:
            logger.warning(f"⚠️  No persistent TTS session found to update for call {call_control_id}")
            return False
    
    async def close_session(self, call_control_id: str):
        """
        Close and remove persistent TTS session for a call
        """
        session = self.sessions.get(call_control_id)
        if session:
            await session.close()
            del self.sessions[call_control_id]
            logger.info(f"✅ Closed persistent TTS session for call {call_control_id}")


# Global manager instance
persistent_tts_manager = PersistentTTSManager()
```

---

### 3. Soniox STT Service

**File:** `/app/backend/soniox_service.py`

This service handles Speech-to-Text using Soniox.

```python
import asyncio
import json
import logging
import websockets
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)

SONIOX_API_KEY = os.getenv("SONIOX_API_KEY")

class SonioxStreamingService:
    """
    Soniox Real-Time Speech-to-Text
    Handles real-time speech-to-text with advanced endpoint detection
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or SONIOX_API_KEY
        self.ws = None
        self.session_id = None
        
    async def connect(self, 
                     model: str = "stt-rt-telephony-v3",
                     audio_format: str = "mulaw",
                     sample_rate: int = 8000,
                     num_channels: int = 1,
                     enable_endpoint_detection: bool = True,
                     enable_speaker_diarization: bool = False,
                     language_hints: list = None,
                     context: str = ""):
        """
        Connect to Soniox Real-Time WebSocket API
        
        Args:
            model: Soniox model to use (default: stt-rt-telephony-v3)
            audio_format: Audio format (mulaw, alaw, pcm_s16le, etc.)
            sample_rate: Audio sample rate (8000 or 16000)
            num_channels: Number of audio channels (1=mono, 2=stereo)
            enable_endpoint_detection: Enable automatic endpoint detection
            enable_speaker_diarization: Enable speaker diarization
            language_hints: List of language codes (e.g. ["en", "es"])
            context: Custom context for improved accuracy
        """
        url = "wss://stt-rt.soniox.com/transcribe-websocket"
        
        # Build configuration message
        config = {
            "api_key": self.api_key,
            "model": model,
            "audio_format": audio_format,
            "sample_rate": sample_rate,
            "num_channels": num_channels,
            "enable_endpoint_detection": enable_endpoint_detection,
        }
        
        # Add optional parameters
        if enable_speaker_diarization:
            config["enable_speaker_diarization"] = True
        
        if language_hints:
            config["language_hints"] = language_hints
        
        if context:
            config["context"] = context
        
        try:
            # Connect to Soniox WebSocket
            self.ws = await websockets.connect(url, ping_interval=30, ping_timeout=10)
            logger.info(f"✅ Connected to Soniox Real-Time STT")
            
            # Send configuration message
            await self.ws.send(json.dumps(config))
            logger.info(f"⚙️  Config: model={model}, format={audio_format}, rate={sample_rate}Hz, channels={num_channels}")
            logger.info(f"⚙️  Endpoint detection: {enable_endpoint_detection}, Speaker diarization: {enable_speaker_diarization}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Soniox: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to Soniox (binary WebSocket frame)"""
        if self.ws and not self.ws.closed:
            try:
                # Soniox expects raw binary audio data
                await self.ws.send(audio_data)
            except Exception as e:
                logger.error(f"❌ Error sending audio to Soniox: {e}")
    
    async def receive_messages(self, 
                               on_partial_transcript: Optional[Callable] = None,
                               on_final_transcript: Optional[Callable] = None,
                               on_endpoint_detected: Optional[Callable] = None):
        """
        Receive and process messages from Soniox
        
        Args:
            on_partial_transcript: Callback for non-final tokens
            on_final_transcript: Callback for final tokens  
            on_endpoint_detected: Callback for <end> token (endpoint detected)
        """
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                # Check for errors
                if "error_code" in data:
                    error_code = data.get("error_code")
                    error_message = data.get("error_message", "Unknown error")
                    logger.error(f"❌ Soniox error {error_code}: {error_message}")
                    break
                
                # Check for finished signal
                if data.get("finished"):
                    logger.info("🛑 Soniox session finished")
                    break
                
                # Process tokens
                tokens = data.get("tokens", [])
                if tokens:
                    # Separate final and non-final tokens
                    final_tokens = []
                    non_final_tokens = []
                    endpoint_detected = False
                    
                    for token in tokens:
                        text = token.get("text", "")
                        is_final = token.get("is_final", False)
                        
                        # Check for endpoint token
                        if text == "<end>" and is_final:
                            endpoint_detected = True
                            logger.info(f"🎯 Endpoint detected: <end> token received")
                            continue  # Don't include <end> in transcript
                        
                        if is_final:
                            final_tokens.append(token)
                        else:
                            non_final_tokens.append(token)
                    
                    # Callbacks for non-final tokens (partial transcripts)
                    if non_final_tokens and on_partial_transcript:
                        text = "".join([t.get("text", "") for t in non_final_tokens])
                        logger.info(f"🔍 Soniox (partial): {text[:50]}...")
                        await on_partial_transcript(text, data)
                    
                    # Callbacks for final tokens
                    if final_tokens and on_final_transcript:
                        text = "".join([t.get("text", "") for t in final_tokens])
                        logger.info(f"✅ Soniox (final): {text}")
                        await on_final_transcript(text, data)
                    
                    # Callback for endpoint detection
                    if endpoint_detected and on_endpoint_detected:
                        await on_endpoint_detected()
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 Soniox connection closed")
        except Exception as e:
            logger.error(f"❌ Error receiving Soniox messages: {e}")
    
    async def finalize_manually(self):
        """Send manual finalization message to force all tokens to become final"""
        if self.ws and not self.ws.closed:
            try:
                finalize_message = {"type": "finalize"}
                await self.ws.send(json.dumps(finalize_message))
                logger.info("📌 Sent manual finalization request to Soniox")
            except Exception as e:
                logger.error(f"❌ Error sending finalization: {e}")
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.ws and not self.ws.closed:
            try:
                # Send empty frame to gracefully end stream
                await self.ws.send(b"")
                logger.info("✅ Sent end-of-stream signal to Soniox")
                
                # Wait briefly for final responses
                await asyncio.sleep(0.5)
                
                await self.ws.close()
                logger.info("✅ Soniox session closed gracefully")
            except Exception as e:
                logger.error(f"❌ Error closing Soniox session: {e}")
```

---

### 4. Server - Soniox Handler & TTS Streaming Callback

**File:** `/app/backend/server.py` (relevant sections)

This is the main handler that orchestrates STT → LLM → TTS flow.

```python
# ============================================================
# HANDLE SONIOX STREAMING - Main WebSocket Handler
# ============================================================

async def handle_soniox_streaming(websocket: WebSocket, session, call_id: str, call_control_id: str):
    """Handle streaming with Soniox"""
    from soniox_service import SonioxStreamingService
    from dead_air_monitor import monitor_dead_air
    
    agent_config = session.agent_config
    soniox_settings = agent_config.get("settings", {}).get("soniox_settings", {})
    
    # Extract Soniox settings
    model = soniox_settings.get("model", "stt-rt-telephony-v3")
    audio_format = soniox_settings.get("audio_format", "mulaw")
    sample_rate = soniox_settings.get("sample_rate", 8000)
    num_channels = soniox_settings.get("num_channels", 1)
    enable_endpoint_detection = soniox_settings.get("enable_endpoint_detection", True)
    enable_speaker_diarization = soniox_settings.get("enable_speaker_diarization", False)
    language_hints = soniox_settings.get("language_hints", ["en"])
    context = soniox_settings.get("context", "")
    
    # ⏱️  LATENCY TRACKING: Track time of last audio packet received
    last_audio_received_time = None
    stt_start_time = None
    
    # 🚦 INTERRUPTION HANDLING: Track agent speaking state locally
    is_agent_speaking = False
    agent_generating_response = False
    current_playback_ids = set()
    call_ending = False
    
    # Also store in global state for webhook access
    call_states[call_control_id] = {
        "agent_generating_response": False,
        "current_playback_ids": set(),
        "session": session
    }
    logger.info(f"✅ Initialized call_states for {call_control_id} with session reference")
    
    # 🔌 Store WebSocket in call_data and update persistent TTS session
    if call_control_id in active_telnyx_calls:
        active_telnyx_calls[call_control_id]["telnyx_ws"] = websocket
        logger.info(f"✅ Stored Telnyx WebSocket in call_data for audio streaming")
        
        # Update persistent TTS session with WebSocket (if it exists)
        persistent_tts_manager.update_websocket(call_control_id, websocket)
    
    # Get user's Soniox API key
    soniox_api_key = await get_api_key(session.user_id, "soniox")
    if not soniox_api_key:
        logger.error("❌ No Soniox API key found for user")
        await websocket.close(code=1011, reason="Soniox API key not configured")
        return
    
    logger.info(f"🔑 Using user's Soniox API key (first 10 chars): {soniox_api_key[:10]}...")
    
    # Initialize Soniox service with user's API key
    soniox = SonioxStreamingService(api_key=soniox_api_key)
    connected = await soniox.connect(
        model=model,
        audio_format=audio_format,
        sample_rate=sample_rate,
        num_channels=num_channels,
        enable_endpoint_detection=enable_endpoint_detection,
        enable_speaker_diarization=enable_speaker_diarization,
        language_hints=language_hints,
        context=context
    )
    
    if not connected:
        logger.error("❌ Failed to connect to Soniox")
        await websocket.close(code=1011, reason="Soniox connection failed")
        return
    
    # Keep track of accumulated transcript
    accumulated_transcript = ""
    partial_transcript = ""
    
    # ... (partial transcript handlers, dead air monitoring, etc.)
    
    # ============================================================
    # ON ENDPOINT DETECTED - Trigger LLM + TTS
    # ============================================================
    
    async def on_endpoint_detected():
        """Called when Soniox detects end of user speech"""
        nonlocal accumulated_transcript, is_agent_speaking, agent_generating_response
        nonlocal first_sentence_played, current_playback_ids, full_response_text
        
        if not accumulated_transcript.strip():
            logger.info("⚠️  Empty transcript at endpoint, ignoring")
            return
        
        # ⏱️ Mark STT end time for latency tracking
        stt_end_time = time.time()
        
        # Log when user stopped speaking
        logger.info(f"⏱️  USER STOPPED SPEAKING at T=0ms")
        
        # 🚦 CRITICAL: Set flags BEFORE LLM starts
        is_agent_speaking = True
        agent_generating_response = True
        call_states[call_control_id]["agent_generating_response"] = True
        logger.info(f"🎙️ Agent generating response - interruption detection active")
        
        # Dead air prevention: Mark agent as speaking
        session.mark_agent_speaking_start()
        
        # ⏱️ Track TTS start
        tts_start_time = None
        
        # Real-time streaming: Start TTS as sentences arrive
        sentence_queue = []
        tts_tasks = []
        first_tts_started = False
        
        # ============================================================
        # STREAM SENTENCE TO TTS - The Magic Callback
        # ============================================================
        
        async def stream_sentence_to_tts(sentence):
            """
            This callback is invoked by the LLM streaming service
            whenever a complete sentence is ready.
            
            It immediately starts TTS generation WITHOUT waiting
            for the full LLM response to complete.
            """
            # Import inside callback to avoid closure scoping issues
            from persistent_tts_service import persistent_tts_manager as tts_manager
            
            nonlocal current_playback_ids, first_sentence_played, full_response_text
            nonlocal tts_start_time, first_tts_started, tts_tasks, sentence_queue
            
            if not tts_start_time:
                tts_start_time = time.time()
            
            full_response_text += sentence + " "
            sentence_queue.append(sentence)
            logger.info(f"📤 Sentence arrived from LLM: {sentence[:50]}...")
            
            # ⏱️ [TIMING] First sentence arrival from LLM
            if len(sentence_queue) == 1:
                ttfs_ms = int((time.time() - stt_end_time) * 1000)
                logger.info(f"⏱️ [TIMING] TTFS (Time To First Sentence): {ttfs_ms}ms")
            
            # 🚀 START TTS GENERATION IMMEDIATELY
            if not first_tts_started:
                first_tts_started = True
                logger.info(f"⚡ Starting REAL-TIME TTS for first sentence")
            
            # Get or create persistent TTS session
            persistent_tts_session = tts_manager.get_session(call_control_id)
            
            # 🚀 ON-DEMAND SESSION CREATION for multi-worker environments
            if not persistent_tts_session:
                agent_config = session.agent_config
                agent_settings = agent_config.get("settings", {})
                tts_provider = agent_settings.get("tts_provider")
                use_persistent_tts = agent_settings.get("elevenlabs_settings", {}).get("use_persistent_tts", True)
                
                if tts_provider == "elevenlabs" and use_persistent_tts:
                    try:
                        logger.info(f"⚡ ON-DEMAND: Creating persistent TTS session")
                        
                        elevenlabs_api_key = await session.get_api_key("elevenlabs")
                        
                        if elevenlabs_api_key:
                            elevenlabs_settings = agent_settings.get("elevenlabs_settings", {})
                            voice_id = elevenlabs_settings.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
                            model_id = elevenlabs_settings.get("model", "eleven_flash_v2_5")
                            
                            telnyx_api_key = await session.get_api_key("telnyx")
                            telnyx_connection_id = await session.get_api_key("telnyx_connection_id")
                            telnyx_svc = get_telnyx_service(api_key=telnyx_api_key, connection_id=telnyx_connection_id)
                            
                            # 🔌 CRITICAL: Use WebSocket from closure
                            logger.info(f"✅ ON-DEMAND: Using Telnyx WebSocket from closure")
                            
                            persistent_tts_session = await tts_manager.create_session(
                                call_control_id=call_control_id,
                                api_key=elevenlabs_api_key,
                                voice_id=voice_id,
                                model_id=model_id,
                                telnyx_service=telnyx_svc,
                                agent_config=agent_config,
                                telnyx_ws=websocket  # From outer function closure!
                            )
                            
                            if persistent_tts_session:
                                logger.info(f"✅ ON-DEMAND: Session created successfully!")
                    except Exception as e:
                        logger.error(f"❌ ON-DEMAND: Error creating session: {e}")
            
            logger.info(f"🔍 Persistent TTS lookup: session={'FOUND' if persistent_tts_session else 'NOT FOUND'}")
            
            if persistent_tts_session:
                # 🚀 USE PERSISTENT TTS WEBSOCKET - Streams immediately!
                is_first = len(sentence_queue) == 1
                is_last = False
                
                logger.info(f"🚀 Streaming sentence #{len(sentence_queue)} via persistent WebSocket")
                
                # Stream sentence immediately (non-blocking)
                tts_task = asyncio.create_task(
                    persistent_tts_session.stream_sentence(sentence, is_first=is_first, is_last=is_last)
                )
                tts_tasks.append(tts_task)
            else:
                # Fallback to REST API
                logger.info(f"🔄 Using REST API fallback")
                agent_config = session.agent_config
                tts_task = asyncio.create_task(generate_tts_audio(sentence, agent_config))
                tts_tasks.append(tts_task)
            
            tts_ready_time = int((time.time() - tts_start_time) * 1000)
            logger.info(f"🎵 TTS task #{len(tts_tasks)} started at +{tts_ready_time}ms")
            
            # ⏱️ [TIMING] First TTS task creation
            if len(tts_tasks) == 1:
                ttft_tts_ms = int((time.time() - stt_end_time) * 1000)
                logger.info(f"⏱️ [TIMING] TTFT_TTS (First TTS Task Started): {ttft_tts_ms}ms")
        
        # ============================================================
        # STREAM LLM RESPONSE WITH TTS CALLBACK
        # ============================================================
        
        # Call LLM with streaming callback
        await calling_service.process_user_input(
            accumulated_transcript,
            stream_callback=stream_sentence_to_tts
        )
        
        # Wait for all TTS tasks to complete
        if tts_tasks:
            await asyncio.gather(*tts_tasks, return_exceptions=True)
        
        # Reset state
        is_agent_speaking = False
        agent_generating_response = False
        call_states[call_control_id]["agent_generating_response"] = False
        accumulated_transcript = ""
```

---

### 5. Telnyx Service

**File:** `/app/backend/telnyx_service.py`

This service handles Telnyx call control and audio playback.

```python
import os
import telnyx
from telnyx import Telnyx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import json

logger = logging.getLogger(__name__)

class TelnyxService:
    def __init__(self, api_key: str = None, connection_id: str = None):
        self.api_key = api_key or os.environ.get('TELNYX_API_KEY')
        self.connection_id = connection_id or os.environ.get('TELNYX_CONNECTION_ID')
        
        if not self.api_key:
            raise ValueError("TELNYX_API_KEY not provided")
        if not self.connection_id:
            raise ValueError("TELNYX_CONNECTION_ID not provided")
        
        self.client = Telnyx(api_key=self.api_key)
        
        # Persistent HTTP client for connection pooling (faster!)
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        
        logger.info(f"Telnyx service initialized with connection: {self.connection_id}")
    
    async def play_audio_url(
        self,
        call_control_id: str,
        audio_url: str,
        loop: bool = False,
        overlay: bool = False
    ) -> Dict[str, Any]:
        """
        Play pre-generated audio from URL on the call
        Uses persistent HTTP client for connection pooling (much faster!)
        
        Args:
            call_control_id: Telnyx call control ID
            audio_url: URL to audio file
            loop: If True, loop the audio continuously
            overlay: If True, play as background
        """
        try:
            telnyx_api_key = os.environ.get('TELNYX_API_KEY')
            playback_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/playback_start"
            
            payload = {"audio_url": audio_url}
            if loop:
                payload["loop"] = "infinity"
            if overlay:
                payload["overlay"] = True
            
            # Use the persistent HTTP client (reuses connections!)
            response = await self.http_client.post(
                playback_url,
                headers={
                    "Authorization": f"Bearer {telnyx_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                playback_id = response_data.get("data", {}).get("playback_id")
                logger.info(f"✅ Playing audio from URL, playback_id: {playback_id}")
                return {"success": True, "playback_id": playback_id}
            else:
                logger.error(f"❌ Playback failed: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Error playing audio URL: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_playback(self, call_control_id: str, playback_id: str) -> Dict[str, Any]:
        """Stop an active audio playback (for interruption handling)"""
        try:
            logger.info(f"🛑 Stopping playback {playback_id} on call: {call_control_id}")
            
            stop_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/playback_stop"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {"playback_ids": [playback_id]}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(stop_url, headers=headers, json=data, timeout=5.0)
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"✅ Successfully stopped playback {playback_id}")
                    return {"success": True}
                else:
                    logger.error(f"❌ Failed to stop playback: {response.status_code}")
                    return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"❌ Error stopping playback: {e}")
            return {"success": False, "error": str(e)}
    
    async def hangup_call(self, call_control_id: str) -> Dict[str, Any]:
        """Hangup an active call"""
        try:
            logger.info(f"📞 Hanging up call: {call_control_id}")
            self.client.calls.actions.hangup(call_control_id=call_control_id)
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error hanging up call: {e}")
            return {"success": False, "error": str(e)}
    
    async def answer_call(self, call_control_id: str, webhook_url: str = None, stream_url: str = None) -> Dict[str, Any]:
        """Answer an inbound call with optional streaming"""
        try:
            logger.info(f"📞 Answering call: {call_control_id}")
            
            answer_params = {"call_control_id": call_control_id}
            
            if webhook_url:
                answer_params["webhook_url"] = webhook_url
                answer_params["webhook_url_method"] = 'POST'
            
            if stream_url:
                answer_params["stream_url"] = stream_url
            
            self.client.calls.actions.answer(**answer_params)
            
            return {"success": True, "call_control_id": call_control_id}
        except Exception as e:
            logger.error(f"❌ Error answering call: {e}")
            return {"success": False, "error": str(e)}
```

---

## Key Configuration

### ElevenLabs WebSocket URL Format

```
wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}&output_format={output_format}&enable_ssml_parsing=true
```

**Important Parameters:**
- `voice_id`: The ElevenLabs voice ID (e.g., "21m00Tcm4TlvDq8ikWAM")
- `model_id`: TTS model (e.g., "eleven_flash_v2_5" for fastest)
- `output_format`: Audio format (e.g., "pcm_16000" for 16kHz PCM)
- `enable_ssml_parsing=true`: **CRITICAL** - Enables SSML tag parsing

### Message Protocol

**Sending Text:**
```json
{
    "text": "Hello world",
    "try_trigger_generation": true
}
```

**Flushing/End of Input:**
```json
{
    "text": "",
    "flush": true
}
```

**Receiving Audio:**
```json
{
    "audio": "base64_encoded_audio_data",
    "isFinal": null,
    "alignment": {...},
    "normalizedAlignment": {...}
}
```

---

## Latency Optimization Summary

| Stage | Target | How |
|-------|--------|-----|
| STT | <200ms | Soniox endpoint detection |
| LLM | <500ms | Streaming with sentence callback |
| TTS Generation | <150ms | ElevenLabs Flash v2.5 model |
| TTS Playback | <100ms | WebSocket audio streaming |
| **Total TTFA** | **<1000ms** | Parallel pipeline |

---

## Common Issues & Fixes

### Issue 1: SSML Tags Spoken Literally
**Cause:** `enable_ssml_parsing=true` not in WebSocket URL
**Fix:** Add parameter to connection URL

### Issue 2: 20-Second Timeout
**Cause:** Not sending empty flush after text
**Fix:** Always send `{"text": "", "flush": true}` after text

### Issue 3: Audio Truncation
**Cause:** Breaking on `normalizedAlignment` too early
**Fix:** Use 0.5s timeout to detect end of audio stream

### Issue 4: REST API Fallback
**Cause:** `telnyx_ws` not passed to session
**Fix:** Use websocket from closure in on-demand creation

---

## Testing

### Direct WebSocket Test
```python
cd /app/backend && python test_tts_websocket.py
```

### Expected Output
```
✅ "Hello!" → E2E: ~150-200ms
✅ "With SSML" → E2E: ~150-200ms (SSML parsed correctly)
✅ "Kendrick?" → E2E: ~150-200ms
```

---

**END OF MASTER DOCUMENT**

---

## Appendix A: Full Telnyx Service Code

**File:** `/app/backend/telnyx_service.py`

This is the complete Telnyx service implementation:

```python
import os
import telnyx
from telnyx import Telnyx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import json

logger = logging.getLogger(__name__)

class TelnyxService:
    def __init__(self, api_key: str = None, connection_id: str = None):
        # Use provided keys or fall back to environment variables
        self.api_key = api_key or os.environ.get('TELNYX_API_KEY')
        self.connection_id = connection_id or os.environ.get('TELNYX_CONNECTION_ID')
        
        if not self.api_key:
            raise ValueError("TELNYX_API_KEY not provided and not found in environment variables")
        if not self.connection_id:
            raise ValueError("TELNYX_CONNECTION_ID not provided and not found in environment variables")
        
        # Initialize Telnyx client
        self.client = Telnyx(api_key=self.api_key)
        
        # Initialize persistent HTTP client for connection pooling
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        
        logger.info(f"Telnyx service initialized with connection: {self.connection_id}")
    
    async def initiate_outbound_call(
        self,
        to_number: str,
        from_number: str,
        webhook_url: str,
        custom_variables: Dict[str, Any] = None,
        stream_url: str = None,
        enable_amd: bool = False,
        amd_mode: str = "premium"
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call using Telnyx
        
        Args:
            to_number: Destination phone number (E.164 format)
            from_number: Source phone number (E.164 format)
            webhook_url: Webhook URL for call events
            custom_variables: Variables to pass to the agent
            stream_url: WebSocket URL for bidirectional media streaming
            enable_amd: Enable Answering Machine Detection
            amd_mode: "standard" ($0.002) or "premium" ($0.0065)
        
        Returns:
            Call information including call_control_id
        """
        try:
            logger.info(f"📞 Initiating outbound call from {from_number} to {to_number}")
            
            # Prepare dial parameters
            dial_params = {
                "to": to_number,
                "from_": from_number,
                "connection_id": self.connection_id,
                "webhook_url": webhook_url
            }
            
            # Add AMD if enabled
            if enable_amd:
                logger.info(f"🤖 Enabling AMD ({amd_mode} mode)")
                dial_params["answering_machine_detection"] = amd_mode
            
            # Add streaming parameters if provided
            if stream_url:
                logger.info(f"🌐 Adding streaming parameters: {stream_url}")
                dial_params["stream_url"] = stream_url
                dial_params["stream_track"] = "inbound_track"  # Only user audio, not agent
                dial_params["stream_bidirectional_mode"] = "rtp"
            
            # Create the call using Telnyx Call Control API
            response = self.client.calls.dial(**dial_params)
            
            # Access response data correctly
            call_data = response.data if hasattr(response, 'data') else response
            call_control_id = call_data.get('call_control_id') if isinstance(call_data, dict) else getattr(call_data, 'call_control_id', None)
            
            logger.info(f"✅ Call initiated: {call_control_id}")
            
            return {
                "success": True,
                "call_control_id": call_control_id,
                "call_leg_id": call_data.get('call_leg_id') if isinstance(call_data, dict) else getattr(call_data, 'call_leg_id', None),
                "call_session_id": call_data.get('call_session_id') if isinstance(call_data, dict) else getattr(call_data, 'call_session_id', None),
                "status": "queued",
                "custom_variables": custom_variables or {}
            }
            
        except Exception as e:
            logger.error(f"❌ Error initiating call: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def answer_call(self, call_control_id: str, webhook_url: str = None, stream_url: str = None) -> Dict[str, Any]:
        """Answer an inbound call with optional streaming"""
        try:
            logger.info(f"📞 Answering call: {call_control_id}")
            
            # Build answer parameters
            answer_params = {
                "call_control_id": call_control_id
            }
            
            # Add webhook URL if provided
            if webhook_url:
                answer_params["webhook_url"] = webhook_url
                answer_params["webhook_url_method"] = 'POST'
            
            # Add streaming URL if provided
            if stream_url:
                answer_params["stream_url"] = stream_url
            
            self.client.calls.actions.answer(**answer_params)
            
            return {"success": True, "call_control_id": call_control_id}
        except Exception as e:
            logger.error(f"❌ Error answering call: {e}")
            return {"success": False, "error": str(e)}
    
    async def reject_call(self, call_control_id: str, cause: str = "CALL_REJECTED") -> Dict[str, Any]:
        """Reject an inbound call"""
        try:
            logger.info(f"📞 Rejecting call: {call_control_id}")
            
            self.client.calls.actions.reject(
                call_control_id=call_control_id,
                cause=cause
            )
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error rejecting call: {e}")
            return {"success": False, "error": str(e)}
    
    async def hangup_call(self, call_control_id: str) -> Dict[str, Any]:
        """Hangup an active call"""
        try:
            logger.info(f"📞 Hanging up call: {call_control_id}")
            
            self.client.calls.actions.hangup(call_control_id=call_control_id)
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error hanging up call: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_playback(self, call_control_id: str, playback_id: str) -> Dict[str, Any]:
        """Stop an active audio playback (for interruption handling)"""
        try:
            import httpx
            
            logger.info(f"🛑 Stopping playback {playback_id} on call: {call_control_id}")
            
            # Use REST API directly (SDK doesn't support playback_stop)
            stop_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/playback_stop"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "playback_ids": [playback_id]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(stop_url, headers=headers, json=data, timeout=5.0)
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"✅ Successfully stopped playback {playback_id}")
                    return {"success": True}
                else:
                    logger.error(f"❌ Failed to stop playback: {response.status_code} - {response.text}")
                    return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"❌ Error stopping playback: {e}")
            return {"success": False, "error": str(e)}
    
    async def play_audio(
        self,
        call_control_id: str,
        audio_url: str
    ) -> Dict[str, Any]:
        """Play audio on the call"""
        try:
            self.client.calls.actions.playback_start(
                call_control_id=call_control_id,
                audio_url=audio_url
            )
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error playing audio: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_recording(
        self,
        call_control_id: str,
        format: str = "mp3",
        channels: str = "dual"
    ) -> Dict[str, Any]:
        """Start recording the call"""
        try:
            logger.info(f"🎙️ Starting recording: {call_control_id}")
            
            self.client.calls.actions.start_recording(
                call_control_id=call_control_id,
                format=format,
                channels=channels
            )
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error starting recording: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_recording(self, call_control_id: str) -> Dict[str, Any]:
        """Stop recording the call"""
        try:
            logger.info(f"🎙️ Stopping recording: {call_control_id}")
            
            self.client.calls.actions.stop_recording(call_control_id=call_control_id)
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error stopping recording: {e}")
            return {"success": False, "error": str(e)}
    
    async def play_audio_url(
        self,
        call_control_id: str,
        audio_url: str,
        loop: bool = False,
        overlay: bool = False
    ) -> Dict[str, Any]:
        """
        Play pre-generated audio from URL on the call
        Used for parallel TTS generation + sequential playback
        Uses persistent HTTP client for connection pooling (much faster!)
        
        Args:
            call_control_id: Telnyx call control ID
            audio_url: URL to audio file
            loop: If True, loop the audio continuously
            overlay: If True, play as background (doesn't interrupt other audio)
        """
        try:
            telnyx_api_key = os.environ.get('TELNYX_API_KEY')
            playback_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/playback_start"
            
            # Build payload
            payload = {"audio_url": audio_url}
            if loop:
                payload["loop"] = "infinity"  # Loop continuously
            if overlay:
                payload["overlay"] = True  # Play as background
            
            # Use the persistent HTTP client (reuses connections!)
            response = await self.http_client.post(
                playback_url,
                headers={
                    "Authorization": f"Bearer {telnyx_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                playback_id = response_data.get("data", {}).get("playback_id")
                logger.info(f"✅ Playing audio from URL, playback_id: {playback_id} (loop={loop}, overlay={overlay})")
                return {"success": True, "playback_id": playback_id}
            else:
                logger.error(f"❌ Playback failed: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Error playing audio URL: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_bidirectional_streaming(
        self,
        call_control_id: str,
        stream_url: str
    ) -> Dict[str, Any]:
        """Start bidirectional RTP audio streaming to WebSocket"""
        try:
            logger.info(f"🎙️ Starting bidirectional RTP streaming on call: {call_control_id} to {stream_url}")
            
            # Use Telnyx bidirectional RTP streaming
            self.client.calls.actions.start_streaming(
                call_control_id=call_control_id,
                stream_url=stream_url,
                stream_track="both_tracks",  # Stream both inbound and outbound
                stream_bidirectional_mode="rtp"  # Enable RTP bidirectional mode
            )
            
            logger.info(f"✅ Bidirectional RTP streaming started for call: {call_control_id}")
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error starting bidirectional streaming: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_audio_streaming(
        self,
        call_control_id: str
    ) -> Dict[str, Any]:
        """Stop streaming audio"""
        try:
            logger.info(f"🛑 Stopping audio streaming on call: {call_control_id}")
            
            self.client.calls.actions.stop_streaming(
                call_control_id=call_control_id
            )
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error stopping audio streaming: {e}")
            return {"success": False, "error": str(e)}

    def verify_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verify webhook signature from Telnyx"""
        # TODO: Implement webhook signature verification
        return True
```

---

## Appendix B: LLM Streaming with Sentence Callback

**File:** `/app/backend/calling_service.py` (relevant section)

This is how LLM streaming with real-time sentence callbacks works:

```python
async def _stream_llm_response_to_tts(self, user_message: str, stream_callback=None) -> str:
    """
    Stream LLM response and invoke TTS callback for each complete sentence
    
    Args:
        user_message: User's input text
        stream_callback: Async callback invoked for each complete sentence
        
    Returns:
        Full response text
    """
    import re
    
    # Sentence ending pattern - split on . ! ? followed by space, or , ; — followed by space
    sentence_endings = re.compile(r'([.!?]\s+|[,—;]\s+)')
    
    # Get LLM provider settings
    llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
    model = self.agent_config.get("model", "gpt-4-turbo")
    
    # Build messages with conversation history
    system_prompt = self.agent_config.get("system_prompt", "You are a helpful AI assistant.")
    
    if self.knowledge_base:
        system_prompt += f"\n\n=== KNOWLEDGE BASE ===\n{self.knowledge_base}\n=== END KNOWLEDGE BASE ===\n"
    
    messages = [
        {"role": "system", "content": system_prompt}
    ] + self.conversation_history
    
    # Get LLM client
    if llm_provider == "grok":
        client = await self.get_llm_client_for_session("grok")
    else:
        client = await self.get_llm_client_for_session("openai")
    
    if not client:
        raise Exception(f"{llm_provider} client not configured")
    
    # ⏱️ Track timing
    llm_request_start = time.time()
    
    # Stream LLM response
    if llm_provider == "grok":
        response = await client.create_completion(
            messages=messages,
            model=model,
            temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
            max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 500),
            stream=True
        )
    else:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
            max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 500),
            stream=True
        )
    
    # Process streamed chunks
    full_response = ""
    sentence_buffer = ""
    first_token_received = False
    
    async for chunk in response:
        # Track first token
        if not first_token_received:
            ttft_ms = int((time.time() - llm_request_start) * 1000)
            logger.info(f"⏱️ LLM FIRST TOKEN: {ttft_ms}ms ({llm_provider} {model})")
            first_token_received = True
        
        # Extract content from chunk
        if llm_provider == "grok":
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                else:
                    continue
            else:
                continue
        else:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
            else:
                continue
        
        full_response += content
        sentence_buffer += content
        
        # Check if we have a complete sentence
        if sentence_endings.search(sentence_buffer):
            # Split into sentences
            sentences = sentence_endings.split(sentence_buffer)
            
            # Process complete sentences (leave last incomplete one in buffer)
            for i in range(0, len(sentences) - 1, 2):
                if i < len(sentences):
                    sentence = sentences[i]
                    if i + 1 < len(sentences):
                        sentence += sentences[i + 1]  # Add delimiter
                    
                    sentence = sentence.strip()
                    if sentence and stream_callback:
                        # 🚀 Stream this sentence immediately to TTS!
                        await stream_callback(sentence)
                        logger.info(f"📤 Streamed sentence: {sentence[:50]}...")
            
            # Keep the last incomplete part in buffer
            sentence_buffer = sentences[-1] if len(sentences) % 2 != 0 else ""
    
    # Send any remaining text
    if sentence_buffer.strip() and stream_callback:
        await stream_callback(sentence_buffer.strip())
        logger.info(f"📤 Streamed final fragment: {sentence_buffer[:50]}...")
    
    # ⏱️ Total LLM response time
    llm_total_ms = int((time.time() - llm_request_start) * 1000)
    logger.info(f"⏱️ LLM_TOTAL: {llm_total_ms}ms for {len(full_response)} chars")
    
    return full_response
```

---

## Appendix C: Audio Conversion Utilities

### FFmpeg Commands Used

**PCM to MP3 (for Telnyx playback via REST API):**
```bash
ffmpeg -f s16le -ar 16000 -ac 1 -i input.pcm -b:a 64k -y output.mp3
```

**MP3 to μ-law (for Telnyx WebSocket streaming):**
```bash
ffmpeg -i input.mp3 -ar 8000 -ac 1 -f mulaw -y output.mulaw
```

### Python Implementation

```python
import subprocess
import os

async def convert_pcm_to_mp3(pcm_path: str, mp3_path: str) -> bool:
    """Convert 16kHz PCM to MP3 for Telnyx REST API playback"""
    try:
        subprocess.run([
            'ffmpeg',
            '-f', 's16le',     # Signed 16-bit little-endian PCM
            '-ar', '16000',    # 16kHz sample rate
            '-ac', '1',        # Mono
            '-i', pcm_path,    # Input file
            '-b:a', '64k',     # 64kbps bitrate
            '-y',              # Overwrite output
            mp3_path           # Output file
        ], check=True, capture_output=True, timeout=5)
        return True
    except Exception as e:
        logger.error(f"FFmpeg conversion failed: {e}")
        return False

async def convert_mp3_to_mulaw(mp3_path: str, mulaw_path: str) -> bool:
    """Convert MP3 to 8kHz μ-law for Telnyx WebSocket streaming"""
    try:
        subprocess.run([
            'ffmpeg',
            '-i', mp3_path,    # Input MP3
            '-ar', '8000',     # 8kHz sample rate (Telnyx requirement)
            '-ac', '1',        # Mono
            '-f', 'mulaw',     # μ-law format
            '-y',              # Overwrite output
            mulaw_path         # Output file
        ], check=True, capture_output=True, timeout=5)
        return True
    except Exception as e:
        logger.error(f"FFmpeg conversion failed: {e}")
        return False
```

---

## Appendix D: WebSocket Message Formats

### Telnyx WebSocket Media Message

**Sending audio to Telnyx:**
```json
{
    "event": "media",
    "media": {
        "payload": "base64_encoded_mulaw_audio"
    }
}
```

### ElevenLabs WebSocket Messages

**Sending text:**
```json
{
    "text": "Hello world",
    "try_trigger_generation": true
}
```

**Flushing (end of input):**
```json
{
    "text": "",
    "flush": true
}
```

**Receiving audio:**
```json
{
    "audio": "base64_encoded_pcm_audio",
    "isFinal": null,
    "alignment": {
        "chars": ["H", "e", "l", "l", "o"],
        "charStartTimesMs": [0, 50, 100, 150, 200]
    },
    "normalizedAlignment": {
        "chars": ["H", "e", "l", "l", "o"],
        "charStartTimesMs": [0, 50, 100, 150, 200]
    }
}
```

### Soniox WebSocket Messages

**Configuration:**
```json
{
    "api_key": "your_api_key",
    "model": "stt-rt-telephony-v3",
    "audio_format": "mulaw",
    "sample_rate": 8000,
    "num_channels": 1,
    "enable_endpoint_detection": true
}
```

**Receiving transcript:**
```json
{
    "tokens": [
        {"text": "Hello", "is_final": true},
        {"text": " world", "is_final": true},
        {"text": "<end>", "is_final": true}
    ]
}
```

---

## Appendix E: Timing Benchmarks

### Expected Latencies

| Component | Target | Typical | Notes |
|-----------|--------|---------|-------|
| Soniox STT TTFR | <200ms | 100-150ms | Time to first recognition |
| Soniox Endpoint Detection | <100ms | 50-100ms | After user stops |
| LLM TTFT | <500ms | 200-400ms | First token |
| LLM Total | <2000ms | 500-1500ms | Full response |
| ElevenLabs TTS TTFB | <200ms | 100-150ms | First audio chunk |
| FFmpeg Conversion | <100ms | 30-60ms | PCM→MP3 |
| Telnyx REST Playback | <200ms | 100-150ms | Playback start |
| **Total TTFA** | **<1000ms** | **600-800ms** | User speech → Agent audio |

### Timing Log Markers

```
⏱️ [TIMING] STT_ENDPOINT: T+0ms (user stopped speaking)
⏱️ [TIMING] TTFS: T+Xms (LLM first sentence)
⏱️ [TIMING] TTFT_TTS: T+Xms (TTS task started)
⏱️ [TIMING] TTS_TTFB: T+Xms (first audio chunk)
⏱️ [TIMING] TTS_COMPLETE: T+Xms (all chunks received)
⏱️ [TIMING] PLAYBACK_START: T+Xms (playback processing)
⏱️ [TIMING] PLAYBACK_FFMPEG: T+Xms (conversion done)
⏱️ [TIMING] PLAYBACK_TELNYX_WS: T+Xms (sent to Telnyx)
⏱️ [TIMING] TTFA: T+Xms (first audio playing)
```

---

## Appendix F: Error Handling

### Common Errors and Solutions

**1. "cannot call recv while another coroutine is already waiting"**
- **Cause:** Concurrent WebSocket access
- **Solution:** Use `asyncio.Lock()` to serialize access

```python
self._stream_lock = asyncio.Lock()

async def stream_sentence(self, sentence):
    async with self._stream_lock:
        # WebSocket operations here
```

**2. "input_timeout_exceeded"**
- **Cause:** ElevenLabs waiting for more text
- **Solution:** Always send flush after text

```python
await ws.send_text(text, flush=False)
await ws.send_text("", flush=True)  # Signal end!
```

**3. SSML tags spoken literally**
- **Cause:** Missing `enable_ssml_parsing=true`
- **Solution:** Add to WebSocket URL

```python
uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?...&enable_ssml_parsing=true"
```

**4. REST API fallback instead of WebSocket**
- **Cause:** `telnyx_ws` not passed to session
- **Solution:** Use websocket from closure

```python
persistent_tts_session = await tts_manager.create_session(
    ...,
    telnyx_ws=websocket  # From outer function!
)
```

---

## Appendix G: Environment Variables

### Required Environment Variables

```bash
# Telnyx
TELNYX_API_KEY=your_telnyx_api_key
TELNYX_CONNECTION_ID=your_connection_id

# ElevenLabs
ELEVEN_API_KEY=your_elevenlabs_api_key

# Soniox
SONIOX_API_KEY=your_soniox_api_key

# LLM (OpenAI or Grok)
OPENAI_API_KEY=your_openai_api_key
GROK_API_KEY=your_grok_api_key

# Backend
BACKEND_URL=https://your-backend-url.com
MONGO_URL=mongodb+srv://...
```

---

## Appendix H: Quick Reference

### Flow Summary

```
1. User speaks → Telnyx WebSocket → Soniox STT
2. Soniox detects endpoint → on_endpoint_detected()
3. LLM streams response → stream_callback(sentence)
4. Each sentence → persistent_tts_session.stream_sentence()
5. ElevenLabs generates audio → audio_queue
6. Playback consumer → Telnyx WebSocket (or REST)
7. User hears agent response
```

### Key Files Quick Reference

| File | Purpose |
|------|---------|
| `elevenlabs_ws_service.py` | ElevenLabs WebSocket client |
| `persistent_tts_service.py` | Session management, audio queue |
| `soniox_service.py` | STT with endpoint detection |
| `telnyx_service.py` | Call control, audio playback |
| `server.py` | Main handlers, TTS callback |
| `calling_service.py` | LLM streaming |

---

**END OF APPENDICES**

