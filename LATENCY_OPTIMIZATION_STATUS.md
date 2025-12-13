# Voice Agent Latency Optimization & Interruption Handling - Status Report

## 🎯 Project Goal
Achieve consistent <1.5s response latency (ideally <500ms) with functional interruption handling for a Retell-like voice assistant.

---

## ✅ COMPLETED IMPLEMENTATIONS

### 1. Comprehensive Latency Instrumentation
**Location**: `/app/backend/server.py` (Soniox handler), `/app/backend/calling_service.py`

**Metrics Tracked**:
- **STT Latency**: Last audio packet → transcript ready
- **LLM TTFT**: Time-To-First-Token (transcript → first LLM token)
- **LLM Total**: Full generation time
- **TTS Latency**: Text ready → audio synthesis complete
- **Total Pause**: User stops speaking → Agent starts speaking (KEY METRIC)

**Logging**:
```
⏱️  TOTAL PAUSE: 604ms (user stopped → agent speaking)
⏱️  Breakdown: STT=19ms + LLM=604ms + TTS=581ms
```

All metrics saved to:
- Console logs: `/var/log/supervisor/backend.*.log`
- Database: `call_logs.logs` field with `level: "metrics"`

### 2. Sentence-Level Streaming
**Location**: `/app/backend/calling_service.py` - `_process_single_prompt_streaming()`, `_process_call_flow_streaming()`

**Implementation**:
- LLM streams tokens via `stream=True`
- Tokens buffered and split by sentence delimiters (`.!?`)
- Each complete sentence sent to TTS immediately
- Reduces perceived latency by starting audio playback during LLM generation

**Providers Supported**:
- OpenAI: Native streaming via `client.chat.completions.create(stream=True)`
- Grok: Added streaming support to `GrokClient.create_completion(stream=True)`

### 3. Interruption Handling (Webhook-Based)
**Location**: `/app/backend/server.py` - Soniox handler + webhook endpoint

**Architecture**:
- **Global State**: `call_states` dict tracks interruption window per call
- **Interruption Window**: Active while agent is generating/playing audio
- **Trigger**: 2+ words during window → stops playback
- **Ignore**: Single words ("yeah", "okay") during window → discarded
- **Normal Processing**: All words (including single) when agent is silent

**Key Logic**:
```python
# Partial transcript callback checks for interruptions
if agent_generating_response and word_count >= 2:
    # Stop all active playbacks immediately
    for playback_id in current_playback_ids:
        await telnyx_service.stop_playback(call_control_id, playback_id)
    
# Webhook closes interruption window when audio finishes
if event_type == "call.playback.ended":
    state["current_playback_ids"].remove(playback_id)
    if len(state["current_playback_ids"]) == 0:
        state["agent_generating_response"] = False  # Window closed
```

**Webhook Integration**:
- Telnyx sends `call.playback.ended` when each audio chunk finishes
- System tracks active `playback_ids` in global state
- Window closes automatically when ALL playbacks complete
- No time-based estimation (archived in `/app/TIME_BASED_INTERRUPTION_APPROACH.md`)

### 4. Provider Optimization
**Current Stack**:
- **STT**: Soniox (8-21ms latency, semantic endpointing)
- **LLM**: Grok 4 Fast non-reasoning (currently active) OR OpenAI GPT-4.1
- **TTS**: ElevenLabs Flash v2.5 (75ms TTFB target)

**Agent ID**: `a44acb0d-938c-4ddd-96b6-778056448731` (Call flow agent)

---

## 📊 CURRENT PERFORMANCE

### Latest Metrics (Grok 4 Fast):
| Turn Type | Total Latency | STT | LLM | TTS |
|-----------|---------------|-----|-----|-----|
| **Best** | 604ms ✅ | 19ms | 604ms | 581ms |
| **Good** | 900-1065ms ✅ | 2-11ms | 900-1065ms | 499-573ms |
| **Complex** | 2047-2684ms ❌ | 6-18ms | 2047-2684ms | 1113-1724ms |

**LLM TTFT**: 458-539ms (excellent)

### Comparison: Grok vs OpenAI
| Metric | OpenAI GPT-4.1 | Grok 4 Fast |
|--------|----------------|-------------|
| Best Turn | 470ms | 604ms |
| Complex Turn | 2.5-3.2s | 2.0-2.7s |

