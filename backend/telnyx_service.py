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
    
    async def get_recording(self, recording_id: str) -> Dict[str, Any]:
        """Get recording details and download content"""
        try:
            logger.info(f"🎵 Fetching recording: {recording_id}")
            
            # Retrieve recording from Telnyx
            recording = self.client.recordings.retrieve(recording_id)
            
            # Extract download URLs from the response structure
            recording_url = None
            
            # The recording object has a 'data' attribute with the actual recording data
            if hasattr(recording, 'data'):
                recording_data = recording.data
                if hasattr(recording_data, 'download_urls'):
                    download_urls = recording_data.download_urls
                    # download_urls is an object with mp3 and wav attributes
                    if hasattr(download_urls, 'mp3') and download_urls.mp3:
                        recording_url = download_urls.mp3
                        logger.info(f"✅ Found fresh MP3 URL")
                    elif hasattr(download_urls, 'wav') and download_urls.wav:
                        recording_url = download_urls.wav
                        logger.info(f"✅ Found fresh WAV URL")
            
            # Download the recording content
            import httpx
            recording_content = None
            if recording_url:
                logger.info(f"🔽 Attempting to download from: {recording_url[:100]}...")
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(recording_url, timeout=30.0)
                        logger.info(f"📥 Download response: HTTP {response.status_code}")
                        if response.status_code == 200:
                            recording_content = response.content
                            logger.info(f"✅ Downloaded recording: {len(recording_content)} bytes")
                        else:
                            logger.warning(f"⚠️ Failed to download recording: HTTP {response.status_code}, URL might be expired")
                except Exception as e:
                    logger.error(f"❌ Error downloading recording: {e}")
            else:
                logger.warning("⚠️ No recording URL found in Telnyx response")
            
            return {
                "success": True,
                "recording_id": recording_id,
                "content": recording_content,
                "content_type": "audio/mpeg" if "mp3" in str(recording_url) else "audio/wav"
            }
        except Exception as e:
            logger.error(f"❌ Error fetching recording: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_dtmf(self, call_control_id: str, digits: str) -> Dict[str, Any]:
        """Send DTMF tones"""
        try:
            self.client.calls.actions.send_dtmf(
                call_control_id=call_control_id,
                digits=digits
            )
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error sending DTMF: {e}")
            return {"success": False, "error": str(e)}
    
    async def bridge_calls(
        self,
        call_control_id: str,
        other_call_control_id: str
    ) -> Dict[str, Any]:
        """Bridge two calls together (for transfers)"""
        try:
            logger.info(f"🔗 Bridging calls: {call_control_id} <-> {other_call_control_id}")
            
            self.client.calls.actions.bridge(
                call_control_id=call_control_id,
                other_call_control_id=other_call_control_id
            )
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error bridging calls: {e}")
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
    
    async def speak_text(
        self,
        call_control_id: str,
        text: str,
        voice: str = "female",
        language: str = "en-US",
        agent_config: dict = None,
        use_websocket_tts: bool = None
    ) -> Dict[str, Any]:
        """
        Convert text to speech and play on the call
        Uses configured TTS provider (ElevenLabs/Hume/Sesame) if agent_config provided,
        otherwise falls back to Telnyx built-in TTS
        
        Args:
            use_websocket_tts: If True, use WebSocket streaming (faster). If None, auto-detect based on provider.
        """
        try:
            # Clean SSML tags from text before TTS
            import re
            text = re.sub(r'<[^>]+>', '', text)  # Remove all XML/SSML tags
            text = text.strip()
            
            if not text:
                logger.warning("⚠️  Text is empty after SSML cleaning, skipping TTS")
                return {"success": False, "error": "Empty text"}
            
            logger.info(f"🔊 Speaking text on call {call_control_id}: {text[:50]}...")
            logger.info(f"🔍 Agent config provided: {agent_config is not None}")
            
            # Check if we should use external TTS (ElevenLabs/Hume/Sesame)
            if agent_config:
                settings = agent_config.get("settings", {})
                tts_provider = settings.get("tts_provider", "elevenlabs")
                logger.info(f"🔍 TTS provider from settings: {tts_provider}")
                
                # Auto-enable WebSocket for Sesame if not explicitly set
                if use_websocket_tts is None:
                    use_websocket_tts = (tts_provider == "sesame")
                
                logger.info(f"🔍 WebSocket TTS: {use_websocket_tts}")
                
                # Try WebSocket TTS first if enabled (ElevenLabs and Sesame)
                if use_websocket_tts and tts_provider in ["elevenlabs", "sesame"]:
                    try:
                        if tts_provider == "sesame":
                            result = await self._speak_text_websocket_sesame(call_control_id, text, agent_config)
                        else:
                            result = await self._speak_text_websocket(call_control_id, text, agent_config)
                        
                        if result.get("success"):
                            return result
                        else:
                            logger.warning(f"⚠️  WebSocket TTS ({tts_provider}) failed, falling back to REST")
                    except Exception as e:
                        logger.warning(f"⚠️  WebSocket TTS ({tts_provider}) error, falling back to REST: {e}")
                
                # Try to use external TTS if provider is set (REST API)
                if tts_provider in ["elevenlabs", "hume", "sesame", "cartesia"]:
                    logger.info(f"🎙️ Attempting {tts_provider} TTS (REST)")
                    
                    try:
                        from server import generate_tts_audio
                        import hashlib
                        import os
                        import time
                        
                        tts_start = time.time()
                        
                        # Generate audio using configured provider
                        audio_bytes = await generate_tts_audio(text, agent_config)
                        
                        tts_gen_time = time.time() - tts_start
                        logger.info(f"⏱️  TTS generation time: {tts_gen_time:.2f}s")
                        
                        if audio_bytes and len(audio_bytes) > 1000:
                            # Save audio to temporary file
                            audio_hash = hashlib.md5(text.encode()).hexdigest()
                            audio_filename = f"tts_{audio_hash}.mp3"
                            audio_path = f"/tmp/{audio_filename}"
                            
                            with open(audio_path, 'wb') as f:
                                f.write(audio_bytes)
                            
                            logger.info(f"✅ Generated {len(audio_bytes)} bytes, saved to {audio_path}")
                            
                            # Get backend URL for serving the audio
                            backend_url = os.environ.get('BACKEND_URL', 'https://api.li-ai.org')
                            audio_url = f"{backend_url}/api/tts-audio/{audio_filename}"
                            
                            logger.info(f"🔗 Using audio URL: {audio_url}")
                            
                            playback_start = time.time()
                            
                            # Use Telnyx REST API directly for playback_start
                            import httpx
                            import os
                            
                            telnyx_api_key = os.environ.get('TELNYX_API_KEY')
                            playback_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/playback_start"
                            
                            async with httpx.AsyncClient() as http_client:
                                response = await http_client.post(
                                    playback_url,
                                    headers={
                                        "Authorization": f"Bearer {telnyx_api_key}",
                                        "Content-Type": "application/json"
                                    },
                                    json={"audio_url": audio_url}
                                )
                                
                                playback_time = time.time() - playback_start
                                logger.info(f"⏱️  Playback API call time: {playback_time:.2f}s")
                                
                                if response.status_code in [200, 201, 202]:
                                    total_time = time.time() - tts_start
                                    logger.info(f"⏱️  Total TTS latency: {total_time:.2f}s")
                                    logger.info(f"✅ Playing {tts_provider} audio via Telnyx playback")
                                    
                                    # Extract playback_id from response for interruption handling
                                    try:
                                        response_data = response.json()
                                        playback_id = response_data.get("data", {}).get("playback_id")
                                        if playback_id:
                                            logger.info(f"🎬 Playback ID: {playback_id}")
                                            return {"success": True, "playback_id": playback_id}
                                    except:
                                        pass
                                    
                                    return {"success": True}
                                else:
                                    logger.error(f"❌ Telnyx playback failed: {response.status_code} - {response.text}")
                            
                    except Exception as e:
                        logger.error(f"Error with {tts_provider} TTS: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
            else:
                logger.info("ℹ️  No agent_config provided")
            
            # Use Telnyx built-in TTS
            logger.info("📢 Using Telnyx built-in TTS")
            self.client.calls.actions.speak(
                call_control_id=call_control_id,
                payload=text,
                voice=voice,
                language=language
            )
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error speaking text: {e}")
            return {"success": False, "error": str(e)}
    
    async def _speak_text_websocket(
        self,
        call_control_id: str,
        text: str,
        agent_config: dict
    ) -> Dict[str, Any]:
        """
        WebSocket-based TTS streaming (OPTIMIZED - no pydub)
        Streams audio chunks as they're generated for lower perceived latency
        
        Args:
            call_control_id: Telnyx call control ID
            text: Text to synthesize
            agent_config: Agent configuration with voice settings
            
        Returns:
            Dict with success status and playback_id
        """
        try:
            from elevenlabs_ws_service import ElevenLabsWebSocketService
            from server import get_api_key, db, ELEVEN_API_KEY
            import hashlib
            import os
            import time
            import subprocess
            
            logger.info("🚀 Using WebSocket TTS (optimized - fast conversion)")
            
            tts_start = time.time()
            
            # Get voice settings
            settings = agent_config.get("settings", {})
            voice_id = settings.get("elevenlabs_settings", {}).get("voice_id", "J5iaaqzR5zn6HFG4jV3b")
            model_id = settings.get("elevenlabs_settings", {}).get("model", "eleven_flash_v2_5")
            
            # Get API key from database or environment (matching REST API logic)
            elevenlabs_api_key = await get_api_key("elevenlabs") or ELEVEN_API_KEY
            
            if not elevenlabs_api_key:
                logger.error("❌ ElevenLabs API key not found in database or environment")
                return {"success": False, "error": "Missing API key"}
            
            # Initialize WebSocket service
            ws_service = ElevenLabsWebSocketService(elevenlabs_api_key)
            
            # Connect with PCM output format (better for streaming)
            connected = await ws_service.connect(
                voice_id=voice_id,
                model_id=model_id,
                output_format="pcm_16000"  # 16kHz PCM
            )
            
            if not connected:
                return {"success": False, "error": "WebSocket connection failed"}
            
            # CRITICAL: Send BOS message with voice_settings FIRST
            stability = settings.get("elevenlabs_settings", {}).get("stability", 0.5)
            similarity_boost = settings.get("elevenlabs_settings", {}).get("similarity_boost", 0.75)
            
            bos_message = {
                "text": " ",  # Space to initialize the stream
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost
                },
                "generation_config": {
                    "chunk_length_schedule": [120, 160, 250, 290]
                }
            }
            await ws_service.websocket.send(json.dumps(bos_message))
            
            # Now send the actual text
            await ws_service.send_text(text, try_trigger_generation=True)
            await ws_service.send_end_of_stream()
            
            # Collect audio chunks
            audio_chunks = []
            first_chunk_time = None
            
            async for audio_chunk in ws_service.receive_audio_chunks():
                if first_chunk_time is None:
                    first_chunk_time = time.time()
                    ttfb = first_chunk_time - tts_start
                    logger.info(f"⚡ WebSocket TTFB: {ttfb*1000:.0f}ms")
                
                audio_chunks.append(audio_chunk)
            
            # Close connection
            await ws_service.close()
            
            if not audio_chunks:
                logger.error("❌ No audio chunks received from WebSocket")
                return {"success": False, "error": "No audio generated"}
            
            # Combine chunks into single PCM audio
            full_audio_pcm = b''.join(audio_chunks)
            logger.info(f"✅ Collected {len(audio_chunks)} chunks, total: {len(full_audio_pcm)} bytes")
            
            # Save PCM to temporary file
            audio_hash = hashlib.md5(text.encode()).hexdigest()
            pcm_path = f"/tmp/tts_ws_{audio_hash}.pcm"
            mp3_path = f"/tmp/tts_ws_{audio_hash}.mp3"
            
            with open(pcm_path, 'wb') as f:
                f.write(full_audio_pcm)
            
            # Convert PCM to MP3 using ffmpeg CLI (FAST - ~50ms)
            conversion_start = time.time()
            try:
                # ffmpeg command: PCM 16kHz mono 16-bit → MP3
                subprocess.run([
                    'ffmpeg',
                    '-f', 's16le',  # signed 16-bit little-endian PCM
                    '-ar', '16000',  # 16kHz sample rate
                    '-ac', '1',      # mono
                    '-i', pcm_path,  # input PCM file
                    '-b:a', '64k',   # 64kbps MP3 bitrate
                    '-y',            # overwrite output
                    mp3_path         # output MP3 file
                ], check=True, capture_output=True, timeout=5)
                
                conversion_time = time.time() - conversion_start
                logger.info(f"⚡ PCM→MP3 conversion: {conversion_time*1000:.0f}ms (ffmpeg)")
                
            except subprocess.TimeoutExpired:
                logger.error("❌ ffmpeg conversion timeout")
                return {"success": False, "error": "Audio conversion timeout"}
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ ffmpeg conversion failed: {e.stderr.decode()}")
                return {"success": False, "error": "Audio conversion failed"}
            except Exception as e:
                logger.error(f"❌ Conversion error: {e}")
                return {"success": False, "error": str(e)}
            
            # Clean up PCM file
            try:
                os.remove(pcm_path)
            except:
                pass
            
            # Verify MP3 was created
            if not os.path.exists(mp3_path):
                logger.error("❌ MP3 file not created")
                return {"success": False, "error": "MP3 conversion failed"}
            
            mp3_size = os.path.getsize(mp3_path)
            logger.info(f"✅ Generated MP3: {mp3_size} bytes")
            
            tts_gen_time = time.time() - tts_start
            logger.info(f"⏱️  Total WebSocket TTS: {tts_gen_time*1000:.0f}ms (including conversion)")
            
            # Get backend URL for serving the audio
            backend_url = os.environ.get('BACKEND_URL', 'https://api.li-ai.org')
            audio_url = f"{backend_url}/api/tts-audio/tts_ws_{audio_hash}.mp3"
            
            logger.info(f"🔗 WebSocket audio URL: {audio_url}")
            
            playback_start = time.time()
            
            # Use Telnyx REST API for playback_start
            import httpx
            
            telnyx_api_key = os.environ.get('TELNYX_API_KEY')
            playback_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/playback_start"
            
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    playback_url,
                    headers={
                        "Authorization": f"Bearer {telnyx_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={"audio_url": audio_url}
                )
                
                playback_time = time.time() - playback_start
                logger.info(f"⏱️  Playback API: {playback_time*1000:.0f}ms")
                
                if response.status_code in [200, 201, 202]:
                    total_time = time.time() - tts_start
                    logger.info(f"⏱️  TOTAL WebSocket TTS latency: {total_time*1000:.0f}ms")
                    logger.info("✅ WebSocket TTS SUCCESS")
                    
                    # Extract playback_id for interruption handling
                    try:
                        response_data = response.json()
                        playback_id = response_data.get("data", {}).get("playback_id")
                        if playback_id:
                            logger.info(f"🎬 Playback ID: {playback_id}")
                            return {"success": True, "playback_id": playback_id}
                    except:
                        pass
                    
                    return {"success": True}
                else:
                    logger.error(f"❌ Telnyx playback failed: {response.status_code} - {response.text}")
                    return {"success": False, "error": "Playback failed"}
                    
        except Exception as e:
            logger.error(f"❌ WebSocket TTS error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    

    async def _speak_text_websocket_sesame(
        self,
        call_control_id: str,
        text: str,
        agent_config: dict
    ) -> Dict[str, Any]:
        """
        Sesame TTS WebSocket streaming for real-time audio
        
        Args:
            call_control_id: Telnyx call control ID
            text: Text to synthesize
            agent_config: Agent configuration with Sesame settings
            
        Returns:
            Dict with success status
        """
        try:
            from sesame_ws_service import stream_sesame_tts
            import hashlib
            import os
            import time
            import subprocess
            
            logger.info("🚀 Using Sesame WebSocket TTS (real-time streaming)")
            
            tts_start = time.time()
            
            # Get Sesame settings
            settings = agent_config.get("settings", {})
            speaker_id = settings.get("sesame_settings", {}).get("speaker_id", 0)
            
            logger.info(f"🎤 Sesame Speaker ID: {speaker_id}")
            
            # Create temp file for streaming
            audio_hash = hashlib.md5(f"{text}_{speaker_id}".encode()).hexdigest()
            temp_pcm = f"/tmp/sesame_ws_{audio_hash}.pcm"
            temp_mulaw = f"/tmp/sesame_ws_{audio_hash}.ulaw"
            
            # Stream audio chunks and write to PCM file
            chunk_count = 0
            first_chunk_time = None
            
            logger.info("📥 Streaming audio chunks from RunPod...")
            
            with open(temp_pcm, 'wb') as f:
                async for chunk in stream_sesame_tts(text, speaker_id):
                    chunk_count += 1
                    
                    if chunk_count == 1:
                        first_chunk_time = time.time() - tts_start
                        logger.info(f"⚡ First chunk received in {first_chunk_time:.2f}s")
                    
                    f.write(chunk)
            
            total_stream_time = time.time() - tts_start
            logger.info(f"✅ Streaming complete: {chunk_count} chunks in {total_stream_time:.2f}s")
            
            # Convert PCM to μ-law (fast conversion)
            conversion_start = time.time()
            
            result = subprocess.run([
                'ffmpeg', '-y',
                '-f', 's16le',  # 16-bit PCM input
                '-ar', '24000',  # 24kHz sample rate
                '-ac', '1',  # Mono
                '-i', temp_pcm,
                '-ar', '8000',  # Resample to 8kHz for Telnyx
                '-f', 'mulaw',  # μ-law output
                '-ac', '1',
                temp_mulaw
            ], capture_output=True, text=True)
            
            conversion_time = time.time() - conversion_start
            logger.info(f"⚡ Audio conversion: {conversion_time:.2f}s")
            
            if result.returncode != 0:
                logger.error(f"❌ FFmpeg error: {result.stderr}")
                return {"success": False, "error": "Audio conversion failed"}
            
            # Upload to S3 or serve locally
            backend_url = os.environ.get('BACKEND_URL', 'https://api.li-ai.org')
            audio_url = f"{backend_url}/api/tts-audio/sesame_ws_{audio_hash}.ulaw"
            
            # Copy to web-accessible location
            web_path = f"/tmp/sesame_ws_{audio_hash}.ulaw"
            os.system(f"cp {temp_mulaw} {web_path}")
            
            logger.info(f"🔗 Audio URL: {audio_url}")
            
            # Play via Telnyx
            playback_start = time.time()
            
            import httpx
            telnyx_api_key = os.environ.get('TELNYX_API_KEY')
            playback_url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/playback_start"
            
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    playback_url,
                    headers={
                        "Authorization": f"Bearer {telnyx_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={"audio_url": audio_url}
                )
                
                playback_time = time.time() - playback_start
                
                if response.status_code in [200, 201, 202]:
                    total_time = time.time() - tts_start
                    logger.info(f"⏱️  Total latency breakdown:")
                    logger.info(f"   - First chunk: {first_chunk_time:.2f}s")
                    logger.info(f"   - Full stream: {total_stream_time:.2f}s")
                    logger.info(f"   - Conversion: {conversion_time:.2f}s")
                    logger.info(f"   - Playback: {playback_time:.2f}s")
                    logger.info(f"   - TOTAL: {total_time:.2f}s")
                    logger.info(f"✅ Sesame WebSocket TTS playing via Telnyx")
                    
                    # Cleanup temp files after a delay
                    try:
                        os.remove(temp_pcm)
                        os.remove(temp_mulaw)
                    except:
                        pass
                    
                    return {"success": True}
                else:
                    logger.error(f"❌ Telnyx playback failed: {response.status_code} - {response.text}")
                    return {"success": False, "error": "Playback failed"}
                    
        except Exception as e:
            logger.error(f"❌ Sesame WebSocket TTS error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    async def gather_using_speak(
        self,
        call_control_id: str,
        text: str,
        language: str = "en-US",
        timeout_secs: int = 5,
        max_digits: int = 1
    ) -> Dict[str, Any]:
        """Speak text and gather user input (DTMF or speech)"""
        try:
            logger.info(f"🎤 Gathering input on call {call_control_id}")
            
            self.client.calls.actions.gather_using_speak(
                call_control_id=call_control_id,
                payload=text,
                voice="female",
                language=language,
                minimum_digits=0 if max_digits == 0 else 1,
                maximum_digits=max(1, max_digits),
                timeout_millis=timeout_secs * 1000,
                inter_digit_timeout_millis=5000
            )
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ Error gathering input: {e}")
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
        # For now, return True
        return True
