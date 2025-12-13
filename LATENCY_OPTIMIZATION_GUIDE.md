# Latency Optimization Guide - Rapid Iteration Without Deployments

## The Problem

**Railway deployments take 10+ minutes**. If you need to iterate on latency optimization, waiting for deployments makes it impossible to work efficiently.

**50 optimization attempts = 8+ hours of waiting** ⏰

## The Solution

**Call Flow Simulator** - Simulate the COMPLETE production pipeline locally:
- ✅ STT (speech-to-text transcription)
- ✅ LLM processing
- ✅ TTS (text-to-speech generation)
- ✅ Webhook triggers (playback events)
- ✅ Node transitions
- ✅ Variable extraction
- ✅ Audio playback timing

**Iterate back-to-back-to-back until you hit your latency targets**, then deploy once.

## Quick Start

### Run a Single Test

```bash
python3 /app/call_flow_simulator.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --scenario quick \
  --target-latency 2.0 \
  --profile
```

### Optimization Loop (Until Target Met)

```bash
/app/optimize_latency.sh \
  b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  2.0 \
  quick
```

This will:
1. Run test
2. Show latency breakdown
3. If target not met, wait for you to make changes
4. Press Enter to test again
5. Repeat until target is achieved

## Complete Pipeline Simulation

The simulator mimics the EXACT production flow:

```
User Speaks
    ↓
🎤 STT Transcription (50-200ms)
    ↓
🧠 Message Processing / LLM Call (500-2000ms)
    ↓
🔊 TTS Generation (200-1000ms)
    ↓
🔗 Webhook: playback.started (20ms)
    ↓
⏸️  Audio Playback (duration based on word count)
    ↓
🔗 Webhook: playback.ended (20ms)
    ↓
🗺️  Node Transition (instant)
    ↓
📋 Variable Extraction (instant)
```

Every stage is timed and profiled.

## Example Output

```
🎯 TURN 1: Yeah, this is Mike
======================================================================
⏱️  Stage 1: STT Transcription...
   ✅ STT: 0.090s
⏱️  Stage 2: Message Processing (LLM)...
   ✅ LLM Processing: 0.063s
⏱️  Stage 3: TTS Audio Generation...
   ✅ TTS: 0.460s

🤖 AGENT RESPONSE:
   Mike Rodriguez?

📊 TURN METRICS:
   Total Time: 3.327s
   Current Node: 2
   Should End: False

⚡ LATENCY BREAKDOWN:
   STT: 0.090s (2.7%)
   LLM: 0.063s (1.9%)
   TTS: 0.460s (13.8%)
   Audio Playback: 2.700s (81.2%)
```

## Detailed Profiling

At the end of each test:

```
================================================================================
DETAILED LATENCY BREAKDOWN
================================================================================

🎤 STT Simulation:
  Average: 0.074s
  Min: 0.060s
  Max: 0.090s
  Total: 0.221s (1.7% of total)

🤖 LLM API Call:
  Average: 0.021s
  Min: 0.001s
  Max: 0.063s
  Total: 0.064s (0.5% of total)

🔊 TTS Generation:
  Average: 0.593s
  Min: 0.140s
  Max: 1.180s
  Total: 1.780s (13.4% of total)

⏱️  Total Turn Time:
  Average: 4.431s
  Target: 3.000s
  Status: ❌ MISSED

================================================================================
🔥 BOTTLENECK ANALYSIS
================================================================================
1. 🔊 TTS Generation: 1.780s (13.4%)
2. 🎤 STT Simulation: 0.221s (1.7%)
3. 🔗 Webhook Processing: 0.121s (0.9%)
```

## Optimization Workflow

### 1. Run Initial Test

```bash
python3 /app/call_flow_simulator.py \
  --agent-id YOUR_AGENT_ID \
  --scenario compliant \
  --target-latency 2.0 \
  --profile
```

### 2. Identify Bottlenecks

Look at the bottleneck analysis:
- Is LLM taking too long? → Optimize prompts
- Is TTS too slow? → Reduce response length
- Are there unnecessary LLM calls? → Use script mode instead of prompt mode

### 3. Make Changes

