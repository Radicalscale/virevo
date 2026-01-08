"""
Persistent TTS Service with WebSocket Streaming
Maintains persistent ElevenLabs WebSocket connections per call for ultra-low latency
Streams audio chunks immediately to eliminate batching delays
"""
import asyncio
import base64
import json
import logging
import time
import hashlib
import subprocess
import os
import re
from typing import Optional, Dict, Callable, Any
from typing import Optional, Dict, Callable, Any
import audioop
from elevenlabs_ws_service import ElevenLabsWebSocketService
from maya_tts_service import MayaTTSService
from voice_library_router import load_voice_sample

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
        telnyx_ws=None,
        voice_settings: dict = None
    ):
        self.call_control_id = call_control_id
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.telnyx_service = telnyx_service
        self.agent_config = agent_config or {}
        self.telnyx_ws = telnyx_ws  # WebSocket connection to Telnyx for streaming audio
        
        # Voice settings for ElevenLabs (controls expressiveness)
        self.voice_settings = voice_settings or {
            "stability": 0.4,  # Lower = more expressive (0.3-0.5 recommended for natural speech)
            "similarity_boost": 0.75,
            "style": 0.2,  # Slight style enhancement
            "use_speaker_boost": True
        }
        
        # WebSocket connection
        self.ws_service: Optional[ElevenLabsWebSocketService] = None
        self.connected = False
        
        # Streaming state
        self.is_streaming = False
        self.sentence_counter = 0
        self.context_id = None
        
        # 🔥 SINGLE SOURCE OF TRUTH: Is the agent currently speaking/sending audio?
        # This is set True when audio chunks start being sent to Telnyx WebSocket
        # This is set False when all audio chunks have been sent
        # 🔥 UPDATED: "is_holding_floor" - concept changed to include padding time
        self.is_holding_floor = False
        self.is_speaking = False  # Maintained for backward compatibility, syncs with is_holding_floor
        
        # 🔥 FIX: Flag to indicate if LLM response generation is complete
        # Set to False by server.py before process_user_input, True after all sentences queued
        # Prevents floor release between sentences of a multi-sentence response
        # Defaults to True (fail-safe: if not managed, floor still releases normally)
        self.generation_complete = True
        
        # 🔥 Interruption flag - when True, stop all audio sending immediately
        self.interrupted = False
        
        # Audio queue for seamless playback
        self.audio_queue = asyncio.Queue()
        self.playback_task: Optional[asyncio.Task] = None
        
        # 🔒 Lock to serialize WebSocket access (prevents concurrent recv() calls)
        self._stream_lock = asyncio.Lock()
        
        # 🏃 Pending sentences queue for decoupled sender/receiver
        # Stores metadata of sentences sent to ElevenLabs but audio not yet received:
        # (sentence_text, sentence_num, is_first, timestamp)
        self.pending_sentences = asyncio.Queue()
        
        self._audio_receiver_task: Optional[asyncio.Task] = None
        
        # ⏱️ Timing tracking
        self.first_audio_chunk_time = None
        self.request_start_time = None
        
        # 💓 Keep-alive task to prevent ElevenLabs 20-second timeout
        self._keepalive_task: Optional[asyncio.Task] = None
        
        # 🔊 Comfort noise task - sends noise when not speaking
        self._comfort_noise_task: Optional[asyncio.Task] = None
        self._comfort_noise_position = 0  # Position in comfort noise loop
        self._enable_comfort_noise = False  # Set from agent config
        
    async def _keepalive_loop(self):
        """
        Send periodic keep-alive to prevent ElevenLabs 20-second text input timeout.
        ElevenLabs closes the WebSocket if no text is received within 20 seconds.
        """
        logger.info(f"💓 [Call {self.call_control_id}] Starting TTS keep-alive loop (every 15s)")
        try:
            while self.connected:
                await asyncio.sleep(15)  # Send every 15 seconds (before 20s timeout)
                
                if not self.connected or not self.ws_service or not self.ws_service.connected:
                    logger.debug(f"💓 [Call {self.call_control_id}] Keep-alive stopping - connection closed")
                    break
                
                # Only send keep-alive if not currently streaming (to avoid interfering with real audio)
                if not self.is_streaming:
                    try:
                        # Send a single space - ElevenLabs accepts this without generating audio
                        # Using try_trigger_generation=False to prevent any audio output
                        await self.ws_service.send_text(" ", try_trigger_generation=False, flush=False)
                        logger.debug(f"💓 [Call {self.call_control_id}] TTS keep-alive sent")
                    except Exception as e:
                        logger.warning(f"💓 [Call {self.call_control_id}] Keep-alive failed: {e}")
                        # Connection likely dead - will be reconnected on next TTS request
                        break
        except asyncio.CancelledError:
            logger.debug(f"💓 [Call {self.call_control_id}] Keep-alive task cancelled")
        except Exception as e:
            logger.error(f"💓 [Call {self.call_control_id}] Keep-alive loop error: {e}")
    
    async def _comfort_noise_loop(self):
        """
        Send comfort noise chunks when agent is not speaking.
        This ensures continuous background audio throughout the call.
        """
        logger.info(f"🔊 [Call {self.call_control_id}] Starting comfort noise loop")
        
        try:
            from comfort_noise import get_comfort_noise_chunk
            chunk_size = 160  # 20ms at 8kHz mulaw
            
            while self.connected and self.telnyx_ws:
                # Only send comfort noise when NOT speaking
                if not self.is_speaking and not self.is_holding_floor:
                    try:
                        # Get a chunk of comfort noise
                        chunk = get_comfort_noise_chunk(chunk_size, self._comfort_noise_position)
                        self._comfort_noise_position += chunk_size
                        
                        # Send via Telnyx WebSocket
                        payload = base64.b64encode(chunk).decode('utf-8')
                        message = {
                            "event": "media",
                            "media": {
                                "payload": payload
                            }
                        }
                        await self.telnyx_ws.send_text(json.dumps(message))
                        
                    except Exception as e:
                        logger.debug(f"🔊 [Call {self.call_control_id}] Comfort noise send error: {e}")
                
                # 20ms per chunk = 50 chunks/second
                await asyncio.sleep(0.02)
                
        except asyncio.CancelledError:
            logger.debug(f"🔊 [Call {self.call_control_id}] Comfort noise task cancelled")
        except Exception as e:
            logger.error(f"🔊 [Call {self.call_control_id}] Comfort noise loop error: {e}")

    async def _audio_receiver_loop(self):
        """
        Background task to receive audio chunks from ElevenLabs.
        Decoupled from sending to prevent blocking LLM generation.
        """
        logger.info(f"🎧 [Call {self.call_control_id}] Audio Receiver Loop STARTED")
        try:
            while self.connected and self.ws_service:
                # Wait for a pending sentence (metadata)
                try:
                    # Wait for next sentence metadata
                    current_sentence_meta = await self.pending_sentences.get()
                    
                    sentence_text = current_sentence_meta['text']
                    sentence_num = current_sentence_meta['sentence_num']
                    is_first = current_sentence_meta['is_first']
                    send_timestamp = current_sentence_meta.get('timestamp', 0)
                    
                    # 📊 DIAGNOSTIC: Queue latency (time from send to receive start)
                    queue_latency_ms = int((time.time() - send_timestamp) * 1000) if send_timestamp else 0
                    pending_count = self.pending_sentences.qsize()
                    audio_queue_count = self.audio_queue.qsize()
                    
                    logger.info(f"🎧 [Call {self.call_control_id}] Receiver processing sentence #{sentence_num}: '{sentence_text[:30]}...'")
                    logger.info(f"📊 [Call {self.call_control_id}] DIAGNOSTIC: queue_latency={queue_latency_ms}ms, pending_sentences={pending_count}, audio_queue={audio_queue_count}, interrupted={self.interrupted}")
                    
                    chunk_count = 0
                    
                    # Receive audio chunks for this sentence
                    async for audio_chunk in self.ws_service.receive_audio_chunks():
                        chunk_count += 1
                        
                        # Stop processing chunks if interrupted
                        if self.interrupted:
                            logger.info(f"🛑 [Call {self.call_control_id}] Receiver discarding chunk for sentence #{sentence_num} (INTERRUPTED)")
                            continue

                        # Add to playback queue
                        await self.audio_queue.put({
                            'sentence': sentence_text,
                            'audio_data': audio_chunk,
                            'format': 'mulaw',
                            'sentence_num': sentence_num,
                            'is_first': is_first and chunk_count == 1
                        })
                    
                    if chunk_count > 0:
                        total_receive_time_ms = int((time.time() - send_timestamp) * 1000) if send_timestamp else 0
                        logger.info(f"✅ [Call {self.call_control_id}] Receiver finished sentence #{sentence_num}: {chunk_count} chunks in {total_receive_time_ms}ms")
                    else:
                        logger.warning(f"⚠️ [Call {self.call_control_id}] Receiver got 0 chunks for sentence #{sentence_num}! interrupted={self.interrupted}")
                    
                    # Mark sentence as done in queue
                    self.pending_sentences.task_done()
                    
                except asyncio.CancelledError:
                    logger.info(f"🛑 [Call {self.call_control_id}] Audio Receiver Loop CANCELLED")
                    break
                except Exception as e:
                    logger.error(f"❌ [Call {self.call_control_id}] Error in Audio Receiver Loop: {e}")
                    # Brief sleep to prevent tight loops on error
                    await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"❌ [Call {self.call_control_id}] Audio Receiver Loop CRASHED: {e}")
        finally:
            logger.info(f"👋 [Call {self.call_control_id}] Audio Receiver Loop STOPPED")

        
    async def connect(self) -> bool:
        """
        Establish persistent WebSocket connection to ElevenLabs
        Connection stays open for entire call duration
        """
        try:
            logger.info(f"🔌 [Call {self.call_control_id}] Establishing persistent TTS WebSocket...")
            logger.info(f"🎙️ [Call {self.call_control_id}] Voice settings: {self.voice_settings}")
            
            # Create WebSocket service
            self.ws_service = ElevenLabsWebSocketService(self.api_key)
            
            # Connect with optimized settings for streaming + voice settings
            connected = await self.ws_service.connect(
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format="ulaw_8000",  # 🔥 NATIVE STREAMING: Direct ulaw output
                voice_settings=self.voice_settings
            )
            
            if connected:
                self.connected = True
                logger.info(f"✅ [Call {self.call_control_id}] Persistent TTS WebSocket established")
                
                # Start playback consumer
                self.playback_task = asyncio.create_task(self._playback_consumer())
                
                # 🎧 Start audio receiver loop (Decoupled from sender)
                self._audio_receiver_task = asyncio.create_task(self._audio_receiver_loop())
                logger.info(f"🎧 [Call {self.call_control_id}] Audio receiver loop started")
                
                # 💓 Start keep-alive loop to prevent 20-second timeout
                self._keepalive_task = asyncio.create_task(self._keepalive_loop())
                
                # 🔊 Check if comfort noise is enabled and start the loop
                agent_settings = self.agent_config.get("settings", {})
                self._enable_comfort_noise = agent_settings.get("enable_comfort_noise", False)
                if self._enable_comfort_noise and self.telnyx_ws:
                    self._comfort_noise_task = asyncio.create_task(self._comfort_noise_loop())
                    logger.info(f"🔊 [Call {self.call_control_id}] Comfort noise loop started")
                
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
            
            # Cancel existing keep-alive task
            if self._keepalive_task:
                self._keepalive_task.cancel()
                try:
                    await self._keepalive_task
                except asyncio.CancelledError:
                    pass
                self._keepalive_task = None
            
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
                output_format="ulaw_8000"
            )
            
            if connected:
                self.connected = True
                logger.info(f"✅ [Call {self.call_control_id}] TTS WebSocket reconnected")
                
                # 💓 Restart keep-alive loop
                self._keepalive_task = asyncio.create_task(self._keepalive_loop())
                
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
        is_last: bool = False,
        current_voice_id: str = None
    ) -> bool:
        """
        Stream a sentence through the persistent WebSocket
        Audio chunks are received and played immediately (no batching)
        
        Args:
            sentence: Text to synthesize
            is_first: If True, this is the first sentence of the response
            is_last: If True, this is the last sentence and should flush
            current_voice_id: If provided, check if voice has changed and reconnect if needed
            
        Returns:
            bool: True if streaming started successfully
        """
        # 🔥 DYNAMIC VOICE CHECK: If voice ID has changed, reconnect with new voice
        if current_voice_id and current_voice_id != self.voice_id:
            logger.info(f"🎙️ [Call {self.call_control_id}] VOICE CHANGE DETECTED: {self.voice_id[:8]}... → {current_voice_id[:8]}...")
            self.voice_id = current_voice_id
            # Force reconnection with new voice
            reconnected = await self._reconnect()
            if not reconnected:
                logger.error(f"❌ [Call {self.call_control_id}] Failed to reconnect with new voice, aborting sentence")
                return False
            logger.info(f"✅ [Call {self.call_control_id}] Reconnected with new voice: {current_voice_id[:8]}...")
        
        # 🔥 CRITICAL FIX: Reset interrupt flag FIRST if this is a new response
        # This MUST happen before checking the flag, otherwise we can never recover from interruption
        if is_first:
            if self.interrupted:
                logger.info(f"🔄 [Call {self.call_control_id}] NEW RESPONSE starting - clearing interrupted flag (was True)")
            self.interrupted = False
        
        # Now check if we should skip (only blocks mid-response sentences during active interruption)
        if self.interrupted:
            logger.info(f"🛑 [Call {self.call_control_id}] Skipping mid-response sentence '{sentence[:30]}...' - interrupted flag set")
            return False
        
        # 🔒 CRITICAL: Acquire lock to serialize WebSocket access
        # This prevents concurrent recv() calls which cause "cannot call recv while another coroutine is already waiting" errors
        async with self._stream_lock:
            # Check if reconnection is needed
            if not self.connected or not self.ws_service or not self.ws_service.connected:
                logger.warning(f"⚠️ [Call {self.call_control_id}] TTS WebSocket disconnected, attempting reconnection...")
                # Attempt to reconnect
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
                
                # 🚀 DECOUPLED: Push to pending queue and return IMMEDIATELY
                # The _audio_receiver_loop will handle the reception in background
                await self.pending_sentences.put({
                    'text': sentence,
                    'sentence_num': sentence_num,
                    'is_first': is_first,
                    'timestamp': time.time()
                })
                
                # 📊 DIAGNOSTIC: Show queue state on send
                pending_count = self.pending_sentences.qsize()
                audio_queue_count = self.audio_queue.qsize()
                send_time_ms = int((time.time() - stream_start) * 1000)
                
                logger.info(f"🚀 [Call {self.call_control_id}] Sent sentence #{sentence_num} (NON-BLOCKING) in {send_time_ms}ms")
                logger.info(f"📊 [Call {self.call_control_id}] DIAGNOSTIC: pending_sentences={pending_count}, audio_queue={audio_queue_count}, is_first={is_first}, is_last={is_last}")
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
                    audio_data=audio_item.get('audio_data'),
                    audio_pcm=audio_item.get('audio_pcm'), # Legacy
                    format=audio_item.get('format', 'pcm'), # Default to PCM (legacy)
                    sentence_num=audio_item['sentence_num'],
                    is_first=audio_item['is_first']
                )
                
                self.audio_queue.task_done()
                
        except Exception as e:
            logger.error(f"❌ [Call {self.call_control_id}] Error in playback consumer: {e}")
    
    async def _play_audio_chunk(
        self,
        sentence: str,
        audio_data: Optional[bytes],
        audio_pcm: Optional[bytes],
        format: str,
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
            
            
            # 🔥 FAST PATH: Native Mulaw Streaming (No FFmpeg)
            if format == 'mulaw' and audio_data:
                # logger.info(f"🚀 [Call {self.call_control_id}] Fast-path: Sending {len(audio_data)} bytes mulaw directly")
                await self._send_audio_via_websocket(audio_data=audio_data)
                return

            # --- LEGACY PCM PATH (Below) ---
            if not audio_pcm: 
                return

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
                success = await self._send_audio_via_websocket(mp3_path=mp3_path)
                telnyx_ms = int((time.time() - telnyx_start) * 1000)
                logger.info(f"⏱️ [TIMING] PLAYBACK_TELNYX_WS: {telnyx_ms}ms")
                
                total_time = (time.time() - play_start) * 1000
                logger.info(f"⏱️ [TIMING] PLAYBACK_TOTAL: {total_time:.0f}ms")
                
                if success:
                    logger.info(f"🔊 [Call {self.call_control_id}] Sentence #{sentence_num} SENT VIA WEBSOCKET ({total_time:.0f}ms total): {sentence[:50]}...")
                    
                    if is_first:
                        logger.info(f"⏱️ [TIMING] FIRST_AUDIO_PLAYING: First sentence started playing on phone")
                        logger.info(f"⏱️  [Call {self.call_control_id}] 🚀 FIRST SENTENCE STARTED PLAYING")
                    
                    # 🔥 THROTTLE: Wait for most of this audio to play before allowing next sentence
                    # This prevents building up a massive buffer at Telnyx that can't be cleared
                    # Get audio duration from the session tracking
                    from server import call_states
                    if self.call_control_id in call_states:
                        expected_end = call_states[self.call_control_id].get("playback_expected_end_time", 0)
                        current_time = time.time()
                        buffer_ahead = expected_end - current_time
                        
                        # If we're buffered more than 2 seconds ahead, wait
                        # This limits how much audio is "in flight" that can't be cleared
                        MAX_BUFFER_AHEAD = 2.0  # seconds
                        if buffer_ahead > MAX_BUFFER_AHEAD:
                            wait_time = buffer_ahead - MAX_BUFFER_AHEAD
                            logger.info(f"⏳ [Call {self.call_control_id}] Buffer throttle: waiting {wait_time:.1f}s (buffer: {buffer_ahead:.1f}s ahead)")
                            
                            # Wait in small increments, checking interrupted flag
                            wait_remaining = wait_time
                            while wait_remaining > 0 and not self.interrupted:
                                await asyncio.sleep(min(0.1, wait_remaining))
                                wait_remaining -= 0.1
                            
                            if self.interrupted:
                                logger.info(f"🛑 [Call {self.call_control_id}] Buffer throttle wait interrupted")
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
    
    async def _send_audio_via_websocket(self, mp3_path: str = None, audio_data: bytes = None) -> bool:
        """
        Send audio via Telnyx WebSocket
        Supports both legacy MP3 path (converts to mulaw) and new direct mulaw bytes
        """
        try:
            if audio_data:
                # 🔥 FAST PATH: Direct Mulaw bytes
                mulaw_data = audio_data
            
            elif mp3_path:
                # 🐢 SLOW PATH: Convert MP3 to mulaw
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
            
            else:
                return False
            
            # Send audio in chunks (Telnyx expects ~20ms chunks = 160 bytes at 8kHz)
            chunk_size = 160  # 20ms at 8kHz mulaw
            total_chunks = (len(mulaw_data) + chunk_size - 1) // chunk_size
            
            # 🔥 Calculate ACTUAL audio duration from mulaw data size
            # At 8kHz sample rate with mulaw (1 byte per sample):
            actual_duration_seconds = len(mulaw_data) / 8000.0
            logger.info(f"📤 Sending {len(mulaw_data)} bytes of audio ({total_chunks} chunks, {actual_duration_seconds:.1f}s duration) via WebSocket")
            
            # 🔊 SINGLE SOURCE OF TRUTH: Mark agent as speaking BEFORE sending audio
            self.is_speaking = True
            logger.info(f"🎙️ [Call {self.call_control_id}] AGENT IS NOW SPEAKING (is_speaking=True)")
            
            # 🔥 CRITICAL FIX: EXTEND playback_expected_end_time instead of overwriting
            # With WebSocket streaming, audio chunks are queued sequentially.
            # Each new chunk plays AFTER the previous ones finish, so we must
            # EXTEND the expected end time, not reset it to just this chunk's duration.
            # Bug: Previously, each chunk overwrote the time causing premature dead-air triggers
            from server import call_states
            if self.call_control_id in call_states:
                current_expected_end = call_states[self.call_control_id].get("playback_expected_end_time", 0)
                current_time = time.time()
                
                # If there's already audio playing (expected end is in the future),
                # extend from that point. Otherwise, start from now.
                base_time = max(current_expected_end, current_time)
                
                # Audio expected end = just the actual audio duration, no padding
                new_expected_end = base_time + actual_duration_seconds
                
                call_states[self.call_control_id]["playback_expected_end_time"] = new_expected_end
                
                # Sync flags
                self.is_holding_floor = True
                self.is_speaking = True
                
                time_until_end = new_expected_end - current_time
                logger.info(f"⏱️ EXTEND playback_expected_end_time: +{actual_duration_seconds:.1f}s (total: {time_until_end:.1f}s from now)")
            
            for i in range(0, len(mulaw_data), chunk_size):
                # 🔥 CHECK INTERRUPTED FLAG - stop immediately if user interrupted
                if self.interrupted:
                    logger.info(f"🛑 [Call {self.call_control_id}] Audio sending STOPPED at chunk {i//chunk_size}/{total_chunks} due to interruption")
                    # Mark agent as NOT speaking since we stopped
                    self.is_speaking = False
                    logger.info(f"🔇 [Call {self.call_control_id}] AGENT STOPPED SPEAKING (interrupted, is_speaking=False)")
                    return False
                
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
            
            # 🔊 Schedule automatic is_speaking=False when audio playback is expected to finish
            # Use playback_expected_end_time as source of truth (accounts for ALL queued audio)
            async def reset_speaking_after_playback():
                try:
                    from server import call_states
                    while True:
                        if self.call_control_id not in call_states:
                            break
                        
                        expected_end = call_states[self.call_control_id].get("playback_expected_end_time", 0)
                        current_time = time.time()
                        time_remaining = expected_end - current_time
                        
                        if time_remaining <= 0:
                            # 🔥 FIX: Only release floor if generation is complete
                            # This prevents premature release between sentences
                            if not self.generation_complete:
                                # More sentences may be coming, wait a bit longer
                                await asyncio.sleep(0.2)
                                continue  # Recheck time_remaining after new audio arrives
                            
                            # All audio should have finished playing AND no more coming
                            if not self.interrupted and self.is_holding_floor:
                                self.is_holding_floor = False
                                self.is_speaking = False
                                logger.info(f"🔇 [Call {self.call_control_id}] FLOOR RELEASED (is_holding_floor=False)")
                            break
                        
                        # Wait in small increments to allow for interruption
                        await asyncio.sleep(min(0.5, time_remaining + 0.3))
                        
                        # Check if interrupted
                        if self.interrupted:
                            break
                            
                except asyncio.CancelledError:
                    pass  # Task was cancelled (e.g., call ended)
                except Exception as e:
                    logger.error(f"❌ Error in reset_speaking_after_playback: {e}")
            
            # Only start the timer if there isn't one already running
            # This prevents the timer from being reset for each sentence
            if not hasattr(self, '_speaking_timer_task') or self._speaking_timer_task is None or self._speaking_timer_task.done():
                self._speaking_timer_task = asyncio.create_task(reset_speaking_after_playback())
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ ffmpeg timeout converting to mulaw")
            self.is_speaking = False  # Error = not speaking
            return False
        except Exception as e:
            logger.error(f"❌ Error sending audio via WebSocket: {e}")
            self.is_speaking = False  # Error = not speaking
            return False
    
    async def clear_audio(self):
        """
        Clear/stop any buffered audio in Telnyx WebSocket.
        Call this when user interrupts.
        """
        try:
            # 📊 DIAGNOSTIC: Log queue state at interruption time
            pending_count = self.pending_sentences.qsize()
            audio_queue_count = self.audio_queue.qsize()
            logger.info(f"⚡ [Call {self.call_control_id}] CLEAR_AUDIO called - pending_sentences={pending_count}, audio_queue={audio_queue_count}")
            
            # 🔥 Set interrupted flag FIRST to stop any ongoing audio sending loops
            self.interrupted = True
            
            # 🔥 FIX: Mark generation as complete so floor releases immediately
            self.generation_complete = True
            
            # 🔊 SINGLE SOURCE OF TRUTH: Agent is no longer speaking
            self.is_holding_floor = False
            self.is_speaking = False
            logger.info(f"🛑 [Call {self.call_control_id}] INTERRUPT - Floor Released (is_holding_floor=False)")
            
            # Cancel any pending speaking timer
            if hasattr(self, '_speaking_timer_task') and self._speaking_timer_task:
                self._speaking_timer_task.cancel()
                self._speaking_timer_task = None
            
            if self.telnyx_ws:
                # 🔥 CRITICAL: Send clear event MULTIPLE times to ensure it's processed
                # Sometimes a single clear event may not be enough if there's a race condition
                message = {"event": "clear"}
                for _ in range(3):  # Send 3 times for reliability
                    try:
                        await self.telnyx_ws.send_text(json.dumps(message))
                    except:
                        break
                    await asyncio.sleep(0.01)  # Small delay between sends
                
                logger.info(f"🛑 [Call {self.call_control_id}] Sent clear event to Telnyx WebSocket (3x)")
                
                # Clear any pending audio in our internal queue
                cleared_queue = 0
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                        cleared_queue += 1
                    except asyncio.QueueEmpty:
                        break
                
                if cleared_queue > 0:
                    logger.info(f"🗑️ [Call {self.call_control_id}] Cleared {cleared_queue} pending audio chunks from queue")
                
                # Reset playback tracking
                self.is_playing = False
                self.current_sentence_start = None
                
                # Reset playback_expected_end_time to NOW
                from server import call_states
                if self.call_control_id in call_states:
                    call_states[self.call_control_id]["playback_expected_end_time"] = time.time()
                    logger.info(f"⏱️ [Call {self.call_control_id}] Reset playback_expected_end_time to NOW")
                
                return True
            else:
                logger.warning(f"⚠️ [Call {self.call_control_id}] No Telnyx WebSocket to clear")
                return False
        except Exception as e:
            logger.error(f"❌ [Call {self.call_control_id}] Error clearing audio: {e}")
            return False
    
    def reset_interrupt_flag(self):
        """Reset the interrupted flag when starting a new response"""
        self.interrupted = False
        logger.info(f"🔄 [Call {self.call_control_id}] Interrupt flag reset - ready for new audio")
    
    def cancel_pending_sentences(self):
        """
        Cancel any sentences waiting to be streamed.
        Call this on interruption to prevent queued sentences from playing.
        """
        # Clear the audio queue
        cleared_count = 0
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                cleared_count += 1
            except asyncio.QueueEmpty:
                break
        
        if cleared_count > 0:
            logger.info(f"🗑️ [Call {self.call_control_id}] Cancelled {cleared_count} pending audio chunks")
            
        # 🏃 Clear pending sentences queue (Decoupled receiver)
        cleared_sentences = 0
        while not self.pending_sentences.empty():
            try:
                self.pending_sentences.get_nowait()
                self.pending_sentences.task_done()
                cleared_sentences += 1
            except asyncio.QueueEmpty:
                break
        
        if cleared_sentences > 0:
            logger.info(f"🗑️ [Call {self.call_control_id}] Cancelled {cleared_sentences} pending sentences (sender queue)")
        
        return cleared_count
    
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
        
        # 💓 Cancel keep-alive task first
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None
        
        # 🎧 Cancel audio receiver task
        if self._audio_receiver_task:
            self._audio_receiver_task.cancel()
            try:
                await self._audio_receiver_task
            except asyncio.CancelledError:
                pass
            self._audio_receiver_task = None
        
        # 🔊 Cancel comfort noise task
        if self._comfort_noise_task:
            self._comfort_noise_task.cancel()
            try:
                await self._comfort_noise_task
            except asyncio.CancelledError:
                pass
            self._comfort_noise_task = None
        
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


class MayaPersistentSession(PersistentTTSSession):
    """
    Manages persistent streaming for Maya TTS
    Uses HTTP Chunked Streaming (not WebSocket) but maintains session interface
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maya_service = MayaTTSService()
        
        # Extract Maya specific settings
        settings = self.agent_config.get("settings", {})
        maya_settings = settings.get("maya_settings", {})
        
        self.voice_ref = maya_settings.get("voice_ref", "default")
        self.temperature = maya_settings.get("temperature", 0.35)
        self.seed = maya_settings.get("seed", 0)
        self.speaker_wav_id = maya_settings.get("speaker_wav_id")
        self.speaker_wav = None
        self.resample_state = None # For 24k -> 8k resampling

    async def connect(self) -> bool:
        """
        Mock connection for Maya (since it's HTTP based)
        But we use this to preload voice sample if needed
        """
        logger.info(f"🔌 [Call {self.call_control_id}] Initializing Maya TTS Session...")
        
        if self.speaker_wav_id:
            try:
                self.speaker_wav = await load_voice_sample(self.speaker_wav_id)
                logger.info(f"✅ [Call {self.call_control_id}] Loaded voice clone sample: {self.speaker_wav_id}")
            except Exception as e:
                logger.warning(f"⚠️ [Call {self.call_control_id}] Failed to load voice sample: {e}")
        
        self.connected = True
        
        # Start keep-alive loop (Maya doesn't need it but good for consistency)
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        
        # Start comfort noise if enabled
        agent_settings = self.agent_config.get("settings", {})
        self._enable_comfort_noise = agent_settings.get("enable_comfort_noise", False)
        if self._enable_comfort_noise and self.telnyx_ws:
            self._comfort_noise_task = asyncio.create_task(self._comfort_noise_loop())
            logger.info(f"🔊 [Call {self.call_control_id}] Comfort noise loop started")
            
        return True

    async def _keepalive_loop(self):
        # Maya doesn't need keepalive, but we keep the method to satisfy interface
        # and maybe send silence to Telnyx to keep that connection alive
        pass

    async def stream_sentence(
        self,
        sentence: str,
        is_first: bool = False,
        is_last: bool = False,
        current_voice_id: str = None
    ) -> bool:
        """
        Stream from Maya TTS -> Convert to Mulaw -> Send to Telnyx WS
        """
        # Maya "voice_id" is actually the description or voice_ref
        # Logic to update voice if needed (omitted for now to keep simple)
        
        if is_first:
            self.interrupted = False
            self.is_holding_floor = True
            
        if self.interrupted:
            return False

        try:
            # We don't use 'voice_id' param from args as Maya uses self.voice_ref or self.speaker_wav
            # But if current_voice_id is passed and differs, we could update self.voice_ref
            
            logger.info(f"🎤 [Maya] Streaming sentence: '{sentence[:30]}...'")
            self.is_speaking = True
            
            chunk_count = 0
            start_time = time.time()
            
            stream = self.maya_service.stream_speech(
                text=sentence,
                voice_ref=self.voice_ref,
                temperature=self.temperature,
                seed=self.seed,
                speaker_wav=self.speaker_wav
            )
            
            async for chunk in stream:
                if self.interrupted:
                    logger.info("🛑 [Maya] Interrupted during streaming")
                    break
                    
                if chunk:
                    try:
                        # Convert PCM to Mulaw with Resampling (24k -> 8k)
                        # We assume Maya outputs 24000Hz 16-bit PCM
                        
                        # Resample 24k -> 8k
                        # chunk, width=2, channels=1, inrate=24000, outrate=8000
                        fragment, self.resample_state = audioop.ratecv(chunk, 2, 1, 24000, 8000, self.resample_state)
                        
                        # Convert to u-law
                        mulaw_chunk = audioop.lin2ulaw(fragment, 2) 
                        
                        payload = base64.b64encode(mulaw_chunk).decode('utf-8')
                        
                        if self.telnyx_ws:
                            msg = {
                                "event": "media",
                                "media": {
                                    "payload": payload
                                }
                            }
                            await self.telnyx_ws.send_text(json.dumps(msg))
                            chunk_count += 1
                    except Exception as e:
                        logger.error(f"Error converting/sending audio: {e}")

            duration = time.time() - start_time
            logger.info(f"✅ [Maya] Streamed {chunk_count} chunks in {duration:.2f}s")

        except Exception as e:
            logger.error(f"❌ [Maya] Streaming error: {e}")
            return False
        finally:
            if is_last:
                self.is_speaking = False
                self.is_holding_floor = False
        
        return True

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
        telnyx_ws=None,
        voice_settings: dict = None
    ) -> Optional[PersistentTTSSession]:
        """
        Create and connect a new persistent TTS session for a call
        
        voice_settings dict can include:
            - stability (0.0-1.0): Lower = more expressive, Higher = more monotone
            - similarity_boost (0.0-1.0): Voice similarity to original
            - style (0.0-1.0): Style exaggeration (v2 models only)
            - use_speaker_boost (bool): Enhance clarity
        """
        if call_control_id in self.sessions:
            logger.warning(f"⚠️  Session already exists for call {call_control_id}")
            return self.sessions[call_control_id]
        
        # Extract voice_settings from agent_config if not provided directly
        if voice_settings is None and agent_config:
            elevenlabs_settings = agent_config.get("settings", {}).get("elevenlabs_settings", {})
            voice_settings = {
                "stability": elevenlabs_settings.get("stability", 0.4),
                "similarity_boost": elevenlabs_settings.get("similarity_boost", 0.75),
                "style": elevenlabs_settings.get("style", 0.2),
                "use_speaker_boost": elevenlabs_settings.get("use_speaker_boost", True)
            }
            logger.info(f"🎙️ Extracted voice_settings from agent config: {voice_settings}")
        
        # Check for Maya provider
        settings = agent_config.get("settings", {}) if agent_config else {}
        tts_provider = settings.get("tts_provider", "elevenlabs")
        
        if tts_provider == "maya":
            session = MayaPersistentSession(
                call_control_id=call_control_id,
                api_key=api_key, # API key handled internally by MayaTTSService env vars
                voice_id=voice_id, # Handled via maya settings
                telnyx_service=telnyx_service,
                agent_config=agent_config,
                telnyx_ws=telnyx_ws
            )
            logger.info(f"✨ Created Maya persistent session for call {call_control_id}")
        else:
            session = PersistentTTSSession(
                call_control_id=call_control_id,
                api_key=api_key,
                voice_id=voice_id,
                model_id=model_id,
                telnyx_service=telnyx_service,
                agent_config=agent_config,
                telnyx_ws=telnyx_ws,
                voice_settings=voice_settings
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
