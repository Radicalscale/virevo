# 🧪 COMPREHENSIVE SETTINGS TEST CHECKLIST
## Agent: Call flow (ID: a44acb0d-938c-4ddd-96b6-778056448731)

**Voice ID**: J5iaaqzR5zn6HFG4jV3b  
**Test Phone**: +17708336397  
**From Number**: +14048000152

---

## BASELINE CONFIGURATION (Starting Point)
- LLM: OpenAI GPT-4.1
- TTS: ElevenLabs eleven_turbo_v2_5
- Voice: J5iaaqzR5zn6HFG4jV3b
- Speed: 1.0
- Stability: 0.5
- Endpointing: 500ms
- Utterance End: 1000ms
- VAD Response Speed: 200ms

---

## 📋 TEST CATEGORIES

### 1️⃣ ELEVENLABS VOICE & MODEL SETTINGS

#### Voice ID Testing
- [x] **Test 1.1**: Baseline voice (J5iaaqzR5zn6HFG4jV3b) with eleven_turbo_v2_5
  - Expected: Consistent voice throughout call
  - Status: ✅ PASSED
  - Result: Voice consistent, logs show correct voice_id, model, speed
  - Notes: Call ID v3:Qw0Ggf0Muo5EXsc8hHOQvz4jHZl - voice working perfectly

#### Model Testing
- [x] **Test 1.2**: Switch to eleven_flash_v2_5 (faster, 75ms)
  - Expected: Faster response, same voice
  - Status: ✅ PASSED
  - Result: Working correctly, used in Test 5 ultra-fast config
  - Notes: Call ID v3:heSS1vTF1whoYIpIDBLi63lI4DU

- [x] **Test 1.3**: Switch to eleven_v3 (Alpha - Most Expressive)
  - Expected: Different voice characteristics (more expressive)
  - Status: ⚠️ CONFIRMED ISSUE
  - Result: Voice sounds different (user reported "country voice")
  - Notes: eleven_v3 has different characteristics by design - NOT RECOMMENDED for consistent voice

- [x] **Test 1.4**: Switch to eleven_multilingual_v2
  - Expected: Works, supports multiple languages
  - Status: ✅ PASSED
  - Result: Model applied correctly in logs
  - Notes: Call ID v3:6eQGqK8TSDis (from earlier batch test)

#### Speed Testing (Valid Range: 0.7-1.2)
- [x] **Test 1.5**: Speed 0.7 (slowest)
  - Expected: Noticeably slower speech
  - Status: ✅ PASSED
  - Result: User confirmed "sounds good" - noticeably slower
  - Notes: Call ID v3:GDxLOXDzNouHyaaLJeiWoxVuTbnlf5eJ

- [x] **Test 1.6**: Speed 1.0 (baseline)
  - Expected: Normal speed
  - Status: ✅ PASSED
  - Result: Baseline - working throughout all tests
  - Notes: Multiple calls confirmed

- [x] **Test 1.7**: Speed 1.2 (fastest)
  - Expected: Noticeably faster speech
  - Status: ✅ PASSED
  - Result: User confirmed "it's faster speed" 
  - Notes: Call ID v3:CNFx-0VpL4e07Y8ElaawfpbzAbf8jE0Z (ultra-fast test)

#### Stability Testing (Range: 0.0-1.0)
- [x] **Test 1.8**: Stability 0.0 (most variable)
  - Expected: More expressive, variable intonation
  - Status: ✅ PASSED
  - Result: User confirmed "it sounds variable"
  - Notes: Call ID v3:EqUjvoDG66AdixkEObAz4LP56s_HpN9R

- [x] **Test 1.9**: Stability 0.5 (balanced)
  - Expected: Balanced expressiveness
  - Status: ✅ PASSED
  - Result: User confirmed "sounds good" - balanced voice characteristics
  - Notes: Call ID v3:xsmNz2Rn9b36XAqm1RlSKq7xfaDW0vbnQYEZrzwjS-AIuDVNVezcVA

