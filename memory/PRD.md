# Voice AI Agent Platform - PRD

## Original Problem Statement
Build a real-time voice AI agent platform with ultra-low latency conversational capabilities using:
- **Telephony:** Telnyx for call control and media streaming
- **STT:** Soniox for speech-to-text
- **TTS:** ElevenLabs for text-to-speech (via persistent WebSocket)
- **LLM:** Grok (x.ai) for conversational logic

### Critical Issue Being Addressed
The platform experienced severe **5-7 second latency** between user finishing speech and agent audio response starting. This made real-time conversation unusable.

## Architecture

```
/app
├── backend/
│   ├── server.py                 # Main FastAPI app, WebSocket handlers, call state
│   ├── core_calling_service.py   # Core call flow logic, state machine, LLM calls
│   ├── telnyx_service.py         # Telnyx API interactions
│   ├── persistent_tts_service.py # Audio queues and persistent TTS WebSockets
│   └── elevenlabs_ws_service.py  # ElevenLabs WebSocket connection
└── frontend/
```

## What's Been Implemented

### 2025-01-09 - Audio Queue Fix
- **Root Cause Identified:** `UnboundLocalError` in `persistent_tts_manager` access due to redundant local imports causing Python scope confusion
- **Fix Applied:** Removed 4 redundant local imports of `persistent_tts_manager` inside `handle_soniox_streaming` function
- **Expected Result:** Audio queue now properly clears when user starts speaking, eliminating stale audio latency

### Previous Session Work
- File-based TTS cache fix (voice-crossing bug)
- Import fixes for `os` and `hashlib` placement
- HTTP/2 client optimization for LLM API calls
- Transition timeout adjustment (1.5s → 3.0s)
- Comprehensive `[REAL TIMING]` logging system

## Current Status

| Component | Status |
|-----------|--------|
| Audio Queue Clearing | ✅ Fixed (pending user verification) |
| STT (Soniox) | ✅ Working (~3-10ms latency) |
| TTS (ElevenLabs) | ✅ Working |
| LLM (Grok) | ✅ Working (~400-2000ms depending on complexity) |
| Barge-in/Interruption | ⚠️ Works but uses calculated timing (needs refactor) |

## Prioritized Backlog

### P0 - Critical
- [x] Fix audio queue not clearing on user interruption (ROOT CAUSE OF 5-7s LATENCY)

### P1 - High Priority
- [ ] Optimize transition latency (currently ~1-1.5s from heavyweight LLM)
  - Option A: Keyword/regex fast-path before LLM
  - Option B: Embeddings-based semantic matching

### P2 - Medium Priority
- [ ] Complete logging system (missing ElevenLabs first audio chunk timing)
- [ ] Refactor barge-in logic to use actual `audio_queue` state instead of `playback_expected_end_time`

### P3 - Low Priority
- [ ] Clean up transition logic in `core_calling_service.py`
- [ ] Code refactoring for maintainability

## 3rd Party Integrations
- **Telnyx:** Call Control and Media Streaming
- **Soniox:** Speech-to-Text (STT)
- **ElevenLabs:** Text-to-Speech (TTS)
- **Grok (x.ai):** LLM - uses Emergent LLM Key
- **Gemini (Google):** LLM (available but Grok is primary) - uses Emergent LLM Key

## Key Database Schema
- **agents:** Agent configurations, TTS settings, voice_id
- **call_sessions:** Redis cache for live call state

## Testing Notes
- Real latency = "user speech finished" → "first agent audio heard"
- Don't trust old log metrics like `E2E_TOTAL`, use `[REAL TIMING]` logs
- User recordings are the ground truth for latency measurement