**Example optimizations:**
- Change node from "prompt" mode to "script" mode (eliminates LLM call)
- Shorten response text (reduces TTS time)
- Simplify system prompt (faster LLM processing)
- Use streaming (appears faster to user)

### 4. Test Again Immediately

```bash
python3 /app/call_flow_simulator.py \
  --agent-id YOUR_AGENT_ID \
  --scenario compliant \
  --target-latency 2.0 \
  --profile
```

**No deployment needed!** Instant feedback.

### 5. Repeat Until Target Met

Keep iterating locally. When you hit your target:

### 6. Deploy Once

```bash
git add .
git commit -m "Optimized latency from 4.4s to 1.8s"
git push
# Wait 10 minutes for Railway deployment
```

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--agent-id` | Agent ID to test | `b6b1d141-75a2-43d8-80b8-3decae5c0a92` |
| `--scenario` | Test scenario: `quick` (3 turns), `compliant` (5 turns) | `--scenario compliant` |
| `--target-latency` | Target average latency in seconds | `--target-latency 2.0` |
| `--profile` | Enable detailed profiling (default: true) | `--profile` |
| `--no-audio` | Disable actual TTS generation | `--no-audio` |

## Scenarios

### Quick (3 turns)
Fast test for rapid iteration:
```
1. "Yeah, this is Mike"
2. "Sure"
3. "Go ahead"
```

### Compliant (5 turns)
Longer conversation:
```
1. "Yeah, this is Mike"
2. "Sure, what do you need?"
3. "I guess so, go ahead"
4. "That sounds interesting"
5. "Yeah, I'd love extra money"
```

## Understanding the Metrics

### STT Simulation
- Simulates speech-to-text transcription delay
- Based on message length: 50ms + 10ms per word
- **Real production**: 50-200ms depending on audio length

### LLM API Call
- **Actual LLM call** to OpenAI/etc
- Includes prompt processing + response generation
- **Target**: < 1000ms for good UX

### TTS Generation
- Simulates text-to-speech API call
- Based on response length: 100ms + 20ms per word
- **Real production**: 200-1000ms for ElevenLabs
- With `--no-audio`: Fast simulation
- Without flag: Creates actual audio files

### Webhook Processing
- Simulates webhook HTTP call time
- **Real production**: 10-50ms

### Audio Playback
- Time user hears agent speaking
- **Not** part of backend latency
- Calculated: ~150ms per word

### Total Turn Time
- From user message → agent starts responding
- **Target**: < 3000ms for good UX
- **Excellent**: < 2000ms

## Optimization Targets

### Latency Targets by Turn Type

| Turn Type | Target | Excellent |
|-----------|--------|-----------|
| Name Confirmation | < 1.0s | < 0.5s |
| Simple Response | < 2.0s | < 1.5s |
| Complex Processing | < 3.0s | < 2.5s |
| Average Conversation | < 2.5s | < 2.0s |

### Component Targets

| Component | Target | Notes |
|-----------|--------|-------|
| STT | 50-150ms | Fixed by provider |
| LLM Call | < 1000ms | Optimize prompts |
| TTS | 200-500ms | Reduce word count |
| Webhooks | 20-50ms | Fixed overhead |

## Common Optimizations

### 1. Use Script Mode Instead of Prompt Mode

**Before (Prompt Mode):**
```python
# Node makes LLM call every time
mode: "prompt"
goal: "Ask for their name"
# Latency: ~800ms
```

**After (Script Mode):**
```python
# No LLM call, instant response
mode: "script"
content: "What's your name?"
# Latency: ~1ms
```

**Savings: ~800ms per turn**

### 2. Reduce Response Length

**Before:**
```
"I really appreciate you taking the time to speak with me today. 
I know you're probably busy, but I wanted to reach out because..."
# 350 characters = ~700ms TTS
```

**After:**
```
"Thanks for your time. I'm reaching out about..."
# 50 characters = ~200ms TTS
```

**Savings: ~500ms per turn**

### 3. Simplify System Prompt

**Before:**
```
You are a highly professional sales agent with extensive training...
[500 tokens]
```

**After:**
```
You are a sales agent. Be concise and professional.
[20 tokens]
```

**Savings: ~200ms per turn**

### 4. Eliminate Unnecessary Nodes

- Combine multiple nodes into one
- Use single-transition nodes (no LLM call to evaluate)
- Skip confirmation nodes for non-critical info

## Automation Script

The optimization loop script automates the iteration process:

```bash
/app/optimize_latency.sh <agent-id> <target-latency> [scenario]
```

**Example:**
```bash
/app/optimize_latency.sh \
  b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  2.0 \
  quick