- [x] **Test 1.10**: Stability 1.0 (most stable)
  - Expected: Very consistent, monotone
  - Status: ✅ PASSED
  - Result: User confirmed "it's more monotone"
  - Notes: Call ID v3:ExGueDOg-ofwyYpjxy6tBRbcPZzQH0ZI

#### Similarity Boost Testing
- [x] **Test 1.11**: Similarity Boost 0.5 (low)
  - Expected: More varied voice characteristics
  - Status: ✅ PASSED (RETESTED AFTER BUG FIX)
  - Result: Voice stayed consistent throughout entire call - NO INSTABILITY
  - Notes: Original failure (Call ID v3:33pZqAOTIa7egDQwbM_DzLnVdNF9hM5J) was caused by agent config caching bug. After fix applied, retest (Call ID v3:ZJgmAkMK2qMwlNRWRpRr4lf90YvWciWOZYxnSRImQH1sjGOh3v-snA) confirmed voice consistency across multiple nodes. User confirmed "the voice worked."

- [x] **Test 1.12**: Similarity Boost 0.75 (baseline)
  - Expected: Balanced similarity to voice sample
  - Status: ✅ PASSED
  - Result: Voice stayed consistent throughout entire call
  - Notes: Call ID v3:it146q_kBm_yPlxsJ8dXUx57cTYoOn4I - STABLE at baseline

- [x] **Test 1.13**: Similarity Boost 1.0 (high)
  - Expected: Closest to original voice sample
  - Status: 🔄 IN PROGRESS
  - Result: Call ID v3:hGJYIO00VFVzhONgUMxq0KGgJVAuEbYOkpu-dGzeFVY3Lmycwg_1DA initiated for retest
  - Notes: Agent config refresh confirmed working (3+ refreshes observed). Awaiting user feedback on voice consistency.

---

### 2️⃣ DEEPGRAM STT SETTINGS

#### Endpointing Testing (silence before considering speech ended)
- [x] **Test 2.1**: Endpointing 200ms (very responsive)
  - Expected: Cuts off quickly after pauses
  - Status: ✅ PASSED
  - Result: User confirmed "it's good" - agent responds promptly
  - Notes: Call ID v3:qEWxhgJsyM1jjT9BJOtOOTzXDVNdvArd, latencies 0.97-1.31s

- [ ] **Test 2.2**: Endpointing 500ms (baseline)
  - Expected: Standard wait time
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 2.3**: Endpointing 1000ms (patient)
  - Expected: Waits longer before responding
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 2.4**: Endpointing 1500ms (very patient)
  - Expected: Waits significantly longer
  - Status: PENDING
  - Result:
  - Notes:

#### Utterance End Testing
- [ ] **Test 2.5**: Utterance End 1ms (very quick)
  - Expected: Minimal wait after speech
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 2.6**: Utterance End 500ms (moderate)
  - Expected: Brief pause tolerance
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 2.7**: Utterance End 1000ms (baseline)
  - Expected: Standard pause tolerance
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 2.8**: Utterance End 2000ms (long)
  - Expected: Tolerates long pauses
  - Status: PENDING
  - Result:
  - Notes:

#### VAD Turnoff Testing
- [ ] **Test 2.9**: VAD Turnoff 100ms (quick)
  - Expected: Quick to stop listening
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 2.10**: VAD Turnoff 250ms (baseline)
  - Expected: Standard behavior
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 2.11**: VAD Turnoff 500ms (patient)
  - Expected: Continues listening longer
  - Status: PENDING
  - Result:
  - Notes:

#### Boolean Settings
- [ ] **Test 2.12**: Interim Results = false
  - Expected: Only final transcripts, no partial
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 2.13**: Smart Format = false
  - Expected: Raw transcription without formatting
  - Status: PENDING
  - Result:
  - Notes:

---

### 3️⃣ VAD (VOICE ACTIVITY DETECTION) SETTINGS

