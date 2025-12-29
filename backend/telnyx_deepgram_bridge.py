"""
Telnyx + Deepgram Voice Agent Bridge
Handles bidirectional audio streaming between Telnyx and Deepgram
"""
import asyncio
import json
import logging
import base64
from fastapi import WebSocket
from typing import Dict, Optional
from deepgram_voice_agent import DeepgramVoiceAgent
from core_calling_service import CallSession

logger = logging.getLogger(__name__)

class TelnyxDeepgramBridge:
    """
    Bridge between Telnyx RTP WebSocket and Deepgram Voice Agent API
    """
    
    def __init__(
        self,
        telnyx_ws: WebSocket,
        call_control_id: str,
        session: CallSession,
        deepgram_api_key: str
    ):
        self.telnyx_ws = telnyx_ws
        self.call_control_id = call_control_id
        self.session = session
        self.deepgram_api_key = deepgram_api_key
        
        self.deepgram_agent: Optional[DeepgramVoiceAgent] = None
        self.is_running = False
        self.user_transcript = []
        self.agent_transcript = []
        
    async def start(self):
        """Start the bridge"""
        logger.info(f"🌉 Starting Telnyx-Deepgram bridge for call: {self.call_control_id}")
        
        # Get agent instructions from session
        agent_instructions = await self._build_agent_instructions()
        
        # Create Deepgram Voice Agent
        self.deepgram_agent = DeepgramVoiceAgent(
            api_key=self.deepgram_api_key,
            agent_instructions=agent_instructions,
            on_user_speech=self._handle_user_speech,
            on_agent_speech=self._handle_agent_speech,
            on_error=self._handle_error
        )
        
        # Connect to Deepgram
        connected = await self.deepgram_agent.connect()
        if not connected:
            logger.error("❌ Failed to connect to Deepgram")
            return False
        
        self.is_running = True
        
        # Start bidirectional streaming tasks
        await asyncio.gather(
            self._forward_telnyx_to_deepgram(),
            self._receive_deepgram_messages()
        )
        
        return True
    
    async def _build_agent_instructions(self) -> str:
        """Build agent instructions from conversation flow"""
        # Get current node from session
        current_node = self.session.current_node
        
        if not current_node:
            return "You are a helpful AI assistant. Respond naturally to the user."
        
        # Extract prompt from current node
        node_data = current_node.get("data", {})
        prompt = node_data.get("prompt", "")
        prompt_type = node_data.get("prompt_type", "prompt")
        
        if prompt_type == "script":
            # Exact script - tell agent to say this exactly
            instructions = f"Say exactly this to the user: '{prompt}'. Do not add anything else."
        else:
            # AI prompt - give context and let agent respond naturally
            instructions = f"You are a helpful AI assistant in a phone conversation. {prompt}"
        
        # Add conversation context
        if self.session.conversation_history:
            history = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in self.session.conversation_history[-5:]  # Last 5 messages
            ])
            instructions += f"\n\nConversation so far:\n{history}"
        
        logger.info(f"📝 Agent instructions: {instructions[:100]}...")
        return instructions
    
    async def _forward_telnyx_to_deepgram(self):
        """Forward audio from Telnyx to Deepgram"""
        try:
            async for message in self.telnyx_ws.iter_text():
                if not self.is_running:
                    break
                
                # Parse Telnyx RTP message
                data = json.loads(message)
                event = data.get("event")
                
                if event == "connected":
                    logger.info("📞 Telnyx WebSocket connected")
                    
                elif event == "start":
                    logger.info("🎬 Telnyx stream started")
                    
                elif event == "media":
                    # Extract base64-encoded RTP audio
                    media = data.get("media", {})
                    payload = media.get("payload", "")
                    
                    if payload:
                        # Decode base64 to get raw audio bytes
                        audio_bytes = base64.b64decode(payload)
                        
                        # Forward to Deepgram
                        await self.deepgram_agent.send_audio(audio_bytes)
                
                elif event == "stop":
                    logger.info("⏹️ Telnyx stream stopped")
                    self.is_running = False
                    break
                    
        except Exception as e:
            logger.error(f"❌ Error forwarding Telnyx audio: {e}", exc_info=True)
            self.is_running = False
    
    async def _receive_deepgram_messages(self):
        """Receive messages from Deepgram and forward audio to Telnyx"""
        try:
            await self.deepgram_agent.receive_messages()
        except Exception as e:
            logger.error(f"❌ Error receiving Deepgram messages: {e}", exc_info=True)
            self.is_running = False
    
    async def _handle_user_speech(self, transcript: str):
        """Handle user speech transcript from Deepgram"""
        logger.info(f"👤 User said: {transcript}")
        self.user_transcript.append(transcript)
        
        # Process through conversation flow
        response = await self.session.process_user_input(transcript)
        
        # Check if we need to update context (node transition)
        if self.session.should_end_call:
            logger.info("📞 Ending node reached - will close call after agent speaks")
            # Deepgram will handle the final response
            # We'll close the call after audio finishes
        
        # Update Deepgram instructions if node changed
        new_node = self.session.current_node
        if new_node:
            new_instructions = await self._build_agent_instructions()
            await self.deepgram_agent.update_context(new_instructions)
    
    async def _handle_agent_speech(self, audio_bytes: bytes):
        """Handle agent speech audio from Deepgram"""
        # Encode audio as base64 and send to Telnyx
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Send media message to Telnyx
        media_message = {
            "event": "media",
            "media": {
                "payload": audio_b64
            }
        }
        
        try:
            await self.telnyx_ws.send_json(media_message)
        except Exception as e:
            logger.error(f"❌ Error sending audio to Telnyx: {e}")
    
    async def _handle_error(self, error: str):
        """Handle errors from Deepgram"""
        logger.error(f"❌ Deepgram error: {error}")
    
    async def stop(self):
        """Stop the bridge"""
        logger.info("🛑 Stopping Telnyx-Deepgram bridge")
        self.is_running = False
        
        if self.deepgram_agent:
            await self.deepgram_agent.close()
        
        # Return conversation data
        return {
            "user_transcript": self.user_transcript,
            "agent_transcript": self.agent_transcript,
            "conversation_history": self.deepgram_agent.get_conversation_history() if self.deepgram_agent else []
        }
