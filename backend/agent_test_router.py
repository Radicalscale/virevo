"""
Agent Testing Router - API endpoints for testing agents without phone calls
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import time
import uuid
from datetime import datetime, timedelta
import aiohttp
import re
import logging

from auth_middleware import get_current_user
from core_calling_service import CallSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Agent Testing"])

# In-memory cache for CallSession objects (can't be serialized to DB)
# The session metadata is stored in DB, CallSession is recreated on-demand
_session_cache: Dict[str, CallSession] = {}

# Database connection (injected from server.py)
_db = None

def set_db(database):
    global _db
    _db = database

def get_db():
    return _db

# Session expiry time (30 minutes)
SESSION_EXPIRY_MINUTES = 30

async def get_or_create_session(session_id: str, agent_doc: dict, user_id: str, start_node_id: str = None) -> tuple:
    """Get session from cache or recreate from DB metadata"""
    db = get_db()
    
    # Check cache first
    if session_id in _session_cache:
        session_data = await db.test_sessions.find_one({"session_id": session_id})
        if session_data:
            return _session_cache[session_id], session_data
    
    # Get session metadata from DB
    session_data = await db.test_sessions.find_one({"session_id": session_id})
    if not session_data:
        return None, None
    
    # Check if session expired
    created_at = session_data.get('created_at')
    if created_at:
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if datetime.utcnow() - created_at > timedelta(minutes=SESSION_EXPIRY_MINUTES):
            # Session expired, clean up
            await db.test_sessions.delete_one({"session_id": session_id})
            if session_id in _session_cache:
                del _session_cache[session_id]
            return None, None
    
    # Recreate CallSession from metadata
    test_call_id = f"test_{int(time.time())}_{session_id[:8]}"
    call_session = CallSession(
        call_id=test_call_id,
        agent_id=session_data['agent_id'],
        agent_config=agent_doc,
        db=db,
        user_id=user_id,
        knowledge_base=""
    )
    
    # Restore session state
    call_session.session_variables = session_data.get('variables', {'customer_name': 'Test User'})
    call_session.conversation_history = session_data.get('conversation_history', [])
    if start_node_id or session_data.get('start_node_id'):
        call_session.current_node_id = start_node_id or session_data.get('start_node_id')
    
    # Cache it
    _session_cache[session_id] = call_session
    
    return call_session, session_data

async def save_session_state(session_id: str, call_session: CallSession, session_data: dict):
    """Save session state to DB"""
    db = get_db()
    
    # Update session data
    update_data = {
        'variables': dict(call_session.session_variables) if hasattr(call_session, 'session_variables') else {},
        'conversation_history': call_session.conversation_history,
        'current_node_id': call_session.current_node_id,
        'updated_at': datetime.utcnow()
    }
    
    # Merge with existing session_data
    session_data.update(update_data)
    
    await db.test_sessions.update_one(
        {"session_id": session_id},
        {"$set": update_data}
    )


async def measure_real_tts_time(text: str, agent_config: dict, api_key: str) -> dict:
    """
    Measure ACTUAL TTS generation time using ElevenLabs API
    
    Returns:
        dict with {
            'tts_time': float,
            'ttfb': float (time to first byte),
            'method': 'real' or 'formula',
            'error': str (if failed)
        }
    """
    if not api_key:
        # Fall back to formula
        words = len(text.split())
        tts_time = 0.15 + (words * 0.012)
        return {
            'tts_time': tts_time,
            'ttfb': None,
            'method': 'formula',
            'error': 'No API key provided'
        }
    
    try:
        settings = agent_config.get("settings", {})
        voice_id = settings.get("elevenlabs_settings", {}).get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        model_id = settings.get("elevenlabs_settings", {}).get("model", "eleven_flash_v2_5")
        stability = settings.get("elevenlabs_settings", {}).get("stability", 0.5)
        similarity_boost = settings.get("elevenlabs_settings", {}).get("similarity_boost", 0.75)
        
        # Strip SSML tags
        clean_text = text
        if '<speak>' in text or '<break' in text:
            clean_text = re.sub(r'<[^>]+>', '', text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        tts_start = time.time()
        
        # Call ElevenLabs API
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": clean_text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        
        ttfb = None
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs API error {response.status}: {error_text}")
                
                # Measure time to first byte
                ttfb = time.time() - tts_start
                
                # Read all audio data
                audio_data = await response.read()
                
        total_time = time.time() - tts_start
        
        return {
            'tts_time': total_time,
            'ttfb': ttfb,
            'audio_size': len(audio_data),
            'method': 'real',
            'error': None
        }
        
    except Exception as e:
        # Fall back to formula on error
        words = len(text.split())
        tts_time = 0.15 + (words * 0.012)
        return {
            'tts_time': tts_time,
            'ttfb': None,
            'method': 'formula',
            'error': str(e)
        }


class TestMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    measure_real_tts: bool = False
    start_node_id: Optional[str] = None  # For testing specific transitions
    expected_next_node: Optional[str] = None  # For validation
    node_overrides: Optional[Dict[str, str]] = None  # Temporary prompt overrides {node_id: new_prompt}


class TestSessionResponse(BaseModel):
    session_id: str
    agent_id: str
    agent_name: str
    agent_type: str
    conversation: List[dict]
    current_node_id: Optional[str]
    node_transitions: List[str]
    variables: Dict
    metrics: dict
    should_end_call: bool


class StartSessionRequest(BaseModel):
    start_node_id: Optional[str] = None  # Optional starting node for transition testing


@router.post("/agents/{agent_id}/test/start")
async def start_test_session(
    agent_id: str, 
    request: StartSessionRequest = None,
    current_user: dict = Depends(get_current_user)
):
    """Start a new test session for an agent"""
    
    db = get_db()
    
    # Handle both body and no body requests
    start_node_id = request.start_node_id if request else None
    
    # Get agent configuration
    agent_doc = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent_doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create unique session ID
    session_id = str(uuid.uuid4())
    test_call_id = f"test_{int(time.time())}_{session_id[:8]}"
    
    # Initialize CallSession
    call_session = CallSession(
        call_id=test_call_id,
        agent_id=agent_id,
        agent_config=agent_doc,
        db=db,
        user_id=current_user['id'],
        knowledge_base=""
    )
    
    # Set default customer name for variable replacement
    call_session.session_variables['customer_name'] = "Test User"
    
    # If start_node_id is provided, set the current node to that node
    if start_node_id:
        call_flow = agent_doc.get('call_flow', [])
        # Find the node in call_flow
        target_node = None
        for node in call_flow:
            if node.get('id') == start_node_id:
                target_node = node
                break
        
        if target_node:
            # Set the current node in the call session
            call_session.current_node_id = start_node_id
            call_session.current_node = target_node.get('data', {})
            logger.info(f"Test session starting from node: {start_node_id}")
        else:
            logger.warning(f"Start node {start_node_id} not found in call flow")
    
    # Store session in MongoDB (persists across server restarts)
    session_data = {
        'session_id': session_id,
        'agent_id': agent_id,
        'user_id': current_user['id'],
        'agent_name': agent_doc.get('name', 'Unknown'),
        'agent_type': agent_doc.get('agent_type', 'unknown'),
        'conversation': [],
        'conversation_history': [],  # For CallSession restoration
        'node_transitions': [start_node_id] if start_node_id else [],
        'start_node_id': start_node_id,
        'current_node_id': start_node_id,
        'variables': {'customer_name': 'Test User'},
        'metrics': {
            'total_turns': 0,
            'total_latency': 0,
            'start_time': time.time()
        },
        'created_at': datetime.utcnow()
    }
    
    # Save to MongoDB
    await db.test_sessions.insert_one(session_data)
    
    # Cache the CallSession object
    _session_cache[session_id] = call_session
    
    logger.info(f"✅ Test session {session_id[:8]}... created and saved to DB")
    
    return {
        'session_id': session_id,
        'agent_id': agent_id,
        'agent_name': agent_doc.get('name'),
        'agent_type': agent_doc.get('agent_type'),
        'start_node_id': start_node_id,
        'current_node_id': start_node_id if start_node_id else None,
        'message': 'Test session started'
    }


@router.post("/agents/{agent_id}/test/message")
async def send_test_message(
    agent_id: str, 
    request: TestMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message in an active test session"""
    
    db = get_db()
    session_id = request.session_id
    
    if not session_id:
        raise HTTPException(status_code=404, detail="Test session not found. Please start a new session.")
    
    # Get agent config
    agent_doc = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent_doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get or recreate session from DB
    call_session, session_data = await get_or_create_session(
        session_id, 
        agent_doc, 
        current_user['id'],
        request.start_node_id
    )
    
    if not call_session or not session_data:
        raise HTTPException(status_code=404, detail="Test session not found. Please start a new session.")
    
    # If start_node_id is provided, override current node for transition testing
    if request.start_node_id:
        call_session.current_node_id = request.start_node_id
        logger.info(f"🎯 Testing transition from node: {request.start_node_id}")
    
    # Apply node prompt overrides if provided
    if request.node_overrides:
        for node_id, new_prompt in request.node_overrides.items():
            for node in call_session.agent_config.get('call_flow', []):
                if node.get('id') == node_id:
                    if 'data' not in node:
                        node['data'] = {}
                    # Store original prompt for reference
                    if '_original_prompt' not in node['data']:
                        node['data']['_original_prompt'] = node['data'].get('prompt', '')
                    node['data']['prompt'] = new_prompt
                    logger.info(f"📝 Applied prompt override for node: {node_id[:8]}...")
    
    # Process message
    turn_start = time.time()
    
    try:
        # Track timing for each component
        llm_start = time.time()
        
        # Process user input and get response
        result = await call_session.process_user_input(request.message)
        
        llm_time = time.time() - llm_start
        turn_latency = time.time() - turn_start
        
        # Extract response details
        if result:
            response_text = result.get('text', '')
            should_end = result.get('end_call', False)
        else:
            response_text = '(Error processing message)'
            should_end = False
        
        current_node = call_session.current_node_id
        
        # Calculate TTS time - use REAL measurement if requested
        words = len(response_text.split())
        
        if request.measure_real_tts:
            # Get ElevenLabs API key
            elevenlabs_api_key = None
            try:
                api_keys_collection = get_db()['api_keys']
                elevenlabs_key_doc = await api_keys_collection.find_one({"service_name": "elevenlabs"})
                if elevenlabs_key_doc:
                    elevenlabs_api_key = elevenlabs_key_doc.get('api_key')
            except Exception as e:
                print(f"⚠️ Could not load ElevenLabs API key: {e}")
            
            # Measure real TTS time
            tts_result = await measure_real_tts_time(
                response_text,
                call_session.agent_config,
                elevenlabs_api_key
            )
            tts_time = tts_result['tts_time']
            ttfb = tts_result['ttfb']
            tts_method = tts_result['method']
        else:
            # Use formula estimate
            tts_time = 0.15 + (words * 0.012)
            ttfb = None
            tts_method = 'formula'
        
        # Get node label
        node_label = "Unknown"
        if current_node:
            agent_flow = call_session.agent_config.get('call_flow', [])
            for node in agent_flow:
                if node.get('id') == current_node:
                    node_label = node.get('label', 'Unnamed Node')
                    break
        
        # Add to conversation log
        turn_data = {
            'turn': len(session_data['conversation']) + 1,
            'user_message': request.message,
            'agent_response': response_text,
            'node_id': current_node,
            'node_label': node_label,
            'latency': round(turn_latency, 3),
            'detailed_timing': {
                'llm_time': round(llm_time, 3),
                'tts_time': round(tts_time, 3),
                'tts_method': tts_method,
                'ttfb': round(ttfb, 3) if ttfb else None,
                'system_overhead': 0.9,
                'total_latency': round(llm_time + tts_time + 0.9, 3),
                'total_turn_time': round(turn_latency, 3)
            },
            'should_end': should_end,
            'timestamp': datetime.utcnow().isoformat()
        }
        session_data['conversation'].append(turn_data)
        
        # Track node transition
        if len(session_data['node_transitions']) == 0 or session_data['node_transitions'][-1] != current_node:
            if current_node:
                session_data['node_transitions'].append(current_node)
        
        # Update metrics
        session_data['metrics']['total_turns'] += 1
        session_data['metrics']['total_latency'] += turn_latency
        session_data['metrics']['avg_latency'] = round(
            session_data['metrics']['total_latency'] / session_data['metrics']['total_turns'], 
            3
        )
        
        # Check if transition validation was requested
        transition_test_result = None
        if request.expected_next_node:
            # Get label for start node
            start_node_label = "Unknown"
            expected_node_label = "Unknown"
            actual_node_label = node_label  # Already computed above
            
            if request.start_node_id:
                for node in call_session.agent_config.get('call_flow', []):
                    if node.get('id') == request.start_node_id:
                        start_node_label = node.get('label', node.get('data', {}).get('label', 'Unnamed'))
                    if node.get('id') == request.expected_next_node:
                        expected_node_label = node.get('label', node.get('data', {}).get('label', 'Unnamed'))
            
            transition_test_result = {
                'start_node': request.start_node_id,
                'start_label': start_node_label,
                'expected_node': request.expected_next_node,
                'expected_label': expected_node_label,
                'actual_node': current_node,
                'actual_label': actual_node_label,
                'user_message': request.message,
                'success': current_node == request.expected_next_node,
                'message': 'Transition successful!' if current_node == request.expected_next_node 
                          else f'Expected {request.expected_next_node} but went to {current_node}'
            }
            logger.info(f"🎯 Transition test: FROM {start_node_label} -> TO {actual_node_label} (expected: {expected_node_label})")
        
        # Save session state to DB
        await save_session_state(session_id, call_session, session_data)
        
        # Return response with full session state
        return {
            'session_id': session_id,
            'agent_response': response_text,
            'current_node_id': current_node,
            'current_node_label': node_label,
            'node_transitions': session_data['node_transitions'],
            'variables': dict(call_session.session_variables) if hasattr(call_session, 'session_variables') else {},
            'latency': round(turn_latency, 3),
            'detailed_timing': {
                'llm_time': round(llm_time, 3),
                'tts_time': round(tts_time, 3),
                'tts_method': tts_method,
                'ttfb': round(ttfb, 3) if ttfb else None,
                'system_overhead': 0.9,
                'total_latency': round(llm_time + tts_time + 0.9, 3),
                'total_turn_time': round(turn_latency, 3)
            },
            'should_end_call': should_end,
            'metrics': session_data['metrics'],
            'conversation': session_data['conversation'],
            'transition_test': transition_test_result  # Add validation result
        }
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        return {
            'session_id': session_id,
            'agent_response': f"Error: {str(e)}",
            'error': str(e),
            'error_trace': error_trace,
            'current_node_id': call_session.current_node_id if hasattr(call_session, 'current_node_id') else None,
            'latency': round(time.time() - turn_start, 3)
        }


