import asyncio
import os
import json
import time
from typing import Dict, List
from openai import AsyncOpenAI
import logging
from dotenv import load_dotenv
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)

# Import RAG service at module level so it loads once when the module is imported
# This avoids 12s cold start on first use during a call
try:
    from rag_service import retrieve_relevant_chunks
    logger.info("✅ RAG service imported successfully at module load")
except Exception as e:
    logger.warning(f"⚠️ Could not import RAG service: {e}")
    retrieve_relevant_chunks = None

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Initialize API clients
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ELEVEN_API_KEY = os.environ.get('ELEVEN_API_KEY')

# Initialize OpenAI client lazily
_openai_client = None
_grok_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None and OPENAI_API_KEY:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client

async def get_llm_client(provider: str = "openai", api_key: str = None, session=None):
    """Get LLM client based on provider (openai or grok)
    
    Args:
        provider: "openai" or "grok"
        api_key: Optional API key (if not provided, retrieves from session)
        session: CallSession instance (used to retrieve user API keys)
    """
    if provider == "grok":
        # Use OpenAI library with xAI base URL for Grok
        try:
            import openai
            
            # Get API key from parameter, session, or environment (fallback)
            if api_key:
                grok_key = api_key
            elif session:
                try:
                    grok_key = await session.get_api_key("grok")
                except ValueError as e:
                    logger.error(f"Failed to get Grok API key: {e}")
                    return None
            else:
                grok_key = os.environ.get('GROK_API_KEY')
            
            if not grok_key:
                logger.error("Grok API key not found")
                return None
            
            # Create OpenAI client with xAI base URL
            client = openai.AsyncOpenAI(
                api_key=grok_key,
                base_url="https://api.x.ai/v1"
            )
            
            # Create a wrapper to match our interface
            class GrokClient:
                def __init__(self, openai_client):
                    self.client = openai_client
                    
                async def create_completion(self, messages, model, temperature, max_tokens, stream=False):
                    """Create a completion using Grok via xAI API"""
                    try:
                        response = await self.client.chat.completions.create(
                            model=model or "grok-3",
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stream=stream
                        )
                        return response
                        
                    except Exception as e:
                        logger.error(f"Error with Grok API: {e}")
                        return None
                        
            return GrokClient(client)
            
        except ImportError as e:
            logger.error(f"OpenAI library not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating Grok client: {e}")
            return None
    else:
        # Default to OpenAI
        if api_key:
            return AsyncOpenAI(api_key=api_key)
        elif session:
            try:
                openai_key = await session.get_api_key("openai")
                return AsyncOpenAI(api_key=openai_key)
            except ValueError as e:
                logger.error(f"Failed to get OpenAI API key: {e}")
                return None
        else:
            # Fallback to environment (for backward compatibility)
            return get_openai_client()

