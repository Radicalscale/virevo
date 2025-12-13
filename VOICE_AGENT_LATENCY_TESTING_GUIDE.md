# Voice Agent Latency Testing Guide

## 📋 Table of Contents

1. [Overview & Goals](#overview--goals)
2. [Test Agent Configuration](#test-agent-configuration)
3. [How to Make Test Calls](#how-to-make-test-calls)
4. [How to Monitor & Listen](#how-to-monitor--listen)
5. [Metrics to Track](#metrics-to-track)
6. [Analysis Procedure](#analysis-procedure)
7. [Current Performance Baseline](#current-performance-baseline)
8. [Optimization Strategies](#optimization-strategies)
9. [Troubleshooting](#troubleshooting)

---

## 📊 Overview & Goals

### Purpose
Test and optimize the real-time voice agent's end-to-end latency to achieve natural, human-like conversation flow.

### Target Metrics
- **Primary Goal**: `kendrick` (TOTAL PAUSE) < 1,500ms average
- **Stretch Goal**: 80% of turns < 1,000ms
- **Best Case**: Sub-500ms for simple acknowledgments

### What is "kendrick"?
The **kendrick metric** measures the total time from when the user stops speaking until the agent starts speaking. This includes:
- STT latency (speech-to-text transcription)
- LLM latency (language model processing)
- TTS latency (text-to-speech generation)
- Any coded delays or processing overhead

### Why This Matters
- **< 1,000ms**: Feels instant, natural conversation
- **1,000-1,500ms**: Acceptable, slight pause
- **1,500-2,500ms**: Noticeable lag, less natural
- **> 2,500ms**: Frustrating, conversation breaks down

---

## 🤖 Test Agent Configuration

### Agent Details

**Name**: `latency tester`  
**Agent ID**: `a44acb0d-938c-4ddd-96b6-778056448731`  
**Type**: Call flow agent with prompt mode

### Current Stack (as of latest test)

```yaml
STT Provider: Soniox
  - Ultra-low latency (5-20ms)
  - Real-time endpoint detection
  - High accuracy

LLM Provider: Grok 4 Fast (xAI)
  - Model: grok-4-fast-non-reasoning
  - Temperature: 0.7
  - Max Tokens: 300
  - Streaming: Enabled

TTS Provider: Cartesia Sonic 2
  - Model: sonic-2
  - Voice ID: a0e99841-438c-4a64-b679-ae501e7d6091 (Friendly Reading Man)
  - Output: PCM 22050Hz → MP3 44100Hz (FFmpeg conversion)
```

### Call Flow Script

The agent follows this conversation flow:

1. **Start Node**: Wait for user to speak
2. **Greeting (Node 2)**: "{{customer_name}}?" (e.g., "Kendrick?")
   - Transition on affirmative → Node 3
   - Transition on wrong number → End
3. **Help Request (Node 3)**: "This is Jake. I was just, um, wondering if you could possibly help me out for a moment?"
4. **Opener (Node 4)**: Delivers "stacking income" pitch, asks for 25 seconds
5. **Intro Model (Node 5)**: Explains passive income websites model
6. **Ending (Node 6)**: "Thank you for calling. Goodbye!" → Hangs up

### Variable Configuration

```json
{
  "custom_variables": {
    "customer_name": "Kendrick"
  }
}
```

### How to View/Edit Agent

1. Navigate to UI: Agent Editor
2. Search for: "latency tester"
3. Settings are in the right panel:
   - LLM settings (provider, model, temperature)
   - TTS settings (provider, voice, model)
   - STT settings (provider, language)

---

## 📞 How to Make Test Calls

### Method 1: Python Script (Recommended)

```python
import requests

payload = {
    "agent_id": "a44acb0d-938c-4ddd-96b6-778056448731",
    "to_number": "+17708336397",  # Your test number
    "from_number": "+14048000152",  # Telnyx number
    "custom_variables": {
        "customer_name": "Kendrick"
    }
}

response = requests.post(
    "http://localhost:8001/api/telnyx/call/outbound",
    json=payload,
    timeout=10
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Call ID: {result.get('call_id')}")
else:
    print(f"❌ Failed: {response.status_code}")
```

Save as `test_call.py` and run:
```bash
python3 test_call.py
```

### Method 2: Using curl

```bash
curl -X POST http://localhost:8001/api/telnyx/call/outbound \
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

### Method 3: UI (Outbound Call Tester)

1. Navigate to: Outbound Call Tester in UI
2. Select agent: "latency tester"
3. Enter phone number: +17708336397
4. Click "Initiate Call"

### Test Call Procedure

**Best Practices:**

1. **Answer promptly** when phone rings
2. **Speak naturally** - don't rush or wait too long
3. **Keep responses varied**:
   - Short: "Yeah", "Okay", "Sure"
   - Medium: "I don't know, this sounds like a scam"
   - Long: Multi-sentence responses
4. **Let the agent finish** before interrupting (unless testing interruption)
5. **Complete the flow** - say "no questions" at the end to trigger goodbye

**Sample Conversation:**

```
Agent: "Kendrick?"
You: "Yeah."

Agent: "This is Jake. I was just, um, wondering if you could possibly help me out for a moment?"
You: "Sure."

Agent: [Delivers pitch about stacking income]
You: "I don't know, this sounds like a scam."

Agent: [Handles objection]
You: "Okay, go ahead."

Agent: [Explains model, asks for questions]
You: "No questions."

Agent: "Thank you for calling. Goodbye!"
[Call ends]
```

---

## 👂 How to Monitor & Listen

### Real-Time Log Monitoring

**Open a terminal and run:**

```bash
tail -f /var/log/supervisor/backend.err.log | grep -E "⏱️|TOTAL PAUSE|Breakdown|Cartesia|elevenlabs"
```

This will show you:
- ⏱️ TOTAL PAUSE (kendrick metric)
- Component breakdowns (STT + LLM + TTS)
- TTS provider activity
- API timing details

### What to Look For

**Good Turn:**
```
⏱️  TOTAL PAUSE: 850ms (user stopped → agent speaking)
⏱️  Breakdown: STT=5ms + LLM=850ms + TTS=750ms
⏱️  Cartesia API time: 480ms
⏱️  Conversion time: 75ms
```

**Problem Turn:**
```
⏱️  TOTAL PAUSE: 4200ms (user stopped → agent speaking)
⏱️  Breakdown: STT=8ms + LLM=4200ms + TTS=3800ms
```

### Extract Call Data After Test

```bash
# Get the call ID from the initiation response, then:
CALL_ID="v3:YOUR_CALL_ID_HERE"

# Extract all latency data for that call
tail -n 1000 /var/log/supervisor/backend.err.log | grep "$CALL_ID" | grep -E "⏱️|Breakdown" > call_analysis.txt
```

### Listen to Call Recording (if enabled)

Recordings are stored in database with signed URLs. Check the Calls page in the UI to:
1. See transcript
2. Play recording
3. View latency metrics per turn

---

## 📊 Metrics to Track

### Primary Metric: kendrick (TOTAL PAUSE)

**Definition**: Time from user speech endpoint → agent audio starts playing

**Formula**:
```
kendrick = STT_latency + LLM_latency + TTS_latency + overhead
```

**Target Distribution**:
- 20% < 500ms (excellent)
- 60% < 1,000ms (good)
- 80% < 1,500ms (acceptable)
- 0% > 2,500ms (poor)

### Component Metrics

#### STT (Speech-to-Text)
- **Measurement**: Audio received → Final transcript
- **Target**: < 50ms
- **Current (Soniox)**: 5-20ms ✅

#### LLM (Language Model)
- **Measurement**: Transcript received → Response generated
- **Target**: < 800ms
- **Current (Grok 4 Fast)**: 800-5,300ms ⚠️
- **Includes**: TTFT (Time to First Token) + generation time

#### TTS (Text-to-Speech)
- **Measurement**: Text received → Audio generated & queued
- **Target**: < 500ms
- **Current (Cartesia)**: 450-2,100ms per sentence ⚠️
- **Includes**: API call + audio conversion + playback_start

### Secondary Metrics

**Conversion Overhead** (Cartesia only):
- PCM → MP3 conversion time
- Target: < 100ms
- Current: 69-96ms ✅

**Multi-Sentence Scaling**:
- How TTS latency increases with response length
- Track: Number of sentences vs total TTS time

**Interruption Response Time**:
- Time from user interruption → playback stops
- Target: < 200ms

---

## 🔬 Analysis Procedure

### Step 1: Collect Raw Data

After completing a test call, extract all latency measurements:

```bash
# Create analysis file
tail -n 1000 /var/log/supervisor/backend.err.log | \
  grep -E "⏱️.*TOTAL PAUSE|Breakdown:" | \
  tail -20 > latency_data.txt
```

### Step 2: Parse Into Table

Create a spreadsheet or markdown table:

| Turn | User Input | Kendrick | STT | LLM | TTS | Status |
|------|-----------|----------|-----|-----|-----|--------|
| 1 | "Yeah" | 806ms | 5ms | 806ms | 783ms | ✅ Sub-1s |
| 2 | "Sure" | 2,054ms | 4ms | 2,054ms | 1,691ms | ⚠️ |
| ... | ... | ... | ... | ... | ... | ... |

### Step 3: Calculate Statistics

```python
# Example calculation
turns = [806, 2054, 5284, 4779, 1528]  # kendrick times in ms

average = sum(turns) / len(turns)
best = min(turns)
worst = max(turns)
sub_1s = sum(1 for t in turns if t < 1000) / len(turns) * 100
sub_1_5s = sum(1 for t in turns if t < 1500) / len(turns) * 100

print(f"Average: {average:.0f}ms")
print(f"Best: {best}ms")
print(f"Worst: {worst}ms")
print(f"Sub-1s rate: {sub_1s:.0f}%")
print(f"Sub-1.5s rate: {sub_1_5s:.0f}%")
```

### Step 4: Identify Patterns

**Look for:**

1. **Short vs Long Response Correlation**
   - Do simple "Yeah" responses have better latency?
   - How much does response length affect TTS?

2. **Turn Number Effects**
   - Does latency increase as call progresses?
   - Is there caching or warmup?

3. **Component Bottlenecks**
   - Which component varies most? (Usually LLM)
   - Is one component consistently slow?

4. **Multi-Sentence Behavior**
   - Count TTS calls per turn
   - Calculate per-sentence average

### Step 5: Compare to Baseline

**Current Baseline (as of 2025-10-20):**

```yaml
Stack: Grok 4 Fast + Cartesia Sonic 2

Average: 2,890ms
Best Turn: 806ms
Worst Turn: 5,284ms
Sub-1s: 20%
Sub-1.5s: 40%

Components:
  STT: 5-9ms (excellent)
  LLM: 806-5,284ms (high variance)
  TTS: 550-4,400ms (scales with length)
```

Compare your results:
- Better: Average < 2,890ms
- Same: Within 10% of baseline
- Worse: Average > 3,200ms

### Step 6: Root Cause Analysis

**If LLM is slow:**
- Check prompt complexity
- Look at response length
- Consider context window size

**If TTS is slow:**
- Count number of sentences
- Check for multi-TTS calls
- Verify conversion times

**If both are slow:**
- Likely long, complex response
- Check the actual agent response text
- Consider prompt optimization

---

## 📈 Current Performance Baseline

### Test Date: 2025-10-20

**Configuration:**
- STT: Soniox
- LLM: Grok 4 Fast (grok-4-fast-non-reasoning)
- TTS: Cartesia Sonic 2 (sonic-2 model)

### Results Summary

```
Test Call: 5 turns
Average Latency: 2,890ms
Success Rate (sub-1.5s): 40%

Turn-by-Turn:
Turn 1: 806ms   ✅ (short response: "Kendrick?")
Turn 2: 2,054ms ⚠️ (medium response: help request)
Turn 3: 5,284ms ❌ (long response: pitch)
Turn 4: 4,779ms ❌ (long response: objection handling)
Turn 5: 1,528ms ⚠️ (medium response: model explanation)
```

### Component Performance

**STT (Soniox):**
```
Range: 4-9ms
Average: 6ms
Status: ✅ OPTIMAL - No optimization needed
```

**LLM (Grok 4 Fast):**
```
Range: 806-5,284ms
Average: 2,890ms
Variance: 6.5x (best to worst)
Status: ⚠️ HIGH VARIANCE - Main bottleneck
Issue: Scales dramatically with prompt complexity/length
```

**TTS (Cartesia Sonic 2):**
```
API Range: 451-2,090ms per sentence
Conversion: 69-96ms per call
Total Range: 550-4,400ms per turn
Average: ~1,600ms
Status: ⚠️ SCALES WITH LENGTH - Secondary bottleneck
Issue: Sequential processing of multi-sentence responses
```

### Comparison to Previous Stacks

| Stack | Average | Best | Sub-1s | Notes |
|-------|---------|------|--------|-------|
| OpenAI GPT-4.1 + ElevenLabs | 2,450ms | 1,185ms | 25% | Baseline |
| Grok 4 Fast + ElevenLabs | 1,605ms | 546ms | 50% | 35% improvement |
| Grok 4 Fast + Cartesia | 2,890ms | 806ms | 20% | Slower due to multi-sentence |

### Key Insights

1. **Short responses excel**: Sub-1s consistently achievable
2. **Long responses struggle**: 3-5 seconds for multi-sentence
3. **Not Cartesia's fault**: Sequential architecture causes slowdown
4. **LLM variance**: Biggest challenge (800ms → 5,300ms)

---

## 🚀 Optimization Strategies

### Completed Optimizations

✅ **Switched to Grok 4 Fast** (35% improvement for simple turns)
✅ **Integrated Cartesia Sonic 2** (450ms TTFB for short responses)
✅ **Optimized Cartesia conversion** (FFmpeg overhead: 70-95ms)
✅ **Fixed audio format** (Normal playback speed at 22050→44100Hz)

### Potential Next Steps

#### Option A: Parallel TTS Generation

**Problem**: Multi-sentence responses process sequentially
```
Current: Sentence 1 (2s) → Sentence 2 (1.5s) → Sentence 3 (1s) = 4.5s
Target:  All 3 start simultaneously → 2s perceived (first audio)
```

**Implementation**:
- Generate all sentences in parallel as LLM yields them
- Queue playback_start calls
- Maintain order for playback

**Expected Improvement**: 40-50% faster for long responses
**Complexity**: Medium
**Risk**: Ordering issues, race conditions

#### Option B: Cache Common Phrases

**Problem**: Repeated phrases regenerated every time

**Solution**:
```python
CACHE = {
    "Kendrick?": "/cache/greeting_kendrick.mp3",
    "This is Jake...": "/cache/intro_jake.mp3",
    # ... more
}

if text in CACHE:
    play_cached_audio(CACHE[text])  # 0ms latency!
else:
    generate_and_play(text)
```

**Expected Improvement**: 0ms for 20-30% of utterances
**Complexity**: Low
**Risk**: Minimal (cache invalidation)

#### Option C: Prompt Optimization

**Problem**: Complex prompts cause LLM slowdown

**Current Prompts**: 500-1,000 words with detailed instructions

**Optimization Strategies**:
- Use few-shot examples instead of verbose instructions
- Compress to <300 words
- Implement sliding context window (last 5 turns only)

**Expected Improvement**: 30-50% LLM latency reduction
**Complexity**: Medium
**Risk**: May affect response quality (need testing)

#### Option D: Try Cartesia Sonic Turbo

**Specs**:
- Model: `sonic-turbo`
- Claimed: 40ms latency (vs 90ms for sonic-2)
- Trade-off: Slightly lower quality

**Implementation**: One-line change in agent settings

**Expected Improvement**: 50ms faster TTS
**Complexity**: Very low
**Risk**: Voice quality may differ

#### Option E: Hybrid LLM Routing

**Problem**: Simple turns don't need powerful LLM

**Solution**:
```
If user_input is simple acknowledgment:
    Use GPT-4o-mini (300ms)
Else:
    Use Grok 4 Fast (800-5,000ms)
```

**Expected Improvement**: 50% faster for simple turns
**Complexity**: High
**Risk**: Routing logic complexity

### Recommended Implementation Order

1. **Option B (Caching)** - Easy win, low risk
2. **Option D (Sonic Turbo)** - Quick test, minimal effort
3. **Option A (Parallel TTS)** - Highest impact for long responses
4. **Option C (Prompt Optimization)** - If quality allows
5. **Option E (Hybrid LLM)** - Advanced, if needed

---

## 🐛 Troubleshooting

### Problem: No Audio Playing

**Symptoms**: Call connects but silence

**Check**:
1. TTS provider logs: `grep "🔊 Generating TTS" /var/log/supervisor/backend.err.log | tail -10`
2. Playback logs: `grep "playback_start" /var/log/supervisor/backend.err.log | tail -10`
3. Audio generation: `grep "✅.*Generated.*bytes" /var/log/supervisor/backend.err.log | tail -10`

**Common Causes**:
- TTS provider not configured correctly
- Audio format incompatibility (wrong sample rate)
- Telnyx playback_start failing (422 error = call ended)

**Solution**:
- Verify agent settings in database
- Check audio format in generate_audio_cartesia()
- Ensure call is still active when playback starts

### Problem: Chipmunk/Sped Up Voice

**Symptoms**: Audio plays too fast, high-pitched

**Cause**: Sample rate mismatch

**Check**:
```python
# In generate_audio_cartesia(), look for:
output_format = {
    "sample_rate": ???  # Should be 22050 for Cartesia
}

# And ffmpeg conversion:
'-ar', '44100',  # Output should be 44100Hz
```

**Solution**: Ensure proper rate conversion (22050 → 44100)

### Problem: High Latency Spikes

**Symptoms**: Some turns are 5+ seconds

**Diagnosis**:
1. Check component breakdown:
   ```bash
   grep "Breakdown:" /var/log/supervisor/backend.err.log | tail -20
   ```
2. Identify if LLM or TTS is slow
3. Check for multi-sentence responses

**Common Causes**:
- Long, complex LLM response
- Multiple TTS calls for multi-sentence responses
- Prompt context too large

**Solution**:
- Keep responses concise
- Implement prompt compression
- Consider parallel TTS generation

### Problem: Agent Not Transitioning

**Symptoms**: Stuck on one node, repeating same message

**Check**:
1. Transition configuration in database
2. Logs: `grep "Transition:" /var/log/supervisor/backend.err.log | tail -20`
3. Verify node has transition for user's response type

**Solution**: Add missing transitions in agent flow builder

### Problem: Call Drops Before Goodbye

**Symptoms**: Call ends without goodbye message

**Check**:
```bash
grep "Ending call now" /var/log/supervisor/backend.err.log | tail -5
grep "playback.ended" /var/log/supervisor/backend.err.log | tail -10
```

**Common Causes**:
- Hangup delay too short (currently 3.5s)
- Audio not finishing playback before hangup
- Playback error causing early termination

**Solution**: Increase wait time in server.py end node handler

### Problem: Inconsistent Results

**Symptoms**: Same setup gives wildly different latencies

**Diagnosis**: This is expected due to:
- LLM response variance (prompt complexity)
- Network conditions
- Response length variation
- API load/performance

**Solution**: Run multiple tests (5-10 calls) and average results

---

## 📝 Testing Checklist

### Pre-Test Setup

- [ ] Verify agent configuration (TTS/LLM/STT providers)
- [ ] Check API keys are active (Cartesia, Grok, Soniox)
- [ ] Ensure backend is running: `sudo supervisorctl status backend`
- [ ] Test phone number works
- [ ] Clear previous logs (optional): `sudo truncate -s 0 /var/log/supervisor/backend.err.log`

### During Test

- [ ] Start log monitoring: `tail -f /var/log/supervisor/backend.err.log | grep "⏱️"`
- [ ] Initiate call via script/curl/UI
- [ ] Answer promptly when phone rings
- [ ] Speak naturally with varied responses
- [ ] Complete full conversation flow
- [ ] Note any audio quality issues
- [ ] Observe latency in real-time

### Post-Test Analysis

- [ ] Extract latency data for all turns
- [ ] Create performance table
- [ ] Calculate average, best, worst
- [ ] Identify bottlenecks (STT/LLM/TTS)
- [ ] Compare to baseline
- [ ] Document findings
- [ ] Plan next optimization

### Reporting Template

```markdown
## Latency Test Report - [Date]

**Configuration:**
- STT: [Provider]
- LLM: [Provider + Model]
- TTS: [Provider + Model]

**Results:**
- Turns: [N]
- Average: [X]ms
- Best: [Y]ms
- Worst: [Z]ms
- Sub-1s: [A]%
- Sub-1.5s: [B]%

**Component Breakdown:**
- STT: [range]ms
- LLM: [range]ms
- TTS: [range]ms

**Observations:**
[Notes on what worked well, what didn't, patterns noticed]

**Next Steps:**
[Recommended optimizations to try next]
```

---

## 🎯 Success Criteria

### Minimum Viable Performance

- ✅ 50% of turns < 1,500ms
- ✅ No turns > 5,000ms
- ✅ Audio quality: Clear, normal speed
- ✅ Interruption handling: Working

### Target Performance

- 🎯 70% of turns < 1,500ms
- 🎯 50% of turns < 1,000ms
- 🎯 Best turn < 500ms
- 🎯 Average < 1,500ms

### Optimal Performance

- 🌟 80% of turns < 1,000ms
- 🌟 Average < 1,000ms
- 🌟 Worst turn < 2,500ms
- 🌟 Consistent across multiple tests

---

## 📚 Additional Resources

### Log File Locations
```
Backend: /var/log/supervisor/backend.err.log
Frontend: /var/log/supervisor/frontend.err.log
```

### Key Code Files
```
Backend:
  - /app/backend/server.py (main API endpoints)
  - /app/backend/calling_service.py (LLM processing)
  - /app/backend/telnyx_service.py (call control)
  - /app/backend/cartesia_service.py (TTS service)
  - /app/backend/soniox_service.py (STT service)

Frontend:
  - /app/frontend/src/components/AgentForm.jsx (agent editor)
  - /app/frontend/src/components/OutboundCallTester.jsx (test UI)
```

### Database Collections
```
agents: Agent configurations
call_logs: Call recordings and transcripts
api_keys: Service API keys
```

### Useful Commands
```bash
# Restart services
sudo supervisorctl restart backend
sudo supervisorctl restart all

# View logs
tail -n 100 /var/log/supervisor/backend.err.log
tail -f /var/log/supervisor/backend.err.log | grep "⏱️"

# Check service status
sudo supervisorctl status

# Test backend endpoint
curl http://localhost:8001/health
```

---

## 🔄 Version History

**v1.0** - 2025-10-20
- Initial latency testing framework
- Baseline established with Grok + Cartesia
- Documentation created

---

**Last Updated**: 2025-10-20  
**Current Best**: 806ms (sub-1s achieved!)  
**Target**: < 1,500ms average (80% success rate)
