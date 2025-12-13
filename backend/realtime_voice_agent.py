"""
Real-time voice agent using Deepgram Live Transcription API
Connects Telnyx audio streams with Deepgram for bidirectional real-time conversation
"""
import asyncio
import json
import base64
import logging

logger = logging.getLogger(__name__)

class RealtimeVoiceAgent:
    """
    Handles real-time bidirectional voice conversation
    Telnyx Audio <-> Deepgram STT <-> AI Agent <-> Telnyx TTS
    """
    
    def __init__(self, deepgram_api_key, call_control_id, session, telnyx_service, db, active_calls):
        self.deepgram_api_key = deepgram_api_key
        self.call_control_id = call_control_id
        self.session = session
        self.telnyx_service = telnyx_service
        self.db = db
        self.active_calls = active_calls
        self.deepgram_ws = None
        self.is_agent_speaking = False
        self.last_agent_text = ""
        
    async def start(self, telnyx_websocket):
        """
        Start the real-time voice agent with Deepgram live transcription
        """
        import websockets
        
        try:
            # Connect to Deepgram live streaming API
            deepgram_url = (
                f"wss://api.deepgram.com/v1/listen?"
                f"model=nova-3&"
                f"encoding=mulaw&"
                f"sample_rate=8000&"
                f"channels=1&"
                f"punctuate=true&"
                f"interim_results=true&"
                f"endpointing=500&"  # 500ms silence = end of speech
                f"vad_events=true&"  # Voice activity detection
                f"smart_format=true"
            )
            
            logger.info(f"🌐 Connecting to Deepgram live streaming...")
            
            self.deepgram_ws = await websockets.connect(
                deepgram_url,
                additional_headers={"Authorization": f"Token {self.deepgram_api_key}"}
            )
            
            logger.info(f"✅ Connected to Deepgram for real-time transcription")
            
            # Send initial greeting
            first_message = await self.session.process_user_input("")
            first_text = first_message.get("text", "Hello! How can I help you?")
            
            await self._speak_and_save(first_text)
            
            # Run bidirectional streaming
            await asyncio.gather(
                self._stream_telnyx_to_deepgram(telnyx_websocket),
                self._receive_deepgram_transcripts()
            )
            
        except Exception as e:
            logger.error(f"❌ Error in real-time voice agent: {e}", exc_info=True)
        finally:
            if self.deepgram_ws:
                await self.deepgram_ws.close()
    
    async def _stream_telnyx_to_deepgram(self, telnyx_websocket):
        """
        Stream audio from Telnyx to Deepgram for real-time transcription
        """
        try:
            audio_count = 0
            async for message in telnyx_websocket:
                if isinstance(message, str):
                    data = json.loads(message)
                    event_type = data.get("event")
                    
                    if event_type == "media" and not self.is_agent_speaking:
                        # Forward audio to Deepgram (only when agent not speaking)
                        media = data.get("media", {})
                        audio_payload = media.get("payload", "")
                        
                        if audio_payload:
                            audio_bytes = base64.b64decode(audio_payload)
                            await self.deepgram_ws.send(audio_bytes)
                            audio_count += 1
                            
                            if audio_count % 100 == 0:
                                logger.debug(f"📡 Forwarded {audio_count} audio packets")
                    
                    elif event_type == "start":
                        logger.info("📞 Telnyx media stream started")
                    
                    elif event_type == "stop":
                        logger.info("📞 Telnyx media stream stopped")
                        break
                        
        except Exception as e:
            logger.error(f"❌ Error streaming audio to Deepgram: {e}", exc_info=True)
    
    async def _receive_deepgram_transcripts(self):
        """
        Receive transcription results from Deepgram with real-time endpointing
        """
        try:
            async for message in self.deepgram_ws:
                result = json.loads(message)
                
                msg_type = result.get("type")
                
                if msg_type == "Results":
                    channel = result.get("channel", {})
                    alternatives = channel.get("alternatives", [])
                    
                    if alternatives:
                        transcript = alternatives[0].get("transcript", "")
                        is_final = channel.get("is_final", False)
                        speech_final = result.get("speech_final", False)
                        
                        if transcript:
                            if not is_final:
                                logger.debug(f"💭 Interim: {transcript}")
                            
                            if speech_final:
                                # Deepgram detected end of speech!
                                logger.info(f"📝 User said (speech_final): {transcript}")
                                await self._handle_user_input(transcript)
                
                elif msg_type == "SpeechStarted":
                    logger.debug("🎤 User started speaking (VAD)")
                
                elif msg_type == "UtteranceEnd":
                    logger.debug("⏸️ Utterance ended (VAD)")
                        
        except Exception as e:
            logger.error(f"❌ Error receiving from Deepgram: {e}", exc_info=True)
    
    async def _handle_user_input(self, text):
        """
        Process user input through AI agent and generate response
        """
        try:
            # Echo filter - check if transcript matches agent's last words
            if self.last_agent_text:
                text_lower = text.lower()
                agent_words = set(self.last_agent_text.lower().split())
                text_words = set(text_lower.split())
                
                if text_words and agent_words:
                    overlap = len(text_words & agent_words)
                    overlap_ratio = overlap / len(text_words)
                    
                    if overlap_ratio > 0.7:
                        logger.warning(f"🔇 Filtered echo: '{text}' (overlap: {overlap_ratio:.0%})")
                        return
            
            # Save user transcript
            await self.db.call_logs.update_one(
                {"call_id": self.call_control_id},
                {"$push": {
                    "transcript": {
                        "speaker": "user",
                        "text": text,
                        "timestamp": self._get_timestamp()
                    }
                }}
            )
            
            # Mark agent as speaking to stop forwarding audio
            self.is_agent_speaking = True
            
            # Process through AI
            response = await self.session.process_user_input(text)
            response_text = response.get("text", "I'm sorry, I didn't understand that.")
            
            logger.info(f"🤖 AI response: {response_text}")
            
            # Speak response
            await self._speak_and_save(response_text)
            
            # Check if should end call
            if self.session.should_end_call:
                logger.info("📞 Ending node reached - hanging up")
                # Wait for speech to finish
                word_count = len(response_text.split())
                speech_duration = max(2, (word_count * 0.15) + 1)
                await asyncio.sleep(speech_duration)
                
                await self.telnyx_service.hangup_call(self.call_control_id)
                if self.call_control_id in self.active_calls:
                    del self.active_calls[self.call_control_id]
            
        except Exception as e:
            logger.error(f"❌ Error handling user input: {e}", exc_info=True)
        finally:
            self.is_agent_speaking = False
    
    async def _speak_and_save(self, text):
        """
        Speak text via Telnyx and save to transcript
        """
        try:
            # Save to transcript
            await self.db.call_logs.update_one(
                {"call_id": self.call_control_id},
                {"$push": {
                    "transcript": {
                        "speaker": "agent",
                        "text": text,
                        "timestamp": self._get_timestamp()
                    }
                }}
            )
            
            # Speak via Telnyx TTS
            await self.telnyx_service.speak_text(self.call_control_id, text)
            logger.info("🔊 Agent spoke")
            
            self.last_agent_text = text
            
            # Wait for speech to finish before listening again
            word_count = len(text.split())
            speech_duration = max(2, (word_count * 0.15) + 1)
            await asyncio.sleep(speech_duration)
            
        except Exception as e:
            logger.error(f"❌ Error speaking: {e}")
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.utcnow().isoformat()
