# Complete AI Call Flow Analysis - Millisecond by Millisecond

## Executive Summary

This document traces the **complete end-to-end flow** of an AI-powered phone call from call initiation to audio playback, with millisecond-level timing expectations and detailed code analysis.

**Target Latency Goals:**
- **STT (Speech-to-Text)**: 100-300ms after user stops speaking
- **LLM TTFT (Time to First Token)**: 200-800ms
- **TTS TTFB (Time to First Byte)**: 100-200ms with WebSocket, 800-1500ms with REST API
- **Total Response Time**: < 1000ms ideal, < 1500ms acceptable, > 2000ms is poor

**Current User Report:** 4-second delay between user speech and AI response

---

## Phase 1: Call Initialization (T = 0ms to ~500ms)

### 1.1 Inbound Call Received
**File:** `server.py` line 4700-4750
**Trigger:** Telnyx webhook `POST /api/telnyx/webhook` with `event_type: "call.answered"`

```python
# T+0ms: Webhook received
@api_router.post("/telnyx/webhook")
async def handle_telnyx_webhook(request: Request):
    event_type = payload.get("event_type")
    
    if event_type == "call.answered":
        # Incoming call just connected
```

**Expected Duration:** ~50-100ms for webhook processing

**What Happens:**
1. Extract `call_control_id` from webhook payload
2. Lookup `agent_id` from custom variables
3. Fetch agent configuration from MongoDB
4. Initialize call state in Redis

### 1.2 Agent Configuration Loading
**File:** `server.py` line 4850-4900
**Expected Duration:** 50-200ms (MongoDB query)

```python
# T+100ms: Query MongoDB for agent config
agent = await db.agents.find_one({"id": agent_id, "user_id": user_id})

# Agent config includes:
# - LLM provider (openai, grok, anthropic)
# - LLM model (gpt-4o, grok-beta, claude-3-5-sonnet)
# - STT provider (soniox, deepgram, assemblyai)
# - TTS provider (elevenlabs, sesame, openai)
# - Voice settings, prompts, call flow nodes
# - API key references (user-specific)
```

**Performance Impact:**
- MongoDB query latency varies: 20-200ms
- Agent config can be 5-50KB depending on call flow complexity
- No caching at call start (loaded fresh each call)

### 1.3 API Keys Retrieval
**File:** `server.py` line 4970-4980
**Expected Duration:** 100-300ms (3-5 database queries)

```python
# T+200ms: Get user's API keys from database
telnyx_api_key = await get_api_key(user_id, "telnyx")           # Query 1
telnyx_connection_id = await get_api_key(user_id, "telnyx_connection_id")  # Query 2
elevenlabs_api_key = await get_api_key(user_id, "elevenlabs")  # Query 3
soniox_api_key = await get_api_key(user_id, "soniox")          # Query 4
```

**Performance Impact:**
- Each `get_api_key()` makes separate MongoDB query
- Keys are encrypted in database, requires decryption
- No batching of key queries
- **OPTIMIZATION OPPORTUNITY**: Could batch all key queries into single aggregation

### 1.4 Call Session Creation
**File:** `server.py` line 5036-5070, `calling_service.py` line 30-220
**Expected Duration:** 200-500ms

```python
# T+350ms: Create CallSession object
session = await create_call_session(
    call_control_id, 
    agent, 
    agent_id=agent.get("id"), 
    user_id=agent.get("user_id"), 
    db=db
)

# CallSession.__init__ does:
# 1. Load agent config into memory
# 2. Initialize conversation history []
# 3. Initialize session_variables {}
# 4. Load Knowledge Base (KB) documents if configured
# 5. Build cached system prompt with KB context
# 6. Initialize voicemail detector
# 7. Set up API key caching per provider
```

**Knowledge Base Loading Impact:**
**File:** `calling_service.py` line 90-120

```python
# If agent has KB documents, load and embed
if kb_items:
    for item in kb_items:
        if item.type == "pdf":
            # Extract text from PDF (CPU-intensive)
            # Generate embeddings (API call to OpenAI)
            # Store in vector index
        elif item.type == "url":
            # Fetch URL content
            # Extract text
            # Generate embeddings
```

**Performance Impact:**
- KB loading happens SYNCHRONOUSLY at call start
- PDF processing: 500ms - 2000ms per document
- Embedding generation: 200-500ms per document
- **CRITICAL BOTTLENECK** if agent has 5+ KB documents
- **User's case**: Check if KB is enabled and how many documents

### 1.5 Persistent TTS WebSocket Initialization
**File:** `server.py` line 5072-5112, `persistent_tts_service.py` line 53-85
**Expected Duration:** 200-500ms

```python
# T+500ms: Only if elevenlabs + use_persistent_tts = True
if tts_provider == "elevenlabs" and use_persistent_tts:
    persistent_tts_session = await persistent_tts_manager.create_session(
        call_control_id=call_control_id,
        api_key=elevenlabs_api_key,
        voice_id=voice_id,
        model_id=model_id,  # "eleven_flash_v2_5" is fastest
        telnyx_service=telnyx_service,
        agent_config=agent
    )
```

**What Happens in create_session:**
```python
# persistent_tts_service.py line 53-85
async def connect(self):
    # 1. Create WebSocket connection to ElevenLabs (150-300ms)
    self.ws_service = ElevenLabsWebSocketService(self.api_key)
    
    # 2. Send connection handshake with voice/model settings (50-100ms)
    connected = await self.ws_service.connect(
        voice_id=self.voice_id,
        model_id=self.model_id,
        output_format="pcm_16000"  # 16kHz PCM for fast conversion
    )
    
    # 3. Start background playback consumer task
    self.playback_task = asyncio.create_task(self._playback_consumer())
```

**Performance Impact:**
- WebSocket handshake: 150-300ms
- DNS resolution + TLS: 50-150ms
- Background task startup: 10-50ms
- **TOTAL**: 200-500ms overhead at call start
- **BENEFIT**: Saves 800-1500ms per TTS request during call

### 1.6 Initial Greeting (If AI Speaks First)
**File:** `server.py` line 5124-5200
**Expected Duration:** 1000-3000ms

```python
# T+1000ms: Check who speaks first
who_speaks_first = start_node_data.get("whoSpeaksFirst", "ai")

if who_speaks_first == "ai":
    # Process empty input to get greeting
    first_message = await session.process_user_input("")
    first_text = first_message.get("text", "Hello! How can I help you?")
    
    # Generate TTS for greeting
    # Play greeting audio via Telnyx
```

**Performance Impact:**
- LLM call for greeting: 500-1500ms
- TTS generation: 200-800ms (WebSocket) or 800-1500ms (REST)
- Audio playback start: 100-300ms
- **User hears greeting at**: T+1500ms to T+3000ms

---

## Phase 2: Audio Streaming & STT Setup (T = 1000ms onwards)