@router.get("/agents/{agent_id}/test/session/{session_id}")
async def get_test_session(
    agent_id: str,
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get current state of a test session"""
    
    db = get_db()
    
    # Get agent config
    agent_doc = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent_doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get or recreate session from DB
    call_session, session_data = await get_or_create_session(
        session_id, 
        agent_doc, 
        current_user['id']
    )
    
    if not call_session or not session_data:
        raise HTTPException(status_code=404, detail="Test session not found")
    
    # Get current node label
    current_node = call_session.current_node_id
    node_label = "Unknown"
    if current_node:
        agent_flow = call_session.agent_config.get('call_flow', [])
        for node in agent_flow:
            if node.get('id') == current_node:
                node_label = node.get('label', 'Unnamed Node')
                break
    
    return {
        'session_id': session_id,
        'agent_id': session_data['agent_id'],
        'agent_name': session_data['agent_name'],
        'agent_type': session_data['agent_type'],
        'conversation': session_data['conversation'],
        'current_node_id': current_node,
        'current_node_label': node_label,
        'node_transitions': session_data['node_transitions'],
        'variables': dict(call_session.session_variables) if hasattr(call_session, 'session_variables') else {},
        'metrics': session_data['metrics'],
        'should_end_call': call_session.should_end_call if hasattr(call_session, 'should_end_call') else False
    }


@router.delete("/agents/{agent_id}/test/session/{session_id}")
async def delete_test_session(
    agent_id: str,
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete/clear a test session"""
    
    db = get_db()
    
    # Delete from DB
    await db.test_sessions.delete_one({"session_id": session_id})
    
    # Remove from cache
    if session_id in _session_cache:
        del _session_cache[session_id]
    
    return {'message': 'Test session deleted', 'session_id': session_id}


@router.post("/agents/{agent_id}/test/reset")
async def reset_test_session(
    agent_id: str,
    request: TestMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Reset an existing test session (clear conversation but keep session)"""
    
    db = get_db()
    session_id = request.session_id
    
    # Check if session exists in DB
    session_data = await db.test_sessions.find_one({"session_id": session_id}) if session_id else None
    
    if not session_id or not session_data:
        # If no session exists, create a new one
        return await start_test_session(agent_id, StartSessionRequest(), current_user)
    
    # Get agent config
    agent_doc = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent_doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Reset session in DB
    reset_data = {
        'conversation': [],
        'conversation_history': [],
        'node_transitions': [],
        'current_node_id': None,
        'variables': {'customer_name': 'Test User'},
        'metrics': {
            'total_turns': 0,
            'total_latency': 0,
            'start_time': time.time()
        },
        'updated_at': datetime.utcnow()
    }
    
    await db.test_sessions.update_one(
        {"session_id": session_id},
        {"$set": reset_data}
    )
    
    # Remove from cache (will be recreated on next request)
    if session_id in _session_cache:
        del _session_cache[session_id]
    
    return {
        'session_id': session_id,
        'message': 'Test session reset',
        'agent_id': agent_id
    }


# ============================================================================
# AI AUTO-TESTER - Simulated Caller Feature
# ============================================================================

# Store active auto-test sessions
_auto_test_sessions: Dict[str, dict] = {}

class AutoTestRequest(BaseModel):
    """Request model for starting an AI auto-test"""
    difficulty: str = "compliant"  # compliant, skeptical, hostile
    custom_instructions: Optional[str] = None
    max_turns: int = 20
    llm_provider: str = "grok"  # grok, openai
    llm_model: Optional[str] = None
    start_node_id: Optional[str] = None

class AutoTestStopRequest(BaseModel):
    """Request to stop an auto-test"""
    session_id: str

# Difficulty level prompts for the simulated caller
DIFFICULTY_PROMPTS = {
    "compliant": """You are a COMPLIANT potential customer on a phone call. You are:
- Friendly and cooperative
- Interested in what's being offered
- Willing to answer questions honestly
- Likely to agree to appointments or next steps
- You ask reasonable clarifying questions
- You respond naturally with brief, conversational answers (1-3 sentences typically)
- You occasionally say things like "okay", "sure", "sounds good", "that makes sense"
""",
    
    "skeptical": """You are a SKEPTICAL potential customer on a phone call. You are:
- Cautious and questioning
- Need convincing before agreeing to anything
- Ask tough questions about legitimacy, costs, and catches
- Hesitant to give personal information
- Concerned about scams or being sold something you don't need
- You might say things like "I'm not sure...", "What's the catch?", "How do I know this is real?"
- You eventually warm up if the agent handles your concerns well
- Respond with brief, guarded answers (1-2 sentences)
""",
    
    "hostile": """You are a HOSTILE potential customer on a phone call. You are:
- Annoyed at being called
- Distrustful and confrontational  
- Looking for reasons to hang up
- Might be rude or dismissive
- Challenge everything the agent says
- You might say things like "Why are you calling me?", "I'm busy", "This sounds like a scam", "Take me off your list"
- You're hard to convince but not impossible if the agent is skilled
- Respond with short, curt answers (1 sentence or less)
- You may threaten to hang up
"""
}

async def generate_simulated_caller_response(
    agent_message: str,
    conversation_history: List[dict],
    difficulty: str,
    custom_instructions: str,
    agent_context: str,
    llm_provider: str = "grok",
    llm_model: str = None
) -> str:
    """Generate a simulated caller response using LLM"""
    import httpx
    import os
    
    difficulty_prompt = DIFFICULTY_PROMPTS.get(difficulty, DIFFICULTY_PROMPTS["compliant"])
    
    # Build conversation context - format differently for better LLM understanding
    conv_text = ""
    for turn in conversation_history[-10:]:  # Last 10 turns for context
        role = "Agent" if turn.get('role') == 'assistant' else "You (Caller)"
        conv_text += f"{role}: {turn.get('content', '')}\n"
    
    system_prompt = f"""You are simulating a phone call as a potential customer. {difficulty_prompt}

{f"Additional instructions: {custom_instructions}" if custom_instructions else ""}

Context about what the agent is selling/offering:
{agent_context[:500] if agent_context else "The agent is making a sales or service call."}

IMPORTANT RULES:
1. Respond ONLY as the caller - do not write what the agent says
2. Keep responses SHORT and natural (like real phone conversations)
3. Do not use quotation marks around your response
4. Do not prefix your response with "Caller:" or similar
5. Respond based on your difficulty level ({difficulty})
6. If the agent asks for specific information (name, availability, etc.), provide realistic fake details
7. If you want to end the call, say something like "I need to go" or "Not interested, bye"
8. IMPORTANT: Each response must be DIFFERENT and advance the conversation naturally
9. React to what the agent actually said, don't repeat yourself
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"The agent just said: \"{agent_message}\"\n\nConversation so far:\n{conv_text}\n\nRespond as the {difficulty} caller with a NEW, UNIQUE response:"}
    ]
    
    async def try_grok_api():
        """Try Grok API"""
        api_key = os.environ.get('GROK_API_KEY') or os.environ.get('XAI_API_KEY')
        if not api_key:
            raise Exception("No Grok API key configured")
        
        model = llm_model or "grok-3-fast"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 150,
                    "temperature": 0.9  # Higher temperature for more variety
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"Grok API error: {response.status_code} - {response.text}")
                raise Exception(f"Grok API error: {response.status_code}")
    
    async def try_openai_api():
        """Try OpenAI API"""
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise Exception("No OpenAI API key configured")
        
        model = llm_model or "gpt-4o-mini"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 150,
                    "temperature": 0.9  # Higher temperature for more variety
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"OpenAI API error: {response.status_code}")
    
    try:
        if llm_provider == "grok":
            try:
                return await try_grok_api()
            except Exception as e:
                logger.warning(f"Grok API failed, trying OpenAI fallback: {e}")
                # Try OpenAI as fallback
                return await try_openai_api()
        
        elif llm_provider == "openai":
            try:
                return await try_openai_api()
            except Exception as e:
                logger.warning(f"OpenAI API failed, trying Grok fallback: {e}")
                # Try Grok as fallback
                return await try_grok_api()
        
        else:
            raise Exception(f"Unsupported LLM provider: {llm_provider}")
            
    except Exception as e:
        logger.error(f"All LLM providers failed for simulated response: {e}")
        # Use context-aware fallback based on conversation length
        turn_count = len(conversation_history)
        
        # Dynamic fallbacks that vary based on turn count and difficulty
        if difficulty == "compliant":
            fallbacks = [
                "Okay, that sounds interesting. Tell me more.",
                "Sure, I'm listening. What else should I know?",
                "That makes sense. So what's the next step?",
                "I see. And how does that work exactly?",
                "Okay, I understand. What would you recommend?",
                "Sounds good to me. Is there anything else?",
                "Got it. Can you explain a bit more?",
                "Alright, that's helpful. What do you need from me?"
            ]
        elif difficulty == "skeptical":
            fallbacks = [
                "I'm not sure about this. What's the catch?",
                "How do I know this is legitimate?",
                "That sounds too good to be true.",
                "I've heard this before. What makes you different?",
                "I need to think about it. Can you send me something in writing?",
                "What are the hidden fees?",
                "I'm still not convinced. Why should I trust you?",
                "Let me talk to my spouse first."
            ]
        else:  # hostile
            fallbacks = [
                "Look, I'm really busy right now.",
                "I'm not interested. Please stop calling.",
                "This sounds like a scam.",
                "How did you get my number?",
                "I don't have time for this.",
                "Why do you keep calling?",
                "Just take me off your list.",
                "I said I'm not interested."
            ]
        
        # Use turn count to vary the fallback
        return fallbacks[turn_count % len(fallbacks)]


