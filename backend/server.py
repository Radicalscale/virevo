from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Header
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
# Manual Rebuild Trigger: 2025-12-28-FIX-ATTEMPT-7
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import httpx
import json
import asyncio
import base64
import websockets
import time
import uuid
# Global state for tracking active calls and their interruption windows
call_states = {}

# Import models
from models import (
    Agent, AgentCreate, Call, CallCreate, PhoneNumber, 
    PhoneNumberCreate, FlowNode, DailyRoomCreate, DailyRoomResponse,
    KnowledgeBaseItem, KnowledgeBaseItemCreate
)

# Import Telnyx models and service
from telnyx_models import (
    PhoneNumberModel, CallLogModel, OutboundCallRequest, WebhookTriggerCallRequest,
    CallDirection, CallStatus, CallEndReason, Sentiment
)
from telnyx_service import TelnyxService
from realtime_voice_agent import RealtimeVoiceAgent
from melo_tts_service import MeloTTSService
from dia_tts_service import DiaTTSService

# Import calling service
from core_calling_service import create_call_session, get_call_session, close_call_session, CallSession
from persistent_tts_service import persistent_tts_manager

# Import Deepgram config
from deepgram_config import DEEPGRAM_CONFIG

# Import Redis service for multi-worker state sharing
from redis_service import redis_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Helper function to get user-specific API keys from database
async def get_user_api_key(user_id: str, service_name: str) -> Optional[str]:
    """
    Get user-specific API key for a service from database
    NO FALLBACK to platform keys - users must provide their own keys
    
    Args:
        user_id: User ID who owns the key
        service_name: Service name (openai, deepgram, elevenlabs, etc.)
        
    Returns:
        Decrypted API key or None if not found
    """
    from key_encryption import decrypt_api_key
    
    try:
        key_doc = await db.api_keys.find_one({
            "user_id": user_id,
            "service_name": service_name,
            "is_active": True
        })
        
        if key_doc and key_doc.get("api_key"):
            encrypted_key = key_doc.get("api_key")
            # Decrypt the key before returning
            decrypted_key = decrypt_api_key(encrypted_key)
            logger.debug(f"🔑 Retrieved {service_name} key for user {user_id[:8]}...")
            return decrypted_key
        else:
            logger.warning(f"⚠️  No {service_name} API key found for user {user_id[:8]}...")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error fetching API key for {service_name} (user: {user_id[:8]}...): {e}")
        return None

# API Keys (fallback to env vars)
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

TELNYX_API_KEY = os.environ.get('TELNYX_API_KEY')

ELEVEN_API_KEY = os.environ.get('ELEVEN_API_KEY')
DAILY_API_KEY = os.environ.get('DAILY_API_KEY')
SIGNUP_SECRET = os.environ.get('SIGNUP_SECRET')

# Create the main app
app = FastAPI(title="Retell AI Clone API")

# Mount static files directory for serving generated TTS audio
app.mount("/api/tts-audio", StaticFiles(directory="/tmp"), name="tts-audio")

# Pre-generate comfort noise on startup for immediate availability
@app.on_event("startup")
async def startup_event():
    """Pre-generate comfort noise files on server startup (both MP3 and mulaw)"""
    try:
        from comfort_noise import generate_continuous_comfort_noise, get_comfort_noise_mulaw
        import os
        
        # 1. Pre-generate MP3 comfort noise for REST API playback
        comfort_noise_path = "/tmp/comfort_noise_continuous.mp3"
        if not os.path.exists(comfort_noise_path) or os.path.getsize(comfort_noise_path) == 0:
            logger.info("🎵 Pre-generating comfort noise file on startup (5 minutes for seamless loops)...")
            # Generate 5-minute file so it rarely loops during typical calls
            generate_continuous_comfort_noise(duration_seconds=300, output_path=comfort_noise_path)
            logger.info("✅ Comfort noise MP3 ready for immediate use")
        else:
            logger.info("✅ Comfort noise MP3 already exists")
        
        # 2. Pre-generate mulaw comfort noise for WebSocket streaming
        # This prevents ~800ms blocking delay on first TTS response
        logger.info("🎵 Pre-warming mulaw comfort noise for WebSocket streaming...")
        mulaw_noise = get_comfort_noise_mulaw()
        if mulaw_noise:
            logger.info(f"✅ Mulaw comfort noise ready ({len(mulaw_noise)} bytes)")
        else:
            logger.warning("⚠️ Failed to pre-warm mulaw comfort noise")
            
    except Exception as e:
        logger.error(f"Error pre-generating comfort noise: {e}")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Import auth modules
from auth_models import (
    UserCreate, UserLogin, User, UserResponse, 
    PasswordResetRequest, PasswordReset, PasswordResetToken, TokenResponse
)
from auth_utils import hash_password, verify_password, create_access_token, generate_reset_token
from auth_middleware import get_current_user, get_optional_user
from fastapi import Depends, Response, Request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pre-load RAG service at startup to avoid cold start delays (optional for deployment)
RAG_ENABLED = os.environ.get('ENABLE_RAG', 'false').lower() == 'true'
if RAG_ENABLED:
    logger.info("🚀 Pre-loading RAG service and KB router to avoid cold start...")
    try:
        import rag_service
        import kb_router
        logger.info("✅ RAG service pre-loaded successfully (embedding model loaded)")
    except Exception as e:
        logger.error(f"⚠️  Failed to pre-load RAG service: {e}")
        logger.warning("⚠️  RAG service disabled - Knowledge Base will use full content instead of semantic search")
        RAG_ENABLED = False
else:
    logger.info("ℹ️  RAG service disabled (set ENABLE_RAG=true to enable semantic search)")

# Pre-warm critical imports and connection libraries to reduce call startup latency
logger.info("🔥 Pre-warming connection libraries...")
try:
    import websockets
    import httpx
    from elevenlabs_ws_service import ElevenLabsWebSocketService
    from soniox_service import SonioxStreamingService
    # Pre-create httpx client pool for LLM calls (will be reused)
    _warmup_client = httpx.AsyncClient(timeout=30.0)
    logger.info("✅ Connection libraries pre-warmed (websockets, httpx, ElevenLabs, Soniox)")
except Exception as e:
    logger.warning(f"⚠️ Pre-warming failed: {e}")

# ============ AUTHENTICATION ENDPOINTS ============

@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate, response: Response, request: Request):
    """Create a new user account"""
    # Check if SIGNUP_SECRET is enforced
    if SIGNUP_SECRET:
        secret_header = request.headers.get("x-signup-secret")
        # Allow if secret matches, or if coming from internal valid source (optional, but strict for now)
        if secret_header != SIGNUP_SECRET:
            logger.warning(f"⚠️ Unauthorized signup attempt: Invalid secret")
            raise HTTPException(status_code=403, detail="Unauthorized: Invalid signup secret")

    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    await db.users.insert_one(user.dict())
    logger.info(f"Created user: {user.email}")
    
    # Create JWT token
    token = create_access_token(user.id, user.email, user_data.remember_me)
    
    # Set httpOnly cookie
    max_age = 30 * 24 * 60 * 60 if user_data.remember_me else 30 * 60  # 30 days or 30 minutes
    
    # Dynamically determine cookie domain based on request origin
    # For virevo.ai production, set domain to share across subdomains
    # For preview/dev environments, don't set domain (allow browser to handle it)
    origin = request.headers.get("origin", "") if hasattr(request, 'headers') else ""
    referer = request.headers.get("referer", "") if hasattr(request, 'headers') else ""
    
    # Check if request is from virevo.ai domain
    is_virevo_domain = "virevo.ai" in origin or "virevo.ai" in referer
    cookie_domain = ".virevo.ai" if is_virevo_domain else None
    
    cookie_kwargs = {
        "key": "access_token",
        "value": token,
        "httponly": True,
        "secure": True,  # Always secure for HTTPS
        "samesite": "none",  # Allow cross-domain cookies
        "max_age": max_age,
    }
    
    # Only set domain for virevo.ai production
    if cookie_domain:
        cookie_kwargs["domain"] = cookie_domain
    
    response.set_cookie(**cookie_kwargs)
    
    return TokenResponse(
        message="User created successfully",
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
            last_login=None
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, response: Response, request: Request):
    """Login with email and password"""
    # Find user
    user_data = await db.users.find_one({"email": credentials.email})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user = User(**user_data)
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    # Update last login
    await db.users.update_one(
        {"id": user.id},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create JWT token
    token = create_access_token(user.id, user.email, credentials.remember_me)
    
    # Set httpOnly cookie
    max_age = 30 * 24 * 60 * 60 if credentials.remember_me else 30 * 60  # 30 days or 30 minutes
    
    # Dynamically determine cookie domain based on request origin
    # For virevo.ai production, set domain to share across subdomains
    # For preview/dev environments, don't set domain (allow browser to handle it)
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    
    # Check if request is from virevo.ai domain
    is_virevo_domain = "virevo.ai" in origin or "virevo.ai" in referer
    cookie_domain = ".virevo.ai" if is_virevo_domain else None
    
    cookie_kwargs = {
        "key": "access_token",
        "value": token,
        "httponly": True,
        "secure": True,  # Always secure for HTTPS
        "samesite": "none",  # Allow cross-domain cookies
        "max_age": max_age,
    }
    
    # Only set domain for virevo.ai production
    if cookie_domain:
        cookie_kwargs["domain"] = cookie_domain
    
    response.set_cookie(**cookie_kwargs)
    
    return TokenResponse(
        message="Login successful",
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
            last_login=datetime.utcnow()
        )
    )

@api_router.post("/auth/logout")
async def logout(response: Response, current_user: dict = Depends(get_current_user)):
    """Logout user"""
    response.delete_cookie(key="access_token")
    return {"message": "Logout successful"}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    user_data = await db.users.find_one({"id": current_user["id"]})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = User(**user_data)
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        last_login=user.last_login
    )

@api_router.post("/auth/forgot-password")
async def forgot_password(request_data: PasswordResetRequest):
    """Request password reset"""
    # Find user
    user_data = await db.users.find_one({"email": request_data.email})
    if not user_data:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a password reset link will be sent"}
    
    user = User(**user_data)
    
    # Generate reset token
    token = generate_reset_token()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    
    # Save reset token
    await db.password_reset_tokens.insert_one(reset_token.dict())
    
    # In production, send email with reset link
    # For now, just log it
    logger.info(f"Password reset token for {user.email}: {token}")
    logger.info(f"Reset link: /reset-password?token={token}")
    
    return {"message": "If the email exists, a password reset link will be sent"}

@api_router.post("/auth/reset-password")
async def reset_password(reset_data: PasswordReset):
    """Reset password with token"""
    # Find reset token
    token_data = await db.password_reset_tokens.find_one({
        "token": reset_data.token,
        "used": False
    })
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    reset_token = PasswordResetToken(**token_data)
    
    # Check if token is expired
    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Update user password
    new_password_hash = hash_password(reset_data.new_password)
    await db.users.update_one(
        {"id": reset_token.user_id},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    # Mark token as used
    await db.password_reset_tokens.update_one(
        {"id": reset_token.id},
        {"$set": {"used": True}}
    )
    
    logger.info(f"Password reset successful for user: {reset_token.user_id}")
    
    return {"message": "Password reset successful"}

# ============ AGENT ENDPOINTS ============

@api_router.post("/agents", response_model=Agent)
async def create_agent(agent_data: AgentCreate, current_user: dict = Depends(get_current_user)):
    """Create a new AI agent"""
    agent_dict = agent_data.dict()
    agent_dict['user_id'] = current_user['id']
    agent = Agent(**agent_dict)
    await db.agents.insert_one(agent.dict())
    logger.info(f"Created agent: {agent.id} for user: {current_user['email']}")
    return agent

@api_router.get("/agents", response_model=List[Agent])
async def list_agents(current_user: dict = Depends(get_current_user)):
    """List all agents for current user"""
    agents = await db.agents.find({"user_id": current_user['id']}).to_list(1000)
    return [Agent(**agent) for agent in agents]

@api_router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    """Get agent by ID"""
    agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Agent(**agent)

@api_router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_data: dict, current_user: dict = Depends(get_current_user)):
    """Update agent"""
    agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_data["updated_at"] = datetime.utcnow()
    # Prevent user_id modification
    agent_data.pop('user_id', None)
    await db.agents.update_one({"id": agent_id, "user_id": current_user['id']}, {"$set": agent_data})
    
    updated_agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    return Agent(**updated_agent)

@api_router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    """Delete agent"""
    result = await db.agents.delete_one({"id": agent_id, "user_id": current_user['id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}

@api_router.post("/agents/{agent_id}/duplicate", response_model=Agent)
async def duplicate_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    """Duplicate an existing agent with all settings and flow"""
    # Get the original agent
    original_agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not original_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create a copy of the agent data
    agent_copy = original_agent.copy()
    
    # Remove MongoDB _id field to avoid duplicate key error
    agent_copy.pop('_id', None)
    
    # Generate new ID and modify name
    agent_copy['id'] = str(uuid.uuid4())
    agent_copy['name'] = f"{original_agent['name']}-copy"
    
    # Reset stats to defaults
    agent_copy['stats'] = {
        'calls_handled': 0,
        'avg_latency': 0.0,
        'success_rate': 0.0
    }
    
    # Update timestamps
    agent_copy['created_at'] = datetime.utcnow()
    agent_copy['updated_at'] = datetime.utcnow()
    
    # Insert the duplicated agent
    await db.agents.insert_one(agent_copy)
    
    logger.info(f"Duplicated agent: {agent_id} -> {agent_copy['id']} for user: {current_user['email']}")
    
    return Agent(**agent_copy)

@api_router.post("/agents/{agent_id}/optimize-node")
async def optimize_node_prompt(
    agent_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Optimize node prompt using Grok 4 with comprehensive voice agent best practices.
    
    Optionally uses:
    - Agent's Knowledge Base for domain-specific context
    - Uploaded file context (PDF/audio transcription) for reference material
    """
    try:
        # Verify agent ownership
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get user's Grok API key
        grok_api_key = await get_user_api_key(current_user['id'], 'grok')
        if not grok_api_key:
            raise HTTPException(
                status_code=400,
                detail="Grok API key not found. Please add your Grok API key in Settings > API Keys"
            )
        
        original_content = request.get('content', '')
        custom_guidelines = request.get('guidelines', '')
        model = request.get('model', 'grok-4-0709')
        file_context = request.get('file_context', None)  # Extracted text from uploaded file
        use_kb = request.get('use_kb', True)  # Whether to include KB context
        
        # Build context sections
        context_sections = []
        context_used_parts = []
        
        # Fetch KB content if enabled
        if use_kb:
            try:
                kb_items = await db.knowledge_base.find({"agent_id": agent_id}).to_list(length=20)
                if kb_items:
                    kb_text = "\n\n".join([
                        f"**{item.get('source_name', 'Document')}:**\n{item.get('content', '')[:2000]}"
                        for item in kb_items
                    ])
                    context_sections.append(f"""
=== AGENT'S KNOWLEDGE BASE (Use this to understand the domain/product/service) ===
{kb_text[:8000]}
=== END KNOWLEDGE BASE ===""")
                    context_used_parts.append(f"{len(kb_items)} KB items")
                    logger.info(f"📚 Including {len(kb_items)} KB items as optimizer context")
            except Exception as e:
                logger.warning(f"Could not fetch KB for optimization: {e}")
        
        # Include uploaded file context if provided
        if file_context:
            context_sections.append(f"""
=== UPLOADED REFERENCE MATERIAL (Use these techniques/examples to improve the node) ===
{file_context[:10000]}
=== END REFERENCE MATERIAL ===""")
            context_used_parts.append("uploaded file")
            logger.info(f"📄 Including uploaded file context ({len(file_context)} chars)")
        
        # Build context block for the optimizer
        context_block = ""
        if context_sections:
            context_block = f"""

**CONTEXT FOR OPTIMIZATION:**
The following context should inform your optimization decisions. Use this information to:
- Apply domain-specific terminology correctly
- Include relevant techniques or approaches from the reference material
- Ensure the optimized prompt aligns with the product/service being discussed
- Incorporate proven tactics or scripts from the examples

{"".join(context_sections)}

**HOW TO USE THIS CONTEXT:**
- Extract relevant objection handling techniques, value propositions, or talking points
- Adapt the node's language to match the brand voice and terminology
- Include specific details or facts from the KB when applicable
- Do NOT just paste the context - intelligently weave relevant parts into the optimized prompt
"""
        
        # Build custom guidelines section if provided
        custom_section = ""
        if custom_guidelines:
            custom_section = f"\n**ADDITIONAL CUSTOM GUIDELINES:**\n{custom_guidelines}\n"
        
        # Build comprehensive optimization prompt
        optimization_prompt = f"""You are an expert at optimizing voice agent conversation node prompts for real-time non-reasoning LLM agents. Your task is to clean up and restructure the provided prompt to optimize for speed, clarity, and hallucination prevention.
{context_block}
**CORE OPTIMIZATION PRINCIPLES:**

**1. Modular Node Structure**
- Design as a focused, self-contained node with clear entry/exit points
- Break complex logic into numbered steps, not nested paragraphs
- Use headings (##) for major sections: Primary Goal, Entry Context, Strategic Toolkit, Core Logic, etc.

**2. Hallucination Prevention**
- Confine agent to retrieval from KB and predefined tactics only
- Include explicit "NEVER GUESS" or "NEVER MAKE UP INFORMATION" rules
- Use declarative, not generative instructions
- Add catch-all tactics for transcription errors or unclear input
- Set low temperature (0.1-0.3) mentally for deterministic outputs

**3. Speed Optimization**
- Reduce verbosity by 40-50% while preserving all logic
- Use bullet points, not prose
- Eliminate redundant explanations
- Make instructions scannable with clear action verbs
- Condense nested IF-THEN statements into flat numbered steps

**4. State Management**
- Explicitly define any state variables needed (e.g., `has_discussed_income_potential`)
- Show clear "set" and "check" points for states
- Use states to guide transitions without re-explaining context

**5. Voice-Specific Rules**
- **CRITICAL:** NO DASHES FOR PAUSES/CONJUNCTIONS. When generating ANY text for speech, NEVER use em-dashes (—) or en-dashes (–). Instead, use periods (`.`) for full stops between distinct ideas, or commas (`,`) with simple conjunctions (e.g., "and," "so," "but") for phrasal breaks.
- Normalize for TTS: "john@example.com" → "john at example dot com"
- Keep sentences short and conversational

**6. Adaptive Logic (If Applicable)**
- If the node handles dynamic interruptions, structure as a clear loop with max iterations (e.g., 2 loops, then escalate)
- For DISC or persona adaptation: Quick KB search, not elaborate analysis
- Show recovery paths explicitly

**7. Strategic Toolkit**
- List predefined tactics for common scenarios (price questions, KB failures, catch-all errors)
- Format as: "**Tactic for: [SCENARIO]** → Agent says: [exact response text]"
- Keep responses concise and on-brand

**8. Escalation Mandate**
- Always include a rule for when to escalate (e.g., after 2 failed loops, or if goal unmet)
- Make it explicit: "If X, then escalate to [Global Prompt / Human / Supervisor Node]"
{custom_section}
**ORIGINAL PROMPT TO CLEAN UP:**
```
{original_content}
```

**YOUR TASK:**
1. Analyze the original prompt's intent, goals, and logic flow
2. If context was provided above, extract relevant techniques, terminology, and approaches to incorporate
3. Restructure into the optimized format described above
4. Reduce verbosity while preserving ALL essential logic, rules, and goals
5. Ensure NO DASHES are used in any speech text (use periods/commas with conjunctions only)
6. Output ONLY the cleaned prompt, ready to paste directly into a voice agent node
7. Do NOT include explanations, context, or comparison tables—just the optimized prompt itself

**OUTPUT FORMAT:**
Return the cleaned prompt using clear markdown headings (##) and bullet points. Make it modular, scannable, and production-ready for a Grok-based voice agent."""

        # Call Grok API with optimized settings
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {grok_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an elite voice agent prompt engineer. You optimize prompts for real-time non-reasoning LLMs by reducing verbosity, preventing hallucinations, and structuring for speed. You intelligently incorporate provided context (KB, reference materials) to enhance prompts with domain-specific knowledge. You output clean, production-ready prompts with zero fluff."
                        },
                        {"role": "user", "content": optimization_prompt}
                    ],
                    "temperature": 0.2,  # Lower temp for more deterministic optimization
                    "max_tokens": 4000   # Allow longer outputs for complex prompts
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Grok API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"Grok API error: {response.text}")
            
            result = response.json()
            optimized_content = result['choices'][0]['message']['content']
            
            # Log token usage for monitoring
            usage = result.get('usage', {})
            logger.info(f"Prompt optimization complete. Tokens: {usage.get('total_tokens', 'unknown')}, Context: {context_used_parts}")
            
            return {
                "original": original_content,
                "optimized": optimized_content,
                "model": model,
                "tokens_used": usage.get('total_tokens', 0),
                "context_used": ", ".join(context_used_parts) if context_used_parts else None
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing node: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error optimizing node: {str(e)}")


@api_router.post("/agents/{agent_id}/extract-context")
async def extract_context_from_file(
    agent_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Extract text from uploaded PDF or transcribe audio file for optimizer context.
    
    Supports:
    - PDF: Extracts text content
    - Audio (MP3, WAV, M4A, WebM): Transcribes using Grok/Whisper
    """
    from fastapi import UploadFile, File
    import tempfile
    
    try:
        # Verify agent ownership
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        filename = file.filename.lower()
        content = await file.read()
        
        # Check file size (max 25MB)
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 25MB.")
        
        extracted_text = ""
        
        if filename.endswith('.pdf'):
            # Extract text from PDF
            try:
                import fitz  # PyMuPDF
                
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                doc = fitz.open(tmp_path)
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()
                
                # Clean up temp file
                import os
                os.unlink(tmp_path)
                
                extracted_text = "\n\n".join(text_parts)
                logger.info(f"📄 Extracted {len(extracted_text)} chars from PDF: {filename}")
                
            except ImportError:
                raise HTTPException(
                    status_code=500, 
                    detail="PDF extraction not available. PyMuPDF not installed."
                )
            except Exception as e:
                logger.error(f"PDF extraction error: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to extract PDF text: {str(e)}")
                
        elif any(filename.endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.webm', '.ogg']):
            # Transcribe audio using OpenAI Whisper API
            try:
                openai_key = await get_user_api_key(current_user['id'], 'openai')
                if not openai_key:
                    raise HTTPException(
                        status_code=400,
                        detail="OpenAI API key required for audio transcription. Add it in Settings > API Keys."
                    )
                
                # Save to temp file for API upload
                suffix = '.' + filename.split('.')[-1]
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                # Call OpenAI Whisper API
                async with httpx.AsyncClient(timeout=120.0) as client:
                    with open(tmp_path, 'rb') as audio_file:
                        response = await client.post(
                            "https://api.openai.com/v1/audio/transcriptions",
                            headers={"Authorization": f"Bearer {openai_key}"},
                            files={"file": (filename, audio_file)},
                            data={"model": "whisper-1"}
                        )
                
                # Clean up temp file
                import os
                os.unlink(tmp_path)
                
                if response.status_code != 200:
                    logger.error(f"Whisper API error: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=500, detail="Failed to transcribe audio")
                
                result = response.json()
                extracted_text = result.get('text', '')
                logger.info(f"🎤 Transcribed {len(extracted_text)} chars from audio: {filename}")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Audio transcription error: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {str(e)}")
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload a PDF or audio file (MP3, WAV, M4A, WebM)."
            )
        
        return {
            "filename": file.filename,
            "extracted_text": extracted_text[:50000],  # Limit to 50K chars
            "char_count": len(extracted_text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting context: {str(e)}")


@api_router.post("/agents/{agent_id}/optimize-transition")
async def optimize_transition_condition(
    agent_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Optimize transition condition for faster LLM evaluation"""
    try:
        # Verify agent ownership
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get user's Grok API key
        grok_api_key = await get_user_api_key(current_user['id'], 'grok')
        if not grok_api_key:
            raise HTTPException(
                status_code=400,
                detail="Grok API key not found. Please add your Grok API key in Settings > API Keys"
            )
        
        original_condition = request.get('condition', '')
        model = request.get('model', 'grok-4-0709')  # Default to Grok 4
        
        # Build transition optimization prompt
        optimization_prompt = f"""You are an expert at optimizing transition conditions for real-time voice agents. Your goal is to make transition evaluation FAST while preserving all logic.

**TRANSITION OPTIMIZATION PRINCIPLES:**

**1. Speed is Critical**
- Transition conditions are evaluated on EVERY user message during real-time conversations
- Verbose conditions add 100-300ms latency per evaluation
- Reduce to bare essentials while keeping all logic intact

**2. Structure for Fast Parsing**
- Use SHORT declarative statements, not full sentences
- Lead with the MAIN condition, then qualifiers
- Use pipes (|) for OR conditions: "agrees | consents | positive response"
- Use parentheses for examples: "(yes/sure/okay)"
- Use colons for conditional logic: "IF objection: address first, THEN transition"

**3. Keep All Logic Intact**
- Do NOT remove any conditions or rules
- Preserve all examples and edge cases
- Maintain the decision tree structure
- Keep all "if-then" logic

**4. Formatting for Speed**
- Start with trigger condition in CAPS if critical
- Group similar conditions with pipes, NO SPACES: "agrees | consents" → "agrees|consents"
- Use minimal words: "User agrees" → "Agrees", "question" → "Q"
- Avoid articles (the, a, an): "If they add question" → "IF Q"
- Use abbreviations where clear: "question" → "Q", "objection" → "obj", "address first then transition" → "address→transition"
- Remove filler words: "directly without context handling" → "direct"

**5. Examples of Optimization**

BEFORE (verbose):
"User agrees (yes/sure/okay/agreeing to hear more/consenting to call/asking what this is about). If they add objection/question/statement: address it first, then transition. Basic acknowledgments (go ahead/sure): proceed directly without context handling."

AFTER (optimized):
"Agrees|consents (yes/sure/okay/what's this). IF objection/Q/statement: address→transition. Basic acks (go ahead/sure): proceed direct."

BEFORE:
"The user is asking a question about pricing or wants to know how much it costs or is inquiring about the investment required"

AFTER:
"Price inquiry | cost question (how much/pricing/investment)"

BEFORE:
"If the user expresses any form of objection such as skepticism, doubt, concern about legitimacy, or questions whether this is a scam"

AFTER:
"Objection: skepticism | doubt | legitimacy concern | scam question"

**ORIGINAL TRANSITION CONDITION:**
```
{original_condition}
```

**YOUR TASK:**
1. Analyze the transition condition's logic and all edge cases
2. Restructure for fastest possible LLM evaluation (aim for 50-70% reduction)
3. Use pipes (|), colons (:), and parentheses () for compact structure
4. Preserve ALL conditions, examples, and if-then logic
5. Lead with main trigger, then qualifiers
6. Output ONLY the optimized condition - no explanations or context

**OUTPUT FORMAT:**
Return just the optimized transition condition text, ready to paste directly into the transition field."""

        # Call Grok API
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {grok_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert at optimizing transition conditions for real-time voice agents. You reduce verbosity while preserving all logic, making evaluations 2-3x faster."
                        },
                        {"role": "user", "content": optimization_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500  # Transitions should be short
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Grok API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"Grok API error: {response.text}")
            
            result = response.json()
            optimized_condition = result['choices'][0]['message']['content'].strip()
            
            # Remove any markdown code blocks if present
            if optimized_condition.startswith('```'):
                optimized_condition = optimized_condition.split('```')[1].strip()
            if optimized_condition.startswith('```'):
                optimized_condition = optimized_condition.split('```')[1].strip()
            
            # Log token usage
            usage = result.get('usage', {})
            logger.info(f"Transition optimization complete. Tokens: {usage.get('total_tokens', 'unknown')}")
            
            return {
                "original": original_condition,
                "optimized": optimized_condition,
                "model": model,
                "tokens_used": usage.get('total_tokens', 0)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing transition: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error optimizing transition: {str(e)}")

@api_router.post("/agents/{agent_id}/enhance-script")
async def enhance_script_for_voice(
    agent_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Enhance script text for voice output with ElevenLabs best practices"""
    try:
        # Verify agent ownership
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get user's Grok API key
        grok_api_key = await get_user_api_key(current_user['id'], 'grok')
        if not grok_api_key:
            raise HTTPException(
                status_code=400,
                detail="Grok API key not found. Please add your Grok API key in Settings > API Keys"
            )
        
        original_script = request.get('script', '')
        model = request.get('model', 'grok-3')  # Default to grok-3
        
        # Build enhancement prompt
        enhancement_prompt = f"""You are an expert at optimizing text scripts for natural voice synthesis (ElevenLabs TTS). Apply these best practices:

**NORMALIZATION:**
- Convert numbers to words: "123" → "one hundred twenty-three"
- Format dates naturally: "3/15/2024" → "March fifteenth, twenty twenty-four"
- Spell out special characters: "john@email.com" → "john at email dot com"
- Convert symbols: "$50" → "fifty dollars", "50%" → "fifty percent"

**SSML CONTROLS:**
- Add natural pauses with <break time="300ms"/> or <break time="500ms"/>
- Use <prosody rate="90%"> for slower delivery on important points
- NO EM-DASHES (—) or EN-DASHES (–) - use periods (.) or commas (,) with conjunctions

**PUNCTUATION FOR SPEECH:**
- Use periods for full stops between distinct ideas
- Use commas with conjunctions ("and", "so", "but") for phrasal breaks
- Avoid semicolons and complex punctuation

**NATURAL FLOW:**
- Keep sentences short and conversational
- Add fillers naturally ("uh", "well") if appropriate
- Ensure rhythm and pacing work for voice

**ORIGINAL SCRIPT:**
{original_script}

**TASK:** Rewrite this script optimized for voice synthesis. Apply all normalization, add SSML tags where appropriate, fix punctuation for natural speech flow. Output only the enhanced script wrapped in <speak> tags."""

        # Call Grok API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {grok_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are an expert at optimizing text for natural voice synthesis with ElevenLabs TTS. You apply normalization, SSML tags, and speech-friendly punctuation."},
                        {"role": "user", "content": enhancement_prompt}
                    ],
                    "temperature": 0.3
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Grok API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"Grok API error: {response.text}")
            
            result = response.json()
            enhanced_script = result['choices'][0]['message']['content']
            
            return {
                "original": original_script,
                "enhanced": enhanced_script,
                "model": model
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enhancing script: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error enhancing script: {str(e)}")


@api_router.post("/agents/{agent_id}/analyze-transitions")
async def analyze_transitions(
    agent_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Analyze all transitions with LLM to show understanding and detect confusion/overlap"""
    try:
        # Verify agent ownership
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        transitions = request.get('transitions', [])
        model = request.get('model', 'grok-3')
        llm_provider = request.get('llm_provider', 'grok')  # 'grok' or 'openai'
        
        if not transitions:
            return {
                "analyses": [],
                "confusion_warnings": [],
                "model": model
            }
        
        # Get appropriate API key
        if llm_provider == 'grok':
            api_key = await get_user_api_key(current_user['id'], 'grok')
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="Grok API key not found. Please add your Grok API key in Settings > API Keys"
                )
        else:
            api_key = await get_user_api_key(current_user['id'], 'openai')
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="OpenAI API key not found. Please add your OpenAI API key in Settings > API Keys"
                )
        
        # Build analysis prompt
        transitions_text = ""
        for i, transition in enumerate(transitions, 1):
            condition = transition.get('condition', 'No condition specified')
            next_node = transition.get('nextNode', 'No target')
            transitions_text += f"\n{i}. Condition: {condition}\n   Target: {next_node}\n"
        
        analysis_prompt = f"""You are analyzing conversation flow transitions for a phone AI agent. Your task is to:

1. Explain each transition condition in simple, clear language
2. Identify potential confusion or overlap between transitions
3. Assess if the conditions are distinct enough for reliable routing

**TRANSITIONS TO ANALYZE:**
{transitions_text}

**YOUR TASK:**
For each transition, provide:
- A clear explanation of what user input would trigger it
- Specific examples of phrases that would match
- Your confidence level (high/medium/low) that you can reliably detect this

Then provide:
- Overall assessment of clarity
- Any confusion or overlap warnings
- Recommendations for improvement if needed

Format your response as JSON:
{{
  "transition_analyses": [
    {{
      "transition_number": 1,
      "understanding": "Clear explanation of what triggers this",
      "example_phrases": ["example 1", "example 2"],
      "confidence": "high|medium|low",
      "notes": "Any concerns or clarifications"
    }}
  ],
  "confusion_warnings": [
    {{
      "affected_transitions": [1, 2],
      "issue": "Description of overlap or confusion",
      "severity": "high|medium|low",
      "recommendation": "How to fix it"
    }}
  ],
  "overall_assessment": "Summary of transition quality"
}}"""

        # Call appropriate LLM API
        async with httpx.AsyncClient(timeout=60.0) as client:
            if llm_provider == 'grok':
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an expert at analyzing conversation flows and transition logic. You provide clear, actionable feedback."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        "temperature": 0.2
                    }
                )
            else:  # OpenAI
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an expert at analyzing conversation flows and transition logic. You provide clear, actionable feedback."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        "temperature": 0.2
                    }
                )
            
            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"LLM API error: {response.text}")
            
            result = response.json()
            analysis_text = result['choices'][0]['message']['content']
            
            # Parse JSON from response
            # Remove markdown code blocks if present
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0]
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1].split("```")[0]
            
            analysis_data = json.loads(analysis_text.strip())
            
            return {
                "transition_analyses": analysis_data.get('transition_analyses', []),
                "confusion_warnings": analysis_data.get('confusion_warnings', []),
                "overall_assessment": analysis_data.get('overall_assessment', ''),
                "model": model,
                "llm_provider": llm_provider
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing transitions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing transitions: {str(e)}")


@api_router.put("/agents/{agent_id}/flow")
async def update_agent_flow(agent_id: str, flow: List[FlowNode], current_user: dict = Depends(get_current_user)):
    """Update agent call flow"""
    agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    await db.agents.update_one(
        {"id": agent_id, "user_id": current_user['id']},
        {"$set": {"call_flow": [node.dict() for node in flow], "updated_at": datetime.utcnow()}}
    )
    return {"message": "Flow updated successfully"}

@api_router.get("/agents/{agent_id}/flow")
async def get_agent_flow(agent_id: str, current_user: dict = Depends(get_current_user)):
    """Get agent call flow"""
    agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"flow": agent.get("call_flow", [])}

# Web-based conversation sessions (for WebCaller)
web_sessions = {}

@api_router.post("/agents/{agent_id}/message")
async def agent_message(agent_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    """Handle web-based conversation with agent"""
    try:
        # Get agent (verify ownership)
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        message = request.get("message", "")
        session_id = request.get("session_id")
        
        logger.info(f"💬 Web message from agent {agent_id}: {message}")
        
        # Create or get session
        if not session_id or session_id not in web_sessions:
            session_id = f"web_{agent_id}_{datetime.utcnow().timestamp()}"
            session = CallSession(session_id, agent, agent_id=agent_id, user_id=agent.get("user_id"), db=db)
            web_sessions[session_id] = session
            logger.info(f"✨ Created new web session: {session_id}")
        else:
            session = web_sessions[session_id]
            logger.info(f"♻️ Using existing session: {session_id}")
        
        # Process message
        response = await session.process_user_input(message)
        
        logger.info(f"🤖 AI response: {response.get('text', '')[:100]}...")
        
        return {
            "session_id": session_id,
            "text": response.get("text", ""),
            "should_end_call": session.should_end_call
        }
        
    except Exception as e:
        logger.error(f"Error processing web message: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/agents/{agent_id}/process")
async def process_message(agent_id: str, request_data: dict, current_user: dict = Depends(get_current_user)):
    """Process a user message and return AI response"""
    try:
        # Get agent (verify ownership)
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get conversation history and user message
        message = request_data.get("message", "")
        conversation_history = request_data.get("conversation_history", [])
        
        logger.info(f"📥 Received message: {message}")
        logger.info(f"📥 Received history length: {len(conversation_history)}")
        logger.info(f"📥 Received history: {conversation_history}")
        
        # Call the calling service to process with KB loading
        session = await create_call_session(f"temp_{agent_id}", agent, agent_id=agent_id, user_id=agent.get("user_id"), db=db)
        
        # Set conversation history if provided
        if conversation_history:
            session.conversation_history = conversation_history
            logger.info(f"✅ Set session history, length: {len(session.conversation_history)}")
        
        response = await session.process_user_input(message)
        
        return {
            "response": response["text"],
            "latency": response["latency"],
            "should_end_call": response.get("end_call", False)
        }
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ KNOWLEDGE BASE ENDPOINTS ============

from fastapi import UploadFile, File

@api_router.post("/agents/{agent_id}/kb/upload")
async def upload_kb_file(agent_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload a file (PDF/TXT/DOCX) to agent's knowledge base"""
    try:
        # Verify agent exists and user owns it
        agent_doc = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent_doc:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        filename = file.filename
        file_content = await file.read()
        
        # Determine file type and extract text
        file_ext = filename.lower().split('.')[-1]
        content = ""
        
        if file_ext == "txt":
            # Text file - direct read
            content = file_content.decode('utf-8', errors='ignore')
        
        elif file_ext == "pdf":
            # PDF extraction using PyPDF2
            import io
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        
        elif file_ext == "docx":
            # DOCX extraction using python-docx
            import io
            import docx
            doc = docx.Document(io.BytesIO(file_content))
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
        
        if not content.strip():
            raise HTTPException(status_code=400, detail="No text content extracted from file")
        
        # Create KB item
        kb_item = KnowledgeBaseItem(
            user_id=current_user['id'],
            agent_id=agent_id,
            source_type="file",
            source_name=filename,
            content=content,
            file_size=len(file_content)
        )
        
        # Store in database
        await db.knowledge_base.insert_one(kb_item.dict())
        
        logger.info(f"📚 KB file uploaded for agent {agent_id}: {filename} ({len(content)} chars)")
        
        # Index with RAG for fast retrieval (if enabled)
        if RAG_ENABLED:
            try:
                from rag_service import index_knowledge_base
                kb_items = await db.knowledge_base.find({"agent_id": agent_id, "user_id": current_user['id']}).to_list(100)
                chunks_indexed = index_knowledge_base(agent_id, kb_items)
                logger.info(f"🔍 RAG: Indexed {chunks_indexed} chunks for agent {agent_id}")
            except Exception as e:
                logger.error(f"❌ RAG indexing error: {e}")
        else:
            logger.info("ℹ️  RAG disabled - KB stored without semantic indexing")
        
        return {
            "id": kb_item.id,
            "agent_id": kb_item.agent_id,
            "source_type": kb_item.source_type,
            "source_name": kb_item.source_name,
            "content_length": len(content),
            "file_size": kb_item.file_size,
            "created_at": kb_item.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading KB file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/agents/{agent_id}/kb/url")
async def add_kb_url(agent_id: str, url: str, current_user: dict = Depends(get_current_user)):
    """Add a website URL to agent's knowledge base (scrapes content)"""
    try:
        # Verify agent exists and user owns it
        agent_doc = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent_doc:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if not url or not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Valid URL required")
        
        # Scrape website content using httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Simple HTML text extraction (remove tags)
            import re
            html_content = response.text
            # Remove script and style elements
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            content = re.sub(r'<[^>]+>', ' ', html_content)
            # Clean up whitespace
            content = re.sub(r'\s+', ' ', content).strip()
        
        if not content.strip():
            raise HTTPException(status_code=400, detail="No text content extracted from URL")
        
        # Create KB item
        kb_item = KnowledgeBaseItem(
            user_id=current_user['id'],
            agent_id=agent_id,
            source_type="url",
            source_name=url,
            content=content,
            file_size=len(content.encode('utf-8'))
        )
        
        # Store in database
        await db.knowledge_base.insert_one(kb_item.dict())
        
        logger.info(f"🌐 KB URL added for agent {agent_id}: {url} ({len(content)} chars)")
        
        # Index with RAG for fast retrieval (if enabled)
        if RAG_ENABLED:
            try:
                from rag_service import index_knowledge_base
                kb_items = await db.knowledge_base.find({"agent_id": agent_id, "user_id": current_user['id']}).to_list(100)
                chunks_indexed = index_knowledge_base(agent_id, kb_items)
                logger.info(f"🔍 RAG: Indexed {chunks_indexed} chunks for agent {agent_id}")
            except Exception as e:
                logger.error(f"❌ RAG indexing error: {e}")
        else:
            logger.info("ℹ️  RAG disabled - KB stored without semantic indexing")
        
        return {
            "id": kb_item.id,
            "agent_id": kb_item.agent_id,
            "source_type": kb_item.source_type,
            "source_name": kb_item.source_name,
            "content_length": len(content),
            "file_size": kb_item.file_size,
            "created_at": kb_item.created_at
        }
        
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error(f"Error fetching URL: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        logger.error(f"Error adding KB URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/agents/{agent_id}/kb/reindex")
async def reindex_agent_kb(agent_id: str, current_user: dict = Depends(get_current_user)):
    """Force re-index all KB items for an agent with RAG"""
    try:
        # Verify agent ownership
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        kb_items = await db.knowledge_base.find({"agent_id": agent_id, "user_id": current_user['id']}).to_list(100)
        
        if not kb_items:
            raise HTTPException(status_code=404, detail="No KB items found for this agent")
        
        # Index with RAG (if enabled)
        if RAG_ENABLED:
            from rag_service import index_knowledge_base
            chunks_indexed = index_knowledge_base(agent_id, kb_items)
            logger.info(f"🔍 RAG: Re-indexed {chunks_indexed} chunks for agent {agent_id}")
        else:
            chunks_indexed = 0
            logger.info(f"ℹ️  RAG disabled - reindexing skipped")
        
        return {
            "agent_id": agent_id,
            "kb_items": len(kb_items),
            "chunks_indexed": chunks_indexed,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-indexing KB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/agents/{agent_id}/kb")
async def list_kb_items(agent_id: str, current_user: dict = Depends(get_current_user)):
    """List all knowledge base items for an agent"""
    try:
        # Verify agent exists and user owns it
        agent_doc = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent_doc:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get all KB items for this agent
        kb_items = await db.knowledge_base.find({"agent_id": agent_id, "user_id": current_user['id']}).to_list(100)
        
        # Return without full content (just metadata)
        return [{
            "id": item.get("id"),
            "agent_id": item.get("agent_id"),
            "source_type": item.get("source_type"),
            "source_name": item.get("source_name"),
            "content_length": len(item.get("content", "")),
            "file_size": item.get("file_size", 0),
            "created_at": item.get("created_at")
        } for item in kb_items]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing KB items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/agents/{agent_id}/kb/{kb_id}")
async def get_kb_item(agent_id: str, kb_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific knowledge base item with full content"""
    try:
        kb_item = await db.knowledge_base.find_one({"id": kb_id, "agent_id": agent_id, "user_id": current_user['id']})
        if not kb_item:
            raise HTTPException(status_code=404, detail="KB item not found")
        
        # Convert MongoDB document to JSON-serializable format
        return {
            "id": kb_item.get("id"),
            "agent_id": kb_item.get("agent_id"),
            "source_type": kb_item.get("source_type"),
            "source_name": kb_item.get("source_name"),
            "content": kb_item.get("content"),
            "file_size": kb_item.get("file_size", 0),
            "created_at": kb_item.get("created_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching KB item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/agents/{agent_id}/kb/{kb_id}")
async def delete_kb_item(agent_id: str, kb_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a knowledge base item"""
    try:
        # Verify ownership
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        result = await db.knowledge_base.delete_one({"id": kb_id, "agent_id": agent_id, "user_id": current_user['id']})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="KB item not found")
        
        logger.info(f"🗑️ KB item deleted: {kb_id} for agent {agent_id}")
        
        # Re-index remaining KB items (if RAG enabled)
        if RAG_ENABLED:
            try:
                from rag_service import index_knowledge_base
                kb_items = await db.knowledge_base.find({"agent_id": agent_id, "user_id": current_user['id']}).to_list(100)
                if kb_items:
                    chunks_indexed = index_knowledge_base(agent_id, kb_items)
                    logger.info(f"🔍 RAG: Re-indexed {chunks_indexed} chunks for agent {agent_id}")
                else:
                    # No more KB items, delete the collection
                    from rag_service import delete_agent_kb
                    delete_agent_kb(agent_id)
                    logger.info(f"🔍 RAG: Deleted empty KB collection for agent {agent_id}")
            except Exception as e:
                logger.error(f"❌ RAG re-indexing error: {e}")
        
        return {"message": "KB item deleted successfully", "id": kb_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting KB item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ NODE SEQUENCE TESTER ENDPOINTS ============

from pydantic import BaseModel as PydanticBaseModel
from typing import Dict as TypingDict, Any as TypingAny
from node_tester import NodeTester, run_node_test

async def create_llm_client_for_agent(user_id: str, llm_provider: str):
    """
    Create an LLM client based on the agent's configured provider and user's API key.
    Supports: openai, grok, groq, anthropic
    """
    # Map provider names to API key service names
    provider_key_map = {
        "openai": "openai",
        "grok": "grok",
        "groq": "groq", 
        "anthropic": "anthropic"
    }
    
    key_service = provider_key_map.get(llm_provider, llm_provider)
    api_key = await get_user_api_key(user_id, key_service)
    
    if not api_key:
        return None
    
    if llm_provider == "openai":
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=api_key)
    
    elif llm_provider in ["grok", "groq"]:
        # Grok/Groq use OpenAI-compatible API
        from openai import AsyncOpenAI
        if llm_provider == "grok":
            return AsyncOpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        else:
            return AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    
    elif llm_provider == "anthropic":
        # Anthropic has its own client
        try:
            from anthropic import AsyncAnthropic
            return AsyncAnthropic(api_key=api_key)
        except ImportError:
            logger.warning("Anthropic library not installed, falling back to OpenAI")
            return None
    
    return None

class NodeTestRequest(PydanticBaseModel):
    """Request model for node testing"""
    node_ids: List[str]
    responses: List[str]
    initial_variables: Optional[TypingDict[str, TypingAny]] = None

class SingleNodeTestRequest(PydanticBaseModel):
    """Request model for single node testing"""
    node_id: str
    user_response: str
    initial_variables: Optional[TypingDict[str, TypingAny]] = None

@api_router.post("/agents/{agent_id}/test-node")
async def test_single_node(
    agent_id: str,
    request: SingleNodeTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Test a single node with a simulated user response.
    Returns detailed extraction, transition, and webhook analysis.
    """
    try:
        # Get agent
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get LLM provider from agent settings
        settings = agent.get("settings", {})
        llm_provider = settings.get("llm_provider", "openai")
        llm_model = settings.get("llm_model")
        
        # Get user's API key for the configured provider
        llm_client = await create_llm_client_for_agent(current_user['id'], llm_provider)
        if not llm_client:
            raise HTTPException(
                status_code=400, 
                detail=f"API key for {llm_provider} not configured. Please add it in Settings."
            )
        
        # Run test
        tester = NodeTester(agent, llm_client=llm_client, llm_provider=llm_provider, llm_model=llm_model)
        result = await tester.test_single_node(
            node_id=request.node_id,
            user_response=request.user_response,
            initial_variables=request.initial_variables
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing node: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/agents/{agent_id}/test-sequence")
async def test_node_sequence(
    agent_id: str,
    request: NodeTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Test a sequence of nodes with simulated user responses.
    Uses the EXACT same code paths as live calls.
    Returns step-by-step breakdown with all intermediate values.
    """
    try:
        # Validate input
        if len(request.node_ids) != len(request.responses):
            raise HTTPException(
                status_code=400, 
                detail=f"Mismatch: {len(request.node_ids)} nodes but {len(request.responses)} responses"
            )
        
        # Get agent
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get LLM provider from agent settings
        settings = agent.get("settings", {})
        llm_provider = settings.get("llm_provider", "openai")
        llm_model = settings.get("llm_model")
        
        # Get user's API key for the configured provider
        llm_client = await create_llm_client_for_agent(current_user['id'], llm_provider)
        if not llm_client:
            raise HTTPException(
                status_code=400, 
                detail=f"API key for {llm_provider} not configured. Please add it in Settings."
            )
        
        # Run test with user's LLM client
        tester = NodeTester(agent, llm_client=llm_client, llm_provider=llm_provider, llm_model=llm_model)
        result = await tester.test_node_sequence(
            node_ids=request.node_ids,
            responses=request.responses,
            initial_variables=request.initial_variables
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing node sequence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/agents/{agent_id}/nodes-for-testing")
async def get_nodes_for_testing(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all nodes in an agent's flow with their testing-relevant info.
    Useful for building the node picker UI.
    """
    try:
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        call_flow = agent.get("call_flow", [])
        nodes = []
        
        for node in call_flow:
            data = node.get("data", {})
            # Label can be at node.label (top level) or node.data.label
            node_label = node.get("label") or data.get("label") or node.get("id")
            node_info = {
                "id": node.get("id"),
                "label": node_label,
                "type": node.get("type") or data.get("type", "dialogue"),
                "has_extraction": bool(data.get("extract_variables")),
                "has_webhook": bool(data.get("webhook", {}).get("url")),
                "has_transitions": bool(data.get("transitions")),
                "extract_variables": [v.get("name") for v in data.get("extract_variables", [])],
                "content_preview": (data.get("content", "")[:100] + "...") if data.get("content") else "",
                "transitions_to": [
                    t.get("target_node_id") or t.get("targetNodeId") 
                    for t in data.get("transitions", [])
                ]
            }
            nodes.append(node_info)
        
        return {
            "agent_id": agent_id,
            "agent_name": agent.get("name"),
            "total_nodes": len(nodes),
            "nodes": nodes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting nodes for testing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ AI NODE FIXER ENDPOINTS ============

from node_fixer import AINodeFixer, FixerUpdate, FixerStatus
from fastapi.responses import StreamingResponse
import asyncio

class NodeFixerRequest(PydanticBaseModel):
    """Request model for AI node fixer"""
    node_ids: List[str]
    test_responses: List[str]
    expected_behavior: Optional[str] = ""
    initial_variables: Optional[TypingDict[str, TypingAny]] = None
    max_iterations: Optional[int] = 5

# Store active fixers for cancellation
active_fixers: TypingDict[str, AINodeFixer] = {}

@api_router.post("/agents/{agent_id}/fix-nodes")
async def fix_nodes_stream(
    agent_id: str,
    request: NodeFixerRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    AI-powered node fixer that iteratively analyzes, tests, and fixes nodes.
    Returns Server-Sent Events (SSE) stream with real-time progress updates.
    """
    # Capture user info before creating generator (dependencies resolved here)
    user_id = current_user['id']
    session_id = f"{agent_id}_{user_id}_{int(time.time())}"
    
    async def event_generator():
        fixer = None
        
        try:
            # Get agent
            agent = await db.agents.find_one({"id": agent_id, "user_id": user_id})
            if not agent:
                yield f"data: {json.dumps({'status': 'failed', 'message': 'Agent not found'})}\n\n"
                return
            
            # Get LLM provider and model from agent settings
            settings = agent.get("settings", {})
            llm_provider = settings.get("llm_provider", "openai")
            llm_model = settings.get("llm_model")
            
            if not llm_model:
                yield f"data: {json.dumps({'status': 'failed', 'message': 'No LLM model configured on this agent. Please set it in agent settings.'})}\n\n"
                return
            
            # Get user's API key for the configured provider
            llm_client = await create_llm_client_for_agent(user_id, llm_provider)
            if not llm_client:
                yield f"data: {json.dumps({'status': 'failed', 'message': f'API key for {llm_provider} not configured'})}\n\n"
                return
            
            # Create fixer using agent's exact LLM settings
            fixer = AINodeFixer(
                agent_config=agent,
                llm_client=llm_client,
                llm_provider=llm_provider,
                llm_model=llm_model,
                max_iterations=request.max_iterations or 5
            )
            
            # Store for potential cancellation
            active_fixers[session_id] = fixer
            
            # Send session ID first
            yield f"data: {json.dumps({'session_id': session_id, 'status': 'started'})}\n\n"
            
            # Run fixer and stream updates
            async for update in fixer.fix_sequence(
                node_ids=request.node_ids,
                test_responses=request.test_responses,
                expected_behavior=request.expected_behavior or "",
                initial_variables=request.initial_variables
            ):
                update_dict = {
                    "status": update.status.value,
                    "iteration": update.iteration,
                    "max_iterations": update.max_iterations,
                    "message": update.message,
                    "details": update.details,
                    "node_changes": update.node_changes,
                    "test_results": update.test_results
                }
                yield f"data: {json.dumps(update_dict)}\n\n"
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.1)
            
            # Send final fixed nodes if successful
            if fixer and not fixer.cancelled:
                fixed_nodes = fixer.get_fixed_nodes()
                yield f"data: {json.dumps({'fixed_nodes': fixed_nodes, 'status': 'complete'})}\n\n"
                
        except Exception as e:
            logger.error(f"Node fixer error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        finally:
            # Cleanup
            if session_id in active_fixers:
                del active_fixers[session_id]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@api_router.post("/agents/{agent_id}/fix-nodes/cancel")
async def cancel_node_fixer(
    agent_id: str,
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel an active node fixer session"""
    if session_id in active_fixers:
        active_fixers[session_id].cancel()
        return {"success": True, "message": "Cancellation requested"}
    return {"success": False, "message": "Session not found"}

@api_router.post("/agents/{agent_id}/apply-fixed-nodes")
async def apply_fixed_nodes(
    agent_id: str,
    fixed_nodes: List[TypingDict[str, TypingAny]],
    current_user: dict = Depends(get_current_user)
):
    """
    Apply the fixed nodes to the actual agent (after user approval).
    This updates the agent's call_flow with the fixed versions.
    """
    try:
        agent = await db.agents.find_one({"id": agent_id, "user_id": current_user['id']})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get current call_flow
        call_flow = agent.get("call_flow", [])
        
        # Create lookup of fixed nodes
        fixed_lookup = {str(n.get("id")): n for n in fixed_nodes}
        
        # Update nodes in call_flow
        updated_flow = []
        changes_applied = 0
        for node in call_flow:
            node_id = str(node.get("id"))
            if node_id in fixed_lookup:
                updated_flow.append(fixed_lookup[node_id])
                changes_applied += 1
            else:
                updated_flow.append(node)
        
        # Save to database
        await db.agents.update_one(
            {"id": agent_id, "user_id": current_user['id']},
            {"$set": {"call_flow": updated_flow}}
        )
        
        return {
            "success": True,
            "message": f"Applied {changes_applied} fixed node(s) to agent",
            "changes_applied": changes_applied
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying fixed nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ API KEY MANAGEMENT ENDPOINTS ============

from models import APIKey, APIKeyCreate

async def get_api_key(user_id: str, service_name: str) -> str:
    """
    Retrieve and decrypt an API key for a user and service.
    Returns None if key not found.
    """
    from key_encryption import decrypt_api_key
    
    key_doc = await db.api_keys.find_one({
        "user_id": user_id,
        "service_name": service_name,
        "is_active": True
    })
    
    if not key_doc:
        return None
    
    # Decrypt and return the key
    encrypted_key = key_doc.get("encrypted_key") or key_doc.get("api_key")
    if not encrypted_key:
        return None
    
    try:
        return decrypt_api_key(encrypted_key)
    except Exception as e:
        # If decryption fails, assume it's plaintext (for backward compatibility)
        logger.warning(f"Failed to decrypt {service_name}, using as plaintext: {str(e)[:50]}")
        return encrypted_key

@api_router.get("/settings/api-keys")
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List all configured API keys (returns service names only, not actual keys)"""
    keys = await db.api_keys.find({"user_id": current_user['id']}).to_list(100)
    return [{
        "id": key.get("id"),
        "service_name": key.get("service_name"),
        "is_active": key.get("is_active", True),
        "created_at": key.get("created_at"),
        "has_key": bool(key.get("api_key"))
    } for key in keys]

@api_router.post("/settings/api-keys")
async def create_or_update_api_key(api_key_data: APIKeyCreate, current_user: dict = Depends(get_current_user)):
    """Create or update an API key for a service (keys are encrypted at rest)"""
    from key_encryption import encrypt_api_key
    
    # Encrypt the API key before storing
    encrypted_key = encrypt_api_key(api_key_data.api_key)
    
    # Check if key already exists for this service and user
    existing = await db.api_keys.find_one({"service_name": api_key_data.service_name, "user_id": current_user['id']})
    
    if existing:
        # Update existing key
        await db.api_keys.update_one(
            {"service_name": api_key_data.service_name, "user_id": current_user['id']},
            {"$set": {
                "api_key": encrypted_key,
                "updated_at": datetime.utcnow(),
                "is_active": True
            }}
        )
        logger.info(f"✅ Updated API key for {api_key_data.service_name} (user: {current_user['email']})")
        return {"message": f"API key for {api_key_data.service_name} updated successfully"}
    else:
        # Create new key
        new_key = APIKey(
            user_id=current_user['id'],
            service_name=api_key_data.service_name,
            api_key=encrypted_key
        )
        await db.api_keys.insert_one(new_key.dict())
        logger.info(f"✅ Created API key for {api_key_data.service_name} (user: {current_user['email']})")
        return {"message": f"API key for {api_key_data.service_name} created successfully"}

@api_router.delete("/settings/api-keys/{service_name}")
async def delete_api_key(service_name: str, current_user: dict = Depends(get_current_user)):
    """Delete an API key for a service"""
    result = await db.api_keys.delete_one({"service_name": service_name, "user_id": current_user['id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No API key found for {service_name}")
    logger.info(f"🗑️  Deleted API key for {service_name}")
    return {"message": f"API key for {service_name} deleted successfully"}

@api_router.post("/settings/api-keys/test/{service_name}")
async def test_api_key(service_name: str, current_user: dict = Depends(get_current_user)):
    """Test if an API key is valid by making a simple API call"""
    import httpx
    from key_encryption import decrypt_api_key
    
    # Get the API key
    key_doc = await db.api_keys.find_one({"service_name": service_name, "user_id": current_user['id']})
    if not key_doc:
        raise HTTPException(status_code=404, detail=f"No API key found for {service_name}")
    
    # Decrypt the key before testing
    encrypted_key = key_doc.get("api_key")
    api_key = decrypt_api_key(encrypted_key)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if service_name == "openai":
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
            elif service_name == "deepgram":
                response = await client.get(
                    "https://api.deepgram.com/v1/projects",
                    headers={"Authorization": f"Token {api_key}"}
                )
            elif service_name == "elevenlabs":
                response = await client.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers={"xi-api-key": api_key}
                )
            elif service_name == "grok" or service_name == "xai":
                response = await client.get(
                    "https://api.x.ai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
            elif service_name == "gemini":
                # Use Google's OpenAI-compatible endpoint to test the key
                response = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/openai/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
            elif service_name == "hume":
                response = await client.get(
                    "https://api.hume.ai/v0/batch/jobs",
                    headers={"X-Hume-Api-Key": api_key}
                )
            elif service_name == "soniox":
                # Soniox doesn't have a simple test endpoint, check if key format is valid
                # Valid keys are 32+ chars alphanumeric
                if len(api_key) >= 32 and api_key.replace('-', '').replace('_', '').isalnum():
                    return {"valid": True, "message": f"API key for {service_name} appears valid (format check)"}
                else:
                    return {"valid": False, "error": "Invalid key format"}
            elif service_name == "assemblyai":
                response = await client.get(
                    "https://api.assemblyai.com/v2/user",
                    headers={"authorization": api_key}
                )
            elif service_name == "telnyx":
                response = await client.get(
                    "https://api.telnyx.com/v2/phone_numbers",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
            elif service_name == "cartesia":
                response = await client.get(
                    "https://api.cartesia.ai/voices",
                    headers={"X-API-Key": api_key}
                )
            else:
                return {"valid": False, "error": f"Unknown service: {service_name}"}
            
            if response.status_code == 200:
                return {"valid": True, "message": f"✅ API key for {service_name} is valid"}
            elif response.status_code == 401 or response.status_code == 403:
                return {"valid": False, "error": f"❌ Invalid API key (401/403 Unauthorized)"}
            elif response.status_code == 404:
                return {"valid": False, "error": f"⚠️ Test endpoint not found, but key format OK"}
            else:
                return {"valid": False, "error": f"⚠️ API returned status {response.status_code}"}
                
    except Exception as e:
        logger.error(f"Error testing {service_name} API key: {e}")
        return {"valid": False, "error": str(e)}


# ============ WEBHOOK TESTER ENDPOINT ============

@api_router.post("/webhook-test")
async def test_webhook(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Proxy endpoint to test webhooks from the Flow Builder.
    Avoids CORS issues by making the request server-side.
    """
    import httpx
    
    try:
        body = await request.json()
        
        url = body.get('url')
        method = body.get('method', 'POST').upper()
        payload = body.get('body', {})
        headers = body.get('headers', {})
        timeout = body.get('timeout', 10000) / 1000  # Convert ms to seconds
        
        if not url:
            return {
                "success": False,
                "error": "URL is required"
            }
        
        # Add default headers
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        logger.info(f"🔗 Testing webhook: {method} {url}")
        
        async with httpx.AsyncClient() as client:
            if method == 'GET':
                response = await client.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = await client.post(url, headers=headers, json=payload, timeout=timeout)
            elif method == 'PUT':
                response = await client.put(url, headers=headers, json=payload, timeout=timeout)
            elif method == 'DELETE':
                response = await client.delete(url, headers=headers, timeout=timeout)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported method: {method}"
                }
            
            # Try to parse response as JSON
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            logger.info(f"🔗 Webhook response: {response.status_code}")
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response": response_data
            }
            
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Request timed out"
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Webhook test error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============ SPEECH-TO-TEXT ENDPOINT ============

from fastapi import File, UploadFile

@api_router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text using Deepgram"""
    import tempfile
    from pydub import AudioSegment
    
    try:
        if not DEEPGRAM_API_KEY:
            raise HTTPException(status_code=500, detail="Deepgram API key not configured")
        
        # Read audio file
        audio_data = await audio.read()
        logger.info(f"Received audio: {len(audio_data)} bytes, type: {audio.content_type}")
        
        # Convert webm to WAV using pydub
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
            temp_webm.write(audio_data)
            temp_webm_path = temp_webm.name
        
        try:
            # Load and convert to WAV
            audio_segment = AudioSegment.from_file(temp_webm_path, format="webm")
            
            # Convert to mono, 16kHz, 16-bit PCM
            audio_segment = audio_segment.set_channels(1)
            audio_segment = audio_segment.set_frame_rate(16000)
            audio_segment = audio_segment.set_sample_width(2)  # 16-bit
            
            # Export as WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                audio_segment.export(temp_wav.name, format="wav")
                temp_wav_path = temp_wav.name
            
            # Read WAV data
            with open(temp_wav_path, 'rb') as f:
                wav_data = f.read()
            
            logger.info(f"Converted to WAV: {len(wav_data)} bytes")
            
            # Clean up temp files
            import os
            os.unlink(temp_webm_path)
            os.unlink(temp_wav_path)
            
        except Exception as conv_error:
            logger.error(f"Audio conversion error: {conv_error}")
            # Try sending original audio anyway
            wav_data = audio_data
        
        # Call Deepgram API with Nova-3
        url = "https://api.deepgram.com/v1/listen"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/wav"
        }
        params = {
            "model": "nova-3",
            "smart_format": "true",
            "language": "en",
            "punctuate": "true"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, params=params, content=wav_data)
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                logger.info(f"✅ Transcript: {transcript}")
                return {"transcript": transcript}
            else:
                logger.error(f"❌ Deepgram error ({response.status_code}): {response.text}")
                raise HTTPException(status_code=500, detail="Speech recognition failed")
        
    except Exception as e:
        logger.error(f"Error in speech-to-text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ TEXT-TO-SPEECH ENDPOINT ============

@api_router.post("/text-to-speech")
async def text_to_speech(request_data: dict):
    """Convert text to speech using ElevenLabs"""
    try:
        if not ELEVEN_API_KEY:
            raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")
        
        text = request_data.get("text", "")
        voice = request_data.get("voice", "Rachel")
        
        # Map voice names to ElevenLabs voice IDs
        voice_map = {
            "Rachel": "21m00Tcm4TlvDq8ikWAM",
            "Joseph": "Zlb1dXrM653N07WRdFW3",
            "Emily": "LcfcDJNUP1GQjkzn1xUU",
            "Daniel": "onwK4e9ZLuTAKqWW03F9",
        }
        
        voice_id = voice_map.get(voice, voice_map["Rachel"])
        
        # Call ElevenLabs API
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVEN_API_KEY
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                from fastapi.responses import Response
                return Response(content=response.content, media_type="audio/mpeg")
            else:
                logger.error(f"ElevenLabs error: {response.text}")
                raise HTTPException(status_code=500, detail="Text-to-speech failed")
        
    except Exception as e:
        logger.error(f"Error in text-to-speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ CALL ENDPOINTS ============

@api_router.post("/calls", response_model=Call)
async def create_call(call_data: CallCreate, current_user: dict = Depends(get_current_user)):
    """Create/start a new call"""
    # Get agent details (verify ownership)
    agent = await db.agents.find_one({"id": call_data.agent_id, "user_id": current_user['id']})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create call record
    call = Call(
        user_id=current_user['id'],
        agent_id=call_data.agent_id,
        agent_name=agent["name"],
        phone_number=call_data.phone_number,
        direction=call_data.direction
    )
    
    await db.calls.insert_one(call.dict())
    
    # Update agent stats
    await db.agents.update_one(
        {"id": call_data.agent_id, "user_id": current_user['id']},
        {"$inc": {"stats.calls_handled": 1}}
    )
    
    logger.info(f"Created call: {call.id} for user: {current_user['email']}")
    return call

@api_router.get("/calls", response_model=List[Call])
async def list_calls(limit: int = 100, current_user: dict = Depends(get_current_user)):
    """List all calls for current user"""
    calls = await db.calls.find({"user_id": current_user['id']}).sort("timestamp", -1).limit(limit).to_list(limit)
    return [Call(**call) for call in calls]

@api_router.get("/calls/{call_id}", response_model=Call)
async def get_call(call_id: str, current_user: dict = Depends(get_current_user)):
    """Get call by ID"""
    call = await db.calls.find_one({"id": call_id, "user_id": current_user['id']})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return Call(**call)

@api_router.post("/calls/{call_id}/end")
async def end_call(call_id: str, call_data: dict):
    """End a call and update stats"""
    call = await db.calls.find_one({"id": call_id})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    update_data = {
        "status": "completed",
        "duration": call_data.get("duration", 0),
        "sentiment": call_data.get("sentiment", "neutral"),
        "latency": call_data.get("latency", 0.0),
        "transcript": call_data.get("transcript", [])
    }
    
    await db.calls.update_one({"id": call_id}, {"$set": update_data})
    
    # Update agent stats
    agent = await db.agents.find_one({"id": call["agent_id"]})
    if agent:
        stats = agent.get("stats", {})
        total_calls = stats.get("calls_handled", 1)
        avg_latency = stats.get("avg_latency", 0.0)
        
        # Calculate new average latency
        new_avg_latency = ((avg_latency * (total_calls - 1)) + call_data.get("latency", 0.0)) / total_calls
        
        await db.agents.update_one(
            {"id": call["agent_id"]},
            {"$set": {"stats.avg_latency": round(new_avg_latency, 2)}}
        )
    
    return {"message": "Call ended successfully"}

# ============ PHONE NUMBER ENDPOINTS ============

@api_router.post("/phone-numbers", response_model=PhoneNumber)
async def create_phone_number(number_data: PhoneNumberCreate, current_user: dict = Depends(get_current_user)):
    """Add a new phone number"""
    phone_number = PhoneNumber(
        user_id=current_user['id'],
        number=number_data.number,
        inbound_agent_id=number_data.inbound_agent_id,
        outbound_agent_id=number_data.outbound_agent_id,
        status="active"
    )
    
    # Get inbound agent name if assigned (verify ownership)
    if number_data.inbound_agent_id:
        agent = await db.agents.find_one({"id": number_data.inbound_agent_id, "user_id": current_user['id']})
        if agent:
            phone_number.inbound_agent_name = agent["name"]
    
    # Get outbound agent name if assigned (verify ownership)
    if number_data.outbound_agent_id:
        agent = await db.agents.find_one({"id": number_data.outbound_agent_id, "user_id": current_user['id']})
        if agent:
            phone_number.outbound_agent_name = agent["name"]
    
    await db.phone_numbers.insert_one(phone_number.dict())
    return phone_number

@api_router.get("/phone-numbers", response_model=List[PhoneNumber])
async def list_phone_numbers(current_user: dict = Depends(get_current_user)):
    """List all phone numbers for current user"""
    numbers = await db.phone_numbers.find({"user_id": current_user['id']}).to_list(1000)
    return [PhoneNumber(**num) for num in numbers]

@api_router.put("/phone-numbers/{number_id}")
async def update_phone_number(number_id: str, update_data: dict, current_user: dict = Depends(get_current_user)):
    """Update phone number agent assignments"""
    number = await db.phone_numbers.find_one({"id": number_id, "user_id": current_user['id']})
    if not number:
        raise HTTPException(status_code=404, detail="Phone number not found")
    
    updated_fields = {}
    
    # Handle inbound agent assignment (verify ownership)
    if "inbound_agent_id" in update_data:
        inbound_agent_id = update_data["inbound_agent_id"]
        updated_fields["inbound_agent_id"] = inbound_agent_id
        
        if inbound_agent_id:
            agent = await db.agents.find_one({"id": inbound_agent_id, "user_id": current_user['id']})
            if agent:
                updated_fields["inbound_agent_name"] = agent["name"]
        else:
            updated_fields["inbound_agent_name"] = None
    
    # Handle outbound agent assignment (verify ownership)
    if "outbound_agent_id" in update_data:
        outbound_agent_id = update_data["outbound_agent_id"]
        updated_fields["outbound_agent_id"] = outbound_agent_id
        
        if outbound_agent_id:
            agent = await db.agents.find_one({"id": outbound_agent_id, "user_id": current_user['id']})
            if agent:
                updated_fields["outbound_agent_name"] = agent["name"]
        else:
            updated_fields["outbound_agent_name"] = None
    
    # Handle number update
    if "number" in update_data:
        updated_fields["number"] = update_data["number"]
    
    await db.phone_numbers.update_one({"id": number_id, "user_id": current_user['id']}, {"$set": updated_fields})
    
    # Return updated phone number
    updated_number = await db.phone_numbers.find_one({"id": number_id, "user_id": current_user['id']})
    return PhoneNumber(**updated_number)

@api_router.delete("/phone-numbers/{number_id}")
async def delete_phone_number(number_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a phone number"""
    result = await db.phone_numbers.delete_one({"id": number_id, "user_id": current_user['id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Phone number not found")
    return {"message": "Phone number deleted successfully"}

# ============ DAILY.CO INTEGRATION ============

async def create_daily_room(agent_id: str) -> dict:
    """Create a Daily.co room for testing"""
    url = "https://api.daily.co/v1/rooms"
    headers = {
        "Authorization": f"Bearer {DAILY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": f"retell-{agent_id.replace('-', '')}",
        "privacy": "public",
        "properties": {
            "enable_recording": "cloud",
            "enable_chat": False,
            "enable_knocking": False,
            "start_audio_off": False,
            "start_video_off": True
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code == 200:
                room_data = response.json()
                return {
                    "room_url": room_data["url"],
                    "room_name": room_data["name"],
                    "config": room_data
                }
            else:
                logger.error(f"Failed to create Daily room: {response.text}")
                return {
                    "room_url": os.environ.get("DAILY_ROOM_URL", "https://aqlyf.daily.co/test"),
                    "room_name": "default",
                    "config": {}
                }
    except Exception as e:
        logger.error(f"Error creating Daily room: {str(e)}")
        return {
            "room_url": os.environ.get("DAILY_ROOM_URL", "https://aqlyf.daily.co/test"),
            "room_name": "default",
            "config": {}
        }

@api_router.post("/test/create-room")
async def create_test_room(agent_id: str):
    """Create a Daily.co room for testing an agent"""
    room = await create_daily_room(agent_id)
    return room

# ============ DEEPGRAM WEBSOCKET PROXY ============

@api_router.websocket("/deepgram-live")
async def deepgram_live_stream(websocket: WebSocket):
    """
    WebSocket proxy for Deepgram Live Streaming with configurable endpointing
    Frontend sends audio chunks, backend forwards to Deepgram and returns transcripts
    """
    await websocket.accept()
    logger.info("🎙️ Client connected for live streaming")
    
    if not DEEPGRAM_API_KEY:
        await websocket.close(code=1008, reason="Deepgram API key not configured")
        return
    
    import aiohttp
    import asyncio
    from deepgram_config import get_deepgram_url, get_config_summary, DEEPGRAM_CONFIG
    
    # Log current configuration
    config_summary = get_config_summary()
    logger.info(f"📊 Deepgram Config: {config_summary}")
    
    deepgram_ws = None
    
    try:
        # Connect to Deepgram
        deepgram_url = get_deepgram_url()
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(deepgram_url, headers=headers) as deepgram_ws:
                logger.info("✅ Connected to Deepgram Live API")
                
                # Send config info to client
                await websocket.send_json({
                    "type": "config",
                    "config": config_summary
                })
                
                async def forward_from_client():
                    """Forward audio from client to Deepgram"""
                    try:
                        while True:
                            data = await websocket.receive()
                            
                            if data["type"] == "websocket.receive":
                                if "bytes" in data:
                                    # Forward audio bytes to Deepgram
                                    await deepgram_ws.send_bytes(data["bytes"])
                                elif "text" in data:
                                    # Handle control messages
                                    msg = json.loads(data["text"])
                                    if msg.get("type") == "close":
                                        break
                    except WebSocketDisconnect:
                        logger.info("Client disconnected")
                    except Exception as e:
                        logger.error(f"Error forwarding from client: {e}")
                
                async def forward_from_deepgram():
                    """Forward transcription results from Deepgram to client"""
                    try:
                        async for msg in deepgram_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                # Forward Deepgram response to client
                                await websocket.send_text(msg.data)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"Deepgram WS error: {deepgram_ws.exception()}")
                                break
                    except Exception as e:
                        logger.error(f"Error forwarding from Deepgram: {e}")
                
                # Run both directions concurrently
                await asyncio.gather(
                    forward_from_client(),
                    forward_from_deepgram(),
                    return_exceptions=True
                )
                
    except Exception as e:
        logger.error(f"Deepgram streaming error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔌 Deepgram live stream closed")

# ============ HEALTH CHECK ============

@api_router.get("/")
async def root():
    return {
        "message": "Retell AI Clone API",
        "version": "1.0.0",
        "status": "operational"
    }

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "deepgram": "configured" if DEEPGRAM_API_KEY else "not configured",
        "openai": "configured" if OPENAI_API_KEY else "not configured",
        "elevenlabs": "configured" if ELEVEN_API_KEY else "not configured",
        "daily": "configured" if DAILY_API_KEY else "not configured"
    }

@api_router.post("/warmup/tts")
async def warmup_tts_connection(
    current_user: dict = Depends(get_current_user)
):
    """
    Pre-warm TTS connection for faster call startup.
    Call this before initiating a call to reduce first-response latency.
    """
    try:
        import time
        start_time = time.time()
        
        # Get user's ElevenLabs API key
        elevenlabs_api_key = await get_api_key(current_user["id"], "elevenlabs")
        
        if not elevenlabs_api_key:
            return {
                "success": False,
                "message": "No ElevenLabs API key configured",
                "warmup_time_ms": 0
            }
        
        # Create a temporary WebSocket connection to warm up the connection
        from elevenlabs_ws_service import ElevenLabsWebSocketService
        
        ws_service = ElevenLabsWebSocketService(elevenlabs_api_key)
        connected = await ws_service.connect(
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Default voice for warmup
            model_id="eleven_flash_v2_5",
            output_format="pcm_16000"
        )
        
        warmup_time = int((time.time() - start_time) * 1000)
        
        if connected:
            # Close the warmup connection
            await ws_service.close()
            logger.info(f"🔥 TTS warmup completed in {warmup_time}ms")
            return {
                "success": True,
                "message": "TTS connection warmed up",
                "warmup_time_ms": warmup_time
            }
        else:
            return {
                "success": False,
                "message": "Failed to establish TTS connection",
                "warmup_time_ms": warmup_time
            }
            
    except Exception as e:
        logger.error(f"TTS warmup failed: {e}")
        return {
            "success": False,
            "message": str(e),
            "warmup_time_ms": 0
        }

# ============ WEBSOCKET FOR REAL-TIME CALLING ============

@app.websocket("/ws/call/{call_id}")
async def websocket_call(websocket: WebSocket, call_id: str):
    """WebSocket endpoint for real-time audio streaming and transcription"""
    await websocket.accept()
    logger.info(f"WebSocket connection established for call {call_id}")
    
    call_session = None
    
    try:
        # Get call details from database
        call = await db.calls.find_one({"id": call_id})
        if not call:
            await websocket.send_json({"error": "Call not found"})
            await websocket.close()
            return
        
        # Get agent configuration
        agent = await db.agents.find_one({"id": call["agent_id"]})
        if not agent:
            await websocket.send_json({"error": "Agent not found"})
            await websocket.close()
            return
        
        # Create call session with audio pipeline, passing agent_id for config refresh and KB
        call_session = await create_call_session(call_id, agent, agent_id=call["agent_id"], user_id=agent.get("user_id"), db=db)
        
        # Send ready signal
        await websocket.send_json({
            "type": "ready",
            "message": "Call session initialized"
        })
        
        # Handle incoming messages
        while True:
            message = await websocket.receive()
            
            if "text" in message:
                # Handle text messages (control signals)
                data = json.loads(message["text"])
                msg_type = data.get("type")
                
                if msg_type == "end_call":
                    logger.info(f"Ending call {call_id}")
                    break
                    
                elif msg_type == "user_message":
                    # Process text input from user
                    user_text = data.get("text", "")
                    response = await call_session.process_user_input(user_text)
                    
                    if response:
                        await websocket.send_json({
                            "type": "agent_response",
                            "text": response["text"],
                            "latency": response["latency"]
                        })
                        
                        # Update call transcript
                        await db.calls.update_one(
                            {"id": call_id},
                            {
                                "$push": {
                                    "transcript": {
                                        "role": "user",
                                        "text": user_text,
                                        "timestamp": datetime.utcnow()
                                    }
                                }
                            }
                        )
                        
                        await db.calls.update_one(
                            {"id": call_id},
                            {
                                "$push": {
                                    "transcript": {
                                        "role": "assistant",
                                        "text": response["text"],
                                        "timestamp": datetime.utcnow()
                                    }
                                }
                            }
                        )
            
            elif "bytes" in message:
                # Handle audio data
                audio_data = message["bytes"]
                await call_session.send_audio_chunk(audio_data)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call {call_id}")
    except Exception as e:
        logger.error(f"WebSocket error for call {call_id}: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        # Clean up call session
        if call_session:
            await close_call_session(call_id)
        await websocket.close()
        logger.info(f"WebSocket closed for call {call_id}")

# ============ TELNYX PHONE SYSTEM ENDPOINTS ============

# Lazy initialize Telnyx service (only when needed)
_telnyx_service = None

def get_telnyx_service(api_key: str = None, connection_id: str = None):
    # For per-user API keys, create a new instance
    if api_key and connection_id:
        return TelnyxService(api_key=api_key, connection_id=connection_id)
    
    # For environment-based keys (webhooks), use singleton
    global _telnyx_service
    if _telnyx_service is None:
        _telnyx_service = TelnyxService()
    return _telnyx_service

# Active calls are now stored in Redis for multi-worker state sharing
# Legacy in-memory dict kept as fallback only (not used when Redis is available)
active_telnyx_calls = {}  # Fallback only - Redis is primary storage

# AMD (Answering Machine Detection) events - used to signal when AMD completes
# Key: call_control_id, Value: {"event": asyncio.Event, "result": "human"|"machine"|"not_sure"|None}
amd_completion_events = {}

def update_call_state(call_control_id: str, updates: dict):
    """
    Update call state in both Redis and in-memory storage
    Helper function to keep both storages in sync
    """
    # Update Redis
    redis_service.update_call_data(call_control_id, updates)
    
    # Update in-memory fallback
    if call_control_id in active_telnyx_calls:
        active_telnyx_calls[call_control_id].update(updates)

# ============ WEBHOOK TRIGGER ENDPOINT (API Key Auth for External Services) ============

@api_router.post("/webhook/trigger-call")
async def webhook_trigger_outbound_call(
    payload: dict,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """
    Trigger an outbound call via external webhook.
    
    Use this endpoint from external services like n8n, Zapier, Make, GoHighLevel, etc.
    
    Authentication: Pass your user API key in the X-API-Key header.
    You can find/create your API key in Settings > API Keys > "webhook" service.
    
    Supports two payload formats:
    
    1. Simple format (recommended):
    ```json
    {
      "agent_id": "your-agent-uuid",
      "to_number": "+17701234567",
      "from_number": "+18722778634",
      "custom_variables": {"name": "John"}
    }
    ```
    
    2. GoHighLevel format (auto-detected):
    ```json
    {
      "phone": "+17701234567",
      "first_name": "John",
      "customData": {
        "agent_id": "your-agent-uuid",
        "from_number": "+18722778634"
      }
    }
    ```
    """
    try:
        from key_encryption import decrypt_api_key
        
        # Extract data from payload - handle both simple and GoHighLevel formats
        custom_data = payload.get("customData", {}) or {}
        
        # Extract agent_id (check root first, then customData)
        agent_id = payload.get("agent_id") or custom_data.get("agent_id")
        
        # Extract to_number (check root first, then customData, then phone field)
        to_number = payload.get("to_number") or custom_data.get("to_number") or payload.get("phone")
        
        # Extract from_number (optional)
        from_number = payload.get("from_number") or custom_data.get("from_number")
        
        # Extract email (optional)
        email = payload.get("email") or custom_data.get("email") or custom_data.get("customer_email")
        
        # Build custom_variables from remaining data
        custom_variables = payload.get("custom_variables") or {}
        
        # Add GoHighLevel fields to custom_variables if present
        if payload.get("first_name"):
            custom_variables["customer_name"] = f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip()
        if custom_data.get("customer_name"):
            custom_variables["customer_name"] = custom_data.get("customer_name")
        if payload.get("contact_id"):
            custom_variables["contact_id"] = payload.get("contact_id")
        
        # Validate required fields
        if not agent_id:
            raise HTTPException(
                status_code=400, 
                detail="Missing agent_id. Provide it at root level or in customData."
            )
        if not to_number:
            raise HTTPException(
                status_code=400, 
                detail="Missing to_number. Provide it at root level, in customData, or as 'phone' field."
            )
        
        logger.info(f"📞 Webhook trigger: agent={agent_id}, to={to_number}, from={from_number}")
        
        # Find user by webhook API key
        all_webhook_keys = await db.api_keys.find({
            "service_name": "webhook",
            "is_active": True
        }).to_list(None)
        
        user_id = None
        for key_doc in all_webhook_keys:
            try:
                decrypted_key = decrypt_api_key(key_doc.get("api_key", ""))
                if decrypted_key == x_api_key:
                    user_id = key_doc.get("user_id")
                    break
            except:
                continue
        
        if not user_id:
            logger.warning(f"❌ Invalid webhook API key attempted")
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        logger.info(f"✅ Webhook auth successful for user: {user_id[:8]}...")
        
        # Get agent and verify ownership
        agent = await db.agents.find_one({"id": agent_id, "user_id": user_id})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or not owned by this user")
        
        # Use extracted from_number or default
        final_from_number = from_number or "+18722778634"
        
        # Create webhook URL
        backend_url = os.environ.get("BACKEND_URL")
        if not backend_url:
            raise ValueError("BACKEND_URL environment variable must be set for outbound calls")
        
        if not backend_url.startswith("http://") and not backend_url.startswith("https://"):
            backend_url = f"https://{backend_url}"
        
        webhook_url = f"{backend_url}/api/telnyx/webhook"
        
        # Create WebSocket streaming URL
        if backend_url.startswith("https://"):
            ws_url = backend_url.replace("https://", "wss://")
        elif backend_url.startswith("http://"):
            ws_url = backend_url.replace("http://", "ws://")
        else:
            ws_url = f"wss://{backend_url}"
        
        stream_url = f"{ws_url}/api/telnyx/audio-stream"
        
        # Get user's Telnyx API keys from database
        telnyx_api_key = await get_api_key(user_id, "telnyx")
        telnyx_connection_id = await get_api_key(user_id, "telnyx_connection_id")
        
        if not telnyx_api_key or not telnyx_connection_id:
            raise HTTPException(
                status_code=400, 
                detail="Telnyx API key and Connection ID must be configured in API Keys settings"
            )
        
        # Get voicemail detection settings
        vm_settings = agent.get("settings", {}).get("voicemail_detection", {})
        enable_amd = vm_settings.get("enabled", True) and vm_settings.get("use_telnyx_amd", True)
        amd_mode = vm_settings.get("telnyx_amd_mode", "premium")
        
        # Initiate call via Telnyx
        telnyx_service = get_telnyx_service(api_key=telnyx_api_key, connection_id=telnyx_connection_id)
        call_result = await telnyx_service.initiate_outbound_call(
            to_number=to_number,
            from_number=final_from_number,
            webhook_url=webhook_url,
            custom_variables=custom_variables,
            stream_url=stream_url,
            enable_amd=enable_amd,
            amd_mode=amd_mode
        )
        
        if not call_result.get("success"):
            raise HTTPException(status_code=500, detail=call_result.get("error"))
        
        call_control_id = call_result["call_control_id"]
        
        # Create call log
        await create_call_log(
            call_id=call_control_id,
            agent_id=agent_id,
            direction="outbound",
            from_number=final_from_number,
            to_number=to_number,
            user_id=user_id
        )
        
        # Sanitize agent data
        agent_sanitized = {}
        for key, value in agent.items():
            if key == "_id":
                continue
            if isinstance(value, datetime):
                agent_sanitized[key] = value.isoformat()
            else:
                agent_sanitized[key] = value
        
        call_data = {
            "agent_id": agent_id,
            "agent": agent_sanitized,
            "custom_variables": {
                **(custom_variables or {}),
                "to_number": to_number,
                "phone_number": to_number,
                "email": email
            },
            "to_number": to_number,
            "email": email,
            "session": None
        }
        
        # Store in Redis and memory
        try:
            redis_service.set_call_data(call_control_id, call_data, ttl=3600)
            active_telnyx_calls[call_control_id] = call_data
            logger.info(f"📦 Call data stored in Redis and memory")
        except Exception as e:
            logger.error(f"❌ Error storing call data: {e}")
            active_telnyx_calls[call_control_id] = call_data
        
        logger.info(f"📞 Webhook-triggered outbound call initiated: {call_control_id}")
        
        # CALL INITIATED WEBHOOK: Send notification when call is placed
        try:
            agent_settings_for_webhook = agent.get("settings", {}) or {}
            call_started_webhook_url = agent_settings_for_webhook.get("call_started_webhook_url")
            is_call_started_webhook_active = agent_settings_for_webhook.get("call_started_webhook_active")
            should_fire_webhook = bool(call_started_webhook_url and is_call_started_webhook_active is not False)
            
            logger.info(f"🔍 DEBUG Call Initiated Webhook (External Trigger): url='{call_started_webhook_url}', active={is_call_started_webhook_active}, should_fire={should_fire_webhook}")
            
            if should_fire_webhook:
                logger.info(f"📤 Sending call-initiated webhook to: {call_started_webhook_url}")
                
                webhook_payload = {
                    "event": "call.initiated",
                    "call_id": call_control_id,
                    "agent_id": str(agent.get("id")),
                    "agent_name": agent.get("name", "Unknown Agent"),
                    "direction": "outbound",
                    "from_number": final_from_number,
                    "to_number": to_number,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                async def send_call_initiated_webhook():
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(
                                call_started_webhook_url,
                                json=webhook_payload,
                                headers={"Content-Type": "application/json"}
                            )
                            if response.status_code >= 200 and response.status_code < 300:
                                logger.info(f"✅ Call-initiated webhook sent successfully (status={response.status_code})")
                            else:
                                logger.warning(f"⚠️ Call-initiated webhook returned status {response.status_code}: {response.text[:200]}")
                    except Exception as webhook_err:
                        logger.error(f"❌ Failed to send call-initiated webhook: {webhook_err}")
                
                asyncio.create_task(send_call_initiated_webhook())
        except Exception as webhook_err:
            logger.error(f"Error preparing call-initiated webhook: {webhook_err}")
        
        return {
            "success": True,
            "call_id": call_control_id,
            "status": "queued",
            "from_number": final_from_number,
            "to_number": to_number,
            "email": email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in webhook trigger call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/telnyx/call/outbound")
async def initiate_outbound_call(
    request: OutboundCallRequest,
    current_user: dict = Depends(get_current_user)
):
    """Initiate an outbound call via Telnyx"""
    try:
        # Get agent and verify ownership
        agent = await db.agents.find_one({"id": request.agent_id, "user_id": current_user["id"]})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get from_number
        from_number = request.from_number or "+18722778634"
        
        # Create webhook URL - use environment variable for deployment flexibility
        backend_url = os.environ.get("BACKEND_URL")
        if not backend_url:
            raise ValueError("BACKEND_URL environment variable must be set for outbound calls")
        
        # Ensure backend_url has protocol for webhook
        if not backend_url.startswith("http://") and not backend_url.startswith("https://"):
            backend_url = f"https://{backend_url}"
        
        webhook_url = f"{backend_url}/api/telnyx/webhook"
        
        # Create WebSocket streaming URL - use generic endpoint
        # Handle both with and without protocol prefix
        if backend_url.startswith("https://"):
            ws_url = backend_url.replace("https://", "wss://")
        elif backend_url.startswith("http://"):
            ws_url = backend_url.replace("http://", "ws://")
        else:
            # No protocol prefix, assume HTTPS/WSS
            ws_url = f"wss://{backend_url}"
        
        stream_url = f"{ws_url}/api/telnyx/audio-stream"
        logger.info(f"🌐 Created WebSocket stream URL: {stream_url}")
        
        # Get user's Telnyx API keys from database
        telnyx_api_key = await get_api_key(current_user["id"], "telnyx")
        telnyx_connection_id = await get_api_key(current_user["id"], "telnyx_connection_id")
        
        if not telnyx_api_key or not telnyx_connection_id:
            raise HTTPException(
                status_code=400, 
                detail="Telnyx API key and Connection ID must be configured in API Keys settings"
            )
        
        # Get voicemail detection settings
        vm_settings = agent.get("settings", {}).get("voicemail_detection", {})
        enable_amd = vm_settings.get("enabled", True) and vm_settings.get("use_telnyx_amd", True)
        amd_mode = vm_settings.get("telnyx_amd_mode", "premium")
        
        # Initiate call via Telnyx WITH streaming parameters AND AMD
        # Pass user's API keys to the service
        telnyx_service = get_telnyx_service(api_key=telnyx_api_key, connection_id=telnyx_connection_id)
        call_result = await telnyx_service.initiate_outbound_call(
            to_number=request.to_number,
            from_number=from_number,
            webhook_url=webhook_url,
            custom_variables=request.custom_variables,
            stream_url=stream_url,
            enable_amd=enable_amd,
            amd_mode=amd_mode
        )
        
        if not call_result.get("success"):
            raise HTTPException(status_code=500, detail=call_result.get("error"))
        
        call_control_id = call_result["call_control_id"]
        
        # Create call log using helper function
        await create_call_log(
            call_id=call_control_id,
            agent_id=request.agent_id,
            direction="outbound",
            from_number=from_number,
            to_number=request.to_number,
            user_id=current_user["id"]
        )

        # CALL INITIATED WEBHOOK: Send notification when call is placed
        try:
            agent_settings_for_webhook = agent.get("settings", {}) or {}
            call_started_webhook_url = agent_settings_for_webhook.get("call_started_webhook_url")
            is_call_started_webhook_active = agent_settings_for_webhook.get("call_started_webhook_active")
            should_fire_webhook = bool(call_started_webhook_url and is_call_started_webhook_active is not False)
            
            # Explicit debug logging for troubleshooting
            logger.info(f"🔍 DEBUG Call Initiated Webhook (UI Trigger): url='{call_started_webhook_url}', active={is_call_started_webhook_active}, should_fire={should_fire_webhook}")
            logger.info(f"🔍 DEBUG Agent Settings Webhook Context: {agent_settings_for_webhook}")
            
            logger.info(f"🔍 DEBUG Call Initiated Webhook: url='{call_started_webhook_url}', active={is_call_started_webhook_active}, should_fire={should_fire_webhook}")
            
            if should_fire_webhook:
                logger.info(f"📤 Sending call-initiated webhook to: {call_started_webhook_url}")
                
                webhook_payload = {
                    "event": "call.initiated",
                    "call_id": call_control_id,
                    "agent_id": str(agent.get("id")),
                    "agent_name": agent.get("name", "Unknown Agent"),
                    "direction": "outbound",
                    "from_number": from_number,
                    "to_number": request.to_number,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                async def send_call_initiated_webhook():
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(
                                call_started_webhook_url,
                                json=webhook_payload,
                                headers={"Content-Type": "application/json"}
                            )
                            if response.status_code >= 200 and response.status_code < 300:
                                logger.info(f"✅ Call-initiated webhook sent successfully (status={response.status_code})")
                            else:
                                logger.warning(f"⚠️ Call-initiated webhook returned status {response.status_code}: {response.text[:200]}")
                    except Exception as webhook_err:
                        logger.error(f"❌ Failed to send call-initiated webhook: {webhook_err}")
                
                asyncio.create_task(send_call_initiated_webhook())
        except Exception as webhook_err:
            logger.error(f"Error preparing call-initiated webhook: {webhook_err}")
        
        # Store in Redis for multi-worker access
        # Sanitize agent data to remove non-serializable fields (MongoDB ObjectId, datetime)
        agent_sanitized = {}
        for key, value in agent.items():
            if key == "_id":
                continue  # Skip MongoDB ObjectId
            # Convert datetime objects to ISO string
            if isinstance(value, datetime):
                agent_sanitized[key] = value.isoformat()
            else:
                agent_sanitized[key] = value
        
        call_data = {
            "agent_id": request.agent_id,
            "agent": agent_sanitized,
            "custom_variables": {
                **(request.custom_variables or {}),
                "to_number": request.to_number,  # Ensure to_number is always in custom_variables
                "phone_number": request.to_number,  # Alias for CRM
                "email": request.email  # Contact's email
            },
            "to_number": request.to_number,  # Also store at top level
            "email": request.email,  # Also store at top level
            "session": None
        }
        
        # Store in Redis (primary) and in-memory (fallback)
        try:
            redis_service.set_call_data(call_control_id, call_data, ttl=3600)
            active_telnyx_calls[call_control_id] = call_data  # Fallback
            logger.info(f"📦 Call data stored in Redis and memory")
        except Exception as e:
            logger.error(f"❌ Error storing call data: {e}")
            # Still store in-memory as fallback
            active_telnyx_calls[call_control_id] = call_data
            logger.info(f"⚠️ Stored in memory only (Redis failed)")
        
        logger.info(f"📞 Outbound call initiated: {call_control_id}")
        
        return {
            "success": True,
            "call_id": call_control_id,
            "status": "queued",
            "from_number": from_number,
            "to_number": request.to_number,
            "email": request.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating outbound call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.websocket("/telnyx/voice-agent-stream/{call_control_id}")
async def telnyx_voice_agent_stream(websocket: WebSocket, call_control_id: str):
    """
    WebSocket endpoint for Telnyx bidirectional RTP streaming + Deepgram Voice Agent
    This is the NEW architecture using unified STT+LLM+TTS
    """
    await websocket.accept()
    logger.info(f"🎙️ Telnyx Voice Agent WebSocket connected for call: {call_control_id}")
    
    bridge = None
    
    try:
        # Get call data
        if call_control_id not in active_telnyx_calls:
            logger.error(f"❌ Call {call_control_id} not found")
            await websocket.close(code=1000, reason="Call not found")
            return
        
        call_data = active_telnyx_calls[call_control_id]
        session = call_data.get("session")
        
        if not session:
            logger.error(f"❌ No session for call {call_control_id}")
            await websocket.close(code=1000, reason="No session")
            return
        
        # Get Deepgram API key
        deepgram_api_key = os.environ.get('DEEPGRAM_API_KEY')
        if not deepgram_api_key:
            logger.error("❌ DEEPGRAM_API_KEY not set")
            await websocket.close(code=1011, reason="Missing API key")
            return
        
        # Create and start the bridge
        from telnyx_deepgram_bridge import TelnyxDeepgramBridge
        
        bridge = TelnyxDeepgramBridge(
            telnyx_ws=websocket,
            call_control_id=call_control_id,
            session=session,
            deepgram_api_key=deepgram_api_key
        )
        
        logger.info("🌉 Starting Telnyx-Deepgram bridge...")
        await bridge.start()
        
    except Exception as e:
        logger.error(f"❌ Error in voice agent stream: {e}", exc_info=True)
    finally:
        logger.info(f"🧹 Cleaning up voice agent stream for {call_control_id}")
        
        if bridge:
            # Get conversation data before closing
            conversation_data = await bridge.stop()
            
            # Save to database
            if call_control_id in active_telnyx_calls:
                await db.call_logs.update_one(
                    {"call_id": call_control_id},
                    {"$set": {
                        "user_transcript": conversation_data.get("user_transcript", []),
                        "agent_transcript": conversation_data.get("agent_transcript", []),
                        "conversation_history": conversation_data.get("conversation_history", [])
                    }}
                )
        
        try:
            await websocket.close()
        except:
            pass


async def handle_assemblyai_streaming(websocket: WebSocket, session, call_id: str, call_control_id: str):
    """Handle streaming with AssemblyAI"""
    from assemblyai_service import AssemblyAIStreamingService
    
    agent_config = session.agent_config
    assemblyai_settings = agent_config.get("settings", {}).get("assemblyai_settings", {})
    threshold = assemblyai_settings.get("threshold", 0.0)
    disable_partial = assemblyai_settings.get("disable_partial_transcripts", False)
    # Smart Endpointing parameters
    end_of_turn_confidence = assemblyai_settings.get("end_of_turn_confidence_threshold", 0.8)
    min_silence_confident = assemblyai_settings.get("min_end_of_turn_silence_when_confident", 500)
    max_silence = assemblyai_settings.get("max_turn_silence", 2000)
    
    # Get user's AssemblyAI API key
    assemblyai_api_key = await get_api_key(session.user_id, "assemblyai")
    if not assemblyai_api_key:
        logger.error("❌ No AssemblyAI API key found for user")
        await websocket.close(code=1011, reason="AssemblyAI API key not configured")
        return
    
    logger.info(f"🔑 Using user's AssemblyAI API key (first 10 chars): {assemblyai_api_key[:10]}...")
    
    # Initialize AssemblyAI service with user's API key
    assemblyai = AssemblyAIStreamingService(api_key=assemblyai_api_key)
    connected = await assemblyai.connect(
        sample_rate=8000,
        threshold=threshold,
        disable_partial_transcripts=disable_partial,
        end_of_turn_confidence_threshold=end_of_turn_confidence,
        min_end_of_turn_silence_when_confident=min_silence_confident,
        max_turn_silence=max_silence
    )
    
    if not connected:
        logger.error("❌ Failed to connect to AssemblyAI")
        await websocket.close(code=1011, reason="AssemblyAI connection failed")
        return
    
    # Transcript accumulation buffer (same conversational logic as Deepgram)
    transcript_buffer = []
    last_transcript_time = None
    processing_task = None
    is_agent_speaking = False
    
    async def process_accumulated_transcript():
        """Process accumulated transcript after a brief delay"""
        nonlocal is_agent_speaking, transcript_buffer, last_transcript_time
        
        await asyncio.sleep(0.8)
        
        if last_transcript_time and (asyncio.get_event_loop().time() - last_transcript_time) < 0.7:
            return
        
        if not transcript_buffer:
            return
        
        full_transcript = " ".join(transcript_buffer).strip()
        transcript_buffer = []
        
        # Filter short utterances and fillers
        if len(full_transcript) < 4:
            logger.info(f"⏭️  Skipping short: '{full_transcript}'")
            return
        
        fillers = ["um", "uh", "hmm", "mhm", "yeah", "yep", "nope", "ok", "okay"]
        if full_transcript.lower() in fillers:
            logger.info(f"⏭️  Skipping filler: '{full_transcript}'")
            return
        
        logger.info(f"📝 User said: {full_transcript}")
        
        llm_start_time = time.time()
        
        # Save user transcript to database
        await db.call_logs.update_one(
            {"call_id": call_control_id},
            {"$push": {
                "transcript": {
                    "role": "user",
                    "text": full_transcript,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }}
        )
        logger.info(f"📝 Saved user transcript to database")
        
        is_agent_speaking = True
        response = await session.process_user_input(full_transcript)
        response_text = response.get("text", "")
        response_latency = response.get("latency", 0)
        llm_latency_ms = int((time.time() - llm_start_time) * 1000)  # Convert to ms
        
        logger.info(f"🤖 AI response: {response_text}")
        
        # Save agent transcript to database with FULL details
        await db.call_logs.update_one(
            {"call_id": call_control_id},
            {"$push": {
                "transcript": {
                    "role": "assistant",
                    "text": response_text,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "logs": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "info",
                    "type": "turn_complete",
                    # FULL TEXT - no truncation
                    "user_text": full_transcript,
                    "agent_text": response_text,
                    # Detailed timing metrics
                    "latency": {
                        "e2e_ms": llm_latency_ms,
                        "llm_ms": int(response_latency * 1000)
                    },
                    # Legacy summary for backwards compatibility
                    "message": f"E2E latency for this turn: {llm_latency_ms}ms (LLM: {int(response_latency * 1000)}ms) | User: '{full_transcript}' -> Agent: '{response_text}'"
                }
            }}
        )
        logger.info(f"📝 Saved assistant transcript and latency to database")
        
        # Agent config already refreshed at call start - no need to refresh again
        telnyx_service = get_telnyx_service()
        agent_config = session.agent_config
        # Helper to speak text
        async def speak_response(text):
            if text:
                # 🔥 CRITICAL FIX: Mark agent as speaking before requesting audio
                if session:
                    session.mark_agent_speaking_start()
                await telnyx_service.speak_text(call_control_id, text, agent_config=agent_config)

        # Handle different response types
        if response_type == "greeting":
             # ... existing logic ...
             pass
        elif response_type == "response":
            await speak_response(response_text)
        
        if session.should_end_call:
            logger.info("📞 Ending call...")
            await asyncio.sleep(2)
            await telnyx_service.hangup_call(call_control_id)
        
        is_agent_speaking = False
    
    # Callbacks for AssemblyAI messages
    async def on_final_transcript(text, data):
        nonlocal transcript_buffer, last_transcript_time, processing_task
        
        transcript_buffer.append(text)
        last_transcript_time = asyncio.get_event_loop().time()
        
        if processing_task and not processing_task.done():
            processing_task.cancel()
            try:
                await processing_task
            except asyncio.CancelledError:
                pass
        
        processing_task = asyncio.create_task(process_accumulated_transcript())
    
    async def forward_telnyx_to_assemblyai():
        """Forward audio from Telnyx to AssemblyAI with resampling and buffering"""
        from audio_resampler import convert_mulaw_8khz_to_pcm_16khz
        import base64
        audio_packet_count = 0
        buffer = bytearray()  # Buffer to accumulate audio chunks
        BUFFER_SIZE = 3  # Accumulate 3x 20ms chunks = 60ms before sending (optimized from 100ms)
        chunk_counter = 0
        
        try:
            while True:
                # Receive JSON text from Telnyx (same as Deepgram handler)
                message = await websocket.receive_text()
                data = json.loads(message)
                event = data.get("event")
                
                # Telnyx sends: {"event": "media", "media": {"payload": "base64..."}  }
                if event == "media" and "media" in data:
                    # Telnyx sends base64 encoded 8kHz mulaw audio (20ms chunks)
                    mulaw_data = base64.b64decode(data["media"]["payload"])
                    
                    # Convert 8kHz mulaw → 16kHz linear PCM for AssemblyAI
                    pcm_16khz = convert_mulaw_8khz_to_pcm_16khz(mulaw_data)
                    
                    # Buffer audio to combine small chunks (20ms → 100ms)
                    buffer.extend(pcm_16khz)
                    chunk_counter += 1
                    
                    # Send buffered audio every BUFFER_SIZE chunks (60ms)
                    if chunk_counter >= BUFFER_SIZE:
                        await assemblyai.send_audio(bytes(buffer))
                        audio_packet_count += 1
                        
                        if audio_packet_count == 1:
                            logger.info(f"✅ Started forwarding audio (8kHz mulaw → 16kHz PCM, buffered 60ms)")
                        if audio_packet_count % 33 == 0:  # Log every ~2 seconds (33 * 60ms)
                            logger.info(f"📤 Sent {audio_packet_count} buffered packets to AssemblyAI")
                        
                        # Clear buffer
                        buffer = bytearray()
                        chunk_counter = 0
                        
        except WebSocketDisconnect:
            logger.info(f"📞 WebSocket disconnected. Sent {audio_packet_count} total buffered packets")
        except Exception as e:
            logger.error(f"❌ Error forwarding audio to AssemblyAI: {type(e).__name__}: {e}")
    
    # Run both tasks
    try:
        await asyncio.gather(
            forward_telnyx_to_assemblyai(),
            assemblyai.receive_messages(on_final_transcript=on_final_transcript)
        )
    except Exception as e:
        logger.error(f"❌ Error in AssemblyAI streaming: {e}")
    finally:
        await assemblyai.close()


async def handle_soniox_streaming(websocket: WebSocket, session, call_id: str, call_control_id: str):
    """Handle streaming with Soniox"""
    from soniox_service import SonioxStreamingService
    from dead_air_monitor import monitor_dead_air
    
    agent_config = session.agent_config
    soniox_settings = agent_config.get("settings", {}).get("soniox_settings", {})
    
    # Extract Soniox settings
    model = soniox_settings.get("model", "stt-rt-v3")  # Updated to v3 (telephony-v3 is deprecated)
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
    
    # 🔥 COMPREHENSIVE LATENCY TRACKING - Track EVERY stage of the pipeline
    latency_tracker = {
        "user_audio_start": None,      # When user starts speaking (first audio packet with voice)
        "user_audio_end": None,        # When user stops speaking (last audio packet)
        "stt_transcript_received": None, # When Soniox gives us the transcript
        "llm_request_start": None,     # When we start LLM call
        "llm_first_token": None,       # When LLM returns first token
        "llm_complete": None,          # When LLM finishes
        "tts_request_start": None,     # When we send text to ElevenLabs
        "tts_first_chunk": None,       # When ElevenLabs returns first audio chunk
        "tts_audio_sent": None,        # When we send audio to Telnyx WebSocket
    }
    
    def log_latency_breakdown():
        """Log comprehensive latency breakdown"""
        if not latency_tracker["user_audio_end"]:
            return
        
        t0 = latency_tracker["user_audio_end"]
        breakdown = ["📊 REAL LATENCY BREAKDOWN:"]
        
        if latency_tracker["stt_transcript_received"]:
            stt_ms = int((latency_tracker["stt_transcript_received"] - t0) * 1000)
            breakdown.append(f"   STT (user done → transcript): {stt_ms}ms")
        
        if latency_tracker["llm_request_start"]:
            llm_start_ms = int((latency_tracker["llm_request_start"] - t0) * 1000)
            breakdown.append(f"   Processing → LLM start: {llm_start_ms}ms")
        
        if latency_tracker["llm_first_token"] and latency_tracker["llm_request_start"]:
            llm_ttft_ms = int((latency_tracker["llm_first_token"] - latency_tracker["llm_request_start"]) * 1000)
            breakdown.append(f"   LLM TTFT: {llm_ttft_ms}ms")
        
        if latency_tracker["tts_request_start"] and latency_tracker["llm_first_token"]:
            to_tts_ms = int((latency_tracker["tts_request_start"] - latency_tracker["llm_first_token"]) * 1000)
            breakdown.append(f"   LLM token → TTS request: {to_tts_ms}ms")
        
        if latency_tracker["tts_first_chunk"] and latency_tracker["tts_request_start"]:
            tts_ttfb_ms = int((latency_tracker["tts_first_chunk"] - latency_tracker["tts_request_start"]) * 1000)
            breakdown.append(f"   TTS TTFB (request → first audio): {tts_ttfb_ms}ms")
        
        if latency_tracker["tts_audio_sent"] and latency_tracker["tts_first_chunk"]:
            send_ms = int((latency_tracker["tts_audio_sent"] - latency_tracker["tts_first_chunk"]) * 1000)
            breakdown.append(f"   TTS chunk → Telnyx send: {send_ms}ms")
        
        if latency_tracker["tts_audio_sent"]:
            total_ms = int((latency_tracker["tts_audio_sent"] - t0) * 1000)
            breakdown.append(f"   ═══════════════════════════")
            breakdown.append(f"   TOTAL (user done → audio sent): {total_ms}ms")
            breakdown.append(f"   + Phone network latency: ~200-500ms (not measured)")
        
        for line in breakdown:
            logger.info(line)
    
    # 🚦 INTERRUPTION HANDLING: Track agent speaking state locally
    is_agent_speaking = False
    agent_generating_response = False
    current_playback_ids = set()  # Use set for easier add/remove
    call_ending = False
    
    # Also store in global state for webhook access (including session reference)
    # 🚫 RESPONSE QUEUE PREVENTION: Track current response task in call_states for nested function access
    call_states[call_control_id] = {
        "agent_generating_response": False,
        "current_playback_ids": set(),
        "session": session,  # Store session reference for dead air monitoring
        "current_response_task": None,  # Track the current LLM/TTS response generation task
        "tts_tasks": []  # Track active TTS tasks for cancellation on interruption
    }
    logger.info(f"✅ Initialized call_states for {call_control_id} with session reference")
    
    # 🔌 Store WebSocket in call_data and update persistent TTS session
    if call_control_id in active_telnyx_calls:
        active_telnyx_calls[call_control_id]["telnyx_ws"] = websocket
        logger.info(f"✅ Stored Telnyx WebSocket in call_data for audio streaming")
        
        # Update persistent TTS session with WebSocket (if it exists)
        # Note: persistent_tts_manager is imported at top of file
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
    partial_transcript = ""  # Track partial transcripts for interruption detection
    
    # Dead air prevention: Start background monitoring task
    dead_air_task = None
    
    # 🚦 Verbose/Barge-In Handling Support
    current_utterance_word_count = 0
    verbose_interruption_triggered = False
    
    async def check_in_callback(message):
        """Callback for sending check-in messages through TTS"""
        nonlocal current_playback_ids
        try:
            telnyx_service = get_telnyx_service()
            agent_config = session.agent_config
            
            settings = agent_config.get("settings", {})
            tts_provider = settings.get("tts_provider")
            
            # TTS provider is REQUIRED
            if not tts_provider:
                logger.error("❌ No TTS provider configured for agent")
                return
            
            use_websocket_tts = False
            if tts_provider == "sesame":
                use_websocket_tts = True
            elif tts_provider == "elevenlabs":
                use_websocket_tts = settings.get("elevenlabs_settings", {}).get("use_websocket_tts", False)
            
            result = await telnyx_service.speak_text(
                call_control_id,
                message,
                agent_config=agent_config,
                use_websocket_tts=use_websocket_tts
            )
            
            if isinstance(result, dict) and "playback_id" in result:
                playback_id = result["playback_id"]
                current_playback_ids.add(playback_id)
                call_states[call_control_id]["current_playback_ids"].add(playback_id)
                
                # MULTI-WORKER FIX: Also add to Redis so any worker can track playbacks
                redis_svc = redis_service
                redis_svc.add_playback_id(call_control_id, playback_id)
                
                # Calculate expected duration for check-in message (with realistic timing)
                word_count = len(message.split())
                estimated_duration = max(1.5, (word_count * 0.4) + 1.0)  # 400ms/word + 1s buffer
                
                # EXTEND the expected end time (check-ins happen during existing speech tracking)
                current_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
                new_expected_end = max(current_expected_end, time.time()) + estimated_duration
                call_states[call_control_id]["playback_expected_end_time"] = new_expected_end
                
                logger.info(f"🎬 Check-in playback ID: {playback_id} (expected duration: {estimated_duration:.1f}s)")
        except Exception as e:
            logger.error(f"Error in check-in callback: {e}")
    
    # Start dead air monitoring in background
    telnyx_svc = get_telnyx_service()
    redis_svc = redis_service
    dead_air_task = asyncio.create_task(
        monitor_dead_air(session, websocket, call_control_id, check_in_callback, telnyx_svc, redis_svc)
    )
    
    # Callback for partial transcripts (for interruption detection)
    async def on_partial_transcript(text, data):
        nonlocal partial_transcript, is_agent_speaking, agent_generating_response, current_playback_ids, current_utterance_word_count, verbose_interruption_triggered
        
        # Update partial transcript
        partial_transcript = text
        
        # Dead air prevention: Mark user as speaking when we get any transcript
        if text.strip() and not session.user_speaking:
            session.mark_user_speaking_start()
            
            # 🔥 CRITICAL FIX: Clear audio queue when user starts speaking
            # This ensures we don't have old audio blocking new responses
            # Fixes the ~3 second hidden latency caused by stale audio in the queue
            # Note: persistent_tts_manager is imported at top of file (line 41)
            try:
                persistent_tts_session = persistent_tts_manager.get_session(call_control_id)
                if persistent_tts_session:
                    await persistent_tts_session.clear_audio()
                    logger.info(f"📊 [REAL TIMING] AUDIO QUEUE CLEARED (user started speaking) for call {call_control_id}")
                else:
                    logger.warning(f"⚠️ [REAL TIMING] No TTS session found to clear for call {call_control_id}")
            except Exception as clear_err:
                logger.error(f"❌ [REAL TIMING] Failed to clear audio queue: {clear_err}")
            
            # 🔥 FIX: Mark globally that user has spoken to prevent race condition with greeting
            # This is critical for preventing "Double Speaking" (Agent Greeting + Agent Reply overlap)
            if call_control_id in active_telnyx_calls:
                active_telnyx_calls[call_control_id]["user_has_spoken"] = True
            
            # Also update Redis for cross-worker visibility
            # Use update_call_data to merge instead of overwrite (prevents data loss)
            try:
                redis_service.update_call_data(call_control_id, {"user_has_spoken": True})
            except Exception as e:
                logger.warning(f"Failed to update user_has_spoken in Redis: {e}")
        
        # DEBUG: Log ALL partials to see if they're coming through
        logger.info(f"🔍 PARTIAL TRANSCRIPT: '{text}' | Generating: {agent_generating_response}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 🚦 CALL CONTROL: Rambling User Interruption (runs even when agent is silent)
        # This check happens BEFORE the agent_interruptible block so it triggers
        # whenever the user is speaking too long, regardless of agent state.
        # ═══════════════════════════════════════════════════════════════════════════
        if text.strip() and not verbose_interruption_triggered:
            # Get global barge-in settings
            barge_in_settings = agent_config.get("settings", {}).get("barge_in_settings", {})
            
            # Check node-level override (if current node has interruption_settings)
            current_node_id = getattr(session, 'current_node_id', None)
            node_settings = None
            if current_node_id:
                flow_nodes = agent_config.get("flow", {}).get("nodes", [])
                for node in flow_nodes:
                    if str(node.get("id")) == str(current_node_id):
                        node_settings = node.get("data", {}).get("interruption_settings")
                        break
            
            # Determine if feature is enabled (node override takes precedence)
            feature_enabled = barge_in_settings.get("enable_verbose_barge_in", False)
            if node_settings is not None:
                feature_enabled = node_settings.get("enabled", feature_enabled)
            
            if feature_enabled:
                # Check cooldown to prevent rapid-fire interruptions
                last_interruption = getattr(session, 'last_interruption_time', 0)
                cooldown = getattr(session, 'interruption_cooldown', 15)
                time_since_last = time.time() - last_interruption
                
                if time_since_last >= cooldown:
                    # Get threshold (node override takes precedence)
                    threshold = barge_in_settings.get("word_count_threshold", 50)
                    if node_settings and node_settings.get("word_count_threshold"):
                        threshold = node_settings.get("word_count_threshold")
                    
                    # Count words in current transcript
                    words = text.strip().split()
                    current_count = len(words)
                    
                    if current_count >= threshold:
                        logger.info(f"🚦 VERBOSE USER DETECTED: {current_count} words (Threshold: {threshold})")
                        verbose_interruption_triggered = True
                        
                        # Route through discernment-aware method (includes LLM check)
                        asyncio.create_task(session._check_rambling_interruption(text, check_in_callback))
                else:
                    logger.debug(f"🚦 Rambling check skipped: cooldown ({time_since_last:.1f}s / {cooldown}s)")
        
        # 🚦 INTERRUPTION DETECTION: Check partial transcripts for interruptions
        # Check if agent is actively generating OR if audio is still playing
        currently_generating = agent_generating_response and call_states.get(call_control_id, {}).get("agent_generating_response", False)
        
        # 🔥 FIX: Also check if audio is expected to still be playing
        playback_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
        current_time = time.time()
        time_until_audio_done = playback_expected_end - current_time if playback_expected_end > 0 else 0
        audio_still_playing = time_until_audio_done > 0
        
        # Agent is "interruptible" if generating OR audio still playing
        agent_interruptible = currently_generating or audio_still_playing
        
        # 🛡️ CALL CONTROL PROTECTION: Skip barge-in if we're playing a Call Control interruption
        # This prevents the agent's "interrupt the rambler" audio from being cancelled by the rambler
        protected_until = getattr(session, 'interrupt_playback_protected_until', 0) if session else 0
        call_control_protected = time.time() < protected_until
        if call_control_protected:
            logger.info(f"🛡️ CALL CONTROL: Barge-in skipped - interruption audio protected ({protected_until - time.time():.1f}s left)")
            agent_interruptible = False  # Disable interruption temporarily
        
        if agent_interruptible and partial_transcript.strip():
            word_count = len(partial_transcript.strip().split())
            interrupt_reason = "during response generation" if currently_generating else f"during audio playback ({time_until_audio_done:.1f}s left)"
            logger.info(f"🚦 BARGE-IN CHECK {interrupt_reason}: {word_count} words - '{partial_transcript}'")
            
            # ECHO FILTER: Check if this matches recent agent speech (speakerphone echo)
            recent_agent_texts = call_states.get(call_control_id, {}).get("recent_agent_texts", [])
            is_echo = False
            
            if recent_agent_texts:
                import string
                transcript_lower = partial_transcript.lower().strip()
                transcript_normalized = ''.join(c for c in transcript_lower if c not in string.punctuation).strip()
                transcript_words = set(transcript_normalized.split())
                
                for agent_text in recent_agent_texts:
                    agent_lower = agent_text.lower().strip()
                    agent_normalized = ''.join(c for c in agent_lower if c not in string.punctuation).strip()
                    agent_words = set(agent_normalized.split())
                    
                    if len(agent_words) >= 2:
                        common_words = agent_words.intersection(transcript_words)
                        
                        # More aggressive echo detection:
                        # 1. Word similarity check (30% threshold - more sensitive)
                        similarity = len(common_words) / len(agent_words) if len(agent_words) > 0 else 0
                        
                        # 2. Substring match check (if transcript contains significant part of agent text)
                        transcript_in_agent = transcript_normalized in agent_normalized
                        agent_in_transcript = agent_normalized in transcript_normalized
                        
                        # 3. Check if ANY 3+ word phrase matches
                        has_phrase_match = False
                        if len(transcript_words) >= 3:
                            transcript_trigrams = set()
                            words_list = transcript_normalized.split()
                            for i in range(len(words_list) - 2):
                                trigram = ' '.join(words_list[i:i+3])
                                if trigram in agent_normalized:
                                    has_phrase_match = True
                                    break
                        
                        if similarity > 0.3 or transcript_in_agent or agent_in_transcript or has_phrase_match:
                            logger.info(f"🔇 ECHO DETECTED (similarity: {similarity:.2f}, substring: {transcript_in_agent or agent_in_transcript}, phrase: {has_phrase_match}) - Ignoring: '{partial_transcript}'")
                            is_echo = True
                            break
            
            # Only trigger interruption if >= 3 words AND not an echo
            if word_count >= 3 and not is_echo:
                # 🔥 GUARD: Prevent multiple simultaneous interrupts
                # Use a flag to ensure we only process one interrupt at a time
                interrupt_in_progress = call_states.get(call_control_id, {}).get("interrupt_in_progress", False)
                if interrupt_in_progress:
                    logger.info(f"⏳ Interrupt already in progress, skipping duplicate trigger")
                    return
                
                # Set the flag
                call_states[call_control_id]["interrupt_in_progress"] = True
                
                logger.info(f"🛑 INTERRUPTION TRIGGERED - User said {word_count} words: '{partial_transcript}'")
                logger.info(f"🛑 Stopping agent IMMEDIATELY...")
                
                # 🚫 RESPONSE QUEUE PREVENTION: Cancel the current response task
                current_response_task = call_states.get(call_control_id, {}).get("current_response_task")
                if current_response_task and not current_response_task.done():
                    logger.info(f"🛑 Cancelling in-flight response generation task")
                    current_response_task.cancel()
                
                # 🔥 CRITICAL: Cancel all in-flight TTS tasks
                tts_tasks = call_states.get(call_control_id, {}).get("tts_tasks", [])
                if tts_tasks:
                    cancelled_count = 0
                    for task in tts_tasks:
                        if not task.done():
                            task.cancel()
                            cancelled_count += 1
                    if cancelled_count > 0:
                        logger.info(f"🛑 Cancelled {cancelled_count} in-flight TTS tasks")
                    # Clear the list
                    tts_tasks.clear()
                
                # 🔥 FIRST PRIORITY: Clear WebSocket TTS audio IMMEDIATELY
                # This sends the clear event to Telnyx to flush the audio buffer
                # Note: persistent_tts_manager is imported at top of file (line 41)
                persistent_tts_session = persistent_tts_manager.get_session(call_control_id)
                if persistent_tts_session:
                    await persistent_tts_session.clear_audio()
                    persistent_tts_session.cancel_pending_sentences()
                    logger.info(f"✋ Cleared WebSocket TTS audio buffer")
                
                # Stop all active HTTP playbacks (but NOT comfort noise)
                telnyx_service = get_telnyx_service()
                comfort_noise_id = call_states.get(call_control_id, {}).get("comfort_noise_playback_id")
                
                stop_tasks = []
                for playback_id in current_playback_ids:
                    # Skip comfort noise - it should keep playing
                    if playback_id != comfort_noise_id:
                        stop_tasks.append(telnyx_service.stop_playback(call_control_id, playback_id))
                
                # Execute all stops concurrently for speed
                if stop_tasks:
                    await asyncio.gather(*stop_tasks, return_exceptions=True)
                    logger.info(f"✋ Stopped {len(stop_tasks)} HTTP playbacks (kept comfort noise)")
                
                current_playback_ids.clear()
                call_states[call_control_id]["current_playback_ids"].clear()
                
                # MULTI-WORKER FIX: Also clear Redis playbacks
                redis_svc = redis_service
                redis_svc.clear_playbacks(call_control_id)
                
                # Reset playback_expected_end_time to NOW (audio is stopped)
                call_states[call_control_id]["playback_expected_end_time"] = time.time()
                
                is_agent_speaking = False
                agent_generating_response = False
                call_states[call_control_id]["agent_generating_response"] = False
                
                # CRITICAL: Do NOT set interruption_triggered = True
                # We just stop playback and let the user's full utterance be processed normally
                
                # 🔥 Clear the interrupt-in-progress flag
                call_states[call_control_id]["interrupt_in_progress"] = False
                
                logger.info(f"✅ Agent stopped, user can continue speaking")
    
    # Callback for endpoint detection (when Soniox detects end of utterance)
    async def on_endpoint_detected():
        nonlocal accumulated_transcript, last_audio_received_time, is_agent_speaking, agent_generating_response, current_playback_ids, call_ending, stt_start_time, verbose_interruption_triggered, current_utterance_word_count, latency_tracker
        
        # 🔥 TIMING: Mark when we receive the transcript from STT
        latency_tracker["stt_transcript_received"] = time.time()
        latency_tracker["user_audio_end"] = last_audio_received_time  # Use the last audio packet time
        
        # Reset verbose tracking for next utterance
        verbose_interruption_triggered = False
        current_utterance_word_count = 0
        
        # Small delay to ensure any concurrent final transcript callback completes first
        # This is necessary because we now run callbacks as fire-and-forget tasks
        await asyncio.sleep(0.01)  # 10ms
        
        # 🚫 CANCELLATION CHECK: Exit early if this task was cancelled
        # FIXED: asyncio.current_task().cancelled() returns a boolean, doesn't raise
        current_task = asyncio.current_task()
        if current_task and current_task.cancelled():
            logger.info(f"⏹️ Endpoint processing cancelled - new user input received")
            return  # Exit gracefully instead of raising
        
        # Log STT latency
        if last_audio_received_time and latency_tracker["stt_transcript_received"]:
            stt_latency = int((latency_tracker["stt_transcript_received"] - last_audio_received_time) * 1000)
            logger.info(f"📊 [REAL TIMING] STT: User audio end → Transcript received: {stt_latency}ms")
        
        logger.info(f"🎤 Endpoint detected by Soniox - processing transcript: {accumulated_transcript}")
        
        # Dead air prevention: Mark user as stopped speaking
        session.mark_user_speaking_end()
        
        # Detect "hold on" phrases in user transcript
        if accumulated_transcript.strip():
            session.hold_on_detected = session._detect_hold_on_phrase(accumulated_transcript)
            if session.hold_on_detected:
                logger.info(f"⏸️ 'Hold on' phrase detected - using longer timeout")
            
            # Voicemail/IVR detection (runs in parallel, zero latency)
            should_disconnect, detection_type, confidence = session.voicemail_detector.analyze_transcript(
                accumulated_transcript,
                call_start_time=session.call_start_time
            )
            if should_disconnect:
                logger.warning(f"🤖 {detection_type.upper()} DETECTED ({confidence:.2f}) - Disconnecting call")
                call_ending = True
                session.should_end_call = True
                
                # Update call log with detection info
                try:
                    await db.call_logs.update_one(
                        {"call_id": call_control_id},
                        {"$set": {
                            "status": "voicemail_detected",
                            "end_reason": f"{detection_type}_detected_ai",
                            "voicemail_detection": {
                                "method": "ai_pattern_matching",
                                "detection_type": detection_type,
                                "confidence": confidence,
                                "detected_at": datetime.utcnow().isoformat()
                            },
                            "ended_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }}
                    )
                except Exception as e:
                    logger.error(f"Error updating call log for voicemail detection: {e}")
                
                # Immediately hang up
                telnyx_svc = get_telnyx_service()
                try:
                    await asyncio.sleep(0.5)  # Brief pause
                    result = await telnyx_svc.hangup_call(call_control_id)
                    logger.info(f"📞 Call hung up due to {detection_type} detection: {result}")
                except Exception as e:
                    logger.error(f"❌ Error hanging up call: {e}")
                return
            
            # Gatekeeper detection - "Press X to connect" systems
            # Instead of hanging up, send the DTMF digit to get through
            is_gatekeeper, digit_to_press = session.voicemail_detector.check_for_gatekeeper(accumulated_transcript)
            if is_gatekeeper and digit_to_press:
                logger.info(f"🚪 GATEKEEPER DETECTED - Pressing {digit_to_press} to connect...")
                telnyx_svc = get_telnyx_service()
                try:
                    # Send DTMF digit to get through the gatekeeper
                    dtmf_result = await telnyx_svc.send_dtmf(call_control_id, digit_to_press)
                    logger.info(f"📱 DTMF '{digit_to_press}' sent to bypass gatekeeper: {dtmf_result}")
                    
                    # Update call log
                    await db.call_logs.update_one(
                        {"call_id": call_control_id},
                        {"$push": {
                            "events": {
                                "type": "gatekeeper_bypass",
                                "digit_pressed": digit_to_press,
                                "transcript": accumulated_transcript[:200],
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }}
                    )
                    
                    # Mark that we've handled this gatekeeper (prevent repeated presses)
                    session.voicemail_detector.detection_made = True
                    session.voicemail_detector.detection_type = "gatekeeper_bypassed"
                    
                except Exception as e:
                    logger.error(f"❌ Error sending DTMF to bypass gatekeeper: {e}")
                
                # Don't process this transcript as normal user input
                return
        
        # CRITICAL: Reset agent speaking flag when user starts a new turn
        # This ensures interruption detection is disabled during user turns
        if is_agent_speaking:
            logger.info(f"✅ User starting new turn - resetting agent speaking flag")
            is_agent_speaking = False
            current_playback_ids.clear()
        
        # Skip processing if call is ending
        if call_ending:
            logger.info(f"⏭️  Skipping processing - call is ending")
            accumulated_transcript = ""
            return
        
        # ⏱️  Calculate STT latency (last audio → endpoint detection)
        stt_end_time = time.time()
        stt_latency_ms = 0
        if last_audio_received_time:
            stt_latency_ms = int((stt_end_time - last_audio_received_time) * 1000)
            logger.info(f"⏱️ [TIMING] STT_START: User last audio packet received")
            logger.info(f"⏱️ [TIMING] STT_END: Endpoint detected at T+{stt_latency_ms}ms")
            logger.info(f"⏱️ [TIMING] STT_LATENCY: {stt_latency_ms}ms (Soniox model: {model})")
        else:
            logger.warning(f"⏱️ [TIMING] STT_LATENCY: Unknown (last_audio_received_time not set)")
        
        # Process with LLM
        if accumulated_transcript.strip():
            try:
                llm_start_time = time.time()
                first_sentence_played = False
                full_response_text = ""
                
                # 🔥 TIMING: Mark LLM request start
                latency_tracker["llm_request_start"] = llm_start_time
                
                # Log when user stopped speaking
                logger.info(f"⏱️  USER STOPPED SPEAKING at T=0ms")
                logger.info(f"📊 [REAL TIMING] Processing start: {int((llm_start_time - latency_tracker.get('user_audio_end', llm_start_time)) * 1000)}ms after user audio end")
                
                # 🚦 CRITICAL: Set flags BEFORE LLM starts (enables interruption detection)
                is_agent_speaking = True
                agent_generating_response = True
                call_states[call_control_id]["agent_generating_response"] = True
                logger.info(f"🎙️ Agent generating response - interruption detection active")
                
                # Dead air prevention: Mark agent as speaking
                session.mark_agent_speaking_start()
                
                # ⏱️  Track TTS start
                tts_start_time = None
                
                # Real-time streaming: Start TTS as sentences arrive
                sentence_queue = []
                tts_tasks = []  # Track TTS generation tasks
                first_tts_started = False
                
                # 🔥 Initialize TTS tasks in call_states for interruption handling
                call_states[call_control_id]["tts_tasks"] = tts_tasks
                
                # Stream callback: Generate TTS IMMEDIATELY as sentences arrive
                async def stream_sentence_to_tts(sentence):
                    # 🔥 CRITICAL FIX: Mark agent as speaking IMMEDIATELY when we have a sentence to stream
                    # This acts as the "Audio-Driven" failsafe. If we are streaming, we are speaking.
                    session.mark_agent_speaking_start()
                    
                    # 🔥 FIX B: Mark that AI has responded to user input
                    # This tells silence timeout logic that we are NOT silent, even if user_has_spoken was set prematurely
                    if call_control_id in active_telnyx_calls:
                        active_telnyx_calls[call_control_id]["ai_has_responded"] = True
                    redis_service.update_call_data(call_control_id, {"ai_has_responded": True})
                    
                    # Note: persistent_tts_manager is imported at top of file (line 41)
                    # Using closure to access the global import
                    tts_manager = persistent_tts_manager
                    
                    nonlocal current_playback_ids, first_sentence_played, full_response_text, tts_start_time
                    nonlocal first_tts_started, tts_tasks, sentence_queue
                    
                    # NOTE: interrupt flag is reset before process_user_input() is called,
                    # so we don't need to check it here. The check in stream_sentence() handles mid-response interruptions.
                    
                    if not tts_start_time:
                        tts_start_time = time.time()
                    
                    full_response_text += sentence + " "
                    sentence_queue.append(sentence)
                    logger.info(f"📤 Sentence arrived from LLM: {sentence[:50]}...")
                    
                    # ⏱️ [TIMING] First sentence arrival from LLM
                    if len(sentence_queue) == 1:
                        ttfs_ms = int((time.time() - stt_end_time) * 1000)
                        logger.info(f"⏱️ [TIMING] TTFS (Time To First Sentence): {ttfs_ms}ms")
                    
                    # 🚀 START TTS GENERATION IMMEDIATELY (don't wait for LLM to finish!)
                    if not first_tts_started:
                        # First sentence: start immediately
                        first_tts_started = True
                        logger.info(f"⚡ Starting REAL-TIME TTS for first sentence")
                    
                    # Check if persistent TTS is enabled for this call
                    # In multi-worker environments, the webhook-created session won't be visible here
                    # So we try once, and if not found, immediately create on-demand
                    persistent_tts_session = tts_manager.get_session(call_control_id)
                    
                    # 🚀 ON-DEMAND SESSION CREATION: Create immediately if not found
                    # This handles multi-worker environments where webhook runs on different worker
                    if not persistent_tts_session:
                        agent_config = session.agent_config
                        agent_settings = agent_config.get("settings", {})
                        tts_provider = agent_settings.get("tts_provider")
                        use_persistent_tts = agent_settings.get("elevenlabs_settings", {}).get("use_persistent_tts", True)
                        
                        if tts_provider == "elevenlabs" and use_persistent_tts:
                            try:
                                logger.info(f"⚡ ON-DEMAND: Creating persistent TTS session (multi-worker mode)")
                                
                                # Get ElevenLabs API key
                                elevenlabs_api_key = await session.get_api_key("elevenlabs")
                                
                                if elevenlabs_api_key:
                                    # Get voice settings
                                    elevenlabs_settings = agent_settings.get("elevenlabs_settings", {})
                                    voice_id = elevenlabs_settings.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
                                    model_id = elevenlabs_settings.get("model", "eleven_flash_v2_5")
                                    
                                    # Get telnyx service
                                    telnyx_api_key = await session.get_api_key("telnyx")
                                    telnyx_connection_id = await session.get_api_key("telnyx_connection_id")
                                    telnyx_svc = get_telnyx_service(api_key=telnyx_api_key, connection_id=telnyx_connection_id)
                                    
                                    # 🔌 CRITICAL: Use WebSocket from closure (the Telnyx websocket parameter)
                                    # This is the actual websocket connection from handle_soniox_streaming
                                    logger.info(f"✅ ON-DEMAND: Using Telnyx WebSocket from closure for streaming audio")
                                    
                                    # Create persistent TTS session on-demand
                                    persistent_tts_session = await tts_manager.create_session(
                                        call_control_id=call_control_id,
                                        api_key=elevenlabs_api_key,
                                        voice_id=voice_id,
                                        model_id=model_id,
                                        telnyx_service=telnyx_svc,
                                        agent_config=agent_config,
                                        telnyx_ws=websocket  # Use websocket from outer function closure
                                    )
                                    
                                    if persistent_tts_session:
                                        logger.info(f"✅ ON-DEMAND: Persistent TTS session created successfully!")
                                    else:
                                        logger.warning(f"⚠️ ON-DEMAND: Failed to create persistent TTS session")
                                else:
                                    logger.warning(f"⚠️ ON-DEMAND: No ElevenLabs API key found")
                            except Exception as e:
                                logger.error(f"❌ ON-DEMAND: Error creating persistent TTS session: {e}")
                    
                    logger.info(f"🔍 Persistent TTS lookup: call_id={call_control_id[:20]}..., session={'FOUND' if persistent_tts_session else 'NOT FOUND'}")
                    
                    if persistent_tts_session:
                        # 🚀 USE PERSISTENT TTS WEBSOCKET - Streams immediately!
                        is_first = len(sentence_queue) == 1
                        is_last = False  # Will be set on last sentence
                        
                        logger.info(f"🚀 Streaming sentence #{len(sentence_queue)} via persistent WebSocket")
                        
                        # Mark agent as speaking (the actual duration will be set by persistent_tts_service
                        # when it knows the real audio length after TTS generation)
                        call_states[call_control_id]["agent_last_spoke_time"] = time.time()
                        
                        # Stream sentence immediately (non-blocking, queued for playback)
                        # Get current voice ID from agent config for dynamic voice updates
                        current_voice_id = session.agent_config.get("settings", {}).get("elevenlabs_settings", {}).get("voice_id")
                        tts_task = asyncio.create_task(
                            persistent_tts_session.stream_sentence(sentence, is_first=is_first, is_last=is_last, current_voice_id=current_voice_id)
                        )
                        tts_tasks.append(tts_task)
                    else:
                        # Fallback to original REST API method
                        logger.info(f"🔄 Using REST API fallback (no persistent session)")
                        agent_config = session.agent_config
                        tts_task = asyncio.create_task(generate_tts_audio(sentence, agent_config))
                        tts_tasks.append(tts_task)
                    
                    tts_ready_time = int((time.time() - tts_start_time) * 1000)
                    logger.info(f"🎵 TTS task #{len(tts_tasks)} started at +{tts_ready_time}ms")
                    
                    # ⏱️ [TIMING] First TTS task creation
                    if len(tts_tasks) == 1:
                        ttft_tts_ms = int((time.time() - stt_end_time) * 1000)
                        logger.info(f"⏱️ [TIMING] TTFT_TTS (First TTS Task Started): {ttft_tts_ms}ms")
                
                # Function to play a single sentence (assumes audio is already generated)
                async def play_sentence(sentence, is_first=False):
                    nonlocal current_playback_ids, first_sentence_played
                    
                    telnyx_service = get_telnyx_service()
                    agent_config = session.agent_config
                    
                    # Check if WebSocket TTS is enabled (check provider-specific settings)
                    settings = agent_config.get("settings", {})
                    tts_provider = settings.get("tts_provider")
                    
                    # TTS provider is REQUIRED
                    if not tts_provider:
                        logger.error("❌ No TTS provider configured for agent")
                        return
                    
                    if tts_provider == "sesame":
                        # For Sesame, always use WebSocket streaming
                        use_websocket_tts = True
                    elif tts_provider == "elevenlabs":
                        # For ElevenLabs, check the setting
                        use_websocket_tts = settings.get("elevenlabs_settings", {}).get("use_websocket_tts", False)
                    else:
                        use_websocket_tts = False
                    
                    # Play the sentence (this returns playback_id)
                    try:
                        result = await telnyx_service.speak_text(
                            call_control_id, 
                            sentence, 
                            agent_config=agent_config,
                            use_websocket_tts=use_websocket_tts
                        )
                        # Track playback ID if available (in both local and global state)
                        if isinstance(result, dict) and "playback_id" in result:
                            playback_id = result["playback_id"]
                            current_playback_ids.add(playback_id)
                            call_states[call_control_id]["current_playback_ids"].add(playback_id)
                            
                            # MULTI-WORKER FIX: Also add to Redis
                            redis_svc = redis_service
                            redis_svc.add_playback_id(call_control_id, playback_id)
                            
                            # 🔥 FIX: Calculate expected duration with realistic timing
                            word_count = len(sentence.split())
                            estimated_duration = max(1.5, (word_count * 0.4) + 1.0)  # 400ms/word + 1s buffer
                            
                            # 🔥 CRITICAL FIX: EXTEND the expected end time instead of overwriting
                            current_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
                            new_expected_end = max(current_expected_end, time.time()) + estimated_duration
                            call_states[call_control_id]["playback_expected_end_time"] = new_expected_end
                            time_until_end = new_expected_end - time.time()
                            
                            logger.info(f"🎬 Tracking playback ID: {playback_id} (+{estimated_duration:.1f}s, total: {time_until_end:.1f}s from now)")
                        
                        if is_first and not first_sentence_played:
                            first_sentence_played = True
                            # Calculate TTFT + TTS for first sentence
                            first_audio_ms = int((time.time() - llm_start_time) * 1000)
                            logger.info(f"⏱️  FIRST AUDIO: {first_audio_ms}ms (LLM TTFT + TTS)")
                            
                        return result
                    except Exception as e:
                        logger.error(f"Error playing sentence: {e}")
                        return None
                
                # Save user transcript to database
                await db.call_logs.update_one(
                    {"call_id": call_control_id},
                    {"$push": {
                        "transcript": {
                            "role": "user",
                            "text": accumulated_transcript,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }}
                )
                logger.info(f"📝 Saved user transcript to database")
                
                # 🚫 CANCELLATION CHECK before expensive LLM call
                current_response_task = call_states.get(call_control_id, {}).get("current_response_task")
                if current_response_task and current_response_task.cancelled():
                    logger.info(f"⏹️ Response task cancelled before LLM - aborting")
                    accumulated_transcript = ""
                    return
                
                # 🔄 CRITICAL: Reset TTS interrupt flag before generating new response
                # This ensures we can speak again after an interruption
                # Note: persistent_tts_manager is imported at top of file (line 41)
                tts_session = persistent_tts_manager.get_session(call_control_id)
                if tts_session and tts_session.interrupted:
                    tts_session.reset_interrupt_flag()
                    logger.info(f"🔄 Reset TTS interrupt flag before new response")
                
                # 🔥 FIX: Mark generation as NOT complete to hold floor during multi-sentence response
                # This prevents "FLOOR RELEASED" from firing between sentences
                if tts_session:
                    tts_session.generation_complete = False
                
                # 🔥 FIX: Capture and clear accumulated_transcript BEFORE processing to prevent race condition
                # Without this, new user speech during agent response would accumulate with old transcript,
                # causing 1-2 word utterances to incorrectly trigger 3+ word interruption detection
                user_input_for_processing = accumulated_transcript
                accumulated_transcript = ""  # Clear immediately so new speech doesn't pile up
                
                # Process with streaming (TTS generation happens in parallel!)
                response = await session.process_user_input(user_input_for_processing, stream_callback=stream_sentence_to_tts)
                
                # 🚫 CANCELLATION CHECK after LLM returns (before TTS playback)
                current_response_task = call_states.get(call_control_id, {}).get("current_response_task")
                if current_response_task and current_response_task.cancelled():
                    logger.info(f"⏹️ Response task cancelled after LLM - stopping before TTS playback")
                    # Clear any partial TTS that was queued
                    sentence_queue.clear()
                    for task in tts_tasks:
                        task.cancel()
                    accumulated_transcript = ""
                    return
                
                response_text = response.get("text", "") if isinstance(response, dict) else (response or "")
                response_latency = response.get("latency", 0) if isinstance(response, dict) else 0
                llm_latency_ms = int((time.time() - llm_start_time) * 1000)
                
                logger.info(f"✅ LLM finished in {llm_latency_ms}ms, TTS tasks already running in background")
                
                # 🚀 STREAMING PLAYBACK: Play chunks as they complete!
                if sentence_queue and tts_tasks:
                    telnyx_service = get_telnyx_service()
                    agent_config = session.agent_config
                    
                    logger.info(f"🎵 Streaming {len(tts_tasks)} TTS chunks as they complete...")
                    
                    # Helper function to save and play audio
                    async def save_and_play(sentence, audio_bytes, sentence_num, total_chunks):
                        import hashlib
                        
                        tts_provider = agent_config.get('settings', {}).get('tts_provider', 'unknown')
                        combined_string = f"{tts_provider}_{sentence}"
                        audio_hash = hashlib.md5(combined_string.encode()).hexdigest()
                        
                        audio_filename = f"tts_{tts_provider}_{audio_hash}.mp3"
                        audio_path = f"/tmp/{audio_filename}"
                        
                        # Save audio
                        with open(audio_path, 'wb') as f:
                            f.write(audio_bytes)
                        
                        backend_url = os.environ.get('BACKEND_URL')
                        if not backend_url:
                            raise ValueError("BACKEND_URL environment variable must be set")
                        audio_url = f"{backend_url}/api/tts-audio/{audio_filename}"
                        
                        playback_start = time.time()
                        logger.info(f"⏱️ [TIMING] TELNYX_PLAY_CALL_START: Calling play_audio_url API")
                        
                        # 🔥 CRITICAL FIX: Mark agent as speaking before playing URL
                        session.mark_agent_speaking_start()
                        
                        result = await telnyx_service.play_audio_url(call_control_id, audio_url)
                        playback_time = int((time.time() - playback_start) * 1000)
                        logger.info(f"⏱️ [TIMING] TELNYX_PLAY_CALL_COMPLETE: {playback_time}ms (API call only, audio may not be playing yet)")
                        
                        if isinstance(result, dict) and "playback_id" in result:
                            playback_id = result["playback_id"]
                            current_playback_ids.add(playback_id)
                            call_states[call_control_id]["current_playback_ids"].add(playback_id)
                            
                            # MULTI-WORKER FIX: Also add to Redis
                            redis_svc = redis_service
                            redis_svc.add_playback_id(call_control_id, playback_id)
                            
                            # Calculate expected audio duration based on text length
                            # 🔥 FIX: Use more realistic duration estimation
                            # Real-world observation: TTS + network + playback takes ~0.4-0.5s/word
                            word_count = len(sentence.split())
                            estimated_duration = max(1.5, (word_count * 0.4) + 1.0)  # words * 400ms + 1s buffer
                            
                            # 🔥 CRITICAL FIX: EXTEND the expected end time instead of overwriting
                            # Previous bug: Each sentence overwrote the previous, causing premature check-ins
                            current_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
                            new_expected_end = max(current_expected_end, time.time()) + estimated_duration
                            call_states[call_control_id]["playback_expected_end_time"] = new_expected_end
                            
                            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            time_until_expected_end = new_expected_end - time.time()
                            logger.info(f"⏱️ [{timestamp_str}] 🔊 AGENT AUDIO PLAYBACK STARTED (chunk {sentence_num}/{total_chunks}, API call: {playback_time}ms, +{estimated_duration:.1f}s, total expected: {time_until_expected_end:.1f}s from now)")
                            
                            # 🚀 Track when agent last spoke (for filtering logic)
                            call_states[call_control_id]["agent_last_spoke_time"] = time.time()
                            logger.info(f"⏱️ [TIMING] AGENT_LAST_SPOKE: Recorded timestamp for filtering logic")
                            
                            # Mark agent as speaking when FIRST chunk starts
                            if sentence_num == 1:
                                session.mark_agent_speaking_start()
                                logger.info(f"🔊 MARKED AGENT AS SPEAKING (first audio chunk started)")
                        
                        return result
                    
                    # Check if using persistent TTS
                    persistent_tts_session = persistent_tts_manager.get_session(call_control_id)
                    
                    try:
                        if persistent_tts_session:
                            # 🚀 PERSISTENT TTS: Audio already streaming! Just wait for tasks to complete
                            logger.info(f"🚀 Persistent TTS: Audio already streaming in background!")
                            logger.info(f"   {len(sentence_queue)} sentences queued and playing seamlessly")
                            
                            # Wait for streaming tasks to complete
                            await asyncio.gather(*tts_tasks, return_exceptions=True)
                            logger.info(f"✅ All {len(sentence_queue)} persistent TTS streams completed")
                            
                            # 🚨 CRITICAL FIX: Reset agent_generating_response after TTS completes
                            # Without this, barge-in check incorrectly triggers on normal user responses
                            agent_generating_response = False
                            call_states[call_control_id]["agent_generating_response"] = False
                            logger.info(f"✅ Agent generation complete (persistent TTS) - response window closed")
                            
                            # 🔥 FIX: Mark generation complete so floor can release
                            # Now the reset_speaking_after_playback timer knows no more sentences are coming
                            if persistent_tts_session:
                                persistent_tts_session.generation_complete = True
                            
                            # Mark agent as speaking (first audio already started)
                            if not first_sentence_played:
                                first_sentence_played = True
                                first_audio_ms = int((time.time() - llm_start_time) * 1000)
                                logger.info(f"⏱️  FIRST AUDIO STARTED: {first_audio_ms}ms from user stop 🚀")
                                session.mark_agent_speaking_start()
                        
                        else:
                            # 🚀 PARALLEL TTS + QUEUED PLAYBACK: Generate TTS in parallel, queue playbacks immediately
                            # This eliminates gaps between sentences by pre-queuing all audio to Telnyx
                            logger.info(f"🚀 PARALLEL PLAYBACK: {len(tts_tasks)} TTS tasks, queueing to Telnyx as ready...")
                            logger.info(f"   Sentence queue: {[s[:30] + '...' for s in sentence_queue]}")
                            
                            # Collect playback tasks to run concurrently
                            playback_tasks = []
                            
                            # Process each TTS task as it completes
                            for i, (tts_task, sentence) in enumerate(zip(tts_tasks, sentence_queue), 1):
                                try:
                                    logger.info(f"⏳ Waiting for TTS task {i}/{len(tts_tasks)} to complete...")
                                    audio_bytes = await tts_task
                                    
                                    if isinstance(audio_bytes, Exception) or audio_bytes is None:
                                        logger.error(f"Error generating TTS for sentence {i}: {audio_bytes}")
                                        continue
                                    
                                    if not audio_bytes or len(audio_bytes) < 1000:
                                        logger.warning(f"Invalid audio for sentence {i} ({len(audio_bytes) if audio_bytes else 0} bytes), skipping")
                                        continue
                                    
                                    logger.info(f"✅ TTS task {i} complete ({len(audio_bytes)} bytes), queueing to Telnyx...")
                                    
                                    # Queue playback immediately (don't await - let Telnyx queue them)
                                    # This ensures minimal gap between sentences
                                    playback_task = asyncio.create_task(
                                        save_and_play(sentence, audio_bytes, i, len(sentence_queue))
                                    )
                                    playback_tasks.append(playback_task)
                                    
                                    # Log first audio timing when first task is queued
                                    if i == 1 and not first_sentence_played:
                                        first_sentence_played = True
                                        first_audio_ms = int((time.time() - llm_start_time) * 1000)
                                        logger.info(f"⏱️  FIRST AUDIO QUEUED: {first_audio_ms}ms from user stop 🚀")
                                    
                                except Exception as e:
                                    logger.error(f"Error preparing sentence {i}: {e}")
                            
                            # Wait for all playback API calls to complete (they queue in Telnyx)
                            if playback_tasks:
                                await asyncio.gather(*playback_tasks, return_exceptions=True)
                            
                            logger.info(f"✅ All {len(sentence_queue)} chunks queued to Telnyx for seamless playback")
                    
                    except Exception as e:
                        logger.error(f"Error in streaming playback: {e}")
                
                # 🚨 CRITICAL FIX: Reset agent_generating_response after TTS completes
                # Without this, the barge-in check incorrectly triggers on normal user responses
                # because it thinks the agent is still generating/speaking
                agent_generating_response = False
                call_states[call_control_id]["agent_generating_response"] = False
                logger.info(f"✅ Agent generation complete - response window closed")
                
                # ⏱️  Calculate total pause and TTS latency
                tts_latency_ms = int((time.time() - tts_start_time) * 1000) if tts_start_time else 0
                total_pause_ms = int((time.time() - stt_end_time) * 1000)
                
                # Get agent configuration for detailed logging
                agent_settings = session.agent_config.get("settings", {})
                stt_provider = agent_settings.get("stt_provider", "unknown")
                llm_provider = agent_settings.get("llm_provider", "unknown")
                llm_model = session.agent_config.get("model", "unknown")
                tts_provider = agent_settings.get("tts_provider", "unknown")
                use_websocket_tts = agent_settings.get("elevenlabs_settings", {}).get("use_persistent_tts", False)
                
                # ⏱️  Enhanced E2E latency summary
                logger.info(f"⏱️  ═══════════════════════════════════════════════")
                logger.info(f"⏱️  [TIMING] ==== E2E LATENCY SUMMARY ====")
                logger.info(f"⏱️  [TIMING] STT: {stt_latency_ms}ms (provider: {stt_provider}, model: {model if 'model' in locals() else 'unknown'})")
                logger.info(f"⏱️  [TIMING] LLM_TOTAL: {llm_latency_ms}ms (provider: {llm_provider}, model: {llm_model})")
                logger.info(f"⏱️  [TIMING] TTS_TOTAL: {tts_latency_ms}ms (provider: {tts_provider}, websocket: {use_websocket_tts})")
                logger.info(f"⏱️  [TIMING] E2E_TOTAL: {total_pause_ms}ms (user stopped → play_audio_url called)")
                logger.info(f"⏱️  [TIMING] ⚠️ NOTE: E2E_TOTAL does not include:")
                logger.info(f"⏱️  [TIMING]   - Telnyx processing time (~50-200ms)")
                logger.info(f"⏱️  [TIMING]   - Network latency to user's phone (~50-150ms)")
                logger.info(f"⏱️  [TIMING]   - Phone audio buffering (~50-200ms)")
                logger.info(f"⏱️  [TIMING]   - TOTAL MISSING: ~150-550ms typically")
                logger.info(f"⏱️  [TIMING]   - REAL USER LATENCY: {total_pause_ms + 300}ms estimated")
                logger.info(f"⏱️  [TIMING] RESPONSE_TEXT: {len(response_text)} chars, {len(sentence_queue)} sentences")
                logger.info(f"⏱️  [TIMING] USER_INPUT: '{user_input_for_processing[:60]}...'")
                logger.info(f"⏱️  [TIMING] AI_RESPONSE: '{response_text[:60]}...'")
                logger.info(f"⏱️  [TIMING] ==========================")
                logger.info(f"⏱️  ═══════════════════════════════════════════════")
                
                # Save assistant transcript to database
                # Extract node info from response for QC analysis
                node_id = response.get("node_id", "")
                node_label = response.get("node_label", "Unknown")
                transition_time_ms = response.get("transition_time_ms", 0)
                kb_time_ms = response.get("kb_time_ms", 0)
                
                # Calculate TRUE "dead air" latency (time user hears silence):
                # Dead air = STT processing + LLM processing + first TTS chunk time
                # This is different from total TTS time which includes full audio generation
                # For TTFS (Time To First Speech), we want: STT end → first audio chunk sent
                ttfs_ms = stt_latency_ms + llm_latency_ms  # Time until we start generating audio
                # Add a small estimate for first TTS chunk (typically ~200-500ms of a 2+ second response)
                # The user doesn't wait for all TTS to complete, just for the first chunk
                first_chunk_estimate_ms = min(tts_latency_ms, 500) if tts_latency_ms > 0 else 0
                dead_air_ms = ttfs_ms + first_chunk_estimate_ms
                
                await db.call_logs.update_one(
                    {"call_id": call_control_id},
                    {"$push": {
                        "transcript": {
                            "role": "assistant",
                            "text": response_text,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        "logs": {
                            "timestamp": datetime.utcnow().isoformat(),
                            "level": "info",
                            "type": "turn_complete",
                            "turn_number": len(session.messages) if hasattr(session, 'messages') else 0,
                            # Node identification for QC reports
                            "node_id": node_id,
                            "node_label": node_label,
                            # FULL TEXT - no truncation
                            "user_text": user_input_for_processing,
                            "agent_text": response_text,
                            # Detailed timing metrics
                            "latency": {
                                "e2e_ms": llm_latency_ms,  # Legacy: time from STT end to LLM complete
                                "llm_ms": int(response_latency * 1000),  # Pure LLM API time
                                "stt_ms": stt_latency_ms,
                                "tts_ms": tts_latency_ms,  # Total TTS generation time
                                "total_pause_ms": total_pause_ms,
                                # NEW: Accurate timing for QC analysis
                                "ttfs_ms": ttfs_ms,  # Time To First Speech (STT + LLM)
                                "dead_air_ms": dead_air_ms,  # Actual silence heard by user
                                "transition_ms": transition_time_ms,  # Node transition evaluation
                                "kb_ms": kb_time_ms  # Knowledge base retrieval
                            },
                            # Legacy summary for backwards compatibility
                            "message": f"E2E latency for this turn: {llm_latency_ms}ms (LLM: {int(response_latency * 1000)}ms) | User: '{user_input_for_processing}' -> Agent: '{response_text}'"
                        }
                    }}
                )
                
                # Save detailed latency metrics to database
                await db.call_logs.update_one(
                    {"call_id": call_control_id},
                    {"$push": {
                        "logs": {
                            "timestamp": datetime.utcnow().isoformat(),
                            "level": "metrics",
                            "type": "latency_breakdown",
                            "node_id": node_id,
                            "node_label": node_label,
                            "latency": {
                                "total_ms": total_pause_ms,
                                "stt_ms": stt_latency_ms,
                                "llm_ms": llm_latency_ms,
                                "tts_ms": tts_latency_ms,
                                "ttfs_ms": ttfs_ms,
                                "dead_air_ms": dead_air_ms,
                                "transition_ms": transition_time_ms,
                                "kb_ms": kb_time_ms
                            },
                            "message": f"LATENCY BREAKDOWN - Node: {node_label} | DEAD_AIR: {dead_air_ms}ms | STT: {stt_latency_ms}ms | LLM: {llm_latency_ms}ms | TTS: {tts_latency_ms}ms | Transition: {transition_time_ms}ms | KB: {kb_time_ms}ms"
                        }
                    }}
                )
                
                logger.info(f"📝 Saved assistant transcript and latency to database (Node: {node_label}, Dead Air: {dead_air_ms}ms)")
                
                # Interruption window stays open until Telnyx playback.ended webhooks arrive
                # The webhooks will call mark_agent_speaking_end() when ALL audio finishes
                logger.info(f"🔊 Agent finished generating, {len(current_playback_ids)} playbacks active - waiting for webhooks to close window and start silence tracking")
                
                # Check if we should end call (flow ending node or dead air max checks)
                logger.info(f"🔍 END CALL CHECK: should_end_call={session.should_end_call}, max_checkins={session.should_end_call_max_checkins()}, max_duration={session.should_end_call_max_duration()}")
                if session.should_end_call or session.should_end_call_max_checkins() or session.should_end_call_max_duration():
                    call_ending = True
                    
                    # Determine goodbye message
                    if session.should_end_call_max_checkins():
                        logger.info("📞 Ending call - max check-ins reached")
                    elif session.should_end_call_max_duration():
                        logger.info("📞 Ending call - max duration reached")
                    else:
                        logger.info("📞 Ending call - flow ending node")
                    
                    logger.info("📞 Ending call now - waiting for goodbye audio to complete...")
                    await asyncio.sleep(3.5)  # Wait longer to ensure audio fully plays
                    telnyx_svc = get_telnyx_service()
                    logger.info("📞 Now hanging up call...")
                    result = await telnyx_svc.hangup_call(call_control_id)
                    logger.info(f"📞 Hangup result: {result}")
                
                # Reset for next turn
                accumulated_transcript = ""
            
            except Exception as e:
                logger.error(f"❌ Error processing transcript: {e}")
                accumulated_transcript = ""
                is_agent_speaking = False
    
    # Callback for final transcript
    async def on_final_transcript(text, data):
        nonlocal accumulated_transcript, last_audio_received_time, stt_start_time, is_agent_speaking, agent_generating_response, current_playback_ids, call_ending
        
        # ⏱️ TIMESTAMP: Final transcript received from STT
        transcript_received_time = time.time()
        import datetime
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Calculate STT latency
        stt_end_time = time.time()
        stt_latency_ms = int((stt_end_time - last_audio_received_time) * 1000) if last_audio_received_time else 0
        
        # 🔥 FIX C: Latency protection - Wait for greeting to start playing
        # If greeting is in-flight (network delay), wait up to 2s for audio to start.
        # This prevents race conditions where user speaks before audio starts, causing node skips.
        # fetch current state
        retry_redis = redis_service.get_call_data(call_control_id) or {}
        check_mem = active_telnyx_calls.get(call_control_id, {})
        greeting_in_flight = retry_redis.get("greeting_in_flight") or check_mem.get("greeting_in_flight")
        
        if greeting_in_flight:
            logger.info(f"🛡️ Greeting IN-FLIGHT - Pausing processing for '{text}'...")
            wait_start = time.time()
            flag_cleared = False
            
            # Poll for flag clear (max 2s)
            for _ in range(20):
                await asyncio.sleep(0.1)
                latest_redis = redis_service.get_call_data(call_control_id) or {}
                latest_mem = active_telnyx_calls.get(call_control_id, {})
                if not latest_redis.get("greeting_in_flight") and not latest_mem.get("greeting_in_flight"):
                    flag_cleared = True
                    break
            
            wait_dur = (time.time() - wait_start) * 1000
            if flag_cleared:
                logger.info(f"✅ Greeting delivered! Clean hand-off to user input after {wait_dur:.0f}ms")
            else:
                logger.warning(f"⚠️ Greeting in-flight TIMEOUT ({wait_dur:.0f}ms) - Proceeding anyway")
            
            # Clear flag to be safe
            if call_control_id in active_telnyx_calls:
                active_telnyx_calls[call_control_id]["greeting_in_flight"] = False
            redis_service.update_call_data(call_control_id, {"greeting_in_flight": False})
        
        logger.info(f"⏱️ [{timestamp_str}] 📝 FINAL TRANSCRIPT RECEIVED: '{text}'")
        logger.info(f"⏱️ [{timestamp_str}] STT endpoint detection latency: {stt_latency_ms}ms")
        logger.info(f"⏱️ [{timestamp_str}] 🎤 USER STOPPED SPEAKING - Beginning processing pipeline")
        
        # 🔥 ATTEMPT 12: Record when user spoke for pre-audio-delivery detection
        user_spoke_time = time.time()
        logger.info(f"⏱️ User spoke at {user_spoke_time}")
        
        # Mark that user has spoken (for aiSpeaksAfterSilence feature)
        if text.strip():
            if call_control_id in active_telnyx_calls:
                active_telnyx_calls[call_control_id]["user_has_spoken"] = True
                active_telnyx_calls[call_control_id]["silence_greeting_triggered"] = True  # Prevent silence greeting
            # 🔥 ATTEMPT 12: Store user_spoke_at in call_states for pre-audio-delivery detection
            if call_control_id in call_states:
                call_states[call_control_id]["user_spoke_at"] = user_spoke_time
            redis_service.set_call_data(call_control_id, {
                "user_has_spoken": True,
                "silence_greeting_triggered": True  # Prevent silence greeting from also firing
            })
            logger.info(f"👤 User has spoken - aiSpeaksAfterSilence timer cancelled if pending")
        
        accumulated_transcript += text
        
        # 🚦 INTERRUPTION DETECTION: Check if agent audio is actively playing
        # For WebSocket streaming, use tts_is_speaking as primary source of truth
        # For HTTP playback, use current_playback_ids as backup
        # Note: persistent_tts_manager is imported at top of file (line 41)
        tts_session = persistent_tts_manager.get_session(call_control_id) if call_control_id else None
        tts_is_speaking = tts_session.is_speaking if tts_session else False
        
        has_active_playbacks = len(current_playback_ids) > 0
        word_count = len(accumulated_transcript.strip().split())
        
        # Also check playback_expected_end_time
        playback_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
        current_time = time.time()
        time_until_audio_done = playback_expected_end - current_time if playback_expected_end > 0 else 0
        
        # 🔥 Agent is speaking if:
        # 1. TTS session says so (WebSocket mode - primary)
        # 2. OR audio expected to still be playing (timer backup)
        # 3. OR has HTTP playbacks (legacy mode)
        is_agent_speaking_now = tts_is_speaking or time_until_audio_done > 0 or has_active_playbacks
        
        # 🚀 FIX: Check when agent last actually SPOKE (not just generating)
        # This prevents filtering "yeah" during long transition evaluations
        agent_last_spoke_time = call_states.get(call_control_id, {}).get("agent_last_spoke_time", 0)
        time_since_agent_spoke = time.time() - agent_last_spoke_time if agent_last_spoke_time > 0 else 999
        
        # CRITICAL: Also check if agent is GENERATING (before playback starts)
        # If agent_generating_response is False, treat as silent even if playback tracked
        # This prevents race condition where playback.ended webhook hasn't arrived yet
        if is_agent_speaking_now and not agent_generating_response and time_until_audio_done <= 0:
            logger.info(f"⚠️ Agent marked as speaking but audio done and not generating - treating as SILENT")
            is_agent_speaking_now = False
        
        if is_agent_speaking_now:
            # Agent is actively speaking (audio playing)
            logger.info(f"🚦 Agent SPEAKING - User said {word_count} word(s), tts_speaking={tts_is_speaking}, time_until_done={time_until_audio_done:.1f}s")
            
            # 🛡️ CALL CONTROL PROTECTION: Check if we're in the protected window
            # If so, don't interrupt - the agent is playing a Call Control interruption
            protected_until = getattr(session, 'interrupt_playback_protected_until', 0) if session else 0
            call_control_protected = time.time() < protected_until
            
            if call_control_protected:
                logger.info(f"🛡️ CALL CONTROL: Final transcript barge-in skipped - interruption audio protected ({protected_until - time.time():.1f}s left)")
                return  # Don't interrupt the agent's interruption!
            
            if word_count >= 3:
                # Real interruption (3+ words) - stop agent immediately
                logger.info(f"🛑 INTERRUPTION DETECTED - User said {word_count} words: '{accumulated_transcript}'")
                logger.info(f"🛑 Stopping {len(current_playback_ids)} active playbacks immediately...")
                
                # Stop all active playbacks IMMEDIATELY (but NOT comfort noise)
                telnyx_service = get_telnyx_service()
                comfort_noise_id = call_states.get(call_control_id, {}).get("comfort_noise_playback_id")
                
                stop_tasks = []
                for playback_id in current_playback_ids:
                    # Skip comfort noise - it should keep playing
                    if playback_id != comfort_noise_id:
                        stop_tasks.append(telnyx_service.stop_playback(call_control_id, playback_id))
                
                if stop_tasks:
                    await asyncio.gather(*stop_tasks, return_exceptions=True)
                    logger.info(f"✋ Stopped {len(stop_tasks)} playbacks (kept comfort noise)")
                
                current_playback_ids.clear()
                call_states[call_control_id]["current_playback_ids"].clear()
                is_agent_speaking = False
                agent_generating_response = False
                call_states[call_control_id]["agent_generating_response"] = False
                
                logger.info(f"✅ Agent interrupted, processing user's message: '{accumulated_transcript}'")
                # Fall through to process the transcript
            else:
                # 1-2 words during agent speech - filter them
                # Only filter if we have DEFINITIVE evidence agent is speaking (tts_is_speaking or time > 0)
                if tts_is_speaking or time_until_audio_done > 0:
                    # Agent is DEFINITELY speaking (confirmed by TTS session or timer)
                    logger.info(f"🔕 Filtering {word_count}-word utterance during agent speech (tts={tts_is_speaking}, time_left={time_until_audio_done:.1f}s): '{accumulated_transcript}'")
                    accumulated_transcript = ""
                    return  # Don't process
                else:
                    # No definitive TTS evidence - use time_since_agent_spoke as fallback
                    # This handles HTTP playback mode or edge cases
                    if time_since_agent_spoke < 3.0:
                        logger.info(f"🔕 Filtering {word_count}-word utterance (spoke {time_since_agent_spoke:.1f}s ago): '{accumulated_transcript}'")
                        accumulated_transcript = ""
                        return  # Don't process
                    else:
                        # Agent hasn't spoken in 3+ seconds AND no TTS evidence - process
                        logger.info(f"⚠️ {word_count}-word utterance, no TTS activity, spoke {time_since_agent_spoke:.1f}s ago - processing")
                        # Fall through to process
        else:
            # Agent is NOT speaking (no active audio) - process ALL transcripts, including 1-word
            logger.info(f"✅ Agent SILENT - User said {word_count} word(s): '{accumulated_transcript}' - Processing...")
    
    # Forward audio from Telnyx to Soniox
    async def forward_telnyx_to_soniox():
        """Forward audio from Telnyx to Soniox (no resampling needed for mulaw!)"""
        import base64
        audio_packet_count = 0
        last_packet_log_time = time.time()
        nonlocal last_audio_received_time, stt_start_time, accumulated_transcript, current_playback_ids, agent_generating_response
        
        try:
            while True:
                # Receive JSON text from Telnyx
                message = await websocket.receive_text()
                data = json.loads(message)
                event = data.get("event")
                
                # Telnyx sends: {"event": "media", "media": {"payload": "base64..."}}
                if event == "media" and "media" in data:
                    # Telnyx sends base64 encoded 8kHz mulaw audio (20ms chunks)
                    mulaw_data = base64.b64decode(data["media"]["payload"])
                    
                    # ⏱️  Track last audio received time for STT latency calculation
                    last_audio_received_time = time.time()
                    if stt_start_time is None:
                        stt_start_time = last_audio_received_time
                    
                    # Send directly to Soniox (no resampling needed!)
                    # Note: We ALWAYS send audio so interruptions work
                    # Garbled echo transcripts are filtered at the transcript level
                    await soniox.send_audio(mulaw_data)
                    audio_packet_count += 1
                    
                    if audio_packet_count == 1:
                        logger.info(f"✅ Started forwarding audio (8kHz mulaw → Soniox, NO BUFFERING)")
                    
                    # Log every 5 seconds to confirm audio is still flowing
                    current_time = time.time()
                    if current_time - last_packet_log_time >= 5.0:
                        logger.info(f"📤 Audio flowing: {audio_packet_count} packets sent to Soniox (5s update)")
                        last_packet_log_time = current_time
                        
        except WebSocketDisconnect:
            logger.info(f"📞 Telnyx WebSocket disconnected. Sent {audio_packet_count} total packets")
        except Exception as e:
            logger.error(f"❌ Error forwarding audio to Soniox: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Run both tasks with auto-reconnect for Soniox
    try:
        # Create receive task
        async def receive_with_reconnect():
            """Keep receiving messages, reconnect if Soniox closes"""
            reconnect_attempts = 0
            max_reconnects = 3
            last_receive_log = time.time()
            messages_received = 0
            
            while reconnect_attempts < max_reconnects:
                try:
                    async def log_receiver_status():
                        nonlocal last_receive_log, messages_received
                        current_time = time.time()
                        if current_time - last_receive_log >= 10.0:
                            logger.info(f"🎤 Soniox receiver alive - {messages_received} messages received in last 10s")
                            last_receive_log = current_time
                            messages_received = 0
                    
                    # Custom receive that logs activity
                    async for msg in soniox.ws:
                        messages_received += 1
                        await log_receiver_status()
                        
                        data = json.loads(msg)
                        
                        if "error_code" in data:
                            logger.error(f"❌ Soniox error: {data}")
                            break
                        
                        if data.get("finished"):
                            logger.info("🛑 Soniox session finished")
                            break
                        
                        tokens = data.get("tokens", [])
                        if tokens:
                            # 🔍 DEBUG: Log raw token evolution (as per Soniox docs)
                            token_summary = []
                            for t in tokens:
                                token_text = t.get("text", "")
                                is_final = t.get("is_final", False)
                                status = "✓" if is_final else "?"
                                token_summary.append(f'"{token_text}"{status}')
                            logger.info(f"🔤 RAW TOKENS: [{', '.join(token_summary)}]")
                            
                            final_tokens = []
                            non_final_tokens = []
                            endpoint_detected = False
                            
                            for token in tokens:
                                text = token.get("text", "")
                                is_final = token.get("is_final", False)
                                
                                if text == "<end>" and is_final:
                                    endpoint_detected = True
                                    logger.info(f"🎯 Endpoint detected: <end> token received")
                                    continue
                                
                                if is_final:
                                    final_tokens.append(token)
                                else:
                                    non_final_tokens.append(token)
                            
                            # Process non-final (partial) tokens - fire and forget
                            if non_final_tokens and on_partial_transcript:
                                partial_text = " ".join([t.get("text", "") for t in non_final_tokens])
                                if partial_text.strip():
                                    # Clean up fragmented transcript
                                    from soniox_service import clean_transcript
                                    partial_text = clean_transcript(partial_text)
                                    asyncio.create_task(on_partial_transcript(partial_text, data))
                            
                            # Process final tokens - fire and forget  
                            if final_tokens:
                                final_text = " ".join([t.get("text", "") for t in final_tokens])
                                if final_text.strip():
                                    # Clean up fragmented transcript (e.g., "H ello" -> "Hello")
                                    from soniox_service import clean_transcript
                                    raw_text = final_text
                                    final_text = clean_transcript(final_text)
                                    if raw_text != final_text:
                                        logger.info(f"🧹 Cleaned transcript: '{raw_text}' -> '{final_text}'")
                                    
                                    # Log final tokens being added
                                    logger.info(f"📥 FINAL TOKENS: '{final_text}' ({len(final_tokens)} tokens)")
                                    logger.info(f"🎤 Soniox final transcript: '{final_text}'")
                                    
                                    # 🔥 GARBLED/ECHO DETECTION: Filter transcripts that are likely TTS echo
                                    # These occur when agent's audio echoes back and Soniox tries to transcribe it
                                    import re
                                    
                                    def is_garbled_transcript(text: str) -> bool:
                                        """Detect if transcript is garbled echo (not real speech)"""
                                        if not text or not text.strip():
                                            return True
                                        
                                        text = text.strip()
                                        
                                        # Pattern 1: Only single letters with spaces/dashes (like "M m -m m", "a b c")
                                        if re.match(r'^[a-zA-Z](\s+[-]?\s*[a-zA-Z])+[\s\.\-]*$', text):
                                            return True
                                        
                                        # Pattern 2: Only M's, spaces, dashes, dots
                                        if re.match(r'^[mMhH\s\-\.]+$', text) and len(text) < 15:
                                            return True
                                        
                                        # Pattern 3: Single repeated letters/sounds
                                        if re.match(r'^(m+|h+|u+|a+)[\s\-\.]*$', text.lower()):
                                            return True
                                        
                                        # ✅ EXCEPTION: Allow valid number patterns (4K, 10K, 5M, 2PM, etc.)
                                        # These are common responses for income/time questions
                                        if re.match(r'^\d+[kKmMbB]?\.?$', text):
                                            return False  # Valid number shorthand like "4K", "10K", "5M"
                                        if re.match(r'^\d+:?\d*\s*[AP]\.?M\.?$', text, re.IGNORECASE):
                                            return False  # Valid time like "2PM", "3:30 PM"
                                        
                                        # Pattern 4: Very short with no vowels (likely noise)
                                        if len(text) < 5 and not re.search(r'[aeiouyAEIOUY]', text):
                                            return True
                                        
                                        # Pattern 5: Just punctuation/dashes
                                        if re.match(r'^[\s\-\.\,\?\!]+$', text):
                                            return True
                                        
                                        return False
                                    
                                    is_garbled = is_garbled_transcript(final_text)
                                    if is_garbled:
                                        logger.warning(f"🔇 GARBLED/ECHO detected: '{final_text.strip()}' - filtering out")
                                    
                                    # 🔥 EARLY FILTER: Check if this is a 1-word filler during agent speech
                                    # If so, don't call on_final_transcript at all (prevents context pollution)
                                    word_count = len(final_text.strip().split())
                                    filler_words = ["um", "uh", "hmm", "mhm", "yeah", "yep", "nope", "ok", "okay", "uh-huh", "yes", "no", "sure", "right", "ah", "oh"]
                                    is_filler = final_text.strip().lower().rstrip('?.,!') in filler_words
                                    
                                    # Check if agent is actively speaking
                                    # NOTE: current_playback_ids is for HTTP-based playbacks (legacy)
                                    # With WebSocket streaming, we use tts_is_speaking as source of truth
                                    has_active_playbacks = len(current_playback_ids) > 0
                                    
                                    # Also check agent_generating_response flag
                                    is_generating = agent_generating_response or call_states.get(call_control_id, {}).get("agent_generating_response", False)
                                    
                                    # 🔊 SINGLE SOURCE OF TRUTH: Check TTS session's is_speaking flag
                                    # This is the authoritative state for whether agent audio is playing
                                    tts_session = persistent_tts_manager.get_session(call_control_id) if call_control_id else None
                                    tts_is_speaking = tts_session.is_speaking if tts_session else False
                                    
                                    # Also check playback_expected_end for logging/debugging
                                    playback_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
                                    current_time = time.time()
                                    time_until_audio_done = playback_expected_end - current_time if playback_expected_end > 0 else 0
                                    
                                    # 🔥 SIMPLIFIED: Agent is active if:
                                    # 1. TTS session says it's speaking (AUTHORITATIVE for WebSocket)
                                    # 2. OR audio expected to still be playing (time backup)
                                    # 3. OR LLM is generating
                                    # NOTE: Removed has_active_playbacks since that's for HTTP mode only
                                    user_actively_speaking = session and session.user_speaking
                                    
                                    if tts_is_speaking:
                                        # TTS session explicitly says agent is speaking
                                        is_agent_active = True
                                        if user_actively_speaking:
                                            logger.info(f"🎯 User speaking while TTS is_speaking=True - INTERRUPTION POSSIBLE")
                                    elif tts_session and getattr(tts_session, 'is_waiting_for_first_audio_of_response', False):
                                        # 🔥 FIX: Agent is technically "speaking" (waiting for audio to arrive)
                                        # This covers the ~500ms gap between LLM done and audio start
                                        is_agent_active = True
                                        logger.info(f"🛡️ Agent active (waiting for audio) - 1-word filter ENABLED")
                                    elif playback_expected_end > 0 and time_until_audio_done > -NETWORK_PROPAGATION_DELAY:
                                        # Audio expected to still be playing (including network latency buffer)
                                        is_agent_active = True
                                    elif is_generating:
                                        # LLM is generating response
                                        is_agent_active = True
                                    else:
                                        # Agent is NOT active - ready to receive user input
                                        is_agent_active = False
                                    
                                    # DEBUG: Log all values
                                    logger.info(f"🔍 FILTER CHECK: words={word_count}, is_filler={is_filler}, is_garbled={is_garbled}, tts_speaking={tts_is_speaking}, time_until_done={time_until_audio_done:.1f}s, generating={is_generating}, playbacks={len(current_playback_ids)}, is_active={is_agent_active}")
                                    
                                    # ALWAYS filter garbled transcripts (these are echo, not real speech)
                                    if is_garbled:
                                        logger.info(f"🔕 FILTERING garbled/echo '{final_text.strip()}' - NOT calling on_final_transcript")
                                    # Filter 1-2 word utterances or fillers ONLY during active audio playback
                                    # Relax filter during latency buffer (time < 0) to allow quick turn-taking (e.g. "Yeah", "What's up?")
                                    elif is_agent_active and time_until_audio_done > 0.2 and (word_count <= 2 or is_filler):
                                        logger.info(f"🔕 FILTERING {word_count}-word/filler '{final_text.strip()}' - NOT calling on_final_transcript")
                                        # Don't call on_final_transcript - skip this entirely
                                    elif on_final_transcript:
                                        # Not filtered - call on_final_transcript
                                        asyncio.create_task(on_final_transcript(final_text, data))
                            
                            # Call endpoint callback - RUN AS BACKGROUND TASK to avoid blocking receive loop!
                            if endpoint_detected and on_endpoint_detected:
                                # 🔥 EARLY FILTER for endpoint too - don't spawn task for filtered utterances
                                if final_tokens and final_text.strip():
                                    word_count = len(final_text.strip().split())
                                    filler_words = ["um", "uh", "hmm", "mhm", "yeah", "yep", "nope", "ok", "okay", "uh-huh", "yes", "no", "sure", "right", "ah", "oh"]
                                    is_filler = final_text.strip().lower().rstrip('?.,!') in filler_words
                                    
                                    # Check for garbled/echo transcripts
                                    is_garbled = is_garbled_transcript(final_text) if 'is_garbled_transcript' in dir() else False
                                    
                                    has_active_playbacks = len(current_playback_ids) > 0
                                    is_generating = agent_generating_response or call_states.get(call_control_id, {}).get("agent_generating_response", False)
                                    
                                    # 🔊 SINGLE SOURCE OF TRUTH: Check TTS session's is_speaking flag
                                    tts_session = persistent_tts_manager.get_session(call_control_id) if call_control_id else None
                                    tts_is_speaking = tts_session.is_speaking if tts_session else False
                                    
                                    # Also check playback_expected_end for backup
                                    playback_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
                                    current_time = time.time()
                                    time_until_audio_done = playback_expected_end - current_time if playback_expected_end > 0 else 0
                                    
                                    # 🔥 SIMPLIFIED: Agent is active if TTS says so or timer backup
                                    # NOTE: Removed has_active_playbacks since that's for HTTP mode only
                                    user_actively_speaking = session and session.user_speaking
                                    
                                    if tts_is_speaking:
                                        # TTS session explicitly says agent is speaking
                                        is_agent_active = True
                                        if user_actively_speaking:
                                            logger.info(f"🎯 User speaking while TTS is_speaking=True - INTERRUPTION POSSIBLE")
                                    elif tts_session and getattr(tts_session, 'is_waiting_for_first_audio_of_response', False):
                                        # 🔥 FIX: Agent is technically "speaking" (waiting for audio to arrive)
                                        # This covers the ~500ms gap between LLM done and audio start
                                        is_agent_active = True
                                    elif playback_expected_end > 0 and time_until_audio_done > -NETWORK_PROPAGATION_DELAY:
                                        # Audio expected to still be playing by timer (including latency buffer)
                                        is_agent_active = True
                                    elif tts_session and getattr(tts_session, 'is_waiting_for_first_audio_of_response', False):
                                        # 🔥 FIX: Agent is technically "speaking" (waiting for audio to arrive)
                                        is_agent_active = True
                                    elif time_until_audio_done > 0:
                                        is_agent_active = True
                                    elif is_generating:
                                        is_agent_active = True
                                    else:
                                        is_agent_active = False
                                    
                                    # ALWAYS filter garbled transcripts
                                    if is_garbled:
                                        logger.info(f"🔕 SKIPPING endpoint for garbled/echo '{final_text.strip()}'")
                                        accumulated_transcript = ""
                                        if session and session.user_speaking:
                                            session.mark_user_speaking_end()
                                        continue
                                    
                                    # Filter 1-2 word utterances or fillers during agent speech
                                    if is_agent_active and (word_count <= 2 or is_filler):
                                        logger.info(f"🔕 SKIPPING endpoint for {word_count}-word/filler '{final_text.strip()}' (tts_speaking={tts_is_speaking}, is_active={is_agent_active})")
                                        accumulated_transcript = ""  # Clear any accumulated text
                                        
                                        # 🔥 CRITICAL FIX: Still mark user as stopped speaking even when filtering
                                        # Otherwise user_speaking stays True and silence detection never triggers
                                        if session and session.user_speaking:
                                            session.mark_user_speaking_end()
                                            logger.info(f"👤 Marked user stopped speaking (filtered utterance)")
                                        
                                        continue
                                
                                # Cancel any existing response task before starting new one
                                # BUT: Don't cancel if call is already ending (hangup in progress)
                                if call_ending:
                                    logger.info(f"⏭️  Skipping processing - call is ending")
                                    continue
                                    
                                current_response_task = call_states.get(call_control_id, {}).get("current_response_task")
                                if current_response_task and not current_response_task.done():
                                    logger.info(f"🛑 Cancelling previous response task before starting new endpoint processing")
                                    
                                    # 🔥 CRITICAL: Stop all in-flight playbacks FIRST to prevent audio queuing
                                    local_playback_ids = call_states.get(call_control_id, {}).get("current_playback_ids", set())
                                    comfort_noise_id = call_states.get(call_control_id, {}).get("comfort_noise_playback_id")
                                    if local_playback_ids:
                                        logger.info(f"🛑 Stopping {len(local_playback_ids)} in-flight playbacks before new response")
                                        telnyx_svc = get_telnyx_service()
                                        stop_tasks = []
                                        for playback_id in list(local_playback_ids):
                                            if playback_id != comfort_noise_id:
                                                stop_tasks.append(telnyx_svc.stop_playback(call_control_id, playback_id))
                                        if stop_tasks:
                                            # Fire and forget - don't block the receive loop
                                            asyncio.create_task(asyncio.gather(*stop_tasks, return_exceptions=True))
                                        call_states[call_control_id]["current_playback_ids"] = set()
                                    
                                    # Cancel the task
                                    current_response_task.cancel()
                                    
                                    # Reset agent state
                                    call_states[call_control_id]["agent_generating_response"] = False
                                    
                                new_task = asyncio.create_task(on_endpoint_detected())
                                if call_control_id in call_states:
                                    call_states[call_control_id]["current_response_task"] = new_task
                                logger.info(f"🚀 Spawned tracked background task for endpoint processing")
                    
                    logger.info("✅ Soniox receive loop ended normally")
                    break
                except Exception as e:
                    reconnect_attempts += 1
                    logger.warning(f"⚠️  Soniox connection lost (attempt {reconnect_attempts}/{max_reconnects}): {e}")
                    import traceback
                    logger.warning(f"Traceback: {traceback.format_exc()}")
                    
                    if reconnect_attempts < max_reconnects:
                        # Reconnect to Soniox
                        logger.info("🔄 Reconnecting to Soniox...")
                        await soniox.connect()
                        logger.info("✅ Soniox reconnected successfully")
                    else:
                        logger.error("❌ Max Soniox reconnect attempts reached")
                        break
        
        await asyncio.gather(
            forward_telnyx_to_soniox(),
            receive_with_reconnect()
        )
    except Exception as e:
        logger.error(f"❌ Error in Soniox streaming: {e}")
    finally:
        # Cancel dead air monitoring task
        if dead_air_task:
            dead_air_task.cancel()
            try:
                await dead_air_task
            except asyncio.CancelledError:
                pass
            logger.info(f"🔇 Dead air monitoring task cancelled")
        
        await soniox.close()


@api_router.websocket("/telnyx/audio-stream")
async def telnyx_audio_stream_generic(websocket: WebSocket):
    """
    Generic WebSocket endpoint for Telnyx audio streaming
    Telnyx sends call_control_id in the 'start' event, not the URL
    """
    import traceback
    logger.info(f"🔌🔌🔌 WEBSOCKET CONNECTION ATTEMPT")
    logger.info(f"   Client: {websocket.client}")
    logger.info(f"   Headers: {dict(websocket.headers)}")
    logger.info(f"   Path: {websocket.url.path}")
    logger.info(f"🔌 Incoming Telnyx WebSocket connection")
    
    # Accept the WebSocket connection immediately
    await websocket.accept()
    logger.info(f"✅ WebSocket accepted, waiting for Telnyx events")
    
    call_control_id = None
    deepgram_ws = None
    is_agent_speaking = False
    
    try:
        # First, handle the "connected" event from Telnyx
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                data = json.loads(message)
                event = data.get("event")
                
                logger.info(f"📬 Received Telnyx event: {event}")
                
                if event == "connected":
                    logger.info(f"📞 Telnyx connected event received, waiting for 'start'...")
                    continue  # Keep waiting for the "start" event
                
                elif event == "start":
                    # Extract call_control_id from start event
                    call_control_id = data.get("start", {}).get("call_control_id")
                    if not call_control_id:
                        logger.error(f"❌ No call_control_id in start event")
                        await websocket.close(code=1000, reason="No call_control_id")
                        return
                    
                    logger.info(f"🎬 Stream started for call: {call_control_id}")
                    break  # Exit loop and proceed with stream handling
                
                else:
                    logger.warning(f"⚠️ Unexpected event before start: {event}")
                    
            except asyncio.TimeoutError:
                logger.error(f"❌ Timeout waiting for events (60s)")
                await websocket.close(code=1000, reason="Timeout")
                return
        
        # Wait for call data to be ready (check Redis for cross-worker support)
        max_wait = 15
        wait_time = 0
        call_data = None
        
        while not call_data:
            # Check Redis first (cross-worker), then in-memory fallback
            call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id)
            
            if wait_time >= max_wait:
                logger.error(f"❌ Timeout waiting for call data after {max_wait}s")
                await websocket.close(code=1000, reason="Call data timeout")
                return
            
            if not call_data:
                await asyncio.sleep(0.2)
                wait_time += 0.2
        
        logger.info(f"✅ Call data found after {wait_time}s wait")
        
        # Get session from call_data (created by webhook handler in same or different worker)
        # Check if session already exists (created by webhook)
        from core_calling_service import get_call_session, create_call_session
        
        session = await get_call_session(call_control_id)
        
        if not session:
            # Session doesn't exist yet - WebSocket arrived before webhook finished
            # Wait briefly for webhook to create it (optimized - single short wait)
            logger.info("⏳ Session not found locally, waiting briefly for webhook...")
            
            # Single 0.5s wait instead of polling loop
            await asyncio.sleep(0.5)
            session = await get_call_session(call_control_id)
            
            if session:
                logger.info(f"✅ Session found after brief wait")
            else:
                logger.info(f"⚠️ Session still not found after wait, will create in worker")
            
            if not session:
                # Still no session - create it ourselves in this worker
                logger.warning("⚠️ Session not found after waiting, creating in WebSocket worker...")
                
                # Re-fetch call_data from Redis to ensure we have latest data
                call_data_fresh = redis_service.get_call_data(call_control_id)
                if not call_data_fresh:
                    logger.error("❌ Cannot retrieve call data from Redis")
                    await websocket.close(code=1000, reason="No call data")
                    return
                
                agent = call_data_fresh.get("agent")
                agent_id = call_data_fresh.get("agent_id")
                
                if not agent or not agent_id:
                    logger.error(f"❌ No agent data in call_data. Keys: {list(call_data_fresh.keys())}")
                    await websocket.close(code=1000, reason="No agent data")
                    return
                
                # Get user_id from agent
                user_id = agent.get("user_id")
                
                logger.info(f"📝 Creating session with agent_id={agent_id}, user_id={user_id}")
                
                # Create session in this worker
                session = await create_call_session(
                    call_control_id,
                    agent,
                    agent_id=agent_id,
                    user_id=user_id,
                    db=db
                )
                
                # Update custom variables
                custom_variables = call_data_fresh.get("custom_variables", {})
                session.session_variables.update(custom_variables)
                
                logger.info("✅ Session created in WebSocket worker")
                
                # 🔥 FIX D: Start silence tracking immediately so dead air monitor 
                # has a baseline even if agent never speaks
                session.start_silence_tracking()
                
                # ═══════════════════════════════════════════════════════════════════
                # SCHEDULE SILENCE TIMEOUT IN THIS WORKER (has the session in memory)
                # ═══════════════════════════════════════════════════════════════════
                flow = agent.get("call_flow", [])
                start_node = flow[0] if flow else {}
                start_node_data = start_node.get("data", {})
                who_speaks_first = start_node_data.get("whoSpeaksFirst", "ai")
                ai_speaks_after_silence = start_node_data.get("aiSpeaksAfterSilence", False)
                silence_timeout_ms = max(start_node_data.get("silenceTimeout", 2000), 3000) # Force min 3000ms
                
                if who_speaks_first == "user" and ai_speaks_after_silence:
                    logger.info(f"⏱️ [WebSocket Worker] Scheduling silence timeout: {silence_timeout_ms}ms")
                    
                    async def trigger_ai_after_silence_ws():
                        """Silence timeout task - runs on WebSocket worker that has the session"""
                        try:
                            logger.info(f"⏱️ [WebSocket Worker] Silence timeout task started, waiting {silence_timeout_ms}ms...")
                            await asyncio.sleep(silence_timeout_ms / 1000.0)
                            
                            # Check if user has already spoken
                            redis_data = redis_service.get_call_data(call_control_id) or {}
                            call_data_check = active_telnyx_calls.get(call_control_id, {})
                            
                            user_has_spoken = redis_data.get("user_has_spoken") or call_data_check.get("user_has_spoken")
                            ai_has_responded = redis_data.get("ai_has_responded") or call_data_check.get("ai_has_responded")
                            greeting_triggered = redis_data.get("silence_greeting_triggered") or call_data_check.get("silence_greeting_triggered")
                            
                            # 🔥 FIX: Only skip if AI has actually responded (or greeting already triggered)
                            # Ignore user_has_spoken because it can be true for filtered utterances (uh-huh due to bug or noise)
                            if ai_has_responded:
                                logger.info(f"⏱️ [WebSocket Worker] Silence timeout: AI already responded, skipping greeting")
                                return
                            
                            if greeting_triggered:
                                logger.info(f"⏱️ [WebSocket Worker] Silence timeout: Greeting already triggered, skipping")
                                return
                            
                            # Mark as triggered
                            if call_control_id in active_telnyx_calls:
                                active_telnyx_calls[call_control_id]["silence_greeting_triggered"] = True
                            
                            # Use update_call_data to prevent wiping session state
                            redis_service.update_call_data(call_control_id, {"silence_greeting_triggered": True})
                            
                            logger.info(f"⏱️ [WebSocket Worker] Silence timeout reached - generating greeting!")
                            
                            # Generate and speak greeting
                            greeting_response = await session.process_user_input("")
                            
                            # Handle both string and dict return types
                            if isinstance(greeting_response, str):
                                greeting_text = greeting_response
                            elif greeting_response:
                                greeting_text = greeting_response.get("text", "Hello?")
                            else:
                                greeting_text = "Hello?"
                            
                            logger.info(f"💬 [WebSocket Worker] AI speaks after silence: {greeting_text}")
                            
                            # Save to transcript
                            await db.call_logs.update_one(
                                {"call_id": call_control_id},
                                {"$push": {
                                    "transcript": {
                                        "role": "assistant",
                                        "text": greeting_text,
                                        "timestamp": datetime.utcnow().isoformat()
                                    }
                                }}
                            )
                            
                            # 🔥 FIX: Check if user spoke DURING greeting generation
                            # This prevents the race condition where user starts speaking
                            # after silence timeout fires but before TTS playback is sent
                            redis_data_check = redis_service.get_call_data(call_control_id) or {}
                            call_data_check = active_telnyx_calls.get(call_control_id, {})
                            user_spoke_during_gen = redis_data_check.get("user_has_spoken") or call_data_check.get("user_has_spoken")
                            
                            if user_spoke_during_gen:
                                logger.info("⏭️ [WebSocket Worker] User spoke during greeting generation - CANCELLING silence greeting")
                                return  # Don't speak - user already started the conversation
                            
                            # Mark agent as speaking BEFORE sending TTS
                            # This prevents dead air monitor from counting silence during greeting
                            # 🔥 FIX C: Latency protection - Buffer user speech while greeting is starting up
                            if call_control_id in active_telnyx_calls:
                                active_telnyx_calls[call_control_id]["greeting_in_flight"] = True
                            redis_service.update_call_data(call_control_id, {"greeting_in_flight": True})
                            
                            session.mark_agent_speaking_start()
                            logger.info("🗣️ [WebSocket Worker] Marked agent as speaking (for initial greeting)")
                            
                            # Speak the greeting
                            telnyx_svc = get_telnyx_service()
                            await telnyx_svc.speak_text(
                                call_control_id,
                                greeting_text,
                                agent_config=session.agent_config
                            )
                            logger.info("🔊 [WebSocket Worker] Silence greeting spoken via Telnyx TTS")
                            
                            # 🔥 ATTEMPT 12: Record when greeting playback started
                            # This enables detecting if user spoke BEFORE hearing the greeting
                            import time
                            greeting_playback_time = time.time()
                            call_states[call_control_id]["greeting_playback_started_at"] = greeting_playback_time
                            logger.info(f"⏱️ [WebSocket Worker] Greeting playback started at {greeting_playback_time}")
                            
                            # Start silence tracking so dead air monitoring kicks in
                            # This is critical for check-in/disconnect flow to work
                            session.start_silence_tracking()
                            logger.info("⏱️ [WebSocket Worker] Silence tracking started for dead air monitoring")
                            
                        except asyncio.CancelledError:
                            logger.info("⏱️ [WebSocket Worker] Silence timeout task cancelled")
                        except Exception as e:
                            logger.error(f"❌ [WebSocket Worker] Error in silence greeting task: {e}")
                    
                    # Start the task on THIS worker (which has the session)
                    asyncio.create_task(trigger_ai_after_silence_ws())
                    logger.info(f"⏱️ [WebSocket Worker] Silence timeout task scheduled!")
                    
        else:
            logger.info("✅ Session found in this worker's active_sessions")
        
        # Get agent configuration and check STT provider
        agent_config = session.agent_config
        stt_provider = agent_config.get("settings", {}).get("stt_provider")
        
        # STT provider is REQUIRED - no defaults
        if not stt_provider:
            logger.error("❌ No STT provider configured for agent")
            await websocket.close(code=1011, reason="STT provider not configured in agent settings")
            return
        
        logger.info(f"📞 Call data loaded, starting {stt_provider.upper()} connection...")
        
        # Route to appropriate STT provider based on agent configuration
        if stt_provider == "assemblyai":
            # Use AssemblyAI for STT
            from assemblyai_service import AssemblyAIStreamingService
            await handle_assemblyai_streaming(websocket, session, call_control_id, call_control_id)
            return
        elif stt_provider == "soniox":
            # Use Soniox for STT
            from soniox_service import SonioxStreamingService
            await handle_soniox_streaming(websocket, session, call_control_id, call_control_id)
            return
        elif stt_provider == "deepgram":
            # Use Deepgram for STT (explicitly configured)
            deepgram_settings = agent_config.get("settings", {}).get("deepgram_settings", {})
            endpointing = deepgram_settings.get("endpointing", 500)
            interim_results = deepgram_settings.get("interim_results", False)
            punctuate = deepgram_settings.get("punctuate", True)
            smart_format = deepgram_settings.get("smart_format", True)
        vad_events = deepgram_settings.get("vad_events", True)
        
        logger.info(f"⚙️  Deepgram settings: endpointing={endpointing}ms, interim={interim_results}, punctuate={punctuate}, smart_format={smart_format}, vad_events={vad_events}")
        
        # Get user's Deepgram API key
        deepgram_api_key = await get_api_key(session.user_id, "deepgram")
        if not deepgram_api_key:
            logger.error("❌ No Deepgram API key found for user")
            await websocket.close(code=1011, reason="Deepgram API key not configured")
            return
        
        logger.info(f"🔑 Using user's Deepgram API key (first 10 chars): {deepgram_api_key[:10]}...")
        
        # Connect to Deepgram using raw websockets (SDK has issues with v2)
        deepgram_ws = None
        
        try:
            # Build Deepgram WebSocket URL with agent-specific settings
            # NOTE: utterance_end_ms and vad_turnoff parameters removed - cause HTTP 400 error on WebSocket API
            deepgram_url = (
                f"wss://api.deepgram.com/v1/listen?"
                f"model=nova-3&"
                f"encoding=mulaw&"
                f"sample_rate=8000&"
                f"channels=1&"
                f"punctuate={'true' if punctuate else 'false'}&"
                f"interim_results={'true' if interim_results else 'false'}&"
                f"endpointing={endpointing}&"
                f"vad_events={'true' if vad_events else 'false'}&"
                f"smart_format={'true' if smart_format else 'false'}"
            )
            
            logger.info(f"🔗 Deepgram URL: {deepgram_url[:150]}...")
            
            # Connect with user's API key
            deepgram_ws = await websockets.connect(
                deepgram_url,
                extra_headers={"Authorization": f"Token {deepgram_api_key}"}
            )
            
            logger.info("✅ Connected to Deepgram live streaming")
            logger.info("🚀 Starting bidirectional audio streaming...")
            
            # Task to forward audio from Telnyx to Deepgram
            async def forward_telnyx_to_deepgram():
                nonlocal is_agent_speaking
                try:
                    audio_packet_count = 0
                    logger.info(f"👂 Starting to listen for Telnyx media...")
                    
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        event = data.get("event")
                        
                        if event == "media":
                            if not is_agent_speaking:
                                media = data.get("media", {})
                                payload = media.get("payload", "")
                                if payload:
                                    # Decode base64 audio and send to Deepgram
                                    audio_bytes = base64.b64decode(payload)
                                    await deepgram_ws.send(audio_bytes)
                                    audio_packet_count += 1
                                    if audio_packet_count % 100 == 0:
                                        logger.info(f"📡 Forwarded {audio_packet_count} packets")
                        elif event == "stop":
                            logger.info(f"⏹️ Telnyx stream stopped")
                            break
                            
                except Exception as e:
                    logger.error(f"❌ Error forwarding audio: {e}")
            
            # Task to receive transcripts from Deepgram
            # Accumulation buffer for natural conversation flow
            transcript_buffer = []
            last_transcript_time = None
            processing_task = None
            
            async def process_accumulated_transcript():
                """Process accumulated transcript after a brief delay"""
                nonlocal is_agent_speaking, transcript_buffer, last_transcript_time
                
                await asyncio.sleep(0.8)  # Wait 800ms to see if more speech comes
                
                # Check if new speech came in during wait
                if last_transcript_time and (asyncio.get_event_loop().time() - last_transcript_time) < 0.7:
                    return  # More speech coming, don't process yet
                
                if not transcript_buffer:
                    return
                
                # Combine accumulated transcripts
                full_transcript = " ".join(transcript_buffer).strip()
                transcript_buffer = []
                
                # Filter out very short utterances (um, uh, yeah, etc.)
                if len(full_transcript) < 4:
                    logger.info(f"⏭️  Skipping short utterance: '{full_transcript}'")
                    return
                
                # Filter out common filler words when alone
                fillers = ["um", "uh", "hmm", "mhm", "yeah", "yep", "nope", "ok", "okay"]
                if full_transcript.lower() in fillers:
                    logger.info(f"⏭️  Skipping filler word: '{full_transcript}'")
                    return
                
                logger.info(f"📝 User said: {full_transcript}")
                
                llm_start_time = time.time()
                
                # Save user transcript to database (non-blocking - fire and forget)
                async def save_user_transcript():
                    try:
                        await db.call_logs.update_one(
                            {"call_id": call_control_id},
                            {"$push": {
                                "transcript": {
                                    "role": "user",
                                    "text": full_transcript,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            }}
                        )
                        logger.info(f"📝 Saved user transcript to database")
                    except Exception as e:
                        logger.error(f"Failed to save user transcript: {e}")
                
                asyncio.create_task(save_user_transcript())
                
                # Process with AI
                is_agent_speaking = True
                response = await session.process_user_input(full_transcript)
                response_text = response.get("text", "")
                response_latency = response.get("latency", 0)
                llm_latency_ms = int((time.time() - llm_start_time) * 1000)  # Convert to ms
                
                logger.info(f"🤖 AI response: {response_text}")
                
                # Save agent transcript to database (non-blocking - fire and forget)
                async def save_assistant_transcript():
                    try:
                        await db.call_logs.update_one(
                            {"call_id": call_control_id},
                            {"$push": {
                                "transcript": {
                                    "role": "assistant",
                                    "text": response_text,
                                    "timestamp": datetime.utcnow().isoformat()
                                },
                                "logs": {
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "level": "info",
                                    "type": "turn_complete",
                                    # FULL TEXT - no truncation
                                    "user_text": full_transcript,
                                    "agent_text": response_text,
                                    # Detailed timing metrics
                                    "latency": {
                                        "e2e_ms": llm_latency_ms,
                                        "llm_ms": int(response_latency * 1000)
                                    },
                                    # Legacy summary for backwards compatibility
                                    "message": f"E2E latency for this turn: {llm_latency_ms}ms (LLM: {int(response_latency * 1000)}ms) | User: '{full_transcript}' -> Agent: '{response_text}'"
                                }
                            }}
                        )
                        logger.info(f"📝 Saved assistant transcript and latency to database")
                    except Exception as e:
                        logger.error(f"Failed to save assistant transcript: {e}")
                
                asyncio.create_task(save_assistant_transcript())
                
                # Speak response with agent config for TTS routing
                telnyx_service = get_telnyx_service()
                agent_config = session.agent_config
                # 🔥 CRITICAL FIX: Mark agent as speaking before emitting audio
                session.mark_agent_speaking_start()
                await telnyx_service.speak_text(call_control_id, response_text, agent_config=agent_config)
                
                # Check if we should end call
                if session.should_end_call:
                    logger.info("📞 Ending call...")
                    await asyncio.sleep(2)
                    await telnyx_service.hangup_call(call_control_id)
                
                is_agent_speaking = False
            
            async def process_deepgram_transcripts():
                nonlocal is_agent_speaking, transcript_buffer, last_transcript_time, processing_task
                try:
                    async for message in deepgram_ws:
                        result = json.loads(message)
                        msg_type = result.get("type")
                        
                        # Check if it's a transcript result
                        if msg_type == "Results":
                            transcript = result.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                            is_final = result.get("is_final", False)
                            
                            # Accumulate final transcripts
                            if transcript and is_final:
                                transcript_buffer.append(transcript)
                                last_transcript_time = asyncio.get_event_loop().time()
                                
                                # Cancel any pending processing and schedule new one
                                if processing_task and not processing_task.done():
                                    processing_task.cancel()
                                    try:
                                        await processing_task
                                    except asyncio.CancelledError:
                                        pass
                                
                                # Schedule processing with delay
                                processing_task = asyncio.create_task(process_accumulated_transcript())
                                
                except Exception as e:
                    logger.error(f"❌ Error processing transcripts: {e}")
            
            # Run both tasks concurrently
            await asyncio.gather(
                forward_telnyx_to_deepgram(),
                process_deepgram_transcripts()
            )
            
        except Exception as e:
            logger.error(f"❌ Error in streaming: {e}", exc_info=True)
        finally:
            if deepgram_ws:
                await deepgram_ws.close()
                logger.info("🔌 Deepgram connection closed")
        
    except Exception as e:
        logger.error(f"❌ Error in WebSocket handler: {e}", exc_info=True)
    finally:
        if deepgram_ws:
            await deepgram_ws.close()
        logger.info(f"🔌 Telnyx WebSocket disconnected")



# buffer to account for network propagation delay (Server -> Telnyx -> Carrier -> Handset)
# This prevents the agent from thinking it's done speaking while the user is still hearing the last words
NETWORK_PROPAGATION_DELAY = 1.5

@api_router.websocket("/telnyx/audio-stream/{call_control_id}")
async def telnyx_audio_stream(websocket: WebSocket, call_control_id: str):
    """
    WebSocket endpoint for bidirectional real-time audio streaming with Telnyx
    Telnyx → Our WS → Deepgram STT → AI → Telnyx TTS
    """
    logger.info(f"🔌 Incoming WebSocket connection for call: {call_control_id}")
    
    # Accept the WebSocket connection immediately
    await websocket.accept()
    logger.info(f"✅ WebSocket accepted for call: {call_control_id}")
    
    deepgram_ws = None
    is_agent_speaking = False
    last_agent_text = ""
    
    try:
        # Accept connection immediately and respond to keep-alive
        logger.info(f"📞 WebSocket connection accepted, ready for Telnyx")
        
        # Send immediate acknowledgment (helps with connection validation)
        try:
            await websocket.send_text(json.dumps({
                "event": "ready",
                "timestamp": datetime.utcnow().isoformat()
            }))
        except:
            pass  # Telnyx might not expect this, but doesn't hurt
        
        # Wait briefly for call data (optimized - single check with short wait)
        if call_control_id not in active_telnyx_calls:
            await asyncio.sleep(0.5)  # Single 500ms wait instead of polling
        
        if call_control_id not in active_telnyx_calls:
            logger.error(f"❌ Call data not ready after wait")
            try:
                await websocket.close(code=1000, reason="Ready but no call data")
            except:
                pass
            return
        
        call_data = active_telnyx_calls[call_control_id]
        session = call_data.get("session")
        
        if not session:
            # Wait a bit more for session to be created
            await asyncio.sleep(1)
            session = call_data.get("session")
            
            if not session:
                logger.error(f"❌ No session for call {call_control_id} - closing")
                await websocket.close(code=1000, reason="No session")
                return
        
        last_agent_text = call_data.get("last_agent_text", "")
        agent_config = session.agent_config
        
        # 🔌 Store WebSocket in call_data so persistent TTS can access it
        call_data["telnyx_ws"] = websocket
        logger.info(f"✅ Stored Telnyx WebSocket in call_data for audio streaming")
        
        # 🔌 Update persistent TTS session with WebSocket (if it exists)
        # Note: persistent_tts_manager is imported at top of file
        persistent_tts_manager.update_websocket(call_control_id, websocket)
        
        logger.info(f"📞 Call data loaded, starting Deepgram connection...")
        
        # Get Deepgram settings from agent configuration
        deepgram_settings = agent_config.get("settings", {}).get("deepgram_settings", {})
        endpointing = deepgram_settings.get("endpointing", 500)
        interim_results = deepgram_settings.get("interim_results", False)
        punctuate = deepgram_settings.get("punctuate", True)
        smart_format = deepgram_settings.get("smart_format", True)
        vad_events = deepgram_settings.get("vad_events", True)
        
        logger.info(f"⚙️ Deepgram settings: endpointing={endpointing}ms, interim={interim_results}, punctuate={punctuate}, smart_format={smart_format}, vad_events={vad_events}")
        
        # Connect to Deepgram's live streaming API with agent-specific settings
        # NOTE: utterance_end_ms and vad_turnoff parameters removed - cause HTTP 400 error on WebSocket API
        deepgram_url = (
            f"wss://api.deepgram.com/v1/listen?"
            f"model=nova-3&"
            f"encoding=mulaw&"
            f"sample_rate=8000&"
            f"channels=1&"
            f"punctuate={'true' if punctuate else 'false'}&"
            f"interim_results={'true' if interim_results else 'false'}&"
            f"endpointing={endpointing}&"
            f"vad_events={'true' if vad_events else 'false'}&"
            f"smart_format={'true' if smart_format else 'false'}"
        )
        
        logger.info(f"🔗 Deepgram URL: {deepgram_url[:150]}...")
        logger.info(f"⚙️ Deepgram settings: endpointing={endpointing}ms, interim={interim_results}, punctuate={punctuate}, smart_format={smart_format}, vad_events={vad_events}")
        logger.info(f"🌐 Connecting to Deepgram...")
        
        try:
            deepgram_ws = await websockets.connect(
                deepgram_url,
                extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
                ping_interval=20,
                ping_timeout=10
            )
            logger.info(f"✅ Connected to Deepgram live streaming")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Deepgram: {e}")
            await websocket.close(code=1011, reason="Deepgram connection failed")
            return
        
        # Task to receive audio from Telnyx and forward to Deepgram
        async def forward_telnyx_to_deepgram():
            nonlocal is_agent_speaking
            try:
                audio_packet_count = 0
                logger.info(f"👂 Starting to listen for Telnyx messages...")
                while True:
                    # Receive message from Telnyx
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    event = data.get("event")
                    logger.info(f"📬 Received Telnyx event: {event}")
                    
                    if event == "connected":
                        logger.info(f"📞 Telnyx stream connected: {data}")
                    
                    elif event == "start":
                        logger.info(f"🎬 Telnyx stream started: {data}")
                    
                    elif event == "media":
                        # Only forward audio when agent is NOT speaking
                        if not is_agent_speaking:
                            media = data.get("media", {})
                            payload = media.get("payload", "")
                            
                            if payload:
                                # Decode base64 audio and send to Deepgram
                                audio_bytes = base64.b64decode(payload)
                                await deepgram_ws.send(audio_bytes)
                                
                                audio_packet_count += 1
                                if audio_packet_count % 100 == 0:
                                    logger.info(f"📡 Forwarded {audio_packet_count} packets")
                        else:
                            if audio_packet_count % 200 == 0:
                                logger.debug(f"🔇 Skipping media (agent speaking)")
                    
                    elif event == "stop":
                        logger.info(f"⏹️ Telnyx stream stopped")
                        break
                    else:
                        logger.info(f"📥 Unknown Telnyx event: {event}, full data: {json.dumps(data)[:200]}")
                        
            except WebSocketDisconnect:
                logger.info(f"🔌 Telnyx WebSocket disconnected")
            except Exception as e:
                logger.error(f"❌ Error forwarding Telnyx audio: {e}", exc_info=True)
        
        # Task to receive transcripts from Deepgram and process
        async def process_deepgram_transcripts():
            nonlocal is_agent_speaking, last_agent_text
            
            try:
                async for message in deepgram_ws:
                    result = json.loads(message)
                    msg_type = result.get("type")
                    
                    if msg_type == "Results":
                        channel = result.get("channel", {})
                        alternatives = channel.get("alternatives", [])
                        
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "")
                            is_final = channel.get("is_final", False)
                            speech_final = result.get("speech_final", False)
                            
                            # Only process when we have final speech
                            if transcript and speech_final:
                                logger.info(f"📝 User said (final): {transcript}")
                                
                                # Mark user as finished speaking
                                session.mark_user_speaking_end()
                                logger.info(f"👤 User finished speaking")
                                
                                # Echo filter
                                if last_agent_text:
                                    transcript_lower = transcript.lower()
                                    agent_words = set(last_agent_text.lower().split())
                                    transcript_words = set(transcript_lower.split())
                                    
                                    if transcript_words and agent_words:
                                        overlap = len(transcript_words & agent_words)
                                        overlap_ratio = overlap / len(transcript_words)
                                        
                                        if overlap_ratio > 0.7:
                                            logger.warning(f"🔇 Filtered echo: {transcript} ({overlap_ratio:.0%})")
                                            continue
                                
                                # Mark agent as speaking to stop audio forwarding
                                is_agent_speaking = True
                                
                                # Save user transcript
                                await db.call_logs.update_one(
                                    {"call_id": call_control_id},
                                    {"$push": {
                                        "transcript": {
                                            "role": "user",
                                            "text": transcript,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    }}
                                )
                                
                                # Process through AI
                                response = await session.process_user_input(transcript)
                                response_text = response.get("text", "I'm sorry, I didn't understand that.")
                                
                                logger.info(f"🤖 AI response: {response_text}")
                                
                                # Save agent transcript
                                await db.call_logs.update_one(
                                    {"call_id": call_control_id},
                                    {"$push": {
                                        "transcript": {
                                            "role": "assistant",
                                            "text": response_text,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    }}
                                )
                                
                                # Get agent config for TTS routing
                                agent_config = session.agent_config
                                
                                # 🔥 CRITICAL FIX: Mark agent as speaking before emitting audio
                                session.mark_agent_speaking_start()
                                await telnyx_service.speak_text(call_control_id, response_text, agent_config=agent_config)
                                
                                # Speak via Telnyx with agent config for TTS routing
                                telnyx_service = get_telnyx_service()
                                logger.info(f"🔍 About to call speak_text with agent_config type: {type(agent_config)}, is None: {agent_config is None}")
                                if agent_config:
                                    logger.info(f"🔍 agent_config has settings: {'settings' in agent_config}")
                                await telnyx_service.speak_text(
                                    call_control_id, 
                                    response_text,
                                    agent_config=agent_config
                                )
                                logger.info(f"🔊 Spoke response")
                                
                                last_agent_text = response_text
                                call_data["last_agent_text"] = response_text
                                
                                # Check if should end call
                                if session.should_end_call:
                                    logger.info(f"📞 Ending node reached - hanging up")
                                    # Wait for speech to finish
                                    word_count = len(response_text.split())
                                    speech_duration = max(2, (word_count * 0.15) + 1)
                                    await asyncio.sleep(speech_duration)
                                    
                                    # Hangup
                                    await telnyx_service.hangup_call(call_control_id)
                                    
                                    # Cleanup
                                    # Clean up from Redis and in-memory
                                    redis_service.delete_call_data(call_control_id)
                                    if call_control_id in active_telnyx_calls:
                                        del active_telnyx_calls[call_control_id]
                                    break
                                
                                # Wait for speech to complete
                                word_count = len(response_text.split())
                                speech_duration = max(2, (word_count * 0.15) + 1)
                                await asyncio.sleep(speech_duration)
                                
                                # Resume listening
                                is_agent_speaking = False
                                logger.info(f"👂 Listening for next input...")
                    
                    elif msg_type == "SpeechStarted":
                        logger.debug(f"🎤 Speech started (VAD)")
                    
                    elif msg_type == "UtteranceEnd":
                        logger.debug(f"⏸️ Utterance ended (VAD)")
                        
            except Exception as e:
                logger.error(f"❌ Error processing Deepgram: {e}", exc_info=True)
        
        # Run both tasks concurrently
        logger.info(f"🚀 Starting bidirectional audio streaming...")
        await asyncio.gather(
            forward_telnyx_to_deepgram(),
            process_deepgram_transcripts()
        )
        
    except Exception as e:
        logger.error(f"❌ Fatal error in audio stream: {e}", exc_info=True)
    finally:
        logger.info(f"🧹 Cleaning up audio stream for {call_control_id}")
        if deepgram_ws:
            await deepgram_ws.close()
        try:
            await websocket.close()
        except:
            pass


async def transcribe_audio_deepgram(audio_data: bytes) -> str:
    """Transcribe audio using Deepgram Nova-3"""
    try:
        url = "https://api.deepgram.com/v1/listen"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/raw"
        }
        
        params = {
            "model": "nova-3",
            "encoding": "mulaw",
            "sample_rate": 8000,
            "channels": 1,
            "punctuate": True,
            "utterances": False
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                headers=headers,
                params=params,
                content=audio_data
            )
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                return transcript
            else:
                logger.error(f"Deepgram error: {response.status_code} - {response.text}")
                return ""
                
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return ""


async def transcribe_audio_deepgram_file(audio_data: bytes) -> str:
    """Transcribe audio file (WAV/MP3) using Deepgram Nova-3 with enhanced settings"""
    try:
        url = "https://api.deepgram.com/v1/listen"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/wav"
        }
        
        params = {
            "model": "nova-3",
            "punctuate": True,
            "utterances": False,
            "smart_format": True,
            "language": "en-US"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=headers,
                params=params,
                content=audio_data
            )
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                confidence = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("confidence", 0)
                logger.info(f"✅ Deepgram transcription (confidence: {confidence:.2f}): {transcript[:100]}...")
                return transcript
            else:
                logger.error(f"Deepgram error: {response.status_code} - {response.text}")
                return ""
                
    except Exception as e:
        logger.error(f"Error transcribing audio file: {e}")
        return ""


async def transcribe_audio_soniox_file(audio_data: bytes, api_key: str) -> str:
    """Transcribe audio file using Soniox REST API v1 - uses curl for reliable uploads"""
    import json as json_module
    import subprocess
    import tempfile
    import os as os_module
    
    try:
        base_url = "https://api.soniox.com"
        
        file_size_mb = len(audio_data) / (1024 * 1024)
        logger.info(f"Soniox: Uploading audio file ({file_size_mb:.2f} MB)...")
        
        # Write audio data to temp file for curl upload
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_file.name
        
        try:
            # Step 1: Upload file using curl (more reliable for large files)
            # Use --http1.1 to avoid HTTP/2 stream issues
            curl_cmd = [
                'curl', '-s', '--http1.1', '-X', 'POST',
                f'{base_url}/v1/files',
                '-H', f'Authorization: Bearer {api_key}',
                '-F', f'file=@{tmp_path}'
            ]
            
            logger.info(f"Soniox: Running curl upload command (HTTP/1.1)...")
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=300)
            
            logger.info(f"Soniox curl result: returncode={result.returncode}, stdout_len={len(result.stdout)}, stderr_len={len(result.stderr)}")
            
            if result.returncode != 0:
                logger.error(f"Soniox curl upload failed: returncode={result.returncode}, stderr={result.stderr}, stdout={result.stdout[:500]}")
                return ""
            
            if not result.stdout.strip():
                logger.error(f"Soniox curl returned empty stdout, stderr={result.stderr}")
                return ""
            
            try:
                upload_response = json_module.loads(result.stdout)
            except json_module.JSONDecodeError:
                logger.error(f"Soniox: Invalid JSON response from upload: {result.stdout[:500]}")
                return ""
            
            file_id = upload_response.get("id") or upload_response.get("file_id")
            if not file_id:
                logger.error(f"Soniox: No file_id in upload response: {upload_response}")
                return ""
            
            logger.info(f"Soniox: File uploaded, file_id={file_id}")
            
            # Step 2: Start transcription - use correct endpoint /v1/transcriptions and model stt-async-v3
            transcribe_payload = json_module.dumps({
                "file_id": file_id,
                "model": "stt-async-v3"
            })
            
            curl_cmd = [
                'curl', '-s', '--http1.1', '-X', 'POST',
                f'{base_url}/v1/transcriptions',
                '-H', f'Authorization: Bearer {api_key}',
                '-H', 'Content-Type: application/json',
                '-d', transcribe_payload
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Soniox curl transcription start failed: {result.stderr}")
                return ""
            
            try:
                transcribe_response = json_module.loads(result.stdout)
            except json_module.JSONDecodeError:
                logger.error(f"Soniox: Invalid JSON response from transcription start: {result.stdout}")
                return ""
            
            transcription_id = transcribe_response.get("id") or transcribe_response.get("transcription_id")
            if not transcription_id:
                logger.error(f"Soniox: No transcription_id in response: {transcribe_response}")
                return ""
            
            logger.info(f"Soniox: Transcription started, transcription_id={transcription_id}")
            
            # Step 3: Poll for status using /v1/transcriptions/{id}
            import asyncio
            max_polls = 60
            poll_interval = 2
            
            for i in range(max_polls):
                await asyncio.sleep(poll_interval)
                
                curl_cmd = [
                    'curl', '-s', '--http1.1', '-X', 'GET',
                    f'{base_url}/v1/transcriptions/{transcription_id}',
                    '-H', f'Authorization: Bearer {api_key}'
                ]
                
                result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    logger.error(f"Soniox curl poll failed: {result.stderr}")
                    continue
                
                try:
                    poll_response = json_module.loads(result.stdout)
                except json_module.JSONDecodeError:
                    logger.error(f"Soniox: Invalid JSON response from poll: {result.stdout}")
                    continue
                
                status = poll_response.get("status")
                
                if status == "completed":
                    # Step 4: Get transcript text from /v1/transcriptions/{id}/transcript
                    curl_cmd = [
                        'curl', '-s', '--http1.1', '-X', 'GET',
                        f'{base_url}/v1/transcriptions/{transcription_id}/transcript',
                        '-H', f'Authorization: Bearer {api_key}'
                    ]
                    
                    result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode != 0:
                        logger.error(f"Soniox curl get transcript failed: {result.stderr}")
                        return ""
                    
                    try:
                        transcript_response = json_module.loads(result.stdout)
                        transcript_text = transcript_response.get("text", "")
                        logger.info(f"Soniox: Transcription completed, {len(transcript_text)} chars")
                        return transcript_text
                    except json_module.JSONDecodeError:
                        logger.error(f"Soniox: Invalid JSON from transcript endpoint: {result.stdout}")
                        return ""
                    
                elif status == "error":
                    error_msg = poll_response.get("error_message", "Unknown error")
                    logger.error(f"Soniox transcription failed: {error_msg}")
                    return ""
                
                logger.info(f"Soniox: Status={status}, polling... ({i+1}/{max_polls})")
            
            logger.error("Soniox: Transcription timed out after polling")
            return ""
            
        finally:
            # Clean up temp file
            try:
                os_module.unlink(tmp_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error transcribing audio file with Soniox: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ""


async def transcribe_audio_file_dynamic(audio_data: bytes, stt_provider: str = "soniox", user_id: str = None) -> str:
    """
    Transcribe audio file using the configured STT provider
    
    Args:
        audio_data: Audio file bytes (WAV/MP3)
        stt_provider: STT provider to use ('soniox', 'deepgram', etc.)
        user_id: User ID to get API keys
        
    Returns:
        str: Transcribed text or empty string if failed
    """
    try:
        if stt_provider == "soniox":
            # Get Soniox API key - prefer environment key for reliability
            soniox_key = os.environ.get("SONIOX_API_KEY")
            
            if soniox_key:
                logger.info(f"Soniox: Using environment API key (first 10 chars): {soniox_key[:10]}...")
            else:
                # Fall back to user's DB key if no env key
                if user_id:
                    soniox_key = await get_api_key(user_id, "soniox")
                    if soniox_key:
                        logger.info(f"Soniox: Using user's DB API key (first 10 chars): {soniox_key[:10]}...")
            
            if not soniox_key:
                logger.error("❌ No Soniox API key available")
                return ""
            
            return await transcribe_audio_soniox_file(audio_data, soniox_key)
        
        elif stt_provider == "deepgram":
            return await transcribe_audio_deepgram_file(audio_data)
        
        else:
            logger.warning(f"⚠️ Unsupported STT provider for file transcription: {stt_provider}, falling back to Soniox")
            # Try Soniox as fallback
            soniox_key = os.environ.get("SONIOX_API_KEY")
            if soniox_key:
                return await transcribe_audio_soniox_file(audio_data, soniox_key)
            return ""
            
    except Exception as e:
        logger.error(f"Error in dynamic transcription: {e}")
        return ""


async def generate_audio_elevenlabs_streaming(text: str, settings: dict = None, user_id: str = None):
    """Generate audio using ElevenLabs TTS streaming API for lower latency"""
    try:
        # Get ElevenLabs settings from agent or use defaults
        elevenlabs_settings = settings.get("elevenlabs_settings", {}) if settings else {}
        
        voice_id = elevenlabs_settings.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        model = elevenlabs_settings.get("model", "eleven_turbo_v2_5")
        
        # Don't override if user explicitly chose a model
        # Just log what we're using
        if model == "eleven_v3":
            logger.info(f"🚀 Using Eleven v3 (Alpha - most expressive, not for real-time)")
        elif model == "eleven_turbo_v2":
            logger.info(f"⚡ Using Turbo v2 (balanced)")
        elif model == "eleven_multilingual_v3":
            # Legacy handling if someone has this in their config
            model = "eleven_v3"
            logger.info(f"🚀 Upgraded to Eleven v3 (Alpha)")
        elif model == "eleven_turbo_v2_5":
            logger.info(f"⚡ Using Turbo v2.5 (high quality)")
        elif model == "eleven_flash_v2_5":
            logger.info(f"⚡ Using Flash v2.5 (fastest - 75ms)")
        elif model == "eleven_flash_v2":
            logger.info(f"⚡ Using Flash v2 (fast)")
        
        stability = elevenlabs_settings.get("stability", 0.5)
        similarity_boost = elevenlabs_settings.get("similarity_boost", 0.75)
        style = elevenlabs_settings.get("style", 0.0)
        speed = elevenlabs_settings.get("speed", 1.0)
        use_speaker_boost = elevenlabs_settings.get("use_speaker_boost", True)
        enable_normalization = elevenlabs_settings.get("enable_normalization", True)
        enable_ssml_parsing = elevenlabs_settings.get("enable_ssml_parsing", False)
        
        # Convert boolean to ElevenLabs API format
        # apply_text_normalization accepts: 'auto', 'on', 'off'
        normalization_value = "on" if enable_normalization else "off"
        
        logger.info(f"🎙️ ElevenLabs streaming TTS: voice={voice_id}, model={model}, speed={speed}, normalization={normalization_value}, ssml={enable_ssml_parsing}")
        
        # Use streaming endpoint
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        
        # Get API key from user's keys or fallback to env
        if user_id:
            try:
                eleven_key = await get_user_api_key(user_id, "elevenlabs")
            except Exception as e:
                logger.error(f"Failed to get user ElevenLabs key: {e}")
                eleven_key = None
        else:
            eleven_key = os.environ.get('ELEVEN_API_KEY')
        
        if not eleven_key:
            logger.error("ElevenLabs API key not found")
            return None
        
        headers = {
            "xi-api-key": eleven_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "use_speaker_boost": use_speaker_boost,
                "speed": speed
            },
            "apply_text_normalization": normalization_value,
            "enable_ssml_parsing": enable_ssml_parsing,
            "optimize_streaming_latency": 4  # 0-4: Higher = more aggressive latency optimization (4 = max speed)
        }
        
        # Add style for v2 models only (v3 doesn't support it)
        if "v2" in model or "turbo" in model or "flash" in model:
            data["voice_settings"]["style"] = style
        
        # CRITICAL DEBUGGING: Log exact payload being sent
        logger.info(f"📦 ElevenLabs Request Payload:")
        logger.info(f"   Text length: {len(text)} chars")
        logger.info(f"   Text content: {repr(text)}")  # repr shows hidden chars
        logger.info(f"   Text bytes: {text.encode('utf-8')[:100]}")  # Check encoding
        logger.info(f"   Model: {model}")
        logger.info(f"   Voice ID: {voice_id}")
        logger.info(f"   URL: {url}")
        logger.info(f"   Full data: {data}")
        
        # Stream the response and collect chunks with retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                timeout_seconds = 10.0  # Reduced from 30s
                logger.info(f"🔌 Attempting ElevenLabs connection (attempt {attempt + 1}/{max_retries})")
                logger.info(f"   Timeout: {timeout_seconds}s")
                
                import time
                start_time = time.time()
                
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    client_created_time = time.time() - start_time
                    logger.info(f"   ✓ HTTP client created ({client_created_time:.3f}s)")
                    
                    logger.info(f"   → Sending POST request to ElevenLabs (optimize_latency=0)...")
                    async with client.stream('POST', url, headers=headers, json=data) as response:
                        connection_time = time.time() - start_time
                        logger.info(f"   ✓ Connection established ({connection_time:.3f}s) [TARGET: <200ms]")
                        logger.info(f"   ✓ Response status: {response.status_code}")
                        if response.status_code == 200:
                            chunks = []
                            chunk_count = 0
                            first_chunk_time = None
                            logger.info(f"   → Streaming audio chunks...")
                            async for chunk in response.aiter_bytes():
                                chunk_count += 1
                                chunks.append(chunk)
                                if chunk_count == 1:
                                    first_chunk_time = time.time() - start_time
                                    logger.info(f"   ✓ FIRST CHUNK received ({first_chunk_time:.3f}s, {len(chunk)} bytes) [TARGET: <300ms]")
                            
                            all_chunks_time = time.time() - start_time
                            logger.info(f"   ✓ ALL CHUNKS received: {chunk_count} chunks ({all_chunks_time:.3f}s)")
                            audio_data = b''.join(chunks)
                            logger.info(f"   ✓ Total audio size: {len(audio_data)} bytes")
                            logger.info(f"   📊 TTS API TIMING BREAKDOWN:")
                            logger.info(f"      - Connection: {connection_time*1000:.0f}ms")
                            logger.info(f"      - First chunk: {first_chunk_time*1000:.0f}ms")
                            logger.info(f"      - All chunks: {all_chunks_time*1000:.0f}ms")
                            logger.info(f"      - Audio generation only: {(first_chunk_time - connection_time)*1000:.0f}ms")
                            
                            if len(audio_data) > 0:
                                return audio_data
                            else:
                                logger.warning(f"ElevenLabs returned empty audio (attempt {attempt + 1}/{max_retries})")
                        else:
                            error_text = await response.aread()
                            logger.error(f"ElevenLabs error: {response.status_code} - {error_text}")
                            
            except httpx.TimeoutException:
                logger.error(f"ElevenLabs timeout after {timeout_seconds}s (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # Brief pause before retry
                    continue
            except Exception as e:
                logger.error(f"Error generating ElevenLabs audio (attempt {attempt + 1}/{max_retries}): {e}")
                import traceback
                logger.error(traceback.format_exc())
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
        
        # All retries failed
        logger.error(f"ElevenLabs TTS failed after {max_retries} attempts")
        return None
                
    except Exception as e:
        logger.error(f"Unexpected error in ElevenLabs TTS: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def generate_audio_elevenlabs(text: str, settings: dict = None, user_id: str = None) -> bytes:
    """Generate audio using ElevenLabs TTS with advanced settings"""
    # Use streaming version for lower latency
    return await generate_audio_elevenlabs_streaming(text, settings, user_id)

async def generate_audio_hume(text: str, settings: dict = None, user_id: str = None) -> bytes:
    """Generate audio using Hume AI TTS with emotional voice synthesis"""
    try:
        # Get Hume settings from agent or use defaults
        hume_settings = settings.get("hume_settings", {}) if settings else {}
        
        voice_name = hume_settings.get("voice_name", "ITO")
        description = hume_settings.get("description", "warm and friendly")
        speed = hume_settings.get("speed", 1.0)
        
        logger.info(f"🎭 Hume AI TTS: voice={voice_name}, emotion={description}, speed={speed}")
        
        # Get API key from user's keys or fallback to env
        if user_id:
            try:
                hume_key = await get_user_api_key(user_id, "hume")
            except Exception as e:
                logger.error(f"Failed to get user Hume key: {e}")
                hume_key = None
        else:
            hume_key = os.environ.get("HUME_API_KEY")
        
        if not hume_key:
            logger.error("Hume API key not found")
            return b""
        
        try:
            from hume.client import AsyncHumeClient
            from hume.tts.types import PostedUtterance, PostedUtteranceVoiceWithId
            
            client = AsyncHumeClient(api_key=hume_key)
            
            # voice_name is actually the voice_id from Hume
            voice_id = voice_name  # The setting stores the voice ID
            
            # Create utterance object with text and voice ID
            utterance = PostedUtterance(
                text=text,
                voice=PostedUtteranceVoiceWithId(id=voice_id),  # Use voice ID
                speed=speed
            )
            
            # Use Hume TTS streaming for low latency
            audio_chunks = []
            
            # Use synthesize_json_streaming (the correct method)
            async for chunk in client.tts.synthesize_json_streaming(
                utterances=[utterance],
                version="2",  # Use version 2 for better quality
                strip_headers=True,  # Remove WAV headers for clean concatenation
            ):
                # Chunks can be SnippetAudioChunk or TimestampMessage
                # Debug: check what attributes the chunk has
                if hasattr(chunk, 'snippet') and chunk.snippet is not None:
                    audio_chunks.append(chunk.snippet)
                elif hasattr(chunk, 'data') and chunk.data is not None:
                    audio_chunks.append(chunk.data)
                elif hasattr(chunk, 'audio') and chunk.audio is not None:
                    audio_chunks.append(chunk.audio)
                elif isinstance(chunk, bytes):
                    audio_chunks.append(chunk)
                else:
                    # Log what we got to understand structure
                    logger.debug(f"Unknown chunk type: {type(chunk)}, attrs: {[a for a in dir(chunk) if not a.startswith('_')][:10]}")
            
            # Combine all chunks (convert strings to bytes if needed)
            if audio_chunks:
                # Check if first chunk is string or bytes
                if isinstance(audio_chunks[0], str):
                    # Chunks are base64 encoded strings
                    import base64
                    complete_audio = b''.join([base64.b64decode(chunk) for chunk in audio_chunks])
                else:
                    complete_audio = b''.join(audio_chunks)
            else:
                complete_audio = b''
                
            logger.info(f"✅ Generated {len(complete_audio)} bytes of Hume audio ({len(audio_chunks)} chunks)")
            return complete_audio
            
        except ImportError as e:
            logger.error(f"Hume library not installed correctly: {e}")
            return b""
        except Exception as e:
            logger.error(f"Error with Hume API: {e}")
            logger.exception(e)
            return b""
                
    except Exception as e:
        logger.error(f"Error generating Hume audio: {e}")
        return b""

async def generate_audio_cartesia(text: str, settings: dict = None, user_id: str = None) -> bytes:
    """Generate audio using Cartesia Sonic TTS - Properly formatted for Telnyx"""
    try:
        import time
        import subprocess
        import tempfile
        import os
        
        total_start = time.time()
        
        # Get Cartesia API key from user's keys or fallback to env
        if user_id:
            try:
                cartesia_api_key = await get_user_api_key(user_id, "cartesia")
            except Exception as e:
                logger.error(f"Failed to get user Cartesia key: {e}")
                cartesia_api_key = None
        else:
            cartesia_api_key = os.environ.get("CARTESIA_API_KEY")
        
        if not cartesia_api_key:
            logger.error("No Cartesia API key found")
            return b""
        
        # Initialize Cartesia service
        from cartesia_service import CartesiaService
        cartesia = CartesiaService(api_key=cartesia_api_key)
        
        # Get voice settings
        cartesia_settings = settings.get("cartesia_settings", {}) if settings else {}
        voice_id = cartesia_settings.get("voice_id", "a0e99841-438c-4a64-b679-ae501e7d6091")
        model = cartesia_settings.get("model", "sonic-2")
        
        logger.info(f"🎙️ Cartesia: Generating with voice {voice_id}, model {model}")
        
        # Request PCM at 22050Hz (Cartesia's native rate)
        output_format = {
            "container": "raw",
            "encoding": "pcm_s16le",  # 16-bit PCM signed little-endian
            "sample_rate": 22050  # Cartesia's native rate
        }
        
        api_start = time.time()
        
        audio_pcm = await cartesia.generate_speech(
            text=text,
            voice_id=voice_id,
            model=model,
            output_format=output_format
        )
        
        api_time = time.time() - api_start
        
        if not audio_pcm or len(audio_pcm) == 0:
            logger.error("Cartesia returned empty audio")
            return b""
        
        logger.info(f"✅ Cartesia: Generated {len(audio_pcm)} bytes PCM 22050Hz")
        
        # Convert PCM 22050Hz to MP3 44100Hz using ffmpeg (standard telephony conversion)
        with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as pcm_file:
            pcm_file.write(audio_pcm)
            pcm_path = pcm_file.name
        
        mp3_path = pcm_path.replace('.pcm', '.mp3')
        
        convert_start = time.time()
        
        try:
            # Convert: 22050Hz PCM → 44100Hz MP3 (standard rates for quality)
            subprocess.run([
                'ffmpeg',
                '-f', 's16le',        # 16-bit signed PCM
                '-ar', '22050',       # Input: 22050Hz (Cartesia native)
                '-ac', '1',           # Mono
                '-i', pcm_path,       # Input file
                '-ar', '44100',       # Output: 44100Hz (standard for telephony)
                '-b:a', '128k',       # 128kbps bitrate for quality
                '-y',                 # Overwrite
                mp3_path              # Output file
            ], check=True, capture_output=True, timeout=5)
            
            convert_time = time.time() - convert_start
            
            # Read MP3 file
            with open(mp3_path, 'rb') as f:
                mp3_audio = f.read()
            
            total_time = time.time() - total_start
            
            logger.info(f"✅ Cartesia: Converted to {len(mp3_audio)} bytes MP3 44100Hz")
            logger.info(f"⏱️  Cartesia API time: {api_time*1000:.0f}ms")
            logger.info(f"⏱️  Conversion time: {convert_time*1000:.0f}ms")
            logger.info(f"⏱️  Cartesia total time: {total_time*1000:.0f}ms")
            
            return mp3_audio
            
        finally:
            # Cleanup temp files
            try:
                os.remove(pcm_path)
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error generating Cartesia audio: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return b""

# Simple in-memory TTS cache for common responses
_tts_cache = {}

async def generate_tts_audio(text: str, agent_config: dict) -> bytes:
    """
    Generate TTS audio based on agent's configured provider
    Routes to ElevenLabs, Hume, Sesame, Cartesia, or MeloTTS based on settings
    Optionally mixes comfort noise if enabled in agent settings
    """
    try:
        settings = agent_config.get("settings", {})
        tts_provider = settings.get("tts_provider")
        user_id = agent_config.get("user_id")  # Get user_id from agent config
        enable_comfort_noise = settings.get("enable_comfort_noise", False)  # Get comfort noise setting
        
        # TTS provider is REQUIRED - no defaults
        if not tts_provider:
            logger.error("❌ No TTS provider configured for agent")
            return None
        
        # Check cache for common/scripted responses (Iteration 7 optimization)
        cache_key = f"{tts_provider}:{text[:200]}"  # Use first 200 chars as key
        if cache_key in _tts_cache:
            logger.info(f"💾 TTS CACHE HIT: Returning cached audio ({len(_tts_cache[cache_key])} bytes)")
            return _tts_cache[cache_key]
        
        import datetime
        tts_start_time = time.time()
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.info(f"⏱️ [{timestamp_str}] 🔊 TTS REQUEST START: provider={tts_provider}, user={user_id[:8] if user_id else 'unknown'}, comfort_noise={enable_comfort_noise}")
        
        # Generate audio using configured provider
        audio_bytes = None
        
        if tts_provider == "elevenlabs":
            audio_bytes = await generate_audio_elevenlabs_streaming(text, settings, user_id)
        elif tts_provider == "cartesia":
            audio_bytes = await generate_audio_cartesia(text, settings, user_id)
        elif tts_provider == "hume":
            audio_bytes = await generate_audio_hume(text, settings, user_id)
        elif tts_provider == "melo":
            # Use MeloTTS
            try:
                melo_settings = settings.get("melo_settings", {})
                voice = melo_settings.get("voice", "EN-US")
                speed = melo_settings.get("speed", 1.2)
                clone_wav = melo_settings.get("clone_wav", None)
                
                logger.info(f"🎤 Generating MeloTTS audio (Voice: {voice}, Speed: {speed})")
                
                melo_service = MeloTTSService()
                wav_bytes = await melo_service.generate_audio(
                    text=text,
                    voice=voice,
                    speed=speed,
                    clone_wav=clone_wav
                )
                
                logger.info(f"✅ MeloTTS generated {len(wav_bytes)} bytes WAV")
                
                # Convert WAV to MP3 for Telnyx compatibility
                import io
                import tempfile
                import subprocess
                
                # Write WAV to temp file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                    wav_path = wav_file.name
                    wav_file.write(wav_bytes)
                
                # Convert to MP3 with 8kHz sample rate for telephony
                mp3_path = wav_path.replace('.wav', '.mp3')
                result = subprocess.run([
                    'ffmpeg', '-y',
                    '-i', wav_path,
                    '-ar', '8000',  # Resample to 8kHz (telephony standard)
                    '-ac', '1',     # Mono
                    '-b:a', '64k',  # 64kbps bitrate
                    mp3_path
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"❌ ffmpeg conversion failed: {result.stderr}")
                    os.unlink(wav_path)
                    logger.warning("⚠️ Falling back to ElevenLabs")
                    return await generate_audio_elevenlabs(text, settings, user_id)
                
                # Read MP3 file
                with open(mp3_path, 'rb') as f:
                    mp3_audio = f.read()
                
                # Cleanup
                os.unlink(wav_path)
                os.unlink(mp3_path)
                
                logger.info(f"✅ MeloTTS converted to MP3: {len(mp3_audio)} bytes")
                audio_bytes = mp3_audio
                
            except Exception as e:
                logger.error(f"❌ MeloTTS error: {e}")
                logger.warning("⚠️ MeloTTS failed, falling back to ElevenLabs")
                audio_bytes = await generate_audio_elevenlabs(text, settings, user_id)
        elif tts_provider == "dia":
            # Use Dia TTS (OpenAI-compatible API)
            try:
                from dia_tts_service import DiaTTSService
                
                dia_settings = settings.get("dia_settings", {})
                voice = dia_settings.get("voice", "S1")
                speed = dia_settings.get("speed", 1.0)
                response_format = dia_settings.get("response_format", "wav")
                
                logger.info(f"🎤 Generating Dia TTS audio (Voice: {voice}, Speed: {speed}, Format: {response_format})")
                
                dia_service = DiaTTSService()
                audio_bytes = await dia_service.generate_audio(
                    text=text,
                    voice=voice,
                    speed=speed,
                    response_format=response_format
                )
                
                logger.info(f"✅ Dia TTS generated {len(audio_bytes)} bytes ({response_format})")
                
                # If WAV format, convert to MP3 for Telnyx compatibility
                if response_format == "wav":
                    import io
                    import tempfile
                    import subprocess
                    
                    # Write audio to temp file
                    with tempfile.NamedTemporaryFile(suffix=f'.{response_format}', delete=False) as audio_file:
                        audio_path = audio_file.name
                        audio_file.write(audio_bytes)
                    
                    # Convert to MP3 with 8kHz sample rate for telephony
                    mp3_path = audio_path.replace(f'.{response_format}', '.mp3')
                    result = subprocess.run([
                        'ffmpeg', '-y',
                        '-i', audio_path,
                        '-ar', '8000',  # Resample to 8kHz (telephony standard)
                        '-ac', '1',     # Mono
                        '-b:a', '64k',  # 64kbps bitrate
                        mp3_path
                    ], capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        logger.error(f"❌ ffmpeg conversion failed: {result.stderr}")
                        os.unlink(audio_path)
                        logger.warning("⚠️ Falling back to ElevenLabs")
                        audio_bytes = await generate_audio_elevenlabs(text, settings, user_id)
                    else:
                        # Read MP3 file
                        with open(mp3_path, 'rb') as f:
                            mp3_audio = f.read()
                        
                        # Cleanup
                        os.unlink(audio_path)
                        os.unlink(mp3_path)
                        
                        logger.info(f"✅ Dia TTS converted to MP3: {len(mp3_audio)} bytes")
                        audio_bytes = mp3_audio
                else:
                    # If already MP3 or other format, use as-is
                    pass  # audio_bytes already set above
                
            except Exception as e:
                logger.error(f"❌ Dia TTS error: {e}")
                logger.warning("⚠️ Dia TTS failed, falling back to ElevenLabs")
                audio_bytes = await generate_audio_elevenlabs(text, settings, user_id)
        elif tts_provider == "kokoro":
            # Use Kokoro TTS (Open-source fast TTS)
            try:
                from kokoro_tts_service import KokoroTTSService
                
                kokoro_settings = settings.get("kokoro_settings", {})
                voice = kokoro_settings.get("voice", "af_bella")
                speed = kokoro_settings.get("speed", 1.0)
                response_format = kokoro_settings.get("response_format", "mp3")
                
                logger.info(f"🎤 Generating Kokoro TTS audio (Voice: {voice}, Speed: {speed})")
                
                kokoro_service = KokoroTTSService()
                audio_bytes = await kokoro_service.generate_audio(
                    text=text,
                    voice=voice,
                    speed=speed,
                    response_format=response_format
                )
                
                logger.info(f"✅ Kokoro TTS generated {len(audio_bytes)} bytes")
                # audio_bytes already set
                
            except Exception as e:
                logger.error(f"❌ Kokoro TTS error: {e}")
                logger.warning("⚠️ Kokoro TTS failed, falling back to Cartesia")
                audio_bytes = await generate_audio_cartesia(text, settings)
        
        elif tts_provider == "chattts":
            # Use ChatTTS (Ultra-low latency conversational TTS)
            try:
                from chattts_tts_service import ChatTTSClient
                import subprocess
                import tempfile
                
                chattts_settings = settings.get("chattts_settings", {})
                voice = chattts_settings.get("voice", "female_1")
                speed = chattts_settings.get("speed", 1.0)
                temperature = chattts_settings.get("temperature", 0.3)
                
                logger.info(f"🎤 Generating ChatTTS audio (Voice: {voice}, Speed: {speed}, Temp: {temperature})")
                
                # Get API URLs from environment (supports multiple instances)
                chattts_api_urls_str = os.environ.get("CHATTTS_API_URLS", "")
                chattts_api_url = os.environ.get("CHATTTS_API_URL", "http://203.57.40.119:10129")
                
                # Parse multiple URLs if provided
                if chattts_api_urls_str:
                    api_urls = [url.strip() for url in chattts_api_urls_str.split(',') if url.strip()]
                    chattts_client = ChatTTSClient(api_urls=api_urls)
                    logger.info(f"Using {len(api_urls)} ChatTTS instances for load balancing")
                else:
                    chattts_client = ChatTTSClient(api_url=chattts_api_url)
                
                # Request WAV format from ChatTTS
                audio_bytes_wav, metadata = await chattts_client.generate_tts(
                    text=text,
                    voice=voice,
                    speed=speed,
                    temperature=temperature,
                    response_format="wav"  # Get WAV from ChatTTS
                )
                
                logger.info(f"✅ ChatTTS generated {len(audio_bytes_wav)} bytes (WAV)")
                if metadata:
                    logger.info(f"   RTF: {metadata.get('rtf')}, Processing: {metadata.get('processing_time')}s")
                    logger.info(f"   Instance: {metadata.get('instance_url', 'N/A')}")
                
                # Convert ChatTTS WAV (24000Hz) to MP3 (44100Hz) for Telnyx compatibility
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                    wav_file.write(audio_bytes_wav)
                    wav_path = wav_file.name
                
                mp3_path = wav_path.replace('.wav', '.mp3')
                
                try:
                    # Convert: 24000Hz WAV → 8000Hz MP3 (telephony standard for PSTN/Telnyx)
                    subprocess.run([
                        'ffmpeg',
                        '-i', wav_path,           # Input WAV file
                        '-ar', '8000',            # Resample to 8000Hz for telephony
                        '-ac', '1',               # Mono
                        '-b:a', '64k',            # 64kbps bitrate (sufficient for telephony)
                        '-y',                     # Overwrite output
                        mp3_path
                    ], check=True, capture_output=True)
                    
                    # Read converted MP3
                    with open(mp3_path, 'rb') as f:
                        audio_bytes = f.read()
                    
                    logger.info(f"✅ Converted to MP3 8000Hz (telephony): {len(audio_bytes)} bytes")
                    # audio_bytes already set
                    
                finally:
                    # Cleanup temp files
                    import os
                    try:
                        os.unlink(wav_path)
                        os.unlink(mp3_path)
                    except:
                        pass
                
            except Exception as e:
                logger.error(f"❌ ChatTTS error: {e}")
                logger.warning("⚠️ ChatTTS failed, falling back to Cartesia")
                audio_bytes = await generate_audio_cartesia(text, settings)

        elif tts_provider == "sesame":
            # Use WebSocket streaming for real-time audio
            from sesame_ws_service import stream_sesame_tts
            import io
            
            try:
                sesame_settings = settings.get("sesame_settings", {})
                speaker_id = sesame_settings.get("speaker_id", 0)
                
                logger.info(f"🚀 Streaming Sesame TTS via WebSocket (Speaker {speaker_id})")
                
                # Stream audio chunks and aggregate
                audio_chunks = []
                chunk_count = 0
                
                async for chunk in stream_sesame_tts(text, speaker_id):
                    chunk_count += 1
                    audio_chunks.append(chunk)
                    
                    if chunk_count == 1:
                        logger.info(f"⚡ First audio chunk received (WebSocket streaming)")
                
                if not audio_chunks:
                    logger.error("❌ No audio chunks received from Sesame WebSocket")
                    logger.warning("⚠️ Sesame WebSocket failed, falling back to ElevenLabs")
                    audio_bytes = await generate_audio_elevenlabs(text, settings, user_id)
                
                # Combine all chunks into complete audio
                audio_bytes = b''.join(audio_chunks)
                logger.info(f"✅ Sesame WebSocket complete: {chunk_count} chunks, {len(audio_bytes)} bytes")
                
                # Convert raw PCM int16 24kHz to WAV format for Telnyx
                import wave
                import tempfile
                import subprocess
                
                # Create WAV file from raw PCM
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                    wav_path = wav_file.name
                    with wave.open(wav_path, 'wb') as wav:
                        wav.setnchannels(1)  # Mono
                        wav.setsampwidth(2)  # 16-bit = 2 bytes
                        wav.setframerate(24000)  # 24kHz
                        wav.writeframes(audio_bytes)
                
                logger.info(f"🔄 Converting Sesame PCM to MP3 ({len(audio_bytes)} bytes)")
                
                # Convert to MP3 with resampling to 8kHz for Telnyx compatibility
                mp3_path = wav_path.replace('.wav', '.mp3')
                result = subprocess.run([
                    'ffmpeg', '-y',
                    '-i', wav_path,
                    '-ar', '8000',  # Resample to 8kHz (Telnyx mulaw rate)
                    '-ac', '1',     # Mono
                    '-b:a', '64k',  # 64kbps bitrate
                    mp3_path
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"❌ ffmpeg conversion failed: {result.stderr}")
                    os.unlink(wav_path)
                    logger.warning("⚠️ Falling back to ElevenLabs")
                    audio_bytes = await generate_audio_elevenlabs(text, settings, user_id)
                else:
                    # Read MP3 file
                    with open(mp3_path, 'rb') as f:
                        mp3_audio = f.read()
                    
                    # Cleanup
                    os.unlink(wav_path)
                    os.unlink(mp3_path)
                    
                    logger.info(f"✅ Sesame audio converted to MP3: {len(mp3_audio)} bytes")
                    audio_bytes = mp3_audio
                
            except Exception as e:
                logger.error(f"❌ Sesame WebSocket error: {e}")
                logger.warning("⚠️ Falling back to ElevenLabs")
                audio_bytes = await generate_audio_elevenlabs(text, settings, user_id)

        elif tts_provider == "maya":
            # Use Maya TTS for expressive voice with emotion tags
            try:
                from maya_tts_service import MayaTTSService
                
                maya_settings = settings.get("maya_settings", {})
                voice_ref = maya_settings.get("voice_ref", "A warm, professional female voice")
                temperature = maya_settings.get("temperature", 0.35)
                seed = maya_settings.get("seed", 0)
                speaker_wav_id = maya_settings.get("speaker_wav_id")
                
                logger.info(f"🎤 Maya TTS: voice='{voice_ref[:50]}...', temp={temperature}, seed={seed}")
                
                # Load cloned voice if specified
                speaker_wav_data = None
                if speaker_wav_id:
                    try:
                        from voice_library_router import load_voice_sample
                        speaker_wav_data = await load_voice_sample(speaker_wav_id, user_id)
                        if speaker_wav_data:
                            logger.info(f"🎤 Using cloned voice from library: {speaker_wav_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load voice sample: {e}")
                
                # Generate audio
                maya_service = MayaTTSService()
                audio_bytes = await maya_service.generate_speech(
                    text=text,
                    voice_ref=voice_ref,
                    temperature=temperature,
                    seed=seed,
                    speaker_wav=speaker_wav_data,
                    output_format="wav"
                )
                
                if audio_bytes:
                    logger.info(f"✅ Maya TTS generated {len(audio_bytes)} bytes")
                    
                    # Convert WAV to MP3 for Telnyx compatibility
                    import tempfile
                    import subprocess
                    import os  # Fix: Import os locally
                    
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                        wav_path = wav_file.name
                        wav_file.write(audio_bytes)
                    
                    mp3_path = wav_path.replace('.wav', '.mp3')
                    result = subprocess.run([
                        'ffmpeg', '-y',
                        '-i', wav_path,
                        '-ar', '8000',  # Resample to 8kHz for Telnyx
                        '-ac', '1',     # Mono
                        '-b:a', '64k',  # 64kbps bitrate
                        mp3_path
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        with open(mp3_path, 'rb') as f:
                            audio_bytes = f.read()
                        logger.info(f"✅ Maya audio converted to MP3: {len(audio_bytes)} bytes")
                        try:
                            os.unlink(wav_path)
                            os.unlink(mp3_path)
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to cleanup temp files: {e}")
                    else:
                        logger.error(f"❌ ffmpeg conversion failed: {result.stderr}")
                        try:
                            os.unlink(wav_path)
                        except:
                            pass
                        audio_bytes = None
                else:
                    logger.warning("⚠️ Maya TTS returned no audio")
                    audio_bytes = None
                    
            except Exception as e:
                logger.error(f"❌ Maya TTS error: {e}")
                # Don't fallback to ElevenLabs to avoid using old voice settings
                audio_bytes = None
                logger.error(f"❌ Maya TTS error: {e}")
                audio_bytes = None
            
            # Fallback to ElevenLabs if Maya failed
            if not audio_bytes:
                logger.warning("⚠️ Maya TTS failed, falling back to ElevenLabs")
                audio_bytes = await generate_audio_elevenlabs(text, settings, user_id)

        else:
            # Default to ElevenLabs
            audio_bytes = await generate_audio_elevenlabs_streaming(text, settings, user_id)
        
        # NOTE: Comfort noise is now handled as continuous background overlay (started at call beginning)
        # No need to mix into each TTS chunk - cleaner and more natural
        
        tts_end_time = time.time()
        tts_latency_ms = int((tts_end_time - tts_start_time) * 1000)
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.info(f"⏱️ [{timestamp_str}] 🔊 TTS COMPLETE: {tts_latency_ms}ms, audio_size={len(audio_bytes) if audio_bytes else 0} bytes")
        
        # Cache the audio for common responses (Iteration 7 optimization)
        if audio_bytes and len(text) < 500:  # Only cache short/scripted responses
            _tts_cache[cache_key] = audio_bytes
            logger.info(f"💾 TTS CACHED: {cache_key[:60]}... ({len(audio_bytes)} bytes)")
        
        return audio_bytes
            
    except Exception as e:
        logger.error(f"Error in TTS generation routing: {e}")
        # Fallback to basic ElevenLabs
        audio_bytes = await generate_audio_elevenlabs(text, None, user_id)
        return audio_bytes


# ==================== CALL LOGGING HELPERS ====================

async def create_call_log(
    call_id: str,
    agent_id: str,
    direction: str,
    from_number: str,
    to_number: str,
    user_id: str,
    phone_number_id: Optional[str] = None
) -> dict:
    """Create a new call log entry"""
    try:
        call_log = {
            "id": str(uuid.uuid4()),
            "call_id": call_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "phone_number_id": phone_number_id,
            "direction": direction,
            "from_number": from_number,
            "to_number": to_number,
            "status": "queued",
            "end_reason": None,
            "duration": 0,
            "cost": 0.0,
            "start_time": datetime.utcnow(),
            "end_time": None,
            "answered_at": None,
            "sentiment": "unknown",
            "transcript": [],
            "summary": "",
            "latency_avg": 0.0,
            "latency_p50": 0.0,
            "latency_p90": 0.0,
            "latency_p99": 0.0,
            "user_sentiment_score": 0.0,
            "recording_url": None,
            "recording_id": None,
            "recording_duration": 0,
            "custom_variables": {},
            "metadata": {},
            "error_message": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            # Initialize logs array with call start event
            "logs": [{
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "type": "call_start",
                "message": f"Call initiated - Direction: {direction}, From: {from_number}, To: {to_number}",
                "details": {
                    "direction": direction,
                    "from_number": from_number,
                    "to_number": to_number,
                    "agent_id": agent_id
                }
            }]
        }
        
        await db.call_logs.insert_one(call_log)
        logger.info(f"📝 Created call log: {call_id}")
        return call_log
    except Exception as e:
        logger.error(f"Error creating call log: {e}")
        return None


async def update_call_log(call_id: str, updates: dict):
    """Update an existing call log"""
    try:
        updates["updated_at"] = datetime.utcnow()
        
        result = await db.call_logs.update_one(
            {"call_id": call_id},
            {"$set": updates}
        )
        
        if result.modified_count > 0:
            logger.info(f"📝 Updated call log: {call_id}")
        
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating call log: {e}")
        return False


async def append_transcript(call_id: str, role: str, text: str, timestamp: datetime = None):
    """Append a message to the call transcript"""
    try:
        message = {
            "role": role,  # "user" or "assistant"
            "text": text,
            "timestamp": (timestamp or datetime.utcnow()).isoformat()
        }
        
        await db.call_logs.update_one(
            {"call_id": call_id},
            {
                "$push": {"transcript": message},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        logger.debug(f"📝 Appended transcript for {call_id}: {role}")
    except Exception as e:
        logger.error(f"Error appending transcript: {e}")


async def finalize_call_log(call_id: str, end_reason: str = None, error_message: str = None):
    """Finalize call log with end time and status"""
    try:
        # Get the call log
        call_log = await db.call_logs.find_one({"call_id": call_id})
        
        if not call_log:
            logger.warning(f"⚠️ Call log not found for finalization: {call_id}")
            return False
        
        # Calculate duration from start_time to now
        start_time = call_log.get("start_time")
        answered_at = call_log.get("answered_at")
        end_time = datetime.utcnow()
        duration = 0
        
        # Calculate duration from when call was answered (or started if never answered)
        if answered_at:
            # Use answered time as start for more accurate duration
            if isinstance(answered_at, str):
                answered_at = datetime.fromisoformat(answered_at.replace('Z', '+00:00'))
            duration = int((end_time - answered_at).total_seconds())
        elif start_time:
            # Fall back to start_time if never answered
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            duration = int((end_time - start_time).total_seconds())
        
        # Ensure duration is positive
        duration = max(0, duration)
        
        # Determine status
        status = "completed" if end_reason in ["hangup", "completed"] else "failed"
        if error_message:
            status = "failed"
        
        # Calculate cost (rough estimate: $0.01 per minute)
        cost = (duration / 60) * 0.01
        
        updates = {
            "end_time": end_time,
            "duration": duration,
            "cost": round(cost, 4),
            "status": status,
            "end_reason": end_reason or "unknown",
            "error_message": error_message
        }
        
        await update_call_log(call_id, updates)
        
        # Add call end log entry with full details
        await db.call_logs.update_one(
            {"call_id": call_id},
            {"$push": {
                "logs": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "info",
                    "type": "call_end",
                    "message": f"Call ended - Duration: {duration}s, Status: {status}, Reason: {end_reason or 'unknown'}",
                    "details": {
                        "duration_seconds": duration,
                        "status": status,
                        "end_reason": end_reason or "unknown",
                        "cost": round(cost, 4),
                        "error_message": error_message
                    }
                }
            }}
        )
        
        logger.info(f"✅ Finalized call log: {call_id} (duration={duration}s, status={status})")
        
        # Save session variables to call_log for CRM and analytics
        try:
            from core_calling_service import get_call_session
            session = await get_call_session(call_id)
            if session and hasattr(session, 'session_variables') and session.session_variables:
                # Store extracted variables in call_log
                await db.call_logs.update_one(
                    {"call_id": call_id},
                    {"$set": {"extracted_variables": dict(session.session_variables)}}
                )
                logger.info(f"📦 Saved {len(session.session_variables)} session variables to call_log: {list(session.session_variables.keys())}")
        except Exception as var_err:
            logger.debug(f"Could not save session variables (session may be closed): {var_err}")
        
        # AUTO-CAMPAIGN ASSOCIATION: Add call to campaign if agent has campaign_id set
        try:
            call_log = await db.call_logs.find_one({"call_id": call_id})
            if call_log and call_log.get("agent_id"):
                agent = await db.agents.find_one({"id": call_log.get("agent_id")})
                if agent:
                    # Check agent's auto_qc_settings for campaign_id
                    auto_qc_settings = agent.get("auto_qc_settings", {})
                    campaign_id = auto_qc_settings.get("campaign_id") if isinstance(auto_qc_settings, dict) else None
                    
                    if campaign_id:
                        # Add call to campaign's calls list
                        campaign_call = {
                            "id": str(uuid.uuid4()),
                            "campaign_id": campaign_id,
                            "call_id": call_id,
                            "call_log_id": call_log.get("id", call_id),
                            "agent_id": call_log.get("agent_id"),
                            "added_at": datetime.utcnow(),
                            "status": "pending",
                            "direction": call_log.get("direction", "outbound"),
                            "duration": duration,
                            "from_number": call_log.get("from_number"),
                            "to_number": call_log.get("to_number"),
                            "transcript": call_log.get("transcript", []),
                            "recording_url": call_log.get("recording_url"),
                            "user_id": call_log.get("user_id")
                        }
                        
                        await db.campaign_calls.insert_one(campaign_call)
                        
                        # Update campaign's total_calls count
                        await db.campaigns.update_one(
                            {"id": campaign_id},
                            {"$inc": {"total_calls": 1}}
                        )
                        
                        logger.info(f"📊 Auto-added call {call_id} to campaign {campaign_id}")
        except Exception as campaign_err:
            logger.error(f"Error auto-adding call to campaign: {campaign_err}")
        
        # POST-CALL WEBHOOK: Send transcript to external webhook if configured
        try:
            call_log = await db.call_logs.find_one({"call_id": call_id})
            if call_log and call_log.get("agent_id"):
                agent = await db.agents.find_one({"id": call_log.get("agent_id")})
                if agent:
                    # Check if post_call_webhook_url is configured in agent settings
                    agent_settings = agent.get("settings", {}) or {}
                    
                    # Check if post_call_webhook_url is configured in agent settings
                    post_call_webhook_url = agent_settings.get("post_call_webhook_url")
                    # Backwards compatible: fire webhook if URL exists and active is not explicitly False
                    # (undefined/None = enabled for existing configs, only False = disabled)
                    is_webhook_active = agent_settings.get("post_call_webhook_active")
                    should_fire_webhook = post_call_webhook_url and is_webhook_active is not False
                    
                    if should_fire_webhook:
                        logger.info(f"📤 Sending post-call webhook to: {post_call_webhook_url}")
                        
                        # Build webhook payload
                        webhook_payload = {
                            "event": "call.completed",
                            "call_id": call_id,
                            "agent_id": call_log.get("agent_id"),
                            "agent_name": agent.get("name", "Unknown Agent"),
                            "direction": call_log.get("direction", "outbound"),
                            "status": status,
                            "end_reason": end_reason,
                            "duration": duration,
                            "from_number": call_log.get("from_number"),
                            "to_number": call_log.get("to_number"),
                            "start_time": call_log.get("start_time").isoformat() if isinstance(call_log.get("start_time"), datetime) else call_log.get("start_time"),
                            "end_time": end_time.isoformat(),
                            "transcript": call_log.get("transcript", []),
                            "extracted_variables": call_log.get("extracted_variables", {}),
                            "custom_variables": call_log.get("custom_variables", {}),
                            "cost": round(cost, 4),
                            "recording_url": call_log.get("recording_url")
                        }
                        
                        # Send webhook asynchronously (non-blocking)
                        async def send_webhook():
                            try:
                                async with httpx.AsyncClient(timeout=30.0) as client:
                                    response = await client.post(
                                        post_call_webhook_url,
                                        json=webhook_payload,
                                        headers={"Content-Type": "application/json"}
                                    )
                                    if response.status_code >= 200 and response.status_code < 300:
                                        logger.info(f"✅ Post-call webhook sent successfully (status={response.status_code})")
                                    else:
                                        logger.warning(f"⚠️ Post-call webhook returned status {response.status_code}: {response.text[:200]}")
                            except Exception as webhook_err:
                                logger.error(f"❌ Failed to send post-call webhook: {webhook_err}")
                        
                        # Fire and forget - don't block call finalization
                        asyncio.create_task(send_webhook())
        except Exception as webhook_err:
            logger.error(f"Error preparing post-call webhook: {webhook_err}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error finalizing call log {call_id}: {e}")
        logger.exception(e)
        return False


@api_router.post("/telnyx/webhook")
async def telnyx_webhook(payload: dict):
    """Webhook endpoint for Telnyx call events"""
    try:
        logger.info(f"📨 ========== TELNYX WEBHOOK RECEIVED ==========")
        logger.info(f"📨 Full payload: {payload}")
        
        # Extract event data
        event_type = payload.get("data", {}).get("event_type")
        call_control_id = payload.get("data", {}).get("payload", {}).get("call_control_id")
        
        logger.info(f"🎯 Event type: {event_type}, Call ID: {call_control_id}")
        logger.info(f"📨 ================================================")
        
        # Handle incoming calls - route to assigned inbound agent
        if event_type == "call.initiated":
            webhook_payload = payload.get("data", {}).get("payload", {})
            direction = webhook_payload.get("direction", "")
            from_number = webhook_payload.get("from", "")
            to_number = webhook_payload.get("to", "")
            
            logger.info(f"📞 Call initiated - Direction: {direction}, From: {from_number}, To: {to_number}")
            
            if direction == "incoming":
                logger.info(f"📥 Incoming call to {to_number} from {from_number}")
                
                # Normalize phone number for lookup (remove spaces, parentheses, dashes)
                def normalize_phone(phone):
                    """Normalize phone number to E.164 format for comparison"""
                    if not phone:
                        return ""
                    # Remove all non-digit characters except leading +
                    import re
                    normalized = re.sub(r'[^\d+]', '', phone)
                    return normalized
                
                normalized_to = normalize_phone(to_number)
                logger.info(f"🔍 Looking up number: {to_number} → normalized: {normalized_to}")
                
                # Try exact match first, then try normalized match
                phone_record = await db.phone_numbers.find_one({"number": to_number})
                
                if not phone_record:
                    # Try to find by normalized number
                    all_numbers = await db.phone_numbers.find().to_list(100)
                    for num_record in all_numbers:
                        if normalize_phone(num_record.get("number")) == normalized_to:
                            phone_record = num_record
                            logger.info(f"✅ Found number via normalization: {num_record.get('number')}")
                            break
                
                if phone_record and phone_record.get("inbound_agent_id"):
                    inbound_agent_id = phone_record.get("inbound_agent_id")
                    inbound_agent_name = phone_record.get("inbound_agent_name", "Unknown Agent")
                    user_id = phone_record.get("user_id")  # Get user_id from phone record for multi-tenancy
                    
                    logger.info(f"✅ Found assigned inbound agent: {inbound_agent_name} (ID: {inbound_agent_id}) for user: {user_id}")
                    
                    # Get agent configuration - verify it belongs to the same user
                    agent = await db.agents.find_one({"id": inbound_agent_id, "user_id": user_id})
                    
                    if agent:
                        logger.info(f"🤖 Starting inbound call with agent: {agent.get('name')}")
                        
                        # Answer the call
                        telnyx_service = get_telnyx_service()
                        
                        # Store call data in Redis for multi-worker access
                        # Sanitize agent data to remove non-serializable fields (MongoDB ObjectId, datetime)
                        agent_sanitized = {}
                        for key, value in agent.items():
                            if key == "_id":
                                continue  # Skip MongoDB ObjectId
                            # Convert datetime objects to ISO string
                            if isinstance(value, datetime):
                                agent_sanitized[key] = value.isoformat()
                            else:
                                agent_sanitized[key] = value
                        
                        call_data = {
                            "agent": agent_sanitized,
                            "call_control_id": call_control_id,
                            "direction": "inbound",
                            "from_number": from_number,
                            "to_number": to_number,
                            "custom_variables": {
                                "from_number": from_number,
                                "to_number": to_number,
                                "phone_number": from_number  # For inbound, caller's number
                            }
                        }
                        
                        try:
                            redis_service.set_call_data(call_control_id, call_data, ttl=3600)
                            active_telnyx_calls[call_control_id] = call_data  # Fallback
                            logger.info(f"📦 Inbound call data stored in Redis and memory")
                        except Exception as e:
                            logger.error(f"❌ Error storing inbound call data: {e}")
                            active_telnyx_calls[call_control_id] = call_data
                            logger.info(f"⚠️ Stored in memory only (Redis failed)")
                        
                        # Create call log with user_id for multi-tenant isolation
                        try:
                            call_log = CallLogModel(
                                call_id=call_control_id,
                                agent_id=inbound_agent_id,
                                direction="inbound",
                                from_number=from_number,
                                to_number=to_number,
                                status="ringing",  # Valid status for incoming call
                                transcript=[],
                                start_time=datetime.utcnow(),
                                user_id=user_id  # CRITICAL: Associate call with correct user
                            )
                            await db.call_logs.insert_one(call_log.dict())
                            logger.info(f"📝 Call log created for inbound call: {call_control_id} (user: {user_id})")
                        except Exception as e:
                            logger.error(f"❌ Error creating call log: {e}")
                        
                        # Answer the call with streaming
                        try:
                            # Get agent settings for STT provider
                            settings = agent.get("settings", {})
                            stt_provider = settings.get("stt_provider", "soniox")
                            
                            # Answer call with real-time streaming
                            if stt_provider == "soniox":
                                # Use Soniox WebSocket streaming via deployed backend
                                backend_url = os.environ.get('BACKEND_URL')
                                if not backend_url:
                                    raise ValueError("BACKEND_URL environment variable must be set for STT streaming")
                                ws_url = backend_url.replace("https://", "wss://").replace("http://", "ws://")
                                stream_url = f"{ws_url}/api/telnyx/audio-stream/{call_control_id}"
                                
                                answer_result = await telnyx_service.answer_call(
                                    call_control_id,
                                    stream_url=stream_url
                                )
                            else:
                                # Standard answer without streaming
                                answer_result = await telnyx_service.answer_call(call_control_id)
                            
                            if answer_result.get("success"):
                                logger.info(f"✅ Inbound call answered: {call_control_id}")
                            else:
                                logger.error(f"❌ Failed to answer call: {answer_result.get('error')}")
                        except Exception as e:
                            logger.error(f"❌ Error answering inbound call: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    else:
                        logger.error(f"❌ Inbound agent not found: {inbound_agent_id}")
                        # Reject call if agent not found
                        try:
                            telnyx_service = get_telnyx_service()
                            await telnyx_service.reject_call(call_control_id)
                            logger.info(f"📞 Call rejected - agent not found")
                        except Exception as e:
                            logger.error(f"Error rejecting call: {e}")
                else:
                    logger.warning(f"⚠️ No inbound agent assigned to number {to_number}")
                    # Reject call if no agent assigned
                    try:
                        telnyx_service = get_telnyx_service()
                        await telnyx_service.reject_call(call_control_id)
                        logger.info(f"📞 Call rejected - no agent assigned to {to_number}")
                    except Exception as e:
                        logger.error(f"Error rejecting call: {e}")
                
                return {"status": "ok"}
        
        # Handle playback started - clear latency protection flag
        if event_type == "call.playback.started":
            # 🔥 FIX C: Greeting started playing, release any buffered speech
            if call_control_id in active_telnyx_calls:
                active_telnyx_calls[call_control_id]["greeting_in_flight"] = False
            redis_service.update_call_data(call_control_id, {"greeting_in_flight": False})
            logger.info(f"🔊 Playback started - Latency protection disabled (greeting_in_flight=False)")

        # Handle playback ended - close interruption window when audio finishes
        if event_type == "call.playback.ended":
            playback_id = payload.get("data", {}).get("payload", {}).get("playback_id")
            media_url = payload.get("data", {}).get("payload", {}).get("media_url", "")
            
            # COMFORT NOISE RESTART: Check if this is the comfort noise playback ending
            # If so, restart it to ensure continuous playback
            state = call_states.get(call_control_id)
            comfort_noise_id = state.get("comfort_noise_playback_id") if state else None
            
            if playback_id == comfort_noise_id:
                logger.info(f"🔊 Comfort noise playback ended (id: {playback_id}), restarting...")
                
                # Restart comfort noise in the background
                async def restart_comfort_noise():
                    try:
                        # Get user's Telnyx keys
                        call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id, {})
                        agent_info = call_data.get("agent", {}) if isinstance(call_data, dict) else {}
                        user_id = agent_info.get("user_id")
                        
                        if user_id:
                            telnyx_api_key = await get_api_key(user_id, "telnyx")
                            telnyx_connection_id = await get_api_key(user_id, "telnyx_connection_id")
                            
                            if telnyx_api_key and telnyx_connection_id:
                                telnyx_service = get_telnyx_service(api_key=telnyx_api_key, connection_id=telnyx_connection_id)
                                backend_url = os.environ.get('BACKEND_URL', os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001'))
                                comfort_noise_url = f"{backend_url}/api/tts-audio/comfort_noise_continuous.mp3"
                                
                                result = await telnyx_service.play_audio_url(
                                    call_control_id,
                                    comfort_noise_url,
                                    loop=True,
                                    overlay=True
                                )
                                
                                if result.get("success"):
                                    new_playback_id = result.get("playback_id")
                                    if call_control_id in call_states:
                                        call_states[call_control_id]["comfort_noise_playback_id"] = new_playback_id
                                    logger.info(f"🎵 Comfort noise restarted (new playback_id: {new_playback_id})")
                                else:
                                    logger.warning(f"⚠️ Failed to restart comfort noise: {result}")
                    except Exception as e:
                        logger.error(f"❌ Error restarting comfort noise: {e}")
                
                asyncio.create_task(restart_comfort_noise())
                
                # Don't process this as a regular playback end
                return {"status": "ok"}
            
            # MULTI-WORKER FIX: Update Redis playback state so WebSocket worker can detect
            # when all playbacks finish, regardless of which worker receives the webhook
            redis_svc = redis_service
            remaining_playbacks = redis_svc.remove_playback_id(call_control_id, playback_id)
            
            logger.info(f"🔊 Redis: Removed playback {playback_id}, {remaining_playbacks} remaining")
            
            # CRITICAL FIX: Use Redis count instead of state dict to determine if all audio finished
            # This avoids issues where call_states becomes unavailable
            if remaining_playbacks == 0:
                logger.info(f"🔊 ALL PLAYBACKS FINISHED (via Redis) - attempting to start silence timer")
                
                # 🔥 CRITICAL FIX: Clear playback_expected_end_time when all audio finishes
                # This prevents the filter from thinking agent is still speaking
                state = call_states.get(call_control_id)
                if state:
                    state["playback_expected_end_time"] = 0
                    logger.info(f"⏱️ CLEARED playback_expected_end_time - agent is definitely done speaking")
                
                # MULTI-WORKER FIX: Use Redis flag to signal the WebSocket worker (which has the session)
                # Instead of trying to access session here, set a flag that the monitor can detect
                redis_svc.set_flag(call_control_id, "agent_done_speaking", "true", expire=10)
                logger.info(f"✅ Set 'agent_done_speaking' flag in Redis for worker with session to detect")
                
                # Still try local access if we're on the same worker (for immediate response)
                # Still try local access if we're on the same worker (for immediate response)
                if state and "session" in state and state["session"]:
                    session = state["session"]
                    logger.info(f"✅ Found session locally: agent_speaking={session.agent_speaking}, user_speaking={session.user_speaking}")
                    if session.agent_speaking:
                        session.mark_agent_speaking_end()
                        logger.info(f"⏱️ Agent done speaking, silence timer STARTED (local)")
                    elif not session.user_speaking:
                        # 🔥 CRITICAL CHECK: Double check if user is speaking using the timestamp
                        # Sometimes user_speaking flag latency issues occur
                        time_since_user_start = time.time() - getattr(session, '_user_started_speaking_at', 0)
                        
                        # Use a small window (e.g., 2 seconds) to account for race conditions where
                        # user started speaking but the flag might be flipping or checked precisely at transition
                        if time_since_user_start < 2.0 and time_since_user_start > 0:
                             logger.info(f"⏱️ SKIPPING silence timer - User started speaking recently ({time_since_user_start:.3f}s ago)")
                        else:
                            session.start_silence_tracking()
                            logger.info(f"⏱️ Silence timer STARTED (local, agent wasn't marked as speaking)")
                    else:
                        logger.info(f"⏱️ SKIPPING silence timer - User is speaking")
                elif call_control_id in active_telnyx_calls:
                    call_data = active_telnyx_calls[call_control_id]
                    if "session" in call_data and call_data["session"]:
                        session = call_data["session"]
                        logger.info(f"✅ Found session in active_telnyx_calls: agent_speaking={session.agent_speaking}, user_speaking={session.user_speaking}")
                        if session.agent_speaking:
                            session.mark_agent_speaking_end()
                            logger.info(f"⏱️ Agent done speaking, silence timer STARTED (memory fallback)")
                        elif not session.user_speaking:
                            # 🔥 CRITICAL CHECK: Double check if user is speaking using the timestamp
                            # Sometimes user_speaking flag latency issues occur
                            time_since_user_start = time.time() - getattr(session, '_user_started_speaking_at', 0)
                            if time_since_user_start < 0.5 or session.user_speaking:
                                logger.info(f"⏱️ SKIPPING silence timer - User started speaking recently ({time_since_user_start:.3f}s ago)")
                            else:
                                session.start_silence_tracking()
                                logger.info(f"⏱️ Silence timer STARTED (memory fallback, agent wasn't marked as speaking)")
                        else:
                            logger.info(f"⏱️ SKIPPING silence timer - User is speaking (memory fallback)")
                else:
                    # Fallback: Just start it if we can't check session state
                    # But without session we can't call start_silence_tracking anyway
                    logger.warning(f"⚠️ Could not find session to start silence timer for {call_control_id}")
                # Check for playback_expected_end_time logic - if it was cleared recently implies interruption.
                # This check is implicitly handled by the `if state:` block above where `playback_expected_end_time` is set to 0.
                # If it was cleared recently due to an interruption, the `agent_done_speaking` flag would still be set,
                # and the silence timer logic would proceed as intended, or be skipped if the user is speaking.
                # No explicit additional code is needed here for this instruction, as the existing logic covers it.
            
            # Also update local state dict if it exists (for interruption detection)
            state = call_states.get(call_control_id)
            if state and playback_id in state.get("current_playback_ids", set()):
                state["current_playback_ids"].remove(playback_id)
                logger.debug(f"🔊 Removed playback from local state, {len(state['current_playback_ids'])} remaining locally")
            
            # Dead air prevention: The dead_air_monitor detects playback completion via Redis
            # This ensures it works in multi-worker setups where webhooks arrive at different workers
            # No need to call mark_agent_speaking_end() here - monitor handles it
        
        # Handle AMD (Answering Machine Detection) events
        if event_type == "call.machine.detection.ended":
            result = payload.get("data", {}).get("payload", {}).get("result")
            detection_type = payload.get("data", {}).get("payload", {}).get("detection_type")
            
            logger.info(f"🤖 AMD Detection: result={result}, type={detection_type}")
            
            # Signal AMD completion to any waiting greeting code
            if call_control_id in amd_completion_events:
                amd_completion_events[call_control_id]["result"] = result
                amd_completion_events[call_control_id]["detection_type"] = detection_type
                amd_completion_events[call_control_id]["event"].set()
                logger.info(f"🔔 AMD event signaled for {call_control_id}: result={result}")
            
            # Handle different detection types
            # result can be: "human", "machine", "not_sure"
            # detection_type can be: "greeting_ended", "beep_detected", "fax_detected", etc.
            
            # Fax machine detected - hang up immediately
            if detection_type == "fax_detected" or "fax" in str(detection_type).lower():
                logger.warning(f"📠 FAX MACHINE detected via Telnyx AMD - hanging up call {call_control_id}")
                telnyx_service = get_telnyx_service()
                try:
                    hangup_result = await telnyx_service.hangup_call(call_control_id)
                    logger.info(f"✅ Call hung up (fax): {hangup_result}")
                    await db.call_logs.update_one(
                        {"call_id": call_control_id},
                        {"$set": {
                            "status": "fax_detected",
                            "end_reason": "fax_machine",
                            "ended_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }}
                    )
                except Exception as e:
                    logger.error(f"❌ Error hanging up fax call: {e}")
                return {"status": "ok"}
            
            # If machine detected (voicemail, answering machine), hang up immediately
            if result == "machine":
                logger.warning(f"📞 Voicemail/Machine detected via Telnyx AMD - hanging up call {call_control_id}")
                
                # Mark in Redis so waiting greeting knows to abort
                call_data = redis_service.get_call_data(call_control_id) or {}
                call_data["voicemail_detected"] = True
                redis_service.set_call_data(call_control_id, call_data, ttl=60)
                
                # Also mark in memory
                if call_control_id in active_telnyx_calls:
                    active_telnyx_calls[call_control_id]["voicemail_detected"] = True
                
                telnyx_service = get_telnyx_service()
                try:
                    await asyncio.sleep(0.5)
                    hangup_result = await telnyx_service.hangup_call(call_control_id)
                    logger.info(f"✅ Call hung up: {hangup_result}")
                    
                    # Update call log with detailed AMD info
                    await db.call_logs.update_one(
                        {"call_id": call_control_id},
                        {"$set": {
                            "status": "voicemail_detected",
                            "end_reason": "voicemail_detected_amd",
                            "voicemail_detection": {
                                "method": "telnyx_amd",
                                "result": result,
                                "detection_type": detection_type,
                                "detected_at": datetime.utcnow().isoformat()
                            },
                            "ended_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }}
                    )
                except Exception as e:
                    logger.error(f"❌ Error hanging up AMD-detected call: {e}")
                
                return {"status": "ok"}
        
        if event_type == "call.machine.greeting.ended":
            # Premium AMD - greeting ended (if we wanted to leave a message, we'd do it here)
            logger.info(f"🤖 Premium AMD: Voicemail greeting ended for {call_control_id}")
            # We're not leaving messages, so this is just informational
        
        if event_type == "call.answered":
            # Call was answered - start AI conversation with speech gathering
            logger.info(f"✅ Call answered: {call_control_id}")
            
            # Try Redis first, then fallback to in-memory
            call_data = redis_service.get_call_data(call_control_id)
            
            if not call_data:
                # Fallback to in-memory dictionary
                logger.warning(f"⚠️ Call not found in Redis, checking in-memory fallback...")
                if call_control_id in active_telnyx_calls:
                    call_data = active_telnyx_calls[call_control_id]
                    logger.info(f"✅ Found call in in-memory fallback")
                else:
                    logger.error(f"❌ CRITICAL: call_control_id {call_control_id} NOT FOUND in Redis or in-memory!")
                    logger.error(f"❌ This means the session was never created or was already cleaned up")
                    return
            else:
                logger.info(f"✅ Found call in Redis (multi-worker state sharing working)")
            agent = call_data["agent"]
            custom_variables = call_data.get("custom_variables", {})
            
            # Extract phone numbers from webhook payload
            webhook_payload = payload.get("data", {}).get("payload", {})
            from_number = webhook_payload.get("from", "")
            to_number = webhook_payload.get("to", "")
            
            # Add phone numbers to custom variables
            if from_number:
                custom_variables["from_number"] = from_number
            if to_number:
                custom_variables["to_number"] = to_number
                custom_variables["phone_number"] = to_number  # Alias for easier use
            
            logger.info(f"📞 Phone numbers added to session: from={from_number}, to={to_number}")
            
            # Update call log
            try:
                await db.call_logs.update_one(
                    {"call_id": call_control_id},
                    {"$set": {
                        "status": "answered",
                        "answered_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }}
                )
                logger.info("✅ Call log updated")
            except Exception as e:
                logger.error(f"❌ Error updating call log: {e}")
            
            # CALL STARTED WEBHOOK: Send notification when call begins (for lead tracking)
            try:
                agent_settings_for_webhook = agent.get("settings", {}) or {}
                call_started_webhook_url = agent_settings_for_webhook.get("call_started_webhook_url")
                # Backwards compatible: fire webhook if URL exists and active is not explicitly False
                # (undefined/None = enabled for existing configs, only False = disabled)
                is_call_started_webhook_active = agent_settings_for_webhook.get("call_started_webhook_active")
                should_fire_webhook = bool(call_started_webhook_url and is_call_started_webhook_active is not False)
                
                logger.info(f"🔍 DEBUG Webhook: url='{call_started_webhook_url}', active={is_call_started_webhook_active}, should_fire={should_fire_webhook}")
                
                if should_fire_webhook:
                    logger.info(f"📤 Sending call-started webhook to: {call_started_webhook_url}")
                    
                    webhook_payload = {
                        "event": "call.started",
                        "call_id": call_control_id,
                        "agent_id": agent.get("id"),
                        "agent_name": agent.get("name", "Unknown Agent"),
                        "direction": call_data.get("direction", "outbound"),
                        "from_number": from_number,
                        "to_number": to_number,
                        "start_time": datetime.utcnow().isoformat()
                    }
                    
                    async def send_call_started_webhook():
                        try:
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                response = await client.post(
                                    call_started_webhook_url,
                                    json=webhook_payload,
                                    headers={"Content-Type": "application/json"}
                                )
                                if response.status_code >= 200 and response.status_code < 300:
                                    logger.info(f"✅ Call-started webhook sent successfully (status={response.status_code})")
                                else:
                                    logger.warning(f"⚠️ Call-started webhook returned status {response.status_code}: {response.text[:200]}")
                        except Exception as webhook_err:
                            logger.error(f"❌ Failed to send call-started webhook: {webhook_err}")
                    
                    # Fire and forget - don't block call processing
                    asyncio.create_task(send_call_started_webhook())
            except Exception as webhook_err:
                logger.error(f"Error preparing call-started webhook: {webhook_err}")
            
            # Get user's Telnyx API keys from database
            user_id = agent.get("user_id")
            logger.info(f"🔧 Getting Telnyx API keys for user: {user_id}")
            
            telnyx_api_key = await get_api_key(user_id, "telnyx")
            telnyx_connection_id = await get_api_key(user_id, "telnyx_connection_id")
            
            if not telnyx_api_key or not telnyx_connection_id:
                logger.error(f"❌ Telnyx keys not found for user {user_id}")
                return
            
            logger.info("🔧 Creating Telnyx service with user's keys...")
            telnyx_service = get_telnyx_service(api_key=telnyx_api_key, connection_id=telnyx_connection_id)
            
            # 🔊 START CONTINUOUS COMFORT NOISE (if enabled in agent settings)
            agent_settings = agent.get("settings", {})
            enable_comfort_noise = agent_settings.get("enable_comfort_noise", False)
            
            if enable_comfort_noise:
                try:
                    backend_url = os.environ.get('BACKEND_URL')
                    if not backend_url:
                        # Try to construct from REACT_APP_BACKEND_URL
                        backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
                    
                    comfort_noise_url = f"{backend_url}/api/tts-audio/comfort_noise_continuous.mp3"
                    
                    # Start comfort noise as continuous background overlay (loops indefinitely)
                    result = await telnyx_service.play_audio_url(
                        call_control_id,
                        comfort_noise_url,
                        loop=True,  # Loop continuously
                        overlay=True  # Play as background layer, don't block other audio
                    )
                    
                    if result.get("success"):
                        comfort_noise_playback_id = result.get("playback_id")
                        call_states[call_control_id]["comfort_noise_playback_id"] = comfort_noise_playback_id
                        logger.info(f"🎵 Comfort noise started as continuous background overlay (playback_id: {comfort_noise_playback_id})")
                    else:
                        logger.warning(f"⚠️ Failed to start comfort noise: {result}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to start comfort noise: {e}")
            else:
                logger.info("⏭️ Comfort noise disabled for this agent")
            
            # Initialize call data for recording management
            call_data["processing_speech"] = False
            call_data["chunk_count"] = 0
            call_data["recent_agent_texts"] = []  # Track last 3 agent messages for echo filtering
            
            # Start call recording
            try:
                recording_result = await telnyx_service.start_recording(
                    call_control_id=call_control_id,
                    format="mp3",
                    channels="dual"
                )
                if recording_result.get("success"):
                    logger.info(f"🎙️ Call recording started for {call_control_id}")
                else:
                    logger.warning(f"⚠️ Failed to start recording: {recording_result.get('error')}")
            except Exception as e:
                logger.error(f"❌ Error starting recording: {e}")
            
            # Create AI session with custom variables injected and KB loaded
            try:
                logger.info(f"🔧 Creating call session for {call_control_id}...")
                logger.info(f"🔍 Agent ID: {agent.get('id')}, User ID: {agent.get('user_id')}")
                
                logger.info(f"🔧 Calling create_call_session() - START")
                session = await create_call_session(
                    call_control_id, 
                    agent, 
                    agent_id=agent.get("id"), 
                    user_id=agent.get("user_id"), 
                    db=db
                )
                logger.info(f"🔧 Calling create_call_session() - COMPLETE")
                
                logger.info(f"✅ Session object created: {type(session).__name__}")
                
                session.session_variables.update(custom_variables)
                
                # CRITICAL: Store serializable data in Redis BEFORE adding session object
                # Session objects can't be JSON-serialized, so update Redis first
                call_data["agent_id"] = agent.get("id")  # For cross-worker session recreation
                call_data["user_id"] = agent.get("user_id")  # For cross-worker session recreation
                redis_service.set_call_data(call_control_id, call_data, ttl=3600)
                logger.info(f"✅ Serializable call_data synced to Redis (agent_id, user_id)")
                
                # THEN add non-serializable session to local worker memory only
                call_data["session"] = session  # Stays in this worker's memory
                active_telnyx_calls[call_control_id] = call_data  # Update local cache
                
                logger.info(f"✅ Session stored in worker memory (not Redis)")
                
                # Mark session as ready in Redis for cross-worker coordination
                redis_service.mark_session_ready(call_control_id, ttl=3600)
                
                logger.info(f"🤖 AI session created for call {call_control_id}")
                logger.info(f"📦 Custom variables injected: {custom_variables}")
                
                # 🚀 INITIALIZE PERSISTENT TTS WEBSOCKET (if ElevenLabs TTS enabled)
                agent_settings = agent.get("settings", {})
                tts_provider = agent_settings.get("tts_provider")
                use_persistent_tts = agent_settings.get("elevenlabs_settings", {}).get("use_persistent_tts", True)  # Default to True for optimization
                
                if tts_provider == "elevenlabs" and use_persistent_tts:
                    # DON'T create persistent TTS session here - it will be created on-demand
                    # in the Soniox handler where we have access to telnyx_ws for WebSocket streaming.
                    # Creating here causes REST API fallback since telnyx_ws isn't available yet.
                    logger.info(f"⏭️ Skipping persistent TTS creation in webhook - will create on-demand with telnyx_ws")
                    call_data["persistent_tts_enabled"] = True  # Will be created on-demand
                else:
                    logger.info(f"⏭️  Persistent TTS disabled (provider: {tts_provider}, enabled: {use_persistent_tts})")
                    call_data["persistent_tts_enabled"] = False
                
            except Exception as e:
                logger.error(f"❌ CRITICAL: Failed to create session: {e}")
                logger.exception("Full traceback:")
                # Try to hangup the call gracefully
                try:
                    await telnyx_service.hangup_call(call_control_id)
                except:
                    pass
                return
            
            # Check who speaks first from start node
            flow = agent.get("call_flow", [])
            first_node = flow[0] if flow else {}
            start_node_data = first_node.get("data", {})
            who_speaks_first = start_node_data.get("whoSpeaksFirst", "ai")
            ai_speaks_after_silence = start_node_data.get("aiSpeaksAfterSilence", False)
            silence_timeout_ms = start_node_data.get("silenceTimeout", 2000)
            
            logger.info(f"👤 Who speaks first: {who_speaks_first}, aiSpeaksAfterSilence: {ai_speaks_after_silence}, timeout: {silence_timeout_ms}ms")
            
            first_text = ""
            
            # Check if AMD is enabled - if so, wait for AMD result before AI speaks
            vm_settings = agent.get("settings", {}).get("voicemail_detection", {})
            amd_enabled = vm_settings.get("enabled", True) and vm_settings.get("use_telnyx_amd", True)
            amd_wait_ms = vm_settings.get("amd_wait_before_greeting_ms", 2500)  # Max wait time for AMD
            
            if amd_enabled and who_speaks_first == "ai":
                logger.info(f"🤖 AMD enabled - waiting up to {amd_wait_ms}ms for AMD detection before greeting...")
                
                # Create an event for this call's AMD completion
                amd_event = asyncio.Event()
                amd_completion_events[call_control_id] = {
                    "event": amd_event,
                    "result": None,
                    "detection_type": None
                }
                
                call_data["waiting_for_amd"] = True
                
                # Wait for AMD event OR timeout (whichever comes first)
                try:
                    await asyncio.wait_for(amd_event.wait(), timeout=amd_wait_ms / 1000.0)
                    amd_result = amd_completion_events.get(call_control_id, {}).get("result")
                    logger.info(f"⚡ AMD completed early with result: {amd_result}")
                except asyncio.TimeoutError:
                    logger.info(f"⏱️ AMD wait timed out after {amd_wait_ms}ms - proceeding with greeting")
                    amd_result = "timeout"
                finally:
                    call_data["waiting_for_amd"] = False
                    # Clean up the event
                    if call_control_id in amd_completion_events:
                        del amd_completion_events[call_control_id]
                
                # Check if call was hung up due to AMD detection during wait
                if call_control_id not in active_telnyx_calls:
                    logger.info(f"📞 Call ended during AMD wait (likely voicemail detected)")
                    return
                
                # Check Redis for call status
                current_call_data = redis_service.get_call_data(call_control_id)
                if current_call_data and current_call_data.get("voicemail_detected"):
                    logger.info(f"📞 Voicemail detected during AMD wait - not sending greeting")
                    return
                
                # If AMD said "machine", don't proceed (should already be hung up, but double-check)
                if amd_result == "machine":
                    logger.info(f"📞 AMD detected machine - not sending greeting")
                    return
                
                logger.info(f"✅ AMD check complete (result: {amd_result}) - proceeding with greeting")
            
            if who_speaks_first == "ai":
                # Get first message from agent (greeting)
                first_message = await session.process_user_input("")
                first_text = first_message.get("text", "Hello! How can I help you?")
                
                logger.info(f"💬 AI speaks first: {first_text}")
                
                # Save greeting to transcript
                await db.call_logs.update_one(
                    {"call_id": call_control_id},
                    {"$push": {
                        "transcript": {
                            "role": "assistant",
                            "text": first_text,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }}
                )
            else:
                logger.info(f"👂 User speaks first - waiting for user input...")
                first_text = ""  # No greeting, wait for user
                
                # ═══════════════════════════════════════════════════════════════════
                # VOICEMAIL PROTECTION FOR "USER SPEAKS FIRST" MODE
                # If we're waiting for user to speak, but they talk for too long 
                # without meaningful interaction, it's likely a voicemail/machine
                # ═══════════════════════════════════════════════════════════════════
                vm_settings = agent.get("settings", {}).get("voicemail_detection", {})
                max_listen_without_interaction_ms = vm_settings.get("max_listen_without_interaction_ms", 15000)  # Default 15s
                
                async def voicemail_timeout_protection():
                    """
                    Monitors for voicemail when user speaks first.
                    If we hear continuous speech for too long without the user 
                    pausing for us to respond, it's likely a voicemail greeting.
                    """
                    try:
                        await asyncio.sleep(max_listen_without_interaction_ms / 1000.0)
                        
                        # Check if call still active
                        if call_control_id not in active_telnyx_calls:
                            return
                        
                        current_call_data = active_telnyx_calls.get(call_control_id, {})
                        current_session = current_call_data.get("session")
                        
                        if not current_session:
                            return
                        
                        # Check if we've had any meaningful back-and-forth
                        # If agent has spoken (responded to user), it's a real conversation
                        if len(current_session.conversation_history) > 1:
                            logger.info(f"✅ Voicemail timeout: Real conversation detected (history: {len(current_session.conversation_history)})")
                            return
                        
                        # Check if voicemail was already detected by other means
                        if current_call_data.get("voicemail_detected"):
                            return
                        
                        # Check the accumulated transcript for voicemail patterns
                        accumulated = current_session.voicemail_detector.accumulated_transcript
                        if accumulated and len(accumulated) > 100:
                            # Long monologue with no interaction - likely voicemail
                            logger.warning(f"🤖 VOICEMAIL PROTECTION: Long monologue ({len(accumulated)} chars) with no interaction - likely voicemail")
                            logger.warning(f"   Transcript preview: {accumulated[:150]}...")
                            
                            # Run one more pattern check
                            is_detected, det_type, confidence = current_session.voicemail_detector.analyze_transcript(
                                "",  # Don't add new text, just re-check
                                call_start_time=current_session.call_start_time
                            )
                            
                            # If patterns detected or just long monologue, hang up
                            if is_detected or len(accumulated) > 200:
                                logger.warning(f"📞 Hanging up - suspected voicemail (user speaks first timeout)")
                                
                                try:
                                    await db.call_logs.update_one(
                                        {"call_id": call_control_id},
                                        {"$set": {
                                            "status": "voicemail_detected",
                                            "end_reason": "voicemail_timeout_user_speaks_first",
                                            "voicemail_detection": {
                                                "method": "long_monologue_timeout",
                                                "transcript_length": len(accumulated),
                                                "detected_at": datetime.utcnow().isoformat()
                                            },
                                            "ended_at": datetime.utcnow(),
                                            "updated_at": datetime.utcnow()
                                        }}
                                    )
                                except Exception as e:
                                    logger.error(f"Error updating call log: {e}")
                                
                                telnyx_svc = get_telnyx_service()
                                try:
                                    await telnyx_svc.hangup_call(call_control_id)
                                    logger.info(f"✅ Call hung up (voicemail timeout protection)")
                                except Exception as e:
                                    logger.error(f"❌ Error hanging up: {e}")
                        
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"❌ Error in voicemail timeout protection: {e}")
                
                # Start the voicemail timeout protection task
                asyncio.create_task(voicemail_timeout_protection())
                logger.info(f"🛡️ Voicemail timeout protection started ({max_listen_without_interaction_ms}ms)")
                
                # If aiSpeaksAfterSilence is enabled, log it and store settings
                # NOTE: The actual silence timeout task is scheduled in the WebSocket worker
                # (where the session lives) to avoid multi-worker issues where this webhook
                # handler runs on a different worker than the one with the session.
                if ai_speaks_after_silence:
                    logger.info(f"⏱️ AI will speak after {silence_timeout_ms}ms of silence (scheduled in WebSocket worker)")
                    # Store the setting in call_data for reference
                    call_data["ai_speaks_after_silence"] = True
                    call_data["silence_timeout_ms"] = silence_timeout_ms
                    call_data["silence_greeting_triggered"] = False
            
            # Check flow type
            is_press_digit_flow = first_node.get("type") == "press_digit"
            
            # For voice flows, WebSocket streaming was already set up in dial command
            if not is_press_digit_flow:
                logger.info("🎤 Voice flow - streaming started via dial command")
                call_data["flow_type"] = "voice_realtime"
                call_data["awaiting_speech"] = True
                call_data["last_agent_text"] = first_text

                # 🔥 FIX: Check if user has ALREADY spoken (race condition protection)
                # If user spoke during AMD wait/setup, we should NOT speak the greeting
                # because the WebSocket handler is already generating a response to them.
                current_call_data = redis_service.get_call_data(call_control_id) or {}
                mem_call_data = active_telnyx_calls.get(call_control_id, {})
                
                user_spoken_redis = current_call_data.get("user_has_spoken", False)
                user_spoken_mem = mem_call_data.get("user_has_spoken", False)
                
                if user_spoken_redis or user_spoken_mem:
                    logger.warning(f"🛑 SKIPPING GREETING: User already spoke! (Redis: {user_spoken_redis}, Mem: {user_spoken_mem})")
                    first_text = ""  # Clear greeting so we don't speak it
                    
                    # Update transcript to show we skipped it (optional, but good for debugging)
                    # We don't remove the DB entry since it "technically" was the plan, 
                    # but we could append a note if needed.

            
            # Now speak greeting if there is one
            try:
                if "telnyx_service" not in locals():
                    telnyx_service = get_telnyx_service()
                
                if first_text:  # Only speak if there's a greeting
                    agent = session.agent_config
                    
                    # 🔥 FIX C: Latency protection - Buffer user speech while greeting is starting up
                    if call_control_id in active_telnyx_calls:
                        active_telnyx_calls[call_control_id]["greeting_in_flight"] = True
                    redis_service.update_call_data(call_control_id, {"greeting_in_flight": True})
                    
                    await telnyx_service.speak_text(
                        call_control_id, 
                        first_text,
                        agent_config=agent
                    )
                    logger.info("🔊 Greeting spoken via Telnyx TTS")
                else:
                    logger.info("🤐 No greeting - waiting for user to speak first")
                
                if is_press_digit_flow:
                    # DTMF flow
                    logger.info("📱 Press Digit flow - using DTMF")
                    call = telnyx_service.client.calls
                    call.actions.gather_using_speak(
                        call_control_id=call_control_id,
                        payload="",
                        voice="female",
                        language="en-US",
                        minimum_digits=1,
                        maximum_digits=1,
                        timeout_millis=30000,
                        inter_digit_timeout_millis=5000
                    )
                    call_data["flow_type"] = "press_digit"
                else:
                    # Voice flow - already started streaming above
                    logger.info("🎤 Voice flow - WebSocket streaming already initiated")
                    pass
                
            except Exception as e:
                logger.error(f"Error in conversation setup: {e}")
        
        elif event_type == "call.hangup":
            # Call ended
            logger.info(f"📞 Call ended: {call_control_id}")
            
            # Get hangup cause
            hangup_cause = payload.get("data", {}).get("payload", {}).get("hangup_cause", "normal")
            logger.info(f"📞 Hangup cause: {hangup_cause}")
            
            # Finalize call log
            await finalize_call_log(call_control_id, end_reason="hangup")
            
            # Trigger QC analysis and CRM update (async, non-blocking)
            try:
                # Get call data to extract user_id, lead_id, agent_id
                redis_data = redis_service.get_call_data(call_control_id)
                memory_data = active_telnyx_calls.get(call_control_id, {})
                call_data = redis_data or memory_data or {}
                
                logger.info(f"📇 [HANGUP] Data source: redis={'Yes' if redis_data else 'No'}, memory={'Yes' if memory_data else 'No'}")
                
                # Ensure we have a dict
                if not isinstance(call_data, dict):
                    call_data = {}
                
                agent_info = call_data.get("agent", {}) or {}
                user_id = agent_info.get("user_id")
                agent_id = agent_info.get("id")
                agent_name = agent_info.get("name", "Unknown Agent")
                
                # Try to get lead_id from custom_variables if it was set
                custom_vars = call_data.get("custom_variables", {}) or {}
                lead_id = custom_vars.get("lead_id")
                
                # Get phone number from call data (check multiple locations)
                to_number = (
                    custom_vars.get("to_number") or 
                    custom_vars.get("phone_number") or
                    call_data.get("to_number")  # Fallback to top-level
                )
                
                # FALLBACK: If critical data is missing, try to get from call_logs in MongoDB
                # This handles cases where Redis is unavailable and in-memory data is lost
                if not user_id or not agent_id or not to_number:
                    logger.info(f"📇 [HANGUP] Missing data from cache, checking MongoDB call_logs...")
                    call_log = await db.call_logs.find_one({
                        "$or": [
                            {"call_id": call_control_id},
                            {"id": call_control_id}
                        ]
                    })
                    if call_log:
                        logger.info(f"📇 [HANGUP] Found call_log in MongoDB, extracting missing data...")
                        if not user_id:
                            user_id = call_log.get("user_id")
                        if not agent_id:
                            agent_id = call_log.get("agent_id")
                        if not to_number:
                            to_number = call_log.get("to_number")
                        if not agent_name or agent_name == "Unknown Agent":
                            # Try to get agent name from agents collection
                            if agent_id:
                                agent_doc = await db.agents.find_one({"id": agent_id}, {"name": 1})
                                if agent_doc:
                                    agent_name = agent_doc.get("name", agent_name)
                        logger.info(f"📇 [HANGUP] After MongoDB fallback: user_id={user_id}, agent_id={agent_id}, to_number={to_number}")
                    else:
                        logger.warning(f"⚠️ [HANGUP] Call log NOT found in MongoDB for {call_control_id}")
                
                # Log what we found for debugging
                logger.info(f"📇 [HANGUP] Final extracted data: user_id={user_id}, agent_id={agent_id}, to_number={to_number}, lead_id={lead_id}, agent_name={agent_name}")
                logger.info(f"📇 [HANGUP] Agent info keys: {list(agent_info.keys()) if agent_info else 'None'}")
                
                if user_id:
                    # Run QC analysis in background (fire and forget)
                    asyncio.create_task(process_qc_analysis(
                        call_id=call_control_id,
                        user_id=user_id,
                        lead_id=lead_id,
                        agent_id=agent_id
                    ))
                    logger.info(f"🚀 Triggered QC analysis for call {call_control_id}")
                    
                    # Trigger Campaign QC (Tech/Script/Tonality) if agent has auto_qc enabled
                    if agent_id:
                        asyncio.create_task(trigger_campaign_qc_for_call(
                            call_id=call_control_id,
                            user_id=user_id,
                            agent_id=agent_id
                        ))
                        logger.info(f"📊 Triggered Campaign QC for call {call_control_id}")
                    
                    # Update CRM lead (fire and forget)
                    if to_number:
                        asyncio.create_task(update_crm_after_call(
                            call_id=call_control_id,
                            user_id=user_id,
                            agent_id=agent_id,
                            agent_name=agent_name,
                            to_number=to_number,
                            custom_variables=custom_vars
                        ))
                        logger.info(f"📇 Triggered CRM update for call {call_control_id}")
                else:
                    logger.warning(f"⚠️ Cannot trigger QC analysis - no user_id found for call {call_control_id}")
            except Exception as e:
                logger.error(f"❌ Error triggering QC analysis: {e}")
            
            # Clean up persistent TTS session
            try:
                await persistent_tts_manager.close_session(call_control_id)
                logger.info(f"✅ Closed persistent TTS session for call {call_control_id}")
            except Exception as e:
                logger.error(f"❌ Error closing persistent TTS session: {e}")
            
            # 🔥 CRITICAL FIX: Close the CallSession to stop dead air monitor
            try:
                from core_calling_service import close_call_session
                await close_call_session(call_control_id)
                logger.info(f"✅ Closed CallSession for call {call_control_id}")
            except Exception as e:
                logger.error(f"❌ Error closing CallSession: {e}")
            
            # Clean up active call from Redis and in-memory
            redis_service.delete_call_data(call_control_id)
            if call_control_id in active_telnyx_calls:
                del active_telnyx_calls[call_control_id]
            logger.info(f"🧹 Cleaned up call session from Redis and memory: {call_control_id}")
        
        elif event_type == "call.recording.saved":
            # Recording is ready - download and transcribe it
            logger.info(f"🎙️ Recording saved for call: {call_control_id}")
            
            # Try to get call data from Redis first, then in-memory fallback
            call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id, {})
            session = call_data.get("session")
            
            # Get recording URL and ID
            recording_data = payload.get("data", {}).get("payload", {})
            recording_urls = recording_data.get("recording_urls", {})
            download_url = recording_urls.get("wav") or recording_urls.get("mp3")
            channels = recording_data.get("channels", "")
            recording_duration = recording_data.get("duration_millis", 0) // 1000  # Convert to seconds
            recording_id = recording_data.get("recording_id")  # Store recording ID for future URL refresh
            
            logger.info(f"🔍 Recording check: download_url={bool(download_url)}, channels={channels}, recording_id={recording_id}, call_data={bool(call_data)}")
            
            # Save recording URL and ID to database
            if download_url:
                try:
                    update_data = {
                        "recording_url": download_url,
                        "recording_duration": recording_duration,
                        "updated_at": datetime.utcnow()
                    }
                    if recording_id:
                        update_data["recording_id"] = recording_id
                    
                    await db.call_logs.update_one(
                        {"call_id": call_control_id},
                        {"$set": update_data}
                    )
                    logger.info(f"💾 Saved recording URL and ID to database: {recording_id}")
                except Exception as e:
                    logger.error(f"❌ Error saving recording URL: {e}")
            
            # Handle dual-channel recordings (user + agent separated)
            if download_url and channels == "dual":
                logger.info(f"✅ Entering dual-channel processing")
                
                # Check if we should process (skip if currently speaking)
                if call_data and call_data.get("processing_speech"):
                    logger.info(f"⏭️  Skipping - currently processing")
                    return {"status": "ok"}
                
                try:
                    logger.info(f"📥 Downloading DUAL-CHANNEL recording...")
                    
                    # Download the recording
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(download_url)
                        audio_data = response.content
                    
                    logger.info(f"✅ Downloaded {len(audio_data)} bytes")
                    
                    # Extract user channel (channel 0)
                    from pydub import AudioSegment
                    import io
                    
                    audio_format = "mp3" if ".mp3" in download_url else "wav"
                    audio = AudioSegment.from_file(io.BytesIO(audio_data), format=audio_format)
                    channels_split = audio.split_to_mono()
                    
                    logger.info(f"✅ Split into {len(channels_split)} channels")
                    
                    # Get STT provider from session/agent config
                    stt_provider = "soniox"  # Default
                    user_id = None
                    if session:
                        # session is a CallSession object, access attributes directly
                        agent_config = getattr(session, 'agent_config', {}) or {}
                        if agent_config:
                            stt_provider = agent_config.get("settings", {}).get("stt_provider", "soniox")
                            user_id = agent_config.get("user_id") or getattr(session, 'user_id', None)
                    
                    logger.info(f"🎤 Using STT provider: {stt_provider} for interruption detection")
                    
                    # Try both channels to find user speech
                    transcript_text = None
                    for channel_idx, channel_audio in enumerate(channels_split):
                        channel_bytes = io.BytesIO()
                        channel_audio.export(channel_bytes, format="wav")
                        channel_data = channel_bytes.getvalue()
                        
                        logger.info(f"📊 Channel {channel_idx}: {len(channel_data)} bytes")
                        
                        transcript = await transcribe_audio_file_dynamic(channel_data, stt_provider, user_id)
                        
                        if transcript and transcript.strip():
                            logger.info(f"✅ Channel {channel_idx} HAS SPEECH: {transcript}")
                            transcript_text = transcript
                            break
                        else:
                            logger.info(f"❌ Channel {channel_idx}: No speech")
                    
                    if not transcript_text or not transcript_text.strip():
                        logger.warning("⚠️ No speech in any channel")
                        return {"status": "ok"}
                    
                    logger.info(f"📝 User said: {transcript_text}")
                    
                    # Echo filtering - ignore if transcript matches recent agent speech
                    recent_agent_texts = call_data.get("recent_agent_texts", [])
                    logger.info(f"🔍 Echo filter check: recent_agent_texts = {recent_agent_texts}")
                    
                    if recent_agent_texts:
                        # Check if transcript is too similar to any recent agent speech
                        transcript_lower = transcript_text.lower().strip()
                        # Normalize: remove punctuation and extra spaces
                        import string
                        transcript_normalized = ''.join(c for c in transcript_lower if c not in string.punctuation).strip()
                        transcript_words = set(transcript_normalized.split())
                        
                        for agent_text in recent_agent_texts:
                            agent_lower = agent_text.lower().strip()
                            agent_normalized = ''.join(c for c in agent_lower if c not in string.punctuation).strip()
                            agent_words = set(agent_normalized.split())
                            
                            if len(agent_words) >= 2:  # Lower threshold - even 2 words can be echo
                                common_words = agent_words.intersection(transcript_words)
                                
                                # Multiple echo detection strategies:
                                # 1. Similarity based on agent words (original)
                                similarity_agent = len(common_words) / len(agent_words) if len(agent_words) > 0 else 0
                                
                                # 2. Similarity based on transcript words (catches short echoes from long agent text)
                                similarity_transcript = len(common_words) / len(transcript_words) if len(transcript_words) > 0 else 0
                                
                                # 3. Substring match (catches "I was just" in "I was just, um, wondering...")
                                transcript_in_agent = transcript_normalized in agent_normalized
                                
                                logger.info(f"🔍 Echo check: agent_sim={similarity_agent:.2f}, transcript_sim={similarity_transcript:.2f}, substring={transcript_in_agent}")
                                
                                # Echo detected if:
                                # - High similarity either direction (60%+)
                                # - OR transcript is a substring of agent text
                                # - OR 80%+ of USER's words match agent (they're echoing what agent said)
                                if similarity_agent > 0.6 or similarity_transcript > 0.8 or transcript_in_agent:
                                    logger.info(f"🔇 ECHO DETECTED - Ignoring: {transcript_text[:50]}")
                                    return {"status": "ok"}
                    
                    # Mark as processing (update both Redis and in-memory)
                    update_call_state(call_control_id, {"processing_speech": True})
                    
                    # Save user transcript
                    await db.call_logs.update_one(
                        {"call_id": call_control_id},
                        {"$push": {
                            "transcript": {
                                "role": "user",
                                "text": transcript_text,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }}
                    )
                    
                    # Process through AI
                    logger.info(f"🔍 Session exists: {bool(session)}, call_data exists: {bool(call_data)}")
                    if session:
                        try:
                            response = await session.process_user_input(transcript_text)
                            
                            if not response:
                                logger.info("🤖 AI response suppressed (likely barge-in or empty)")
                                return {"status": "ok"}
                                
                            response_text = response.get("text", "I'm sorry, I didn't understand.")
                            
                            logger.info(f"🤖 AI response: {response_text}")
                            
                            # Save agent transcript
                            await db.call_logs.update_one(
                                {"call_id": call_control_id},
                                {"$push": {
                                    "transcript": {
                                        "role": "assistant",
                                        "text": response_text,
                                        "timestamp": datetime.utcnow().isoformat()
                                    }
                                }}
                            )
                            
                            # Speak response if call still active
                            if call_control_id in active_telnyx_calls:
                                telnyx_service = get_telnyx_service()
                                agent_config = session.agent_config if session else None
                                try:
                                    # 🔥 OPTIMIZATION: Update recent_agent_texts BEFORE speaking
                                    # This ensures the echo filter is active immediately, preventing race conditions
                                    # where the agent hears its own audio start before the list is updated.
                                    
                                    # Update recent agent texts for echo filtering (keep last 3)
                                    # Get current data from Redis or fallback
                                    call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id, {})
                                    recent_texts = call_data.get("recent_agent_texts", [])
                                    recent_texts.append(response_text)
                                    recent_texts = recent_texts[-3:]  # Keep only last 3
                                    
                                    # Update both Redis and in-memory
                                    update_call_state(call_control_id, {
                                        "recent_agent_texts": recent_texts,
                                        "last_agent_text": response_text
                                    })
                                    
                                    # Also store in call_states for interruption handler echo filtering
                                    # CRITICAL: Don't replace the dict, just update the key to preserve current_playback_ids and session
                                    if call_control_id in call_states:
                                        call_states[call_control_id]["recent_agent_texts"] = recent_texts
                                    else:
                                        logger.warning(f"⚠️ call_states entry missing for {call_control_id}, skipping recent_agent_texts update")

                                    # 🔥 CRITICAL FIX: Mark agent as speaking before emitting audio
                                    session.mark_agent_speaking_start()
                                    await telnyx_service.speak_text(call_control_id, response_text, agent_config=agent_config)
                                    logger.info(f"🔊 Spoke response successfully")
                                except Exception as speak_error:
                                    logger.error(f"❌ Error speaking: {speak_error}")
                                
                                # Check ending node
                                logger.info(f"🔍 Checking should_end_call: {session.should_end_call}")
                                if session.should_end_call:
                                    logger.info("📞 Ending node - hanging up in 3s")
                                    await asyncio.sleep(3)
                                    try:
                                        await telnyx_service.hangup_call(call_control_id)
                                        logger.info("☎️ Call hung up successfully")
                                    except Exception as e:
                                        logger.error(f"Error hanging up: {e}")
                                    # Clean up from Redis and in-memory
                                    redis_service.delete_call_data(call_control_id)
                                    if call_control_id in active_telnyx_calls:
                                        del active_telnyx_calls[call_control_id]
                                    return {"status": "ok"}
                                
                                # Resume recording after speech completes
                                logger.info("⏰ Waiting 2s for speech to complete...")
                                await asyncio.sleep(2)
                                
                                # Check if call still active (Redis or in-memory)
                                call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id)
                                if call_data:
                                    logger.info("🔄 Resuming recording and continuous loop...")
                                    update_call_state(call_control_id, {"processing_speech": False})
                                    
                                    # Restart the continuous recording loop
                                    async def restart_continuous_recording():
                                        try:
                                            await telnyx_service.start_recording(
                                                call_control_id=call_control_id,
                                                format="wav",
                                                channels="dual"
                                            )
                                            logger.info("🎙️ Recording resumed successfully")
                                            update_call_state(call_control_id, {"recording_start_time": time.time()})
                                            
                                            # Continue the loop
                                            call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id, {})
                                            chunk = call_data.get("chunk_count", 0)
                                            
                                            while True:
                                                # Check if call still active and not processing
                                                call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id)
                                                if not call_data or call_data.get("processing_speech"):
                                                    break
                                                await asyncio.sleep(3)  # 3-second chunks
                                                
                                                # Check again if still active
                                                call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id)
                                                if call_data and not call_data.get("processing_speech"):
                                                    try:
                                                        await telnyx_service.stop_recording(call_control_id)
                                                        chunk += 1
                                                        update_call_state(call_control_id, {"chunk_count": chunk})
                                                        logger.info(f"⏱️ Dual-channel chunk {chunk} stopped (3s)")
                                                        
                                                        await asyncio.sleep(0.3)
                                                        
                                                        # Check once more before restarting
                                                        call_data = redis_service.get_call_data(call_control_id) or active_telnyx_calls.get(call_control_id)
                                                        if call_data and not call_data.get("processing_speech"):
                                                            await telnyx_service.start_recording(
                                                                call_control_id=call_control_id,
                                                                format="wav",
                                                                channels="dual"
                                                            )
                                                            update_call_state(call_control_id, {"recording_start_time": time.time()})
                                                            logger.info(f"🔄 Chunk {chunk + 1} recording started")
                                                    except Exception as e:
                                                        logger.error(f"❌ Error in resumed recording loop: {e}")
                                                        break
                                        except Exception as e:
                                            logger.error(f"❌ Error restarting recording: {e}")
                                    
                                    asyncio.create_task(restart_continuous_recording())
                                else:
                                    logger.warning("⚠️ Call no longer active, not resuming recording")
                        except Exception as e:
                            logger.error(f"Error in AI processing: {e}")
                
                except Exception as e:
                    logger.error(f"❌ Error processing dual-channel: {e}", exc_info=True)
            else:
                if not download_url:
                    logger.error("No recording URL found in webhook")
                elif channels != "dual":
                    logger.info(f"Skipping {channels} channel recording (not dual-channel)")
        
        elif event_type == "call.gather.ended":
                # Gather ended - could have digits or speech
                logger.info(f"🎤 Gather ended for call: {call_control_id}")
            
                if call_control_id in active_telnyx_calls:
                    call_data = active_telnyx_calls[call_control_id]
                    session = call_data.get("session")
                
                    # Skip first chunk if it's a continuous voice flow (contains greeting)
                    if call_data.get("flow_type") == "voice_continuous" and not call_data.get("first_chunk_processed"):
                        logger.info("⏭️  Skipping first recording chunk (greeting)")
                        call_data["first_chunk_processed"] = True
                        return {"status": "ok"}
                
                    if session:
                        # Get the gathered result
                        gather_payload = payload.get("data", {}).get("payload", {})
                        digits = gather_payload.get("digits", "")
                        status = gather_payload.get("status", "")
                    
                        logger.info(f"📝 Gather result - status: '{status}', digits: '{digits}'")
                    
                        # Check if it was a speech gather (status = 'call_hangup' or 'timeout')
                        # For speech gathers, we don't get digits - need to use recording or stream
                        # Since gather_using_speak doesn't return speech transcript, we need recording
                    
                        if status == "valid":
                            # DTMF digit was pressed
                            user_input = digits
                            logger.info(f"🔢 Processing DTMF digit: {user_input}")
                        
                            # Save user input to transcript
                            await db.call_logs.update_one(
                                {"call_id": call_control_id},
                                {"$push": {
                                    "transcript": {
                                        "role": "user",
                                        "text": f"Pressed {user_input}",
                                        "timestamp": datetime.utcnow().isoformat()
                                    }
                                }}
                            )
                        
                            # Process through AI
                            try:
                                response = await session.process_user_input(user_input)
                                response_text = response.get("text", "I'm sorry, I didn't understand that.")
                            
                                logger.info(f"🤖 AI response: {response_text}")
                            
                                # Save AI response to transcript
                                await db.call_logs.update_one(
                                    {"call_id": call_control_id},
                                    {"$push": {
                                        "transcript": {
                                            "role": "assistant",
                                            "text": response_text,
                                            "timestamp": datetime.utcnow().isoformat()
                                        }
                                    }}
                                )
                            
                                # Check if should end call
                                if session.should_end_call:
                                    logger.info("📞 Ending node reached - hanging up")
                                    telnyx_service = get_telnyx_service()
                                    agent_config = session.agent_config
                                    # 🔥 CRITICAL FIX: Mark agent as speaking before emitting audio
                                    session.mark_agent_speaking_start()
                                    await telnyx_service.speak_text(call_control_id, response_text, agent_config=agent_config)
                                    await asyncio.sleep(3)
                                    await telnyx_service.hangup_call(call_control_id)
                                    # Clean up from Redis and in-memory
                                    redis_service.delete_call_data(call_control_id)
                                    if call_control_id in active_telnyx_calls:
                                        del active_telnyx_calls[call_control_id]
                                else:
                                    # Continue conversation
                                    telnyx_service = get_telnyx_service()
                                    await telnyx_service.gather_using_speak(
                                        call_control_id=call_control_id,
                                        text=response_text,
                                        language="en-US",
                                        timeout_secs=5,
                                        max_digits=0
                                    )
                                    logger.info("🔊 Spoke AI response and listening for next input")
                            except Exception as e:
                                logger.error(f"Error processing gather result: {e}")
                        else:
                            # Timeout or no input - start recording to capture speech
                            logger.info(f"⏱️ Gather timeout - starting recording to capture speech")
                            telnyx_service = get_telnyx_service()
                            await telnyx_service.start_recording(
                                call_control_id=call_control_id,
                                format="wav",
                                channels="single"
                            )
                            call_data["recording_start_time"] = time.time()
                        
                            # Stop after 3 seconds
                            async def stop_gather_recording():
                                await asyncio.sleep(3)
                                if call_control_id in active_telnyx_calls:
                                    try:
                                        await telnyx_service.stop_recording(call_control_id)
                                        logger.info("⏱️ Stopped gather recording")
                                    except:
                                        pass
                            asyncio.create_task(stop_gather_recording())
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}



@api_router.get("/telnyx/call/{call_id}")
async def get_call_log(call_id: str):
    """Get call log details including transcript"""
    try:
        call_log = await db.call_logs.find_one({"call_id": call_id})
        
        if not call_log:
            raise HTTPException(status_code=404, detail="Call log not found")
        
        # Convert ObjectId to string if present
        if "_id" in call_log:
            call_log["_id"] = str(call_log["_id"])
        
        # Convert datetime objects to ISO strings
        for field in ["start_time", "end_time", "answered_at", "created_at", "updated_at"]:
            if field in call_log and call_log[field]:
                call_log[field] = call_log[field].isoformat() if hasattr(call_log[field], 'isoformat') else str(call_log[field])
        
        return call_log
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching call log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve TTS audio files
from fastapi.responses import FileResponse
import os

@api_router.get("/tts-audio/{filename}")
async def serve_tts_audio(filename: str):
    """Serve generated TTS audio files"""
    file_path = f"/tmp/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg")

# Include the router in the main app


# ==================== CALL HISTORY & ANALYTICS API ====================

@api_router.get("/call-history", response_model=dict)
async def get_call_history(
    current_user: dict = Depends(get_current_user),
    agent_id: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get call history with filters"""
    try:
        # Build query - ALWAYS filter by user_id for multi-tenant isolation
        query = {"user_id": current_user['id']}
        
        logger.info(f"📞 Call history request - user_id: {current_user['id']}, limit: {limit}, offset: {offset}")
        
        if agent_id:
            query["agent_id"] = agent_id
        
        if direction:
            query["direction"] = direction
        
        if status:
            query["status"] = status
        
        if start_date:
            query["start_time"] = {"$gte": datetime.fromisoformat(start_date)}
        
        if end_date:
            if "start_time" in query:
                query["start_time"]["$lte"] = datetime.fromisoformat(end_date)
            else:
                query["start_time"] = {"$lte": datetime.fromisoformat(end_date)}
        
        logger.info(f"📞 Query: {query}")
        
        # Get total count first
        total_count = await db.call_logs.count_documents(query)
        
        # Query database - sort by created_at since start_time may not exist in all records
        # Try start_time first, fall back to created_at
        cursor = db.call_logs.find(query).sort("created_at", -1).skip(offset).limit(limit)
        calls = await cursor.to_list(length=limit)
        
        logger.info(f"📞 Found {len(calls)} calls for user (Total: {total_count})")
        
        # Convert ObjectId to string and datetime to ISO
        for call in calls:
            if "_id" in call:
                call["_id"] = str(call["_id"])
            # Handle both start_time and created_at for sorting display
            if "start_time" in call and call["start_time"]:
                if hasattr(call["start_time"], 'isoformat'):
                    call["start_time"] = call["start_time"].isoformat()
            elif "created_at" in call and call["created_at"]:
                # Use created_at as start_time if start_time doesn't exist
                if hasattr(call["created_at"], 'isoformat'):
                    call["start_time"] = call["created_at"].isoformat()
                else:
                    call["start_time"] = str(call["created_at"])
            if "end_time" in call and call["end_time"]:
                if hasattr(call["end_time"], 'isoformat'):
                    call["end_time"] = call["end_time"].isoformat()
            if "answered_at" in call and call["answered_at"]:
                if hasattr(call["answered_at"], 'isoformat'):
                    call["answered_at"] = call["answered_at"].isoformat()
            if "created_at" in call and call["created_at"]:
                if hasattr(call["created_at"], 'isoformat'):
                    call["created_at"] = call["created_at"].isoformat()
        
        return {
            "calls": calls,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching call history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/call-history/{call_id}/recording")
async def get_call_recording(call_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Download and serve recording directly from Telnyx with Range support for seeking"""
    from fastapi.responses import Response, StreamingResponse
    
    try:
        call = await db.call_logs.find_one({"call_id": call_id, "user_id": current_user['id']})
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        recording_id = call.get("recording_id")
        if not recording_id:
            raise HTTPException(status_code=404, detail="No recording ID found for this call")
        
        # Download recording from Telnyx
        telnyx_service = get_telnyx_service()
        recording_result = await telnyx_service.get_recording(recording_id)
        
        if not recording_result.get("success"):
            raise HTTPException(status_code=500, detail=f"Failed to fetch recording from Telnyx: {recording_result.get('error')}")
        
        recording_content = recording_result.get("content")
        if not recording_content:
            raise HTTPException(status_code=404, detail="Recording content not available")
        
        content_length = len(recording_content)
        content_type = recording_result.get("content_type", "audio/mpeg")
        
        # Handle Range requests for seeking support
        range_header = request.headers.get("range")
        
        if range_header:
            # Parse range header: "bytes=0-1023" or "bytes=1024-"
            try:
                range_match = range_header.replace("bytes=", "").split("-")
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else content_length - 1
                
                # Ensure valid range
                start = max(0, min(start, content_length - 1))
                end = max(start, min(end, content_length - 1))
                
                # Slice content
                partial_content = recording_content[start:end + 1]
                
                return Response(
                    content=partial_content,
                    status_code=206,  # Partial Content
                    media_type=content_type,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{content_length}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(len(partial_content)),
                        "Content-Disposition": f"inline; filename=recording_{call_id[:20]}.mp3",
                        "Cache-Control": "public, max-age=31536000"
                    }
                )
            except (ValueError, IndexError):
                # Invalid range, fall through to full response
                pass
        
        # Full response with Accept-Ranges header to indicate seeking support
        return Response(
            content=recording_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename=recording_{call_id[:20]}.mp3",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Cache-Control": "public, max-age=31536000"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/call-history/{call_id}")
async def get_call_detail(call_id: str, current_user: dict = Depends(get_current_user)):
    """Get detailed call information including transcript"""
    try:
        call = await db.call_logs.find_one({"call_id": call_id, "user_id": current_user['id']})
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Convert fields
        if "_id" in call:
            call["_id"] = str(call["_id"])
        if "start_time" in call:
            call["start_time"] = call["start_time"].isoformat()
        if "end_time" in call and call["end_time"]:
            call["end_time"] = call["end_time"].isoformat()
        if "answered_at" in call and call["answered_at"]:
            call["answered_at"] = call["answered_at"].isoformat()
        
        # Add computed fields for conversation analysis
        if "call_successful" not in call:
            # Determine if call was successful based on duration and status
            call["call_successful"] = call.get("status") == "completed" and call.get("duration", 0) > 10
        
        if "sentiment" not in call:
            # Simple sentiment based on call completion
            call["sentiment"] = "Positive" if call.get("call_successful") else "Neutral"
        
        if "disconnect_reason" not in call:
            call["disconnect_reason"] = "User_hangup" if call.get("status") == "completed" else "Unknown"
        
        if "e2e_latency" not in call:
            # Compute average latency from logs if available
            latency_values = []
            if call.get("logs"):
                for log in call["logs"]:
                    if "E2E latency" in log.get("message", ""):
                        # Extract latency value from message like "E2E latency for this turn: 1234ms"
                        try:
                            import re
                            match = re.search(r"E2E latency for this turn: (\d+)ms", log["message"])
                            if match:
                                latency_values.append(int(match.group(1)))
                        except:
                            pass
            
            if latency_values:
                call["e2e_latency"] = int(sum(latency_values) / len(latency_values))
            else:
                call["e2e_latency"] = None
        
        # Generate simple logs if not present
        if "logs" not in call or not call["logs"]:
            call["logs"] = []
            
            if call.get("start_time"):
                call["logs"].append({
                    "timestamp": call["start_time"],
                    "level": "info",
                    "message": f"Call started - {call.get('direction', 'unknown')} call from {call.get('from_number', 'unknown')} to {call.get('to_number', 'unknown')}"
                })
            
            if call.get("transcript"):
                for i, msg in enumerate(call["transcript"][:10]):  # First 10 messages
                    # Support both old (speaker) and new (role) format
                    is_user = msg.get('role') == 'user' or msg.get('speaker') == 'user'
                    speaker_label = 'User' if is_user else 'Agent'
                    call["logs"].append({
                        "timestamp": msg.get("timestamp", call.get("start_time")),
                        "level": "info",
                        "message": f"{speaker_label} message: {msg.get('text', '')[:100]}..."
                    })
            
            if call.get("end_time"):
                call["logs"].append({
                    "timestamp": call["end_time"],
                    "level": "info",
                    "message": f"Call ended - Status: {call.get('status', 'unknown')}, Duration: {call.get('duration', 0)}s"
                })
        
        # Add agent name if not present
        if "agent_name" not in call and call.get("agent_id"):
            # Try to fetch agent name
            try:
                agent = await db.agents.find_one({"id": call["agent_id"]})
                if agent:
                    call["agent_name"] = agent.get("name", "Unknown Agent")
            except:
                call["agent_name"] = "Unknown Agent"
        
        # Ensure version field
        if "version" not in call:
            call["version"] = 0
        
        # Ensure cost and llm_tokens
        if "cost" not in call:
            call["cost"] = 0.0
        if "llm_tokens" not in call:
            call["llm_tokens"] = 0.0
        
        return call
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching call detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/dashboard/analytics")
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    """Get real-time dashboard analytics"""
    try:
        from datetime import datetime, timedelta, timezone
        
        # Get today's date range
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Total calls today - filtered by user_id for multi-tenant isolation
        total_calls_today = await db.call_logs.count_documents({
            "user_id": current_user['id'],
            "start_time": {"$gte": today_start}
        })
        
        # Yesterday's calls for comparison - filtered by user_id
        yesterday_start = today_start - timedelta(days=1)
        yesterday_calls = await db.call_logs.count_documents({
            "user_id": current_user['id'],
            "start_time": {"$gte": yesterday_start, "$lt": today_start}
        })
        calls_change = ((total_calls_today - yesterday_calls) / yesterday_calls * 100) if yesterday_calls > 0 else 0
        
        # Average response time (E2E latency) - filtered by user_id
        pipeline = [
            {"$match": {"user_id": current_user['id'], "logs": {"$exists": True, "$ne": []}}},
            {"$unwind": "$logs"},
            {"$match": {"logs.message": {"$regex": "E2E latency"}}},
            {"$limit": 100}  # Last 100 calls with latency
        ]
        
        latency_calls = await db.call_logs.aggregate(pipeline).to_list(length=100)
        latencies = []
        for call in latency_calls:
            try:
                import re
                match = re.search(r"E2E latency for this turn: (\d+)ms", call["logs"]["message"])
                if match:
                    latencies.append(int(match.group(1)))
            except:
                pass
        
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        avg_latency_seconds = avg_latency / 1000  # Convert to seconds
        
        # Success rate - filtered by user_id
        total_calls = await db.call_logs.count_documents({"user_id": current_user['id']})
        successful_calls = await db.call_logs.count_documents({"user_id": current_user['id'], "status": "completed"})
        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Active agents count - filtered by user_id
        active_agents = await db.agents.count_documents({"user_id": current_user['id']})
        
        # Get total call count - filtered by user_id
        total_all_time = await db.call_logs.count_documents({"user_id": current_user['id']})
        
        # Voicemail detection stats - filtered by user_id
        voicemail_detected_today = await db.call_logs.count_documents({
            "user_id": current_user['id'],
            "start_time": {"$gte": today_start},
            "status": "voicemail_detected"
        })
        voicemail_detected_all_time = await db.call_logs.count_documents({
            "user_id": current_user['id'],
            "status": "voicemail_detected"
        })
        
        # Calculate voicemail detection rate
        voicemail_rate = (voicemail_detected_today / total_calls_today * 100) if total_calls_today > 0 else 0
        
        return {
            "total_calls_today": total_calls_today,
            "calls_change_percent": round(calls_change, 1),
            "active_agents": active_agents,
            "avg_response_time": round(avg_latency_seconds, 2),
            "success_rate": round(success_rate, 1),
            "total_all_time": total_all_time,
            "voicemail_detected_today": voicemail_detected_today,
            "voicemail_detected_all_time": voicemail_detected_all_time,
            "voicemail_rate": round(voicemail_rate, 1)
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/call-analytics")
async def get_comprehensive_call_analytics(
    current_user: dict = Depends(get_current_user),
    agent_id: Optional[str] = None,
    call_id: Optional[str] = None,
    batch_call_id: Optional[str] = None,
    type: Optional[str] = None,
    duration_min: Optional[int] = None,
    duration_max: Optional[int] = None,
    from_number: Optional[str] = None,
    to_number: Optional[str] = None,
    user_sentiment: Optional[str] = None,
    disconnection_reason: Optional[str] = None,
    call_status: Optional[str] = None,
    call_successful: Optional[str] = None,
    e2e_latency_min: Optional[int] = None,
    e2e_latency_max: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get call analytics and metrics with comprehensive filtering"""
    try:
        # Build query - MUST filter by user_id for multi-tenant isolation
        query = {"user_id": current_user['id']}
        
        if agent_id:
            query["agent_id"] = agent_id
        
        if call_id:
            query["call_id"] = {"$regex": call_id, "$options": "i"}
        
        if batch_call_id:
            query["batch_call_id"] = batch_call_id
        
        if type:  # direction filter
            query["direction"] = type
        
        if duration_min is not None or duration_max is not None:
            query["duration"] = {}
            if duration_min is not None:
                query["duration"]["$gte"] = duration_min
            if duration_max is not None:
                query["duration"]["$lte"] = duration_max
        
        if from_number:
            query["from_number"] = {"$regex": from_number, "$options": "i"}
        
        if to_number:
            query["to_number"] = {"$regex": to_number, "$options": "i"}
        
        if user_sentiment:
            query["sentiment"] = user_sentiment
        
        if disconnection_reason:
            query["disconnect_reason"] = disconnection_reason
        
        if call_status:
            query["status"] = call_status
        
        if call_successful:
            query["call_successful"] = call_successful == "true"
        
        if e2e_latency_min is not None or e2e_latency_max is not None:
            query["e2e_latency"] = {}
            if e2e_latency_min is not None:
                query["e2e_latency"]["$gte"] = e2e_latency_min
            if e2e_latency_max is not None:
                query["e2e_latency"]["$lte"] = e2e_latency_max
        
        if start_date or end_date:
            query["start_time"] = {}
            if start_date:
                query["start_time"]["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                query["start_time"]["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Aggregate statistics
        total_calls = await db.call_logs.count_documents(query)
        
        # Get all calls for aggregation
        calls = await db.call_logs.find(query).to_list(length=None)
        
        # Calculate metrics
        successful_calls = sum(1 for c in calls if c.get("status") == "completed")
        failed_calls = sum(1 for c in calls if c.get("status") in ["failed", "busy", "no-answer"])
        total_duration = sum(c.get("duration", 0) for c in calls)
        total_cost = sum(c.get("cost", 0.0) for c in calls)
        
        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        
        # Sentiment breakdown
        sentiment_breakdown = {
            "positive": sum(1 for c in calls if c.get("sentiment") == "positive"),
            "neutral": sum(1 for c in calls if c.get("sentiment") == "neutral"),
            "negative": sum(1 for c in calls if c.get("sentiment") == "negative"),
            "unknown": sum(1 for c in calls if c.get("sentiment") == "unknown")
        }
        
        # Calculate average sentiment score
        sentiment_scores = [c.get("user_sentiment_score", 0) for c in calls if c.get("user_sentiment_score")]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Calculate average latency
        latencies = [c.get("latency_avg", 0) for c in calls if c.get("latency_avg")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        # Group by status for disconnection reasons
        by_status = {}
        for call in calls:
            status = call.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
        
        # Group by direction
        by_direction = {}
        for call in calls:
            direction = call.get("direction", "unknown")
            by_direction[direction] = by_direction.get(direction, 0) + 1
        
        # Group calls by date for time series
        from collections import defaultdict
        call_count_by_date = defaultdict(int)
        for call in calls:
            if call.get("start_time"):
                date_key = call["start_time"].strftime("%Y-%m-%d")
                call_count_by_date[date_key] += 1
        
        # Convert to sorted list
        call_count_data = [{"date": date, "count": count} for date, count in sorted(call_count_by_date.items())]
        
        # Calculate success rate
        completed_calls = sum(1 for c in calls if c.get("status") == "completed")
        success_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
        
        analytics = {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": round(success_rate, 1),
            "avg_duration": round(avg_duration, 2),
            "total_duration": total_duration,
            "total_cost": round(total_cost, 2),
            "avg_sentiment": round(avg_sentiment, 3),
            "sentiment_positive": sentiment_breakdown.get("positive", 0),
            "sentiment_negative": sentiment_breakdown.get("negative", 0),
            "sentiment_neutral": sentiment_breakdown.get("neutral", 0),
            "sentiment_unknown": sentiment_breakdown.get("unknown", 0),
            "avg_latency": round(avg_latency, 2),
            "by_status": by_status,
            "by_direction": by_direction,
            "call_count_by_date": call_count_data,
            "period_start": start_date or "all_time",
            "period_end": end_date or "now"
        }
        
        return analytics
    except Exception as e:
        logger.error(f"Error calculating analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/call-history/{call_id}")
async def delete_call_log(call_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a call log"""
    try:
        result = await db.call_logs.delete_one({"call_id": call_id, "user_id": current_user['id']})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Call not found")
        
        return {"message": "Call log deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting call log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ CORS CONFIGURATION ============
# CRITICAL: CORS middleware MUST be added BEFORE any routers
cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

if not cors_origins:
    cors_origins = ["http://localhost:3000"]
    logger.warning("⚠️ No CORS_ORIGINS set, defaulting to localhost:3000")
else:
    logger.info(f"✅ CORS configured for origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ============ QC ENHANCED ROUTER (4-Tab System) ============
# IMPORTANT: Must be included in api_router BEFORE api_router is added to app
from qc_enhanced_router import qc_enhanced_router, set_db as set_qc_enhanced_db, run_full_qc_analysis
set_qc_enhanced_db(db)  # Inject database connection
api_router.include_router(qc_enhanced_router)  # Include under /api prefix
logger.info("✅ QC enhanced router loaded")

# ============ QC AGENT ROUTER (Custom QC Agent System) ============
from qc_agent_router import qc_agent_router, set_db as set_qc_agent_db
set_qc_agent_db(db)  # Inject database connection
api_router.include_router(qc_agent_router)  # Include under /api prefix
logger.info("✅ QC agent router loaded")

# ============ QC LEARNING ROUTER (Memory & Playbook System) ============
from qc_learning_router import qc_learning_router, set_learning_db
set_learning_db(db)  # Inject database connection
api_router.include_router(qc_learning_router)  # Include under /api prefix
logger.info("✅ QC learning router loaded")

# ============ VOICE LIBRARY ROUTER (Maya TTS Voice Cloning) ============
from voice_library_router import voice_library_router, load_voice_sample
api_router.include_router(voice_library_router)  # Include under /api prefix
logger.info("✅ Voice library router loaded")

# Debug endpoint to test post-call automation
@api_router.post("/debug/test-post-call-automation/{call_id}")
async def test_post_call_automation(call_id: str, current_user: dict = Depends(get_current_user)):
    """
    Debug endpoint to manually trigger post-call automation (QC + CRM) for a specific call.
    This simulates what happens in the call.hangup handler.
    """
    results = {
        "call_id": call_id,
        "user_id": current_user.get('id'),
        "steps": []
    }
    
    try:
        # Step 1: Find the call in call_logs
        call_log = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id},
                {"id": call_id}
            ],
            "user_id": current_user.get('id')
        })
        
        if not call_log:
            results["steps"].append({"step": "find_call", "status": "error", "message": f"Call not found: {call_id}"})
            return results
        
        results["steps"].append({
            "step": "find_call", 
            "status": "success",
            "data": {
                "call_id": call_log.get("call_id"),
                "agent_id": call_log.get("agent_id"),
                "to_number": call_log.get("to_number"),
                "transcript_turns": len(call_log.get("transcript", [])),
                "status": call_log.get("status")
            }
        })
        
        agent_id = call_log.get("agent_id")
        user_id = current_user.get('id')
        to_number = call_log.get("to_number")
        
        # Step 2: Check agent's auto_qc_settings
        if agent_id:
            agent = await db.agents.find_one({"id": agent_id, "user_id": user_id})
            if agent:
                auto_qc = agent.get("auto_qc_settings", {})
                results["steps"].append({
                    "step": "check_agent_qc_settings",
                    "status": "success",
                    "data": {
                        "agent_name": agent.get("name"),
                        "auto_qc_enabled": auto_qc.get("enabled", False),
                        "campaign_id": auto_qc.get("campaign_id"),
                        "run_tech": auto_qc.get("run_tech_analysis", True),
                        "run_script": auto_qc.get("run_script_analysis", True),
                        "run_tonality": auto_qc.get("run_tonality_analysis", True)
                    }
                })
                
                # Step 3: Trigger Campaign QC if enabled
                if auto_qc.get("enabled") and auto_qc.get("campaign_id"):
                    results["steps"].append({
                        "step": "trigger_campaign_qc",
                        "status": "triggered",
                        "message": f"Triggering QC for campaign {auto_qc.get('campaign_id')}"
                    })
                    
                    # Actually trigger it
                    asyncio.create_task(trigger_campaign_qc_for_call(
                        call_id=call_log.get("call_id") or call_id,
                        user_id=user_id,
                        agent_id=agent_id
                    ))
                else:
                    results["steps"].append({
                        "step": "trigger_campaign_qc",
                        "status": "skipped",
                        "message": "Auto QC not enabled or no campaign_id configured"
                    })
            else:
                results["steps"].append({
                    "step": "check_agent_qc_settings",
                    "status": "error",
                    "message": f"Agent not found: {agent_id}"
                })
        else:
            results["steps"].append({
                "step": "check_agent_qc_settings",
                "status": "skipped",
                "message": "No agent_id in call log"
            })
        
        # Step 4: Trigger CRM update
        if to_number:
            results["steps"].append({
                "step": "trigger_crm_update",
                "status": "triggered",
                "message": f"Triggering CRM update for {to_number}"
            })
            
            # Actually trigger it
            agent_name = "Debug Test Agent"
            if agent_id:
                agent_doc = await db.agents.find_one({"id": agent_id}, {"name": 1})
                if agent_doc:
                    agent_name = agent_doc.get("name", agent_name)
            
            asyncio.create_task(update_crm_after_call(
                call_id=call_log.get("call_id") or call_id,
                user_id=user_id,
                agent_id=agent_id,
                agent_name=agent_name,
                to_number=to_number,
                custom_variables=call_log.get("custom_variables", {})
            ))
        else:
            results["steps"].append({
                "step": "trigger_crm_update",
                "status": "skipped",
                "message": "No to_number in call log"
            })
        
        results["status"] = "success"
        results["message"] = "Post-call automation triggered. Check logs and database for results."
        
    except Exception as e:
        results["status"] = "error"
        results["message"] = str(e)
        logger.error(f"Error in debug post-call automation: {e}")
    
    return results

app.include_router(api_router)

# ============ CRM ROUTER INTEGRATION ============
from crm_router import crm_router, set_db as set_crm_db
set_crm_db(db)  # Inject database connection
app.include_router(crm_router)
logger.info("✅ CRM router loaded")

# ============ QC TEST ROUTER INTEGRATION ============
from qc_test_router import qc_test_router, set_db as set_qc_test_db
set_qc_test_db(db)  # Inject database connection
app.include_router(qc_test_router)
logger.info("✅ QC test router loaded")

# ============ AGENT TESTING ROUTER ============
from agent_test_router import router as agent_test_router, set_db as set_agent_test_db
set_agent_test_db(db)  # Inject database connection
app.include_router(agent_test_router)
logger.info("✅ Agent test router loaded")

# ============ DIRECTOR STUDIO ROUTER ============
from director_router import router as director_router
app.include_router(director_router)
logger.info("✅ Director Studio router loaded")

# ============ QC AGENTS INTEGRATION ============
from qc_agents.orchestrator import QCAgentOrchestrator
qc_orchestrator = None  # Will be initialized per-request

async def process_qc_analysis(call_id: str, user_id: str, lead_id: str = None, agent_id: str = None):
    """
    Trigger QC analysis for a completed call
    Runs asynchronously in background
    """
    try:
        logger.info(f"🔍 Starting QC analysis for call {call_id}")
        
        # Get call log with transcript
        call_log = await db.call_logs.find_one({"call_id": call_id, "user_id": user_id})
        if not call_log:
            logger.warning(f"⚠️ Call log not found for QC analysis: {call_id}")
            return
        
        transcript_data = call_log.get("transcript", [])
        if not transcript_data:
            logger.warning(f"⚠️ No transcript available for QC analysis: {call_id}")
            return
        
        # Convert list of message objects to single concatenated string
        if isinstance(transcript_data, list):
            transcript_parts = []
            for msg in transcript_data:
                role = msg.get("role", "unknown")
                content = msg.get("text", msg.get("content", ""))
                transcript_parts.append(f"{role}: {content}")
            transcript = "\n".join(transcript_parts)
        else:
            # If it's already a string, use it as-is
            transcript = str(transcript_data)
        
        logger.info(f"📝 Converted transcript from {len(transcript_data)} messages to {len(transcript)} characters")
        
        # Get API key for LLM calls - use user's OpenAI key
        api_key = await get_api_key(user_id, "openai")
        
        if not api_key:
            logger.warning(f"⚠️ No OpenAI API key available for QC analysis for user {user_id}")
            return
        
        # Initialize orchestrator
        orchestrator = QCAgentOrchestrator(db, api_key)
        
        # Prepare metadata
        metadata = {
            'duration_seconds': call_log.get('duration', 0),
            'call_hour': datetime.utcnow().hour,
            'day_of_week': datetime.utcnow().weekday()
        }
        
        # Run QC analysis
        analysis_result = await orchestrator.analyze_call(
            call_id=call_id,
            user_id=user_id,
            transcript=transcript,
            metadata=metadata,
            lead_id=lead_id,
            agent_id=agent_id
        )
        
        if not analysis_result:
            logger.warning(f"⚠️ QC analysis returned no result for call {call_id}")
            return
        
        logger.info(f"✅ QC analysis completed for call {call_id}")
        scores = analysis_result.get('aggregated_scores', {}) or {}
        logger.info(f"📊 Scores: Commitment={scores.get('commitment_score')}, "
                   f"Conversion={scores.get('conversion_score')}, "
                   f"Excellence={scores.get('excellence_score')}")
        
        # Update campaign_calls with QC results if the call is in a campaign
        try:
            campaign_call = await db.campaign_calls.find_one({"call_id": call_id})
            if campaign_call:
                await db.campaign_calls.update_one(
                    {"call_id": call_id},
                    {"$set": {
                        "auto_analyzed": True,
                        "analyzed_at": datetime.utcnow(),
                        "qc_scores": scores,
                        "status": "completed"
                    }}
                )
                logger.info(f"📊 Updated campaign_calls with QC scores for {call_id}")
        except Exception as e:
            logger.error(f"Error updating campaign_calls: {e}")
        
        # Sync scores to lead if we have a phone number
        try:
            if lead_id:
                await db.leads.update_one(
                    {"id": lead_id},
                    {"$set": {
                        "commitment_score": scores.get('commitment_score'),
                        "conversion_score": scores.get('conversion_score'),
                        "excellence_score": scores.get('excellence_score'),
                        "show_up_probability": scores.get('show_up_probability'),
                        "risk_level": scores.get('risk_level'),
                        "qc_updated_at": datetime.utcnow()
                    }}
                )
                logger.info(f"📈 Synced QC scores to lead {lead_id}")
            else:
                # Try to find lead by phone from call log
                if call_log.get('to_number'):
                    to_number = call_log.get('to_number')
                    lead = await db.leads.find_one({"phone": to_number, "user_id": user_id})
                    if lead:
                        await db.leads.update_one(
                            {"id": lead['id']},
                            {"$set": {
                                "commitment_score": scores.get('commitment_score'),
                                "conversion_score": scores.get('conversion_score'),
                                "excellence_score": scores.get('excellence_score'),
                                "show_up_probability": scores.get('show_up_probability'),
                                "risk_level": scores.get('risk_level'),
                                "qc_updated_at": datetime.utcnow()
                            }}
                        )
                        logger.info(f"📈 Synced QC scores to lead {lead['id']} via phone match")
        except Exception as e:
            logger.error(f"Error syncing scores to lead: {e}")
        
        # Update lead status based on risk level
        try:
            risk_level = scores.get('risk_level', 'medium')
            status_map = {
                'low': 'qualified',
                'medium': 'contacted',
                'high': 'needs_followup'
            }
            new_status = status_map.get(risk_level, 'contacted')
            
            if lead_id:
                await db.leads.update_one(
                    {"id": lead_id},
                    {"$set": {"status": new_status}}
                )
            elif call_log.get('to_number'):
                await db.leads.update_one(
                    {"phone": call_log.get('to_number'), "user_id": user_id},
                    {"$set": {"status": new_status}}
                )
            logger.info(f"🏷️ Updated lead status to '{new_status}' based on risk level '{risk_level}'")
        except Exception as e:
            logger.error(f"Error updating lead status: {e}")
        
        # Auto-detect appointments from transcript
        try:
            await auto_detect_appointment_from_call(call_id, user_id, transcript)
        except Exception as e:
            logger.error(f"Error in auto appointment detection: {e}")
        
    except Exception as e:
        logger.error(f"❌ Error in QC analysis for call {call_id}: {e}")


async def auto_detect_appointment_from_call(call_id: str, user_id: str, transcript: list):
    """
    Automatically detect if an appointment was set during the call.
    If detected, creates an appointment record in the CRM.
    """
    try:
        if not transcript or len(transcript) < 2:
            logger.info(f"📅 Skipping appointment detection - insufficient transcript for {call_id}")
            return
        
        # Format transcript for analysis
        conversation_text = ""
        for entry in transcript:
            role = entry.get('role', entry.get('speaker', 'unknown'))
            text = entry.get('text', entry.get('content', ''))
            conversation_text += f"{role}: {text}\n"
        
        # Quick keyword check before LLM call
        appointment_keywords = [
            'appointment', 'schedule', 'book', 'meeting', 'call back',
            'tomorrow', 'next week', 'monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'morning', 'afternoon', 'pm', 'am',
            'see you', 'talk to you', 'speak with you', 'confirm'
        ]
        
        conversation_lower = conversation_text.lower()
        has_keywords = any(kw in conversation_lower for kw in appointment_keywords)
        
        if not has_keywords:
            logger.info(f"📅 No appointment keywords found in call {call_id}")
            return
        
        logger.info(f"📅 Appointment keywords detected, analyzing call {call_id}")
        
        # Import the detection function from crm_router
        from crm_router import analyze_transcript_for_appointment
        
        result = await analyze_transcript_for_appointment(conversation_text, user_id)
        
        if not result.get('appointment_detected') or result.get('confidence', 0) < 0.7:
            logger.info(f"📅 No appointment detected in call {call_id} (confidence: {result.get('confidence', 0)})")
            return
        
        logger.info(f"📅 Appointment detected in call {call_id}! Confidence: {result.get('confidence')}")
        
        # Get call info
        call_log = await db.call_logs.find_one({"call_id": call_id}, {"_id": 0})
        if not call_log:
            return
        
        to_number = call_log.get('to_number')
        
        # Find or create lead
        lead = await db.leads.find_one({
            "phone": to_number,
            "user_id": user_id
        })
        
        if not lead:
            from uuid import uuid4
            lead = {
                "id": str(uuid4()),
                "user_id": user_id,
                "name": result.get('customer_name', 'Unknown'),
                "phone": to_number,
                "email": None,
                "source": "call",
                "status": "appointment_set",
                "total_calls": 1,
                "total_appointments": 0,
                "appointments_showed": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await db.leads.insert_one(lead)
            logger.info(f"📇 Created new lead {lead['id']} from call")
        
        # Create appointment
        from uuid import uuid4
        appointment_datetime = result.get('appointment_datetime')
        if not appointment_datetime:
            # Default to tomorrow noon
            appointment_datetime = datetime.utcnow() + timedelta(days=1)
            appointment_datetime = appointment_datetime.replace(hour=12, minute=0, second=0, microsecond=0)
        
        appointment = {
            "id": str(uuid4()),
            "user_id": user_id,
            "lead_id": lead['id'],
            "agent_id": call_log.get('agent_id'),
            "call_id": call_id,
            "scheduled_time": appointment_datetime,
            "status": "scheduled",
            "showed_up": None,
            "notes": f"Auto-detected from call. {result.get('notes', '')}",
            "detected_info": {
                "date": result.get('appointment_date'),
                "time": result.get('appointment_time'),
                "confidence": result.get('confidence'),
                "indicators": result.get('indicators', [])
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db.appointments.insert_one(appointment)
        
        # Update lead status
        await db.leads.update_one(
            {"id": lead['id']},
            {
                "$set": {
                    "status": "appointment_set",
                    "updated_at": datetime.utcnow()
                },
                "$inc": {"total_appointments": 1}
            }
        )
        
        # Update call log with appointment info
        await db.call_logs.update_one(
            {"call_id": call_id},
            {"$set": {
                "appointment_detected": True,
                "appointment_id": appointment['id']
            }}
        )
        
        logger.info(f"✅ Auto-created appointment {appointment['id']} from call {call_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in auto appointment detection for call {call_id}: {e}")


async def trigger_campaign_qc_for_call(call_id: str, user_id: str, agent_id: str):
    """
    Trigger campaign-specific QC analysis (Tech/Script/Tonality) if agent has auto_qc enabled.
    This runs the detailed analysis that populates campaign_calls with full QC results.
    """
    try:
        logger.info(f"🔍 [AUTO-QC] Starting campaign QC check for call={call_id}, user={user_id}, agent={agent_id}")
        
        # Verify call exists in call_logs first
        call_log = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": user_id},
                {"id": call_id, "user_id": user_id}
            ]
        })
        
        if call_log:
            transcript_len = len(call_log.get('transcript', []))
            logs_len = len(call_log.get('logs', []))
            logger.info(f"🔍 [AUTO-QC] Call log found: transcript_turns={transcript_len}, logs_count={logs_len}, status={call_log.get('status')}")
        else:
            logger.warning(f"⚠️ [AUTO-QC] Call log NOT FOUND in database for call={call_id}")
        
        # Get agent's auto QC settings
        agent = await db.agents.find_one({
            "id": agent_id,
            "user_id": user_id
        })
        
        if not agent:
            logger.warning(f"⚠️ [AUTO-QC] Agent not found: agent_id={agent_id}, user_id={user_id}")
            return
        
        logger.info(f"🔍 [AUTO-QC] Agent found: name={agent.get('name')}, has_auto_qc_settings={bool(agent.get('auto_qc_settings'))}")
        
        auto_qc = agent.get('auto_qc_settings', {})
        
        if not auto_qc.get('enabled', False):
            logger.info(f"ℹ️ [AUTO-QC] Auto QC not enabled for agent {agent_id}. Settings: {auto_qc}")
            return
        
        campaign_id = auto_qc.get('campaign_id')
        if not campaign_id:
            logger.warning(f"⚠️ [AUTO-QC] No campaign_id configured in auto_qc_settings: {auto_qc}")
            return
        
        # Verify campaign exists
        campaign = await db.campaigns.find_one({"id": campaign_id})
        if not campaign:
            logger.warning(f"⚠️ [AUTO-QC] Campaign not found: {campaign_id}")
            return
        
        logger.info(f"📊 [AUTO-QC] Running full QC analysis: call={call_id} → campaign={campaign_id} (tech={auto_qc.get('run_tech_analysis', True)}, script={auto_qc.get('run_script_analysis', True)}, tonality={auto_qc.get('run_tonality_analysis', True)})")
        logger.info(f"📊 [AUTO-QC] LLM settings: provider={auto_qc.get('llm_provider', 'grok')}, model={auto_qc.get('llm_model', 'grok-3')}")
        
        # Run the full campaign QC analysis
        await run_full_qc_analysis(
            call_id=call_id,
            user_id=user_id,
            agent_id=agent_id,
            campaign_id=campaign_id,
            run_tech=auto_qc.get('run_tech_analysis', True),
            run_script=auto_qc.get('run_script_analysis', True),
            run_tonality=auto_qc.get('run_tonality_analysis', True),
            llm_provider=auto_qc.get('llm_provider', 'grok'),
            model=auto_qc.get('llm_model', 'grok-3')
        )
        
        logger.info(f"✅ [AUTO-QC] Campaign QC completed successfully for call {call_id}")
        
    except Exception as e:
        import traceback
        logger.error(f"❌ [AUTO-QC] Error in campaign QC for call {call_id}: {e}")
        logger.error(f"❌ [AUTO-QC] Traceback: {traceback.format_exc()}")


async def update_crm_after_call(call_id: str, user_id: str, agent_id: str, agent_name: str, 
                                 to_number: str, custom_variables: dict = None):
    """
    Update or create CRM lead after a call ends.
    Uses phone number to find existing lead, or creates new one if not found.
    Updates call count, last contact time, and extracted variables.
    
    Variable Sources (in order of priority):
    1. Extracted session variables from the call session
    2. custom_variables passed at call initiation
    3. call_log custom_variables stored during the call
    
    Supported CRM Fields:
    - name / customer_name: Lead's name
    - email / customer_email: Lead's email
    - income_range / annual_income / income: Income information
    - employment_status / job_title / occupation: Employment info
    - address / city / state / zip: Location info
    - company / employer: Company name
    - Any other extracted variables go to custom_fields
    """
    try:
        from uuid import uuid4
        from datetime import timezone
        from core_calling_service import get_call_session
        
        logger.info(f"📇 CRM update starting for call {call_id}: to_number={to_number}, user_id={user_id}")
        
        # Normalize phone number (remove non-digits except leading +)
        phone = to_number
        if phone:
            # Keep the + if present, remove other non-digits
            if phone.startswith('+'):
                phone = '+' + ''.join(filter(str.isdigit, phone[1:]))
            else:
                phone = '+' + ''.join(filter(str.isdigit, phone))
        
        if not phone or len(phone) < 10:
            logger.warning(f"⚠️ Cannot update CRM - invalid phone number: {to_number} (normalized: {phone})")
            return
        
        logger.info(f"📇 Normalized phone: {phone}")
        
        # Collect all variables from multiple sources
        all_variables = {}
        
        # Source 1: Get session variables from active call session (if still available)
        try:
            session = await get_call_session(call_id)
            if session and hasattr(session, 'session_variables') and session.session_variables:
                all_variables.update(session.session_variables)
                logger.info(f"📇 CRM: Got {len(session.session_variables)} variables from active session")
        except Exception as e:
            logger.debug(f"📇 CRM: No active session for {call_id} (normal after hangup): {e}")
        
        # Source 2: Get variables from custom_variables passed at call initiation
        if custom_variables:
            all_variables.update(custom_variables)
            logger.info(f"📇 CRM: Got {len(custom_variables)} variables from custom_variables")
        
        # Source 3: Get variables from call_log stored during the call
        call_log = await db.call_logs.find_one({"call_id": call_id})
        if call_log:
            # Check custom_variables in call_log
            log_vars = call_log.get("custom_variables", {})
            if log_vars:
                all_variables.update(log_vars)
                logger.info(f"📇 CRM: Got {len(log_vars)} variables from call_log")
            
            # Also check for extracted_variables field (some flows store here)
            extracted = call_log.get("extracted_variables", {})
            if extracted:
                all_variables.update(extracted)
                logger.info(f"📇 CRM: Got {len(extracted)} extracted variables")
        
        logger.info(f"📇 CRM: Total variables collected: {list(all_variables.keys())}")
        
        # Extract standard CRM fields from variables (with multiple aliases)
        customer_name = (
            all_variables.get("customer_name") or 
            all_variables.get("name") or
            all_variables.get("full_name") or
            all_variables.get("first_name")
        )
        
        customer_email = (
            all_variables.get("customer_email") or 
            all_variables.get("email") or
            all_variables.get("email_address")
        )
        
        income_range = (
            all_variables.get("income_range") or
            all_variables.get("annual_income") or
            all_variables.get("income") or
            all_variables.get("yearly_income") or
            all_variables.get("salary")
        )
        
        employment_status = (
            all_variables.get("employment_status") or
            all_variables.get("job_title") or
            all_variables.get("occupation") or
            all_variables.get("employment") or
            all_variables.get("job")
        )
        
        company = (
            all_variables.get("company") or
            all_variables.get("employer") or
            all_variables.get("company_name") or
            all_variables.get("business")
        )
        
        address = all_variables.get("address")
        city = all_variables.get("city")
        state = all_variables.get("state")
        zip_code = all_variables.get("zip") or all_variables.get("zip_code") or all_variables.get("postal_code")
        
        # Build custom_fields for any other extracted variables
        standard_fields = {
            "customer_name", "name", "full_name", "first_name",
            "customer_email", "email", "email_address",
            "income_range", "annual_income", "income", "yearly_income", "salary",
            "employment_status", "job_title", "occupation", "employment", "job",
            "company", "employer", "company_name", "business",
            "address", "city", "state", "zip", "zip_code", "postal_code",
            "to_number", "from_number", "phone_number", "now", "lead_id"  # System fields
        }
        
        custom_fields = {
            k: v for k, v in all_variables.items() 
            if k not in standard_fields and v is not None
        }
        
        # Try to find existing lead by phone number
        existing_lead = await db.leads.find_one({
            "user_id": user_id,
            "phone": phone
        })
        
        now = datetime.now(timezone.utc)
        
        if existing_lead:
            # Update existing lead
            update_data = {
                "updated_at": now,
                "last_contact": now,
                "last_agent_id": agent_id,
                "last_agent_name": agent_name
            }
            
            # Update name if provided and lead has no name or "Unknown"
            if customer_name and (not existing_lead.get("name") or existing_lead.get("name") == "Unknown"):
                update_data["name"] = customer_name
            
            # Update email if provided and lead has no email
            if customer_email and not existing_lead.get("email"):
                update_data["email"] = customer_email
            
            # Update income_range if provided
            if income_range:
                update_data["income_range"] = income_range
            
            # Update employment if provided
            if employment_status:
                update_data["employment_status"] = employment_status
            
            # Update company if provided
            if company:
                update_data["company"] = company
            
            # Update address fields if provided
            if address:
                update_data["address"] = address
            if city:
                update_data["city"] = city
            if state:
                update_data["state"] = state
            if zip_code:
                update_data["zip_code"] = zip_code
            
            # Merge custom_fields (add new, don't overwrite existing)
            if custom_fields:
                existing_custom = existing_lead.get("custom_fields", {})
                for k, v in custom_fields.items():
                    if v is not None:  # Only add non-null values
                        existing_custom[k] = v
                update_data["custom_fields"] = existing_custom
            
            await db.leads.update_one(
                {"id": existing_lead["id"]},
                {
                    "$set": update_data,
                    "$inc": {"total_calls": 1}
                }
            )
            logger.info(f"📇 CRM: Updated lead {existing_lead['id']} ({phone}) - fields: {list(update_data.keys())}")
        else:
            # Create new lead
            new_lead = {
                "id": str(uuid4()),
                "user_id": user_id,
                "name": customer_name or "Unknown",
                "email": customer_email,
                "phone": phone,
                "source": "outbound_call",
                "status": "contacted",
                "tags": ["auto_created"],
                "notes": f"Auto-created from outbound call via {agent_name}",
                # New extended fields
                "income_range": income_range,
                "employment_status": employment_status,
                "company": company,
                "address": address,
                "city": city,
                "state": state,
                "zip_code": zip_code,
                "custom_fields": custom_fields,
                # Agent tracking
                "last_agent_id": agent_id,
                "last_agent_name": agent_name,
                # Scores (to be filled by QC)
                "commitment_score": None,
                "conversion_score": None,
                "excellence_score": None,
                "show_up_probability": None,
                # Counters
                "total_calls": 1,
                "total_appointments": 0,
                "appointments_showed": 0,
                # Timestamps
                "created_at": now,
                "updated_at": now,
                "last_contact": now
            }
            
            await db.leads.insert_one(new_lead)
            logger.info(f"📇 CRM: Created new lead {new_lead['id']} ({phone}) with fields: name={customer_name}, income={income_range}, custom={list(custom_fields.keys())}")
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Error updating CRM after call {call_id}: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")


logger.info("✅ QC agents orchestrator loaded")

# CORS middleware already configured above (before routers)

# CORS Test Endpoint - No Auth Required
@app.get("/api/cors-test")
async def cors_test():
    """Test endpoint to verify CORS is working"""
    return {
        "status": "success",
        "message": "CORS is configured correctly!",
        "allowed_origins": cors_origins,
        "timestamp": datetime.utcnow().isoformat()
    }

# QC Configuration Endpoints
@app.get("/api/settings/qc-config")
async def get_qc_config(current_user: dict = Depends(get_current_user)):
    """Get user's QC agent configuration"""
    try:
        config = await db.user_preferences.find_one({
            'user_id': current_user['id'],
            'type': 'qc_config'
        })
        
        if not config:
            return {'model': 'gpt-4o'}  # Default
        
        return {'model': config.get('model', 'gpt-4o')}
    except Exception as e:
        logger.error(f"Error fetching QC config: {e}")
        return {'model': 'gpt-4o'}

@app.post("/api/settings/qc-config")
async def save_qc_config(request: dict, current_user: dict = Depends(get_current_user)):
    """Save user's QC agent configuration"""
    try:
        model = request.get('model', 'gpt-4o')
        
        # Validate model
        valid_models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo']
        if model not in valid_models:
            raise HTTPException(status_code=400, detail=f"Invalid model. Must be one of: {valid_models}")
        
        # Upsert config
        await db.user_preferences.update_one(
            {'user_id': current_user['id'], 'type': 'qc_config'},
            {'$set': {
                'user_id': current_user['id'],
                'type': 'qc_config',
                'model': model,
                'updated_at': datetime.utcnow()
            }},
            upsert=True
        )
        
        logger.info(f"✅ Updated QC config for user {current_user['id']}: model={model}")
        return {'success': True, 'model': model}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving QC config: {e}")
        raise HTTPException(status_code=500, detail="Failed to save QC configuration")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()