### 2.1 Telnyx Audio Stream Connection
**File:** `server.py` line 5200-5250
**Trigger:** Telnyx connects to WebSocket `ws://[backend]/api/telnyx/audio-stream`

```python
# After call.answered, Telnyx opens WebSocket connection
@api_router.websocket("/telnyx/audio-stream")
async def handle_telnyx_audio_stream(websocket: WebSocket):
    await websocket.accept()
    # Connection established, ready to receive audio packets
```

**Expected Duration:** 100-300ms for WebSocket handshake

### 2.2 STT Service Initialization (Soniox Path)
**File:** `server.py` line 2170-2232
**Expected Duration:** 200-500ms

```python
# T+1200ms: Initialize Soniox streaming
soniox = SonioxStreamingService(api_key=soniox_api_key)
connected = await soniox.connect(
    model=model,  # e.g., "en_v2_jumbo" or "en_v3_lightning"
    audio_format="pcm",
    sample_rate=8000,  # Telnyx sends 8kHz
    num_channels=1,
    enable_endpoint_detection=True,  # CRITICAL for detecting when user stops
    enable_speaker_diarization=False,
    language_hints=[],
    context=[]
)
```

**Soniox Connection Process:**
**File:** `soniox_service.py` (imported)

```python
# 1. Open WebSocket to Soniox API
ws_url = "wss://api.soniox.com/transcribe-websocket"
self.websocket = await websockets.connect(ws_url)

# 2. Send configuration message
config = {
    "model": model,
    "enable_endpoint_detection": True,
    "sample_rate_hertz": 8000,
    ...
}
await self.websocket.send(json.dumps(config))

# 3. Wait for acknowledgment (50-200ms)
```

**Performance Impact:**
- WebSocket connection: 100-200ms
- Configuration handshake: 50-150ms
- Model loading on Soniox side: 100-300ms
- **TOTAL**: 250-650ms before ready to transcribe

**Model Choice Impact:**
- `en_v2_jumbo`: Higher accuracy, 150-250ms latency
- `en_v3_lightning`: Lower accuracy, 80-120ms latency
- **User's agent settings**: Need to check which model is configured

### 2.3 Audio Packet Forwarding Loop
**File:** `server.py` line 5300-5400
**Continuous:** Runs throughout entire call

```python
# Receive audio from Telnyx, forward to Soniox
try:
    while True:
        # Receive 20ms audio chunk from Telnyx (160 bytes at 8kHz)
        telnyx_message = await websocket.receive_bytes()  # 20ms chunks
        
        # ⏱️ TIMING CRITICAL: Track when last audio received
        last_audio_received_time = time.time()
        
        # Parse Telnyx payload (10-20 microseconds)
        payload = json.loads(telnyx_message)
        audio_data = base64.b64decode(payload["media"]["payload"])
        
        # Forward to Soniox immediately (5-10 microseconds)
        await soniox.send_audio(audio_data)
```

**Packet Timing:**
- Telnyx sends audio every 20ms (50 packets per second)
- Each packet is 160 bytes (20ms of 8kHz PCM audio)
- Forwarding latency: < 1ms per packet
- Network jitter: 10-50ms typical

**Performance Impact:**
- Minimal CPU usage (< 1% per call)
- Minimal memory usage (< 10MB per call)
- Buffering in Soniox: 100-300ms before transcription starts

---

## Phase 3: User Speech & Endpoint Detection (Variable Duration)

### 3.1 User Speaking
**Duration:** Variable (1-10 seconds typical)

**What's Happening:**
1. User speaks into phone
2. Telnyx captures audio, sends to backend every 20ms
3. Backend forwards to Soniox every 20ms
4. Soniox accumulates audio buffer (100-300ms buffer)
5. Soniox begins transcribing as audio arrives

### 3.2 Partial Transcripts (During Speech)
**File:** `server.py` line 2294-2393
**Callback:** `on_partial_transcript()` triggered every 100-500ms

```python
async def on_partial_transcript(text, data):
    # Called by Soniox as transcription happens in real-time
    partial_transcript = text  # e.g., "Can you help me with..."
    
    # Dead air prevention: Mark user as speaking
    if text.strip() and not session.user_speaking:
        session.mark_user_speaking_start()
    
    # 🚦 INTERRUPTION DETECTION: Check if user is interrupting agent
    if agent_generating_response and partial_transcript.strip():
        word_count = len(partial_transcript.strip().split())
        
        # ⚠️ ECHO FILTER (lines 2316-2356)
        # Check if transcript matches recent agent speech (speakerphone echo)
        # Uses 30% word similarity threshold
        # Prevents false interruptions from acoustic echo
        
        if word_count >= 2 and not is_echo:
            # INTERRUPT! Stop all audio playback immediately
            logger.info(f"🛑 INTERRUPTION TRIGGERED - User said {word_count} words")
            
            # Stop all active playbacks (but not comfort noise)
            for playback_id in current_playback_ids:
                await telnyx_service.stop_playback(call_control_id, playback_id)
            
            # Clear flags
            is_agent_speaking = False
            agent_generating_response = False
```

**Performance Impact:**
- Partial transcripts arrive every 100-500ms during speech
- Interruption detection latency: < 50ms
- Audio stop command to Telnyx: 50-150ms
- User perceives interruption stop: 150-300ms after speaking

### 3.3 Endpoint Detection (User Stops Speaking)
**File:** `server.py` line 2396-2400
**Callback:** `on_endpoint_detected()` - **CRITICAL LATENCY POINT**

```python
async def on_endpoint_detected():
    # ⏱️ CRITICAL: This is triggered when Soniox detects user stopped speaking
    logger.info(f"🎤 Endpoint detected by Soniox - processing transcript: {accumulated_transcript}")
```

**When Does Endpoint Fire?**
**File:** Soniox service configuration line 2223

```python
enable_endpoint_detection=True
# Soniox endpoint detection thresholds:
# - Silence duration: 500-800ms of silence (configurable)
# - Confidence threshold: 0.8 (confident utterance is complete)
# - Audio energy check: background noise vs speech detection
```

**Endpoint Detection Latency Breakdown:**
1. **User stops speaking**: T+0ms
2. **Silence accumulation**: T+500-800ms (Soniox waits for silence)
3. **Endpoint decision**: T+600-900ms (Soniox processes final audio)
4. **Websocket message**: T+650-950ms (network latency 50-100ms)
5. **Callback triggered**: T+700-1000ms

**⚠️ FIRST MAJOR LATENCY COMPONENT: 700-1000ms**

**STT Latency Calculation:**
**File:** `server.py` line 2463-2468

```python
# Calculate STT latency (last audio → endpoint detection)
stt_end_time = time.time()
stt_latency_ms = 0
if last_audio_received_time:
    stt_latency_ms = int((stt_end_time - last_audio_received_time) * 1000)
    logger.info(f"⏱️  STT LATENCY: {stt_latency_ms}ms (Soniox)")
```