class CallSession:
    """Manages a single call session with STT, LLM, and TTS pipeline"""
    
    def __init__(self, call_id: str, agent_config: dict, agent_id: str = None, knowledge_base: str = "", user_id: str = None, db=None):
        self.call_id = call_id
        self.agent_config = agent_config
        self.agent_id = agent_id or agent_config.get("id")  # Store agent_id for refreshing config
        self.user_id = user_id or agent_config.get("user_id")  # Store user_id for API key retrieval
        self.db = db  # Database connection for retrieving user API keys
        self.conversation_history = []
        self.current_node_id = None  # Track current position in flow
        self.current_node_label = None  # Track current node label for QC reports
        self.should_end_call = False  # Flag for ending nodes
        self.session_variables = {}  # Store variables from webhooks and extractions
        self.knowledge_base = knowledge_base  # Store KB content for LLM context
        self._api_key_cache = {}  # Cache user API keys for this session
        
        # Webhook execution flag - pauses dead air monitoring during webhook
        self.executing_webhook = False
        
        # Timing metrics for QC analysis (per-turn tracking)
        self.last_transition_time_ms = 0  # Time spent evaluating transitions
        self.last_kb_time_ms = 0  # Time spent on KB retrieval (if any)
        
        # Voicemail/IVR detection
        from voicemail_detector import VoicemailDetector
        self.voicemail_detector = VoicemailDetector(agent_config.get("settings", {}))
        
        # Add current date/time in EST timezone as {{now}} variable
        from datetime import datetime
        import pytz
        est = pytz.timezone('America/New_York')
        now_est = datetime.now(est)
        # Format: "Monday, November 4, 2025 at 3:45 PM EST"
        self.session_variables['now'] = now_est.strftime("%A, %B %-d, %Y at %-I:%M %p %Z")
        
        # Initialize customer_name and callerName as empty - will be populated when extracted
        # Both are kept in sync so webhooks can use either field name
        self.session_variables['customer_name'] = ""
        self.session_variables['callerName'] = ""
        
        # Build cached system prompt ONCE with KB - critical for Grok's prefix caching
        # Grok caches based on exact prefix match, so we must reuse the SAME string object
        self._cached_system_prompt = self._build_cached_system_prompt()
        
        self.is_active = True
        self.deepgram_connection = None
        self.current_transcript = ""
        self.latency_start = None
        
        # Dead air prevention tracking
        self.silence_start_time = None  # When silence started (after agent stopped speaking)
        self.agent_speaking = False  # Track if agent is currently speaking
        self.user_speaking = False  # Track if user is currently speaking
        self.checkin_count = 0  # Current check-in count for this silence period
        self.last_message_was_checkin = False  # Track if last agent message was a check-in
        self.hold_on_detected = False  # Whether user said "hold on" in last response
        self.call_start_time = time.time()  # Track call start for max duration
        self.silence_timer_task = None  # Background task for silence monitoring
        self.last_checkin_time = None  # Track last check-in to avoid rapid repeats
        self.max_checkins_reached = False  # Flag to indicate we've hit max and should end after next timeout
        
        # Initialize Natural Delivery Middleware (Dual-Stream Architecture)
        from natural_delivery_middleware import NaturalDeliveryMiddleware
        self.delivery_middleware = NaturalDeliveryMiddleware()
    
    def set_customer_name(self, name: str):
        """Set customer name - keeps customer_name and callerName in sync for webhook compatibility"""
        if name:
            self.session_variables['customer_name'] = name
            self.session_variables['callerName'] = name
            logger.info(f"📛 Customer name set: {name} (synced to both customer_name and callerName)")
    
    def set_variable(self, name: str, value):
        """Set a session variable with automatic syncing for name fields"""
        self.session_variables[name] = value
        # Keep customer_name and callerName in sync
        if name == 'customer_name' and value:
            self.session_variables['callerName'] = value
        elif name == 'callerName' and value:
            self.session_variables['customer_name'] = value
    
    async def get_api_key(self, service_name: str) -> str:
        """
        Get user-specific API key for a service
        Caches keys per session for performance
        
        Args:
            service_name: Service name (openai, deepgram, elevenlabs, grok, hume, soniox, assemblyai, telnyx)
            
        Returns:
            Decrypted API key
            
        Raises:
            ValueError: If key not found for user
        """
        # Check cache first
        if service_name in self._api_key_cache:
            return self._api_key_cache[service_name]
        
        if not self.user_id:
            raise ValueError(f"Cannot retrieve {service_name} API key: user_id not set")
        
        if self.db is None:
            raise ValueError(f"Cannot retrieve {service_name} API key: database connection not available")
        
        try:
            from key_encryption import decrypt_api_key
            
            # Retrieve key from database
            key_doc = await self.db.api_keys.find_one({
                "user_id": self.user_id,
                "service_name": service_name,
                "is_active": True
            })
            
            if not key_doc or not key_doc.get("api_key"):
                raise ValueError(
                    f"No {service_name} API key found for user. "
                    f"Please add your {service_name} API key in Settings."
                )
            
            # Decrypt and cache the key
            encrypted_key = key_doc.get("api_key")
            decrypted_key = decrypt_api_key(encrypted_key)
            self._api_key_cache[service_name] = decrypted_key
            
            logger.debug(f"🔑 Retrieved {service_name} key for user {self.user_id[:8]}...")
            return decrypted_key
            
        except ValueError:
            # Re-raise ValueError with clear message
            raise
        except Exception as e:
            logger.error(f"❌ Error retrieving {service_name} API key: {e}")
            raise ValueError(f"Failed to retrieve {service_name} API key: {str(e)}")
    
    async def get_llm_client_for_session(self, provider: str = None):
        """Get LLM client using this session's user API keys
        
        Args:
            provider: Override provider from agent settings
            
        Returns:
            LLM client instance
        """
        # Get provider from agent settings if not specified
        if not provider:
            settings = self.agent_config.get("settings", {})
            provider = settings.get("llm_provider", "openai")
        
        # Use the updated get_llm_client with session parameter
        return await get_llm_client(provider=provider, session=self)


    def _build_cached_system_prompt(self):
        """Build the cached system prompt ONCE - KB added dynamically via smart routing"""
        
        # START WITH AGENT'S GLOBAL PROMPT (personality, behavior, rules)
        # This is the most important part - it defines the agent's character and boundaries
        global_prompt = self.agent_config.get("system_prompt", "").strip()
        
        # Then add technical communication rules
        technical_rules = """

# COMMUNICATION STYLE
- Speak naturally and conversationally
- Keep responses concise (1-2 sentences when possible)
- Use natural pauses, not XML tags
- Be friendly and professional

# STRICT RULES
- NO format markers or meta-text
- NO XML tags like <speak> or <break>
- NO phrases like '--- AI TURN ---' or 'AGENT_SCRIPT_LINE_INPUT:'
- Just speak naturally as a human would

# CRITICAL - AVOID REPETITION
- Review the conversation history carefully before responding
- DO NOT repeat questions or phrases you've already said
- If you've already asked about a specific dollar amount (like $20,000/month), DO NOT ask it again
- If you need to accomplish the same goal, come up with a DIFFERENT approach - rephrase, use different framing, or ask from a different angle
- Track what you've already said and ensure each response brings something NEW to the conversation

# VOICE DELIVERY (INTERNAL)
- You are a voice actor. You MUST prefix your responses with a "Voice Tag" to control your tone.
- [H]: Use for HAPPY, excited, positive, or helpful news. (e.g., "[H] Great! I can help with that.")
- [S]: Use for SERIOUS, empathetic, careful, or focused moments. (e.g., "[S] I understand, let's reset.")
- [N]: Use for NEUTRAL, factual information.
- Rules:
  1. ALWAYS start your response with [H], [S], or [N].
  2. Do NOT output the tag if you are just thinking or calling a tool. Only for spoken text.
"""
        
        # Combine: Global prompt (character/boundaries) + Technical rules (format/repetition)
        if global_prompt:
            prompt = global_prompt + technical_rules
            logger.info(f"📋 Built cached system prompt: {len(global_prompt)} chars (global) + {len(technical_rules)} chars (technical)")
        else:
            # Fallback if no global prompt defined
            prompt = "You are a phone agent conducting natural conversations." + technical_rules
            logger.info(f"⚠️ No global prompt found - using default")
        
        # NOTE: KB is added dynamically via smart routing, not in cached prompt
        # This keeps the cached prompt clean and enables sub-500ms simple chat responses
        if self.knowledge_base:
            logger.info(f"📚 KB available - will use smart routing (simple chat: NO KB, factual: WITH KB)")
        
        return prompt
    
    async def refresh_agent_config(self, db):
        """Refresh agent configuration from database to get latest settings
        
        Uses PRIMARY read preference to ensure no replica lag and always gets
        the most recent data, even immediately after UI updates.
        """
        try:
            if not self.agent_id:
                logger.warning(f"Cannot refresh agent config: agent_id not set for call {self.call_id}")
                return
            
            # Fetch latest agent config from database with PRIMARY read preference
            # This ensures we get the most recent data, avoiding replica lag
            from pymongo import ReadPreference
            agent = await db.agents.with_options(
                read_preference=ReadPreference.PRIMARY
            ).find_one({"id": self.agent_id})
            
            if agent:
                self.agent_config = agent
                settings = agent.get('settings', {})
                tts_provider = settings.get('tts_provider', 'NOT SET')
                logger.info(f"✅ Refreshed agent config for call {self.call_id}, agent {self.agent_id}")
                logger.info(f"   🔊 TTS Provider: {tts_provider}")
                
                # Log provider-specific settings
                if tts_provider == 'elevenlabs':
                    voice_id = settings.get('elevenlabs_settings', {}).get('voice_id', 'N/A')
                    logger.info(f"   🎙️ ElevenLabs Voice ID: {voice_id}")
                elif tts_provider == 'cartesia':
                    voice_id = settings.get('voice_id', 'N/A')
                    logger.info(f"   🎙️ Cartesia Voice ID: {voice_id}")
                elif tts_provider == 'melo':
                    melo_voice = settings.get('melo_settings', {}).get('voice', 'N/A')
                    melo_speed = settings.get('melo_settings', {}).get('speed', 'N/A')
                    logger.info(f"   🎙️ MeloTTS Voice: {melo_voice}, Speed: {melo_speed}")
            else:
                logger.warning(f"Agent {self.agent_id} not found in database, keeping cached config")
        except Exception as e:
            logger.error(f"Error refreshing agent config: {e}, keeping cached config")
        
    
    def _detect_hold_on_phrase(self, text: str) -> bool:
        """Detect if user said 'hold on' or similar phrase"""
        hold_on_phrases = [
            "hold on", "wait", "one moment", "give me a second", 
            "hang on", "just a sec", "one sec", "hold please"
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in hold_on_phrases)
    
    def start_silence_tracking(self):
        """Start tracking silence after agent stops speaking"""
        if not self.agent_speaking and not self.user_speaking:
            self.silence_start_time = time.time()
            logger.info(f"⏱️ SILENCE TIMER STARTED at {self.silence_start_time} for call {self.call_id}")
    
    def reset_silence_tracking(self):
        """Reset silence tracking when user gives meaningful response"""
        if self.silence_start_time:
            logger.info(f"⏱️ SILENCE TIMER RESET (user gave meaningful response) for call {self.call_id}")
        self.silence_start_time = None
        self.checkin_count = 0  # Reset check-in count when user responds
        self.hold_on_detected = False
        self.max_checkins_reached = False  # Reset the flag when user responds
        logger.info(f"🔊 Silence tracking reset for call {self.call_id} (user responded)")
    
    def reset_silence_timer_only(self):
        """Reset only the silence timer when user starts speaking (don't reset checkin_count)"""
        if self.silence_start_time:
            logger.info(f"⏱️ SILENCE TIMER RESET (user started speaking) for call {self.call_id}")
        self.silence_start_time = None
        logger.info(f"🔊 Silence timer reset for call {self.call_id} (user started speaking)")
    
    def mark_agent_speaking_start(self):
        """Mark that agent has started speaking"""
        self.agent_speaking = True
        self.silence_start_time = None  # Stop counting silence
        logger.info(f"🤖 Agent started speaking for call {self.call_id}")
    
    def mark_agent_speaking_end(self):
        """Mark that agent has stopped speaking - start silence timer"""
        self.agent_speaking = False
        # Start silence tracking immediately after agent stops
        if not self.user_speaking:
            self.start_silence_tracking()
        logger.info(f"🤖 Agent stopped speaking for call {self.call_id}")
    
    def mark_user_speaking_start(self):
        """Mark that user started speaking"""
        self.user_speaking = True
        # DON'T reset checkin_count here - only reset when user gives meaningful response
        # (handled in process_user_response after we know what they said)
        self.reset_silence_timer_only()
        logger.info(f"👤 User started speaking for call {self.call_id}")
    
    def mark_user_speaking_end(self):
        """Mark that user has stopped speaking"""
        self.user_speaking = False
        # Don't start silence tracking yet - wait for agent to finish responding
        logger.info(f"👤 User stopped speaking for call {self.call_id}")
    
    def get_silence_duration(self) -> float:
        """Get current silence duration in seconds"""
        if self.silence_start_time and not self.agent_speaking and not self.user_speaking:
            duration = time.time() - self.silence_start_time
            return duration
        return 0.0
    
    def should_checkin(self) -> bool:
        """Check if we should send a check-in message"""
        settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
        silence_timeout = settings.get("silence_timeout_hold_on", 25) if self.hold_on_detected else settings.get("silence_timeout_normal", 7)
        max_checkins = settings.get("max_checkins_before_disconnect", 2)
        
        # If we've already reached max check-ins, don't send more check-ins
        # (but we'll still wait for the timeout to end the call)
        if self.checkin_count >= max_checkins:
            logger.debug(f"❌ should_checkin: No - already sent {self.checkin_count}/{max_checkins} check-ins")
            return False
        
        # Check silence duration
        silence_duration = self.get_silence_duration()
        
        # Only log when close to triggering or when triggered
        # (removed excessive logging that caused latency)
        
        if silence_duration >= silence_timeout:
            # Prevent rapid check-ins (at least 3 seconds between check-ins)
            if self.last_checkin_time is None or (time.time() - self.last_checkin_time) >= 3:
                logger.info(f"⏰ Check-in triggered after {silence_duration:.1f}s silence (threshold: {silence_timeout}s)")
                return True
            else:
                logger.debug(f"❌ should_checkin: No - too soon after last check-in")
        
        return False
    
    def should_end_call_max_duration(self) -> bool:
        """Check if call should end due to max duration"""
        settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
        max_duration = settings.get("max_call_duration", 1500)  # 25 minutes default
        
        call_duration = time.time() - self.call_start_time
        if call_duration >= max_duration:
            logger.warning(f"⏱️ Max call duration ({max_duration}s) reached for call {self.call_id}")
            return True
        return False
    
    def should_end_call_max_checkins(self) -> bool:
        """Check if call should end due to max check-ins
        
        After max check-ins are sent, we wait one more silence period.
        If still no response after that period, end the call.
        """
        settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
        max_checkins = settings.get("max_checkins_before_disconnect", 2)
        silence_timeout = settings.get("silence_timeout_hold_on", 25) if self.hold_on_detected else settings.get("silence_timeout_normal", 7)
        
        # If we've reached max check-ins
        if self.checkin_count >= max_checkins and not self.max_checkins_reached:
            # Set flag - we'll wait one more period before ending
            self.max_checkins_reached = True
            logger.warning(f"⚠️ Max check-ins ({max_checkins}) reached - will end call after one more {silence_timeout}s silence period")
            return False
        
        # If flag is set AND we've waited the additional silence period
        if self.max_checkins_reached:
            silence_duration = self.get_silence_duration()
            if silence_duration >= silence_timeout:
                logger.warning(f"🚫 Call ending - max check-ins reached AND additional {silence_timeout}s timeout expired")
                return True
        
        return False
    
    def get_checkin_message(self) -> str:
        """Get the check-in message to send"""
        settings = self.agent_config.get("settings", {}).get("dead_air_settings", {})
        max_checkins = settings.get("max_checkins_before_disconnect", 2)
        message = settings.get("checkin_message", "Are you still there?")
        self.checkin_count += 1
        self.last_message_was_checkin = True  # Mark that we're sending a check-in
        self.last_checkin_time = time.time()
        
        # If this is the last check-in, set the flag
        if self.checkin_count >= max_checkins:
            self.max_checkins_reached = True
            logger.info(f"💬 Sending FINAL check-in #{self.checkin_count}/{max_checkins}: {message}")
            logger.info(f"⚠️ Will end call if no response after next silence timeout")
        else:
            logger.info(f"💬 Sending check-in #{self.checkin_count}/{max_checkins}: {message}")
        
        return message

    async def initialize_deepgram(self):
        """Initialize Deepgram live transcription"""
        try:
            # For now, we'll use a simplified approach without real-time STT
            # In production, you would set up the Deepgram WebSocket connection here
            logger.info(f"Deepgram initialized for call {self.call_id}")
            self.deepgram_connection = None  # Placeholder
            
        except Exception as e:
            logger.error(f"Error initializing Deepgram: {e}")
            raise
    
    async def on_transcript(self, result):
        """Handle transcription results from Deepgram"""
        try:
            transcript = result.channel.alternatives[0].transcript
            
            if len(transcript) > 0:
                is_final = result.is_final
                
                if is_final:
                    logger.info(f"Final transcript: {transcript}")
                    self.current_transcript = transcript
                    
                    # Process the complete utterance
                    await self.process_user_input(transcript)
                    self.current_transcript = ""
                else:
                    # Update current transcript for interim results
                    self.current_transcript = transcript
                    
        except Exception as e:
            logger.error(f"Error processing transcript: {e}")
    
    def on_error(self, error):
        """Handle Deepgram errors"""
        logger.error(f"Deepgram error: {error}")
    
    async def process_user_input(self, user_text: str, stream_callback=None):
        """Process user input through LLM and generate response
        
        Args:
            user_text: User's transcribed text
            stream_callback: Optional callback for streaming sentences as they're generated
        """
        try:
            from datetime import datetime
            import asyncio
            latency_start = time.time()
            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.info(f"⏱️ [{timestamp_str}] 📥 process_user_input() ENTRY - text: '{user_text[:50]}...'")
            
            # ═══════════════════════════════════════════════════════════════════
            # 🚨 BARGE-IN INTERCEPTOR 🚨
            # Check if we generated a silence greeting that the user is now interrupting
            # ═══════════════════════════════════════════════════════════════════
            try:
                from redis_service import redis_service
                call_data = redis_service.get_call_data(self.call_id)
                
                if call_data and call_data.get("silence_greeting_triggered"):
                    logger.warning(f"🚨 BARGE-IN DETECTED for call {self.call_id}: User spoke while Silence Greeting was triggering")
                    
                    # 1. Stop Audio Immediately (best-effort - may fail if audio already finished)
                    try:
                        from telnyx_service import TelnyxService
                        # TelnyxService will use env vars for api_key and connection_id
                        # This is safe because we're just stopping playback, not initiating calls
                        ts = TelnyxService()
                        await ts.stop_audio_playback(self.call_id)
                        logger.info("✅ BARGE-IN: Audio playback STOPPED")
                    except Exception as e:
                        # This is expected if audio already finished or never started
                        logger.warning(f"⚠️ BARGE-IN: Could not stop audio (may have finished): {e}")

                    # 2. Clean History (Remove the silence greeting)
                    # SAFETY: Only remove if last message is the silence greeting (short, question-like)
                    if self.conversation_history and len(self.conversation_history) >= 1:
                        last_msg = self.conversation_history[-1]
                        if last_msg.get("role") == "assistant":
                            last_content = last_msg.get("content", "")
                            # Only remove if it looks like a silence greeting (short, ends with ?)
                            if len(last_content) < 50 and "?" in last_content:
                                removed = self.conversation_history.pop()
                                logger.info(f"✅ BARGE-IN: Removed silence greeting from history: '{removed.get('content')}'")
                            else:
                                logger.info(f"⚠️ BARGE-IN: Last message doesn't look like silence greeting, keeping history")
                    
                    # 3. Clear the flag so we don't trigger this again
                    redis_service.update_call_data(self.call_id, {"silence_greeting_triggered": False})
                    logger.info("✅ BARGE-IN: Reset silence_greeting_triggered flag")
                    
                    # 4. FIX: Return the greeting script directly
                    # The user spoke before/during our greeting - we should just deliver the greeting
                    # and THEN wait for their response. NOT treat their barge-in as a transition.
                    flow_nodes = self.agent_config.get("call_flow", [])
                    
                    # Logic to find the correct content to speak
                    target_node_id = self.current_node_id
                    
                    # Fallback: If no current node (e.g. first interaction), find the start node
                    if not target_node_id and flow_nodes:
                        logger.warning("⚠️ BARGE-IN: current_node_id is missing, attempting to find Start Node...")
                        # 1. Find node with type 'start'
                        start_node = next((n for n in flow_nodes if n.get("type", "").lower() == "start"), None)
                        
                        if start_node:
                            # 2. Find the edge connecting start to the next node
                            # Check both keys just in case
                            edges = self.agent_config.get("call_flow_edges", []) or self.agent_config.get("edges", [])
                            start_edge = next((e for e in edges if e.get("source") == start_node.get("id")), None)
                            
                            if start_edge:
                                target_node_id = start_edge.get("target")
                                logger.info(f"✅ BARGE-IN: Found start node target: {target_node_id}")
                        
                        # 3. Hail Mary: If still no target, look for a node with a greeting-like label
                        if not target_node_id:
                            greeting_node = next((n for n in flow_nodes if n.get("data", {}).get("label", "").lower() in ["greeting", "intro", "introduction", "start"]), None)
                            if greeting_node:
                                target_node_id = greeting_node.get("id")
                                logger.info(f"✅ BARGE-IN: Found greeting node via label: {target_node_id}")
                    
                    content_to_return = None
                    
                    if flow_nodes and target_node_id:
                        for node in flow_nodes:
                            if node.get("id") == target_node_id:
                                node_data = node.get("data", {})
                                # Get script content (conversation nodes use 'script', others use 'content')
                                content = node_data.get("script", "") or node_data.get("content", "")
                                
                                # Replace variables in the greeting (inline, like the rest of the code)
                                for var_name, var_value in self.session_variables.items():
                                    content = content.replace(f"{{{{{var_name}}}}}", str(var_value))
                                
                                if content:
                                    content_to_return = content
                                break
                    
                    if content_to_return:
                        logger.info(f"✅ BARGE-IN: Returning greeting script: '{content_to_return}'")
                        
                        # Add user's message to history (they did speak)
                        self.conversation_history.append({
                            "role": "user",
                            "content": user_text
                        })
                        
                        # Stream the greeting
                        if stream_callback:
                            await stream_callback(content_to_return)
                        
                        # Add greeting to history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": content_to_return,
                            "_node_id": target_node_id or self.current_node_id
                        })
                        
                        return content_to_return
                    else:
                        # CRITICAL: Even if we couldn't find the content, we MUST NOT fall through
                        # to normal processing, because that would treat the interruption ("...")
                        # as a user turn and generate a new LLM response (Double Speak).
                        logger.warning("⚠️ BARGE-IN: Could not find greeting content to return, but preventing fall-through.")
                        return None


                    
            except Exception as e:
                logger.error(f"⚠️ Error in Barge-In Interceptor: {e}")

            
            # ═══════════════════════════════════════════════════════════════════
            # WEBHOOK EXECUTION GUARD: Wait for any executing webhook to complete
            # This prevents race conditions where user speaks during webhook chain
            # and causes stale current_node_id to be used for transition evaluation
            # ═══════════════════════════════════════════════════════════════════
            if self.executing_webhook:
                logger.info(f"⏳ WEBHOOK GUARD: Webhook executing, waiting for completion before processing user input...")
                wait_start = time.time()
                max_wait = 15.0  # Max 15 seconds wait for webhook
                while self.executing_webhook and (time.time() - wait_start) < max_wait:
                    await asyncio.sleep(0.1)
                wait_time = time.time() - wait_start
                if self.executing_webhook:
                    logger.warning(f"⚠️ WEBHOOK GUARD: Timed out after {wait_time:.1f}s, proceeding anyway")
                else:
                    logger.info(f"✅ WEBHOOK GUARD: Webhook completed after {wait_time:.1f}s, proceeding with user input")
            
            # Update {{now}} variable with current date/time in EST
            import pytz
            est = pytz.timezone('America/New_York')
            now_est = datetime.now(est)
            self.session_variables['now'] = now_est.strftime("%A, %B %-d, %Y at %-I:%M %p %Z")
            
            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.info(f"⏱️ [{timestamp_str}] ⏩ About to call _process_call_flow_streaming()")
            
            # Note: conversation_history is already set in server.py if provided
            # Only add current message if it's not already in history
            if not self.conversation_history or self.conversation_history[-1]["content"] != user_text:
                self.conversation_history.append({
                    "role": "user",
                    "content": user_text
                })
            
            # Determine which logic to use based on agent type
            agent_type = self.agent_config.get("agent_type", "single_prompt")
            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.info(f"⏱️ [{timestamp_str}] 🔀 Agent type: {agent_type}, calling flow processor...")
            
            if agent_type == "call_flow":
                # Call Flow Agent - use flow nodes with streaming
                assistant_response = await self._process_call_flow_streaming(user_text, stream_callback)
            else:
                # Single Prompt Agent - use system prompt with streaming
                assistant_response = await self._process_single_prompt_streaming(user_text, stream_callback)
            
            # Check if user gave meaningful response (not just acknowledgment)
            # But ONLY check for acknowledgments if last message was a check-in
            if self.last_message_was_checkin:
                # User is responding to a check-in
                acknowledgment_words = ['yeah', 'yes', 'okay', 'ok', 'yep', 'sure', 'uh-huh', 'mhm', 'go ahead']
                user_words = user_text.lower().strip().split()
                is_acknowledgment = (
                    len(user_words) <= 2 and 
                    any(word in acknowledgment_words for word in user_words)
                )
                
                if not is_acknowledgment:
                    # User gave meaningful response to check-in - reset counter and resume flow
                    self.reset_silence_tracking()
                    logger.info(f"✅ User gave meaningful response to check-in, resetting counter")
                else:
                    # User only acknowledged check-in - keep counter, will check-in again
                    logger.info(f"⚠️ User gave acknowledgment only to check-in, keeping counter at {self.checkin_count}")
                
                # Clear the flag now that we've handled the response
                self.last_message_was_checkin = False
            else:
                # User is responding to regular message - always reset counter
                self.reset_silence_tracking()
                logger.info(f"✅ User responded to regular message, resetting counter")
            
            # Add assistant response to conversation history
            assistant_msg = {
                "role": "assistant",
                "content": assistant_response
            }
            
            # For call flow agents, include the current node ID for state tracking
            if agent_type == "call_flow" and self.current_node_id:
                assistant_msg["_node_id"] = self.current_node_id
                logger.info(f"💾 Storing node ID {self.current_node_id} in conversation history")
            
            self.conversation_history.append(assistant_msg)
            
            # Calculate LLM latency
            llm_latency = time.time() - latency_start
            logger.info(f"LLM response ({llm_latency:.2f}s): {assistant_response}")
            
            # Calculate total latency
            total_latency = time.time() - latency_start
            logger.info(f"Total latency: {total_latency:.2f}s")
            
            # Return response with node info and timing metrics for QC analysis
            return {
                "text": assistant_response,
                "latency": total_latency,
                "end_call": self.should_end_call,
                # Node information for QC reports
                "node_id": self.current_node_id,
                "node_label": self.current_node_label or "Unknown",
                # Timing metrics for accurate latency analysis
                "transition_time_ms": self.last_transition_time_ms,
                "kb_time_ms": self.last_kb_time_ms
            }
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return None
    
    async def _process_single_prompt_streaming(self, user_text: str, stream_callback=None):
        """Process with single prompt mode and stream sentences"""
        import re
        import datetime
        
        # Build conversation history
        messages = []
        system_prompt = self.agent_config.get("system_prompt", "You are a helpful assistant.")
        
        # Add knowledge base to system prompt if available
        if self.knowledge_base:
            system_prompt += f"\n\n=== KNOWLEDGE BASE ===\nYou have access to multiple reference sources below. Each source serves a different purpose.\n\n🧠 HOW TO USE THE KNOWLEDGE BASE:\n1. When user asks a question, FIRST identify which knowledge base source(s) are relevant based on their descriptions\n2. Read ONLY the relevant source(s) to find the answer\n3. Use ONLY information from the knowledge base - do NOT make up or improvise ANY factual details\n4. If the knowledge base doesn't contain the answer, say: \"I don't have that specific information available\"\n5. Different sources contain different types of information - match the user's question to the right source\n\n⚠️ NEVER invent: company names, product names, prices, processes, methodologies, or any factual information not in the knowledge base\n\n{self.knowledge_base}\n=== END KNOWLEDGE BASE ===\n"
        
        messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history)
        
        llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
        if not llm_provider:
            logger.error("❌ No LLM provider configured for agent")
            return None
        model = self.agent_config.get("model", "gpt-4-turbo")
        
        # Validate model matches provider and fix if mismatched
        grok_models = ["grok-4-1-fast-non-reasoning", "grok-4-fast-non-reasoning", "grok-4-fast-reasoning", "grok-3", "grok-2-1212", "grok-beta", "grok-4-fast"]
        openai_models = ["gpt-4.1-2025-04-14", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
        
        if llm_provider == "grok":
            if model not in grok_models:
                logger.warning(f"⚠️  Model '{model}' not valid for Grok, using 'grok-3'")
                model = "grok-3"
        else:
            if model in grok_models:
                logger.warning(f"⚠️  Model '{model}' is a Grok model but provider is OpenAI, using 'gpt-4-turbo'")
                model = "gpt-4-turbo"
        
        logger.info(f"🤖 Using LLM provider: {llm_provider}, model: {model}")
        
        # Get appropriate client
        if llm_provider == "grok":
            client = await self.get_llm_client_for_session("grok")
        else:
            client = await self.get_llm_client_for_session("openai")
        
        if not client:
            raise Exception(f"{llm_provider} client not configured")
        
        # Stream LLM response and process sentence by sentence
        llm_request_start = time.time()
        
        if llm_provider == "grok":
            response = await client.create_completion(
                messages=messages,
                model=model,
                temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 300),
                stream=True
            )
        else:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 300),
                stream=True
            )
        
        # Collect response and stream sentences
        full_response = ""
        sentence_buffer = ""
        first_token_received = False
        
        # Sentence delimiters - expanded to handle run-on sentences
        # Primary: .!? (strong boundaries)
        # Secondary: , — ; (weak boundaries after 2s timeout)
        sentence_endings = re.compile(r'([.!?]\s+|[,—;]\s+)')
        
        async for chunk in response:
            if not first_token_received:
                ttft_ms = int((time.time() - llm_request_start) * 1000)
                timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                logger.info(f"⏱️ [{timestamp_str}] 💬 LLM FIRST TOKEN: {ttft_ms}ms ({llm_provider} {model})")
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
                            # Stream this sentence immediately to TTS
                            await stream_callback(sentence)
                            logger.info(f"📤 Streamed sentence: {sentence[:50]}...")
                
                # Keep the last incomplete part in buffer
                sentence_buffer = sentences[-1] if len(sentences) % 2 != 0 else ""
        
        # Send any remaining text
        if sentence_buffer.strip() and stream_callback:
            await stream_callback(sentence_buffer.strip())
            logger.info(f"📤 Streamed final fragment: {sentence_buffer[:50]}...")
        
        # ⏱️ TIMING: Total LLM response time
        llm_total_ms = int((time.time() - llm_request_start) * 1000)
        logger.info(f"⏱️ [TIMING] LLM_TOTAL: {llm_total_ms}ms for {len(full_response)} chars ({llm_provider} {model})")
        
        return full_response
    
    async def _process_single_prompt(self, user_message: str) -> str:
        """Process using traditional single system prompt"""
        try:
            import datetime
            system_prompt = self.agent_config.get("system_prompt", "You are a helpful AI assistant.")
            
            # Add knowledge base to system prompt if available
            if self.knowledge_base:
                system_prompt += f"\n\n=== KNOWLEDGE BASE ===\nYou have access to multiple reference sources below. Each source serves a different purpose.\n\n🧠 HOW TO USE THE KNOWLEDGE BASE:\n1. When user asks a question, FIRST identify which knowledge base source(s) are relevant based on their descriptions\n2. Read ONLY the relevant source(s) to find the answer\n3. Use ONLY information from the knowledge base - do NOT make up or improvise ANY factual details\n4. If the knowledge base doesn't contain the answer, say: \"I don't have that specific information available\"\n5. Different sources contain different types of information - match the user's question to the right source\n\n⚠️ NEVER invent: company names, product names, prices, processes, methodologies, or any factual information not in the knowledge base\n\n{self.knowledge_base}\n=== END KNOWLEDGE BASE ===\n"
            
            messages = [
                {"role": "system", "content": system_prompt}
            ] + self.conversation_history  # Full history with 2M context window
            
            # Get LLM provider from agent settings
            llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
            if not llm_provider:
                logger.error("❌ No LLM provider configured for agent")
                return None
            model = self.agent_config.get("model", "gpt-4-turbo")
            
            # Validate model matches provider and fix if mismatched
            grok_models = ["grok-4-1-fast-non-reasoning", "grok-4-fast-non-reasoning", "grok-4-fast-reasoning", "grok-3", "grok-2-1212", "grok-beta", "grok-4-fast"]
            openai_models = ["gpt-4.1-2025-04-14", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
            
            if llm_provider == "grok":
                if model not in grok_models:
                    logger.warning(f"⚠️  Model '{model}' not valid for Grok, using 'grok-3'")
                    model = "grok-3"
            else:
                if model in grok_models:
                    logger.warning(f"⚠️  Model '{model}' is a Grok model but provider is OpenAI, using 'gpt-4-turbo'")
                    model = "gpt-4-turbo"
            
            logger.info(f"🤖 Using LLM provider: {llm_provider}, model: {model}")
            
            # Get appropriate client
            if llm_provider == "grok":
                client = await self.get_llm_client_for_session("grok")
            else:
                client = await self.get_llm_client_for_session("openai")
                
            if not client:
                raise Exception(f"{llm_provider} client not configured")
            
            # ⏱️  Track LLM TTFT (Time-To-First-Token)
            llm_request_start = time.time()
            
            # Use the appropriate client method WITH STREAMING for faster TTFT
            if llm_provider == "grok":
                response = await client.create_completion(
                    messages=messages,
                    model=model,
                    temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                    max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 500),
                    stream=True
                )
                
                # Collect streamed response
                full_response = ""
                first_token_received = False
                async for chunk in response:
                    if not first_token_received:
                        ttft_ms = int((time.time() - llm_request_start) * 1000)
                        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        logger.info(f"⏱️ [{timestamp_str}] 💬 LLM FIRST TOKEN: {ttft_ms}ms ({llm_provider} {model})")
                        first_token_received = True
                    
                    if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            full_response += delta.content
                
                return full_response
            else:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                    max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 500),
                    stream=True
                )
                
                # Collect streamed response and track TTFT
                full_response = ""
                first_token_received = False
                async for chunk in response:
                    if not first_token_received:
                        ttft_ms = int((time.time() - llm_request_start) * 1000)
                        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        logger.info(f"⏱️ [{timestamp_str}] 💬 LLM FIRST TOKEN: {ttft_ms}ms ({llm_provider} {model})")
                        first_token_received = True
                    
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                
                return full_response
        except Exception as e:
            logger.error(f"Error in single prompt: {e}")
            return "I apologize, but I'm having trouble processing your request."
    
    async def _process_call_flow_streaming(self, user_message: str, stream_callback=None) -> str:
        """Process using call flow nodes with streaming support"""
        try:
            from datetime import datetime
            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.info(f"⏱️ [{timestamp_str}] 🔀 _process_call_flow_streaming() ENTRY")
            
            flow_nodes = self.agent_config.get("call_flow", [])
            
            if not flow_nodes:
                logger.warning("No flow nodes, falling back to single prompt streaming")
                return await self._process_single_prompt_streaming(user_message, stream_callback)
            
            selected_node = None
            
            # Reset per-turn timing metrics
            self.last_transition_time_ms = 0
            self.last_kb_time_ms = 0
            
            # Determine if this is first message based on history length BEFORE adding current message
            # (conversation_history gets set in server.py, then current message added in process_user_input)
            is_first_message = len(self.conversation_history) <= 1
            
            logger.info(f"Flow processing - History length: {len(self.conversation_history)}, Is first: {is_first_message}")
            
            # Check if we have an explicitly set current_node_id for transition testing
            # In this case, we want to EVALUATE TRANSITION from that node, not respond from it
            if self.current_node_id and is_first_message:
                logger.info(f"🎯 Transition test mode: Current node is {self.current_node_id}, evaluating transition FROM this node...")
                
                # Find the current node (the one we're transitioning FROM)
                from_node = None
                for node in flow_nodes:
                    if node.get("id") == self.current_node_id:
                        from_node = node
                        break
                
                if from_node:
                    from_node_label = from_node.get("data", {}).get("label") or from_node.get("label", self.current_node_id)
                    logger.info(f"🎯 Evaluating transitions FROM node: {from_node_label}")
                    
                    # Use the proper _follow_transition method for full LLM-based evaluation
                    # This handles affirmative/negative caching, variable checks, and LLM evaluation
                    transition_start = time.time()
                    selected_node = await self._follow_transition(from_node, user_message, flow_nodes)
                    transition_ms = int((time.time() - transition_start) * 1000)
                    self.last_transition_time_ms = transition_ms
                    
                    if selected_node and selected_node.get("id") != from_node.get("id"):
                        # Successfully transitioned to a new node
                        to_node_label = selected_node.get("data", {}).get("label") or selected_node.get("label", selected_node.get("id"))
                        logger.info(f"✅ Transition test: {from_node_label} -> {to_node_label} (took {transition_ms}ms)")
                        self.current_node_id = selected_node.get("id")
                    else:
                        # No transition found or stayed at same node
                        logger.warning(f"⚠️ No transition matched from {from_node_label}, staying at current node")
                        selected_node = from_node
                else:
                    logger.warning(f"⚠️ Start node {self.current_node_id} not found in call flow")
            
            # Normal first message logic (when no explicit current_node_id set)
            elif is_first_message:
                # If no explicit node set, use normal first message logic
                if not selected_node:
                    # Find start node
                    start_node = None
                    for node in flow_nodes:
                        if node.get("type", "").lower() == "start":
                            start_node = node
                            break
                    
                    # Handle start node settings
                    if start_node:
                        start_data = start_node.get("data", {})
                        who_speaks_first = start_data.get("whoSpeaksFirst", "user")
                        
                        # If AI speaks first, find first conversation node
                        if who_speaks_first == "ai":
                            for node in flow_nodes:
                                if node.get("type") == "conversation":
                                    selected_node = node
                                    break
                        # If user speaks first, we're in this function, so find matching node
                    
                    # Find first interactive node for response (conversation, collect_input, press_digit, or extract_variable)
                    if not selected_node:
                        for node in flow_nodes:
                            node_type = node.get("type", "").lower()
                            if node_type in ["conversation", "collect_input", "press_digit", "extract_variable"]:
                                selected_node = node
                                break
            else:
                # Subsequent messages - follow transitions from current node
                # Extract last node from conversation history OR use explicitly set current_node_id
                current_node_id = None
                
                # FIRST: Check if current_node_id is explicitly set (e.g., from transition test mode)
                if self.current_node_id:
                    current_node_id = self.current_node_id
                    logger.info(f"🔍 Using explicitly set current_node_id: {current_node_id}")
                # SECOND: Try to get from conversation history
                elif self.conversation_history:
                    for msg in reversed(self.conversation_history):
                        if msg.get("role") == "assistant" and "_node_id" in msg:
                            current_node_id = msg.get("_node_id")
                            break
                    if current_node_id:
                        logger.info(f"🔍 Current node ID from history: {current_node_id}")
                
                # Find the current node
                current_node = None
                if current_node_id:
                    for node in flow_nodes:
                        if node.get("id") == current_node_id:
                            current_node = node
                            break
                
                # If no current node found, start from first conversation node
                if not current_node:
                    logger.warning("No current node in history, starting from first conversation node")
                    current_node = await self._get_first_conversation_node(flow_nodes)
                
                if current_node:
                    # Check if current node is a collect_input node that needs processing
                    current_node_type = current_node.get("type", "")
                    if current_node_type == "collect_input":
                        # Process collect_input node first
                        selected_node = current_node
                        self.last_transition_time_ms = 0  # No transition for collect_input
                    else:
                        # ═══════════════════════════════════════════════════════════════════
                        # PRE-TRANSITION MANDATORY VARIABLE CHECK
                        # CRITICAL: Extract variables on CURRENT node BEFORE transitioning
                        # This ensures we capture user's response to reprompt questions
                        # ═══════════════════════════════════════════════════════════════════
                        current_node_data = current_node.get("data", {})
                        if current_node_type == "conversation":
                            current_extract_vars = current_node_data.get("extract_variables", [])
                            if current_extract_vars and len(current_extract_vars) > 0:
                                has_mandatory = any(var.get("mandatory", False) for var in current_extract_vars)
                                if has_mandatory:
                                    logger.info(f"🔍 PRE-TRANSITION: Extracting mandatory vars on CURRENT node {current_node.get('label')} before transition")
                                    extraction_result = await self._extract_variables_realtime(current_extract_vars, user_message)
                                    
                                    if not extraction_result.get("success", True):
                                        # Mandatory variables STILL missing after extraction
                                        # Stay on current node - DO NOT transition
                                        logger.info(f"⚠️ PRE-TRANSITION: Mandatory vars still missing - BLOCKING transition, staying on {current_node.get('label')}")
                                        selected_node = current_node
                                        self.last_transition_time_ms = 0
                                        # Jump to node processing (skip transition logic below)
                                        # The mandatory check at line 1305 will generate reprompt
                                    else:
                                        logger.info(f"✅ PRE-TRANSITION: All mandatory vars satisfied on {current_node.get('label')} - proceeding with transition")
                        
                        # Only proceed with transition if we didn't block above
                        if selected_node is None:
                            # Check if node has auto-transition enabled (skip LLM evaluation, save ~574ms)
                            auto_transition_node_id = current_node_data.get("auto_transition_to")
                        
                            if auto_transition_node_id:
                                # Skip transition evaluation entirely, go directly to specified node
                                logger.info(f"⚡ AUTO-TRANSITION enabled - skipping evaluation, moving to node: {auto_transition_node_id}")
                                selected_node = self._get_node_by_id(auto_transition_node_id, flow_nodes)
                                self.last_transition_time_ms = 0  # Auto-transition is instant
                                if selected_node:
                                    logger.info(f"✅ Auto-transitioned to: {selected_node.get('label', 'unnamed')}")
                                else:
                                    logger.warning(f"⚠️ Auto-transition target not found: {auto_transition_node_id}, using default transition logic")
                                    # Fallback to normal transition logic
                                    transition_start = time.time()
                                    selected_node = await self._follow_transition(current_node, user_message, flow_nodes)
                                    transition_ms = int((time.time() - transition_start) * 1000)
                                    self.last_transition_time_ms = transition_ms
                                    logger.info(f"⏱️ [TIMING] TRANSITION_EVAL: {transition_ms}ms")
                            else:
                                # Normal transition evaluation with LLM
                                timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                logger.info(f"⏱️ [{timestamp_str}] 🔀 About to call _follow_transition() for: {user_message[:30]}...")
                                logger.info(f"Evaluating transitions from {current_node.get('label')} for message: {user_message}")
                                
                                # ⏱️ TIMING: Transition evaluation start
                                transition_start = time.time()
                                selected_node = await self._follow_transition(current_node, user_message, flow_nodes)
                                transition_ms = int((time.time() - transition_start) * 1000)
                                self.last_transition_time_ms = transition_ms  # Store for QC analysis
                                logger.info(f"⏱️ [TIMING] TRANSITION_EVAL: {transition_ms}ms")
                else:
                    selected_node = await self._get_first_conversation_node(flow_nodes)
            
            if selected_node:
                timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                logger.info(f"⏱️ [{timestamp_str}] ✅ Node selected, about to process content...")
                
                # Save the node_id BEFORE processing - function nodes may update it via recursion
                pre_processing_node_id = self.current_node_id
                
                # Update current node position and label for QC tracking
                self.current_node_id = selected_node.get("id")
                self.current_node_label = selected_node.get("label", selected_node.get("id", "Unknown"))
                node_data = selected_node.get("data", {})
                node_type = selected_node.get("type", "")
                
                # Get the actual script content, not the prompt field
                if node_type == "conversation":
                    content = node_data.get("script", "") or node_data.get("content", "")
                else:
                    content = node_data.get("content", "") or node_data.get("script", "")
                
                # Replace variables in content BEFORE processing
                for var_name, var_value in self.session_variables.items():
                    content = content.replace(f"{{{{{var_name}}}}}", str(var_value))
                    logger.info(f"🔧 Replaced {{{{{var_name}}}}} with {var_value} in content")
                
                # Smart detection of mode: if content is very long or has instructions, it's "prompt" mode
                # Get mode from data (can be "prompt" or "script") - check both possible field names
                prompt_type = node_data.get("mode")
                if prompt_type is None:
                    prompt_type = node_data.get("promptType")
                
                # ONLY auto-detect if mode is None or empty - NEVER override explicit script mode
                # Script mode must be respected regardless of content length
                if prompt_type is None or prompt_type == "":
                    # If content contains instruction markers, treat as prompt
                    if any(marker in content.lower() for marker in [
                        "## ", "### ", "instructions:", "goal:", "objective:", "**important**", 
                        "you are", "your task", "rules:", "primary goal", "**no dashes"
                    ]):
                        prompt_type = "prompt"
                        logger.info(f"🔍 Auto-detected PROMPT mode (instruction markers found)")
                    else:
                        prompt_type = "script"
                        logger.info(f"🔍 Auto-detected SCRIPT mode (no instruction markers, length: {len(content)} chars)")
                elif prompt_type == "script":
                    logger.info(f"✅ Using explicit SCRIPT mode (length: {len(content)} chars) - will return text instantly")
                
                logger.info(f"Using flow node: {selected_node.get('label', 'unnamed')} (type: {node_type}, mode: {prompt_type})")
                
                # Handle function/webhook node FIRST - before any content processing
                # Function nodes don't need content, they execute webhooks
                if node_type == "function":
                    logger.info("🔧 Function/Webhook node reached - executing webhook")
                    
                    # Check if we should speak during execution
                    speak_during_execution = node_data.get("speak_during_execution", False)
                    dialogue_text = node_data.get("dialogue_text", "")
                    dialogue_type = node_data.get("dialogue_type", "static")
                    wait_for_result = node_data.get("wait_for_result", True)
                    
                    dialogue_response = ""
                    
                    # Generate and speak dialogue if enabled
                    if speak_during_execution and dialogue_text:
                        logger.info(f"💬 Generating dialogue before webhook execution (type: {dialogue_type})")
                        
                        if dialogue_type == "static":
                            # Use exact text provided
                            dialogue_response = dialogue_text
                            logger.info(f"📢 Static dialogue: {dialogue_response[:50]}...")
                        else:
                            # AI-generated dialogue based on prompt
                            logger.info(f"🤖 Generating AI dialogue from prompt: {dialogue_text[:50]}...")
                            dialogue_response = await self._generate_ai_response_streaming(dialogue_text, stream_callback)
                        
                        # NOTE: Do NOT call stream_callback again here!
                        # _generate_ai_response_streaming already streams sentences as they're generated.
                        # Calling stream_callback(dialogue_response) would duplicate the entire message.
                        # For static dialogue, stream it since it wasn't streamed yet
                        if dialogue_type == "static" and stream_callback and dialogue_response:
                            await stream_callback(dialogue_response)
                    
                    # Execute webhook based on wait_for_result setting
                    # NOTE: Keep executing_webhook TRUE through entire chain including recursive calls
                    was_already_executing = self.executing_webhook
                    if wait_for_result:
                        # Wait for webhook to complete before transitioning
                        logger.info("⏳ Waiting for webhook to complete before transitioning...")
                        # Pause dead air monitoring during webhook execution
                        self.executing_webhook = True
                        try:
                            webhook_response = await self._execute_webhook(node_data, user_message)
                            
                            # Check if webhook requires re-prompt (missing required variables)
                            if webhook_response.get("requires_reprompt"):
                                logger.warning("🔁 Webhook requires re-prompt - staying on same node")
                                # Don't transition, return the re-prompt message
                                return webhook_response.get("message", "I need more information to proceed.")
                            
                            # After webhook, transition to next node (still within try block to keep flag)
                            if node_data.get("transitions"):
                                # CRITICAL: Pass webhook_response to transition evaluation for function nodes
                                # This allows transitions to be evaluated based on the webhook result, not user message
                                logger.info(f"🔀 Evaluating transition for function node with webhook response...")
                                next_node = await self._follow_transition(selected_node, user_message, flow_nodes, webhook_response=webhook_response)
                                if next_node and next_node.get("id") != selected_node.get("id"):
                                    # Recursively process the next node (keep webhook flag TRUE)
                                    self.current_node_id = next_node.get("id")
                                    self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", next_node.get("id", "Unknown")))
                                    logger.info(f"📍 Function node recursion: Updated current_node to {self.current_node_label}")
                                    return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
                            
                            # If we had dialogue, return that, otherwise return webhook message
                            if dialogue_response:
                                return dialogue_response
                            else:
                                return webhook_response.get("message", "Function executed successfully")
                        finally:
                            # Only reset flag if we were the one who set it
                            if not was_already_executing:
                                self.executing_webhook = False
                    else:
                        # Execute webhook async and transition immediately
                        logger.info("🚀 Executing webhook async, transitioning immediately...")
                        import asyncio
                        asyncio.create_task(self._execute_webhook(node_data, user_message))
                        webhook_response = {"success": True, "message": "Webhook executing in background"}
                        
                        # After async webhook start, transition to next node
                        if node_data.get("transitions"):
                            logger.info(f"🔀 Evaluating transition for function node (async webhook)...")
                            next_node = await self._follow_transition(selected_node, user_message, flow_nodes, webhook_response=webhook_response)
                            if next_node and next_node.get("id") != selected_node.get("id"):
                                self.current_node_id = next_node.get("id")
                                self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", next_node.get("id", "Unknown")))
                                logger.info(f"📍 Function node recursion: Updated current_node to {self.current_node_label}")
                                return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
                        
                        if dialogue_response:
                            return dialogue_response
                        else:
                            return webhook_response.get("message", "Function executed successfully")
                
                # Handle ending node - special case
                if node_type == "ending":
                    logger.info("🛑 Ending node reached - call should terminate")
                    # Add a marker that call should end
                    self.should_end_call = True
                
                # Handle transfer call node - special case
                if node_type in ["call_transfer", "agent_transfer"]:
                    logger.info("📞 Transfer node reached - initiating transfer")
                    transfer_info = self._handle_transfer(node_data)
                    
                    # Store transfer request in session variables
                    self.session_variables["transfer_requested"] = True
                    self.session_variables["transfer_info"] = transfer_info
                    
                    # Return transfer message
                    return transfer_info.get("message", "Please hold while I transfer your call...")
                
                # Handle collect input node - special case
                if node_type == "collect_input":
                    logger.info("📝 Collect Input node reached - gathering user input")
                    collect_result = self._handle_collect_input(node_data, user_message)
                    
                    if collect_result.get("valid"):
                        # Store collected value and move to next node
                        variable_name = node_data.get("variable_name", "user_input")
                        self.session_variables[variable_name] = collect_result.get("value")
                        logger.info(f"✅ Collected and stored {variable_name}: {collect_result.get('value')}")
                        
                        # Keep customer_name and callerName in sync (bidirectional)
                        if variable_name == "customer_name":
                            self.session_variables["callerName"] = collect_result.get("value")
                            logger.info(f"✅ callerName synced")
                        elif variable_name == "callerName":
                            self.session_variables["customer_name"] = collect_result.get("value")
                            logger.info(f"✅ customer_name synced")
                        
                        # Transition to next node if available
                        if node_data.get("transitions"):
                            next_node = await self._follow_transition(selected_node, user_message, flow_nodes)
                            if next_node and next_node.get("id") != selected_node.get("id"):
                                self.current_node_id = next_node.get("id")
                                self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", next_node.get("id", "Unknown")))
                                return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
                        
                        return collect_result.get("success_message", "Thank you, I have that information.")
                    else:
                        # Invalid input - prompt again
                        logger.info(f"❌ Invalid input: {collect_result.get('error')}")
                        return collect_result.get("error_message", "I didn't understand that. Please try again.")
                
                # Handle send SMS node - special case
                if node_type == "send_sms":
                    logger.info("📱 Send SMS node reached - sending message")
                    sms_result = await self._handle_send_sms(node_data, user_message)
                    
                    # Store SMS status in session variables
                    self.session_variables["sms_sent"] = sms_result.get("success", False)
                    self.session_variables["sms_status"] = sms_result.get("status", "pending")
                    
                    # Transition to next node if available
                    if node_data.get("transitions"):
                        next_node = await self._follow_transition(selected_node, user_message, flow_nodes)
                        if next_node and next_node.get("id") != selected_node.get("id"):
                            self.current_node_id = next_node.get("id")
                            self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", next_node.get("id", "Unknown")))
                            return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
                    
                    return sms_result.get("message", "I've sent you an SMS.")
                
                # Handle logic split node - special case
                if node_type == "logic_split":
                    logger.info("🔀 Logic Split node reached - evaluating conditions")
                    
                    # Evaluate conditions and get next node
                    next_node_id = self._evaluate_logic_conditions(node_data)
                    
                    if next_node_id:
                        next_node = self._get_node_by_id(next_node_id, flow_nodes)
                        if next_node:
                            logger.info(f"✅ Condition matched - moving to node: {next_node.get('label')}")
                            self.current_node_id = next_node_id
                            self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", next_node_id))
                            return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
                    
                    # No condition matched - return default message
                    return "Let me help you with that."
                
                # Handle press digit node - special case
                if node_type == "press_digit":
                    logger.info("🔢 Press Digit node reached - processing DTMF input")
                    digit_result = self._handle_press_digit(node_data, user_message)
                    
                    if digit_result.get("next_node_id"):
                        next_node = self._get_node_by_id(digit_result["next_node_id"], flow_nodes)
                        if next_node:
                            logger.info(f"✅ Digit {digit_result['digit']} pressed - routing to node: {next_node.get('label')}")
                            self.current_node_id = digit_result["next_node_id"]
                            self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", digit_result["next_node_id"]))
                            return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
                    
                    return digit_result.get("message", "Please press a digit.")
                
                # Handle extract variable node - special case
                if node_type == "extract_variable":
                    logger.info("📋 Extract Variable node reached - extracting data")
                    extract_result = await self._handle_extract_variable(node_data, user_message)
                    
                    if extract_result.get("success"):
                        # Store extracted value
                        variable_name = node_data.get("variable_name", "extracted_data")
                        self.session_variables[variable_name] = extract_result.get("value")
                        logger.info(f"✅ Extracted {variable_name}: {extract_result.get('value')}")
                        
                        # Keep customer_name and callerName in sync (bidirectional)
                        if variable_name == "customer_name":
                            self.session_variables["callerName"] = extract_result.get("value")
                            logger.info(f"✅ callerName synced")
                        elif variable_name == "callerName":
                            self.session_variables["customer_name"] = extract_result.get("value")
                            logger.info(f"✅ customer_name synced")
                        
                        # Transition to next node
                        if node_data.get("transitions"):
                            next_node = await self._follow_transition(selected_node, user_message, flow_nodes)
                            if next_node and next_node.get("id") != selected_node.get("id"):
                                self.current_node_id = next_node.get("id")
                                self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", next_node.get("id", "Unknown")))
                                return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
                        
                        return extract_result.get("message", "Got it.")
                    
                    return "Could you please provide that information again?"
                
                # ═══════════════════════════════════════════════════════════════════
                # MANDATORY VARIABLE CHECK - BEFORE generating response
                # For nodes with mandatory variables, we must extract and validate
                # BEFORE speaking, so we can reprompt if something is missing
                # ═══════════════════════════════════════════════════════════════════
                # 🔥 CONFIGURABLE: Check for node-level setting to skip pre-response mandatory check
                # This is useful for Q&A/KB nodes where the agent should answer the user's
                # question first, and only check mandatory variables on transition.
                # Set "skip_mandatory_precheck": true in node settings to enable this behavior.
                skip_mandatory_precheck = node_data.get("skip_mandatory_precheck", False)
                
                # Also check for legacy label-based detection as fallback
                node_label = selected_node.get("label", "").lower() if selected_node else ""
                is_qa_or_kb_node = "q&a" in node_label or "kb" in node_label or "knowledge" in node_label
                
                should_skip_precheck = skip_mandatory_precheck or is_qa_or_kb_node
                
                if node_type == "conversation" and not should_skip_precheck:
                    extract_variables = node_data.get("extract_variables", [])
                    if extract_variables and len(extract_variables) > 0:
                        has_mandatory = any(var.get("mandatory", False) for var in extract_variables)
                        
                        if has_mandatory:
                            logger.info(f"🔍 PRE-RESPONSE: Checking {len(extract_variables)} variables ({sum(1 for v in extract_variables if v.get('mandatory'))} mandatory)")
                            extraction_result = await self._extract_variables_realtime(extract_variables, user_message)
                            
                            if not extraction_result.get("success", True):
                                # Mandatory variable missing - reprompt BEFORE generating normal response
                                reprompt = extraction_result.get("reprompt_message", "Could you please provide more information?")
                                missing_vars = extraction_result.get("missing_variables", [])
                                logger.info(f"⚠️ PRE-RESPONSE: Mandatory variables missing: {missing_vars} - sending reprompt instead of normal response")
                                
                                # Stream the reprompt as the response
                                if stream_callback:
                                    await stream_callback(reprompt)
                                return reprompt
                            else:
                                logger.info(f"✅ PRE-RESPONSE: All mandatory variables present, proceeding with response")
                elif should_skip_precheck:
                    if skip_mandatory_precheck:
                        logger.info(f"📚 skip_mandatory_precheck=true - skipping pre-response mandatory check, will check on transition")
                    else:
                        logger.info(f"📚 Q&A/KB node detected by label - skipping pre-response mandatory check, will check on transition")
                
                # Handle script vs prompt mode
                timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                logger.info(f"⏱️ [{timestamp_str}] 📄 About to process content (mode={prompt_type}, length={len(content)})")
                
                # 🔥 FIX: Check if we STAYED on the same node (no transition matched)
                # This prevents re-speaking script content when user's response didn't trigger a transition
                stayed_on_same_node = (
                    not is_first_message and 
                    pre_processing_node_id is not None and
                    selected_node.get("id") == pre_processing_node_id
                )
                
                if stayed_on_same_node and prompt_type == "script":
                    dynamic_rephrase = node_data.get("dynamic_rephrase", False)
                    
                    if dynamic_rephrase:
                        # Generate a rephrased version of the script
                        rephrase_prompt = node_data.get("rephrase_prompt", "")
                        logger.info(f"🔄 Dynamic rephrase enabled - generating natural variation of script")
                        response_text = await self._generate_rephrased_script(content, user_message, rephrase_prompt)
                        if stream_callback:
                            await stream_callback(response_text)
                        # Add to conversation history and return
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response_text,
                            "_node_id": self.current_node_id
                        })
                        logger.info(f"🔄 Rephrased script: {response_text[:100]}...")
                        return response_text
                    else:
                        # FIX: Prevent "Dead Air" when user input doesn't trigger transition
                        # Instead of returning empty string (silence), generate a contextual acknowledgment
                        logger.info(f"🛡️ Preventing Dead Air: User stayed on script node '{selected_node.get('label')}' without transition")
                        
                        # Create a prompt that acknowledges the user but keeps them on track
                        prevention_prompt = (
                            f"The user said '{user_message}'. They are currently at a node with this script: '{content}'. "
                            f"However, they did not answer the question or trigger a transition. "
                            f"Briefly acknowledge what they said (e.g. 'I hear you', 'Right', 'I understand'), "
                            f"and then gently nudge them to answer the script's question or move forward. "
                            f"DO NOT repeat the script verbatim. Keep it conversational and under 2 sentences."
                        )
                        
                        logger.info(f"🤖 Generating sticky-prevention response...")
                        response_text = await self._generate_ai_response_streaming(prevention_prompt, stream_callback, selected_node)
                        return response_text
                
                # Generate and stream the response
                response_text = ""
                if prompt_type == "script":
                    # 🚀 STREAMING FIX: Split script into sentences and stream each one
                    # This allows TTS to start playing the first sentence immediately
                    # instead of waiting for the entire script to be processed
                    if stream_callback:
                        import re
                        # Split by sentence-ending punctuation (., !, ?) followed by space or end
                        # Keep the punctuation with the sentence
                        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
                        sentences = [s.strip() for s in sentences if s.strip()]
                        
                        if sentences:
                            logger.info(f"📤 Streaming script as {len(sentences)} sentence(s)")
                            for i, sentence in enumerate(sentences):
                                await stream_callback(sentence)
                                logger.info(f"📤 Streamed script sentence {i+1}/{len(sentences)}: {sentence[:50]}...")
                        else:
                            # Fallback if no sentences detected
                            await stream_callback(content)
                            logger.info(f"📤 Streamed script content (no sentences): {content[:50]}...")
                    response_text = content
                else:
                    # Prompt mode - use AI to generate response based on instructions with streaming
                    response_text = await self._generate_ai_response_streaming(content, stream_callback, selected_node)
                
                # AFTER agent has spoken, extract NON-MANDATORY variables in background (non-blocking)
                # Mandatory variables were already extracted above before we spoke
                if node_type == "conversation":
                    extract_variables = node_data.get("extract_variables", [])
                    if extract_variables and len(extract_variables) > 0:
                        has_mandatory = any(var.get("mandatory", False) for var in extract_variables)
                        
                        # Extract in background if NO mandatory variables OR if we explicitly skipped the precheck
                        # This ensures that if we skipped precheck, we still attempt to extract the values for future use
                        if not has_mandatory or should_skip_precheck:
                            logger.info(f"🔍 Extracting {len(extract_variables)} variables AFTER response (non-blocking) [has_mandatory={has_mandatory}, skipped_precheck={should_skip_precheck}]")
                            import asyncio
                            asyncio.create_task(self._extract_variables_background(extract_variables, user_message))
                            logger.info(f"🚀 Variable extraction started in background")
                
                return response_text
            else:
                logger.warning("No suitable node found, falling back")
                return await self._process_single_prompt_streaming(user_message, stream_callback)
                
        except Exception as e:
            logger.error(f"Error in call flow streaming: {e}")
            return await self._process_single_prompt_streaming(user_message, stream_callback)
    
    async def _process_call_flow(self, user_message: str) -> str:
        """Process using call flow nodes"""
        try:
            flow_nodes = self.agent_config.get("call_flow", [])
            
            if not flow_nodes:
                logger.warning("No flow nodes, falling back to single prompt")
                return await self._process_single_prompt(user_message)
            
            selected_node = None
            
            # Determine if this is first message based on history length BEFORE adding current message
            # (conversation_history gets set in server.py, then current message added in process_user_input)
            is_first_message = len(self.conversation_history) <= 1
            
            logger.info(f"Flow processing - History length: {len(self.conversation_history)}, Is first: {is_first_message}")
            
            # First message - check start node settings OR use explicitly set current_node_id
            if is_first_message:
                # FIRST: Check if current_node_id is explicitly set (e.g., from transition test mode)
                if self.current_node_id:
                    logger.info(f"🎯 First message but using explicitly set start node: {self.current_node_id}")
                    for node in flow_nodes:
                        if node.get("id") == self.current_node_id:
                            selected_node = node
                            logger.info(f"✅ Starting from explicit node: {node.get('label', node.get('id', 'unknown'))}")
                            break
                
                # If no explicit node set, use normal first message logic
                if not selected_node:
                    # Find start node
                    start_node = None
                    for node in flow_nodes:
                        if node.get("type", "").lower() == "start":
                            start_node = node
                            break
                    
                    # Handle start node settings
                    if start_node:
                        start_data = start_node.get("data", {})
                        who_speaks_first = start_data.get("whoSpeaksFirst", "user")
                        
                        # If AI speaks first, find first conversation node
                        if who_speaks_first == "ai":
                            for node in flow_nodes:
                                if node.get("type") == "conversation":
                                    selected_node = node
                                    break
                        # If user speaks first, we're in this function, so find matching node
                    
                    # Find first interactive node for response (conversation, collect_input, press_digit, or extract_variable)
                    if not selected_node:
                        for node in flow_nodes:
                            node_type = node.get("type", "").lower()
                            if node_type in ["conversation", "collect_input", "press_digit", "extract_variable"]:
                                selected_node = node
                                break
            else:
                # Subsequent messages - follow transitions from current node
                # Extract last node from conversation history OR use explicitly set current_node_id
                current_node_id = None
                
                # FIRST: Check if current_node_id is explicitly set (e.g., from transition test mode)
                if self.current_node_id:
                    current_node_id = self.current_node_id
                    logger.info(f"🔍 Using explicitly set current_node_id: {current_node_id}")
                # SECOND: Try to get from conversation history
                elif self.conversation_history:
                    for msg in reversed(self.conversation_history):
                        if msg.get("role") == "assistant" and "_node_id" in msg:
                            current_node_id = msg.get("_node_id")
                            break
                    if current_node_id:
                        logger.info(f"🔍 Current node ID from history: {current_node_id}")
                
                logger.info(f"🔍 Current node ID from history: {current_node_id}")
                
                # Find the current node
                current_node = None
                if current_node_id:
                    for node in flow_nodes:
                        if node.get("id") == current_node_id:
                            current_node = node
                            break
                
                # If no current node found, start from first conversation node
                if not current_node:
                    logger.warning("No current node in history, starting from first conversation node")
                    current_node = await self._get_first_conversation_node(flow_nodes)
                
                if current_node:
                    # Check if current node is a collect_input node that needs processing
                    current_node_type = current_node.get("type", "")
                    if current_node_type == "collect_input":
                        # Process collect_input node first
                        selected_node = current_node
                    else:
                        # For other node types, follow transitions
                        logger.info(f"Evaluating transitions from {current_node.get('label')} for message: {user_message}")
                        selected_node = await self._follow_transition(current_node, user_message, flow_nodes)
                else:
                    selected_node = await self._get_first_conversation_node(flow_nodes)
            
            if selected_node:
                # Update current node position
                self.current_node_id = selected_node.get("id")
                node_data = selected_node.get("data", {})
                node_type = selected_node.get("type", "")
                
                # Get the actual script content, not the prompt field
                if node_type == "conversation":
                    content = node_data.get("script", "") or node_data.get("content", "")
                else:
                    content = node_data.get("content", "") or node_data.get("script", "")
                
                # Replace variables in content BEFORE processing
                for var_name, var_value in self.session_variables.items():
                    content = content.replace(f"{{{{{var_name}}}}}", str(var_value))
                    logger.info(f"🔧 Replaced {{{{{var_name}}}}} with {var_value} in content")
                
                # Smart detection of mode: if content is very long or has instructions, it's "prompt" mode
                # Get mode from data (can be "prompt" or "script") - check both possible field names
                prompt_type = node_data.get("mode")
                if prompt_type is None:
                    prompt_type = node_data.get("promptType")
                
                # ONLY auto-detect if mode is None or empty - NEVER override explicit script mode
                # Script mode must be respected regardless of content length
                if prompt_type is None or prompt_type == "":
                    # If content contains instruction markers, treat as prompt
                    if any(marker in content.lower() for marker in [
                        "## ", "### ", "instructions:", "goal:", "objective:", "**important**", 
                        "you are", "your task", "rules:", "primary goal", "**no dashes"
                    ]):
                        prompt_type = "prompt"
                        logger.info(f"🔍 Auto-detected PROMPT mode (instruction markers found)")
                    else:
                        prompt_type = "script"
                        logger.info(f"🔍 Auto-detected SCRIPT mode (no instruction markers, length: {len(content)} chars)")
                elif prompt_type == "script":
                    logger.info(f"✅ Using explicit SCRIPT mode (length: {len(content)} chars) - will return text instantly")
                
                logger.info(f"Using flow node: {selected_node.get('label', 'unnamed')} (type: {node_type}, mode: {prompt_type})")
                
                # Handle ending node - special case
                if node_type == "ending":
                    logger.info("🛑 Ending node reached - call should terminate")
                    # Add a marker that call should end
                    self.should_end_call = True
                
                # Handle transfer call node - special case
                if node_type in ["call_transfer", "agent_transfer"]:
                    logger.info("📞 Transfer node reached - initiating transfer")
                    transfer_info = self._handle_transfer(node_data)
                    
                    # Store transfer request in session variables
                    self.session_variables["transfer_requested"] = True
                    self.session_variables["transfer_info"] = transfer_info
                    
                    # Return transfer message
                    return transfer_info.get("message", "Please hold while I transfer your call...")
                
                # Handle collect input node - special case
                if node_type == "collect_input":
                    logger.info("📝 Collect Input node reached - gathering user input")
                    collect_result = self._handle_collect_input(node_data, user_message)
                    
                    if collect_result.get("valid"):
                        # Store collected value and move to next node
                        variable_name = node_data.get("variable_name", "user_input")
                        self.session_variables[variable_name] = collect_result.get("value")
                        logger.info(f"✅ Collected and stored {variable_name}: {collect_result.get('value')}")
                        
                        # Keep customer_name and callerName in sync (bidirectional)
                        if variable_name == "customer_name":
                            self.session_variables["callerName"] = collect_result.get("value")
                            logger.info(f"✅ callerName synced")
                        elif variable_name == "callerName":
                            self.session_variables["customer_name"] = collect_result.get("value")
                            logger.info(f"✅ customer_name synced")
                        
                        # Transition to next node if available
                        if node_data.get("transitions"):
                            next_node = await self._follow_transition(selected_node, user_message, flow_nodes)
                            if next_node and next_node.get("id") != selected_node.get("id"):
                                self.current_node_id = next_node.get("id")
                                return await self._process_node_content(next_node, user_message, flow_nodes)
                        
                        return collect_result.get("success_message", "Thank you, I have that information.")
                    else:
                        # Invalid input - prompt again
                        logger.info(f"❌ Invalid input: {collect_result.get('error')}")
                        return collect_result.get("error_message", "I didn't understand that. Please try again.")
                
                # Handle send SMS node - special case
                if node_type == "send_sms":
                    logger.info("📱 Send SMS node reached - sending message")
                    sms_result = await self._handle_send_sms(node_data, user_message)
                    
                    # Store SMS status in session variables
                    self.session_variables["sms_sent"] = sms_result.get("success", False)
                    self.session_variables["sms_status"] = sms_result.get("status", "pending")
                    
                    # Transition to next node if available
                    if node_data.get("transitions"):
                        next_node = await self._follow_transition(selected_node, user_message, flow_nodes)
                        if next_node and next_node.get("id") != selected_node.get("id"):
                            self.current_node_id = next_node.get("id")
                            return await self._process_node_content(next_node, user_message, flow_nodes)
                    
                    return sms_result.get("message", "I've sent you an SMS.")
                
                # Handle logic split node - special case
                if node_type == "logic_split":
                    logger.info("🔀 Logic Split node reached - evaluating conditions")
                    
                    # Evaluate conditions and get next node
                    next_node_id = self._evaluate_logic_conditions(node_data)
                    
                    if next_node_id:
                        next_node = self._get_node_by_id(next_node_id, flow_nodes)
                        if next_node:
                            logger.info(f"✅ Condition matched - moving to node: {next_node.get('label')}")
                            self.current_node_id = next_node_id
                            return await self._process_node_content(next_node, user_message, flow_nodes)
                    
                    # No condition matched - return default message
                    return "Let me help you with that."
                
                # Handle press digit node - special case
                if node_type == "press_digit":
                    logger.info("🔢 Press Digit node reached - processing DTMF input")
                    digit_result = self._handle_press_digit(node_data, user_message)
                    
                    if digit_result.get("next_node_id"):
                        next_node = self._get_node_by_id(digit_result["next_node_id"], flow_nodes)
                        if next_node:
                            logger.info(f"✅ Digit {digit_result['digit']} pressed - routing to node: {next_node.get('label')}")
                            self.current_node_id = digit_result["next_node_id"]
                            return await self._process_node_content(next_node, user_message, flow_nodes)
                    
                    return digit_result.get("message", "Please press a digit.")
                
                # Handle extract variable node - special case
                if node_type == "extract_variable":
                    logger.info("📋 Extract Variable node reached - extracting data")
                    extract_result = await self._handle_extract_variable(node_data, user_message)
                    
                    if extract_result.get("success"):
                        # Store extracted value
                        variable_name = node_data.get("variable_name", "extracted_data")
                        self.session_variables[variable_name] = extract_result.get("value")
                        logger.info(f"✅ Extracted {variable_name}: {extract_result.get('value')}")
                        
                        # Keep customer_name and callerName in sync (bidirectional)
                        if variable_name == "customer_name":
                            self.session_variables["callerName"] = extract_result.get("value")
                            logger.info(f"✅ callerName synced")
                        elif variable_name == "callerName":
                            self.session_variables["customer_name"] = extract_result.get("value")
                            logger.info(f"✅ customer_name synced")
                        
                        # Transition to next node
                        if node_data.get("transitions"):
                            next_node = await self._follow_transition(selected_node, user_message, flow_nodes)
                            if next_node and next_node.get("id") != selected_node.get("id"):
                                self.current_node_id = next_node.get("id")
                                return await self._process_node_content(next_node, user_message, flow_nodes)
                        
                        return extract_result.get("message", "Got it.")
                    
                    return "Could you please provide that information again?"
                
                # Handle function/webhook node - special case
                if node_type == "function":
                    logger.info("🔧 Function/Webhook node reached - executing webhook")
                    
                    # Check if we should speak during execution
                    speak_during_execution = node_data.get("speak_during_execution", False)
                    dialogue_text = node_data.get("dialogue_text", "")
                    dialogue_type = node_data.get("dialogue_type", "static")
                    wait_for_result = node_data.get("wait_for_result", True)
                    
                    dialogue_response = ""
                    
                    # Generate and speak dialogue if enabled
                    if speak_during_execution and dialogue_text:
                        logger.info(f"💬 Generating dialogue before webhook execution (type: {dialogue_type})")
                        
                        if dialogue_type == "static":
                            # Use exact text provided
                            dialogue_response = dialogue_text
                            logger.info(f"📢 Static dialogue: {dialogue_response[:50]}...")
                        else:
                            # AI-generated dialogue based on prompt
                            logger.info(f"🤖 Generating AI dialogue from prompt: {dialogue_text[:50]}...")
                            dialogue_response = await self._generate_ai_response(dialogue_text)
                    
                    # Execute webhook based on wait_for_result setting
                    if wait_for_result:
                        # Wait for webhook to complete before transitioning
                        logger.info("⏳ Waiting for webhook to complete before transitioning...")
                        # Pause dead air monitoring during webhook execution
                        self.executing_webhook = True
                        try:
                            webhook_response = await self._execute_webhook(node_data, user_message)
                        finally:
                            self.executing_webhook = False
                        
                        # Check if webhook requires re-prompt (missing required variables)
                        if webhook_response.get("requires_reprompt"):
                            logger.warning("🔁 Webhook requires re-prompt - staying on same node")
                            # Don't transition, return the re-prompt message
                            return webhook_response.get("message", "I need more information to proceed.")
                    else:
                        # Execute webhook async and transition immediately
                        logger.info("🚀 Executing webhook async, transitioning immediately...")
                        import asyncio
                        asyncio.create_task(self._execute_webhook(node_data, user_message))
                        webhook_response = {"success": True, "message": "Webhook executing in background"}
                    
                    # After webhook (or immediately if not waiting), transition to next node
                    if node_data.get("transitions"):
                        # CRITICAL: Pass webhook_response to transition evaluation for function nodes
                        logger.info(f"🔀 Evaluating transition for function node with webhook response...")
                        next_node = await self._follow_transition(selected_node, user_message, flow_nodes, webhook_response=webhook_response)
                        if next_node and next_node.get("id") != selected_node.get("id"):
                            # Recursively process the next node
                            self.current_node_id = next_node.get("id")
                            return await self._process_node_content(next_node, user_message, flow_nodes)
                    
                    # If we had dialogue, return that, otherwise return webhook message
                    if dialogue_response:
                        return dialogue_response
                    else:
                        return webhook_response.get("message", "Function executed successfully")
                    
                    # If no transitions or same node, return a message
                    return webhook_response.get("message", "Function executed successfully")
                
                # Extract variables in background for conversation nodes (non-blocking)
                # Variables will be ready for next turn
                # UNLESS there are mandatory variables - those need blocking/realtime extraction
                if node_type == "conversation":
                    extract_variables = node_data.get("extract_variables", [])
                    if extract_variables and len(extract_variables) > 0:
                        # Check if any variables are mandatory
                        has_mandatory = any(var.get("mandatory", False) for var in extract_variables)
                        
                        if has_mandatory:
                            logger.info(f"🔍 Extracting {len(extract_variables)} variables with MANDATORY check (blocking)")
                            extraction_result = await self._extract_variables_realtime(extract_variables, user_message)
                            if not extraction_result.get("success", True):
                                # Mandatory variable missing - stay on this node and reprompt
                                reprompt = extraction_result.get("reprompt_message", "Could you please provide more information?")
                                logger.info(f"⚠️ Mandatory variable missing - reprompting: {reprompt[:100]}...")
                                return reprompt
                        else:
                            logger.info(f"🔍 Extracting {len(extract_variables)} variables AFTER response (non-blocking)")
                            import asyncio
                            asyncio.create_task(self._extract_variables_background(extract_variables, user_message))
                
                # Handle script vs prompt mode
                if prompt_type == "prompt":
                    # PROMPT MODE: Always generate AI response based on instructions
                    # This ensures prompt-mode nodes respond to ANY user input, including objections
                    logger.info("🤖 PROMPT mode detected - will generate AI response for user input")
                    node_goal = node_data.get("goal", "")
                    instruction = node_goal if node_goal else content
                    
                    if not instruction:
                        instruction = "Continue the conversation naturally based on the node's purpose"
                    
                    # Generate AI response with streaming
                    full_response = ""
                    async for sentence in self._generate_ai_response_streaming(instruction, None):
                        full_response += sentence + " "
                    
                    return full_response.strip()
                    
                elif prompt_type == "script":
                    # Check if we're repeating the same script (stayed on same node)
                    # This happens when user's response didn't match any transition
                    is_repeating = False
                    last_user_message = ""
                    if len(self.conversation_history) >= 2:
                        # Check if the last assistant message was the same script
                        # AND get the last user message for context
                        for msg in reversed(self.conversation_history):
                            if msg.get("role") == "user" and not last_user_message:
                                last_user_message = msg.get("content", "")
                            if msg.get("role") == "assistant":
                                last_assistant_msg = msg.get("content", "")
                                # If the content is very similar or same, we're repeating
                                if last_assistant_msg.strip() == content.strip():
                                    is_repeating = True
                                    logger.info("🔄 Detected script repetition")
                                break
                    
                    if is_repeating:
                        # User's response didn't match any transition
                        # Use global prompt for intelligent recovery if available
                        global_prompt = self.agent_config.get("system_prompt", "").strip()
                        
                        # Add knowledge base to global prompt if available
                        if self.knowledge_base:
                            global_prompt += f"\n\n=== KNOWLEDGE BASE ===\nYou have access to multiple reference sources below. Each source serves a different purpose.\n\n🧠 HOW TO USE THE KNOWLEDGE BASE:\n1. When user asks a question, FIRST identify which knowledge base source(s) are relevant based on their descriptions\n2. Read ONLY the relevant source(s) to find the answer\n3. Use ONLY information from the knowledge base - do NOT make up or improvise ANY factual details\n4. If the knowledge base doesn't contain the answer, say: \"I don't have that specific information available\"\n5. Different sources contain different types of information - match the user's question to the right source\n\n⚠️ NEVER invent: company names, product names, prices, processes, methodologies, or any factual information not in the knowledge base\n\n{self.knowledge_base}\n=== END KNOWLEDGE BASE ===\n"
                        
                        node_goal = node_data.get("goal", "").strip()
                        
                        if global_prompt and node_goal:
                            logger.info("🌍 Using global prompt + node goal for intelligent recovery")
                            
                            # Detect if user has a question or objection for better context
                            user_has_question = False
                            if last_user_message:
                                question_indicators = ["?", "how", "what", "why", "scam", "legit", "trust", "real", "catch", "cost", "price", "much"]
                                if any(indicator in last_user_message.lower() for indicator in question_indicators):
                                    user_has_question = True
                                    logger.info(f"🤔 User appears to have a question/objection: {last_user_message[:100]}")
                            
                            # Use AI to generate intelligent recovery based on global prompt + goal
                            try:
                                llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
                                if not llm_provider:
                                    logger.error("❌ No LLM provider configured for agent")
                                    return None
                                model = self.agent_config.get("model", "gpt-4-turbo")
                                
                                if llm_provider == "grok":
                                    client = await self.get_llm_client_for_session("grok")
                                else:
                                    client = await self.get_llm_client_for_session("openai")
                                
                                if client:
                                    # Tailor the instruction based on whether it's a question or not
                                    if user_has_question:
                                        recovery_instruction = f"""The user responded with a question or concern instead of giving a direct answer.

Node Goal: {node_goal}
Original Script: {content}
User's Response: {last_user_message}

CRITICAL INSTRUCTION - AVOID REPETITION:
- Review the conversation history below carefully
- DO NOT repeat any questions or phrases you've already said in this conversation
- If you've already asked about a specific dollar amount (like $20,000/month), DO NOT ask it again
- If you need to circle back to the goal, come up with a DIFFERENT approach - rephrase, use different framing, or ask a different angle

Your task: 
1. Address their question or concern FIRST (briefly and naturally)
2. Then guide them back toward the goal using a FRESH approach (not what you already said)
3. Stay in character based on your persona

DO NOT just repeat the question. Handle their concern, THEN continue the conversation naturally with NEW phrasing."""
                                    else:
                                        recovery_instruction = f"""The user's response didn't quite match what was expected for this step in the conversation.

Node Goal: {node_goal}
Original Script: {content}
User's Response: {last_user_message}

CRITICAL INSTRUCTION - AVOID REPETITION:
- Review the conversation history below carefully
- DO NOT repeat any questions or phrases you've already said in this conversation
- If you've already asked about a specific dollar amount (like $20,000/month), DO NOT ask it again
- If you need to circle back to the goal, come up with a DIFFERENT approach - rephrase, use different framing, or ask a different angle

Your task: 
1. Acknowledge their response naturally
2. Guide them back toward the goal using a FRESH approach (without repeating the exact script OR what you already said)
3. Stay in character based on your persona

Use your natural conversational style to handle this smoothly with NEW phrasing."""

                                    var_context = ""
                                    if self.session_variables:
                                        var_context = f"\n\nAvailable context: {json.dumps(self.session_variables)}"
                                    
                                    # IMPORTANT: Include MORE conversation history (last 8 messages instead of 3)
                                    # This ensures the LLM can see what it already said and avoid repetition
                                    messages = [
                                        {"role": "system", "content": global_prompt + var_context},
                                        {"role": "system", "content": recovery_instruction}
                                    ] + self.conversation_history  # Full history
                                    
                                    if llm_provider == "grok":
                                        response = await client.create_completion(
                                            messages=messages,
                                            model=model,
                                            temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                                            max_tokens=300  # Increased to allow more thoughtful responses
                                        )
                                    else:
                                        response = await client.chat.completions.create(
                                            model=model,
                                            messages=messages,
                                            temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                                            max_tokens=300  # Increased to allow more thoughtful responses
                                        )
                                    
                                    recovery_response = response.choices[0].message.content.strip()
                                    if recovery_response:
                                        logger.info(f"✅ Generated intelligent recovery: {recovery_response[:100]}...")
                                        return recovery_response
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to generate intelligent recovery: {e}")
                        
                        # Fallback: Add clarifying phrase before repeating the question
                        # This only happens if no global prompt or no node goal
                        logger.info("➕ No global prompt available - adding simple clarification before repeating script")
                        clarifications = [
                            "Sorry, I didn't quite catch that. ",
                            "Let me ask that again. ",
                            "Could you repeat that? ",
                            "I'm sorry, ",
                        ]
                        import random
                        clarification = random.choice(clarifications)
                        return clarification + content
                    else:
                        # Return exact script
                        return content
            else:
                logger.warning("No suitable node found, falling back")
                return await self._process_single_prompt(user_message)
                
        except Exception as e:
            logger.error(f"Error in call flow: {e}")
            return await self._process_single_prompt(user_message)
    
    async def _get_first_conversation_node(self, flow_nodes: list) -> dict:
        """Get the first interactive node in the flow (conversation, collect_input, press_digit, or extract_variable)"""
        for node in flow_nodes:
            if node.get("type") in ["conversation", "collect_input", "press_digit", "extract_variable"]:
                return node
        return None
    
    async def _follow_transition(self, current_node: dict, user_message: str, flow_nodes: list, webhook_response: dict = None) -> dict:
        """Use AI to evaluate transitions and follow to next node
        
        Args:
            current_node: The node we're transitioning from
            user_message: The user's last message
            flow_nodes: All nodes in the flow
            webhook_response: Optional webhook response for function nodes (used to evaluate transitions based on webhook result)
        """
        try:
            node_data = current_node.get("data", {})
            transitions = node_data.get("transitions", [])
            
            # 🎤 AUTO TRANSITION AFTER RESPONSE - Skip LLM evaluation if enabled
            # This is different from auto_transition_to which skips immediately
            # This one WAITS for user to speak, captures their response, then transitions
            auto_transition_after_response_node_id = node_data.get("auto_transition_after_response")
            if auto_transition_after_response_node_id:
                logger.info(f"🎤 AUTO-TRANSITION AFTER RESPONSE enabled - user spoke, transitioning to: {auto_transition_after_response_node_id}")
                next_node = self._get_node_by_id(auto_transition_after_response_node_id, flow_nodes)
                if next_node:
                    logger.info(f"✅ Auto-transitioned (after response) to: {next_node.get('label', 'unnamed')}")
                    logger.info(f"📝 User's response captured: '{user_message[:50]}...'")
                    return next_node
                else:
                    logger.warning(f"⚠️ Auto-transition after response target not found: {auto_transition_after_response_node_id}, falling back to normal evaluation")
            
            if not transitions:
                # No transitions, stay on current node
                logger.info(f"No transitions from {current_node.get('label')}, staying on current node")
                return current_node
            
            # Helper function to check if a transition passes variable checks
            def passes_variable_checks(trans: dict) -> bool:
                check_variables = trans.get("check_variables", [])
                if not check_variables:
                    return True  # No variable checks required
                
                for var_name in check_variables:
                    if var_name not in self.session_variables or self.session_variables[var_name] is None:
                        logger.info(f"  ❌ Variable check FAILED for '{var_name}' - missing or null")
                        return False
                logger.info(f"  ✅ All variable checks passed: {check_variables}")
                return True
            
            # All transitions are evaluated by the LLM - no shortcuts or cached responses
            # The LLM understands context and can properly match user intent to transition conditions
            
            # Build options for AI to evaluate
            transition_options = []
            for i, trans in enumerate(transitions):
                condition = trans.get("condition", "")
                next_node_id = trans.get("nextNode", "")
                check_variables = trans.get("check_variables", [])
                
                # Check if this transition requires variable validation
                if check_variables:
                    logger.info(f"🔍 Transition {i} requires variable checks: {check_variables}")
                    missing_vars = []
                    
                    for var_name in check_variables:
                        if var_name not in self.session_variables or self.session_variables[var_name] is None:
                            missing_vars.append(var_name)
                            logger.warning(f"  ❌ Variable '{var_name}' is missing or null")
                    
                    if missing_vars:
                        logger.info(f"⏸️ Skipping transition {i} - missing required variables: {missing_vars}")
                        continue  # Skip this transition option, don't make it available for selection
                    else:
                        logger.info(f"  ✅ All required variables present for transition {i}")
                
                if condition and next_node_id:
                    transition_options.append({
                        "index": i,
                        "condition": condition,
                        "next_node_id": next_node_id
                    })
            
            if not transition_options:
                # No valid transitions available (all blocked by variable checks), stay on current node
                logger.info("⏸️ No valid transitions available (variable checks blocking), staying on current node")
                return current_node
            
            # ALWAYS use LLM to evaluate transitions - even with only 1 option
            # The LLM must verify the user's response actually matches the transition condition
            # Otherwise, the agent should stay on the current node and re-prompt
            # Get LLM provider and appropriate client
            llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
            if not llm_provider:
                logger.error("❌ No LLM provider configured for agent")
                return None
            model = self.agent_config.get("model", "gpt-4")
            
            if llm_provider == "grok":
                client = await self.get_llm_client_for_session("grok")
            else:
                client = await self.get_llm_client_for_session("openai")
            
            if not client:
                # No AI available, take first transition
                logger.warning("No LLM client available, taking first transition")
                first_trans = transitions[0]
                next_node_id = first_trans.get("nextNode")
                return self._get_node_by_id(next_node_id, flow_nodes) or current_node
            
            # Build evaluation prompt - make it MUCH more intelligent
            options_text = ""
            for i, opt in enumerate(transition_options):
                options_text += f"\nOption {i}:\n"
                options_text += f"  Condition: {opt['condition']}\n"
            
            # Get full conversation context
            full_context = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in self.conversation_history[-10:]  # Last 10 messages (matching webhook extraction)
            ])
            
            # Check if this is a function/webhook node - if so, include webhook response in evaluation
            is_function_node = current_node.get("type") == "function"
            webhook_context = ""
            if is_function_node and webhook_response:
                logger.info(f"🔧 Function node detected - including webhook response in transition evaluation")
                # Format webhook response for the prompt
                webhook_data = webhook_response.get("data", webhook_response)
                webhook_context = f"""
WEBHOOK RESPONSE (CRITICAL - base your decision primarily on this):
{json.dumps(webhook_data, indent=2, default=str)}

This is a WEBHOOK/FUNCTION node. The transitions should be evaluated based on the WEBHOOK RESPONSE above, NOT the user's message.
- If the webhook response indicates success/booking/completion → choose the positive transition
- If the webhook response indicates failure/unavailability/error → choose the negative transition
- Look for keys like "status", "success", "booked", "available", "message" in the response
"""
                logger.info(f"📦 Webhook response data for transition: {json.dumps(webhook_data, default=str)[:200]}...")
            
            # Adjust prompt based on whether this is a webhook node or conversation node
            if is_function_node and webhook_response:
                eval_prompt = f"""You are analyzing a webhook response to determine which transition path to take.

CONVERSATION HISTORY (for context only):
{full_context}

{webhook_context}

TRANSITION OPTIONS:
{options_text}

Your task:
1. Carefully analyze the WEBHOOK RESPONSE above
2. Match the webhook result to the appropriate transition condition
3. For booking/scheduling webhooks:
   - If the response shows appointment was "booked", "confirmed", "scheduled", or "success" → choose the positive/booked transition
   - If the response shows "unavailable", "full", "failed", "error", or offers alternative times → choose the negative/unavailable transition
4. Look at ALL fields in the webhook response: status, message, success, booked, available, etc.

CRITICAL: Your decision should be based on the WEBHOOK RESPONSE, not what the user said.

Respond with ONLY the number (0, 1, 2, etc.) of the BEST matching transition.
If absolutely none match, respond with "-1".

Your response (just the number):"""
            else:
                eval_prompt = f"""You are analyzing a phone conversation to determine which transition path to take based on what the user just said.

CONVERSATION HISTORY:
{full_context}

TRANSITION OPTIONS:
{options_text}

Your task:
1. Carefully read what the user ACTUALLY said in their most recent message
2. Understand the INTENT and MEANING behind their words
3. Check if their response SATISFIES the transition condition - does it provide what the condition is looking for?

CRITICAL RULES:
- The transition condition describes what the user MUST do/say for that transition to fire
- If the condition says "user provides their income" and the user says "I don't want to tell you" - that does NOT satisfy the condition → return -1
- If the condition says "user agrees" and user says "okay" - that DOES satisfy the condition → return that option
- If the condition says "user asks for callback" and user says "call me back later" - that DOES satisfy the condition
- A refusal or deflection is NOT the same as providing the requested information

Examples:
- Condition: "User provides their yearly income" + User says "I make about 50k" → MATCH (they provided income)
- Condition: "User provides their yearly income" + User says "I don't want to tell you" → NO MATCH (they refused)
- Condition: "User provides their yearly income" + User says "Why do you need that?" → NO MATCH (they asked a question instead)
- Condition: "User agrees to continue" + User says "sure go ahead" → MATCH
- Condition: "User says they are busy" + User says "I'm in a meeting" → MATCH

Respond with ONLY the number (0, 1, 2, etc.) of the transition whose condition is SATISFIED by the user's response.
If the user's response does NOT satisfy ANY condition (refusal, deflection, unrelated response), respond with "-1".

Your response (just the number):"""

            import datetime
            timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.info(f"⏱️ [{timestamp_str}] 🔀 TRANSITION EVALUATION START - Calling LLM for {len(transition_options)} options")
            transition_start = time.time()
            
            # 🚀 CRITICAL FIX: Add 2-second timeout to prevent 13-second freezes
            try:
                # Call LLM based on provider with timeout wrapper
                async def call_llm_for_transition():
                    if llm_provider == "grok":
                        return await client.create_completion(
                            messages=[
                                {"role": "system", "content": "You are an expert at understanding conversation flow and user intent in phone calls. You analyze what users say and match it to transition conditions intelligently."},
                                {"role": "user", "content": eval_prompt}
                            ],
                            model=model,
                            temperature=0,
                            max_tokens=10,
                            stream=False
                        )
                    else:
                        return await client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": "You are an expert at understanding conversation flow and user intent in phone calls. You analyze what users say and match it to transition conditions intelligently."},
                                {"role": "user", "content": eval_prompt}
                            ],
                            temperature=0,
                            max_tokens=10,
                            stream=False
                        )
                
                # Apply 1.5-second timeout (aggressive) - Grok is fast, should complete in < 500ms normally
                response = await asyncio.wait_for(call_llm_for_transition(), timeout=1.5)
                
            except asyncio.TimeoutError:
                # Timeout! STAY on current node - don't auto-transition
                # Taking the first transition was causing unexpected jumps (e.g., after empty messages)
                logger.warning(f"⚠️ TRANSITION EVALUATION TIMEOUT (>1.5s) - staying on current node")
                logger.warning(f"⚠️ This prevents 13-second freezes. User should re-respond to trigger evaluation.")
                
                # Return current node to stay in place
                return current_node
            
            ai_response = response.choices[0].message.content.strip()
            transition_end = time.time()
            transition_latency_ms = int((transition_end - transition_start) * 1000)
            timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.info(f"⏱️ [{timestamp_str}] 🔀 TRANSITION EVALUATION COMPLETE - took {transition_latency_ms}ms")
            logger.info(f"🤖 AI transition decision: '{ai_response}'")
            logger.info(f"📊 Available transitions: {[opt['condition'][:50] + '...' for opt in transition_options]}")
            
            try:
                selected_index = int(ai_response)
                logger.info(f"Selected transition index: {selected_index}")
                
                if selected_index >= 0 and selected_index < len(transition_options):
                    next_node_id = transition_options[selected_index]["next_node_id"]
                    next_node = self._get_node_by_id(next_node_id, flow_nodes)
                    
                    if next_node:
                        logger.info(f"Transition: {current_node.get('label')} -> {next_node.get('label')}")
                        return next_node
                    else:
                        logger.warning(f"Next node {next_node_id} not found")
                elif selected_index == -1:
                    # No specific condition matched, look for default/fallback transition
                    logger.info("No specific condition matched, looking for default transition...")
                    
                    # First, look for an explicit default transition (empty condition)
                    for trans in transitions:
                        condition = trans.get("condition", "").strip()
                        next_node_id = trans.get("nextNode", "")
                        
                        # If condition is empty or very generic, it's the default
                        if not condition or condition.lower() in ["default", "otherwise", "else"]:
                            next_node = self._get_node_by_id(next_node_id, flow_nodes)
                            if next_node:
                                logger.info(f"Taking default transition to: {next_node.get('label')}")
                                return next_node
                    
                    # If AI returned -1 (no match), check if node has a GOAL
                    # Goals allow the agent to continue the conversation and guide toward a transition
                    node_goal = node_data.get("goal", "").strip()
                    node_mode = node_data.get("mode", "script")
                    
                    if node_goal:
                        logger.info(f"⚠️ No transition matched, but node has GOAL. Staying on current node to continue with goal-based guidance.")
                        logger.info(f"🎯 Goal: {node_goal[:100]}...")
                        # Return current node - the _process_node_content will use the goal to generate a response
                        # that guides the user toward meeting a transition condition
                        return current_node
                    elif node_mode == "script":
                        # Script mode nodes without goals should stay on current node to re-ask/clarify
                        logger.info(f"⚠️ No transition matched for script-mode node. Staying on current node to clarify/re-ask.")
                        # Return current node - will repeat the script with clarification
                        return current_node
                    
                    # 🔥 FIX: If no goal and no explicit default transition, STAY on current node
                    # DO NOT blindly take the first transition - that causes "banana" to trigger transitions
                    # The user said something nonsensical/irrelevant, so we should re-prompt, not advance
                    logger.info(f"⚠️ No transition matched, no goal defined. Staying on current node to re-prompt user.")
                    return current_node
                else:
                    logger.info(f"Selected index {selected_index} out of range, staying on current node")
            except ValueError:
                logger.warning(f"Could not parse AI response as integer: '{ai_response}'")
            
            # No transition matched, stay on current node
            logger.info("No transition matched, staying on current node")
            return current_node
            
        except Exception as e:
            logger.error(f"Error following transition: {e}")
            return current_node
    
    def _get_node_by_id(self, node_id: str, flow_nodes: list) -> dict:
        """Find node by ID"""
        for node in flow_nodes:
            if node.get("id") == node_id:
                return node
        return None
    
    async def _extract_variables_realtime(self, extract_variables: list, user_message: str) -> dict:
        """Extract variables in real-time during conversation
        
        Returns:
            dict with 'success' bool and optional 'reprompt_message' if mandatory variables are missing
        """
        try:
            logger.info(f"🔍 Real-time extraction: Processing {len(extract_variables)} variables")
            
            # Only extract variables that don't already exist and aren't empty configs
            # UNLESS allow_update is True, which clears the variable for re-extraction
            variables_to_extract = []
            for var in extract_variables:
                var_name = var.get("name", "")
                allow_update = var.get("allow_update", False)
                
                if not var_name:
                    continue
                    
                # If allow_update is enabled, clear the variable for fresh extraction
                if allow_update and var_name in self.session_variables:
                    old_value = self.session_variables.pop(var_name)
                    logger.info(f"  🔄 {var_name}: Cleared for update (was: {old_value})")
                    variables_to_extract.append(var)
                elif var_name not in self.session_variables:
                    variables_to_extract.append(var)
                else:
                    logger.info(f"  ✓ {var_name}: {self.session_variables[var_name]} (already extracted)")
            
            if not variables_to_extract:
                logger.info("✅ All variables already extracted")
                # Still need to check if mandatory variables are present
                return await self._check_mandatory_variables(extract_variables)
            
            # Build extraction prompt with hints - look at recent conversation context
            # Get last 10 conversation turns for better context (matching webhook extraction)
            recent_conversation = ""
            if self.conversation_history:
                recent_turns = self.conversation_history[-10:]  # Last 10 messages
                for msg in recent_turns:
                    role = "User" if msg.get("role") == "user" else "Assistant"
                    content = msg.get("content", "")
                    recent_conversation += f"{role}: {content}\n"
            
            # Include existing session variables for reference in calculations
            existing_vars_str = ""
            if self.session_variables:
                existing_vars_str = "\n\nEXISTING VARIABLES (use these exact values for calculations):\n"
                for k, v in self.session_variables.items():
                    existing_vars_str += f"  {k} = {v}\n"
            
            extraction_prompt = "Extract the following information from the recent conversation:\n\n"
            for var in variables_to_extract:
                var_name = var.get("name", "")
                var_description = var.get("description", "")
                var_hint = var.get("extraction_hint", "")
                if var_name:
                    extraction_prompt += f"- {var_name}: {var_description}\n"
                    if var_hint:
                        extraction_prompt += f"  Hint: {var_hint}\n"
            
            extraction_prompt += existing_vars_str
            extraction_prompt += f"\n\nRecent conversation:\n{recent_conversation}\n"
            extraction_prompt += f"Current user message: {user_message}\n\n"
            extraction_prompt += """IMPORTANT INSTRUCTIONS:

**CRITICAL - DO NOT HALLUCINATE VALUES:**
- ONLY extract values that the USER has EXPLICITLY stated in the conversation
- If the user has NOT provided a specific number/value, return null
- DO NOT guess, estimate, or make up values
- DO NOT use "typical" or "average" values
- If asking for income and user said "I work" without stating a number → return null for income
- If asking for time and user hasn't mentioned a time → return null for time
- The user MUST have actually said the information for you to extract it

1. Look through the ENTIRE conversation above, not just the current message.

2. **AGREEMENT PATTERN RECOGNITION** (CRITICAL - READ THIS CAREFULLY):
   - If the user's current message is a short confirmation like "sure", "yeah", "yes", "okay", "ok", "that works", "sounds good", "perfect", "yep", "uh huh", "alright", etc.
   - This means the user is AGREEING to what the Assistant just proposed or suggested
   - You MUST extract values from the ASSISTANT's most recent message that the user is confirming
   - Examples:
     * Assistant: "How about 3 PM tomorrow?"  →  User: "Sure"
       Extract: scheduleTime="3 PM tomorrow", amPm="PM" (from Assistant's proposal)
     * Assistant: "So that's $5000 monthly, correct?"  →  User: "Yeah"
       Extract: monthly_amount=5000 (from Assistant's statement)
     * Assistant: "Would 2:30 in the afternoon work?"  →  User: "That works"
       Extract: time="2:30", amPm="PM" (afternoon = PM)
   - The user's agreement CONFIRMS and ACCEPTS the Assistant's proposed values
   - DO NOT return null just because the user only said "sure" - look at what they're agreeing TO
   - BUT if the Assistant asked a question and user said something unrelated, don't assume agreement

3. If a variable description mentions CALCULATING from other variables (e.g., "convert to monthly", "add X + Y", "divide by 12"), you MUST PERFORM THE MATH:
   - Use the EXISTING VARIABLES values above for calculations
   - Example: if business_income=120000 and side_hustle=24000, then (120000 + 24000) / 12 = 144000 / 12 = 12000
   - But ONLY calculate if the source values actually exist and were provided by the user

4. For monetary values, extract just the number (e.g., "50000" not "$50,000" or "50k").

5. If someone says "50k" or "fifty thousand", convert to 50000.

6. For monthly conversions: yearly / 12 = monthly. For yearly from monthly: monthly * 12 = yearly.

7. Return numbers as plain integers without commas or currency symbols.

8. **CRITICAL - SPEECH-TO-TEXT NUMBER PARSING:**
   - Speech transcripts often have filler words, hesitations, and spacing in numbers
   - "20, Uh, 4,000" or "20, uh, 4000" means TWENTY-FOUR THOUSAND (24000), NOT 204000
   - "I make about 20, 4,000 a year" = 24000 (twenty-four thousand)
   - "like 1, 2000" = 12000 (twelve thousand)  
   - "about 3, 5000" = 35000 (thirty-five thousand)
   - When someone says a number with a pause/comma before "thousand", combine them logically:
     * "24, thousand" = 24000
     * "fifty, thousand" = 50000
   - DO NOT concatenate numbers that should be spoken together (e.g., "20" + "4000" ≠ 204000)
   - The KEY pattern: "[small number], [larger number ending in 000]" usually means a single number
     * "20, 4000" = 24000 (twenty-four thousand)
     * "1, 2 million" = 1.2 million = 1200000
     * "5, hundred thousand" = 500000
   - But high earners exist! "I make 500,000" or "1.2 million" are valid - don't cap incomes

9. For time-related extractions:
   - "morning" = AM, "afternoon" = PM, "evening" = PM, "night" = PM
   - "noon" = 12 PM, "midnight" = 12 AM
   - If Assistant said "3 PM" and user agreed, amPm = "PM"

10. DOUBLE-CHECK YOUR ARITHMETIC before returning.

**CRITICAL - DO NOT HALLUCINATE VALUES:**
- ONLY extract values that the USER has EXPLICITLY stated in the conversation
- If the user has NOT provided a specific number/value, return null
- DO NOT guess, estimate, or make up values
- DO NOT use "typical" or "average" values
- If asking for income and user said "I work" without stating a number → return null for income
- If asking for time and user hasn't mentioned a time → return null for time
- The user MUST have actually said the information for you to extract it

Return ONLY a JSON object with the extracted values. If a value was NOT explicitly stated by the user in this conversation, use null. Format:
"""
            extraction_prompt += "{"
            for i, var in enumerate(variables_to_extract):
                var_name = var.get("name", "")
                if var_name:
                    extraction_prompt += f'"{var_name}": <value>'
                    if i < len(variables_to_extract) - 1:
                        extraction_prompt += ", "
            extraction_prompt += "}"
            
            # Get LLM provider from agent config (not hardcoded OpenAI)
            llm_provider = self.agent_config.get("settings", {}).get("llm_provider", "openai")
            model = self.agent_config.get("model", "gpt-4o-mini")
            
            logger.info(f"🤖 Using configured LLM provider: {llm_provider} ({model}) for extraction")
            
            # Get appropriate client based on provider
            if llm_provider == "grok":
                client = await self.get_llm_client_for_session("grok")
            else:
                client = await self.get_llm_client_for_session("openai")
            
            # Helper function to make the extraction call
            async def call_extraction():
                if llm_provider == "grok":
                    return await client.create_completion(
                        messages=[{"role": "user", "content": extraction_prompt}],
                        model=model,
                        temperature=0.0,
                        max_tokens=500
                    )
                else:
                    return await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": extraction_prompt}],
                        temperature=0.0,
                        max_tokens=500
                    )
            
            # 1-second timeout with silent retry
            response = None
            for attempt in range(2):  # Max 2 attempts
                try:
                    response = await asyncio.wait_for(call_extraction(), timeout=1.0)
                    break  # Success, exit loop
                except asyncio.TimeoutError:
                    if attempt == 0:
                        logger.warning(f"⚠️ Extraction timeout (attempt 1) - retrying silently...")
                    else:
                        logger.warning(f"⚠️ Extraction timeout (attempt 2) - falling back to normal node logic")
                        # Return success with no extraction - normal node logic handles missing vars
                        return {"success": True}
            
            if response is None:
                logger.warning(f"⚠️ Extraction failed - falling back to normal node logic")
                return {"success": True}
            
            extraction_response = response.choices[0].message.content.strip()
            # Remove markdown if present
            if extraction_response.startswith("```"):
                extraction_response = extraction_response.split("```")[1]
                if extraction_response.startswith("json"):
                    extraction_response = extraction_response[4:]
            extraction_response = extraction_response.strip()
            
            extracted_vars = json.loads(extraction_response)
            
            # Store extracted variables
            for var_name, var_value in extracted_vars.items():
                if var_value is not None:
                    self.session_variables[var_name] = var_value
                    logger.info(f"  ✓ {var_name}: {var_value} (extracted in real-time)")
                    
                    # Keep customer_name and callerName in sync (bidirectional)
                    if var_name == "customer_name":
                        self.session_variables["callerName"] = var_value
                        logger.info(f"  ✓ callerName: {var_value} (synced)")
                    elif var_name == "callerName":
                        self.session_variables["customer_name"] = var_value
                        logger.info(f"  ✓ customer_name: {var_value} (synced)")
            
            logger.info(f"✅ Real-time extraction complete: {len(extracted_vars)} variables")
            
            # Check if any mandatory variables are still missing
            return await self._check_mandatory_variables(extract_variables)
            
        except Exception as e:
            logger.error(f"Error in real-time extraction: {e}")
            return {"success": True}  # Don't block conversation on extraction errors


    async def _extract_variables_background(self, extract_variables: list, user_message: str):
        """Extract variables in the background (non-blocking, fire-and-forget)
        
        This runs AFTER the agent has already responded, so extraction happens
        while the audio is playing. Variables are ready for the next turn.
        """
        try:
            logger.info(f"🔍 Background extraction: Processing {len(extract_variables)} variables")
            
            # Only extract variables that don't already exist
            # UNLESS allow_update is True, which clears the variable for re-extraction
            variables_to_extract = []
            for var in extract_variables:
                var_name = var.get("name", "")
                allow_update = var.get("allow_update", False)
                
                if not var_name:
                    continue
                    
                # If allow_update is enabled, clear the variable for fresh extraction
                if allow_update and var_name in self.session_variables:
                    old_value = self.session_variables.pop(var_name)
                    logger.info(f"  🔄 {var_name}: Cleared for update (was: {old_value})")
                    variables_to_extract.append(var)
                elif var_name not in self.session_variables:
                    variables_to_extract.append(var)
                else:
                    logger.info(f"  ✓ {var_name}: {self.session_variables[var_name]} (already extracted)")
            
            if not variables_to_extract:
                logger.info("✅ All variables already extracted")
                return
            
            # Build extraction prompt with recent conversation context
            recent_conversation = ""
            if self.conversation_history:
                recent_turns = self.conversation_history[-10:]  # Last 10 messages (matching webhook extraction)
                for msg in recent_turns:
                    role = "User" if msg.get("role") == "user" else "Assistant"
                    content = msg.get("content", "")
                    recent_conversation += f"{role}: {content}\n"
            
            # Include existing session variables for reference in calculations
            existing_vars_str = ""
            if self.session_variables:
                existing_vars_str = "\n\nEXISTING VARIABLES (use these exact values for calculations):\n"
                for k, v in self.session_variables.items():
                    existing_vars_str += f"  {k} = {v}\n"
            
            extraction_prompt = "Extract the following information from the recent conversation:\n\n"
            for var in variables_to_extract:
                var_name = var.get("name", "")
                var_description = var.get("description", "")
                var_hint = var.get("extraction_hint", "")
                if var_name:
                    extraction_prompt += f"- {var_name}: {var_description}\n"
                    if var_hint:
                        extraction_prompt += f"  Hint: {var_hint}\n"
            
            extraction_prompt += existing_vars_str
            extraction_prompt += f"\n\nRecent conversation:\n{recent_conversation}\n"
            extraction_prompt += f"Current user message: {user_message}\n\n"
            extraction_prompt += """IMPORTANT INSTRUCTIONS:

**CRITICAL - DO NOT HALLUCINATE VALUES:**
- ONLY extract values that the USER has EXPLICITLY stated in the conversation
- If the user has NOT provided a specific number/value, return null
- DO NOT guess, estimate, or make up values
- DO NOT use "typical" or "average" values
- If asking for income and user said "I work" without stating a number → return null for income
- If asking for time and user hasn't mentioned a time → return null for time
- The user MUST have actually said the information for you to extract it

1. Look through the ENTIRE conversation above, not just the current message.

2. **AGREEMENT PATTERN RECOGNITION** (CRITICAL - READ THIS CAREFULLY):
   - If the user's current message is a short confirmation like "sure", "yeah", "yes", "okay", "ok", "that works", "sounds good", "perfect", "yep", "uh huh", "alright", etc.
   - This means the user is AGREEING to what the Assistant just proposed or suggested
   - You MUST extract values from the ASSISTANT's most recent message that the user is confirming
   - Examples:
     * Assistant: "How about 3 PM tomorrow?"  →  User: "Sure"
       Extract: scheduleTime="3 PM tomorrow", amPm="PM" (from Assistant's proposal)
     * Assistant: "So that's $5000 monthly, correct?"  →  User: "Yeah"
       Extract: monthly_amount=5000 (from Assistant's statement)
     * Assistant: "Would 2:30 in the afternoon work?"  →  User: "That works"
       Extract: time="2:30", amPm="PM" (afternoon = PM)
   - The user's agreement CONFIRMS and ACCEPTS the Assistant's proposed values
   - DO NOT return null just because the user only said "sure" - look at what they're agreeing TO
   - BUT if the Assistant asked a question and user said something unrelated, don't assume agreement

3. If a variable description mentions CALCULATING from other variables (e.g., "convert to monthly", "add X + Y", "divide by 12"), you MUST PERFORM THE MATH:
   - Use the EXISTING VARIABLES values above for calculations
   - Example: if business_income=120000 and side_hustle=24000, then (120000 + 24000) / 12 = 144000 / 12 = 12000
   - But ONLY calculate if the source values actually exist and were provided by the user

4. For monetary values, extract just the number (e.g., "50000" not "$50,000" or "50k").

5. If someone says "50k" or "fifty thousand", convert to 50000.

6. For monthly conversions: yearly / 12 = monthly. For yearly from monthly: monthly * 12 = yearly.

7. Return numbers as plain integers without commas or currency symbols.

8. **CRITICAL - SPEECH-TO-TEXT NUMBER PARSING:**
   - Speech transcripts often have filler words, hesitations, and spacing in numbers
   - "20, Uh, 4,000" or "20, uh, 4000" means TWENTY-FOUR THOUSAND (24000), NOT 204000
   - "I make about 20, 4,000 a year" = 24000 (twenty-four thousand)
   - "like 1, 2000" = 12000 (twelve thousand)  
   - "about 3, 5000" = 35000 (thirty-five thousand)
   - When someone says a number with a pause/comma before "thousand", combine them logically:
     * "24, thousand" = 24000
     * "fifty, thousand" = 50000
   - DO NOT concatenate numbers that should be spoken together (e.g., "20" + "4000" ≠ 204000)
   - The KEY pattern: "[small number], [larger number ending in 000]" usually means a single number
     * "20, 4000" = 24000 (twenty-four thousand)
     * "1, 2 million" = 1.2 million = 1200000
     * "5, hundred thousand" = 500000
   - But high earners exist! "I make 500,000" or "1.2 million" are valid - don't cap incomes

9. For time-related extractions:
   - "morning" = AM, "afternoon" = PM, "evening" = PM, "night" = PM
   - "noon" = 12 PM, "midnight" = 12 AM
   - If Assistant said "3 PM" and user agreed, amPm = "PM"

10. DOUBLE-CHECK YOUR ARITHMETIC before returning.

**CRITICAL - DO NOT HALLUCINATE VALUES:**
- ONLY extract values that the USER has EXPLICITLY stated in the conversation
- If the user has NOT provided a specific number/value, return null
- DO NOT guess, estimate, or make up values
- DO NOT use "typical" or "average" values
- If asking for income and user said "I work" without stating a number → return null for income
- If asking for time and user hasn't mentioned a time → return null for time
- The user MUST have actually said the information for you to extract it

Return ONLY a JSON object with the extracted values. If a value was NOT explicitly stated by the user in this conversation, use null. Format:
"""
            extraction_prompt += "{"
            for i, var in enumerate(variables_to_extract):
                var_name = var.get("name", "")
                if var_name:
                    extraction_prompt += f'"{var_name}": <value>'
                    if i < len(variables_to_extract) - 1:
                        extraction_prompt += ", "
            extraction_prompt += "}"
            
            # Call LLM to extract - use temperature=0 for deterministic math calculations
            var_extract_start = time.time()
            client = await self.get_llm_client_for_session("openai")
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.0,
                max_tokens=500
            )
            
            extraction_response = response.choices[0].message.content.strip()
            # Remove markdown if present
            if extraction_response.startswith("```"):
                extraction_response = extraction_response.split("```")[1]
                if extraction_response.startswith("json"):
                    extraction_response = extraction_response[4:]
            extraction_response = extraction_response.strip()
            
            extracted_vars = json.loads(extraction_response)
            
            # Store extracted variables
            for var_name, var_value in extracted_vars.items():
                if var_value is not None:
                    self.session_variables[var_name] = var_value
                    logger.info(f"  ✓ {var_name}: {var_value} (extracted in background)")
                    
                    # Keep customer_name and callerName in sync (bidirectional)
                    if var_name == "customer_name":
                        self.session_variables["callerName"] = var_value
                        logger.info(f"  ✓ callerName: {var_value} (synced)")
                    elif var_name == "callerName":
                        self.session_variables["customer_name"] = var_value
                        logger.info(f"  ✓ customer_name: {var_value} (synced)")
            
            var_extract_ms = int((time.time() - var_extract_start) * 1000)
            logger.info(f"✅ Background extraction complete: {len(extracted_vars)} variables in {var_extract_ms}ms")
            
        except Exception as e:
            logger.error(f"Error in background extraction: {e} (non-blocking, continuing)")
    

    
    async def _check_mandatory_variables(self, extract_variables: list) -> dict:
        """Check if mandatory variables are present, return reprompt if missing"""
        try:
            missing_mandatory = []
            
            for var in extract_variables:
                var_name = var.get("name", "")
                is_mandatory = var.get("mandatory", False)
                prompt_message = var.get("prompt_message", "")
                
                if is_mandatory and var_name:
                    # Check if variable is missing or null
                    if var_name not in self.session_variables or self.session_variables[var_name] is None:
                        missing_mandatory.append({
                            "name": var_name,
                            "prompt_message": prompt_message,
                            "description": var.get("description", "")
                        })
                        logger.warning(f"⚠️ Mandatory variable missing: {var_name}")
            
            if missing_mandatory:
                logger.info(f"🚫 {len(missing_mandatory)} mandatory variables missing, generating reprompt")
                
                # Use the first missing variable's prompt message
                first_missing = missing_mandatory[0]
                prompt_message = first_missing["prompt_message"]
                
                if prompt_message:
                    # Use the provided prompt message to ask AI to generate a natural request
                    logger.info(f"📝 Using prompt message: {prompt_message}")
                    
                    # Get LLM to generate natural request based on prompt message
                    client = await self.get_llm_client_for_session("openai")
                    global_prompt = self.agent_config.get("system_prompt", "")
                    
                    generation_prompt = f"""You are having a conversation and need to ask for specific information.

Context: {prompt_message}

Your task: Generate a natural, conversational way to ask for this information. Be friendly and concise (1-2 sentences max).

Generate the request:"""
                    
                    messages = [
                        {"role": "system", "content": global_prompt},
                        {"role": "user", "content": generation_prompt}
                    ]
                    
                    response = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                        max_tokens=150
                    )
                    
                    reprompt_text = response.choices[0].message.content.strip()
                    logger.info(f"✅ Generated reprompt: {reprompt_text[:100]}...")
                    
                    return {
                        "success": False,
                        "reprompt_message": reprompt_text,
                        "missing_variables": [v["name"] for v in missing_mandatory]
                    }
                else:
                    # Fallback: generic reprompt
                    var_names = ", ".join([v["name"] for v in missing_mandatory])
                    return {
                        "success": False,
                        "reprompt_message": f"Could you please provide the {missing_mandatory[0]['name']}?",
                        "missing_variables": [v["name"] for v in missing_mandatory]
                    }
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error checking mandatory variables: {e}")
            return {"success": True}  # Don't block on errors


    async def _execute_webhook(self, node_data: dict, user_message: str) -> dict:
        """Execute webhook/function call with variable extraction"""
        try:
            webhook_url = node_data.get("webhook_url", "")
            webhook_method = node_data.get("webhook_method", "POST").upper()
            webhook_headers = node_data.get("webhook_headers", {})
            webhook_body_template = node_data.get("webhook_body", "")
            webhook_timeout = node_data.get("webhook_timeout", 10)
            response_variable = node_data.get("response_variable", "webhook_response")
            extract_variables = node_data.get("extract_variables", [])
            
            if not webhook_url:
                logger.warning("No webhook URL configured")
                return {"success": False, "message": "No webhook URL configured"}
            
            # Extract variables from conversation if configured
            if extract_variables and len(extract_variables) > 0:
                logger.info(f"🔍 Extracting {len(extract_variables)} variables from conversation...")
                
                # First, check if variables already exist in session_variables
                variables_to_extract = []
                already_available = {}
                
                for var in extract_variables:
                    var_name = var.get("name", "")
                    if var_name:
                        # Check if variable already exists in session
                        if var_name in self.session_variables:
                            already_available[var_name] = self.session_variables[var_name]
                            logger.info(f"  ✓ {var_name}: {self.session_variables[var_name]} (already in session)")
                        else:
                            variables_to_extract.append(var)
                
                # Only extract variables that aren't already available
                if variables_to_extract:
                    logger.info(f"🤖 Need to extract {len(variables_to_extract)} variables from conversation using LLM...")
                    
                    # Include existing session variables for reference in calculations
                    existing_vars_str = ""
                    if self.session_variables:
                        existing_vars_str = "\n\nEXISTING VARIABLES (use these exact values for calculations):\n"
                        for k, v in self.session_variables.items():
                            existing_vars_str += f"  {k} = {v}\n"
                    
                    # Build extraction prompt
                    extraction_prompt = "Extract the following information from the conversation:\n\n"
                    for var in variables_to_extract:
                        var_name = var.get("name", "")
                        var_description = var.get("description", "")
                        if var_name:
                            extraction_prompt += f"- {var_name}: {var_description}\n"
                    
                    extraction_prompt += existing_vars_str
                    extraction_prompt += "\n\nConversation history:\n"
                    for msg in self.conversation_history[-10:]:  # Last 10 messages
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        extraction_prompt += f"{role}: {content}\n"
                    
                    extraction_prompt += f"\nUser's latest message: {user_message}\n\n"
                    extraction_prompt += """IMPORTANT INSTRUCTIONS:
1. Look through the ENTIRE conversation above.
2. If a variable description mentions CALCULATING from other variables (e.g., "convert to monthly", "add X + Y", "divide by 12"), you MUST PERFORM THE MATH:
   - Use the EXISTING VARIABLES values above for calculations
   - Example: if business_income=120000 and side_hustle=24000, then (120000 + 24000) / 12 = 144000 / 12 = 12000
3. For monetary values, extract just the number (e.g., "50000" not "$50,000" or "50k").
4. If someone says "50k" or "fifty thousand", convert to 50000.
5. For monthly conversions: yearly / 12 = monthly. For yearly from monthly: monthly * 12 = yearly.
6. Return numbers as plain integers without commas or currency symbols.
7. DOUBLE-CHECK YOUR ARITHMETIC before returning.

Return ONLY a JSON object with the extracted values. If a value cannot be determined, use null. Example format:
"""
                    extraction_prompt += "{"
                    for i, var in enumerate(variables_to_extract):
                        var_name = var.get("name", "")
                        if var_name:
                            extraction_prompt += f'"{var_name}": <value>'
                            if i < len(variables_to_extract) - 1:
                                extraction_prompt += ", "
                    extraction_prompt += "}"
                    
                    # Call LLM to extract variables - use temperature=0 for deterministic math
                    try:
                        # Get LLM client
                        llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
                        if not llm_provider:
                            logger.error("❌ No LLM provider configured for agent")
                            return None
                        llm_model = self.agent_config.get("settings", {}).get("llm_model", "gpt-4o-mini")
                        
                        if llm_provider == "openai":
                            client = await self.get_llm_client_for_session("openai")
                            response = await client.chat.completions.create(
                                model=llm_model,
                                messages=[{"role": "user", "content": extraction_prompt}],
                                temperature=0.0,
                                max_tokens=500
                            )
                            extraction_response = response.choices[0].message.content
                        else:
                            # Fallback to OpenAI
                            client = await self.get_llm_client_for_session("openai")
                            response = await client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": extraction_prompt}],
                                temperature=0.0,
                                max_tokens=500
                            )
                            extraction_response = response.choices[0].message.content
                        
                        # Parse extracted variables
                        extracted_text = extraction_response.strip()
                        # Remove markdown code blocks if present
                        if extracted_text.startswith("```"):
                            extracted_text = extracted_text.split("```")[1]
                            if extracted_text.startswith("json"):
                                extracted_text = extracted_text[4:]
                        extracted_text = extracted_text.strip()
                        
                        extracted_vars = json.loads(extracted_text)
                        
                        # Store extracted variables in session
                        for var_name, var_value in extracted_vars.items():
                            if var_value is not None:
                                self.session_variables[var_name] = var_value
                                logger.info(f"  ✓ {var_name}: {var_value}")
                                
                                # Keep customer_name and callerName in sync (bidirectional)
                                if var_name == "customer_name":
                                    self.session_variables["callerName"] = var_value
                                    logger.info(f"  ✓ callerName: {var_value} (synced)")
                                elif var_name == "callerName":
                                    self.session_variables["customer_name"] = var_value
                                    logger.info(f"  ✓ customer_name: {var_value} (synced)")
                        
                        logger.info(f"✅ Extracted {len(extracted_vars)} variables from conversation")
                        
                    except Exception as e:
                        logger.error(f"Error extracting variables: {e}")
                        # Continue anyway with whatever variables we have
                else:
                    logger.info(f"✅ All {len(extract_variables)} variables already available in session")
            
            # Validate mandatory variables
            missing_required = []
            for var in extract_variables:
                var_name = var.get("name", "")
                is_required = var.get("required", False)
                if is_required and var_name:
                    if var_name not in self.session_variables or self.session_variables[var_name] is None:
                        missing_required.append(var)
                        logger.warning(f"❌ Required variable missing: {var_name}")
            
            # If mandatory variables are missing, return error with re-prompt
            if missing_required:
                logger.error(f"🚫 Cannot execute webhook: {len(missing_required)} required variables missing")
                
                # Generate re-prompt messages based on type (static or prompt)
                reprompt_messages = []
                for var in missing_required:
                    var_name = var.get("name", "")
                    reprompt_text = var.get("reprompt_text", "")
                    reprompt_type = var.get("reprompt_type", "static")  # Default to static
                    
                    if reprompt_text:
                        if reprompt_type == "prompt":
                            # AI-generated re-prompt based on instruction
                            logger.info(f"🤖 Generating AI re-prompt for {var_name} using instruction: {reprompt_text[:50]}...")
                            try:
                                # Build context for AI
                                context_messages = [
                                    {"role": "system", "content": f"You are a helpful phone agent. Generate a natural, conversational response. DO NOT include any format markers or meta-text."},
                                    {"role": "user", "content": f"Instruction: {reprompt_text}\n\nConversation context: {' '.join([msg.get('content', '')[:100] for msg in self.conversation_history[-3:]])}\n\nGenerate a natural response asking for the missing information."}
                                ]
                                
                                client = await self.get_llm_client_for_session("openai")
                                response = await client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=context_messages,
                                    temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                                    max_tokens=150
                                )
                                
                                generated_reprompt = response.choices[0].message.content.strip()
                                reprompt_messages.append(generated_reprompt)
                                logger.info(f"  ✓ Generated: {generated_reprompt[:50]}...")
                            except Exception as e:
                                logger.error(f"Error generating AI re-prompt: {e}, falling back to instruction text")
                                reprompt_messages.append(reprompt_text)
                        else:
                            # Static re-prompt - use exact text
                            logger.info(f"📢 Using static re-prompt for {var_name}: {reprompt_text[:50]}...")
                            reprompt_messages.append(reprompt_text)
                    else:
                        # No re-prompt text provided - generate default
                        var_description = var.get("description", var_name)
                        default_reprompt = f"I need to know {var_description}. Could you provide that?"
                        logger.info(f"📝 Using default re-prompt for {var_name}: {default_reprompt}")
                        reprompt_messages.append(default_reprompt)
                
                # Combine all re-prompts
                combined_reprompt = " ".join(reprompt_messages)
                logger.info(f"💬 Final re-prompt message: {combined_reprompt[:100]}...")
                
                return {
                    "success": False,
                    "message": combined_reprompt,
                    "missing_variables": [var.get("name") for var in missing_required],
                    "requires_reprompt": True
                }
            
            logger.info(f"🌐 Calling webhook: {webhook_method} {webhook_url}")
            
            # Prepare request body with context
            request_body = {}
            if webhook_body_template:
                try:
                    # Parse the webhook body template to check if it's a schema or a template
                    body_obj = json.loads(webhook_body_template)
                    
                    # Check if it's a JSON schema (has "type" and "properties" keys)
                    if isinstance(body_obj, dict) and "type" in body_obj and "properties" in body_obj:
                        # It's a schema - build request body from extracted variables
                        logger.info("📋 Detected JSON schema format - building request from extracted variables")
                        request_body = {}
                        
                        # Build request body from schema properties and extracted variables
                        for prop_name, prop_def in body_obj.get("properties", {}).items():
                            if prop_name in self.session_variables:
                                request_body[prop_name] = self.session_variables[prop_name]
                            else:
                                # Property not found in extracted variables
                                logger.warning(f"⚠️ Variable '{prop_name}' not found in extracted variables")
                                request_body[prop_name] = None
                    else:
                        # It's a template with {{variable}} placeholders - replace them
                        logger.info("📝 Detected template format - replacing placeholders")
                        body_str = webhook_body_template
                        body_str = body_str.replace("{{user_message}}", user_message)
                        body_str = body_str.replace("{{call_id}}", self.call_id)
                        
                        # Replace session variables
                        for var_name, var_value in self.session_variables.items():
                            body_str = body_str.replace(f"{{{{{var_name}}}}}", str(var_value))
                        
                        request_body = json.loads(body_str)
                except Exception as e:
                    logger.error(f"Error parsing webhook body template: {e}")
                    request_body = {
                        "user_message": user_message,
                        "call_id": self.call_id,
                        "variables": self.session_variables
                    }
            else:
                # Default body
                request_body = {
                    "user_message": user_message,
                    "call_id": self.call_id,
                    "conversation_history": self.conversation_history[-10:],  # Last 10 messages
                    "variables": self.session_variables
                }
            
            logger.info(f"📤 Request body: {json.dumps(request_body, indent=2)[:500]}...")
            
            # Retry configuration
            max_retries = node_data.get("webhook_max_retries", 1)  # Default: 1 retry (2 total attempts)
            retry_timeout = node_data.get("webhook_retry_timeout", 30)  # 30s for retry attempts
            
            # Retry loop - only retries on timeout, not on other errors
            response = None
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Use configured timeout for first attempt, longer timeout for retries
                    current_timeout = webhook_timeout if attempt == 0 else retry_timeout
                    
                    if attempt > 0:
                        logger.warning(f"🔄 Webhook retry attempt {attempt + 1}/{max_retries + 1} with {current_timeout}s timeout...")
                    
                    async with httpx.AsyncClient(timeout=current_timeout) as client:
                        if webhook_method == "GET":
                            response = await client.get(webhook_url, headers=webhook_headers)
                        else:  # POST
                            response = await client.post(
                                webhook_url,
                                json=request_body,
                                headers=webhook_headers
                            )
                        
                        logger.info(f"✅ Webhook response: {response.status_code}")
                        
                        # Success - break out of retry loop
                        if response.status_code == 200:
                            break
                        else:
                            # Non-200 response - don't retry, just handle the error
                            logger.error(f"Webhook failed with status {response.status_code}: {response.text}")
                            return {
                                "success": False,
                                "message": f"Webhook failed with status {response.status_code}"
                            }
                            
                except httpx.TimeoutException as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(f"⏳ Webhook timeout after {current_timeout}s (attempt {attempt + 1}/{max_retries + 1}), will retry...")
                        # NOTE: No dialogue is spoken on retry - the filler statement was already spoken before the first attempt
                        continue
                    else:
                        logger.error(f"❌ Webhook failed after {max_retries + 1} attempts (all timed out)")
                        return {"success": False, "message": f"Webhook timeout after {max_retries + 1} attempts"}
                        
                except Exception as e:
                    # For non-timeout errors, don't retry
                    logger.error(f"Error executing webhook: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return {"success": False, "message": f"Webhook error: {str(e)}"}
            
            # If we get here without a response, all retries timed out
            if response is None:
                logger.error(f"❌ Webhook failed - no response after {max_retries + 1} attempts")
                return {"success": False, "message": "Webhook timeout after retries"}
                
            # Process successful response
            if response.status_code == 200:
                # Try to parse JSON response
                try:
                    response_text = response.text
                    logger.info(f"📥 Response text: {response_text[:200]}...")
                    
                    if response_text.strip():
                        # Try strict JSON parsing first
                        try:
                            response_data = response.json()
                        except json.JSONDecodeError:
                            # If that fails, try with json.loads which is more lenient
                            logger.warning("⚠️ Standard JSON parsing failed, trying lenient parsing...")
                            response_data = json.loads(response_text, strict=False)
                        
                        logger.info(f"📥 Response data: {json.dumps(response_data, indent=2)[:300]}...")
                    else:
                        # Empty response - treat as success
                        logger.warning("⚠️ Webhook returned empty response, treating as success")
                        response_data = {"success": True, "message": "Webhook completed"}
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"❌ Failed to parse webhook response as JSON: {e}")
                    logger.error(f"Response text: {response.text[:500]}")
                    # Try to extract JSON from text using regex
                    import re
                    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if json_match:
                        try:
                            logger.info("🔍 Found JSON pattern in response, attempting to parse...")
                            response_data = json.loads(json_match.group(0), strict=False)
                        except:
                            # Return the raw text as response
                            response_data = {
                                "success": True,
                                "message": "Webhook completed",
                                "raw_response": response.text
                            }
                    else:
                        # Return the raw text as response
                        response_data = {
                            "success": True,
                            "message": "Webhook completed",
                            "raw_response": response.text
                        }
                
                # Store response in session variables
                self.session_variables[response_variable] = response_data
                logger.info(f"💾 Stored webhook response in variable: {response_variable}")
                
                # Extract individual fields from response and update session variables
                # This allows subsequent nodes to access updated values
                if isinstance(response_data, dict):
                    logger.info(f"🔄 Extracting fields from webhook response to update session variables...")
                    logger.info(f"Response data keys: {list(response_data.keys())}")
                    updated_vars = []
                    
                    # Try to intelligently extract data from common n8n/automation response formats
                    actual_data = response_data
                    
                    # Check if we have a raw_response string that might contain JSON
                    if "raw_response" in response_data and isinstance(response_data.get("raw_response"), str):
                        logger.info("📦 Detected raw_response string - attempting to parse as JSON...")
                        logger.info(f"raw_response type: {type(response_data['raw_response'])}")
                        logger.info(f"raw_response preview: {str(response_data['raw_response'])[:100]}...")
                        raw_str = response_data["raw_response"]
                        
                        # Check if this contains tool_calls_results with markdown JSON
                        # Many n8n webhooks return JSON embedded in markdown code blocks
                        import re
                        if "tool_calls_results" in raw_str and "```json" in raw_str:
                            logger.info("📦 Detected tool_calls_results with markdown JSON - extracting...")
                            try:
                                # Extract JSON directly from markdown code block (simplest and most reliable)
                                json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_str, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(1)
                                    actual_data = json.loads(json_str)
                                    logger.info(f"✅ Extracted JSON from markdown: {json.dumps(actual_data, indent=2)[:200]}...")
                                else:
                                    logger.warning("⚠️ Could not find JSON in markdown code block")
                            except Exception as e:
                                logger.warning(f"⚠️ Could not extract from markdown: {e}")
                        elif "tool_calls_results" in raw_str:
                            # tool_calls_results exists but no markdown, try standard extraction
                            logger.info("📦 Detected tool_calls_results without markdown - trying standard extraction...")
                            try:
                                temp_data = json.loads(raw_str, strict=False)
                                result_str = temp_data.get("tool_calls_results", [{}])[0].get("result", "")
                                if result_str.strip().startswith('{'):
                                    actual_data = json.loads(result_str.strip())
                                    logger.info(f"✅ Parsed result as JSON: {json.dumps(actual_data, indent=2)[:200]}...")
                            except Exception as e:
                                logger.warning(f"⚠️ Could not extract from tool_calls_results: {e}")
                        else:
                            # No tool_calls_results, try standard JSON parsing
                            try:
                                actual_data = json.loads(raw_str, strict=False)
                                logger.info(f"✅ Parsed raw_response as JSON: {list(actual_data.keys())}")
                            except Exception as e:
                                logger.warning(f"⚠️ Could not parse raw_response as JSON: {e}")
                                # Try regex extraction
                                json_match = re.search(r'\{.*\}', raw_str, re.DOTALL)
                                if json_match:
                                    try:
                                        actual_data = json.loads(json_match.group(0), strict=False)
                                        logger.info(f"✅ Extracted and parsed JSON from raw_response: {list(actual_data.keys())}")
                                    except Exception as e2:
                                        logger.warning(f"⚠️ Regex extraction also failed: {e2}, using original data")
                    
                    # Check for n8n tool_call_response format (if not already handled above)
                    elif "tool_calls_results" in actual_data:
                        logger.info("📦 Detected n8n tool_calls_results format - extracting nested data...")
                        try:
                            # Get the result from tool_calls_results array
                            result_str = actual_data.get("tool_calls_results", [{}])[0].get("result", "")
                            
                            # Try to extract JSON from the result string
                            import re
                            json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_str, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1)
                                actual_data = json.loads(json_str)
                                logger.info(f"✅ Extracted JSON from tool_calls_results: {json.dumps(actual_data, indent=2)[:200]}...")
                            elif result_str.strip().startswith('{'):
                                # Try parsing as direct JSON
                                actual_data = json.loads(result_str)
                                logger.info(f"✅ Parsed result as JSON: {json.dumps(actual_data, indent=2)[:200]}...")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not extract nested JSON: {e}, using top-level data")
                            actual_data = response_data
                    
                    # Check for common wrapper formats
                    if "data" in actual_data and isinstance(actual_data.get("data"), dict):
                        logger.info("📦 Detected 'data' wrapper - extracting nested data...")
                        actual_data = actual_data["data"]
                    elif "result" in actual_data and isinstance(actual_data.get("result"), dict):
                        logger.info("📦 Detected 'result' wrapper - extracting nested data...")
                        actual_data = actual_data["result"]
                    
                    # Now extract fields from actual_data
                    for field_name, field_value in actual_data.items():
                        # Skip meta fields that shouldn't be individual variables
                        if field_name not in ["success", "message", "error", "status", "response_type", "tool_calls_results", "raw_response"]:
                            self.session_variables[field_name] = field_value
                            updated_vars.append(f"{field_name}={field_value}")
                            logger.info(f"  ✓ Updated session variable: {field_name} = {field_value}")
                    
                    if updated_vars:
                        logger.info(f"✅ Updated {len(updated_vars)} session variables from webhook response")
                    else:
                        logger.info("ℹ️ No individual fields to extract from webhook response")
                
                return {
                    "success": True,
                    "message": "Webhook executed successfully",
                    "data": response_data
                }
            else:
                logger.error(f"Webhook failed with status {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "message": f"Webhook failed with status {response.status_code}"
                }
                    
        except Exception as e:
            logger.error(f"Error executing webhook: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "message": f"Webhook error: {str(e)}"}
    
    def _handle_transfer(self, node_data: dict) -> dict:
        """Handle call transfer request"""
        try:
            transfer_type = node_data.get("transfer_type", "cold")  # cold or warm
            destination_type = node_data.get("destination_type", "phone")  # phone or agent
            destination = node_data.get("destination", "")
            transfer_message = node_data.get("transfer_message", "Please hold while I transfer your call...")
            
            logger.info(f"📞 Transfer request: {transfer_type} transfer to {destination_type}: {destination}")
            
            # In a real implementation, this would:
            # 1. For phone: Initiate SIP/PSTN transfer to phone number
            # 2. For agent: Transfer to another agent or queue
            # 3. Handle warm transfer (conference) vs cold transfer (blind)
            
            # For now, we store the transfer request and return info
            return {
                "success": True,
                "transfer_type": transfer_type,
                "destination_type": destination_type,
                "destination": destination,
                "message": transfer_message
            }
            
        except Exception as e:
            logger.error(f"Error handling transfer: {e}")
            return {
                "success": False,
                "message": "Transfer failed. Please stay on the line."
            }
    
    def _handle_collect_input(self, node_data: dict, user_input: str) -> dict:
        """Validate and collect user input based on specified type"""
        try:
            import re
            
            input_type = node_data.get("input_type", "text")  # text, email, phone, number
            variable_name = node_data.get("variable_name", "user_input")
            error_message = node_data.get("error_message", "That doesn't look right. Please try again.")
            
            logger.info(f"📝 Validating input type: {input_type}")
            
            # Validate based on input type
            if input_type == "email":
                # Basic email validation
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if re.match(email_pattern, user_input.strip()):
                    return {
                        "valid": True,
                        "value": user_input.strip(),
                        "success_message": f"Got it, your email is {user_input.strip()}."
                    }
                else:
                    return {
                        "valid": False,
                        "error": "Invalid email format",
                        "error_message": error_message or "That doesn't look like a valid email address. Please provide your email."
                    }
            
            elif input_type == "phone":
                # Basic phone validation (digits only, 10-15 digits)
                phone_digits = re.sub(r'[^\d]', '', user_input)
                if 10 <= len(phone_digits) <= 15:
                    return {
                        "valid": True,
                        "value": phone_digits,
                        "success_message": "Thank you, I have your phone number."
                    }
                else:
                    return {
                        "valid": False,
                        "error": "Invalid phone format",
                        "error_message": error_message or "That doesn't look like a valid phone number. Please provide your phone number."
                    }
            
            elif input_type == "number":
                # Validate number
                try:
                    number_value = float(user_input.strip())
                    return {
                        "valid": True,
                        "value": number_value,
                        "success_message": f"Got it, {number_value}."
                    }
                except ValueError:
                    return {
                        "valid": False,
                        "error": "Not a valid number",
                        "error_message": error_message or "Please provide a valid number."
                    }
            
            else:  # text - accept any non-empty input
                if user_input.strip():
                    return {
                        "valid": True,
                        "value": user_input.strip(),
                        "success_message": "Thank you."
                    }
                else:
                    return {
                        "valid": False,
                        "error": "Empty input",
                        "error_message": error_message or "Please provide your information."
                    }
                    
        except Exception as e:
            logger.error(f"Error validating input: {e}")
            return {
                "valid": False,
                "error": str(e),
                "error_message": "I didn't understand that. Please try again."
            }
    
    async def _handle_send_sms(self, node_data: dict, user_message: str) -> dict:
        """Send SMS message (mock implementation)"""
        try:
            phone_number = node_data.get("phone_number", "")
            sms_message = node_data.get("sms_message", "")
            
            # Replace variables in phone number and message
            if phone_number:
                for var_name, var_value in self.session_variables.items():
                    phone_number = phone_number.replace(f"{{{{{var_name}}}}}", str(var_value))
            
            if sms_message:
                for var_name, var_value in self.session_variables.items():
                    sms_message = sms_message.replace(f"{{{{{var_name}}}}}", str(var_value))
            
            logger.info(f"📱 Sending SMS to {phone_number}: {sms_message[:50]}...")
            
            # In a real implementation, this would:
            # 1. Use Twilio, AWS SNS, or similar SMS service
            # 2. Send actual SMS to phone number
            # 3. Handle delivery status and callbacks
            
            # For now, we mock the SMS sending
            if not phone_number or not sms_message:
                return {
                    "success": False,
                    "status": "failed",
                    "error": "Missing phone number or message",
                    "message": "I couldn't send the SMS. Missing information."
                }
            
            # Mock successful SMS
            logger.info(f"✅ SMS sent successfully to {phone_number}")
            return {
                "success": True,
                "status": "sent",
                "phone_number": phone_number,
                "message": "I've sent you an SMS with the information."
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return {
                "success": False,
                "status": "error",
                "error": str(e),
                "message": "I encountered an error sending the SMS. Please try again."
            }
    
    def _evaluate_logic_conditions(self, node_data: dict) -> str:
        """Evaluate logic conditions and return next node ID"""
        try:
            conditions = node_data.get("conditions", [])
            
            logger.info(f"🔀 Evaluating {len(conditions)} conditions")
            
            for idx, condition in enumerate(conditions):
                variable_name = condition.get("variable", "")
                operator = condition.get("operator", "equals")
                compare_value = condition.get("value", "")
                next_node_id = condition.get("nextNode", "")
                
                # Get variable value from session
                variable_value = self.session_variables.get(variable_name, "")
                
                logger.info(f"  Condition {idx + 1}: {variable_name} {operator} {compare_value}")
                logger.info(f"    Variable value: {variable_value}")
                
                # Evaluate condition
                result = False
                
                if operator == "equals":
                    result = str(variable_value).lower() == str(compare_value).lower()
                elif operator == "not_equals":
                    result = str(variable_value).lower() != str(compare_value).lower()
                elif operator == "contains":
                    result = str(compare_value).lower() in str(variable_value).lower()
                elif operator == "greater_than":
                    try:
                        var_num = self._extract_numeric_value(variable_value)
                        compare_num = self._extract_numeric_value(compare_value)
                        if var_num is not None and compare_num is not None:
                            result = var_num > compare_num
                            logger.info(f"    Numeric comparison: {var_num} > {compare_num} = {result}")
                        else:
                            logger.warning(f"    Could not extract numbers: var={var_num}, compare={compare_num}")
                            result = False
                    except (ValueError, TypeError) as e:
                        logger.warning(f"    Error in greater_than comparison: {e}")
                        result = False
                elif operator == "less_than":
                    try:
                        var_num = self._extract_numeric_value(variable_value)
                        compare_num = self._extract_numeric_value(compare_value)
                        if var_num is not None and compare_num is not None:
                            result = var_num < compare_num
                            logger.info(f"    Numeric comparison: {var_num} < {compare_num} = {result}")
                        else:
                            logger.warning(f"    Could not extract numbers: var={var_num}, compare={compare_num}")
                            result = False
                    except (ValueError, TypeError) as e:
                        logger.warning(f"    Error in less_than comparison: {e}")
                        result = False
                elif operator == "greater_than_or_equal":
                    try:
                        var_num = self._extract_numeric_value(variable_value)
                        compare_num = self._extract_numeric_value(compare_value)
                        if var_num is not None and compare_num is not None:
                            result = var_num >= compare_num
                            logger.info(f"    Numeric comparison: {var_num} >= {compare_num} = {result}")
                        else:
                            result = False
                    except (ValueError, TypeError):
                        result = False
                elif operator == "less_than_or_equal":
                    try:
                        var_num = self._extract_numeric_value(variable_value)
                        compare_num = self._extract_numeric_value(compare_value)
                        if var_num is not None and compare_num is not None:
                            result = var_num <= compare_num
                            logger.info(f"    Numeric comparison: {var_num} <= {compare_num} = {result}")
                        else:
                            result = False
                    except (ValueError, TypeError):
                        result = False
                elif operator == "exists":
                    result = variable_name in self.session_variables and variable_value not in [None, "", "undefined"]
                elif operator == "not_exists":
                    result = variable_name not in self.session_variables or variable_value in [None, "", "undefined"]
                elif operator == "starts_with":
                    result = str(variable_value).lower().startswith(str(compare_value).lower())
                elif operator == "ends_with":
                    result = str(variable_value).lower().endswith(str(compare_value).lower())
                
                logger.info(f"    Result: {result}")
                
                if result and next_node_id:
                    logger.info(f"✅ Condition {idx + 1} matched - routing to node {next_node_id}")
                    return next_node_id
            
            # No condition matched - use default path
            default_next_node = node_data.get("default_next_node", "")
            if default_next_node:
                logger.info(f"ℹ️ No conditions matched - using default path: {default_next_node}")
                return default_next_node
            
            logger.info("⚠️ No conditions matched and no default path")
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating logic conditions: {e}")
            return None
    
    def _extract_numeric_value(self, value) -> float:
        """
        Extract numeric value from various formats:
        - Pure numbers: 10000, 10000.50
        - With currency: $10,000, $10k
        - With text: "8k a month", "$100k a year", "Greater than $8k"
        - Shorthand: 10k, 100K, 1M
        """
        import re
        
        if value is None:
            return None
        
        # Convert to string
        value_str = str(value).lower().strip()
        
        # If it's already a number, return it
        try:
            return float(value)
        except (ValueError, TypeError):
            pass
        
        # Remove common text and keep numbers
        # Remove currency symbols and commas
        value_str = value_str.replace('$', '').replace(',', '').replace(' ', '')
        
        # Handle shorthand multipliers (k, K, m, M)
        # Look for patterns like "8k", "100k", "1m", "1.5m"
        multiplier_match = re.search(r'(\d+(?:\.\d+)?)\s*([kmb])', value_str)
        if multiplier_match:
            number = float(multiplier_match.group(1))
            multiplier = multiplier_match.group(2)
            if multiplier == 'k':
                return number * 1000
            elif multiplier == 'm':
                return number * 1000000
            elif multiplier == 'b':
                return number * 1000000000
        
        # Try to extract any number from the string
        number_match = re.search(r'(\d+(?:\.\d+)?)', value_str)
        if number_match:
            return float(number_match.group(1))
        
        return None
    
    def _handle_press_digit(self, node_data: dict, user_message: str) -> dict:
        """Handle DTMF digit press"""
        try:
            # Extract digit from user message (looking for single digit 0-9, *, #)
            import re
            
            # Check if message contains a single digit or DTMF character
            digit_match = re.search(r'[0-9*#]', user_message)
            
            if digit_match:
                digit = digit_match.group(0)
                logger.info(f"🔢 Detected digit: {digit}")
                
                # Get digit mappings from node data
                digit_mappings = node_data.get("digit_mappings", {})
                
                # Find corresponding next node for this digit
                next_node_id = digit_mappings.get(digit, "")
                
                if next_node_id:
                    return {
                        "digit": digit,
                        "next_node_id": next_node_id,
                        "message": f"You pressed {digit}."
                    }
                else:
                    return {
                        "digit": digit,
                        "next_node_id": None,
                        "message": f"You pressed {digit}, but no action is configured for this digit."
                    }
            else:
                prompt = node_data.get("prompt_message", "Please press a digit from 0 to 9, * or #.")
                return {
                    "digit": None,
                    "next_node_id": None,
                    "message": prompt
                }
                
        except Exception as e:
            logger.error(f"Error handling press digit: {e}")
            return {
                "digit": None,
                "next_node_id": None,
                "message": "Please press a digit."
            }
    
    async def _handle_extract_variable(self, node_data: dict, user_message: str) -> dict:
        """Extract variable from user message using AI"""
        try:
            variable_name = node_data.get("variable_name", "extracted_data")
            extraction_prompt = node_data.get("extraction_prompt", "")
            
            logger.info(f"📋 Extracting {variable_name} from: {user_message}")
            
            # Use AI to extract the variable
            client = await self.get_llm_client_for_session("openai")
            if not client:
                logger.warning("OpenAI client not available for extraction")
                return {
                    "success": False,
                    "message": "Could not extract information."
                }
            
            # Create extraction prompt
            system_prompt = f"""Extract the following information from the user's message: {extraction_prompt}

Return ONLY the extracted value, nothing else. If you cannot find the information, respond with "NOT_FOUND".

Examples:
- If asked to extract a name from "My name is John", return: John
- If asked to extract an email from "Contact me at john@email.com", return: john@email.com
- If asked to extract a date from "I'll be there on Monday", return: Monday"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await client.chat.completions.create(
                model=self.agent_config.get("model", "gpt-4-turbo"),
                messages=messages,
                temperature=0.3,
                max_tokens=100
            )
            
            extracted_value = response.choices[0].message.content.strip()
            
            if extracted_value and extracted_value != "NOT_FOUND":
                logger.info(f"✅ Extracted value: {extracted_value}")
                return {
                    "success": True,
                    "value": extracted_value,
                    "message": f"Got it, {extracted_value}."
                }
            else:
                logger.info(f"❌ Could not extract {variable_name}")
                return {
                    "success": False,
                    "message": f"I couldn't find the {variable_name}. Could you please provide it again?"
                }
                
        except Exception as e:
            logger.error(f"Error extracting variable: {e}")
            return {
                "success": False,
                "message": "I had trouble understanding. Could you please repeat that?"
            }
    
    async def _generate_rephrased_script(self, original_script: str, user_message: str, custom_prompt: str = "") -> str:
        """Generate a natural rephrase of the script for retry scenarios.
        
        Used when agent stays on same script node (no transition matched) and 
        dynamic_rephrase is enabled. Creates a natural variation instead of 
        repeating the exact same words.
        
        Args:
            original_script: The original script text to rephrase
            user_message: What the user said
            custom_prompt: Optional custom instructions for how to rephrase
        """
        try:
            # Get LLM provider and appropriate client using user's API keys
            llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
            if not llm_provider:
                llm_provider = "openai"  # Default
            
            llm_model = self.agent_config.get("settings", {}).get("llm_model") or "gpt-4o-mini"
            
            from api_key_service import get_api_key
            api_key = await get_api_key(self.user_id, llm_provider)
            
            if llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=api_key)
            elif llm_provider == "anthropic":
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=api_key)
                
                # Build the prompt with optional custom instructions
                base_prompt = f"""The user responded: "{user_message}"

The agent needs to say something similar to: "{original_script}"

But the agent just said this exact phrase. Generate a natural variation that:
- Conveys the same intent/meaning
- Sounds natural (not robotic)
- Is concise (similar length or shorter)
- Can acknowledge the user's response briefly if appropriate"""
                
                if custom_prompt:
                    base_prompt += f"\n\nAdditional guidance: {custom_prompt}"
                
                base_prompt += "\n\nRespond with ONLY the rephrased text, no quotes or explanation."
                
                # Use Anthropic's API format
                response = await client.messages.create(
                    model=llm_model,
                    max_tokens=150,
                    messages=[{"role": "user", "content": base_prompt}]
                )
                return response.content[0].text.strip()
            else:
                # Default to OpenAI-compatible
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=api_key)
            
            # Build the prompt with optional custom instructions
            base_prompt = f"""The user responded: "{user_message}"

The agent needs to say something similar to: "{original_script}"

But the agent just said this exact phrase. Generate a natural variation that:
- Conveys the same intent/meaning
- Sounds natural (not robotic)
- Is concise (similar length or shorter)
- Can acknowledge the user's response briefly if appropriate"""
            
            if custom_prompt:
                base_prompt += f"\n\nAdditional guidance: {custom_prompt}"
            
            base_prompt += "\n\nRespond with ONLY the rephrased text, no quotes or explanation."
            
            # OpenAI format
            response = await client.chat.completions.create(
                model=llm_model,
                messages=[{"role": "user", "content": base_prompt}],
                max_tokens=150,
                temperature=0.8
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating rephrased script: {e}")
            # Fallback to slightly modified original
            return f"Let me say that again - {original_script}"
    
    async def _generate_ai_response_streaming(self, content: str, stream_callback=None, current_node: dict = None) -> str:
        """Generate AI response with streaming support"""
        import re
        
        # Get LLM provider and appropriate client using user's API keys
        llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
        if not llm_provider:
            logger.error("❌ No LLM provider configured for agent")
            return None
        model = self.agent_config.get("model", "gpt-4-turbo")
        
        try:
            client = await self.get_llm_client_for_session(provider=llm_provider)
        except ValueError as e:
            logger.error(f"Failed to get LLM client: {e}")
            # Return content as-is with error message
            error_msg = f"AI service unavailable: {str(e)}"
            if stream_callback:
                await stream_callback(error_msg)
            return error_msg
        
        if not client:
            # No AI available, return content as-is
            if stream_callback:
                await stream_callback(content)
            return content
        
        # Extract actual script from content if it has markers
        script_to_use = content
        extracted = False
        if "AGENT_SCRIPT_LINE_INPUT:" in content:
            # Extract the script line from format like: `AGENT_SCRIPT_LINE_INPUT:` "{{customer_name}}?"
            match = re.search(r'AGENT_SCRIPT_LINE_INPUT[:`\s]+["\']([^"\']+)["\']', content)
            if match:
                script_to_use = match.group(1)
                extracted = True
                logger.info(f"📝 Extracted script: {script_to_use}")
        
        # If we extracted the script, just return it with variable substitution
        if extracted:
            # Do variable substitution
            for var_name, var_value in self.session_variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                script_to_use = script_to_use.replace(placeholder, str(var_value))
            
            if stream_callback:
                await stream_callback(script_to_use)
                logger.info(f"📤 Streamed extracted script: {script_to_use[:50]}...")
            return script_to_use
        
        # Otherwise, use LLM to interpret the prompt with streaming
        # 🚀 GROK PREFIX CACHING: Reuse the EXACT same system prompt string object
        # Grok automatically caches based on prefix matching, so using the same string enables caching
        
        # STATIC PART (cached across all turns) - built once in __init__, reused every turn
        # This enables Grok's automatic prefix caching to work efficiently
        cached_system_prompt = self._cached_system_prompt
        
        # SMART ROUTING: Determine if KB retrieval is needed
        # Get last user message first (needed for both KB routing and preprocessing)
        last_user_msg = ""
        for msg in reversed(self.conversation_history):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        # Check if parallel mode enabled for THIS node
        use_parallel = current_node and current_node.get("data", {}).get("use_parallel_llm", False)
        
        # RAG: Retrieve relevant KB chunks (parallelize if multi-LLM enabled)
        kb_context = ""
        
        if use_parallel and self.knowledge_base and self.agent_id:
            # PARALLEL MODE: Run KB + preprocessing simultaneously
            try:
                logger.info("⚡ PARALLEL MODE: Running KB + analysis simultaneously")
                import asyncio
                from kb_router import needs_knowledge_base
                from rag_service import retrieve_chunks_chromadb, retrieve_relevant_chunks_by_agent
                
                parallel_start = time.time()
                
                # Check if KB needed
                needs_kb, reason = needs_knowledge_base(last_user_msg)
                
                if needs_kb:
                    # Try ChromaDB first (pre-indexed, searches ALL chunks - better for large KBs)
                    kb_chunks = await retrieve_chunks_chromadb(
                        agent_id=self.agent_id,
                        query=last_user_msg,
                        top_k=None,  # Use dynamic top_k based on query complexity
                    )
                    
                    # Fallback to MongoDB if ChromaDB returns nothing (not indexed yet)
                    if not kb_chunks:
                        logger.info("⚡ ChromaDB empty, falling back to MongoDB retrieval")
                        kb_chunks = await retrieve_relevant_chunks_by_agent(
                            agent_id=self.agent_id,
                            query=last_user_msg,
                            top_k=None,
                            db=self.db
                        )
                    
                    if kb_chunks:
                        # Use reasonable chunk sizes - enough to be useful
                        kb_context = "\n\n".join([chunk.get('content', '')[:3000] for chunk in kb_chunks])  # 3K chars per chunk = ~600 words
                        kb_context = f"\n\n=== RELEVANT KNOWLEDGE ===\n{kb_context}\n⚠️ Use ONLY this information.\n=== END KNOWLEDGE ===\n"
                        logger.info(f"⚡ Parallel KB retrieval: {len(kb_chunks)} chunks")
                else:
                    logger.info(f"⚡ Skipping KB (reason: {reason})")
                
                parallel_time = int((time.time() - parallel_start) * 1000)
                logger.info(f"⚡ Parallel operations completed in {parallel_time}ms")
                
            except Exception as e:
                logger.error(f"❌ Parallel processing error: {e}, falling back")
                
        elif self.knowledge_base and self.agent_id:
            # REGULAR MODE: Sequential KB retrieval
            from kb_router import needs_knowledge_base
            
            needs_kb, reason = needs_knowledge_base(last_user_msg)
            
            if needs_kb:
                try:
                    retrieval_start = time.time()
                    from rag_service import retrieve_chunks_chromadb, retrieve_relevant_chunks_by_agent
                    
                    # Try ChromaDB first (pre-indexed, searches ALL chunks - better for large KBs)
                    kb_chunks = await retrieve_chunks_chromadb(
                        agent_id=self.agent_id,
                        query=last_user_msg,
                        top_k=None,  # Use dynamic top_k based on query complexity
                    )
                    
                    # Fallback to MongoDB if ChromaDB returns nothing (not indexed yet)
                    if not kb_chunks:
                        logger.info("🔍 ChromaDB empty, falling back to MongoDB retrieval")
                        kb_chunks = await retrieve_relevant_chunks_by_agent(
                            agent_id=self.agent_id,
                            query=last_user_msg,
                            top_k=None,
                            db=self.db
                        )
                    
                    if kb_chunks:
                        # Use full chunks - 3K chars each for useful context
                        kb_context = "\n\n".join([chunk.get('content', '')[:3000] for chunk in kb_chunks])
                        retrieval_time = (time.time() - retrieval_start) * 1000
                        logger.info(f"🔍 RAG retrieval: {retrieval_time:.0f}ms, {len(kb_chunks)} chunks")
                        
                        kb_context = f"\n\n=== RELEVANT KNOWLEDGE ===\n{kb_context}\n⚠️ Use ONLY this information.\n=== END KNOWLEDGE ===\n"
                        
                except Exception as e:
                    logger.error(f"❌ RAG retrieval error: {e}")
            else:
                logger.info(f"⚡ Skipping RAG (reason: {reason})")
        
        # 🚀 PARALLEL SPECIALISTS: Run analysis in parallel for speed
        # Check if parallel mode is enabled for THIS SPECIFIC NODE
        use_parallel = False
        if current_node:
            use_parallel = current_node.get("data", {}).get("use_parallel_llm", False)
            node_label = current_node.get("label", "unknown")
            logger.info(f"🔍 Node '{node_label}': use_parallel_llm={use_parallel}")
        
        # PREPROCESSING LAYER (Iteration 15) - Help LLM prioritize
        from preprocessing_layer import build_preprocessing_context
        preprocessing_context = build_preprocessing_context(
            last_user_msg,  # Use the last user message we already extracted above
            self.session_variables,
            self.conversation_history
        )
        
        # DYNAMIC PART (changes every turn) - context, customer info, current instruction
        # KB added here ONLY when needed (smart routing)
        dynamic_context = f"""
{preprocessing_context}
# CURRENT CONTEXT
Customer: {self.session_variables.get('customer_name', 'the customer')}
Variables: {json.dumps(self.session_variables)}
{kb_context}
# YOUR TASK RIGHT NOW
{content}

Respond naturally to the user based on these instructions. Remember: DO NOT repeat what you've already said."""
        
        # Construct messages with caching hint
        # For parallel-enabled nodes: Use condensed history for speed
        # For regular nodes: Use full history for context
        if use_parallel:
            # Parallel mode: Use last 10 messages only for speed
            conversation_history = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
            logger.info(f"⚡ Parallel mode: Using condensed history ({len(conversation_history)}/{len(self.conversation_history)} messages)")
        else:
            # Regular mode: Full history
            conversation_history = self.conversation_history
        
        messages = [
            {"role": "system", "content": cached_system_prompt, "cache_control": {"type": "ephemeral"}},
            {"role": "system", "content": dynamic_context}
        ] + conversation_history
        
        # Log context usage
        history_count = len(self.conversation_history)
        total_prompt_chars = len(cached_system_prompt) + len(dynamic_context)
        import datetime
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.info(f"⏱️ [{timestamp_str}] 💬 LLM REQUEST START: {history_count} conversation turns, {total_prompt_chars} system chars (KB cached)")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # DETAILED PROMPT LOGGING - Shows what's being sent to LLM each turn
        # ═══════════════════════════════════════════════════════════════════════════
        logger.info(f"📝 ═══════════ LLM PROMPT BREAKDOWN ═══════════")
        logger.info(f"📝 [SYSTEM MSG 1 - GLOBAL PROMPT] ({len(cached_system_prompt)} chars):")
        # Log first 500 chars of global prompt to see what's there
        logger.info(f"📝   Preview: {cached_system_prompt[:500]}...")
        logger.info(f"📝 [SYSTEM MSG 2 - DYNAMIC CONTEXT] ({len(dynamic_context)} chars):")
        # Log the dynamic context which includes node instructions
        logger.info(f"📝   Preview: {dynamic_context[:800]}...")
        logger.info(f"📝 [CONVERSATION HISTORY] ({len(conversation_history)} messages)")
        # Log last 2 messages for context
        if conversation_history:
            for msg in conversation_history[-2:]:
                role = msg.get('role', 'unknown')
                content_preview = msg.get('content', '')[:100]
                logger.info(f"📝   {role}: {content_preview}...")
        logger.info(f"📝 ═══════════════════════════════════════════")
        
        # Stream LLM response and process sentence by sentence
        llm_request_start = time.time()
        
        # Call LLM based on provider with streaming
        if llm_provider == "grok":
            response = await client.create_completion(
                messages=messages,
                model=model,
                temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 300),
                stream=True
            )
        else:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 300),
                stream=True
            )
        
        # Collect response and stream sentences
        full_response = ""
        sentence_buffer = ""
        first_token_received = False
        
        # Sentence delimiters - expanded to handle run-on sentences
        # Primary: .!? (strong boundaries)
        # Secondary: , — ; (weak boundaries after 2s timeout)
        sentence_endings = re.compile(r'([.!?]\s+|[,—;]\s+)')
        
        async for chunk in response:
            if not first_token_received:
                ttft_ms = int((time.time() - llm_request_start) * 1000)
                timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                logger.info(f"⏱️ [{timestamp_str}] 💬 LLM FIRST TOKEN: {ttft_ms}ms ({llm_provider} {model})")
                first_token_received = True
            
            # Extract content from chunk
            if llm_provider == "grok":
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        chunk_content = delta.content
                    else:
                        continue
                else:
                    continue
            else:
                if chunk.choices[0].delta.content:
                    chunk_content = chunk.choices[0].delta.content
                else:
                    continue
            
            full_response += chunk_content
            sentence_buffer += chunk_content
            
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
                            # Stream this sentence immediately to TTS
                            await stream_callback(sentence)
                            logger.info(f"📤 Streamed sentence: {sentence[:50]}...")
                
                # Keep the last incomplete part in buffer
                sentence_buffer = sentences[-1] if len(sentences) % 2 != 0 else ""
        
        # Send any remaining text
        if sentence_buffer.strip() and stream_callback:
            await stream_callback(sentence_buffer.strip())
            logger.info(f"📤 Streamed final fragment: {sentence_buffer[:50]}...")
        
        # ⏱️ TIMING: Total LLM response time
        llm_total_ms = int((time.time() - llm_request_start) * 1000)
        logger.info(f"⏱️ [TIMING] LLM_TOTAL: {llm_total_ms}ms for {len(full_response)} chars ({llm_provider} {model})")
        
        return full_response
    
    async def _process_node_content_streaming(self, node: dict, user_message: str, flow_nodes: list, stream_callback=None) -> str:
        """Process a node and return its content/response with streaming support"""
        node_data = node.get("data", {})
        node_type = node.get("type", "")
        
        # Get the actual script content properly
        if node_type == "conversation":
            content = node_data.get("script", "") or node_data.get("content", "")
        elif node_type == "ending":
            content = node_data.get("script", "") or node_data.get("content", "")
        else:
            content = node_data.get("content", "") or node_data.get("script", "")
        
        # Get mode from data (can be "prompt" or "script")
        # Check both "mode" and "promptType" fields
        prompt_type = node_data.get("mode")
        if prompt_type is None:
            prompt_type = node_data.get("promptType")
        
        # If still None, auto-detect based on content
        if prompt_type is None:
            # If content is very long (>500 chars) or contains instruction markers, treat as prompt
            if len(content) > 500 or any(marker in content.lower() for marker in [
                "## ", "### ", "instructions:", "goal:", "objective:", "**important**", 
                "you are", "your task", "rules:", "your role", "context:", "important:"
            ]):
                prompt_type = "prompt"
                logger.info(f"🔍 Auto-detected PROMPT mode in _process_node_content_streaming (length: {len(content)} chars)")
            else:
                prompt_type = "script"
                logger.info(f"🔍 Auto-detected SCRIPT mode in _process_node_content_streaming (length: {len(content)} chars)")
        
        logger.info(f"📋 Processing node streaming - Type: {node_type}, Mode: {prompt_type}, Content length: {len(content)} chars")
        
        # Handle different node types
        if node_type == "ending":
            self.should_end_call = True
            if stream_callback:
                # Support both string and dictionary payloads for callback
                # This ensures compatibility if middleware passes structured data
                await stream_callback(content)
                logger.info(f"📤 Streamed ending content: {content[:50]}...")
            return content
        
        if node_type == "logic_split":
            # Evaluate conditions and route to next node
            next_node_id = self._evaluate_logic_conditions(node_data)
            if next_node_id:
                next_node = self._get_node_by_id(next_node_id, flow_nodes)
                if next_node:
                    self.current_node_id = next_node_id
                    self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", next_node_id))
                    return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
            # No condition matched - return default message
            return "Let me help you with that."
        
        if node_type == "function":
            # Pause dead air monitoring during webhook execution
            # NOTE: Keep flag TRUE for entire chain including recursive calls
            was_already_executing = self.executing_webhook
            self.executing_webhook = True
            try:
                webhook_response = await self._execute_webhook(node_data, user_message)
                # Continue to next node after webhook
                if node_data.get("transitions"):
                    # CRITICAL: Pass webhook_response to transition evaluation for function nodes
                    logger.info(f"🔀 Evaluating transition for function node with webhook response...")
                    next_node = await self._follow_transition(node, user_message, flow_nodes, webhook_response=webhook_response)
                    if next_node and next_node.get("id") != node.get("id"):
                        self.current_node_id = next_node.get("id")
                        self.current_node_label = next_node.get("label", next_node.get("data", {}).get("label", next_node.get("id", "Unknown")))
                        logger.info(f"📍 Function node recursion (method): Updated current_node to {self.current_node_label}")
                        # Keep executing_webhook TRUE during recursive call
                        return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
                return webhook_response.get("message", "Function executed")
            finally:
                # Only reset flag if we were the one who set it
                if not was_already_executing:
                    self.executing_webhook = False
                    return await self._process_node_content_streaming(next_node, user_message, flow_nodes, stream_callback)
            return webhook_response.get("message", "Function executed")
        
        # Handle script vs prompt mode for conversation nodes
        if prompt_type == "script":
            logger.info("📜 Using SCRIPT mode - will speak content directly")
            if stream_callback:
                await stream_callback(content)
                logger.info(f"📤 Streamed script content: {content[:50]}...")
            return content
        else:
            # Prompt mode - use AI with streaming
            logger.info("🤖 Using PROMPT mode - will generate AI response")
            return await self._generate_ai_response_streaming(content, stream_callback)
    
    async def _process_node_content(self, node: dict, user_message: str, flow_nodes: list) -> str:
        """Process a node and return its content/response"""
        node_data = node.get("data", {})
        node_type = node.get("type", "")
        
        # Get the actual script content properly
        if node_type == "conversation":
            content = node_data.get("script", "") or node_data.get("content", "")
        elif node_type == "ending":
            content = node_data.get("script", "") or node_data.get("content", "")
        else:
            content = node_data.get("content", "") or node_data.get("script", "")
        
        # Get mode from data (can be "prompt" or "script")
        # Check both "mode" and "promptType" fields
        prompt_type = node_data.get("mode")
        if prompt_type is None:
            prompt_type = node_data.get("promptType")
        
        # If still None, auto-detect based on content markers ONLY (NOT length)
        if prompt_type is None:
            # If content contains instruction markers, treat as prompt
            if any(marker in content.lower() for marker in [
                "## ", "### ", "instructions:", "goal:", "objective:", "**important**", 
                "you are", "your task", "rules:", "your role", "context:", "important:"
            ]):
                prompt_type = "prompt"
                logger.info(f"🔍 Auto-detected PROMPT mode in _process_node_content (instruction markers found)")
            else:
                prompt_type = "script"
                logger.info(f"🔍 Auto-detected SCRIPT mode in _process_node_content (no instruction markers)")
        
        logger.info(f"📋 Processing node - Type: {node_type}, Mode: {prompt_type}, Content length: {len(content)} chars")
        
        # Handle different node types
        if node_type == "ending":
            self.should_end_call = True
            return content
        
        if node_type == "logic_split":
            # Evaluate conditions and route to next node
            next_node_id = self._evaluate_logic_conditions(node_data)
            if next_node_id:
                next_node = self._get_node_by_id(next_node_id, flow_nodes)
                if next_node:
                    self.current_node_id = next_node_id
                    return await self._process_node_content(next_node, user_message, flow_nodes)
            # No condition matched - return default message
            return "Let me help you with that."
        
        if node_type == "function":
            # Pause dead air monitoring during webhook execution
            self.executing_webhook = True
            try:
                webhook_response = await self._execute_webhook(node_data, user_message)
            finally:
                self.executing_webhook = False
            # Continue to next node after webhook
            if node_data.get("transitions"):
                # CRITICAL: Pass webhook_response to transition evaluation for function nodes
                logger.info(f"🔀 Evaluating transition for function node with webhook response...")
                next_node = await self._follow_transition(node, user_message, flow_nodes, webhook_response=webhook_response)
                if next_node and next_node.get("id") != node.get("id"):
                    return await self._process_node_content(next_node, user_message, flow_nodes)
            return webhook_response.get("message", "Function executed")
        
        # Handle script vs prompt mode for conversation nodes
        if prompt_type == "script":
            logger.info("📜 Using SCRIPT mode - will speak content directly")
            # Replace variables in script
            script = content
            logger.info(f"🔧 Script before replacement: {script[:100]}")
            logger.info(f"🔧 Session variables: {self.session_variables}")
            for var_name, var_value in self.session_variables.items():
                logger.info(f"🔧 Replacing {{{{{var_name}}}}} with {var_value}")
                script = script.replace(f"{{{{{var_name}}}}}", str(var_value))
            logger.info(f"🔧 Script after replacement: {script[:100]}")
            return script
        else:
            logger.info("💭 Using PROMPT mode - will use AI to interpret instructions")
            # Prompt mode - use AI
            # FIRST replace variables in the content/prompt itself
            prompt_with_vars = content
            logger.info(f"🔧 Prompt before replacement: {prompt_with_vars[:100]}")
            logger.info(f"🔧 Session variables: {self.session_variables}")
            for var_name, var_value in self.session_variables.items():
                logger.info(f"🔧 Replacing {{{{{var_name}}}}} with {var_value}")
                prompt_with_vars = prompt_with_vars.replace(f"{{{{{var_name}}}}}", str(var_value))
            logger.info(f"🔧 Prompt after replacement: {prompt_with_vars[:100]}")
            logger.info(f"📏 Full prompt length: {len(prompt_with_vars)} chars")
            
            # Get LLM provider from agent settings
            llm_provider = self.agent_config.get("settings", {}).get("llm_provider")
            if not llm_provider:
                logger.error("❌ No LLM provider configured for agent")
                return None
            model = self.agent_config.get("model", "gpt-4-turbo")
            
            # Validate model matches provider and fix if mismatched
            grok_models = ["grok-4-1-fast-non-reasoning", "grok-4-fast-non-reasoning", "grok-4-fast-reasoning", "grok-3", "grok-2-1212", "grok-beta", "grok-4-fast"]
            openai_models = ["gpt-4.1-2025-04-14", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
            
            if llm_provider == "grok":
                if model not in grok_models:
                    logger.warning(f"⚠️  Model '{model}' not valid for Grok, using 'grok-3'")
                    model = "grok-3"
            else:
                if model in grok_models:
                    logger.warning(f"⚠️  Model '{model}' is a Grok model but provider is OpenAI, using 'gpt-4-turbo'")
                    model = "gpt-4-turbo"
            
            logger.info(f"🤖 Using LLM provider: {llm_provider}, model: {model}")
            
            # Get appropriate client
            if llm_provider == "grok":
                client = await self.get_llm_client_for_session("grok")
            else:
                client = await self.get_llm_client_for_session("openai")
                
            if not client:
                logger.warning(f"⚠️ {llm_provider} client not available, returning raw prompt")
                return prompt_with_vars
            
            # Include session variables in system prompt
            # 🚀 HYBRID CACHING: Separate static (cached) and dynamic (per-turn) parts
            
            # GLOBAL PROMPT - Universal personality and behavior layer
            global_prompt = self.agent_config.get("system_prompt", "").strip()
            
            # Add knowledge base to global prompt if available
            if self.knowledge_base:
                global_prompt += f"\n\n=== KNOWLEDGE BASE ===\nYou have access to multiple reference sources below. Each source serves a different purpose.\n\n🧠 HOW TO USE THE KNOWLEDGE BASE:\n1. When user asks a question, FIRST identify which knowledge base source(s) are relevant based on their descriptions\n2. Read ONLY the relevant source(s) to find the answer\n3. Use ONLY information from the knowledge base - do NOT make up or improvise ANY factual details\n4. If the knowledge base doesn't contain the answer, say: \"I don't have that specific information available\"\n5. Different sources contain different types of information - match the user's question to the right source\n\n⚠️ NEVER invent: company names, product names, prices, processes, methodologies, or any factual information not in the knowledge base\n\n{self.knowledge_base}\n=== END KNOWLEDGE BASE ===\n"
            
            if global_prompt:
                # User has defined a custom global prompt - use it as the foundation
                logger.info(f"📋 Using custom global prompt ({len(global_prompt)} chars)")
                cached_system_prompt = global_prompt
            else:
                # No global prompt defined - use default conversational AI behavior
                logger.info("📋 Using default system prompt (no global prompt configured)")
                cached_system_prompt = """You are a conversational AI assistant having real conversations with users.

# COMMUNICATION STYLE  
- Generate natural, conversational responses
- Be concise but complete
- Maintain context across the conversation
- Sound like a real person, not a robot

# STRICT RULES
- RESPOND to the user, don't just analyze instructions
- NO meta-commentary about what you're doing
- Keep it natural and flowing"""
            
            # DYNAMIC PART (changes every turn) - current context, variables, specific instructions
            var_context = ""
            if self.session_variables:
                var_context = f"\n\nAvailable context variables: {json.dumps(self.session_variables)}"
            
            dynamic_context = f"""
# CURRENT TASK
Your instructions for this conversation:
{prompt_with_vars}{var_context}

IMPORTANT: Based on these instructions, generate a natural, conversational response to the user."""
            
            messages = [
                {"role": "system", "content": cached_system_prompt, "cache_control": {"type": "ephemeral"}},
                {"role": "system", "content": dynamic_context}
            ] + self.conversation_history  # Full history
            
            logger.info(f"🤖 Sending to {llm_provider} - Model: {model}")
            logger.info(f"🤖 System message length: {len(cached_system_prompt) + len(dynamic_context)} chars")
            logger.info(f"🤖 Conversation history: {len(self.conversation_history)} messages (sending last 5)")
            
            # Call LLM based on provider
            if llm_provider == "grok":
                response = await client.create_completion(
                    messages=messages,
                    model=model,
                    temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                    max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 500)
                )
            else:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self.agent_config.get("settings", {}).get("temperature", 0.7),
                    max_tokens=self.agent_config.get("settings", {}).get("max_tokens", 500)
                )
            
            ai_response = response.choices[0].message.content
            logger.info(f"✅ AI response received: {ai_response[:200]}...")
            logger.info(f"📏 AI response length: {len(ai_response)} chars")
            
            if not ai_response or ai_response.strip() == "":
                logger.error("❌ AI returned EMPTY response!")
                return "I apologize, I'm having trouble formulating a response. Could you please repeat that?"
            
            return ai_response

    async def _select_node_with_ai(self, user_message: str, flow_nodes: list) -> dict:
        """Use AI to select the best node based on transitions"""
        try:
            # Get conversation nodes with transitions
            available_nodes = [n for n in flow_nodes if n.get("type") == "conversation"]
            
            if not available_nodes:
                return None
            
            # Build options for AI to choose from
            node_options = []
            for i, node in enumerate(available_nodes):
                node_data = node.get("data", {})
                transitions = node_data.get("transitions", [])
                
                # Collect all transition conditions for this node
                conditions = []
                for trans in transitions:
                    condition = trans.get("condition", "")
                    if condition:
                        conditions.append(condition)
                
                if conditions:
                    node_options.append({
                        "index": i,
                        "label": node.get("label", "Node"),
                        "conditions": " OR ".join(conditions)
                    })
            
            if not node_options:
                # No transitions defined, return first conversation node
                return available_nodes[0]
            
            # Ask AI to select best node
            client = await self.get_llm_client_for_session("openai")
            if not client:
                return available_nodes[0]
            
            # Build selection prompt
            options_text = "\n".join([
                f"{opt['index']}: {opt['label']} - Use if: {opt['conditions']}"
                for opt in node_options
            ])
            
            recent_context = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in self.conversation_history[-3:]
            ])
            
            selection_prompt = f"""Based on the conversation context, select which node to use.

Recent conversation:
{recent_context}

Available nodes:
{options_text}

Respond with ONLY the number of the best matching node (e.g., "0" or "1" or "2").
If none match well, respond with "0"."""

            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": selection_prompt}],
                temperature=0.3,
                max_tokens=10
            )
            
            selected_index = int(response.choices[0].message.content.strip())
            logger.info(f"AI selected node index: {selected_index}")
            
            return available_nodes[selected_index] if selected_index < len(available_nodes) else available_nodes[0]
            
        except Exception as e:
            logger.error(f"Error in AI node selection: {e}")
            # Fallback to first conversation node
            for node in flow_nodes:
                if node.get("type") == "conversation":
                    return node
            return None
    
    async def synthesize_speech(self, text: str):
        """Convert text to speech using ElevenLabs - Uses settings from agent config"""
        try:
            # Get ElevenLabs settings from agent config
            elevenlabs_settings = self.agent_config.get("settings", {}).get("elevenlabs_settings", {})
            
            # Use voice_id from elevenlabs_settings, with fallback to Rachel's voice ID
            voice_id = elevenlabs_settings.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
            model = elevenlabs_settings.get("model", "eleven_turbo_v2_5")
            
            # Log which voice and model we're using
            logger.info(f"🎤 Synthesizing speech with voice_id={voice_id}, model={model}: {text[:50]}...")
            
            # NOTE: This is a legacy function. The actual TTS is handled by telnyx_service.speak_text()
            # which correctly uses all elevenlabs_settings including voice_id, model, speed, stability, etc.
            # This function is kept for compatibility but should eventually be removed.
            
            return {
                "audio": "base64_encoded_audio_data",
                "text": text
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return None
    
    async def send_audio_chunk(self, audio_data: bytes):
        """Send audio chunk to Deepgram for transcription"""
        try:
            if self.deepgram_connection and self.is_active:
                await self.deepgram_connection.send(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio chunk: {e}")
    
    async def close(self):
        """Close the call session"""
        self.is_active = False
        if self.deepgram_connection:
            await self.deepgram_connection.finish()
        logger.info(f"Call session {self.call_id} closed")


# Global storage for active call sessions
active_sessions: Dict[str, CallSession] = {}


async def create_call_session(call_id: str, agent_config: dict, agent_id: str = None, user_id: str = None, db=None) -> CallSession:
    """Create a new call session with RAG-enabled KB (smart routing + retrieval)"""
    # Extract user_id from agent_config if not provided
    if not user_id:
        user_id = agent_config.get("user_id")
    
    # Check if agent has KB items (will be retrieved dynamically via RAG when needed)
    has_kb = False
    if db is not None and agent_id:
        try:
            logger.info(f"🔍 Checking KB for agent {agent_id}...")
            import asyncio
            kb_count = await asyncio.wait_for(
                db.knowledge_base.count_documents({"agent_id": agent_id}),
                timeout=2.0  # 2 second timeout
            )
            logger.info(f"🔍 KB count query completed: {kb_count} items")
            if kb_count > 0:
                has_kb = True
                logger.info(f"📚 Agent {agent_id} has {kb_count} KB items - Smart routing enabled (RAG on demand)")
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ KB check timed out for agent {agent_id}, continuing without KB")
        except Exception as e:
            logger.error(f"❌ Error checking KB for agent {agent_id}: {e}")
    
    # Use RAG (on-demand retrieval) instead of loading full KB
    # Pass flag to indicate RAG is available
    knowledge_base = "RAG_ENABLED" if has_kb else ""
    
    session = CallSession(call_id, agent_config, agent_id=agent_id, user_id=user_id, knowledge_base=knowledge_base, db=db)
    
    # 🚀 PRE-WARM LLM CLIENT: Fetch API key and create client NOW instead of on first message
    # This saves ~100-300ms on the first turn by moving setup earlier
    try:
        llm_provider = agent_config.get("settings", {}).get("llm_provider", "openai")
        logger.info(f"🔥 Pre-warming LLM client ({llm_provider})...")
        prewarm_start = time.time()
        await session.get_llm_client_for_session(provider=llm_provider)
        prewarm_ms = int((time.time() - prewarm_start) * 1000)
        logger.info(f"✅ LLM client pre-warmed in {prewarm_ms}ms")
    except Exception as e:
        # Non-fatal - will retry on first message if needed
        logger.warning(f"⚠️ LLM pre-warm failed (will retry on first message): {e}")
    
    # STT provider initialization now handled in server.py based on agent's stt_provider setting
    # Do NOT hardcode Deepgram here - it breaks Soniox/AssemblyAI configurations
    active_sessions[call_id] = session
    return session


async def get_call_session(call_id: str) -> CallSession:
    """Get an existing call session"""
    return active_sessions.get(call_id)


async def close_call_session(call_id: str):
    """Close a call session"""
    session = active_sessions.get(call_id)
    if session:
        await session.close()
        del active_sessions[call_id]
