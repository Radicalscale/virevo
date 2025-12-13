# WebSocket TTS Streaming Implementation Plan

## 🎯 Goal
Replace REST API TTS with WebSocket streaming to reduce perceived latency by 50-75% WITHOUT breaking existing functionality.

## 📋 Current Architecture (REST)

### How it works now:
1. `calling_service.py` yields sentences from LLM
2. Each sentence → `speak_text()` in `telnyx_service.py`
3. `speak_text()` calls `generate_tts_audio()` (REST API to ElevenLabs)
4. Full audio synthesized (180-450ms)
5. Audio saved to `/tmp/tts_*.mp3`
6. `playback_start` REST call to Telnyx with audio URL
7. Returns `playback_id` for interruption tracking
8. Interruption: Uses `stop_playback(call_control_id, playback_id)`

### Interruption Handling:
- Tracks active `playback_id`s in `call_states[call_id]['active_playbacks']`
- On interruption: Calls `stop_playback()` for all active playback IDs
- Uses `call.playback.ended` webhooks to close interruption window

## 🔄 Target Architecture (WebSocket)

### How it will work:
1. **One-time setup per call**: Open WebSocket to ElevenLabs when call starts
2. `calling_service.py` yields sentences from LLM (unchanged)
3. Each sentence → Send text chunk to ElevenLabs WebSocket
4. ElevenLabs streams back audio chunks in real-time
5. Forward audio chunks directly to Telnyx Media Stream WebSocket
6. Audio plays as it's generated (perceived latency: 300-500ms vs 2,000ms+)

### Critical Preservation:
- **MUST maintain playback tracking** for interruption handling
- **MUST preserve single-word vs multi-word detection**
- **MUST keep `call.playback.ended` webhook logic**
- **MUST NOT break Soniox STT integration**

## 🏗️ Implementation Strategy

### Phase 1: Add WebSocket Support (Parallel to REST)
**Goal**: Add new WebSocket path WITHOUT removing REST API

1. Create `elevenlabs_ws_service.py`:
   - WebSocket connection manager for ElevenLabs
   - Methods: `connect()`, `send_text()`, `receive_audio_chunks()`
   - Handle reconnection on errors

2. Create `telnyx_media_stream.py`:
   - Manage Telnyx Media Stream WebSocket
   - Methods: `send_audio_chunk()`, `handle_bidirectional()`
   - Audio format: Base64-encoded PCM μ-law

3. Add WebSocket route in `server.py`:
   - `/api/telnyx/media-stream` WebSocket endpoint
   - Handles bidirectional audio (STT input + TTS output)

### Phase 2: Modify `speak_text()` with Fallback
**Goal**: Add WebSocket option while keeping REST as fallback

Update `telnyx_service.py`:
```python
async def speak_text(
    self,
    call_control_id: str,
    text: str,
    agent_config: dict = None,
    use_websocket: bool = False  # NEW PARAMETER
) -> Dict[str, Any]:
    if use_websocket and agent_config:
        # Try WebSocket streaming
        try:
            return await self._speak_text_websocket(call_control_id, text, agent_config)
        except Exception as e:
            logger.warning(f"WebSocket TTS failed, falling back to REST: {e}")
            # Fall through to REST API below
    
    # Existing REST API logic (unchanged)
    ...
```

### Phase 3: Maintain Interruption Tracking
**CRITICAL**: WebSocket TTS must still support interruption

Options:
A. **Generate synthetic playback_id** for WebSocket streams
   - Track "stream_id" as if it were a playback_id
   - Interruption: Close WebSocket connection to stop audio

B. **Use Telnyx queue with WebSocket**
   - Still use `playback_start` but with WebSocket-generated audio
   - Maintains existing playback_id tracking

**RECOMMENDED**: Option B for safety (least changes to interruption logic)

### Phase 4: Testing Protocol
1. Test with `use_websocket=False` (should work exactly as before)
2. Test with `use_websocket=True` on single sentence
3. Test with multi-sentence responses
4. **Test interruption handling** (most critical)
   - Single-word affirmatives during speech (should ignore)
   - Multi-word interruptions (should stop playback)
5. Test end-to-end call flow with transitions

### Phase 5: Gradual Rollout
1. Add feature flag in agent settings: `"use_websocket_tts": false`
2. Test on "latency tester" agent first
3. Once stable, enable for other agents
4. Eventually make it default, keep REST as fallback

## ⚠️ Risks & Mitigations

### Risk 1: Breaking Interruption Handling
**Mitigation**: 
- Keep REST API as fallback
- Extensive testing before removing old code
- Maintain `playback_id` concept even with WebSocket

### Risk 2: WebSocket Connection Failures
**Mitigation**:
- Automatic reconnection logic
- Fallback to REST on WebSocket errors
- Comprehensive error handling

### Risk 3: Audio Format Mismatches
**Mitigation**:
- ElevenLabs WebSocket: Request `output_format: "pcm_16000"`
- Telnyx Media Stream: Accept `encoding: "PCMU"` (8kHz μ-law)
- Use audio resampling if needed (already have `audio_resampler.py`)

### Risk 4: Latency from Audio Processing
**Mitigation**:
- Use efficient audio encoding/decoding
- Minimize buffering
- Stream chunks immediately (don't wait for sentence completion)

## 📊 Expected Improvements

### Current (REST API):
- LLM TTFT: 480-773ms
- Full sentence TTS: 180-450ms
- Playback API call: 180-340ms
- **Total to first audio: 1,993-2,338ms**

### Target (WebSocket):
- LLM TTFT: 480-773ms (unchanged)
- First TTS chunk: 75-150ms (ElevenLabs WebSocket TTFB)
- Stream audio immediately
- **Total to first audio: 555-923ms** (60-70% faster)

### Sentence-level improvement:
- 3-sentence response current: 1,628ms TTS
- 3-sentence response target: 600-900ms perceived (audio starts immediately)

## ✅ Success Criteria

1. **Functionality Preserved**:
   - ✅ Interruption handling works correctly
   - ✅ Single-word affirmative detection works
   - ✅ Multi-word interruption triggers correctly
   - ✅ Call transitions work unchanged
   - ✅ End node hangs up correctly

2. **Latency Improved**:
   - ✅ First audio <1,000ms for simple turns
   - ✅ "Kendrick" metric reduced by 40-60%
   - ✅ Multi-sentence responses feel faster

3. **Reliability**:
   - ✅ Fallback to REST works on WebSocket failure
   - ✅ No dropped audio or glitches
   - ✅ Reconnection works after disconnects

## 🔄 Implementation Timeline

**Step 1** (30 min): Research ElevenLabs WebSocket API docs
**Step 2** (1-2 hours): Create `elevenlabs_ws_service.py`
**Step 3** (1 hour): Create `telnyx_media_stream.py`
**Step 4** (1 hour): Update `speak_text()` with WebSocket option
**Step 5** (30 min): Add feature flag to agent settings
**Step 6** (1-2 hours): Testing and refinement
**Step 7** (30 min): Document and rollout

**Total Estimated Time**: 5-7 hours

## 🚦 Decision Point

**Before proceeding, I need your confirmation:**

1. ✅ This plan preserves interruption handling correctly?
2. ✅ Fallback to REST API is acceptable for safety?
3. ✅ Feature flag approach is good for gradual rollout?
4. ✅ Should I proceed with implementation?

**Any concerns or modifications to this plan?**