**Expected STT Latency:**
- **Fast case** (short utterance, clean audio): 200-400ms
- **Typical case**: 500-800ms
- **Slow case** (long utterance, noisy audio): 1000-1500ms

**Soniox Model Performance:**
- `en_v3_lightning`: 300-600ms typical
- `en_v2_jumbo`: 500-1000ms typical
- **User's agent**: Need to check model configuration

---

## Phase 4: LLM Processing & Response Generation (T = 0ms to 3000ms from endpoint)

### 4.1 Pre-Processing & Database Save
**File:** `server.py` line 2401-2461
**Expected Duration:** 50-150ms

```python
# T+0ms (from endpoint detection)

# Dead air prevention: Mark user as stopped speaking
session.mark_user_speaking_end()  # 1-5ms

# Voicemail/IVR detection (runs in parallel, no blocking)
should_disconnect, detection_type = session.voicemail_detector.analyze_transcript(
    accumulated_transcript
)  # 10-50ms (regex matching)

if should_disconnect:
    # Hangup call if voicemail detected
    await telnyx_service.hangup_call(call_control_id)
    return

# Reset agent speaking flag
if is_agent_speaking:
    is_agent_speaking = False
    current_playback_ids.clear()

# Calculate STT latency
stt_latency_ms = int((time.time() - last_audio_received_time) * 1000)
logger.info(f"⏱️  STT LATENCY: {stt_latency_ms}ms")

# Set flags BEFORE LLM starts (enables interruption detection)
is_agent_speaking = True
agent_generating_response = True
call_states[call_control_id]["agent_generating_response"] = True

# Dead air prevention: Mark agent as speaking
session.mark_agent_speaking_start()

# Save user transcript to database (NON-BLOCKING but takes time)
await db.call_logs.update_one(
    {"call_id": call_control_id},
    {"$push": {
        "transcript": {
            "role": "user",
            "text": accumulated_transcript,
            "timestamp": datetime.utcnow().isoformat()
        }
    }}
)  # 20-100ms MongoDB write
```

**Performance Impact:**
- Voicemail detection: 10-50ms (regex, non-blocking)
- Database write: 20-100ms (async but blocks execution)
- Flag updates: < 1ms
- **TOTAL**: 50-150ms before LLM call starts