@router.post("/agents/{agent_id}/auto-test/start")
async def start_auto_test(
    agent_id: str,
    request: AutoTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start an AI auto-test session where a simulated caller interacts with the agent.
    Returns immediately with session_id - use /status endpoint to get results.
    """
    import asyncio
    
    db = get_db()
    
    # Get agent config
    agent_doc = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent_doc:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create a unique session ID for this auto-test
    session_id = f"auto_{uuid.uuid4().hex[:12]}"
    
    # Get agent context for the simulated caller
    agent_context = agent_doc.get('system_prompt', '') or agent_doc.get('prompt', '')
    if not agent_context:
        # Try to extract from call flow
        call_flow = agent_doc.get('call_flow', [])
        for node in call_flow:
            if node.get('data', {}).get('prompt'):
                agent_context = node['data']['prompt'][:500]
                break
    
    # Initialize auto-test session
    _auto_test_sessions[session_id] = {
        'status': 'running',
        'agent_id': agent_id,
        'user_id': current_user['id'],
        'difficulty': request.difficulty,
        'custom_instructions': request.custom_instructions,
        'llm_provider': request.llm_provider,
        'llm_model': request.llm_model,
        'max_turns': request.max_turns,
        'current_turn': 0,
        'conversation': [],
        'node_transitions': [],
        'started_at': datetime.utcnow().isoformat(),
        'agent_context': agent_context,
        'error': None
    }
    
    # Start the auto-test in background
    asyncio.create_task(run_auto_test(
        session_id=session_id,
        agent_id=agent_id,
        agent_doc=agent_doc,
        user_id=current_user['id'],
        difficulty=request.difficulty,
        custom_instructions=request.custom_instructions,
        max_turns=request.max_turns,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        start_node_id=request.start_node_id,
        agent_context=agent_context
    ))
    
    return {
        'session_id': session_id,
        'status': 'started',
        'difficulty': request.difficulty,
        'max_turns': request.max_turns,
        'message': f'Auto-test started with {request.difficulty} difficulty'
    }


async def run_auto_test(
    session_id: str,
    agent_id: str,
    agent_doc: dict,
    user_id: str,
    difficulty: str,
    custom_instructions: str,
    max_turns: int,
    llm_provider: str,
    llm_model: str,
    start_node_id: str,
    agent_context: str
):
    """Background task that runs the auto-test conversation"""
    import asyncio
    
    db = get_db()
    
    try:
        # Create a test call session
        test_call_id = f"autotest_{int(time.time())}_{session_id[:8]}"
        call_session = CallSession(
            call_id=test_call_id,
            agent_id=agent_id,
            agent_config=agent_doc,
            db=db,
            user_id=user_id,
            knowledge_base=""
        )
        
        # Set default customer name
        call_session.session_variables['customer_name'] = "Test Caller"
        
        # Set start node if specified
        if start_node_id:
            call_session.current_node_id = start_node_id
        
        conversation_history = []
        
        logger.info(f"🤖 [AUTO-TEST {session_id}] Starting with difficulty: {difficulty}")
        
        # STEP 1: Get agent's initial greeting
        # We need to find the first conversation node and get its content
        call_flow = agent_doc.get('call_flow', [])
        
        # Find start node and check whoSpeaksFirst
        start_node = None
        first_conversation_node = None
        for node in call_flow:
            if node.get("type", "").lower() == "start":
                start_node = node
            if node.get("type") == "conversation" and not first_conversation_node:
                first_conversation_node = node
        
        # Get agent's opening message
        agent_greeting = None
        
        # Check if start node has greeting content
        if start_node:
            start_data = start_node.get("data", {})
            who_speaks_first = start_data.get("whoSpeaksFirst", "ai")
            logger.info(f"🤖 [AUTO-TEST {session_id}] Who speaks first: {who_speaks_first}")
            
            # If start node has content, use it
            if start_data.get("content"):
                agent_greeting = start_data.get("content")
                logger.info(f"🤖 [AUTO-TEST {session_id}] Got greeting from start node")
        
        # If no greeting from start node, get from first conversation node
        if not agent_greeting and first_conversation_node:
            conv_data = first_conversation_node.get("data", {})
            agent_greeting = conv_data.get("content") or conv_data.get("prompt")
            if agent_greeting:
                call_session.current_node_id = first_conversation_node.get("id")
                logger.info(f"🤖 [AUTO-TEST {session_id}] Got greeting from first conversation node: {first_conversation_node.get('id')}")
        
        # If still no greeting, try calling process_user_input with special handling
        if not agent_greeting:
            logger.info(f"🤖 [AUTO-TEST {session_id}] No static greeting found, calling process_user_input...")
            # Add an empty assistant message to history to trigger "subsequent message" flow
            # This tricks the system into navigating from start node to first conversation node
            initial_result = await call_session.process_user_input("Hello, I'm calling about your service.")
            
            if initial_result and initial_result.get('text'):
                agent_greeting = initial_result['text']
                logger.info(f"🤖 [AUTO-TEST {session_id}] Got greeting from process_user_input: {agent_greeting[:50]}...")
        
        if agent_greeting:
            # Clean up the greeting (remove any instruction markers)
            if "---" in agent_greeting:
                agent_greeting = agent_greeting.split("---")[0].strip()
            if "[[" in agent_greeting:
                agent_greeting = agent_greeting.split("[[")[0].strip()
            
            conversation_history.append({
                'role': 'assistant', 
                'content': agent_greeting,
                'node_id': call_session.current_node_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            _auto_test_sessions[session_id]['conversation'] = conversation_history
            _auto_test_sessions[session_id]['current_turn'] = 1
            
            if call_session.current_node_id:
                _auto_test_sessions[session_id]['node_transitions'].append({
                    'turn': 0,
                    'node_id': call_session.current_node_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            logger.info(f"🤖 [AUTO-TEST {session_id}] Agent greeting: {agent_greeting[:100]}...")
        else:
            logger.error(f"❌ [AUTO-TEST {session_id}] Could not get agent greeting!")
            _auto_test_sessions[session_id]['status'] = 'error'
            _auto_test_sessions[session_id]['error'] = 'Could not get agent greeting. Check that the agent has content in its conversation nodes.'
            return
        
        # STEP 2: Main conversation loop - simulated caller responds to agent
        for turn in range(1, max_turns + 1):
            # Check if session was stopped
            if session_id not in _auto_test_sessions:
                logger.info(f"🛑 [AUTO-TEST {session_id}] Session stopped externally")
                return
            
            if _auto_test_sessions[session_id]['status'] == 'stopped':
                logger.info(f"🛑 [AUTO-TEST {session_id}] Session stop requested")
                break
            
            # Get the last agent message
            last_agent_msg = ""
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant':
                    last_agent_msg = msg['content']
                    break
            
            if not last_agent_msg:
                logger.warning(f"⚠️ [AUTO-TEST {session_id}] No agent message to respond to")
                break
            
            # Generate simulated caller response
            logger.info(f"🎭 [AUTO-TEST {session_id}] Turn {turn}: Generating {difficulty} caller response...")
            
            caller_response = await generate_simulated_caller_response(
                agent_message=last_agent_msg,
                conversation_history=conversation_history,
                difficulty=difficulty,
                custom_instructions=custom_instructions,
                agent_context=agent_context,
                llm_provider=llm_provider,
                llm_model=llm_model
            )
            
            logger.info(f"👤 [AUTO-TEST {session_id}] Caller: {caller_response[:100]}...")
            
            conversation_history.append({
                'role': 'user',
                'content': caller_response,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Update session immediately so UI can show progress
            _auto_test_sessions[session_id]['conversation'] = conversation_history.copy()
            _auto_test_sessions[session_id]['current_turn'] = turn
            
            # Check for call-ending phrases from caller
            end_phrases = ["bye", "goodbye", "hang up", "not interested", "take me off", "stop calling", "i need to go", "gotta go"]
            if any(phrase in caller_response.lower() for phrase in end_phrases):
                logger.info(f"📞 [AUTO-TEST {session_id}] Caller ended the conversation")
                _auto_test_sessions[session_id]['status'] = 'completed'
                _auto_test_sessions[session_id]['end_reason'] = 'caller_ended'
                break
            
            # Get agent response
            agent_result = await call_session.process_user_input(caller_response)
            
            if agent_result and agent_result.get('text'):
                agent_response = agent_result['text']
                
                # Clean up agent response
                if "---" in agent_response:
                    agent_response = agent_response.split("---")[0].strip()
                if "[[" in agent_response:
                    agent_response = agent_response.split("[[")[0].strip()
                
                conversation_history.append({
                    'role': 'assistant',
                    'content': agent_response,
                    'node_id': call_session.current_node_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"🤖 [AUTO-TEST {session_id}] Agent: {agent_response[:100]}...")
                
                # Track node transition
                if call_session.current_node_id:
                    last_node = _auto_test_sessions[session_id]['node_transitions'][-1]['node_id'] if _auto_test_sessions[session_id]['node_transitions'] else None
                    if call_session.current_node_id != last_node:
                        _auto_test_sessions[session_id]['node_transitions'].append({
                            'turn': turn,
                            'node_id': call_session.current_node_id,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                
                # Check if agent wants to end call
                if agent_result.get('end_call'):
                    logger.info(f"📞 [AUTO-TEST {session_id}] Agent ended the conversation")
                    _auto_test_sessions[session_id]['status'] = 'completed'
                    _auto_test_sessions[session_id]['end_reason'] = 'agent_ended'
                    _auto_test_sessions[session_id]['conversation'] = conversation_history
                    break
            else:
                logger.warning(f"⚠️ [AUTO-TEST {session_id}] No agent response received")
                # Still continue - might be a transition issue
                continue
            
            # Update session state
            _auto_test_sessions[session_id]['conversation'] = conversation_history.copy()
            _auto_test_sessions[session_id]['current_turn'] = turn
            
            # Small delay between turns to avoid rate limiting
            await asyncio.sleep(0.5)
        
        # Mark as completed if we reached max turns
        if _auto_test_sessions[session_id]['status'] == 'running':
            _auto_test_sessions[session_id]['status'] = 'completed'
            _auto_test_sessions[session_id]['end_reason'] = 'max_turns_reached'
        
        _auto_test_sessions[session_id]['completed_at'] = datetime.utcnow().isoformat()
        _auto_test_sessions[session_id]['conversation'] = conversation_history
        
        logger.info(f"✅ [AUTO-TEST {session_id}] Completed with {len(conversation_history)} messages")
        
    except Exception as e:
        import traceback
        logger.error(f"❌ [AUTO-TEST {session_id}] Error: {e}")
        logger.error(traceback.format_exc())
        if session_id in _auto_test_sessions:
            _auto_test_sessions[session_id]['status'] = 'error'
            _auto_test_sessions[session_id]['error'] = str(e)


@router.get("/agents/{agent_id}/auto-test/status/{session_id}")
async def get_auto_test_status(
    agent_id: str,
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the current status and conversation of an auto-test session"""
    
    if session_id not in _auto_test_sessions:
        raise HTTPException(status_code=404, detail="Auto-test session not found")
    
    session = _auto_test_sessions[session_id]
    
    # Verify ownership
    if session['user_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to view this session")
    
    return {
        'session_id': session_id,
        'status': session['status'],
        'difficulty': session['difficulty'],
        'current_turn': session.get('current_turn', 0),
        'max_turns': session['max_turns'],
        'conversation': session.get('conversation', []),
        'node_transitions': session.get('node_transitions', []),
        'started_at': session.get('started_at'),
        'completed_at': session.get('completed_at'),
        'end_reason': session.get('end_reason'),
        'error': session.get('error')
    }


@router.post("/agents/{agent_id}/auto-test/stop")
async def stop_auto_test(
    agent_id: str,
    request: AutoTestStopRequest,
    current_user: dict = Depends(get_current_user)
):
    """Stop a running auto-test session"""
    
    session_id = request.session_id
    
    if session_id not in _auto_test_sessions:
        raise HTTPException(status_code=404, detail="Auto-test session not found")
    
    session = _auto_test_sessions[session_id]
    
    # Verify ownership
    if session['user_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to stop this session")
    
    if session['status'] == 'running':
        _auto_test_sessions[session_id]['status'] = 'stopped'
        _auto_test_sessions[session_id]['end_reason'] = 'user_stopped'
        _auto_test_sessions[session_id]['completed_at'] = datetime.utcnow().isoformat()
    
    return {
        'session_id': session_id,
        'status': 'stopped',
        'message': 'Auto-test stopped',
        'conversation': session.get('conversation', [])
    }


@router.delete("/agents/{agent_id}/auto-test/{session_id}")
async def delete_auto_test_session(
    agent_id: str,
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an auto-test session from memory"""
    
    if session_id not in _auto_test_sessions:
        raise HTTPException(status_code=404, detail="Auto-test session not found")
    
    session = _auto_test_sessions[session_id]
    
    # Verify ownership
    if session['user_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to delete this session")
    
    del _auto_test_sessions[session_id]
    
    return {
        'message': 'Auto-test session deleted',
        'session_id': session_id
    }

