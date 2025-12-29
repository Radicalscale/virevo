# Comprehensive AI Voice Agent Call Feature Documentation

**Last Updated:** December 29, 2025  
**Version:** 1.0  
**Purpose:** Complete technical reference for the AI Voice Agent call infrastructure

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Call Flow Node Types](#2-call-flow-node-types)
3. [Agent Settings Configuration](#3-agent-settings-configuration)
4. [Opening Flow & Who Speaks First](#4-opening-flow--who-speaks-first)
5. [Real-Time Audio Pipeline](#5-real-time-audio-pipeline)
6. [Speech-to-Text (STT) System](#6-speech-to-text-stt-system)
7. [Text-to-Speech (TTS) System](#7-text-to-speech-tts-system)
8. [Transition Evaluation System](#8-transition-evaluation-system)
9. [Variable Extraction System](#9-variable-extraction-system)
10. [Webhook & Function Nodes](#10-webhook--function-nodes)
11. [Interruption Handling](#11-interruption-handling)
12. [Dead Air Prevention](#12-dead-air-prevention)
13. [Barge-In Detection](#13-barge-in-detection)
14. [Voicemail & IVR Detection](#14-voicemail--ivr-detection)
15. [Knowledge Base Integration](#15-knowledge-base-integration)
16. [Post-Call Webhooks](#16-post-call-webhooks)
17. [Redis State Management](#17-redis-state-management)
18. [Feature Verification Checklist](#18-feature-verification-checklist)

---

# 1. System Architecture Overview

## Core Components

### Backend Services

| Component | File | Purpose |
|-----------|------|---------|
| Call Session Manager | `core_calling_service.py` | Manages individual call sessions, LLM calls, flow processing |
| WebSocket Server | `server.py` | Handles Telnyx WebSocket connections, audio streaming |
| Telnyx Integration | `telnyx_service.py` | Call control, playback, recording |
| Persistent TTS | `persistent_tts_service.py` | WebSocket-based TTS streaming for low latency |
| Dead Air Monitor | `dead_air_monitor.py` | Silence detection and check-in triggering |
| Interruption System | `interruption_system.py` | Rambler detection and interruption handling |
| STT Services | `soniox_service.py`, `deepgram_service.py` | Speech-to-text providers |
| Redis Service | `redis_service.py` | Multi-worker state coordination |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INBOUND AUDIO FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Phone  ──▶  Telnyx  ──▶  WebSocket  ──▶  STT (Soniox)  ──▶  Transcript │
│                                    │                                         │
│                                    ▼                                         │
│                             Buffer (8kHz μ-law)                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          OUTBOUND AUDIO FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Transcript ──▶ LLM (Grok/GPT) ──▶ TTS (ElevenLabs) ──▶ Telnyx ──▶ User      │
│                      │                    │                                  │
│                      ▼                    ▼                                  │
│              Call Flow Logic      WebSocket Streaming                        │
│             (transitions,         (sentence-by-sentence)                     │
│              variables)                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### State Management

```python
# CallSession State (in-memory per worker)
class CallSession:
    call_id: str                    # Telnyx call control ID
    agent_config: dict              # Full agent configuration
    conversation_history: List      # Full conversation
    session_variables: Dict         # Extracted variables
    current_node_id: str            # Current position in flow
    
    # Speaking state
    agent_speaking: bool            # Is agent currently speaking?
    user_speaking: bool             # Is user currently speaking?
    
    # Silence tracking
    last_speech_time: float         # When someone last spoke
    checkin_count: int              # Number of check-ins sent
    
    # Flags
    is_active: bool                 # Is session still active?
    should_end_call: bool           # Should call be terminated?
    executing_webhook: bool         # Is a webhook currently executing?
```

---

# 2. Call Flow Node Types

## Overview

Call flow agents use a node-based structure where each node represents a step in the conversation. Nodes are connected by transitions based on user input.

## Node Type Reference

### 2.1 Start Node

**Purpose:** Entry point for the call flow. Configures initial behavior.

**Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `whoSpeaksFirst` | `"ai"` \| `"user"` | Who initiates the conversation |
| `aiSpeaksAfterSilence` | `boolean` | Should AI speak if user is silent? |
| `silenceTimeout` | `number` (ms) | How long to wait before AI speaks (default: 2000) |
| `firstMessage` | `string` | Optional override for AI's first message |

**Example:**
```json
{
  "id": "start_1",
  "type": "start",
  "label": "Start",
  "data": {
    "whoSpeaksFirst": "user",
    "aiSpeaksAfterSilence": true,
    "silenceTimeout": 2000
  }
}
```

### 2.2 Conversation Node

**Purpose:** Primary interactive node. Speaks content and evaluates transitions.

**Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `script` | `string` | Exact text to speak (SCRIPT mode) |
| `prompt` | `string` | Instructions for AI to generate response (PROMPT mode) |
| `goal` | `string` | Node objective (helps AI stay on track) |
| `transitions` | `array` | Outgoing transitions based on user response |
| `extract_variables` | `array` | Variables to extract from user input |
| `promptType` | `"script"` \| `"prompt"` | Which content to use |
| `skip_mandatory_precheck` | `boolean` | Skip mandatory variable validation before speaking |
| `auto_transition_after_response` | `string` | Node ID to auto-transition to after user speaks |
| `use_parallel_llm` | `boolean` | Run KB lookup and LLM in parallel |

**Modes:**
- **SCRIPT Mode:** Speaks the exact script text (fastest, no LLM call)
- **PROMPT Mode:** Uses LLM to generate contextual response based on prompt

**Example:**
```json
{
  "id": "greeting_1",
  "type": "conversation",
  "label": "Greeting",
  "data": {
    "promptType": "script",
    "script": "Hey {{customer_name}}, this is Jake from ABC Company.",
    "goal": "Confirm speaking to the right person",
    "transitions": [
      {
        "condition": "User confirms identity (Yes, Speaking, This is he/she)",
        "nextNode": "introduction_1"
      },
      {
        "condition": "Wrong number or denial",
        "nextNode": "wrong_number_1"
      }
    ]
  }
}
```

### 2.3 Function Node (Webhook)

**Purpose:** Execute external API calls during the conversation.

**Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `webhookUrl` | `string` | URL to call |
| `webhookMethod` | `"GET"` \| `"POST"` | HTTP method |
| `webhookHeaders` | `object` | Headers to include |
| `webhookBody` | `object` | Body template with variable placeholders |
| `waitForResponse` | `boolean` | Wait for webhook response before continuing |
| `transitions` | `array` | Transitions based on webhook result |
| `preCallMessage` | `string` | What to say before webhook executes |
| `successMessage` | `string` | What to say on success |
| `failureMessage` | `string` | What to say on failure |

**Example:**
```json
{
  "id": "book_appointment",
  "type": "function",
  "label": "Book Appointment",
  "data": {
    "webhookUrl": "https://api.calendly.com/schedule",
    "webhookMethod": "POST",
    "webhookBody": {
      "name": "{{customer_name}}",
      "phone": "{{phone_number}}",
      "date": "{{appointment_date}}",
      "time": "{{appointment_time}}"
    },
    "preCallMessage": "Perfect! Let me check that for you... one moment.",
    "transitions": [
      {
        "condition": "Booking successful",
        "nextNode": "confirmation_1"
      },
      {
        "condition": "Time unavailable",
        "nextNode": "reschedule_1"
      }
    ]
  }
}
```

### 2.4 Collect Input Node

**Purpose:** Collect specific information from user with validation.

**Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `variableName` | `string` | Variable to store the input |
| `inputType` | `"text"` \| `"number"` \| `"email"` \| `"phone"` \| `"date"` \| `"time"` | Expected input type |
| `prompt` | `string` | Question to ask |
| `retryMessage` | `string` | Message if input is invalid |
| `maxRetries` | `number` | Maximum retry attempts |

**Example:**
```json
{
  "id": "collect_email",
  "type": "collect_input",
  "label": "Get Email",
  "data": {
    "variableName": "customer_email",
    "inputType": "email",
    "prompt": "What email address should I use for the confirmation?",
    "retryMessage": "I didn't catch that. Could you spell out your email for me?",
    "maxRetries": 3
  }
}
```

### 2.5 Press Digit Node

**Purpose:** Handle IVR-style digit input.

**Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `variableName` | `string` | Variable to store digit |
| `prompt` | `string` | Message before waiting for digit |
| `validDigits` | `string[]` | Accepted digits |
| `timeout` | `number` | Timeout in seconds |

### 2.6 Extract Variable Node

**Purpose:** Dedicated variable extraction with LLM.

**Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `variables` | `array` | Variables to extract |
| `prompt` | `string` | Extraction context |

### 2.7 End Node

**Purpose:** Terminate the call.

**Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `message` | `string` | Final message before hangup |
| `disposition` | `string` | Call outcome category |
| `delay` | `number` | Seconds to wait before hangup |

**Example:**
```json
{
  "id": "end_success",
  "type": "end",
  "label": "Call Complete",
  "data": {
    "message": "Thanks so much, {{customer_name}}! We'll see you on {{appointment_date}}. Have a great day!",
    "disposition": "booked",
    "delay": 2
  }
}
```

---

# 3. Agent Settings Configuration

## Settings Structure

All agent settings are defined in the `settings` object of the agent configuration.

### 3.1 Core Settings

```python
class AgentSettings:
    # LLM
    temperature: float = 0.7          # Response creativity (0.0-1.0)
    max_tokens: int = 500             # Max response length
    llm_provider: str = "grok"        # "openai" | "grok"
    
    # TTS
    tts_speed: float = 1.0            # Speech speed (0.5-2.0)
    tts_provider: str = "elevenlabs"  # "elevenlabs" | "hume" | "cartesia" | etc.
    
    # STT
    stt_provider: str = "soniox"      # "soniox" | "deepgram" | "assemblyai"
    
    # Comfort Noise
    enable_comfort_noise: bool = True  # Background noise during silence
```

### 3.2 Dead Air Settings

Controls silence detection and check-in behavior.

```python
class DeadAirSettings:
    silence_timeout_normal: int = 7       # Seconds before "Are you still there?"
    silence_timeout_hold_on: int = 25     # Extended timeout if user said "hold on"
    max_checkins_before_disconnect: int = 2  # Check-ins before hanging up
    max_call_duration: int = 1500         # Max call length (seconds)
    checkin_message: str = "Are you still there?"
```

**Flow:**
```
User Silent → 7s → "Are you still there?" → 7s → "Are you still there?" → 7s → Hang up
                   (checkin_count = 1)          (checkin_count = 2)         (max reached)
```

### 3.3 Voicemail Detection Settings

```python
class VoicemailDetectionSettings:
    enabled: bool = True                   # Enable detection
    use_telnyx_amd: bool = True           # Use Telnyx AMD
    telnyx_amd_mode: str = "premium"      # "standard" | "premium"
    use_llm_detection: bool = True        # Backup LLM detection
    disconnect_on_detection: bool = True  # Auto-disconnect on voicemail
```

### 3.4 ElevenLabs TTS Settings

```python
class ElevenLabsSettings:
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Voice ID
    model: str = "eleven_turbo_v2_5"        # TTS model
    stability: float = 0.5                   # Voice consistency (0-1)
    similarity_boost: float = 0.75          # Voice matching (0-1)
    style: float = 0.0                       # Expressiveness (0-1)
    speed: float = 1.0                       # Speech rate (0.5-2.0)
    use_speaker_boost: bool = True
    enable_normalization: bool = True        # "5" → "five"
    enable_ssml_parsing: bool = False        # SSML support
```

### 3.5 Soniox STT Settings

```python
class SonioxSettings:
    model: str = "stt-rt-v3"               # Real-time model
    sample_rate: int = 8000                # Audio sample rate
    audio_format: str = "mulaw"            # μ-law encoding (telephony)
    num_channels: int = 1                  # Mono
    enable_endpoint_detection: bool = True # Detect speech boundaries
    enable_speaker_diarization: bool = False
    language_hints: List[str] = ["en"]
    context: str = ""                      # Domain-specific context
```

### 3.6 Deepgram STT Settings

```python
class DeepgramSettings:
    endpointing: int = 500      # ms before speech end
    vad_turnoff: int = 250      # VAD silence threshold
    utterance_end_ms: int = 1000  # Finalization delay
    interim_results: bool = True
    smart_format: bool = True
```

### 3.7 AssemblyAI STT Settings

```python
class AssemblyAISettings:
    sample_rate: int = 8000
    word_boost: List[str] = []                    # Boost specific words
    enable_extra_session_information: bool = True
    disable_partial_transcripts: bool = False
    threshold: float = 0.0                        # Turn detection (0=responsive)
    end_of_turn_confidence_threshold: float = 0.8
    min_end_of_turn_silence_when_confident: int = 500
    max_turn_silence: int = 2000
```

### 3.8 Webhook Settings

```python
# Post-call webhook (sends transcript after call ends)
post_call_webhook_url: Optional[str] = None
post_call_webhook_active: Optional[bool] = None

# Call-started webhook (notifies when call begins)
call_started_webhook_url: Optional[str] = None
call_started_webhook_active: Optional[bool] = None
```

---

# 4. Opening Flow & Who Speaks First

## Overview

The opening flow determines how the conversation begins. This is configured in the **Start Node**.

## Configuration Options

| Setting | Value | Behavior |
|---------|-------|----------|
| `whoSpeaksFirst` | `"ai"` | Agent immediately speaks first node content |
| `whoSpeaksFirst` | `"user"` | Agent waits for user to speak first |
| `aiSpeaksAfterSilence` | `true` | If user is silent, agent speaks after timeout |
| `silenceTimeout` | `2000` | Milliseconds to wait before speaking (default: 2s) |

## Scenario Matrix

### Scenario 1: Agent Speaks First

**Config:** `whoSpeaksFirst: "ai"`

```
CALL CONNECTS
    │
    ▼
AGENT SPEAKS NODE 1 (immediately)
"Hey Kendrick, this is Jake from ABC Company."
    │
    ▼
WAIT FOR USER RESPONSE
    │
    ▼
USER RESPONDS
"Yeah, what's up?"
    │
    ▼
EVALUATE TRANSITIONS → Move to next node
```

### Scenario 2: User Speaks First

**Config:** `whoSpeaksFirst: "user"`

```
CALL CONNECTS
    │
    ▼
AGENT WAITS (silent)
    │
    ▼
USER SPEAKS
"Hello?"
    │
    ▼
AGENT SPEAKS NODE 1 (in response)
"Hey, is this Kendrick?"
    │
    ▼
WAIT FOR USER RESPONSE
```

### Scenario 3: User Silent + AI Speaks After Silence

**Config:** `whoSpeaksFirst: "user"`, `aiSpeaksAfterSilence: true`, `silenceTimeout: 2000`

```
CALL CONNECTS
    │
    ▼
AGENT WAITS (silent)
    │
    │ (2 seconds pass, no user speech)
    ▼
SILENCE TIMEOUT FIRES
    │
    ▼
AGENT SPEAKS NODE 1
"Kendrick?"
    │
    ▼
WAIT FOR USER RESPONSE
```

### Scenario 4: Barge-In Race Condition

**Config:** Same as Scenario 3, but user speaks during greeting generation

```
CALL CONNECTS
    │
    ▼
AGENT WAITS (silent)
    │
    │ (2 seconds pass)
    ▼
SILENCE TIMEOUT FIRES
    │
    │ ← USER SPEAKS HERE (before audio played)
    │   "Hello?"
    ▼
DETECT USER SPOKE BEFORE AUDIO DELIVERED
    │
    ▼
CANCEL PENDING GREETING
    │
    ▼
TREAT AS SCENARIO 2 (User Speaks First)
```

## Implementation Details

**Location:** `server.py` lines 5240-5340

```python
# Check start node configuration
flow = agent.get("call_flow", [])
start_node = flow[0] if flow else {}
start_node_data = start_node.get("data", {})

who_speaks_first = start_node_data.get("whoSpeaksFirst", "ai")
ai_speaks_after_silence = start_node_data.get("aiSpeaksAfterSilence", False)
silence_timeout_ms = start_node_data.get("silenceTimeout", 2000)

if who_speaks_first == "user" and ai_speaks_after_silence:
    # Schedule silence timeout task
    asyncio.create_task(trigger_ai_after_silence_ws())
```

## State Flags

| Flag | Location | Purpose |
|------|----------|---------|
| `user_has_spoken` | Redis + Memory | Tracks if user spoke at all |
| `silence_greeting_triggered` | Redis + Memory | Prevents duplicate greetings |

---

# 5. Real-Time Audio Pipeline

## Audio Flow Architecture

### Inbound Audio (User → Server)

```
User's Phone
    │
    ▼ (8kHz μ-law audio)
Telnyx Cloud
    │
    ▼ (WebSocket: "media" events)
Server WebSocket Handler (server.py)
    │
    ├──▶ Raw Audio Packets
    │       │
    │       ▼
    │    STT Service (Soniox/Deepgram)
    │       │
    │       ▼
    │    Transcript Events
    │       │
    │       ├──▶ Partial: Update UI
    │       │
    │       └──▶ Final: Process Input
    │
    └──▶ Buffer for playback detection
```

### Outbound Audio (Server → User)

```
LLM Response Text
    │
    ▼
Sentence Splitter (regex-based)
    │
    ├──▶ Sentence 1: "Hey Kendrick,"
    │       │
    │       ▼
    │    TTS (ElevenLabs WebSocket)
    │       │
    │       ▼
    │    μ-law Audio Chunks
    │       │
    │       ▼
    │    Telnyx WebSocket (immediate)
    │
    ├──▶ Sentence 2: "yeah it's me."
    │       (same pipeline, parallel)
    │
    └──▶ Sentence 3: "You there?"
            (same pipeline, parallel)
```

## Latency Breakdown

| Stage | Target | Description |
|-------|--------|-------------|
| STT | <100ms | Soniox endpoint detection |
| LLM | <800ms | First token from Grok/GPT |
| TTS | <300ms | First audio chunk from ElevenLabs |
| Total E2E | <1200ms | User stops speaking → First audio plays |

## WebSocket Events

### Inbound Events (Telnyx → Server)

```json
// Media packet
{
  "event": "media",
  "payload": "<base64-encoded-audio>"
}

// Start streaming
{
  "event": "start",
  "stream_id": "abc123",
  "call_control_id": "v3:xyz"
}
```

### Outbound Events (Server → Telnyx)

```json
// Send audio
{
  "event": "media",
  "media": {
    "track": "outbound",
    "payload": "<base64-encoded-mulaw>",
    "timestamp": 1234567890
  }
}

// Clear audio buffer (for interruption)
{
  "event": "clear"
}
```

---

# 6. Speech-to-Text (STT) System

## Supported Providers

| Provider | File | Strengths |
|----------|------|-----------|
| Soniox | `soniox_service.py` | Fast endpoint detection, streaming |
| Deepgram | `deepgram_service.py` | High accuracy, good interim results |
| AssemblyAI | (integrated) | Smart endpointing, word boost |

## Soniox Integration

### Connection

```python
# soniox_service.py
class SonioxService:
    async def connect(self, api_key: str, settings: dict):
        # WebSocket connection to Soniox
        self.ws = await websockets.connect(
            "wss://api.soniox.com/v1/speech",
            extra_headers={"Authorization": f"Bearer {api_key}"}
        )
        
        # Send configuration
        await self.ws.send(json.dumps({
            "model": settings.get("model", "stt-rt-v3"),
            "sample_rate": 8000,
            "audio_format": "mulaw",
            "enable_endpoint_detection": True
        }))
```

### Event Handling

```python
# Token events from Soniox
{
    "tokens": [
        {"text": "Hello", "final": True},
        {"text": " ", "final": True},
        {"text": "there", "final": True}
    ],
    "endpoint": True  # End of utterance detected
}
```

### Endpoint Detection

Soniox detects when the user has finished speaking using:
- Voice Activity Detection (VAD)
- Semantic analysis for complete thoughts
- Configurable silence thresholds

When `endpoint: True` is received, the server:
1. Finalizes the transcript
2. Triggers `process_user_input()`
3. Generates AI response

---

# 7. Text-to-Speech (TTS) System

## Supported Providers

| Provider | Latency | Quality | WebSocket |
|----------|---------|---------|-----------|
| ElevenLabs | ~300ms | Excellent | ✅ Yes |
| Hume | ~400ms | Good | ❌ No |
| Cartesia | ~200ms | Good | ❌ No |
| Kokoro | ~300ms | Good | ❌ No |

## Persistent TTS Session (WebSocket)

For lowest latency, ElevenLabs uses a persistent WebSocket connection.

### Architecture

```python
# persistent_tts_service.py
class PersistentTTSSession:
    def __init__(self, call_control_id, api_key, voice_id):
        self.call_control_id = call_control_id
        self.elevenlabs_service = ElevenLabsWebSocketService()
        self.sentence_queue = asyncio.Queue()
        self.is_speaking = False
        self.generation_complete = False
        self.playback_expected_end_time = 0
```

### Sentence Streaming

Instead of waiting for the full LLM response, sentences are streamed immediately:

```python
async def stream_sentence(self, sentence: str, is_first: bool, is_last: bool):
    """Stream a single sentence through TTS"""
    # 1. Send text to ElevenLabs WebSocket
    await self.elevenlabs_service.send_text(sentence)
    
    # 2. Receive audio chunks (streaming)
    audio_data = await self.elevenlabs_service.receive_audio()
    
    # 3. Convert to μ-law and send to Telnyx WebSocket
    mulaw_audio = self.convert_to_mulaw(audio_data)
    await self.send_to_telnyx(mulaw_audio)
    
    # 4. Update expected playback end time
    duration = len(mulaw_audio) / 8000  # 8kHz sample rate
    self.playback_expected_end_time = time.time() + duration
```

### Audio Flow Timing

```
T=0ms    : LLM starts generating
T=200ms  : First sentence extracted "Hey Kendrick,"
T=250ms  : TTS starts for sentence 1
T=450ms  : First audio chunk received
T=460ms  : Audio playing on user's phone  ← FIRST AUDIO
T=500ms  : LLM still generating...
T=600ms  : Second sentence "yeah it's me."
T=650ms  : TTS for sentence 2 (parallel)
```

### Keepalive

ElevenLabs closes WebSocket after 20s of no input:

```python
async def _keepalive_loop(self):
    """Send periodic keepalive to prevent timeout"""
    while True:
        await asyncio.sleep(15)  # Every 15 seconds
        if self.is_connected:
            await self.elevenlabs_service.send_keepalive()
```

---

# 8. Transition Evaluation System

## Overview

Transitions determine how the agent moves between nodes based on user responses.

## Transition Structure

```json
{
  "condition": "User confirms identity (Yes, Speaking, This is he/she)",
  "nextNode": "introduction_1",
  "check_variables": ["customer_name"]  // Optional: require variables
}
```

## Evaluation Flow

```
USER RESPONSE RECEIVED
    │
    ▼
CHECK AUTO-TRANSITION SETTINGS
    ├── auto_transition_to? → Immediate transition, no evaluation
    └── auto_transition_after_response? → Skip LLM, go to specified node
    │
    ▼
HARD-CODED OVERRIDES (for specific patterns)
    ├── Greeting node + "Hello?" → Force transition to Introduction
    └── Other patterns...
    │
    ▼
VARIABLE CHECKS
    ├── Any transition requires missing variables? → Skip that transition
    └── All required variables present? → Include in options
    │
    ▼
LLM EVALUATION
    │
    ├── Build prompt with conversation context
    ├── Present transition options
    └── Ask LLM to pick best match (or -1 for no match)
    │
    ▼
RESULT
    ├── Valid index → Transition to next node
    └── -1 (no match) → Stay on current node, use goal for response
```

## LLM Evaluation Prompt

```python
eval_prompt = f"""You are analyzing a user's response to determine which transition path to take.

CONVERSATION HISTORY:
{conversation_context}

USER'S RESPONSE: "{user_message}"

TRANSITION OPTIONS:
Option 0: User confirms identity (Yes, Speaking, This is he/she)
Option 1: Wrong number or denial

Your task:
1. Carefully analyze the user's response
2. Determine which transition condition best matches their intent
3. Consider context and tone

Respond with ONLY the number (0, 1) of the BEST matching transition.
If NONE match, respond with -1."""
```

## Variable-Gated Transitions

Transitions can require specific variables to be extracted before they become available:

```json
{
  "condition": "Confirm appointment details",
  "nextNode": "booking_webhook",
  "check_variables": ["appointment_date", "appointment_time"]
}
```

If `appointment_date` or `appointment_time` is missing, this transition is **not presented** to the LLM.

---

# 9. Variable Extraction System

## Overview

Variables are extracted from user responses and stored in `session_variables` for use in scripts and webhooks.

## Variable Definition

```json
{
  "extract_variables": [
    {
      "name": "customer_name",
      "description": "The customer's full name",
      "mandatory": true,
      "type": "text"
    },
    {
      "name": "appointment_date",
      "description": "Preferred appointment date (MM/DD/YYYY)",
      "mandatory": false,
      "type": "date"
    }
  ]
}
```

## Extraction Modes

### 1. Mandatory Variables (Pre-Response)

Extracted **before** the agent speaks to ensure required info is captured:

```python
if has_mandatory_variables and not should_skip_precheck:
    # Extract variables FIRST
    await self._extract_mandatory_variables(extract_variables, user_message)
    
    # Check if all mandatory variables are set
    if all_mandatory_set:
        # Proceed with response
    else:
        # Generate prompt to ask for missing info
```

### 2. Non-Mandatory Variables (Background)

Extracted **after** the agent speaks to avoid latency:

```python
if not has_mandatory_variables:
    # Start extraction in background (non-blocking)
    asyncio.create_task(
        self._extract_variables_background(extract_variables, user_message)
    )
```

## Extraction Prompt

```python
extraction_prompt = f"""Extract the following variables from the user's response:

Variables to extract:
- customer_name: The customer's full name
- phone_number: A 10-digit phone number

User said: "{user_message}"

Conversation context:
{conversation_history}

Return JSON with the extracted values. Use null for values not found.
Example: {{"customer_name": "John Smith", "phone_number": null}}"""
```

## Using Variables

Variables can be used in node scripts with double-brace syntax:

```
"Hey {{customer_name}}, I have you down for {{appointment_date}} at {{appointment_time}}."
```

**Built-in Variables:**
| Variable | Source |
|----------|--------|
| `{{customer_name}}` | Extracted or injected |
| `{{phone_number}}` | From call data |
| `{{to_number}}` | Called number |
| `{{from_number}}` | Calling number |
| `{{now}}` | Current date/time (EST) |
| `{{email}}` | Customer email |

---

# 10. Webhook & Function Nodes

## Overview

Function nodes execute external API calls (webhooks) during the conversation.

## Execution Flow

```
ARRIVE AT FUNCTION NODE
    │
    ▼
SPEAK PRE-CALL MESSAGE
"Perfect! Let me check that for you..."
    │
    ▼
SET executing_webhook = True
(Pauses dead air monitoring)
    │
    ▼
EXECUTE WEBHOOK
    │
    ├── Build URL with variables
    ├── Send HTTP request
    └── Wait for response (up to 30s)
    │
    ▼
PARSE RESPONSE
    │
    ├── Extract result data
    └── Store in session variables
    │
    ▼
SET executing_webhook = False
    │
    ▼
EVALUATE TRANSITIONS
(Based on webhook response, not user message)
    │
    ▼
SPEAK SUCCESS/FAILURE MESSAGE
"Great news! You're all booked for..."
```

## Webhook Body Template

Variables are replaced before sending:

```json
{
  "webhookBody": {
    "action": "book_appointment",
    "name": "{{customer_name}}",
    "phone": "{{phone_number}}",
    "date": "{{appointment_date}}",
    "time": "{{appointment_time}}"
  }
}
```

## Response Handling

The webhook response is used for transition evaluation:

```python
# In _follow_transition()
if is_function_node and webhook_response:
    webhook_context = f"""
    WEBHOOK RESPONSE (base your decision on this):
    {json.dumps(webhook_response)}
    
    Look for keys like "status", "success", "booked", "available"
    """
    # LLM evaluates transitions based on webhook result
```

## Error Handling

```python
try:
    response = await http_client.post(webhook_url, json=body, timeout=30)
    webhook_result = response.json()
except Exception as e:
    logger.error(f"Webhook failed: {e}")
    webhook_result = {"success": False, "error": str(e)}
    # Will trigger failure transition
```

---

# 11. Interruption Handling

## Overview

The system detects when users interrupt the agent and handles it gracefully.

## Types of Interruptions

### 1. Barge-In (User speaks during TTS playback)

**Detection:**
- Track `playback_expected_end_time`
- If `user_spoke_at < playback_expected_end_time` → Barge-in detected

**Response:**
```python
# Clear Telnyx WebSocket buffer
await persistent_tts_session.clear_audio()

# Cancel pending sentences
persistent_tts_session.cancel_pending_sentences()

# Process user's input
await session.process_user_input(user_message)
```

### 2. Rambler Detection

For users who go off-topic or talk too long, the rambler detection system can interrupt:

```python
# interruption_system.py
class InterruptionConfig:
    enabled: bool = False
    word_count_threshold: int = 100      # Words before potential interrupt
    duration_threshold_seconds: int = 30
    off_topic_threshold: float = 0.7
    
    interrupt_phrases: list = [
        "I understand. Let me just ask...",
        "Got it. Just to keep us on track..."
    ]
```

## Clear Audio Implementation

```python
# persistent_tts_service.py
async def clear_audio(self):
    """Clear/stop any buffered audio in Telnyx WebSocket"""
    if self.telnyx_ws:
        try:
            # Send clear event to Telnyx
            message = {"event": "clear"}
            await self.telnyx_ws.send_text(json.dumps(message))
            logger.info("🛑 Sent clear audio event to Telnyx")
        except Exception as e:
            logger.error(f"Error clearing audio: {e}")
    
    # Mark as interrupted
    self.interrupted = True
    self.is_speaking = False
```

---

# 12. Dead Air Prevention

## Overview

The dead air monitor prevents awkward silences by tracking when both parties have stopped speaking.

## Configuration

```python
class DeadAirSettings:
    silence_timeout_normal: int = 7       # Default silence threshold
    silence_timeout_hold_on: int = 25     # Extended for "hold on" requests
    max_checkins_before_disconnect: int = 2
    checkin_message: str = "Are you still there?"
```

## Monitoring Logic

```python
# dead_air_monitor.py
async def monitor_dead_air(session, ...):
    while session.is_active:
        # Skip if webhook executing
        if session.executing_webhook:
            await asyncio.sleep(0.5)
            continue
        
        # Skip if audio still playing
        time_until_audio_done = playback_expected_end_time - time.time()
        if time_until_audio_done > 0.5:
            await asyncio.sleep(0.5)
            continue
        
        # Check silence duration
        silence_duration = session.get_silence_duration()
        
        if not session.agent_speaking and not session.user_speaking:
            if session.should_checkin():
                # Send check-in message
                await telnyx_service.speak_text(
                    call_control_id,
                    session.checkin_message
                )
                session.checkin_count += 1
```

## State Tracking

| Flag | Controlled By | Purpose |
|------|---------------|---------|
| `agent_speaking` | TTS start/end | Is agent audio playing? |
| `user_speaking` | STT partial/final | Is user talking? |
| `silence_start_time` | Agent stop speaking | When silence began |
| `checkin_count` | Check-in sent | How many check-ins sent |

## Silence Reset Conditions

Silence timer resets when:
1. User speaks (meaningful response, not just acknowledgment)
2. Agent speaks
3. Webhook starts executing

---

# 13. Barge-In Detection

## Overview

Barge-in occurs when the user speaks while the agent's silence greeting is being generated or played.

## Detection Points

### 1. During TTS Generation

```python
# In silence timeout task
greeting_response = await session.process_user_input("")

# Check if user spoke during generation
user_spoke_during_gen = redis_service.get("user_has_spoken")
if user_spoke_during_gen:
    logger.info("User spoke during greeting generation - CANCELLING")
    return  # Don't speak the greeting
```

### 2. After Greeting Started

```python
# In process_user_input()
if call_data.get("silence_greeting_triggered") and not is_silence_timeout:
    logger.warning("🚨 BARGE-IN DETECTED")
    
    # Stop audio
    await telnyx_service.stop_audio_playback(call_id)
    
    # Preserve history (greeting was spoken, user responded)
    # Continue processing user's input as response
```

## Key Insight

The system must track **when audio actually reached the user's ear**, not just when TTS generation started. If user speaks before audio is delivered, treat as "User Speaks First" scenario.

---

# 14. Voicemail & IVR Detection

## Overview

Detects when a call reaches voicemail or IVR system instead of a human.

## Detection Methods

### 1. Telnyx AMD (Answering Machine Detection)

```python
# In webhook handler
if event_type == "call.machine.premium.detection.ended":
    result = payload.get("result")  # "human_residence", "machine", etc.
    
    if result == "machine":
        if settings.disconnect_on_detection:
            await telnyx_service.hangup_call(call_control_id)
```

**AMD Results:**
| Result | Meaning |
|--------|---------|
| `human_residence` | Human answered |
| `machine` | Voicemail detected |
| `fax` | Fax machine |
| `not_sure` | Uncertain |

### 2. LLM-Based Detection

Backup detection using transcript analysis:

```python
async def detect_voicemail_llm(transcript: str) -> bool:
    prompt = f"""Analyze if this is a voicemail or IVR:
    "{transcript}"
    
    Voicemail indicators:
    - "Please leave a message"
    - "After the beep"
    - Automated greetings
    
    IVR indicators:
    - "Press 1 for..."
    - Menu options
    
    Return: true or false"""
```

---

# 15. Knowledge Base Integration

## Overview

Agents can access a knowledge base for factual information.

## KB Structure

```python
class KnowledgeBaseItem:
    id: str
    agent_id: str
    source_type: str        # "file" | "url"
    source_name: str        # filename or URL
    content: str            # extracted text
    description: str        # what this KB contains
```

## Smart KB Routing

Not all queries need KB:

```python
# kb_router.py
def should_use_kb(message: str, word_count: int) -> bool:
    # Skip for very short messages
    if word_count < 3:
        return False
    
    # Skip for simple acknowledgments
    if message.lower() in ["yes", "no", "okay"]:
        return False
    
    # Use KB for factual questions
    if any(q in message.lower() for q in ["what", "how", "why", "when"]):
        return True
    
    return False
```

## KB Injection

When KB is needed, content is added to the system prompt:

```python
if should_use_kb:
    kb_content = await fetch_relevant_kb(agent_id, user_message)
    
    system_prompt += f"""
    
    KNOWLEDGE BASE (use this for factual answers):
    {kb_content}
    """
```

---

# 16. Post-Call Webhooks

## Types

### 1. Call Started Webhook

Sent when call is answered.

```python
webhook_payload = {
    "event": "call.started",
    "call_id": call_control_id,
    "agent_id": agent_id,
    "to_number": to_number,
    "from_number": from_number,
    "timestamp": datetime.utcnow().isoformat()
}
```

### 2. Post-Call Webhook

Sent when call ends.

```python
webhook_payload = {
    "event": "call.ended",
    "call_id": call_control_id,
    "agent_id": agent_id,
    "duration": duration_seconds,
    "disposition": disposition,
    "transcript": transcript,
    "variables": extracted_variables,
    "recording_url": recording_url,
    "timestamp": datetime.utcnow().isoformat()
}
```

## Configuration

```python
settings = {
    "post_call_webhook_url": "https://your-crm.com/webhook",
    "post_call_webhook_active": True,
    "call_started_webhook_url": "https://your-crm.com/webhook",
    "call_started_webhook_active": True
}
```

---

# 17. Redis State Management

## Purpose

Redis enables state sharing across multiple server workers (horizontal scaling).

## Key Patterns

### Call Data Storage

```python
# Store call data
redis_service.set_call_data(call_control_id, {
    "agent_id": agent_id,
    "user_id": user_id,
    "custom_variables": {...},
    "silence_greeting_triggered": False,
    "user_has_spoken": False
})

# Retrieve call data
call_data = redis_service.get_call_data(call_control_id)
```

### Flag Coordination

```python
# Set flag (for cross-worker signaling)
redis_service.set_flag(call_control_id, "agent_done_speaking", True)

# Check flag (from another worker)
flag = redis_service.get_flag(call_control_id, "agent_done_speaking")
```

### Playback Tracking

```python
# Track active playbacks
redis_service.add_playback(call_control_id, playback_id)
redis_service.remove_playback(call_control_id, playback_id)

# Check if any playbacks active
count = redis_service.get_playback_count(call_control_id)
```

## TTL (Time-To-Live)

Call data expires after 1 hour:

```python
redis_service.set_call_data(call_control_id, data, ttl=3600)
```

---

# 18. Feature Verification Checklist

Use this checklist to verify all features are working correctly.

## 18.1 Call Connection

- [ ] Outbound call initiates successfully
- [ ] Telnyx webhook received for `call.initiated`
- [ ] Telnyx webhook received for `call.answered`
- [ ] WebSocket connection established
- [ ] Call data stored in Redis
- [ ] Session created in worker memory

## 18.2 Opening Flow

- [ ] **Agent Speaks First:** AI speaks immediately on connect
- [ ] **User Speaks First:** AI waits silently
- [ ] **Silence Timeout:** AI speaks after configured delay
- [ ] **User Speaks During Generation:** Greeting cancelled
- [ ] **User Speaks During Playback:** Audio stops, processes response

## 18.3 Speech-to-Text

- [ ] Soniox/Deepgram connects successfully
- [ ] Partial transcripts received and logged
- [ ] Final transcripts trigger processing
- [ ] Endpoint detection works correctly
- [ ] Latency < 100ms

## 18.4 LLM Processing

- [ ] Provider (Grok/OpenAI) connects
- [ ] System prompt includes agent personality
- [ ] Conversation history maintained
- [ ] Streaming responses enabled
- [ ] Latency to first token < 800ms

## 18.5 Text-to-Speech

- [ ] ElevenLabs WebSocket connects
- [ ] Audio streams sentence-by-sentence
- [ ] Correct voice ID used
- [ ] Speed settings applied
- [ ] Latency to first audio < 300ms

## 18.6 Transitions

- [ ] Transitions evaluated on user response
- [ ] LLM correctly identifies best match
- [ ] Variable-gated transitions respected
- [ ] "No match" stays on current node
- [ ] Auto-transitions work

## 18.7 Variables

- [ ] Variables extracted from user speech
- [ ] Mandatory variables block progress until provided
- [ ] Variables replaced in scripts
- [ ] Variables sent to webhooks
- [ ] Built-in variables ({{now}}, etc.) work

## 18.8 Webhooks

- [ ] Function nodes execute webhooks
- [ ] Pre-call message speaks first
- [ ] Webhook response parsed correctly
- [ ] Transitions based on webhook result
- [ ] Error handling works

## 18.9 Dead Air

- [ ] Silence detected after 7 seconds
- [ ] Check-in message sent
- [ ] Counter increments correctly
- [ ] Call ends after max check-ins
- [ ] "Hold on" extends timeout

## 18.10 Interruption

- [ ] User speech stops TTS playback
- [ ] Audio buffer cleared
- [ ] Pending sentences cancelled
- [ ] Conversation continues naturally

## 18.11 Voicemail Detection

- [ ] Telnyx AMD result received
- [ ] Machine detection triggers disconnect
- [ ] Human detected continues call

## 18.12 Recording

- [ ] Recording starts on call answer
- [ ] Recording saves on call end
- [ ] Recording URL in webhook payload

## 18.13 Post-Call

- [ ] Call-started webhook sent
- [ ] Post-call webhook sent
- [ ] Transcript included
- [ ] Variables included
- [ ] Recording URL included

---

# Appendix A: Error Codes

| Error | Cause | Solution |
|-------|-------|----------|
| `No LLM provider configured` | Missing `llm_provider` in settings | Set provider in agent settings |
| `No STT provider configured` | Missing `stt_provider` in settings | Set provider in agent settings |
| `ElevenLabs timeout` | No audio received in 2.5s | Check ElevenLabs API key |
| `Telnyx playback failed` | Invalid call ID or ended | Handle gracefully |
| `Variable check FAILED` | Transition requires missing variable | Extract variable first |

---

# Appendix B: Latency Optimization

## Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| STT Endpoint Detection | < 100ms | ~20ms (Soniox) |
| LLM First Token | < 800ms | ~500ms (Grok) |
| TTS First Chunk | < 300ms | ~250ms (ElevenLabs) |
| E2E (User Stop → Audio) | < 1200ms | ~800-1500ms |

## Optimization Techniques

1. **Persistent WebSocket Connections:** Keep ElevenLabs WS open for entire call
2. **Sentence Streaming:** Don't wait for full LLM response
3. **Parallel Processing:** LLM + KB lookup simultaneously
4. **Pre-warming:** Initialize clients before needed
5. **Caching:** TTS audio for repeated phrases

---

# Appendix C: File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `core_calling_service.py` | ~4700 | Core call logic, CallSession |
| `server.py` | ~10000 | FastAPI server, WebSocket handlers |
| `persistent_tts_service.py` | ~1000 | WebSocket TTS streaming |
| `dead_air_monitor.py` | ~170 | Silence detection |
| `telnyx_service.py` | ~1000 | Telnyx API integration |
| `soniox_service.py` | ~300 | Soniox STT |
| `models.py` | ~430 | Pydantic models |
| `redis_service.py` | ~300 | Redis operations |
| `interruption_system.py` | ~400 | Rambler detection |

---

**Document End**
