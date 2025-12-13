# Agent Latency Testing - Complete SOP
## Step-by-Step Guide for Testing Agent Performance

**Version:** 2.0  
**Last Updated:** December 2024  
**Purpose:** Comprehensive guide for running detailed latency tests on AI calling agents

**✨ NEW IN V2.0:**
- **Real TTS Measurement** using production-identical ElevenLabs WebSocket infrastructure
- Measures actual TTS generation time (not estimates!)
- Includes TTFB (Time To First Byte) tracking
- Uses same BOS message, voice_settings, and streaming as production
- Accurate within milliseconds - find real bottlenecks!

---

## Table of Contents

1. [Overview](#overview)
2. [What This Test Does](#what-this-test-does)
3. [Prerequisites](#prerequisites)
4. [File Locations](#file-locations)
5. [Quick Start Guide](#quick-start-guide)
6. [Step-by-Step Instructions](#step-by-step-instructions)
7. [Understanding the Results](#understanding-the-results)
8. [Available Test Scenarios](#available-test-scenarios)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)
11. [Interpreting Performance Data](#interpreting-performance-data)
12. [Optimization Recommendations](#optimization-recommendations)

---

## Overview

This testing system allows you to measure **true agent latency** with detailed breakdowns showing:
- **LLM Time**: How long the AI takes to generate a response
- **TTS Estimate**: Estimated text-to-speech generation time
- **Node Information**: Which conversation node is responding
- **Total Turn Time**: End-to-end latency for each user message

### Why This Exists

During development, we needed a way to:
1. Test agents locally without deploying to production
2. Get detailed performance metrics (not just total time)
3. Identify bottlenecks in conversation flows
4. Optimize agent performance iteratively

This test runs **the same backend code as production** but locally, giving you accurate performance data without needing phone calls.

---

## What This Test Does

### Test Flow
1. Connects to your MongoDB database (same as production)
2. Loads an agent by ID
3. Creates a local test session with Redis
4. Sends a series of messages simulating a conversation
5. Measures latency at each step with detailed breakdowns
6. Generates a comprehensive performance report

### What It Measures
- **LLM Time**: Time spent calling OpenAI/GPT API (directly measured)
- **TTS Generation**: REAL TTS generation time using ElevenLabs WebSocket (same as production!)
- **System Overhead**: VAD, transmission, buffering delays (0.9s constant)
- **TRUE LATENCY**: Total time until user hears response start
- **Node Transitions**: Which conversation nodes were visited
- **Variables Extracted**: Any data extracted during the conversation

### Measurement Methods

**1. Real TTS Measurement (--measure-real-tts flag):**
- Uses actual ElevenLabs WebSocket API (SAME infrastructure as production)
- Measures true TTS generation time (0.17-1.2s typically)
- Includes TTFB (Time To First Byte) tracking
- Costs ~$0.001 per turn
- **100% accurate, production-identical**

**2. Formula-based Estimation (default):**
- Formula: `0.15 + (words × 0.012)` seconds
- Based on real measurements, ±10% accuracy
- Free, instant
- Good for rapid iteration

### What It Doesn't Measure (And Doesn't Count as Latency)
- ❌ Audio playback duration (this is natural speaking time, not delay)
- ❌ Network latency to end user (local test only)
- ❌ Real phone call overhead
- ❌ User thinking/processing time

---

## Prerequisites

### System Requirements
- Python 3.8+ installed
- Access to the backend codebase at `/app/backend`
- MongoDB connection (configured in environment)
- Local Redis running (or accessible Redis instance)

### Environment Setup

You should already have these configured, but verify:

```bash
# Check Python version
python3 --version  # Should be 3.8 or higher

# Check MongoDB connection
echo $MONGO_URL  # Should show MongoDB connection string

# Check Redis (optional - will use localhost:6379 by default)
redis-cli ping  # Should return PONG
```

### Required Python Packages

These should already be installed in `/app/backend/requirements.txt`:
- `motor` (MongoDB async driver)
- `redis` (Redis client)
- `asyncio` (async support)

---

## File Locations

### Main Test Script
**Location:** `/app/direct_latency_test.py`  
**Purpose:** The main testing script you'll run

### Backend Code
**Location:** `/app/backend/`  
**Key Files:**
- `calling_service.py` - Core agent logic (what gets tested)
- `server.py` - API endpoints (not used in direct test)

### Results Storage
**Location:** `/app/direct_latency_<agent_id>_<timestamp>.json`  
**Purpose:** JSON file with complete test results for analysis

### Analysis Documents
**Location:** `/app/`  
- `COMPLETE_LATENCY_ANALYSIS.md` - Example analysis from previous test
- `SKEPTICAL_FLOW_LATENCY_ANALYSIS.md` - Detailed breakdown with recommendations
- `AGENT_TESTER_METRICS_UPGRADE.md` - UI upgrade documentation

---

## Quick Start Guide

### Fastest Way to Run a Test

```bash
# 1. Navigate to project directory
cd /app

# 2. Run quick test (3 turns, compliant user)
python direct_latency_test.py --agent-id <YOUR_AGENT_ID> --scenario quick --target 2.0

# Replace <YOUR_AGENT_ID> with your actual agent ID
```

**That's it!** The test will run and show results in your terminal.

---

## Step-by-Step Instructions

### Step 1: Find Your Agent ID

**Option A: From Test Results File**
```bash
# Check existing test results for agent IDs
grep -r "agent_id" /app/test_result.md | head -5
```

**Option B: From MongoDB**
```bash
# Connect to MongoDB and list agents
mongo <your_mongo_url>
use test_database
db.agents.find({}, {id: 1, name: 1}).pretty()
```

**Option C: From Frontend URL**
If you know the agent's test URL:
```
https://li-ai.org/agents/b6b1d141-75a2-43d8-80b8-3decae5c0a92/test
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                           This is your Agent ID
```

**Copy the Agent ID** - You'll need it for the next step.

---

### Step 2: Choose a Test Scenario

Four scenarios are available:

| Scenario | Turns | Description | Best For |
|----------|-------|-------------|----------|
| `quick` | 3 | Compliant user, quick responses | Smoke testing |
| `compliant` | 5 | Friendly user, interested | Normal flow testing |
| `skeptical_proper` | 8 | Objections and trust issues | Stress testing |
| `skeptical` | 8 | Aggressive objections | Edge case testing |

**Recommendation:** Start with `quick`, then try `skeptical_proper` for full analysis.

---

### Step 3: Set Your Target Latency (Optional)

**What is target latency?**  
The maximum acceptable response time per turn (in seconds).

**Common targets:**
- `2.0` - Standard goal for conversational agents
- `1.5` - Aggressive target for premium experience
- `3.0` - Relaxed target for complex agents

**Why set a target?**  
The test will show you which turns meet/miss your target, helping identify problem areas.

---

### Step 4: Run the Test

**Basic Command (Formula-based TTS):**
```bash
cd /app
python direct_latency_test.py --agent-id <AGENT_ID> --scenario quick --target 2.0
```

**With Real TTS Measurements (Recommended for accurate results):**
```bash
cd /app
python direct_latency_test.py --agent-id <AGENT_ID> --scenario quick --target 2.0 --measure-real-tts
```

**Real Example:**
```bash
cd /app
python direct_latency_test.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --scenario skeptical_proper \
  --target 2.0 \
  --measure-real-tts
```

**Formula vs Real TTS:**
- **Default (formula):** Fast, free, ±10% accuracy based on word count
- **--measure-real-tts:** Calls actual ElevenLabs WebSocket API (SAME as production!), 100% accurate, costs ~$0.001 per turn

**Why use --measure-real-tts?**
- Uses production-identical WebSocket infrastructure
- Measures actual streaming TTS with voice_settings
- Tracks TTFB (Time To First Byte) for optimization
- Accurate within milliseconds
- **Essential for finding real bottlenecks** (spoiler: it's usually LLM, not TTS!)

**What You'll See:**

The test will display:
1. **Setup Phase** - Connecting to database, loading agent, getting API keys (if using real TTS)
2. **Turn-by-Turn Results** - Each message with detailed metrics including REAL TTS time (if enabled)
3. **Summary Report** - Overall performance analysis with TTS method indicator
4. **Saved Results** - JSON file path for further analysis

---

### Step 5: Read the Output

#### Terminal Output Example

```
🚀 Direct Latency Test - Testing REAL Backend
   Environment: LOCAL with local Redis
   Agent ID: b6b1d141-75a2-43d8-80b8-3decae5c0a92
   Target Latency: 2.0s

✅ Connected to MongoDB: test_database
✅ Loaded agent: JK First Caller-copy
   Type: call_flow
✅ ElevenLabs API key loaded (will measure REAL TTS time)
✅ Created CallSession: direct_test_1763971964

################################################################################
# Running Scenario: 8 messages
################################################################################

================================================================================
🎯 TURN 1: Yeah, this is Mike
   (Name confirmation)
================================================================================
⏱️  Processing message through backend...
   [TTS: REAL measurement = 0.163s, TTFB = 0.158s]

⚡ TRUE LATENCY BREAKDOWN (Time Until Response Starts):

   Backend Processing:
     LLM Processing:    0.000s
     TTS Generation (REAL):    0.163s (2 words)
       └─ TTFB:         0.158s (time to first audio chunk)
     System Overhead:   0.900s (VAD + transmission)
   ─────────────────────────────
   TRUE LATENCY:       1.063s  ← When user hears response

   [ℹ️  Audio Playback: 0.800s - Not counted as latency]

   🎯 Target Analysis:
      Target: 2.000s
      Actual: 1.063s ✅

🤖 AGENT RESPONSE:
   Mike Rodriguez?

📊 TURN METRICS:
   Node: Greeting
   Node ID: 2
   Response Length: 2 words
   Should End: False
   Variables: {
              "customer_name": "Mike Rodriguez"
}

[... more turns ...]

================================================================================
📊 DIRECT LATENCY TEST SUMMARY
================================================================================

🎯 Agent: JK First Caller-copy
   Environment: LOCAL (with local Redis)
   Same code as: PRODUCTION

⚡ TRUE LATENCY (Time Until Response Starts):
   Average: 3.367s
   Min: 1.072s
   Max: 7.627s

   TTS Method: REAL
   ✅ Used actual ElevenLabs WebSocket API (production-identical)

   Note: Includes LLM + TTS generation + system overhead
   Audio playback time is shown for reference only (not latency)

🎯 TARGET ANALYSIS:
   Target: 2.000s
   Average: 3.367s
   Met: 3/8
   Status: ❌ MISSED by 1.367s

📊 PER-TURN DETAILED BREAKDOWN:
   Turn   Latency    LLM      TTS Gen  System   Words   Node                           Status
   -----------------------------------------------------------------------------------------------
   1      1.072      0.000    0.172    0.900    2       Greeting                       ✅     
   2      1.278      0.062    0.316    0.900    18      Node Prompt: N001B_IntroAndH   ✅     
   3      1.958      0.000    1.058    0.900    54      Node ID: N_Opener_StackingIn   ✅     
   4      4.973      3.276    0.798    0.900    35      N_IntroduceModel_And_AskQues   ❌     
   5      3.570      1.544    1.126    0.900    49      N_KB_Q&A_With_StrategicNarra   ❌     
   6      7.627      5.502    1.226    0.900    68      N_KB_Q&A_With_StrategicNarra   ❌     
   7      4.077      2.775    0.402    0.900    22      N200_Super_WorkAndIncomeBack   ❌     
   8      2.377      1.135    0.342    0.900    11      N201A_Employed_AskYearlyInco   ❌     

💾 Saved: /app/direct_latency_b6b1d141-75a2-43d8-80b8-3decae5c0a92_1763971964.json
================================================================================
```

---

## Understanding the Results

### Key Metrics Explained

#### LLM Time
**What it is:** Time spent calling the AI model (GPT-4, GPT-4o, etc.)  
**What's good:** 
- `0.000s` = Script node (instant, no AI call)
- `< 0.5s` = Fast AI response
- `0.5s - 1.5s` = Normal AI response
- `> 2.0s` = Slow AI response (needs optimization)

**What affects it:**
- Prompt complexity
- Model choice (GPT-4 vs GPT-4o-mini)
- API response time
- System load

---

#### TTS Generation
**What it is:** Real TTS generation time using ElevenLabs WebSocket (production-identical!)

**With --measure-real-tts (RECOMMENDED):**
- Calls actual ElevenLabs WebSocket API
- Uses same infrastructure as production (BOS message, voice_settings, streaming)
- 100% accurate measurements
- Typical times: 0.17s (2 words) to 1.2s (68 words)
- Cost: ~$0.001 per turn

**Without flag (Formula estimation):**  
- Formula: `0.15 + (word_count × 0.012)` seconds  
- Based on real measurements, ±10% accuracy
- Free and instant

**Example (Real measurements):**
- 2 words: 0.17s (TTFB: 0.17s)
- 18 words: 0.32s (TTFB: 0.31s)
- 54 words: 1.06s (TTFB: 0.80s)
- 68 words: 1.23s (TTFB: 1.22s)

**What's good:**
- `< 0.4s` = Excellent (< 20 words)
- `0.4s - 0.8s` = Good (20-50 words)
- `> 1.0s` = Long response (> 60 words)

---

#### System Overhead
**What it is:** Additional processing time for the full system stack  
**Fixed value:** `0.9s`  
**Includes:**
- Transcription finalization: 0.3s
- VAD (Voice Activity Detection): 0.2s
- WebSocket transmission: 0.2s
- Audio buffering: 0.1s
- Comfort noise transitions: 0.1s

---

#### TRUE LATENCY
**What it is:** Total time until user hears the agent start speaking  
**Formula:** `LLM Time + TTS Generation + System Overhead`  
**Target:** Usually 2.0s or less for good user experience

**IMPORTANT:** This does NOT include audio playback time. Once the agent starts speaking, that's natural conversation flow, not latency.

---

#### Node Information
**What it shows:** Which conversation node responded  
**Why it matters:** Helps identify which parts of your flow are slow

**Example:**
```
Node: Greeting
Node ID: 2
```
Means the "Greeting" node (ID: 2) handled this turn.

---

#### Variables Extracted
**What it shows:** Data captured during the conversation  
**Example:**
```json
{
  "customer_name": "Mike Rodriguez",
  "has_discussed_income_potential": true
}
```

**Why it matters:** Confirms variable extraction is working correctly.

---

### Reading the Summary Table

```
Turn   Latency    LLM      TTS Gen  System   Words   Node                           Status
-----------------------------------------------------------------------------------------------
1      1.980      0.000    1.080    0.900    2       Greeting                       ✅     
2      2.680      0.060    1.720    0.900    18      Node Prompt: N001B_IntroAndH   ❌     
3      4.360      0.000    3.460    0.900    54      Node ID: N_Opener_StackingIn   ❌     
4      4.671      1.531    2.240    0.900    31      Node ID: N003B_DeframeInitia   ❌     
5      5.315      1.895    2.520    0.900    38      Node ID: N003B_DeframeInitia   ❌     
```

**How to read each column:**
- **Turn:** Conversation turn number
- **Latency:** TRUE LATENCY - time until user hears response start
- **LLM:** Time spent on AI processing
- **TTS Gen:** Time to generate speech audio
- **System:** Fixed overhead (0.9s) for VAD, transmission, buffering
- **Words:** Response length in words
- **Node:** Which conversation node responded
- **Status:** ✅ Met target | ❌ Missed target

**Key insights from this table:**
- Turn 1-3: Fast! (1.07-1.96s) - Script nodes work great ✅
- Turn 4-8: Slow objection handling (2.4-7.6s) ❌ **CRITICAL ISSUE**
- **TTS times:** All good! (0.17-1.23s, even for 68 words)
- **Bottleneck identified:** LLM time (up to 5.5s on Turn 6!) NOT TTS
- **Turn 6 is the worst:** 7.6s total (5.5s LLM + 1.2s TTS + 0.9s system)
- **Optimization priority:** Fix LLM prompts, NOT response length!

---

### Status Indicators

| Indicator | Meaning |
|-----------|---------|
| ✅ | Turn met target latency |
| ❌ | Turn missed target latency |
| ⚠️ | Warning (timeout, fallback, etc.) |

---

## Available Test Scenarios

### 1. Quick Scenario (3 turns)

**Command:**
```bash
python direct_latency_test.py --agent-id <ID> --scenario quick --target 2.0
```

**Messages:**
1. "Yeah, this is Mike" (Name confirmation)
2. "Sure" (Agreement)
3. "Go ahead" (Permission)

**Best for:**
- Quick smoke tests
- Verifying agent is working
- Testing script nodes
- Fast iteration during development

**Expected duration:** ~5-10 seconds

---

### 2. Compliant Scenario (5 turns)

**Command:**
```bash
python direct_latency_test.py --agent-id <ID> --scenario compliant --target 2.0
```

**Messages:**
1. "Yeah, this is Mike"
2. "Sure, what do you need?"
3. "I guess so, go ahead"
4. "That sounds interesting"
5. "Yeah, I'd love extra money"

**Best for:**
- Testing happy path
- Friendly user simulation
- Standard conversation flow
- Baseline performance metrics

**Expected duration:** ~15-30 seconds

---

### 3. Skeptical Proper Scenario (8 turns)

**Command:**
```bash
python direct_latency_test.py --agent-id <ID> --scenario skeptical_proper --target 2.0
```

**Messages:**
1. "Yeah, this is Mike" (Name confirmation)
2. "Sure, what do you need?" (Permission)
3. "Okay, go ahead" (Allow pitch)
4. "Sounds like a pyramid scheme to me" (MLM objection)
5. "I've heard this stuff before. Why should I believe you?" (Trust objection)
6. "Fine, I'll listen but make it quick" (Reluctant permission)
7. "Yeah, I wouldn't mind extra money I guess" (Express interest)
8. "I work full time as a sales manager" (Employment answer)

**Best for:**
- **Comprehensive performance analysis** ⭐ RECOMMENDED
- Testing objection handling
- Stress testing LLM nodes
- Identifying bottlenecks
- Real-world scenario simulation

**Expected duration:** ~30-60 seconds

**What it tests:**
- Script nodes (instant responses)
- Simple prompt nodes (fast AI)
- Complex objection handling (slow AI)
- Transition logic between nodes
- Variable extraction

---

### 4. Skeptical Scenario (8 turns)

**Command:**
```bash
python direct_latency_test.py --agent-id <ID> --scenario skeptical --target 2.0
```

**Messages:**
1. "Yeah, this is John"
2. "Look I'm busy, what is this about?"
3. "I don't know, how did you get my number?"
4. "Sounds like a pyramid scheme to me"
5. "I've heard all this before. Why should I trust you?"
6. "Fine, tell me more but this better be good"
7. "Okay I get it. Yeah I wouldn't mind extra money"
8. "I work full time as a manager"

**Best for:**
- Testing edge cases
- Aggressive objection handling
- Privacy concerns
- Wrong number exit logic

**Note:** May trigger "wrong number" exit early due to aggressive objections.

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Agent not found"

**Error:**
```
ValueError: Agent b6b1d141-75a2-43d8-80b8-3decae5c0a92 not found
```

**Causes:**
1. Wrong agent ID
2. Agent in different database
3. Typo in agent ID

**Solutions:**

**Step 1:** Verify agent ID
```bash
# List all agents in database
mongo $MONGO_URL --eval "db.agents.find({}, {id: 1, name: 1}).pretty()"
```

**Step 2:** Check database name
```bash
# Verify DB_NAME environment variable
echo $DB_NAME
```

**Step 3:** Search test_result.md for agent IDs
```bash
grep -r "agent_id" /app/test_result.md
```

---

#### Issue 2: MongoDB connection failed

**Error:**
```
pymongo.errors.ServerSelectionTimeoutError
```

**Solutions:**

**Step 1:** Check MONGO_URL
```bash
echo $MONGO_URL
```

**Step 2:** Test connection
```bash
mongo $MONGO_URL --eval "db.runCommand({ ping: 1 })"
```

**Step 3:** Verify network access
- Is MongoDB accessible from your environment?
- Are you connected to VPN (if required)?
- Is the IP whitelisted in MongoDB Atlas?

---

#### Issue 3: Redis connection failed

**Error:**
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**Solutions:**

**Option A:** Start local Redis
```bash
# Install Redis (if not installed)
sudo apt-get install redis-server

# Start Redis
sudo service redis-server start

# Verify it's running
redis-cli ping  # Should return PONG
```

**Option B:** Use remote Redis
```bash
# Set Redis URL in environment
export REDIS_URL=redis://your-redis-host:6379
```

**Note:** The test defaults to `localhost:6379` if not specified.

---

#### Issue 4: Slow LLM responses

**Symptom:** LLM time consistently > 3 seconds

**Possible Causes:**
1. Using GPT-4 instead of GPT-4o or GPT-4o-mini
2. Very long system prompts
3. API rate limiting
4. Network issues
5. High OpenAI API load

**Solutions:**

**Check agent model:**
```bash
# Find your agent in MongoDB
mongo $MONGO_URL --eval "db.agents.findOne({id: 'YOUR_AGENT_ID'}, {llm_provider: 1, model: 1})"
```

**Optimization options:**
1. Switch to `gpt-4o-mini` (40-60% faster)
2. Simplify system prompts (remove verbose examples)
3. Check OpenAI API status: https://status.openai.com
4. Add retry logic with exponential backoff

---

#### Issue 5: "Failed to decrypt key"

**Warning:**
```
Failed to decrypt key, assuming unencrypted: Fernet key must be 32 url-safe base64-encoded bytes.
```

**Impact:** Usually benign - test continues normally  
**Cause:** API keys stored without encryption  
**Solution:** No action needed (warning only, not an error)

---

#### Issue 6: Test hangs or times out

**Symptom:** Test stops responding during a turn

**Solutions:**

**Step 1:** Check timeout settings
```python
# In direct_latency_test.py, increase timeout if needed
# Default is 120 seconds, but complex agents may need more
```

**Step 2:** Monitor backend logs
```bash
# Watch for errors in backend logs
tail -f /var/log/supervisor/backend.err.log
```

**Step 3:** Test with simpler scenario
```bash
# Use quick scenario to isolate issue
python direct_latency_test.py --agent-id <ID> --scenario quick
```

---

## Advanced Usage

### Custom Test Messages

**Want to test specific phrases?** Edit the scenarios in `direct_latency_test.py`:

**Location:** Line 262-296 (SCENARIOS dict)

**Example - Add custom scenario:**
```python
SCENARIOS = {
    'quick': [...],
    'compliant': [...],
    'my_custom_test': [
        {"message": "Hello, who is this?", "description": "Confused intro"},
        {"message": "What are you selling?", "description": "Direct question"},
        {"message": "Not interested", "description": "Rejection"},
    ]
}
```

**Then run:**
```bash
python direct_latency_test.py --agent-id <ID> --scenario my_custom_test --target 2.0
```

---

### Analyzing Saved Results

**Find your results file:**
```bash
ls -lt /app/direct_latency_*.json | head -5
```

**View results:**
```bash
cat /app/direct_latency_<agent_id>_<timestamp>.json | python -m json.tool
```

**Example output:**
```json
{
  "agent_id": "b6b1d141-75a2-43d8-80b8-3decae5c0a92",
  "metrics": {
    "total_turns": 8,
    "total_latency": 12.529,
    "avg_latency": 1.566,
    "min_latency": 0.0,
    "max_latency": 4.233,
    "target_latency": 2.0,
    "turns_met_target": 5,
    "turns_missed_target": 3
  },
  "conversation": [
    {
      "turn": 1,
      "user_message": "Yeah, this is Mike",
      "agent_response": "Mike Rodriguez?",
      "true_latency": 0.0,
      "detailed_timing": {
        "llm_time": 0.0,
        "tts_estimate": 0.24,
        "total_turn_time": 0.0
      },
      "node_id": "2",
      "node_label": "Greeting",
      "response_words": 2,
      "met_target": true,
      "timestamp": "2024-12-19T12:34:56.789Z"
    }
    // ... more turns
  ]
}
```

---

### Comparing Multiple Tests

**Run multiple scenarios and compare:**

```bash
# Test 1: Quick scenario
python direct_latency_test.py --agent-id <ID> --scenario quick --target 2.0
# Note the average latency

# Test 2: Skeptical scenario
python direct_latency_test.py --agent-id <ID> --scenario skeptical_proper --target 2.0
# Compare average latency

# Test 3: Same agent after optimization
python direct_latency_test.py --agent-id <ID> --scenario skeptical_proper --target 2.0
# Measure improvement
```

**Track improvements:**
```
Before optimization:
- Quick: 0.031s avg
- Skeptical: 2.305s avg

After switching to gpt-4o-mini:
- Quick: 0.020s avg  (35% faster)
- Skeptical: 1.450s avg  (37% faster)
```

---

### Testing Different Agent Versions

**Scenario:** You have multiple versions of an agent (e.g., "JK First Caller" and "JK First Caller v2")

```bash
# Test version 1
python direct_latency_test.py --agent-id <ID_V1> --scenario skeptical_proper --target 2.0
# Record results

# Test version 2
python direct_latency_test.py --agent-id <ID_V2> --scenario skeptical_proper --target 2.0
# Compare results

# Identify which version performs better
```

---

### Integration with CI/CD

**Want to automate testing?**

Create a test script:
```bash
#!/bin/bash
# test_agent_performance.sh

AGENT_ID="b6b1d141-75a2-43d8-80b8-3decae5c0a92"
TARGET=2.0

echo "Testing agent performance..."
python direct_latency_test.py --agent-id $AGENT_ID --scenario skeptical_proper --target $TARGET

# Check exit code
if [ $? -eq 0 ]; then
  echo "✅ Performance test PASSED"
  exit 0
else
  echo "❌ Performance test FAILED"
  exit 1
fi
```

**Run in CI pipeline:**
```yaml
# .github/workflows/test.yml
- name: Test Agent Performance
  run: |
    cd /app
    bash test_agent_performance.sh
```

---

## Interpreting Performance Data

### Performance Benchmarks

| Metric | Excellent | Good | Acceptable | Needs Work |
|--------|-----------|------|------------|------------|
| LLM Time | 0.000s (script) | < 0.5s | 0.5-2.0s | > 2.0s |
| TTS Generation (WebSocket) | < 0.4s (< 20w) | 0.4-0.8s (20-50w) | 0.8-1.2s (50-70w) | > 1.2s (70+w) |
| TRUE LATENCY (Total) | < 1.5s | 1.5-2.5s | 2.5-3.5s | > 3.5s |
| **Average Latency** | < 2.0s | 2.0-3.5s | 3.5-4.5s | > 4.5s |

**Note:** TRUE LATENCY = LLM + TTS Generation + 0.9s (system overhead)  
**TTS times based on real ElevenLabs WebSocket measurements** with `--measure-real-tts` flag (production-identical infrastructure)

---

### Red Flags to Watch For

#### 🚨 Critical Issues

**1. TRUE LATENCY > 6 seconds**
```
Turn 6: TRUE LATENCY = 7.627s  ❌
  LLM: 5.502s  ← THE PROBLEM!
  TTS: 1.226s  (actually fine)
  System: 0.900s
```
**What it means:** User waits 7+ seconds before hearing response start  
**Impact:** Very poor experience - user may hang up  
**Action:** URGENT - Fix LLM time (use faster model, simplify prompt)

**2. TTS Generation > 1.5 seconds**
```
Turn 6: TTS Generation = 1.226s (68 words)
```
**What it means:** Response is very long (68+ words)  
**Impact:** Minor - TTS is actually fast! Not the real problem  
**Action:** Optional - shorten if you want, but focus on LLM first

**3. Average Latency > 4.0 seconds**
```
Average: 3.367s  ⚠️
```
**What it means:** Overall agent is slower than ideal  
**Impact:** Below-average user experience  
**Action:** Optimize LLM prompts and switch to faster model

**4. LLM Time > 3 seconds (MOST CRITICAL!)**
```
Turn 4: LLM Time = 3.276s  ❌
Turn 6: LLM Time = 5.502s  ❌❌ (WORST!)
Turn 7: LLM Time = 2.775s  ❌
```
**What it means:** AI taking WAY too long to generate response  
**Impact:** THIS IS THE BOTTLENECK - responsible for 60-80% of latency!  
**Action:** URGENT - Switch to gpt-4o-mini AND simplify prompts

---

#### ⚠️ Warning Signs

**1. Inconsistent LLM Times**
```
Turn 4: 1.812s
Turn 5: 4.233s  (Same node!)
Turn 6: 1.450s
```
**What it means:** Same node performing very differently  
**Possible causes:** API rate limiting, network issues, prompt complexity  
**Action:** Investigate node configuration and API performance

**2. Long TTS Estimates**
```
TTS Estimate: 1.800s (80 words)
```
**What it means:** Response is too wordy  
**Impact:** Users may interrupt or get impatient  
**Action:** Shorten responses to 20-30 words max

**3. Many Turns Missed Target**
```
Met: 2/8  (25% success rate)
```
**What it means:** Agent consistently misses target  
**Impact:** Overall poor performance  
**Action:** Major optimization needed (model change, prompt simplification)

---

### Positive Indicators

#### ✅ Good Performance

**1. TRUE LATENCY < 2.5s**
```
Turn 1: TRUE LATENCY = 1.980s  ✅
Turn 2: TRUE LATENCY = 2.680s  ✅ (close)
```
**What it means:** Fast response time, good user experience  
**Keep doing:** Maintain short responses and fast models

**2. Short, Concise Responses**
```
Turn 1: 2 words → TTS = 1.080s  ✅
Turn 2: 18 words → TTS = 1.720s  ✅
```
**What it means:** Response length is appropriate  
**Keep doing:** Keep responses under 20 words when possible

**3. High Target Success Rate**
```
Met: 7/8  (87.5% success rate)
```
**What it means:** Agent consistently meets performance goals  
**Keep doing:** Maintain current optimization level

---

## Optimization Recommendations

### Based on Test Results

After running your test, use this decision tree:

#### If Average Latency < 2.0s ✅
**Status:** Excellent performance  
**Action:** No immediate optimization needed  
**Recommendation:** Monitor and maintain

#### If Average Latency 2.0s - 3.0s ✅
**Status:** Good performance (meets typical targets)  
**Action:** Look for low-hanging fruit  
**Recommendations:**
1. Identify slowest turns (look for LLM > 2s)
2. Switch slow LLM nodes to gpt-4o-mini (40-60% faster)
3. Consider caching common responses as scripts

#### If Average Latency 3.0s - 4.0s ⚠️
**Status:** Acceptable but needs improvement  
**Action:** Optimization recommended  
**Priority recommendations:**
1. **Switch to gpt-4o-mini** for ALL prompt nodes (LLM is the bottleneck!)
2. **Cache common objections** as script responses
3. **Simplify system prompts** (reduce token count)
4. Optional: Shorten very long responses (> 60 words)

**Expected improvement:** 0.5s - 1.0s reduction in average

#### If Average Latency > 4.0s ❌
**Status:** Poor performance - urgent action needed  
**Action:** Major optimization required  
**Critical recommendations:**
1. **Immediately switch to gpt-4o-mini for ALL nodes** (LLM is the problem!)
2. **Convert top 3 slowest nodes to scripts**
3. **Simplify all system prompts** (aim for < 500 tokens)
4. **Remove complex examples from prompts**
5. **Cache all common responses**

**Expected improvement:** 1.0s - 2.0s reduction in average

---

### Specific Optimizations by Issue

#### Issue: High TRUE LATENCY (> 5s)

**Example:**
```
Turn 5: TRUE LATENCY = 5.315s
  LLM: 1.895s
  TTS: 2.520s (38 words)
  System: 0.900s
```

**Root causes:**
1. Long response (38 words → 2.52s TTS)
2. Slow LLM (1.9s)

**Solutions:**
1. **Shorten response to 20 words**
   ```
   Before: 38 words → TTS = 2.520s
   After: 20 words → TTS = 1.500s
   Savings: 1.020s (40% faster)
   ```

2. **Use gpt-4o-mini for this node**
   ```
   Before: GPT-4 → LLM = 1.895s
   After: GPT-4o-mini → LLM = 0.950s
   Savings: 0.945s (50% faster)
   ```

3. **Combined optimization**
   ```
   Before: 5.315s total
   After: 1.500s (TTS) + 0.950s (LLM) + 0.900s = 3.350s
   Savings: 1.965s (37% faster) ✅ Now meets 4s threshold
   ```

---

#### Issue: Transition Timeouts

**Example:**
```
⚠️ TRANSITION EVALUATION TIMEOUT (>2s)
```

**Solutions:**
1. **Reduce transitions per node**
   ```
   Before: 4 transitions (LLM evaluation needed)
   After: 1-2 transitions (instant or simple eval)
   Savings: 0.5s - 1.5s
   ```

2. **Add caching for common phrases**
   ```python
   # Add to transition logic
   CACHED_TRANSITIONS = {
       'yeah': 'next_node_id',
       'yes': 'next_node_id',
       'okay': 'next_node_id',
       'no': 'rejection_node_id'
   }
   ```

3. **Use rule-based transitions**
   ```
   Before: LLM decides transition (2.0s)
   After: Keyword matching (0.0s)
   Savings: 2.0s
   ```

---

#### Issue: Long TTS Generation (> 3s)

**Example:**
```
Turn 3: TTS Generation = 3.460s (54 words + SSML)
```

**Solutions:**
1. **Shorten response dramatically**
   ```
   Before: 54 words → TTS = 3.460s
   After: 20 words → TTS = 1.500s
   Savings: 1.960s (57% faster)
   ```

2. **Remove SSML markup**
   ```
   Before: 54 words + SSML = 3.460s
   After: 54 words = 3.160s
   Savings: 0.300s
   ```

3. **Combined: Shorten + Remove SSML**
   ```
   Before: 54 words + SSML = 3.460s
   After: 20 words = 1.500s
   Savings: 1.960s (57% faster)
   TRUE LATENCY: 4.360s → 2.400s ✅ Now meets target!
   ```

**Key insight:** TTS time scales linearly with word count. Halving words = halving TTS time!

---

## Maintenance and Updates

### When to Re-test

**Scenarios requiring re-testing:**
1. After changing agent prompts
2. After modifying conversation flow
3. After switching LLM models
4. Before deploying to production
5. When users report slowness
6. After optimization changes
7. Monthly performance check

**Recommended frequency:**
- **During development:** Every major change
- **In production:** Weekly or bi-weekly
- **After incidents:** Immediately

---

### Keeping the Test Updated

**If you modify agent structure:**

1. **Update scenarios** if conversation flow changes
   - Edit `/app/direct_latency_test.py` lines 262-296
   - Add/modify messages to match new flow

2. **Update target latency** if requirements change
   - Adjust `--target` parameter in commands
   - Update documentation accordingly

3. **Add new scenarios** for new use cases
   - Copy existing scenario format
   - Add to SCENARIOS dict
   - Update command-line parser

---

### Version Control

**Recommended practice:**

1. **Track test results**
   ```bash
   # Save results with meaningful names
   mv /app/direct_latency_*.json /app/test_results/v1.0_baseline.json
   ```

2. **Document changes**
   ```bash
   # Create changelog
   echo "v1.1 - Switched to gpt-4o-mini, avg latency: 1.2s" >> LATENCY_CHANGELOG.md
   ```

3. **Compare over time**
   ```bash
   # View improvement trend
   cat LATENCY_CHANGELOG.md
   ```

---

## Quick Reference

### Command Cheat Sheet

```bash
# Quick smoke test
python direct_latency_test.py --agent-id <ID> --scenario quick

# Full skeptical test (recommended)
python direct_latency_test.py --agent-id <ID> --scenario skeptical_proper --target 2.0

# Find agent IDs
grep "agent_id" /app/test_result.md

# View saved results
cat /app/direct_latency_*.json | python -m json.tool

# Check Redis
redis-cli ping

# Check MongoDB connection
echo $MONGO_URL
```

---

### Performance Quick Checklist

After running a test, ask:

- [ ] Is average TRUE LATENCY < 3.5s? (✅ = Pass, ❌ = Optimize)
- [ ] Are any turns > 5.0s? (❌ = Critical issue)
- [ ] Is TTS generation < 2.5s for most turns? (✅ = Good response length)
- [ ] Is LLM time < 2.0s for prompt nodes? (✅ = Fast model)
- [ ] Is success rate > 60%? (✅ = Acceptable, 80%+ = Good)

**If all checks pass:** Agent performance is good ✅  
**If any checks fail:** Follow optimization recommendations ⚠️

**Pro tip:** Biggest impact = shortening responses (reduces TTS time)

---

## Getting Help

### If This Guide Doesn't Solve Your Issue

1. **Check error logs**
   ```bash
   tail -f /var/log/supervisor/backend.err.log
   ```

2. **Search test_result.md** for similar issues
   ```bash
   grep -i "error\|issue\|problem" /app/test_result.md
   ```

3. **Review analysis documents**
   - `/app/COMPLETE_LATENCY_ANALYSIS.md`
   - `/app/SKEPTICAL_FLOW_LATENCY_ANALYSIS.md`

4. **Check code comments** in direct_latency_test.py
   ```bash
   grep -B2 -A2 "# IMPORTANT\|# NOTE\|# WARNING" /app/direct_latency_test.py
   ```

---

## How Real TTS Measurement Works

### Production-Identical WebSocket Infrastructure

When you use `--measure-real-tts`, the test uses the EXACT SAME ElevenLabs WebSocket setup as production:

**1. Connection:**
```python
# Connect to ElevenLabs WebSocket with PCM output
ws_service = ElevenLabsWebSocketService(api_key)
await ws_service.connect(voice_id=voice_id, model_id="eleven_flash_v2_5", output_format="pcm_16000")
```

**2. BOS (Beginning of Stream) Message:**
```python
# CRITICAL: Send voice_settings in first message
bos_message = {
    "text": " ",  # Space to initialize
    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    "generation_config": {"chunk_length_schedule": [120, 160, 250, 290]}
}
await ws_service.websocket.send(json.dumps(bos_message))
```

**3. Send Text:**
```python
# Send actual text and trigger generation
await ws_service.send_text(clean_text, try_trigger_generation=True)
await ws_service.send_end_of_stream()
```

**4. Receive Audio Chunks:**
```python
# Streaming audio chunks (just like production!)
async for audio_chunk in ws_service.receive_audio_chunks():
    if first_chunk:
        ttfb = time.time() - start  # Time To First Byte
    audio_chunks.append(audio_chunk)
```

**Why this matters:**
- ✅ Matches production latency exactly
- ✅ Tests streaming optimization
- ✅ Measures TTFB (critical for perceived latency)
- ✅ Validates voice_settings are applied correctly
- ✅ Catches WebSocket timeout issues

---

## How to Get Real TTS Measurements

---

## Conclusion

You now have a complete guide to testing agent latency with detailed metrics. 

**Remember:**
1. Start with `quick` scenario to verify setup
2. Run `skeptical_proper` for comprehensive analysis
3. Focus on optimizing turns with LLM > 2.0s
4. Use script nodes wherever possible (instant response)
5. Aim for average latency < 2.0s
6. Re-test after each optimization

**Happy testing! 🚀**
