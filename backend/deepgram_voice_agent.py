"""
Deepgram Voice Agent API Integration
Handles STT + LLM + TTS in a unified WebSocket connection
"""
import asyncio
import json
import logging
import base64
import websockets
from typing import Dict, Any, Optional, Callable
import os

logger = logging.getLogger(__name__)

class DeepgramVoiceAgent:
    """
    Deepgram Voice Agent API client
    Unified STT + LLM + TTS orchestration
    """
    
    def __init__(
        self,
        api_key: str,
        agent_instructions: str,
        on_user_speech: Optional[Callable] = None,
        on_agent_speech: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        self.api_key = api_key
        self.agent_instructions = agent_instructions
        self.on_user_speech = on_user_speech
        self.on_agent_speech = on_agent_speech
        self.on_error = on_error
        
        self.websocket = None
        self.is_connected = False
        self.conversation_history = []
        
    async def connect(self):
        """Connect to Deepgram Voice Agent API"""
        try:
            url = "wss://agent.deepgram.com/agent"
            headers = {
                "Authorization": f"Token {self.api_key}"
            }
            
            logger.info("🌐 Connecting to Deepgram Voice Agent API...")
            self.websocket = await websockets.connect(url, extra_headers=headers)
            self.is_connected = True
            logger.info("✅ Connected to Deepgram Voice Agent API")
            
            # Send initial settings configuration
            await self._send_settings()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Deepgram: {e}")
            self.is_connected = False
            if self.on_error:
                await self.on_error(str(e))
            return False
    
    async def _send_settings(self):
        """Send configuration settings to Deepgram Voice Agent"""
        settings = {
            "type": "SettingsConfiguration",
            "audio": {
                "input": {
                    "encoding": "mulaw",  # Telnyx uses mulaw
                    "sample_rate": 8000
                },
                "output": {
                    "encoding": "mulaw",  # Telnyx expects mulaw
                    "sample_rate": 8000,
                    "container": "none"
                }
            },
            "agent": {
                "listen": {
                    "model": "nova-3",
                    "language": "en-US"
                },
                "think": {
                    "provider": {
                        "type": "open_ai"
                    },
                    "model": "gpt-4-turbo",
                    "instructions": self.agent_instructions
                },
                "speak": {
                    "model": "aura-asteria-en"
                }
            }
        }
        
        logger.info("📤 Sending settings to Deepgram Voice Agent")
        await self.websocket.send(json.dumps(settings))
        logger.info("✅ Settings sent successfully")
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram for processing"""
        if not self.is_connected or not self.websocket:
            logger.error("❌ Not connected to Deepgram")
            return False
        
        try:
            # Deepgram expects raw audio bytes
            await self.websocket.send(audio_data)
            return True
        except Exception as e:
            logger.error(f"❌ Error sending audio to Deepgram: {e}")
            if self.on_error:
                await self.on_error(str(e))
            return False
    
    async def receive_messages(self):
        """Receive and process messages from Deepgram"""
        if not self.is_connected or not self.websocket:
            logger.error("❌ Not connected to Deepgram")
            return
        
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 Deepgram connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Error receiving from Deepgram: {e}")
            if self.on_error:
                await self.on_error(str(e))
    
    async def _handle_message(self, message):
        """Handle incoming messages from Deepgram"""
        try:
            # Check if message is binary (audio data)
            if isinstance(message, bytes):
                # This is TTS audio output from Deepgram
                logger.debug(f"🔊 Received audio chunk: {len(message)} bytes")
                if self.on_agent_speech:
                    await self.on_agent_speech(message)
                return
            
            # Parse JSON message
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "UserStartedSpeaking":
                logger.info("🎤 User started speaking")
                
            elif msg_type == "UserStoppedSpeaking":
                logger.info("🤐 User stopped speaking")
                
            elif msg_type == "ConversationText":
                # User's transcribed speech
                role = data.get("role")
                content = data.get("content", "")
                
                if role == "user":
                    logger.info(f"👤 User said: {content}")
                    self.conversation_history.append({"role": "user", "content": content})
                    if self.on_user_speech:
                        await self.on_user_speech(content)
                        
                elif role == "assistant":
                    logger.info(f"🤖 Agent said: {content}")
                    self.conversation_history.append({"role": "assistant", "content": content})
            
            elif msg_type == "AgentThinking":
                logger.info("💭 Agent is thinking...")
                
            elif msg_type == "AgentAudioDone":
                logger.info("✅ Agent finished speaking")
                
            elif msg_type == "Error":
                error_msg = data.get("message", "Unknown error")
                logger.error(f"❌ Deepgram error: {error_msg}")
                if self.on_error:
                    await self.on_error(error_msg)
            
            else:
                logger.debug(f"📨 Received message type: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error(f"❌ Failed to parse message: {message}")
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
    
    async def update_context(self, new_instructions: str):
        """Update the agent's context/instructions mid-conversation"""
        try:
            update_msg = {
                "type": "UpdateInstructions",
                "instructions": new_instructions
            }
            await self.websocket.send(json.dumps(update_msg))
            self.agent_instructions = new_instructions
            logger.info("✅ Updated agent instructions")
        except Exception as e:
            logger.error(f"❌ Error updating instructions: {e}")
    
    async def close(self):
        """Close the Deepgram connection"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("🔌 Closed Deepgram connection")
    
    def get_conversation_history(self):
        """Get the full conversation history"""
        return self.conversation_history