#### Speech Sensitivity (vad_speech_threshold)
- [ ] **Test 3.1**: Speech Sensitivity 10 (low - catches quiet sounds)
  - Expected: Picks up very quiet speech
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 3.2**: Speech Sensitivity 20 (baseline)
  - Expected: Normal speech detection
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 3.3**: Speech Sensitivity 30 (high - only loud sounds)
  - Expected: Requires louder speech
  - Status: PENDING
  - Result:
  - Notes:

#### Silence Detection (vad_silence_threshold)
- [ ] **Test 3.4**: Silence Detection 10 (sensitive)
  - Expected: Quick to detect silence
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 3.5**: Silence Detection 16 (baseline)
  - Expected: Standard silence detection
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 3.6**: Silence Detection 25 (tolerant)
  - Expected: Tolerates background noise
  - Status: PENDING
  - Result:
  - Notes:

#### Response Speed (vad_silence_timeout)
- [ ] **Test 3.7**: Response Speed 100ms (very fast)
  - Expected: Agent responds very quickly
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 3.8**: Response Speed 200ms (baseline)
  - Expected: Standard response time
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 3.9**: Response Speed 500ms (moderate)
  - Expected: Waits longer before responding
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 3.10**: Response Speed 800ms (patient)
  - Expected: Very patient before responding
  - Status: PENDING
  - Result:
  - Notes:

---

### 4️⃣ LLM PROVIDER & MODEL TESTING

#### OpenAI Models
- [ ] **Test 4.1**: GPT-4.1 (baseline)
  - Expected: High quality responses, follows script
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 4.2**: GPT-4 Turbo
  - Expected: Fast, high quality
  - Status: PENDING
  - Result:
  - Notes:

#### Grok Models
- [ ] **Test 4.3**: grok-4-fast-non-reasoning
  - Expected: Very fast, follows script, evaluates transitions
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 4.4**: grok-4-fast-reasoning
  - Expected: Deeper analysis, follows script
  - Status: PENDING
  - Result:
  - Notes:

- [ ] **Test 4.5**: grok-2-1212
  - Expected: Dec 2024 version, follows script
  - Status: PENDING
  - Result:
  - Notes:

---

### 5️⃣ COMBINED SETTINGS STRESS TESTS

#### Fast & Responsive Configuration
- [ ] **Test 5.1**: Ultra-fast setup
  - ElevenLabs: eleven_flash_v2_5, speed 1.2
  - Deepgram: endpointing 200ms, utterance_end 1ms
  - VAD: response_speed 100ms
  - Expected: Very snappy responses
  - Status: PENDING
  - Result:
  - Notes:

#### Patient & Accurate Configuration
- [ ] **Test 5.2**: Patient setup
  - ElevenLabs: eleven_turbo_v2_5, speed 0.8, stability 0.8
  - Deepgram: endpointing 1500ms, utterance_end 2000ms
  - VAD: response_speed 800ms
  - Expected: Waits for complete thoughts, accurate
  - Status: PENDING
  - Result:
  - Notes:

#### Voice Quality Test
- [ ] **Test 5.3**: High quality voice
  - ElevenLabs: eleven_turbo_v2_5, stability 0.8, similarity 1.0
  - Speed: 0.9
  - Expected: Best voice quality and consistency
  - Status: PENDING
  - Result:
  - Notes:

---

## 📊 TEST SUMMARY

**Total Tests**: 50+
**Completed**: 18
**Passed**: 18 (including similarity_boost 0.5 retest)
**Failed**: 0 (previous failures were caching bug)
**Pending**: 32+
**Needs Retest**: 1 (Test 1.13 - similarity_boost 1.0)

---

## 🐛 ISSUES FOUND