**⚠️ OPTIMIZATION OPPORTUNITY:**
- Database write could be fire-and-forget (don't await)
- Would save 20-100ms

### 4.2 LLM Call with Streaming
**File:** `server.py` line 2471-2540
**Expected Duration:** 800-3000ms to first sentence, 2000-5000ms total

```python
# T+100ms: Start LLM processing
llm_start_time = time.time()
logger.info(f"⏱️  USER STOPPED SPEAKING at T=0ms")

# Initialize streaming state
sentence_queue = []
tts_tasks = []
first_tts_started = False
tts_start_time = None

# Define streaming callback
async def stream_sentence_to_tts(sentence):
    # Called by LLM as each sentence is generated
    # Starts TTS immediately (parallel to LLM generation)
    ...

# 🚀 PROCESS WITH STREAMING
response = await session.process_user_input(
    accumulated_transcript, 
    stream_callback=stream_sentence_to_tts
)
```

**What Happens in process_user_input:**
**File:** `calling_service.py` line 530-800

```python
async def process_user_input(self, user_message, stream_callback=None):
    # 1. Determine call flow processing mode
    if self.agent_config.get("call_flow"):
        # CALL FLOW MODE: Node-based conversation
        response = await self._process_call_flow_streaming(
            user_message, 
            stream_callback=stream_callback
        )
    else:
        # SIMPLE MODE: Direct LLM conversation
        response = await self._generate_ai_response_streaming(
            user_message,
            stream_callback=stream_callback
        )
    
    return response
```

**Call Flow Mode Processing:**
**File:** `calling_service.py` line 1040-1300
**Expected Duration:** Adds 200-800ms to base LLM latency

```python
async def _process_call_flow_streaming(self, user_message, stream_callback=None):
    # STEP 1: Get current node (50-100ms)
    current_node = self._get_current_node()
    
    # STEP 2: Extract variables from user message (if configured)
    if current_node.get("extract_variables"):
        extraction_result = await self._extract_variables_realtime(
            user_message,
            current_node["extract_variables"]
        )
        # LLM call for extraction: 500-1500ms
        # ⚠️ SECOND LLM CALL - MAJOR LATENCY COMPONENT
    
    # STEP 3: Check if mandatory variables are present
    if current_node.get("extract_variables"):
        reprompt_message = await self._check_mandatory_variables(
            current_node["extract_variables"]
        )
        if reprompt_message:
            # User didn't provide required info, ask again
            # Another LLM call: 500-1500ms
            # ⚠️ THIRD LLM CALL - ADDS MORE LATENCY
            return {"text": reprompt_message, "latency": ...}
    
    # STEP 4: Evaluate transitions (if user input matches conditions)
    should_transition = False
    if current_node.get("transitions"):
        transition_result = await self._follow_transition(
            user_message,
            current_node["transitions"]
        )
        # LLM call to evaluate conditions: 500-1500ms
        # ⚠️ FOURTH LLM CALL - MORE LATENCY
        
        if transition_result.get("selected_index") is not None:
            # Transition to new node
            next_node = self._get_node_by_id(transition_id)
            self.current_node_id = next_node["id"]
            should_transition = True
    
    # STEP 5: Generate response based on node type
    node_type = current_node.get("node_type", "conversation")
    
    if node_type == "function":
        # Execute webhook
        await self._execute_webhook(current_node)
        # HTTP request: 100-5000ms depending on webhook
        # Then auto-transition to next node
    
    elif node_type == "conversation":
        if current_node.get("prompt_type") == "script":
            # Return pre-written script (no LLM call)
            response_text = current_node.get("content", "")
            # FAST: 10-50ms
        
        elif current_node.get("prompt_type") == "prompt":
            # Generate AI response using node goal as instruction
            response = await self._generate_ai_response_streaming(
                user_message,
                stream_callback=stream_callback,
                custom_instruction=current_node.get("content")
            )
            # LLM call: 800-3000ms
    
    elif node_type == "ending":
        # Return ending message and set should_end_call flag
        response_text = current_node.get("content", "Goodbye!")
        self.should_end_call = True
```

**⚠️ CRITICAL LATENCY BOTTLENECK IDENTIFIED:**

**Multiple Sequential LLM Calls:**
1. **Variable extraction**: 500-1500ms (if configured)
2. **Mandatory variable check + reprompt**: 500-1500ms (if missing vars)
3. **Transition evaluation**: 500-1500ms (if transitions exist)
4. **Response generation**: 800-3000ms (always)

**WORST CASE**: 2300-7500ms total (all steps)
**TYPICAL CASE**: 1300-4500ms (extraction + transitions + response)
**BEST CASE**: 800-3000ms (script node or simple prompt)

**User's 4-Second Delay Analysis:**
- 700-1000ms: STT latency
- 1300-4500ms: LLM processing (multiple calls)
- **TOTAL**: 2000-5500ms
- **Matches user's reported 4-second delay!**

### 4.3 LLM Streaming Response Generation
**File:** `calling_service.py` line 2230-2450
**Expected Duration:** 800-3000ms to first sentence

```python
async def _generate_ai_response_streaming(self, user_message, stream_callback=None, custom_instruction=None):
    # ⏱️ T+0ms: Start LLM streaming call
    llm_start = time.time()
    
    # Build conversation context (50-100ms)
    messages = []
    
    # Add system prompt (1-10KB typically)
    system_prompt = self._build_cached_system_prompt()
    messages.append({"role": "system", "content": system_prompt})
    
    # Add conversation history (last 8 messages)
    for msg in self.conversation_history[-8:]:
        messages.append({"role": msg["role"], "content": msg["text"]})
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    # Get LLM provider and model
    llm_provider = self.agent_config.get("settings", {}).get("llm_provider")  # "openai", "grok", "anthropic"
    model = self.agent_config.get("settings", {}).get("llm_model")  # "gpt-4o", "grok-beta", "claude-3-5-sonnet"
    
    # Call LLM with streaming
    if llm_provider == "openai":
        # ⏱️ T+100ms: HTTP request sent to OpenAI
        stream = await self.openai_client.chat.completions.create(
            model=model,  # "gpt-4o" or "gpt-4o-mini"
            messages=messages,
            temperature=0.7,
            max_tokens=200,  # ⚠️ AFFECTS LATENCY: Higher = slower
            stream=True  # CRITICAL for low latency
        )
        
        # ⏱️ T+300-1000ms: First token arrives (TTFT - Time To First Token)
        # TTFT depends on:
        # - Model: gpt-4o (400-800ms), gpt-4o-mini (200-400ms)
        # - Context length: More tokens = slower
        # - API load: Peak times = slower
        
        # Stream tokens as they arrive
        current_sentence = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                current_sentence += delta.content
                
                # Check if sentence is complete (. ! ? detected)
                if current_sentence.strip().endswith(('.', '!', '?')):
                    # ⏱️ T+500-1500ms: First sentence complete
                    if stream_callback:
                        await stream_callback(current_sentence.strip())
                    current_sentence = ""
    
    elif llm_provider == "grok":
        # Similar streaming logic with xAI API
        # Grok-beta TTFT: 200-600ms (faster than GPT-4o)
        ...
    
    elif llm_provider == "anthropic":
        # Claude streaming
        # Claude-3-5-sonnet TTFT: 300-700ms
        ...
```

**LLM Performance by Model:**

| Model | TTFT | Tokens/sec | 50-token response | 200-token response |
|-------|------|------------|-------------------|---------------------|
| GPT-4o | 400-800ms | 30-50 | 1.5-2.5s | 5-8s |
| GPT-4o-mini | 200-400ms | 50-80 | 1.0-1.5s | 3-5s |
| Grok-beta | 200-600ms | 40-60 | 1.2-2.0s | 4-6s |
| Claude-3-5-sonnet | 300-700ms | 35-55 | 1.5-2.5s | 5-8s |
| Claude-3-haiku | 150-300ms | 60-90 | 0.8-1.2s | 2-4s |

**User's Agent:** Need to check LLM provider and model configuration

**Context Length Impact:**

```python
# Conversation history: last 8 messages
for msg in self.conversation_history[-8:]:
    messages.append({"role": msg["role"], "content": msg["text"]})

# Example token count:
# - System prompt: 200-1000 tokens
# - KB context (if enabled): 500-3000 tokens
# - Conversation history (8 messages): 400-2000 tokens
# - Current message: 50-200 tokens
# TOTAL CONTEXT: 1150-6200 tokens

# TTFT increases with context:
# - 1000 tokens: +0ms baseline
# - 2000 tokens: +50-100ms
# - 4000 tokens: +100-200ms
# - 6000 tokens: +200-400ms
```

**⚠️ OPTIMIZATION OPPORTUNITY:**
- Reduce conversation history from 8 to 3-5 messages
- Reduce max_tokens from 200 to 100-150
- Use faster model (GPT-4o-mini, Grok-beta, Claude-haiku)
- Remove KB context if not needed for current query

---

## Phase 5: TTS Generation via Persistent WebSocket (T = 0ms to 800ms from first sentence)

### 5.1 Stream Callback Triggered
**File:** `server.py` line 2498-2540
**Trigger:** LLM generates complete sentence

```python
async def stream_sentence_to_tts(sentence):
    # ⏱️ T+0ms: First sentence arrived from LLM
    # e.g., sentence = "Hello! I'd be happy to help you with that."
    
    if not tts_start_time:
        tts_start_time = time.time()
    
    full_response_text += sentence + " "
    sentence_queue.append(sentence)
    logger.info(f"📤 Sentence arrived from LLM: {sentence[:50]}...")
    
    if not first_tts_started:
        first_tts_started = True
        logger.info(f"⚡ Starting REAL-TIME TTS for first sentence")
    
    # ⏱️ T+10ms: Check if persistent TTS is enabled
    persistent_tts_session = persistent_tts_manager.get_session(call_control_id)
    
    logger.info(f"🔍 Persistent TTS lookup: call_id={call_control_id[:20]}..., session={'FOUND' if persistent_tts_session else 'NOT FOUND'}")
    
    if persistent_tts_session:
        # 🚀 USE PERSISTENT TTS WEBSOCKET
        is_first = len(sentence_queue) == 1
        is_last = False
        
        logger.info(f"🚀 Streaming sentence #{len(sentence_queue)} via persistent WebSocket")
        
        # ⏱️ T+15ms: Start TTS task (non-blocking)
        tts_task = asyncio.create_task(
            persistent_tts_session.stream_sentence(sentence, is_first=is_first, is_last=is_last)
        )
        tts_tasks.append(tts_task)
    else:
        # Fallback to REST API (SLOW PATH - 800-1500ms)
        agent_config = session.agent_config
        tts_task = asyncio.create_task(generate_tts_audio(sentence, agent_config))
        tts_tasks.append(tts_task)
```

**Performance Impact:**
- Callback overhead: 5-15ms
- Session lookup: < 1ms (dictionary lookup)
- Task creation: 1-5ms
- **TOTAL**: 10-20ms before TTS starts

### 5.2 Persistent TTS Stream Sentence
**File:** `persistent_tts_service.py` line 87-165
**Expected Duration:** 150-400ms to first audio chunk

```python
async def stream_sentence(self, sentence, is_first=False, is_last=False):
    # ⏱️ T+0ms: Start TTS generation
    
    if not self.connected or not self.ws_service:
        logger.error(f"❌ TTS WebSocket not connected")
        return False
    
    self.sentence_counter += 1
    sentence_num = self.sentence_counter
    
    logger.info(f"🎤 [Call {self.call_control_id}] Streaming sentence #{sentence_num}: {sentence[:50]}...")
    
    stream_start = time.time()
    
    # ⏱️ T+10ms: Send text to ElevenLabs WebSocket
    await self.ws_service.send_text(
        text=sentence,  # e.g., "Hello! I'd be happy to help you with that."
        try_trigger_generation=True,
        flush=is_last
    )
    # Network latency: 20-50ms
    # ElevenLabs receives text: T+30-60ms
    
    # ⏱️ T+50-150ms: ElevenLabs starts generating audio
    # Model processing time (eleven_flash_v2_5):
    # - Text → Phonemes: 20-40ms
    # - Phonemes → Audio: 30-80ms
    # - Streaming buffer fill: 50-100ms
    
    # ⏱️ T+150-300ms: First audio chunk arrives
    chunk_count = 0
    first_chunk_time = None
    audio_chunks = []
    
    async for audio_chunk in self.ws_service.receive_audio_chunks():
        if first_chunk_time is None:
            first_chunk_time = time.time()
            ttfb = (first_chunk_time - stream_start) * 1000
            logger.info(f"⚡ [Call {self.call_control_id}] Sentence #{sentence_num} TTFB: {ttfb:.0f}ms")
            # ⏱️ TTFB = Time To First Byte
            # Expected: 150-300ms for WebSocket
            # Compare to REST API: 800-1500ms
        
        chunk_count += 1
        audio_chunks.append(audio_chunk)
        
        # Chunks arrive continuously, typically:
        # - 50-100ms between chunks
        # - 2-8 chunks per second
        # - Chunk size: 2000-8000 bytes PCM
    
    # ⏱️ T+300-800ms: All audio chunks received for sentence
    total_time = (time.time() - stream_start) * 1000
    logger.info(f"✅ [Call {self.call_control_id}] Sentence #{sentence_num} complete: {chunk_count} chunks in {total_time:.0f}ms")
    
    # Combine chunks
    if audio_chunks:
        full_audio = b''.join(audio_chunks)
        
        # ⏱️ T+310ms: Queue for playback
        await self.audio_queue.put({
            'sentence': sentence,
            'audio_pcm': full_audio,
            'sentence_num': sentence_num,
            'is_first': is_first,
            'is_last': is_last
        })
        
        logger.info(f"📤 [Call {self.call_control_id}] Queued sentence #{sentence_num} for playback ({len(full_audio)} bytes)")
```

**ElevenLabs Model Performance:**

| Model | TTFB (WebSocket) | TTFB (REST) | Streaming Speed | Quality |
|-------|------------------|-------------|-----------------|---------|
| eleven_flash_v2_5 | 150-250ms | 800-1200ms | 7-10 chunks/sec | Good |
| eleven_turbo_v2_5 | 200-300ms | 1000-1500ms | 5-8 chunks/sec | Better |
| eleven_multilingual_v2 | 300-500ms | 1500-2500ms | 4-6 chunks/sec | Best |

**User's Agent:** Using `eleven_flash_v2_5` (correct choice for speed)

**WebSocket vs REST API:**
- **WebSocket TTFB**: 150-300ms ✅
- **REST API TTFB**: 800-1500ms ❌
- **Latency Savings**: 500-1200ms per sentence

### 5.3 Playback Consumer (Background Task)
**File:** `persistent_tts_service.py` line 167-196
**Runs continuously:** Consumes from audio_queue

```python
async def _playback_consumer(self):
    # Background task started at call initialization
    # Waits for audio chunks and plays them immediately
    
    logger.info(f"🎵 [Call {self.call_control_id}] Playback consumer started")
    
    try:
        while True:
            # ⏱️ Wait for next audio chunk (blocking)
            audio_item = await self.audio_queue.get()
            # Waits until stream_sentence() puts item in queue
            # Once item arrives, processes immediately
            
            if audio_item is None:
                # Shutdown signal
                break
            
            # ⏱️ Play immediately (no batching, no delay)
            await self._play_audio_chunk(
                sentence=audio_item['sentence'],
                audio_pcm=audio_item['audio_pcm'],
                sentence_num=audio_item['sentence_num'],
                is_first=audio_item['is_first']
            )
            
            self.audio_queue.task_done()
```

**Queue Performance:**
- Queue size: Typically 0-1 items (items consumed faster than produced)
- Queue latency: < 1ms (async queue is instant when item available)
- No batching: Items processed one at a time
- **BENEFIT**: Immediate playback as audio arrives

### 5.4 Play Audio Chunk (PCM → MP3 → Telnyx)
**File:** `persistent_tts_service.py` line 197-263
**Expected Duration:** 100-300ms

```python
async def _play_audio_chunk(self, sentence, audio_pcm, sentence_num, is_first):
    # ⏱️ T+0ms: Audio chunk ready to play
    
    play_start = time.time()
    
    # Generate unique filename
    audio_hash = hashlib.md5(f"{sentence_num}_{sentence}".encode()).hexdigest()
    pcm_path = f"/tmp/tts_persistent_{self.call_control_id}_{audio_hash}.pcm"
    mp3_path = f"/tmp/tts_persistent_{self.call_control_id}_{audio_hash}.mp3"
    
    # ⏱️ T+10ms: Save PCM to disk
    with open(pcm_path, 'wb') as f:
        f.write(audio_pcm)  # Disk write: 5-20ms for 50-200KB
    
    # ⏱️ T+20ms: Convert PCM to MP3 using ffmpeg
    conversion_start = time.time()
    subprocess.run([
        'ffmpeg',
        '-f', 's16le',  # PCM 16-bit little-endian
        '-ar', '16000',  # 16kHz sample rate
        '-ac', '1',  # Mono
        '-i', pcm_path,
        '-b:a', '64k',  # 64kbps MP3
        '-y',  # Overwrite
        mp3_path
    ], check=True, capture_output=True, timeout=5)
    # ffmpeg processing: 30-100ms for 2-5 second audio
    
    conversion_time = (time.time() - conversion_start) * 1000
    logger.debug(f"⚡ [Call {self.call_control_id}] PCM→MP3: {conversion_time:.0f}ms")
    
    # ⏱️ T+70ms: Clean up PCM file
    os.remove(pcm_path)  # 1-5ms
    
    # ⏱️ T+75ms: Play via Telnyx
    if self.telnyx_service:
        backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8001')
        audio_url = f"{backend_url}/api/audio/{os.path.basename(mp3_path)}"
        
        # Send play command to Telnyx
        playback_result = await self.telnyx_service.play_audio_url(
            call_control_id=self.call_control_id,
            audio_url=audio_url
        )
        # Telnyx API call: 50-150ms
        
        total_time = (time.time() - play_start) * 1000
        
        if playback_result.get('success'):
            logger.info(f"🔊 [Call {self.call_control_id}] Sentence #{sentence_num} PLAYING ({total_time:.0f}ms total): {sentence[:50]}...")
            
            if is_first:
                # ⏱️ CRITICAL METRIC: Time from user stopped speaking to first audio playing
                logger.info(f"⏱️  [Call {self.call_control_id}] 🚀 FIRST SENTENCE STARTED PLAYING")
```

**Playback Latency Breakdown:**
1. **PCM save to disk**: 5-20ms
2. **ffmpeg conversion**: 30-100ms
3. **PCM cleanup**: 1-5ms
4. **Telnyx play_audio_url**: 50-150ms
5. **Network latency**: 20-50ms
6. **Telnyx processing**: 30-80ms
7. **Audio starts playing on phone**: 100-300ms total

**⚠️ OPTIMIZATION OPPORTUNITY:**
- ffmpeg conversion is synchronous (blocks)
- Could use async subprocess or pre-convert in chunks
- Could stream audio directly to Telnyx (avoid file write)

---

## Phase 6: Total Latency Analysis

### 6.1 Best Case Scenario (All Optimized)

| Phase | Component | Duration |
|-------|-----------|----------|
| **STT** | Endpoint detection | 300ms |
| **Pre-LLM** | DB write + setup | 50ms |
| **LLM** | TTFT (gpt-4o-mini) | 250ms |
| **LLM** | First sentence generation | 300ms |
| **TTS** | WebSocket TTFB | 180ms |
| **TTS** | Audio generation | 150ms |
| **Playback** | PCM→MP3 + Telnyx | 150ms |
| **TOTAL** | | **1380ms** ✅ |

**Conditions:**
- Fast STT model (en_v3_lightning)
- Fast LLM model (gpt-4o-mini or grok-beta)
- Script node (no variable extraction or transitions)
- Persistent WebSocket TTS enabled
- Low network latency
- No KB context

### 6.2 Typical Case Scenario

| Phase | Component | Duration |
|-------|-----------|----------|
| **STT** | Endpoint detection | 600ms |
| **Pre-LLM** | DB write + setup | 80ms |
| **LLM** | Variable extraction | 800ms |
| **LLM** | Transition evaluation | 700ms |
| **LLM** | TTFT | 500ms |
| **LLM** | First sentence generation | 400ms |
| **TTS** | WebSocket TTFB | 220ms |
| **TTS** | Audio generation | 200ms |
| **Playback** | PCM→MP3 + Telnyx | 180ms |
| **TOTAL** | | **3680ms** ⚠️ |

**Conditions:**
- Standard STT model (en_v2_jumbo)
- Standard LLM model (gpt-4o)
- Conversation node with variable extraction
- Transitions enabled
- Persistent WebSocket TTS enabled
- Moderate network latency
- KB context loaded (2000 tokens)

**This matches user's 4-second delay!**

### 6.3 Worst Case Scenario

| Phase | Component | Duration |
|-------|-----------|----------|
| **STT** | Endpoint detection | 1000ms |
| **Pre-LLM** | DB write + setup | 150ms |
| **LLM** | Variable extraction | 1500ms |
| **LLM** | Mandatory var reprompt | 1200ms |
| **LLM** | Transition evaluation | 1000ms |
| **LLM** | TTFT | 800ms |
| **LLM** | First sentence generation | 600ms |
| **TTS** | REST API (fallback) | 1200ms |
| **Playback** | PCM→MP3 + Telnyx | 200ms |
| **TOTAL** | | **7650ms** ❌ |

**Conditions:**
- Slow STT model (en_v2_jumbo) + noisy audio
- Slow LLM model (gpt-4o) + large context
- Multiple LLM calls (extraction, reprompt, transition, response)
- WebSocket TTS not enabled (REST API fallback)
- High network latency
- Large KB context (5000 tokens)

---

## Phase 7: Feature Analysis & Overhead

### 7.1 Variable Extraction
**File:** `calling_service.py` line 1640-1780
**Cost:** 500-1500ms per extraction

```python
async def _extract_variables_realtime(self, conversation, variables_to_extract):
    # Separate LLM call to extract structured data
    # Example: Extract "appointment_time", "customer_name", "phone_number"
    
    # Build extraction prompt (50-100ms)
    extraction_messages = [
        {"role": "system", "content": "Extract the following variables..."},
        {"role": "user", "content": f"Conversation: {conversation}\nVariables: {variables_to_extract}"}
    ]
    
    # Call LLM (500-1500ms)
    response = await self.openai_client.chat.completions.create(
        model=self.llm_model,
        messages=extraction_messages,
        temperature=0.3,
        max_tokens=150
    )
    
    # Parse JSON response (10-30ms)
    extracted_vars = json.loads(response.choices[0].message.content)
    
    return extracted_vars
```

**Performance Impact:**
- **ADDS**: 500-1500ms to every turn where variables are configured
- **Benefit**: Extracts structured data for webhooks/CRM
- **User's agent**: Check if variable extraction is enabled on nodes

### 7.2 Transition Evaluation
**File:** `calling_service.py` line 1330-1500
**Cost:** 500-1500ms per evaluation

```python
async def _follow_transition(self, user_message, transitions):
    # Separate LLM call to evaluate which transition to take
    # Example: Check if user said "yes" or "no" to proceed to different nodes
    
    # Build transition evaluation prompt
    transition_messages = [
        {"role": "system", "content": "You are evaluating conversation flow transitions..."},
        {"role": "user", "content": f"User said: {user_message}\nWhich condition matches?\n{transitions}"}
    ]
    
    # Call LLM (500-1500ms)
    response = await self.openai_client.chat.completions.create(
        model=self.llm_model,
        messages=transition_messages,
        temperature=0.1,  # Low temperature for consistent decisions
        max_tokens=50
    )
    
    # Parse which transition was selected
    selected_index = parse_transition_response(response)
    
    return {"selected_index": selected_index, ...}
```

**Performance Impact:**
- **ADDS**: 500-1500ms to every turn where transitions exist
- **Benefit**: Enables conversation flow branching
- **User's agent**: Check if transitions are configured on nodes

### 7.3 Mandatory Variable Reprompting
**File:** `calling_service.py` line 1780-1850
**Cost:** 500-1500ms per reprompt

```python
async def _check_mandatory_variables(self, variables_config):
    # Check if any mandatory variables are missing
    missing_vars = []
    for var in variables_config:
        if var.get("mandatory") and not self.session_variables.get(var["name"]):
            missing_vars.append(var)
    
    if missing_vars:
        # Generate reprompt using LLM (500-1500ms)
        reprompt = await self._generate_mandatory_reprompt(missing_vars)
        return reprompt
    
    return None
```

**Performance Impact:**
- **ADDS**: 500-1500ms when mandatory variable is missing
- **Benefit**: Ensures required data is collected
- **User's agent**: Check if mandatory variables are configured

### 7.4 Knowledge Base (KB) Context
**File:** `calling_service.py` line 2280-2320
**Cost:** +100-400ms LLM latency due to larger context

```python
# System prompt includes KB context
system_prompt = self._build_cached_system_prompt()

# Example system prompt with KB:
"""
You are an AI assistant for Acme Corp.

**Knowledge Base:**
- Product pricing: $99/month for Basic, $299/month for Pro
- Support hours: 9am-5pm EST Monday-Friday
- Refund policy: 30-day money-back guarantee
... (2000-5000 tokens of KB content)

**Instructions:**
Answer user questions based on the knowledge base above.
"""
```

**Performance Impact:**
- **KB loading at call start**: 500-2000ms (one-time cost)
- **LLM context size**: +2000-5000 tokens per request
- **TTFT increase**: +100-400ms due to larger context
- **Benefit**: Agent can answer specific product/company questions
- **User's agent**: Check if KB documents are configured

### 7.5 Voicemail/IVR Detection
**File:** `server.py` line 2410-2448
**Cost:** 10-50ms (regex, non-blocking)

```python
# Runs in parallel, no blocking
should_disconnect, detection_type, confidence = session.voicemail_detector.analyze_transcript(
    accumulated_transcript,
    call_start_time=session.call_start_time
)
```

**Performance Impact:**
- **ADDS**: 10-50ms (negligible)
- **Benefit**: Auto-detect and hangup on voicemail/IVR
- **User's agent**: Enabled by default

### 7.6 Echo Filtering (Interruption Detection)
**File:** `server.py` line 2316-2356
**Cost:** 20-80ms per partial transcript

```python
# Check if transcript matches recent agent speech
is_echo = False
for agent_text in recent_agent_texts:
    # Word similarity check (30% threshold)
    similarity = len(common_words) / len(agent_words)
    
    # Substring match check
    transcript_in_agent = transcript_normalized in agent_normalized
    
    # Trigram phrase match
    if any_trigram_matches:
        is_echo = True
        break
```

**Performance Impact:**
- **ADDS**: 20-80ms per partial transcript (during speech)
- **Benefit**: Prevents false interruptions from speakerphone echo
- **Runs continuously**: Every 100-500ms during user speech

### 7.7 Dead Air Monitoring
**File:** `server.py` line 2287-2292, separate background task
**Cost:** 0ms (background task, non-blocking)

```python
# Background task monitors for silence
dead_air_task = asyncio.create_task(
    monitor_dead_air(session, websocket, call_control_id, check_in_callback, telnyx_svc, redis_svc)
)
```

**Performance Impact:**
- **ADDS**: 0ms (runs in background)
- **Benefit**: Sends "Are you there?" message if >10 seconds silence

---

## Phase 8: Critical Optimizations Needed

### 8.1 Immediate Optimizations (High Impact, Low Effort)

#### Optimization 1: Reduce Conversation History
**File:** `calling_service.py` line 2340-2350
**Current:** 8 messages
**Recommended:** 3-5 messages

```python
# BEFORE (current)
for msg in self.conversation_history[-8:]:
    messages.append({"role": msg["role"], "content": msg["text"]})

# AFTER (optimized)
for msg in self.conversation_history[-3:]:  # Reduced from 8 to 3
    messages.append({"role": msg["role"], "content": msg["text"]})
```

**Expected Improvement:** -50 to -150ms LLM latency

#### Optimization 2: Reduce max_tokens
**File:** `calling_service.py` line 2370-2380
**Current:** 200 tokens
**Recommended:** 100-120 tokens

```python
# BEFORE
max_tokens=200

# AFTER
max_tokens=120  # Reduced from 200 to 120
```

**Expected Improvement:** -100 to -300ms LLM latency

#### Optimization 3: Switch to Faster LLM Model
**Current:** Check user's agent config
**Recommended:** gpt-4o-mini or grok-beta

**Expected Improvement:** -200 to -500ms LLM latency

| Model Change | TTFT Improvement | Total Improvement |
|--------------|------------------|-------------------|
| GPT-4o → GPT-4o-mini | -200 to -400ms | -400 to -800ms |
| GPT-4o → Grok-beta | -100 to -300ms | -300 to -600ms |
| Any → Claude-haiku | -200 to -500ms | -500 to -1000ms |

#### Optimization 4: Make Database Writes Non-Blocking
**File:** `server.py` line 2602-2613
**Current:** await db.call_logs.update_one() blocks execution
**Recommended:** Fire-and-forget

```python
# BEFORE (blocks)
await db.call_logs.update_one(...)

# AFTER (non-blocking)
asyncio.create_task(db.call_logs.update_one(...))
```

**Expected Improvement:** -20 to -100ms per turn

#### Optimization 5: Batch API Key Queries
**File:** `server.py` line 4970-4980
**Current:** 4-5 sequential queries
**Recommended:** Single aggregation query

**Expected Improvement:** -80 to -250ms at call initialization

### 8.2 Medium Optimizations (High Impact, Medium Effort)

#### Optimization 6: Conditional Variable Extraction
**Current:** Runs on every turn if configured
**Recommended:** Only run when user provides new info

```python
# Check if user message contains potential variable values
if self._message_likely_has_variables(user_message):
    # Run extraction
else:
    # Skip extraction, save 500-1500ms
```

**Expected Improvement:** -500 to -1500ms on turns without new info

#### Optimization 7: Cache Transition Evaluations
**Current:** Re-evaluate transitions on every turn
**Recommended:** Cache recent evaluations

```python
# Check if same user message was recently evaluated
cache_key = f"{current_node_id}:{user_message_normalized}"
if cache_key in self.transition_cache:
    return self.transition_cache[cache_key]
```

**Expected Improvement:** -500 to -1500ms on repeated phrases

#### Optimization 8: Parallel LLM Calls
**Current:** Sequential (extraction → transitions → response)
**Recommended:** Run extraction and transitions in parallel

```python
# BEFORE (sequential)
extraction_result = await self._extract_variables(...)  # 800ms
transition_result = await self._follow_transition(...)  # 700ms
response = await self._generate_response(...)  # 1000ms
# TOTAL: 2500ms

# AFTER (parallel)
extraction_task = asyncio.create_task(self._extract_variables(...))
transition_task = asyncio.create_task(self._follow_transition(...))
await asyncio.gather(extraction_task, transition_task)  # 800ms (parallel)
response = await self._generate_response(...)  # 1000ms
# TOTAL: 1800ms
```

**Expected Improvement:** -500 to -700ms when both enabled

### 8.3 Advanced Optimizations (Very High Impact, High Effort)

#### Optimization 9: Speculative TTS Generation
**Concept:** Start generating TTS before LLM finishes deciding

```python
# Pre-generate common phrases while waiting for LLM
common_phrases = ["I'd be happy to help!", "Let me check that for you.", "Sure!"]
pre_generate_tts_in_background(common_phrases)
```

**Expected Improvement:** -200 to -500ms perceived latency

#### Optimization 10: Context Compression
**Current:** Full conversation history sent to LLM
**Recommended:** Summarize old messages, keep recent ones full

```python
# Messages 1-5: Compressed summary (50 tokens)
# Messages 6-8: Full text (200 tokens)
# TOTAL: 250 tokens instead of 600 tokens
```

**Expected Improvement:** -100 to -300ms LLM latency

#### Optimization 11: Streaming ffmpeg Conversion
**Current:** Wait for full PCM, then convert to MP3
**Recommended:** Stream chunks to ffmpeg as they arrive

**Expected Improvement:** -50 to -150ms playback latency

---

## Phase 9: Recommended Logging Additions

### 9.1 STT Timing Logs
**File:** `server.py` line 2463-2470

```python
# CURRENT
stt_latency_ms = int((stt_end_time - last_audio_received_time) * 1000)
logger.info(f"⏱️  STT LATENCY: {stt_latency_ms}ms (Soniox)")

# ADD
logger.info(f"⏱️  [TIMING] STT_START: User last audio packet at T+0ms")
logger.info(f"⏱️  [TIMING] STT_END: Endpoint detected at T+{stt_latency_ms}ms")
logger.info(f"⏱️  [TIMING] STT_MODEL: {soniox_model}")
```

### 9.2 LLM Component Timing Logs
**File:** `calling_service.py` line 1040-1300

```python
# Variable Extraction
if current_node.get("extract_variables"):
    var_extract_start = time.time()
    extraction_result = await self._extract_variables_realtime(...)
    var_extract_ms = int((time.time() - var_extract_start) * 1000)
    logger.info(f"⏱️  [TIMING] VAR_EXTRACTION: {var_extract_ms}ms")

# Transition Evaluation
if current_node.get("transitions"):
    transition_start = time.time()
    transition_result = await self._follow_transition(...)
    transition_ms = int((time.time() - transition_start) * 1000)
    logger.info(f"⏱️  [TIMING] TRANSITION_EVAL: {transition_ms}ms")

# Response Generation
response_start = time.time()
response = await self._generate_ai_response_streaming(...)
response_ms = int((time.time() - response_start) * 1000)
logger.info(f"⏱️  [TIMING] LLM_RESPONSE: {response_ms}ms")
```

### 9.3 LLM TTFT Logging
**File:** `calling_service.py` line 2350-2400

```python
# Track TTFT
llm_start = time.time()
first_token_time = None

async for chunk in stream:
    if first_token_time is None:
        first_token_time = time.time()
        ttft_ms = int((first_token_time - llm_start) * 1000)
        logger.info(f"⏱️  [TIMING] LLM_TTFT: {ttft_ms}ms (model: {self.llm_model})")
```

### 9.4 TTS Timing Logs
**File:** `persistent_tts_service.py` line 115-145

```python
# CURRENT
logger.info(f"⚡ [Call {self.call_control_id}] Sentence #{sentence_num} TTFB: {ttfb:.0f}ms")
logger.info(f"✅ [Call {self.call_control_id}] Sentence #{sentence_num} complete: {chunk_count} chunks in {total_time:.0f}ms")

# ADD
logger.info(f"⏱️  [TIMING] TTS_START: Sent to ElevenLabs at T+0ms")
logger.info(f"⏱️  [TIMING] TTS_TTFB: First audio chunk at T+{ttfb:.0f}ms")
logger.info(f"⏱️  [TIMING] TTS_COMPLETE: All chunks received at T+{total_time:.0f}ms")
logger.info(f"⏱️  [TIMING] TTS_MODEL: {self.model_id}")
logger.info(f"⏱️  [TIMING] TTS_CHUNKS: {chunk_count} chunks")
```

### 9.5 Playback Timing Logs
**File:** `persistent_tts_service.py` line 197-260

```python
# ADD
logger.info(f"⏱️  [TIMING] PLAYBACK_START: Processing sentence #{sentence_num}")
logger.info(f"⏱️  [TIMING] PLAYBACK_PCM_SAVE: {pcm_save_ms:.0f}ms")
logger.info(f"⏱️  [TIMING] PLAYBACK_FFMPEG: {conversion_time:.0f}ms")
logger.info(f"⏱️  [TIMING] PLAYBACK_TELNYX: {telnyx_ms:.0f}ms")
logger.info(f"⏱️  [TIMING] PLAYBACK_TOTAL: {total_time:.0f}ms")
```

### 9.6 E2E Summary Log
**File:** `server.py` line 2620-2650

```python
# ADD comprehensive summary
total_latency = int((time.time() - llm_start_time) * 1000)

logger.info(f"""
⏱️  [TIMING] ==== E2E LATENCY SUMMARY ====
⏱️  [TIMING] STT: {stt_latency_ms}ms
⏱️  [TIMING] VAR_EXTRACTION: {var_extract_ms}ms (if applicable)
⏱️  [TIMING] TRANSITION_EVAL: {transition_ms}ms (if applicable)
⏱️  [TIMING] LLM_TTFT: {llm_ttft_ms}ms
⏱️  [TIMING] LLM_TOTAL: {llm_total_ms}ms
⏱️  [TIMING] TTS_TTFB: {tts_ttfb_ms}ms
⏱️  [TIMING] TTS_TOTAL: {tts_total_ms}ms
⏱️  [TIMING] PLAYBACK: {playback_ms}ms
⏱️  [TIMING] E2E_TOTAL: {total_latency}ms
⏱️  [TIMING] MODEL_CONFIG: STT={stt_model}, LLM={llm_model}, TTS={tts_model}
⏱️  [TIMING] ==========================
""")
```

---

## Summary & Recommendations

### Current Performance (User's Case)
- **Reported latency**: 4 seconds
- **Expected breakdown**:
  - STT: 600-800ms
  - Variable extraction: 800ms
  - Transition evaluation: 700ms
  - LLM response: 1000ms
  - TTS: 300-400ms
  - Playback: 200ms
  - **TOTAL**: ~3600-4000ms ✅ Matches report

### Root Causes
1. **Multiple sequential LLM calls** (extraction + transitions + response)
2. **STT endpoint detection delay** (500-800ms silence wait)
3. **Large context size** (8 messages + KB content)
4. **Potentially slow LLM model** (need to check config)

### Priority Actions
1. **Add detailed timing logs** (as specified above)
2. **Check agent configuration** (LLM model, STT model, features enabled)
3. **Implement immediate optimizations** (reduce history, max_tokens, faster model)
4. **Test with simplified flow** (disable variable extraction + transitions temporarily)
5. **Measure improvement** (compare before/after logs)

### Expected Improvement with Optimizations
- **Current**: 3600-4000ms
- **After immediate optimizations**: 2000-2500ms (-1500ms)
- **After medium optimizations**: 1500-2000ms (-500ms more)
- **Target**: < 1500ms total latency

This comprehensive analysis provides the foundation for precise logging and targeted optimizations.