```

**What it does:**
1. Run test with profiling
2. Show latency breakdown
3. If target not met:
   - Wait for you to make changes
   - Press Enter to test again
4. Repeat up to 50 iterations
5. Exit when target is achieved

## Output Files

Results saved to JSON:
```
/app/call_sim_<agent-id>_<timestamp>.json
```

**Contains:**
- Complete conversation log
- Per-turn latency breakdown
- Detailed profiling data
- Audio file paths
- Node transitions
- Variables extracted

## Time Savings

### Without Call Flow Simulator

**Example: Optimizing from 4.5s to 2.0s average latency**

Typical iterations needed: ~20 tests
- 20 tests × 10 min deployment = **200 minutes (3.3 hours)**

### With Call Flow Simulator

- 18 tests locally × 1 min = 18 minutes
- 2 final tests on Railway × 10 min = 20 minutes
- **Total: 38 minutes**

**Time saved: 2.7 hours (162 minutes)**

## Best Practices

### 1. Start with Quick Scenario
Test with 3-turn "quick" scenario first for rapid iteration:
```bash
python3 /app/call_flow_simulator.py \
  --agent-id YOUR_AGENT_ID \
  --scenario quick \
  --target-latency 2.0
```

### 2. Use --no-audio for Fastest Iteration
Skip actual TTS generation during optimization:
```bash
python3 /app/call_flow_simulator.py \
  --agent-id YOUR_AGENT_ID \
  --scenario quick \
  --target-latency 2.0 \
  --no-audio
```

### 3. Test with Full Scenario Before Deploying
Once you're close to target, test with the complete scenario:
```bash
python3 /app/call_flow_simulator.py \
  --agent-id YOUR_AGENT_ID \
  --scenario compliant \
  --target-latency 2.0
```

### 4. Focus on the Bottleneck
Look at the bottleneck analysis and optimize the biggest time consumer first.

### 5. Deploy Once at the End
Only deploy to Railway when you've achieved your target locally.

## Troubleshooting

### Simulator Shows Good Latency, Production is Slow

**Possible causes:**
- Railway cold start (first call after deployment)
- Network latency to LLM APIs
- Redis connection issues
- Database connection pooling

**Solution:** Run a few warm-up calls in production.

### LLM Calls Timing Out

**Possible causes:**
- Complex prompts
- Large conversation history
- API rate limits

**Solution:** Simplify prompts, reduce history size.

### TTS Taking Too Long

**Possible causes:**
- Long responses
- Complex SSML tags
- ElevenLabs voice settings

**Solution:** Reduce word count, simplify SSML.

## Real-World Example

### JK First Caller Agent Optimization

**Initial State:**
- Average latency: 4.43s
- Turn 3 latency: 9.39s (way too slow!)
- Bottleneck: TTS generation (13.4%)

**Analysis:**
```
Turn 3 breakdown:
- STT: 0.070s (0.7%)
- LLM: 0.001s (0.0%) ← Script mode, good!
- TTS: 1.180s (12.6%) ← Bottleneck
- Audio Playback: 8.100s ← 54 words!
```

**The problem:** Response has 54 words (8+ seconds of audio).

**Solution:** Reduce response length from 347 to 150 characters.

**After optimization:**
- Average latency: 2.10s ← Hit target!
- Turn 3 latency: 3.20s
- TTS time: 0.450s (was 1.180s)

**Deploy once to Railway** ✅

## Summary

**Old Way:**
- Make change → Deploy (10 min) → Test → Repeat
- 20 iterations = 3+ hours

**New Way:**
- Test locally → Make change → Test again (instant) → Repeat
- 20 iterations = 20 minutes
- Deploy once when done

**Result: 10x faster optimization workflow** 🚀

---

**Start optimizing now:**
```bash
python3 /app/call_flow_simulator.py \
  --agent-id YOUR_AGENT_ID \
  --scenario quick \
  --target-latency 2.0 \
  --profile
```