### Component Analysis:
- ✅ **STT (Soniox)**: 0-21ms - OPTIMAL
- ⚠️ **LLM**: 600ms - 2.7s - Needs optimization on complex prompts
- ⚠️ **TTS**: 500ms - 1.7s - Scales poorly with response length

---

## 🚧 CURRENT ISSUES

### 1. Complex Prompt Latency
**Problem**: Call flow nodes with long prompts (1000+ words) cause 2-3s delays
**Hypothesis**: Prompt length directly impacts LLM processing time
**Next Steps**: Need to investigate if this is unavoidable or can be optimized

### 2. TTS Latency Scaling
**Problem**: TTS takes 1-1.7s for longer responses
**Current**: ElevenLabs Flash v2.5 claims 75ms TTFB but we see 500-1700ms total
**Hypothesis**: 
- Sentence-level streaming helps TTFT
- But total synthesis time scales with word count
- May need WebSocket TTS streaming for true real-time playback

### 3. End Node Hangup
**Status**: Fixed (scope issue resolved)
**Location**: `/app/backend/server.py` line ~1460
**Implementation**: `telnyx_svc = get_telnyx_service()` then `hangup_call()`

---

## 🧪 TESTING WORKFLOW

### A/B Testing LLM Providers

**Switch to OpenAI**:
```bash
curl -s -X PUT "http://localhost:8001/api/agents/a44acb0d-938c-4ddd-96b6-778056448731" \
-H "Content-Type: application/json" \
-d '{
  "name": "Call flow",
  "agent_type": "call_flow",
  "settings": {
    "llm_provider": "openai",
    "temperature": 0.7,
    "max_tokens": 300
  }
}'
```

**Switch to Grok**:
```bash
curl -s -X PUT "http://localhost:8001/api/agents/a44acb0d-938c-4ddd-96b6-778056448731" \
-H "Content-Type: application/json" \
-d '{
  "name": "Call flow",
  "agent_type": "call_flow",
  "settings": {
    "llm_provider": "grok",
    "temperature": 0.7,
    "max_tokens": 300
  }
}'
```

**Initiate Test Call**:
```bash
curl -s -X POST "http://localhost:8001/api/telnyx/call/outbound" \
-H "Content-Type: application/json" \
-d '{
  "agent_id": "a44acb0d-938c-4ddd-96b6-778056448731",
  "to_number": "+17708336397",
  "from_number": "+14048000152",
  "custom_variables": {
    "customer_name": "Kendrick"
  }
}'
```

**Extract Latency Metrics**:
```bash
# During call
tail -f /var/log/supervisor/backend.err.log | grep "⏱️"

# After call (replace CALL_ID)
tail -n 1000 /var/log/supervisor/backend.err.log | grep -E "CALL_ID" | grep -E "⏱️.*TOTAL PAUSE|Breakdown|LLM TTFT"
```

### Standard Test Script for User

**Node 1**: Say "Yeah" (1 word, agent silent) → Should transition ✅

**Node 2**: 
- Agent speaks → Say "okay" mid-speech (1 word) → Should ignore ✅
- Agent finishes → Say "Sure" (1 word) → Should transition ✅

**Node 3**: 
- Agent speaks → Say "wait wait hold on" (2+ words) mid-speech → Should interrupt ✅

**End Node**: Agent says goodbye → Call should hang up after 2s ✅

### Verification Checklist

After each test call:

1. **Check Transcript** (database):
```bash
python3 << 'EOF'
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017")
db = client["test_database"]
call = db.call_logs.find_one({"call_id": "CALL_ID"})
for entry in call.get("transcript", []):
    print(f"{entry['role'].upper()}: {entry['text']}")
client.close()
EOF
```

2. **Check Logs**:
- ✅ "🔕 Ignoring 1-word acknowledgment during generation" - Single words ignored
- ✅ "🛑 INTERRUPTION TRIGGERED" - Interruptions detected
- ✅ "✋ Stopped X playbacks" - Playback stopped
- ✅ "🔊 All audio finished - interruption window CLOSED" - Webhooks working

3. **Check Latency**:
- Best case: <1s
- Good case: <1.5s
- Complex: Document and investigate

---

## 🔧 KEY FILES

### Backend
- `/app/backend/server.py` - Main FastAPI, Soniox handler, webhooks, latency tracking
- `/app/backend/calling_service.py` - LLM streaming, sentence splitting, call flow logic
- `/app/backend/telnyx_service.py` - Telnyx API, playback control, hangup