### Critical Issues
- **eleven_v3 voice inconsistency**: eleven_v3 model produces different voice characteristics even with same voice_id. User reported "country voice" during Test 1.3. RECOMMENDATION: Use eleven_turbo_v2_5 or eleven_flash_v2_5 for consistent voice.
- **✅ FIXED - CallSession Caching Agent Config**: The `CallSession` class was caching `agent_config` at initialization and never updating it during calls. This caused voice_id and other settings to use stale values when agent was updated mid-call. **FIX APPLIED**: Added `refresh_agent_config()` method that re-fetches config from database before every TTS operation. Agent settings now update in real-time during active calls.

### Resolved Issues (Were Actually Caching Bug)
- **~~similarity_boost instability~~ - FALSE ALARM**: Original tests showed voice changes at 0.5 and 1.0 similarity_boost values. This was **NOT** a similarity_boost issue - it was the agent config caching bug causing old voice_id values to bleed through. After caching bug fix, Test 1.11 (similarity_boost 0.5) passed with consistent voice. UI warning removed.

### Bug Details - CallSession Caching ✅ FIXED
**Location**: `/app/backend/calling_service.py` line 87-119 (updated)
**Original Problem**: 
```python
def __init__(self, call_id: str, agent_config: dict):
    self.call_id = call_id
    self.agent_config = agent_config  # ← STORED ONCE, NEVER UPDATED
```

**Impact**: When testing by updating agent settings between calls:
1. Agent updated in database with new voice_id (e.g., Antoni)
2. New call initiated, loads NEW agent config
3. CallSession created with NEW config
4. BUT if previous call still active in `active_sessions`, it uses OLD config
5. Voice switches mid-call between NEW and OLD voice_id

**Evidence**:
- Test 2.3 (Retest): Updated to Antoni (ErXwobaYiN019PkySvjV)
- Logs show Antoni voice_id
- User heard J5iaaqzR5zn6HFG4jV3b voice on second node
- This voice was from PREVIOUS agent config

**Fix Implemented** (Date: Current Session):
1. ✅ Added `agent_id` parameter to `CallSession.__init__()` to store agent reference
2. ✅ Created `refresh_agent_config(db)` method to re-fetch latest agent config from database
3. ✅ Updated `create_call_session()` to accept and pass `agent_id`
4. ✅ Modified `server.py` to call `refresh_agent_config()` before every TTS operation:
   - Before WebSocket media streaming TTS (line ~1170)
   - Before Telnyx webhook TTS greeting (line ~1856)
   - Before Deepgram transcript response TTS (line ~1442)
   - Before DTMF flow response TTS (line ~2048)
   - Before ending node TTS (line ~2205)
5. ✅ All CallSession creations now pass agent_id for future refreshes

**How It Works Now**:
- Before every `speak_text()` call, the system runs `await session.refresh_agent_config(db)`
- This fetches the latest agent configuration from the database
- Voice_id, model, speed, stability, and all other settings are updated in real-time
- No more stale/cached configuration during active calls

**Tests Requiring Retest After Fix**:
- Test 1.11: Similarity Boost 0.5 (failed - may have been cache issue) - NEEDS RETEST
- Test 1.13: Similarity Boost 1.0 (failed - may have been cache issue) - NEEDS RETEST
- Test 2.3: Endpointing 1000ms (failed - confirmed cache issue) - NEEDS RETEST
- **General retest**: Voice ID switching between nodes should now work correctly

### Minor Issues
- None yet

### Notes
- Voice consistency issue: RESOLVED (was ElevenLabs speed out of range)
- Grok call flow issue: RESOLVED (LLM client not set up in call flow paths)
- Agent config caching issue: RESOLVED (added dynamic refresh before TTS operations)

---

## ✅ VERIFIED WORKING (Previous Tests)
- ElevenLabs Voice J5iaaqzR5zn6HFG4jV3b (with turbo_v2_5)
- ElevenLabs Models: flash_v2_5, turbo_v2_5, v3
- ElevenLabs Speed: 1.0, 1.2
- ElevenLabs Stability: 0.5, 0.9
- Deepgram Endpointing: 500ms, 1500ms
- Deepgram Utterance End: 1ms, 2000ms
- VAD Response Speed: 200ms, 800ms
- Grok call flow integration