### Documentation
- `/app/TIME_BASED_INTERRUPTION_APPROACH.md` - Archived timing approach
- `/app/LATENCY_OPTIMIZATION_STATUS.md` - This file
- `/app/test_result.md` - Testing protocol and agent communication

### Configuration
- Agent ID: `a44acb0d-938c-4ddd-96b6-778056448731`
- Test phone: `+17708336397`
- From number: `+14048000152`

---

## 🎯 NEXT STEPS

### Immediate Focus: LLM & TTS Optimization

**LLM Investigation**:
1. Run A/B tests: OpenAI vs Grok on SAME prompts
2. Measure if complex prompts always cause 2-3s delays
3. Test with shorter max_tokens (150 vs 300)
4. Investigate prompt caching or optimization

**TTS Investigation**:
1. Verify ElevenLabs Flash v2.5 settings (`optimize_streaming_latency=4`)
2. Test if WebSocket TTS streaming improves latency
3. Consider alternative TTS providers for comparison
4. Measure actual vs claimed TTFB

### Long-Term Optimizations

1. **Parallel Processing**: Overlap TTS generation with LLM streaming more aggressively
2. **Prompt Engineering**: Reduce call flow node prompt sizes
3. **Model Selection**: Test GPT-4o-mini vs GPT-4.1 for speed vs quality tradeoff
4. **Caching**: Implement prompt caching for repeated instructions

---

## 📝 INSTRUCTIONS FOR FRESH AGENT

### On Takeover:

1. **Read this file completely** - Do not ask user to re-explain what's been done
2. **Check current agent settings**: Is it using Grok or OpenAI?
3. **Run a quick test call** to verify system is working
4. **Check latest logs** to understand current state
5. **Ask user**: "What specific issue are you experiencing?" or "What would you like to optimize next?"

### DO NOT:
- ❌ Ask user to explain the architecture again
- ❌ Ask about interruption handling implementation
- ❌ Ask about latency tracking implementation
- ❌ Break functionality by rewriting working code
- ❌ Use time-based interruption windows (archived approach)

### DO:
- ✅ Run A/B tests to compare providers
- ✅ Document findings in this file
- ✅ Make incremental changes
- ✅ Test after each change
- ✅ Focus on LLM and TTS optimization

### Testing Philosophy:
- User will provide feedback after each test
- Cross-reference with transcript and logs
- Don't claim success without verification
- If interruption fails 2+ times, troubleshoot with deep investigation
- Keep user in the loop but minimize interruptions

---

## 🔍 TROUBLESHOOTING

### Interruption Not Working
1. Check logs for "BARGE-IN CHECK" or "INTERRUPTION TRIGGERED"
2. Verify `agent_generating_response` is True during agent speech
3. Confirm `call.playback.ended` webhooks are arriving
4. Check `current_playback_ids` is being populated

### Latency Regression
1. Check if STT provider changed (should be Soniox)
2. Verify streaming is enabled (`stream=True`)
3. Check TTS model (should be Flash v2.5)
4. Review recent code changes for blocking calls

### End Node Not Hanging Up
1. Check logs for "📞 Ending call now..."
2. Verify "Hangup result" appears
3. Check `session.should_end_call` flag is set
4. Confirm `telnyx_svc.hangup_call()` executes

---

## 📊 METRICS ARCHIVE

### Test Cycle 8 (OpenAI GPT-4.1 + Sentence Streaming)
- Best: 495ms (STT=15ms, LLM=495ms, TTS=494ms)
- Good: 552ms (STT=0ms, LLM=552ms, TTS=551ms)

### Test Cycle 20+ (Grok 4 Fast + Webhook Interruption)
- Best: 604ms (STT=19ms, LLM=604ms, TTS=581ms)
- Complex: 2047-2684ms (LLM bottleneck)

### Provider Comparison Summary
- OpenAI: Slightly faster best case (470ms vs 604ms)
- Grok: Slightly faster complex case (2.0-2.7s vs 2.5-3.2s)
- Both: Sub-1s possible on simple prompts, 2-3s on complex prompts

---

**Last Updated**: 2025-10-20 00:48 UTC
**Status**: Active Development - Optimizing LLM & TTS Latency
**Current Agent**: Grok 4 Fast
**All Systems**: ✅ Operational (Interruption, Streaming, Latency Tracking)
