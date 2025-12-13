# LATENCY OPTIMIZATION STANDARD OPERATING PROCEDURE

**Version:** 2.0
**Last Updated:** 2025-11-24
**Status:** ACTIVE - This is the definitive guide
**Session Context:** Everything learned from 20+ hour optimization sessions

---

## TABLE OF CONTENTS

1. [Project Overview](#project-overview)
2. [Critical Context - Why This Approach](#critical-context)
3. [The 8 Critical Rules (NEVER Break These)](#the-8-critical-rules)
4. [Complete Testing Process](#complete-testing-process)
5. [MongoDB Agent Search](#mongodb-agent-search)
6. [API Key Retrieval](#api-key-retrieval)
7. [Running Baseline Tests](#running-baseline-tests)
8. [Analyzing Results](#analyzing-results)
9. [Optimization Strategies](#optimization-strategies)
10. [Transition Validation (MANDATORY)](#transition-validation)
11. [Common Mistakes (From This Session)](#common-mistakes)
12. [Troubleshooting Guide](#troubleshooting-guide)
13. [File Locations](#file-locations)
14. [Current Project Status](#current-project-status)

---

## PROJECT OVERVIEW

### Goal
Reduce voice agent latency to **1500ms or less** (average E2E response generation time)

### What We Measure
- **LLM Processing Time** (typically 700-1300ms)
- **TTS Generation Time** (typically 400-800ms)
- **KB Retrieval Time** (when triggered, 300-1000ms)
- **Transition Evaluation** (0-400ms)
- **Variable Extraction** (~700ms when needed)

### What We DON'T Measure
- ❌ Audio playback time (user listens to response)
- ❌ Network latency
- ❌ User speaking time
- ❌ STT processing (speech-to-text)

**Why?** We only measure what we can optimize (generation time), not what we can't control (playback, network).

### Current Agent
- **ID:** e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4
- **Name:** JK First Caller-optimizer
- **Database:** test_database (MongoDB Atlas)
- **User:** kendrickbowman9@gmail.com (ID: dcafa642-6136-4096-b77d-a4cb99a62651)
- **Structure:** 51 call_flow nodes
- **System Prompt:** 8,518 chars (unoptimized baseline)
- **Baseline Latency:** 1797ms (297ms OVER target)
- **Backup Location:** /app/new_agent_backup.json

---

## CRITICAL CONTEXT

### Why This Approach Exists

**The Problem (User's Experience):**

> "I spent 20+ hours doing that with you before and you still weren't able to fix the latency"

Previous workflow:
1. Make a change to agent
2. Deploy to production (wait 10 minutes)
3. Make real phone call
4. Download logs
5. Analyze logs
6. Try another change
7. Repeat...

**Result:** 20+ hours, still no fix

**Why It Failed:**
- Too slow (15-20 minutes per iteration)
- Only 3-4 attempts per hour
- Hard to isolate what changed
- Can't iterate quickly

### The New Approach

**Rapid Pre-Deployment Testing:**
- Use real system components (CallSession, LLM API, TTS API)
- Run locally BEFORE deployment
- Get results in 2-3 minutes
- Iterate 10x faster
- Close enough to production to be accurate

**User's Requirement:**
> "you need rapid fast pre-deployment but close to real deployment environment level testing and optimizations"

**Key Insight:**
- NOT actual phone calls (too slow)
- NOT simulation (inaccurate)
- Use real infrastructure components in test environment

---

## THE 8 CRITICAL RULES

### Rule 1: NEVER Simulate or Estimate

**What This Means:**
- ❌ Don't use `asyncio.sleep()` to fake TTS time
- ❌ Don't estimate latencies based on character counts
- ❌ Don't mock LLM responses
- ✅ Use actual `generate_tts_audio()` function
- ✅ Make real Grok API calls
- ✅ Generate real audio files

**User's Correction:**
> "Stop trying to estimate it - just generate audio files and connect to the webhook you are not allowed to try to simulate anything ever again"

**Why:**
- Estimates are always wrong
- TTS time varies by text content
- LLM time varies by prompt complexity
- Only real measurements are accurate

**Example of Failure:**
- Estimated TTS at 15 chars/second
- Reality: ElevenLabs Flash v2.5 is 100+ chars/second
- Off by 7-10x

### Rule 2: NEVER Optimize Before Baseline

**What This Means:**
- ❌ Don't make changes first
- ❌ Don't assume you know what's slow
- ✅ Run baseline test first
- ✅ Identify actual bottlenecks
- ✅ Then optimize targeted areas

**The Correct Order:**
1. Baseline test
2. Analyze results
3. Optimize specific issues
4. Test again
5. Compare

**Why:**
- You might optimize the wrong thing
- Can't measure improvement without baseline
- Wasted effort on non-bottlenecks

### Rule 3: NEVER Skip Transition Validation

**What This Means:**
- ✅ After optimization, check if transitions still work
- ✅ Compare node paths: baseline vs optimized
- ✅ Require 100% match (0 failures)
- ❌ Don't declare success on latency alone

**Real Example From This Session:**
- Achieved 1382ms latency (118ms under target) ✅
- But 22% of transitions were broken ❌
- Users would get wrong conversation paths
- **Result: COMPLETE FAILURE** - had to revert

**User's Question:**
> "And you verified the transitions still worked properly right? that was the biggest thing"

**The Rule:**
**Fast but broken = Failure**
**Must have BOTH speed AND correctness**

### Rule 4: NEVER Include Audio Playback Time

**What This Means:**
- ✅ Measure LLM processing time
- ✅ Measure TTS generation time
- ❌ Don't measure audio playback time
- ❌ Don't measure user listening time

**User's Correction:**
> "do not count playback as latency all of this should have been established in the sop"

**Why:**
- Playback happens AFTER response is ready
- Can't optimize playback time (fixed by audio length)
- Focus on what we can control (generation)

**What We Measure:**
- Time from user message received → audio file generated
- NOT: Time from user message → user hears response

### Rule 5: NEVER Use Simple/Mock Tests

**What This Means:**
- ❌ Don't test with just "Hello"
- ❌ Don't use 2-3 message conversations
- ✅ Test 8+ nodes deep
- ✅ Include objections (triggers KB)
- ✅ Test complex transitions

**Why Simple Tests Fail:**
- "Hello" returns scripted response (0ms)
- Short conversations don't trigger KB
- Don't test transition complexity
- Give unrealistic low latencies

**Real Example:**
- Simple test showed 1365ms ✅
- User suspicious: "No way the latency is that... Are you measuring this properly?"
- User was right - test was incomplete

**Required Test Depth:**
- Minimum 8 nodes per conversation
- Include objections (time, money, trust, skepticism)
- Trigger KB retrieval multiple times
- Test variable extraction
- Exercise complex transitions

### Rule 6: NEVER Use Wrong API Keys

**What This Means:**
- ✅ Check user's api_keys collection first
- ✅ Use user's Grok/OpenAI keys
- ❌ Don't default to Emergent LLM keys
- ❌ Don't assume keys are in user document

**User's Correction:**
> "there's a grok api key on the kendrickbowman9@gmail.com account in the mogonddb - don't use any emergent keys for this. Obviously it's there otherwise the agent could never make calls with that llm - duh"

**Common Mistake:**
- Looking in `user.api_keys` field (doesn't exist)
- Should look in `api_keys` collection

**Correct Approach:**
```python
keys = await db.api_keys.find({"user_id": USER_ID}).to_list(50)
for key in keys:
    if key.get('service_name') == 'grok' and key.get('is_active'):
        grok_key = key.get('api_key')
```

### Rule 7: NEVER Trust First Search Result

**What This Means:**
- ❌ Don't assume agent is missing if first search fails
- ✅ Check BOTH databases (test_database AND ai_calling_db)
- ✅ Try searching by name if ID fails
- ✅ Check both 'nodes' and 'call_flow' structures

**Common Issue:**
- Search in test_database → not found
- Assume agent doesn't exist
- Actually in ai_calling_db

**User Had to Remind Multiple Times:**
- I searched once, said "not found"
- User corrected me
- Had to explain MongoDB has multiple databases

### Rule 8: NEVER Update SOP Without User Corrections

**What This Means:**
- ✅ Document every mistake user catches
- ✅ Add user's exact corrections
- ✅ Update SOP immediately
- ❌ Don't make same mistake twice

**User's Feedback:**
> "I need the testing sop changed and updated so that a brand new agent that's never seen any of the context here could pick up a test - you have a lot of old invalid things in there and I had to remind you of a lot of stuff"

**This Section Exists Because:**
- User had to correct me 8+ times
- Each correction goes in SOP
- Future agents won't need same corrections

---

## COMPLETE TESTING PROCESS

### Step 1: Find the Agent in MongoDB

**Important:** MongoDB environment variables don't auto-load. Must export first.

```bash
cd /app/backend
export $(cat .env | grep MONGO_URL | xargs)
python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json

async def find_agent():
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("❌ MONGO_URL not set! Use export command first.")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    
    # Target agent
    agent_id = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
    agent_name = "JK First Caller-optimizer"
    
    print(f"🔍 Searching for agent...")
    print(f"   ID: {agent_id}")
    print(f"   Name: {agent_name}\n")
    
    # Check BOTH databases
    for db_name in ['test_database', 'ai_calling_db']:
        print(f"Checking {db_name}...")
        db = client[db_name]
        
        # Try by ID
        agent = await db.agents.find_one({"id": agent_id})
        if agent:
            agent.pop('_id', None)
            print(f"\n✅ FOUND BY ID in {db_name}!")
            print(f"   Name: {agent.get('name')}")
            print(f"   System Prompt: {len(agent.get('system_prompt', '')):,} chars")
            print(f"   Call Flow Nodes: {len(agent.get('call_flow', []))}")
            print(f"   Has 'nodes' structure: {'nodes' in agent}")
            print(f"   Has 'call_flow' structure: {'call_flow' in agent}")
            
            # Save backup
            with open('/app/agent_backup.json', 'w') as f:
                json.dump(agent, f, indent=2, default=str)
            print(f"\n💾 Backup saved to /app/agent_backup.json")
            return agent
        
        # Try by name
        agent = await db.agents.find_one({"name": agent_name})
        if agent:
            agent.pop('_id', None)
            print(f"\n✅ FOUND BY NAME in {db_name}!")
            print(f"   ID: {agent.get('id')}")
            print(f"   System Prompt: {len(agent.get('system_prompt', '')):,} chars")
            return agent
    
    print("\n❌ Agent not found in either database")
    print("\nTroubleshooting:")
    print("1. Check if agent ID is correct")
    print("2. Verify MONGO_URL is set correctly")
    print("3. Try listing all agents in both databases")
    return None

asyncio.run(find_agent())
EOF
```

**Common Issues:**
- "Agent not found" → Check both databases
- "MONGO_URL not set" → Use export command
- "Connection timeout" → Check MongoDB Atlas whitelist

### Step 2: Get API Keys

**Critical:** API keys are in a SEPARATE collection, NOT in user document.

```bash
cd /app/backend
export $(cat .env | grep MONGO_URL | xargs)
python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def get_api_keys():
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    user_id = "dcafa642-6136-4096-b77d-a4cb99a62651"
    
    print(f"🔑 Getting API keys for user {user_id}...\n")
    
    # Get from api_keys collection
    keys = await db.api_keys.find({"user_id": user_id}).to_list(length=50)
    
    if not keys:
        print("❌ No API keys found in api_keys collection")
        return
    
    print(f"✅ Found {len(keys)} API keys:\n")
    
    for key_doc in keys:
        service_name = key_doc.get('service_name', 'unknown')
        is_active = key_doc.get('is_active', False)
        api_key = key_doc.get('api_key', '')
        
        print(f"Service: {service_name}")
        print(f"Active: {is_active}")
        print(f"Key: {api_key[:40]}..." if api_key else "Key: (empty)")
        print()
        
        # Check for Grok specifically
        if service_name == 'grok' and is_active and api_key:
            print(f"✅ Active Grok API key found!")
            print(f"   Use this for optimization")

asyncio.run(get_api_keys())
EOF
```

**Key Fields:**
- `service_name` - 'grok', 'openai', 'elevenlabs', etc.
- `is_active` - Boolean, check before using
- `api_key` - The actual key
- `user_id` - Links to user

### Step 3: Run Baseline Test

**This is the main test script. Uses real system components.**

```bash
cd /app/backend
export $(cat .env | grep -E "MONGO_URL|REACT_APP_BACKEND_URL" | xargs)
python3 webhook_latency_tester.py
```

**What This Script Does:**
1. Creates real CallSession (same as production)
2. Sends 3 test conversations (19 total messages)
3. Each message:
   - Goes through actual LLM (Grok API call)
   - Generates real TTS audio (ElevenLabs API)
   - Retrieves from KB when needed
   - Evaluates transitions
   - Extracts variables
4. Measures time for each component
5. Saves results to JSON file

**Test Scenarios:**
1. **Objection Handling Flow** (8 messages)
   - Hello → Name → Time objection → KB query → Rejection → Challenge → Stall → Engagement
   - Tests: objection handling, KB retrieval, complex transitions
   
2. **Qualification Flow** (6 messages)
   - Hello → Name → Requirements → Employment → Income → Vehicle
   - Tests: qualification logic, variable extraction
   
3. **Skeptical Prospect** (5 messages)
   - Hello → Name → Scam concern → Proof request → Evidence
   - Tests: trust building, KB queries for social proof

**Expected Output:**
```
╔══════════════════════════════════════════════════════════════════════════════╗
║              WEBHOOK LATENCY TESTER - Real System Testing                    ║
║              Uses actual API endpoints, no simulation                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

📡 Backend URL: http://localhost:8001
🎯 Agent ID: e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4

📥 Loading agent...
✅ Agent: JK First Caller-optimizer
✅ System Prompt: 8,518 chars
✅ Nodes: 51

================================================================================
🧪 Testing: Objection Handling Flow
================================================================================

✅ Session started: test_1732456789

  1. User: "Hello"
     ⏱️  Total E2E: 1667ms
        LLM: 790ms | TTS: 400ms
     📍 Node: N100_Greeting_V4_Adaptive
     💬 Response: Hey there! This is Jake with...
     🔊 TTS Audio: 82,450 bytes

  2. User: "My name is John"
     ⏱️  Total E2E: 1190ms
        LLM: 654ms | TTS: 380ms
     📍 Node: N101_ConfirmName_V2
     💬 Response: Awesome, John! Great to...
     🔊 TTS Audio: 75,230 bytes

[... continues for all messages ...]

================================================================================
📊 OVERALL RESULTS
================================================================================

  📈 Full E2E Time (LLM + TTS Generation):
     Average: 1797ms
     Min: 273ms
     Max: 3327ms
     Total Messages: 19

  📊 Component Breakdown:
     Avg LLM: 946ms (52.6%)
     Avg TTS: 579ms (32.2%)

  🎯 Target: 1500ms
     Status: ❌ ABOVE TARGET (over by 297ms)

  💡 Optimization Needed:
     - LLM time high (946ms) - optimize prompts/transitions

  📋 Per-Conversation Averages:
     - Objection Handling Flow: 1834ms
     - Qualification Flow: 1612ms
     - Skeptical Prospect: 1945ms

  💾 Results saved to: /app/webhook_latency_test_20251124_130742.json

================================================================================
✅ WEBHOOK TESTING COMPLETE
================================================================================
```

**Result File Location:**
`/app/webhook_latency_test_YYYYMMDD_HHMMSS.json`

### Step 4: Analyze Results

**View Overall Stats:**
```bash
python3 -m json.tool /app/webhook_latency_test_20251124_130742.json | grep -A20 "overall_stats"
```

**Output:**
```json
"overall_stats": {
  "avg_latency_ms": 1797.0,
  "min_latency_ms": 273.0,
  "max_latency_ms": 3327.0,
  "avg_llm_ms": 946.0,
  "avg_tts_ms": 579.0,
  "target_latency_ms": 1500,
  "meets_target": false,
  "total_messages": 19
}
```

**Identify Bottlenecks:**

```python
import json

# Load test results
with open('/app/webhook_latency_test_20251124_130742.json', 'r') as f:
    data = json.load(f)

# Analyze by node
node_times = {}
for conv in data['conversations']:
    for msg in conv['messages']:
        node = msg.get('current_node', 'Unknown')
        llm_time = msg.get('llm_ms', 0)
        
        if node not in node_times:
            node_times[node] = []
        node_times[node].append(llm_time)

# Find slowest nodes
node_averages = {node: sum(times)/len(times) for node, times in node_times.items()}
slowest = sorted(node_averages.items(), key=lambda x: x[1], reverse=True)[:10]

print("🔥 SLOWEST NODES (Top 10):\n")
for node, avg_time in slowest:
    count = len(node_times[node])
    print(f"{node[:60]}")
    print(f"   Avg LLM: {avg_time:.0f}ms ({count} calls)\n")
```

**Decision Matrix:**

| LLM Time | TTS Time | Action |
|----------|----------|--------|
| >700ms | <600ms | Optimize prompts (main bottleneck) |
| <700ms | >600ms | Shorten responses |
| >700ms | >600ms | Optimize both |
| <700ms | <600ms | Already meeting target, done! |

**Common Slow Nodes:**
- `N_KB_Q&A_*` - KB queries take 1000-3000ms
- `N200_Super_*` - Long qualification prompts (6000+ chars)
- `N201_*` - Variable extraction nodes (~700ms overhead)

### Step 5: Optimize (If Needed)

**Use Conservative Optimizer:**

```bash
cd /app/backend
export $(cat .env | grep MONGO_URL | xargs)
python3 conservative_optimizer.py
```

**What It Does:**
- Targets slowest nodes only
- Max 30% reduction (not 50-60%)
- Preserves transition keywords
- Keeps qualification logic
- Uses Grok 4 for intelligent optimization

**Optimization Strategy:**

1. **System Prompt** (sent with every call)
   - Target: 20-30% reduction
   - Focus: Remove redundant examples, verbose explanations
   - Keep: All transition logic, variable names, KB references

2. **Slowest Nodes** (top 5-10)
   - Target: 20-30% reduction per node
   - Focus: Convert paragraphs to bullets, remove fluff
   - Keep: Core instructions, exact phrasing for speech

3. **Long Transitions** (>100 chars)
   - Target: 30-50% reduction
   - Focus: Boolean logic, pattern shortcuts
   - Keep: Exact matching intent

**Example Optimization:**

**Before (395 chars):**
```
If the user mentions that they're employed or have a job or work somewhere, 
this is a positive qualification signal. We want to understand their income 
level because that affects their ability to invest. Ask them about their 
yearly income in a conversational way. If they seem hesitant, reassure them 
that this is just to understand if the opportunity is a good fit.
```

**After (187 chars, 53% reduction):**
```
If user mentions employment/job:
- Positive qualification signal
- Ask yearly income conversationally
- If hesitant: "Just to see if it's a good fit"
```

**Preserved:**
- Employment detection logic
- Income question requirement
- Reassurance for hesitation

**Removed:**
- Explanatory text ("because that affects...")
- Redundant phrases ("employed or have a job or work")
- Obvious instructions ("in a conversational way")

### Step 6: Re-Test

**Run test again with same command:**
```bash
cd /app/backend
export $(cat .env | grep -E "MONGO_URL|REACT_APP_BACKEND_URL" | xargs)
python3 webhook_latency_tester.py
```

**Save results with different filename for comparison**

### Step 7: Validate Transitions (MANDATORY)

**This is THE most critical step. Don't skip.**

```python
import json

# Load both test results
with open('/app/webhook_latency_test_baseline.json', 'r') as f:
    baseline = json.load(f)

with open('/app/webhook_latency_test_optimized.json', 'r') as f:
    optimized = json.load(f)

print("="*80)
print("TRANSITION VALIDATION - CRITICAL CHECK")
print("="*80)
print()

total_messages = 0
transition_failures = 0
failures_detail = []

# Compare each conversation
for b_conv, o_conv in zip(baseline['conversations'], optimized['conversations']):
    conv_name = b_conv['name']
    
    # Compare each message
    for b_msg, o_msg in zip(b_conv['messages'], o_conv['messages']):
        total_messages += 1
        
        user_msg = b_msg['message']
        b_node = b_msg.get('current_node', 'Unknown')
        o_node = o_msg.get('current_node', 'Unknown')
        
        if b_node != o_node:
            transition_failures += 1
            failures_detail.append({
                'conversation': conv_name,
                'message': user_msg,
                'expected_node': b_node,
                'got_node': o_node
            })

# Print results
if transition_failures == 0:
    print("✅ ✅ ✅ ALL TRANSITIONS MATCH BASELINE! ✅ ✅ ✅")
    print(f"   {total_messages}/{total_messages} transitions correct")
    print("   Optimization is SAFE to keep")
else:
    print("❌ ❌ ❌ TRANSITION FAILURES DETECTED ❌ ❌ ❌")
    print(f"   {transition_failures}/{total_messages} transitions FAILED")
    print(f"   Failure rate: {(transition_failures/total_messages)*100:.1f}%")
    print()
    print("Failed transitions:")
    for failure in failures_detail[:10]:  # Show first 10
        print(f"\n  Conversation: {failure['conversation']}")
        print(f"  User: \"{failure['message']}\"")
        print(f"  Expected: {failure['expected_node'][:60]}")
        print(f"  Got: {failure['got_node'][:60]}")
    
    if len(failures_detail) > 10:
        print(f"\n  ... and {len(failures_detail) - 10} more failures")
    
    print()
    print("🚨 ACTION REQUIRED:")
    print("   1. REVERT optimization immediately")
    print("   2. Analysis why transitions broke")
    print("   3. Try less aggressive optimization (10-20% reduction)")
    print("   4. Re-test and validate again")

print()
print("="*80)
```

**Success Criteria:**
- ✅ **100% of transitions must match** (zero failures allowed)
- ✅ Latency reduced
- ✅ Response quality maintained

**If ANY Failures:**
1. **REVERT** optimization immediately
2. Analyze which nodes broke
3. Try less aggressive (10-20% vs 30%)
4. Re-test
5. Validate again

**Real Example From This Session:**
- Iteration 2: 22% transitions failed (11 out of 49)
- User caught it: "You verified the transitions still worked properly right?"
- Had to revert and start over
- Learned: Even 1-2% failure = broken logic

### Step 8: Compare Latency

**Only do this if transitions are 100% correct**

```python
import json

with open('baseline.json', 'r') as f:
    baseline = json.load(f)

with open('optimized.json', 'r') as f:
    optimized = json.load(f)

baseline_avg = baseline['overall_stats']['avg_latency_ms']
optimized_avg = optimized['overall_stats']['avg_latency_ms']

improvement = baseline_avg - optimized_avg
improvement_pct = (improvement / baseline_avg) * 100

print(f"Baseline: {baseline_avg:.0f}ms")
print(f"Optimized: {optimized_avg:.0f}ms")
print(f"Improvement: {improvement:.0f}ms ({improvement_pct:.1f}%)")

if optimized_avg <= 1500:
    print("\n✅ TARGET MET!")
else:
    print(f"\n⚠️ Still {optimized_avg - 1500:.0f}ms over target")
    print(f"Need {((optimized_avg - 1500) / optimized_avg) * 100:.1f}% more reduction")
```

### Step 9: Document & Iterate

**Log to LATENCY_ITERATIONS.md:**

```markdown
## Iteration X: [Description]
**Date:** 2025-11-24
**Status:** [Success/Failure]

### Changes:
- System prompt: 8518 → 6200 chars
- Node N200_Super: 6685 → 4200 chars
- 5 nodes optimized total

### Results:
- Baseline: 1797ms
- Optimized: 1520ms
- Improvement: 277ms (15.4%)
- Transitions: 100% correct ✅

### Status: ✅ Success - keeping changes
```

**If Still Over Target:**
- Identify next bottleneck
- Apply another round of optimization
- Test and validate again
- Repeat until target met

---

## MONGODB AGENT SEARCH

### The Problem

Agent searches fail on first try because:
1. Python doesn't auto-load .env variables
2. Multiple databases exist (test_database, ai_calling_db)
3. Agent structure varies (nodes vs call_flow)

**User Had to Remind Me Multiple Times**

### The Solution

**Always use this exact pattern:**

```bash
cd /app/backend
export $(cat .env | grep MONGO_URL | xargs)
python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json

async def comprehensive_agent_search():
    mongo_url = os.environ.get('MONGO_URL')
    
    if not mongo_url:
        print("❌ MONGO_URL not loaded!")
        print("   Use: export $(cat .env | grep MONGO_URL | xargs)")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    
    # Search parameters
    target_id = "YOUR_AGENT_ID"
    target_name = "YOUR_AGENT_NAME"
    
    print(f"Searching for:")
    print(f"  ID: {target_id}")
    print(f"  Name: {target_name}\n")
    
    # Get all databases
    db_names = await client.list_database_names()
    print(f"Available databases: {db_names}\n")
    
    # Check each database
    for db_name in db_names:
        if db_name in ['admin', 'local', 'config']:
            continue
        
        print(f"Checking {db_name}...")
        db = client[db_name]
        
        # Try by ID
        agent = await db.agents.find_one({"id": target_id})
        if agent:
            agent.pop('_id', None)
            print(f"  ✅ FOUND BY ID!")
            print(f"     Name: {agent.get('name')}")
            print(f"     Structure: {'call_flow' if 'call_flow' in agent else 'nodes'}")
            print(f"     Nodes: {len(agent.get('call_flow', agent.get('nodes', [])))}")
            
            with open(f'/app/found_agent_{db_name}.json', 'w') as f:
                json.dump(agent, f, indent=2, default=str)
            print(f"     Saved: /app/found_agent_{db_name}.json")
            return agent
        
        # Try by name
        agent = await db.agents.find_one({"name": target_name})
        if agent:
            agent.pop('_id', None)
            print(f"  ✅ FOUND BY NAME!")
            print(f"     ID: {agent.get('id')}")
            return agent
        
        # Try partial name match
        agents = await db.agents.find({
            "name": {"$regex": target_name.split()[0], "$options": "i"}
        }).to_list(length=10)
        
        if agents:
            print(f"  📋 Found {len(agents)} agents with similar names:")
            for a in agents[:5]:
                print(f"     - {a.get('name')} ({a.get('id')})")
    
    print("\n❌ Agent not found in any database")
    return None

asyncio.run(comprehensive_agent_search())
EOF
```

### Common Pitfalls

**Pitfall 1: Environment not loaded**
```
Error: MONGO_URL not set
Fix: export $(cat .env | grep MONGO_URL | xargs)
```

**Pitfall 2: Only checked one database**
```
Mistake: Only searched test_database
Reality: Agent was in ai_calling_db
Fix: Check ALL non-system databases
```

**Pitfall 3: Wrong structure assumption**
```
Mistake: Looking for agent.get('nodes')
Reality: Agent uses 'call_flow'
Fix: Check both structures
```

**Pitfall 4: Assuming agent missing**
```
Mistake: "Agent not found" → give up
Reality: In different database or has different ID
Fix: Try name search, list all agents
```

---

## API KEY RETRIEVAL

### The Critical Lesson

**User's Correction:**
> "there's a grok api key on the kendrickbowman9@gmail.com account in the mogonddb - don't use any emergent keys for this. Obviously it's there otherwise the agent could never make calls with that llm - duh"

### The Common Mistake

Looking in the **wrong place**:
```python
# ❌ WRONG - This field doesn't exist
user = await db.users.find_one({"id": USER_ID})
api_keys = user.get('api_keys', {})  # This is empty!
grok_key = api_keys.get('grok')  # None
```

### The Correct Approach

API keys are in a **separate collection**:

```python
# ✅ CORRECT
keys = await db.api_keys.find({"user_id": USER_ID}).to_list(length=50)

for key_doc in keys:
    service_name = key_doc.get('service_name')  # 'grok', 'openai', etc.
    is_active = key_doc.get('is_active')
    api_key = key_doc.get('api_key')
    
    if service_name == 'grok' and is_active:
        grok_key = api_key  # This is what you need!
```

### Full Working Example

```bash
cd /app/backend
export $(cat .env | grep MONGO_URL | xargs)
python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def get_user_api_keys():
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    user_id = "dcafa642-6136-4096-b77d-a4cb99a62651"
    
    print(f"Getting API keys for user: {user_id}\n")
    
    # Query the api_keys collection
    keys = await db.api_keys.find({"user_id": user_id}).to_list(length=100)
    
    if not keys:
        print("❌ No keys found in api_keys collection")
        print("\nChecking user document...")
        user = await db.users.find_one({"id": user_id})
        if user:
            print(f"User exists but has no keys in api_keys collection")
        return
    
    print(f"✅ Found {len(keys)} API keys:\n")
    
    # Organize by service
    by_service = {}
    for key_doc in keys:
        service = key_doc.get('service_name', 'unknown')
        if service not in by_service:
            by_service[service] = []
        by_service[service].append(key_doc)
    
    # Display each service
    for service, service_keys in by_service.items():
        print(f"Service: {service}")
        for key_doc in service_keys:
            is_active = key_doc.get('is_active', False)
            api_key = key_doc.get('api_key', '')
            
            status = "✅ ACTIVE" if is_active else "❌ Inactive"
            key_preview = api_key[:40] + "..." if api_key else "(empty)"
            
            print(f"  {status}")
            print(f"  Key: {key_preview}")
            
            if service == 'grok' and is_active:
                print(f"  👉 USE THIS KEY for optimization")
        print()

asyncio.run(get_user_api_keys())
EOF
```

### Key Fields in api_keys Collection

```javascript
{
  "user_id": "dcafa642-6136-4096-b77d-a4cb99a62651",
  "service_name": "grok",  // or 'openai', 'elevenlabs', etc.
  "api_key": "xai-...",      // The actual key
  "is_active": true,          // Check this!
  "created_at": "...",
  "encrypted_key": null       // Sometimes keys are encrypted
}
```

### Why This Matters

If you use the wrong key or no key:
- ❌ API calls fail
- ❌ Test doesn't run
- ❌ Can't measure latency
- ❌ Wastes time debugging

User has to remind you:
> "Obviously it's there otherwise the agent could never make calls with that llm - duh"

---

## RUNNING BASELINE TESTS

### The Test Script

**Location:** `/app/backend/webhook_latency_tester.py`

**What It Does:**
- Creates real CallSession
- Makes real Grok LLM API calls
- Generates real ElevenLabs TTS audio
- Retrieves from real knowledge base
- Evaluates real transitions
- Extracts real variables
- NO simulation or estimation

### Running the Test

```bash
cd /app/backend
export $(cat .env | grep -E "MONGO_URL|REACT_APP_BACKEND_URL" | xargs)
python3 webhook_latency_tester.py
```

**Expected Duration:** 2-3 minutes

**What You'll See:**
```
╔══════════════════════════════════════════════════════════════════════════════╗
║              WEBHOOK LATENCY TESTER - Real System Testing                    ║
║              Uses actual API endpoints, no simulation                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

📡 Backend URL: http://localhost:8001
🎯 Agent ID: e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4

📥 Loading agent...
✅ Agent: JK First Caller-optimizer
✅ System Prompt: 8,518 chars
✅ Nodes: 51

================================================================================
🧪 Testing: Objection Handling Flow
================================================================================

✅ Session started: test_1732456789

  1. User: "Hello"
     ⏱️  Total E2E: 1667ms
        LLM: 790ms | TTS: 400ms
     📍 Node: N100_Greeting_V4_Adaptive
     💬 Response: Hey there! This is Jake with Income...
     🔊 TTS Audio: 82,450 bytes

  2. User: "My name is John"
     ⏱️  Total E2E: 1190ms
        LLM: 654ms | TTS: 380ms
     📍 Node: N101_ConfirmName_V2
     💬 Response: Awesome, John! Great to connect with you...
     🔊 TTS Audio: 75,230 bytes

[... continues ...]

  📊 Conversation Summary:
     Messages: 8
     Average Response Generation: 1834ms

[... more conversations ...]

================================================================================
📊 OVERALL RESULTS
================================================================================

  📈 Full E2E Time (LLM + TTS Generation):
     Average: 1797ms
     Min: 273ms
     Max: 3327ms
     Total Messages: 19

  📊 Component Breakdown:
     Avg LLM: 946ms (52.6%)
     Avg TTS: 579ms (32.2%)

  🎯 Target: 1500ms
     Status: ❌ ABOVE TARGET (over by 297ms)

  💡 Optimization Needed:
     - LLM time high (946ms) - optimize prompts/transitions

  📋 Per-Conversation Averages:
     - Objection Handling Flow: 1834ms
     - Qualification Flow: 1612ms
     - Skeptical Prospect: 1945ms

  💾 Results saved to: /app/webhook_latency_test_20251124_130742.json

================================================================================
✅ WEBHOOK TESTING COMPLETE
================================================================================
```

### Test Scenarios Explained

**Scenario 1: Objection Handling Flow (8 messages)**

Purpose: Test objection handling, KB retrieval, complex transitions

1. "Hello" → Initial greeting
2. "My name is John" → Name confirmation
3. "I don't have time for this" → TIME OBJECTION → triggers objection handling
4. "What is this about?" → KB QUERY → triggers knowledge base retrieval
5. "I'm still not interested" → PERSISTENT OBJECTION → tests objection persistence
6. "Why should I care?" → CHALLENGE → tests value reframe
7. "I need to think about it" → STALL → tests stall handling
8. "Actually tell me more" → ENGAGEMENT → tests breakthrough transition

**Why This Tests Real Performance:**
- Multiple KB queries (high latency)
- Complex transition evaluations
- Various objection types
- Mirrors real prospect behavior

**Scenario 2: Qualification Flow (6 messages)**

Purpose: Test qualification logic, variable extraction

1. "Hello" → Greeting
2. "I'm Sarah" → Name
3. "What are the requirements?" → INFO SEEKING
4. "I'm employed" → QUALIFICATION → tests employment detection
5. "I make 70k per year" → INCOME → tests variable extraction (~700ms)
6. "Yes I have a vehicle" → VEHICLE → tests additional qualification

**Why This Tests Real Performance:**
- Variable extraction overhead
- Qualification node prompts (often long)
- Sequential transitions

**Scenario 3: Skeptical Prospect (5 messages)**

Purpose: Test trust building, social proof KB queries

1. "Hello" → Greeting
2. "This is Mike" → Name
3. "This sounds like a scam" → TRUST OBJECTION
4. "How do I know this is real?" → PROOF REQUEST → KB query
5. "Do you have proof?" → EVIDENCE → more KB queries

**Why This Tests Real Performance:**
- Multiple KB lookups for social proof
- Trust-building responses (often longer)
- Tests most common objection type

### Understanding the Output

**Per-Message Output:**
```
⏱️  Total E2E: 1667ms       <- Total generation time (what we optimize)
   LLM: 790ms | TTS: 400ms  <- Component breakdown
📍 Node: N100_Greeting...    <- Which node handled this
💬 Response: Hey there...    <- What was said (first 80 chars)
🔊 TTS Audio: 82,450 bytes  <- Audio file size generated
```

**Component Breakdown:**
- **LLM Time** - How long Grok took to generate response text
- **TTS Time** - How long ElevenLabs took to generate audio
- **Total E2E** - LLM + TTS (this is what we measure and optimize)

**NOT Included (correctly):**
- Audio playback time
- Network transmission
- User speaking time
- STT processing

### Interpreting Results

**Target: ≤1500ms average**

**If 1200-1500ms:**
- ✅ Excellent! At or near target
- May want to optimize outliers (>2000ms messages)

**If 1500-1800ms:**
- ⚠️ Slightly over (like our baseline: 1797ms)
- Need ~15-20% reduction
- Focus on slowest nodes

**If 1800-2200ms:**
- ❌ Significantly over
- Need ~25-35% reduction
- Major optimization required

**If >2200ms:**
- ❌❌ Way over
- Need fundamental changes
- Check for errors (KB timeouts, etc.)

### Result File Structure

**JSON Output:**
```json
{
  "timestamp": "2025-11-24T13:07:42...",
  "agent_id": "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4",
  "agent_name": "JK First Caller-optimizer",
  "system_prompt_length": 8518,
  "backend_url": "http://localhost:8001",
  
  "overall_stats": {
    "avg_latency_ms": 1797.0,
    "min_latency_ms": 273.0,
    "max_latency_ms": 3327.0,
    "avg_llm_ms": 946.0,
    "avg_tts_ms": 579.0,
    "target_latency_ms": 1500,
    "meets_target": false,
    "total_messages": 19
  },
  
  "conversations": [
    {
      "name": "Objection Handling Flow",
      "session_id": "test_1732456789",
      "messages": [
        {
          "message": "Hello",
          "latency_ms": 1667.3,
          "llm_ms": 790.2,
          "tts_ms": 400.1,
          "response": "Hey there! This is Jake...",
          "current_node": "N100_Greeting_V4_Adaptive",
          "response_length": 156,
          "tts_audio_size": 82450
        },
        // ... more messages
      ],
      "total_latency": 14673.2,
      "avg_latency": 1834.15
    },
    // ... more conversations
  ]
}
```

---

## ANALYZING RESULTS

### Step 1: Check Overall Performance

```bash
python3 -m json.tool /app/webhook_latency_test_*.json | grep -A15 "overall_stats"
```

**Look at:**
- `avg_latency_ms` - Is it ≤1500?
- `avg_llm_ms` - Is LLM the bottleneck? (>700ms)
- `avg_tts_ms` - Is TTS the bottleneck? (>600ms)
- `meets_target` - Quick true/false check

### Step 2: Find Slowest Nodes

```python
import json

# Load results
with open('/app/webhook_latency_test_20251124_130742.json', 'r') as f:
    data = json.load(f)

# Aggregate by node
node_stats = {}

for conv in data['conversations']:
    for msg in conv['messages']:
        node = msg.get('current_node', 'Unknown')
        llm_time = msg.get('llm_ms', 0)
        tts_time = msg.get('tts_ms', 0)
        total_time = msg.get('latency_ms', 0)
        
        if node not in node_stats:
            node_stats[node] = {
                'calls': 0,
                'llm_times': [],
                'tts_times': [],
                'total_times': []
            }
        
        node_stats[node]['calls'] += 1
        node_stats[node]['llm_times'].append(llm_time)
        node_stats[node]['tts_times'].append(tts_time)
        node_stats[node]['total_times'].append(total_time)

# Calculate averages
node_averages = []
for node, stats in node_stats.items():
    avg_llm = sum(stats['llm_times']) / len(stats['llm_times'])
    avg_tts = sum(stats['tts_times']) / len(stats['tts_times'])
    avg_total = sum(stats['total_times']) / len(stats['total_times'])
    
    node_averages.append({
        'node': node,
        'calls': stats['calls'],
        'avg_llm': avg_llm,
        'avg_tts': avg_tts,
        'avg_total': avg_total
    })

# Sort by total time
node_averages.sort(key=lambda x: x['avg_total'], reverse=True)

# Print top 10 slowest
print("🔥 TOP 10 SLOWEST NODES:\n")
for i, node_data in enumerate(node_averages[:10], 1):
    node = node_data['node']
    calls = node_data['calls']
    avg_llm = node_data['avg_llm']
    avg_tts = node_data['avg_tts']
    avg_total = node_data['avg_total']
    
    print(f"{i}. {node[:60]}")
    print(f"   Avg Total: {avg_total:.0f}ms ({calls} calls)")
    print(f"   LLM: {avg_llm:.0f}ms | TTS: {avg_tts:.0f}ms")
    
    # Suggest optimization
    if avg_llm > 1000:
        print(f"   🎯 HIGH PRIORITY - LLM time very high")
    elif avg_llm > 700:
        print(f"   ⚠️ OPTIMIZE - LLM time above average")
    print()
```

### Step 3: Identify Patterns

**Common Slow Node Types:**

1. **KB Query Nodes** (`N_KB_Q&A_*`)
   - Typical time: 2000-3000ms
   - Reason: Knowledge base retrieval + long response generation
   - Optimization: Can't reduce KB time, but can shorten prompts

2. **Variable Extraction Nodes** (`N201_*`, `N202_*`)
   - Typical time: 1500-2000ms
   - Reason: ~700ms extraction overhead + long qualification prompts
   - Optimization: Shorten prompts, keep extraction logic

3. **Super Nodes** (`N200_Super_*`)
   - Typical time: 1800-2500ms
   - Reason: Very long prompts (6000+ chars)
   - Optimization: High priority, big reduction potential

4. **Scripted Nodes** (`N100_*`, `N101_*`)
   - Typical time: 200-500ms
   - Reason: Return pre-written responses
   - Optimization: Already fast, skip

### Step 4: Calculate Optimization Potential

```python
# Which nodes should we optimize?

optimization_targets = []

for node_data in node_averages:
    node = node_data['node']
    avg_llm = node_data['avg_llm']
    calls = node_data['calls']
    
    if avg_llm < 500:
        continue  # Already fast
    
    # Calculate potential savings
    # Assume 30% reduction in LLM time
    potential_reduction = avg_llm * 0.30
    
    # Weight by number of calls
    weighted_impact = potential_reduction * calls
    
    optimization_targets.append({
        'node': node,
        'current_llm': avg_llm,
        'potential_reduction': potential_reduction,
        'weighted_impact': weighted_impact,
        'calls': calls
    })

# Sort by weighted impact
optimization_targets.sort(key=lambda x: x['weighted_impact'], reverse=True)

print("🎯 OPTIMIZATION PRIORITY (Weighted by Impact):\n")
for i, target in enumerate(optimization_targets[:10], 1):
    print(f"{i}. {target['node'][:60]}")
    print(f"   Current LLM: {target['current_llm']:.0f}ms")
    print(f"   30% Reduction: -{target['potential_reduction']:.0f}ms")
    print(f"   Weighted Impact: {target['weighted_impact']:.0f}")
    print(f"   ({target['calls']} calls)")
    print()
```

### Step 5: Estimate Total Improvement

```python
# If we optimize top 10 nodes by 30%

top_10_nodes = [t['node'] for t in optimization_targets[:10]]

# Recalculate average with optimized nodes
new_latencies = []

for conv in data['conversations']:
    for msg in conv['messages']:
        node = msg.get('current_node')
        llm_time = msg.get('llm_ms', 0)
        tts_time = msg.get('tts_ms', 0)
        
        # Apply 30% reduction if node in top 10
        if node in top_10_nodes:
            llm_time = llm_time * 0.70  # 30% reduction
        
        new_latencies.append(llm_time + tts_time)

current_avg = data['overall_stats']['avg_latency_ms']
projected_avg = sum(new_latencies) / len(new_latencies)
improvement = current_avg - projected_avg

print(f"📊 PROJECTION:\n")
print(f"Current Avg: {current_avg:.0f}ms")
print(f"Projected Avg: {projected_avg:.0f}ms")
print(f"Expected Improvement: {improvement:.0f}ms ({(improvement/current_avg)*100:.1f}%)")
print()

if projected_avg <= 1500:
    print(f"✅ Would meet target! ({1500 - projected_avg:.0f}ms under)")
else:
    print(f"⚠️ Still {projected_avg - 1500:.0f}ms over target")
    print(f"Need {((projected_avg - 1500)/projected_avg)*100:.1f}% more reduction")
```

---

## OPTIMIZATION STRATEGIES

### Strategy 1: System Prompt Optimization

**Impact:** High (sent with every LLM call)

**Current:** 8,518 chars

**Target:** 5,500-6,500 chars (20-30% reduction)

**What to Remove:**
- Redundant examples (keep 1-2 best ones)
- Verbose explanations
- Repeated instructions
- Flowery language

**What to Keep:**
- All transition logic keywords
- Variable names and extraction rules
- KB reference syntax
- Core qualification criteria
- Brand voice essentials

**Example:**

Before:
```
You are Jake, a friendly and enthusiastic representative from Income Stacking. 
Your main goal is to help people understand how they can create additional 
income streams through our proven system. When talking to prospects, you should 
always maintain a conversational, upbeat tone. If someone asks you a question, 
try to answer it directly but also look for opportunities to understand their 
situation better.
```

After:
```
You're Jake from Income Stacking. Goal: Help people understand additional 
income opportunities. Tone: Conversational, upbeat. Answer questions directly, 
then qualify their situation.
```

### Strategy 2: Node Content Optimization

**Target Nodes:**
1. N200_Super_WorkAndIncomeBackground (6,685 chars)
2. N_KB_Q&A nodes (3,000+ chars)
3. N201_* qualification nodes (4,000+ chars)
4. N202_* business qualification nodes (5,000+ chars)

**Conservative Approach (20-30% reduction):**

**Before:**
```
Now that we know they're employed, we need to understand their income level 
because that's going to affect whether they have the capital to invest in this 
opportunity. Ask them about their yearly income in a natural, conversational 
way. Don't make it feel like an interrogation. If they seem uncomfortable 
sharing this information, you can reassure them that we're just trying to 
make sure this is a good fit for their situation and financial goals. Once 
they share their income, acknowledge it positively regardless of the amount, 
and then transition to the next qualification question.
```

**After:**
```
Employment confirmed. Next: yearly income (affects investment capacity).

Ask conversationally. If hesitant: "Just checking if it's a good fit."

Acknowledge positively regardless of amount. Then continue qualification.
```

**Preserved:**
- Income question requirement
- Conversational tone
- Reassurance for hesitation
- Positive acknowledgment
- Flow to next question

**Removed:**
- Explanatory text ("because that's going to affect...")
- Redundant phrases ("natural, conversational way")
- Obvious instructions ("Don't make it feel like...")

### Strategy 3: Transition Optimization

**Target:** Transitions >100 chars

**Aggressive Reduction (30-50%):**

**Before:**
```
If the user says something like "yes" or "yeah" or "sure" or "okay" or any 
other positive affirmation that indicates they want to continue, then move 
to the next node
```

**After:**
```
yes|yeah|sure|okay|positive affirmation → next node
```

**Preserved:**
- Exact matching logic
- All trigger words
- Next node destination

**Removed:**
- Explanatory text
- Redundant "or"
- Verbose description

### Strategy 4: Response Length Reduction

**Impact:** Reduces TTS time

**Current TTS:** 400-800ms typical

**Target:** 300-600ms (25% reduction)

**Approach:**
- Shorten agent responses by 20-30%
- Remove filler words
- Get to the point faster
- Keep conversational tone

**Example:**

Before (186 chars):
```
That's great to hear! So you mentioned you're employed - that's awesome. 
Can I ask, what's your approximate yearly income? This just helps me understand 
if our opportunity would be a good fit for where you're at financially.
```

After (124 chars, 33% reduction):
```
Great! You're employed - awesome. What's your yearly income? Just want to 
see if this fits your financial situation.
```

---

## TRANSITION VALIDATION

### Why This is THE Most Critical Step

**From This Session:**
- Achieved 1382ms (118ms under target)
- 22% of transitions were broken
- Users would get wrong conversation paths
- **Had to revert everything**

**User's Reaction:**
> "And you verified the transitions still worked properly right? that was the biggest thing - getting it down while maintaining functionality"

### The Validation Script

**Save as `/app/validate_transitions.py`:**

```python
#!/usr/bin/env python3
"""
Transition Validation Script
Compares baseline vs optimized test results
Must show 100% match (zero failures)
"""
import json
import sys

def validate_transitions(baseline_file, optimized_file):
    # Load both files
    with open(baseline_file, 'r') as f:
        baseline = json.load(f)
    
    with open(optimized_file, 'r') as f:
        optimized = json.load(f)
    
    print("="*80)
    print("TRANSITION VALIDATION - MANDATORY CHECK")
    print("="*80)
    print()
    
    # Track results
    total_messages = 0
    total_failures = 0
    failures_by_conversation = {}
    
    # Compare each conversation
    for b_conv, o_conv in zip(baseline['conversations'], optimized['conversations']):
        conv_name = b_conv['name']
        conv_failures = []
        
        # Compare each message
        for b_msg, o_msg in zip(b_conv['messages'], o_conv['messages']):
            total_messages += 1
            
            user_msg = b_msg['message']
            b_node = b_msg.get('current_node', 'Unknown')
            o_node = o_msg.get('current_node', 'Unknown')
            
            if b_node != o_node:
                total_failures += 1
                conv_failures.append({
                    'message': user_msg,
                    'expected': b_node,
                    'got': o_node
                })
        
        if conv_failures:
            failures_by_conversation[conv_name] = conv_failures
    
    # Print results
    if total_failures == 0:
        print("" + "✅"*20)
        print()
        print("  " + " "*15 + "ALL TRANSITIONS MATCH!")
        print()
        print("" + "✅"*20)
        print()
        print(f"  {total_messages}/{total_messages} transitions correct (100%)")
        print()
        print("  🎉 OPTIMIZATION IS SAFE TO KEEP")
        print()
        print("  Next steps:")
        print("  1. Check latency improvement")
        print("  2. Document changes in LATENCY_ITERATIONS.md")
        print("  3. If target met, you're done!")
        print("  4. If not, run another iteration")
        return True
    
    else:
        print("" + "❌"*20)
        print()
        print("  " + " "*12 + "TRANSITION FAILURES DETECTED")
        print()
        print("" + "❌"*20)
        print()
        print(f"  Failures: {total_failures}/{total_messages} ({(total_failures/total_messages)*100:.1f}%)")
        print()
        
        # Show failures by conversation
        for conv_name, failures in failures_by_conversation.items():
            print(f"\n  Conversation: {conv_name}")
            print(f"  Failures: {len(failures)}")
            print()
            
            for failure in failures[:5]:  # Show first 5 per conversation
                print(f"    Message: \"{failure['message']}\"")
                print(f"    Expected: {failure['expected'][:60]}")
                print(f"    Got:      {failure['got'][:60]}")
                print()
            
            if len(failures) > 5:
                print(f"    ... and {len(failures) - 5} more failures in this conversation")
                print()
        
        print()
        print("  🚨 CRITICAL - MUST REVERT OPTIMIZATION")
        print()
        print("  Why this failed:")
        print("  - Optimization removed too much context")
        print("  - LLM can't evaluate transitions correctly")
        print("  - Users would get wrong conversation paths")
        print()
        print("  Action required:")
        print("  1. REVERT changes to MongoDB")
        print("  2. Restore from backup (/app/agent_backup.json)")
        print("  3. Try less aggressive optimization (10-20% vs 30%)")
        print("  4. Re-test and validate again")
        print()
        return False
    
    print("="*80)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_transitions.py baseline.json optimized.json")
        sys.exit(1)
    
    baseline_file = sys.argv[1]
    optimized_file = sys.argv[2]
    
    success = validate_transitions(baseline_file, optimized_file)
    sys.exit(0 if success else 1)
```

### Running Validation

```bash
cd /app
python3 validate_transitions.py \
  webhook_latency_test_baseline.json \
  webhook_latency_test_optimized.json
```

### Interpreting Results

**Success (100% match):**
```
✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅

               ALL TRANSITIONS MATCH!

✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅

  49/49 transitions correct (100%)

  🎉 OPTIMIZATION IS SAFE TO KEEP
```

**Proceed to check latency improvement**

**Failure (any failures):**
```
❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌

            TRANSITION FAILURES DETECTED

❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌

  Failures: 11/49 (22.4%)

  🚨 CRITICAL - MUST REVERT OPTIMIZATION
```

**Must revert immediately**

### What Transition Failures Mean

**Example:**
```
Message: "I don't have time for this"
Expected: N_ObjectionHandler_Time_V3
Got:      N200_Super_WorkAndIncome
```

**What happened:**
- User said time objection
- Should go to objection handler
- Instead went to qualification node
- Wrong conversation path!

**Impact on real calls:**
- User: "I don't have time"
- Agent: "Great! Tell me about your income" (WRONG)
- User hangs up (bad experience)
- Lost opportunity

**Root Cause:**
- Optimization removed context from node
- LLM can't evaluate transition condition correctly
- Matches wrong condition
- Goes to wrong node

### Acceptable Failure Rates

**0% failures:** ✅ Perfect, keep optimization

**1-5% failures:** ❌ Revert, too risky
- Even 1% = 1 in 100 calls broken
- That's 10-20 bad calls per day
- Unacceptable

**5-15% failures:** ❌❌ Definitely revert
- Major logic breakage
- 1 in 10 calls wrong
- User experience severely impacted

**15-25% failures:** ❌❌❌ Catastrophic failure
- Like our Iteration 2 (22%)
- 1 in 4 calls broken
- Agent is unusable

**>25% failures:** ❌❌❌❌ Complete disaster
- Optimization destroyed the agent
- Immediate revert required

### The Rule

**Zero tolerance for transition failures.**

**100% match required.**

**No exceptions.**

---

## COMMON MISTAKES

### Mistake 1: Simulating TTS

**What I Did:**
```python
# ❌ WRONG
tts_time = len(text) / 15  # 15 chars/second
await asyncio.sleep(tts_time)
```

**User's Correction:**
> "Stop trying to estimate it - just generate audio files and connect to the webhook you are not allowed to try to simulate anything ever again - code in a proper test."

**Why This Was Wrong:**
- ElevenLabs Flash v2.5 is actually 100+ chars/second, not 15
- Off by 7-10x
- Gave completely wrong latency measurements

**Correct Approach:**
```python
# ✅ CORRECT
from server import generate_tts_audio
tts_audio = await generate_tts_audio(response, agent_config)
# Real API call, real audio generation, real timing
```

### Mistake 2: Optimizing Before Baseline

**What I Did:**
- Ran optimizer first
- Then tried to test
- No way to compare results

**User's Correction:**
- Had to remind me multiple times
- "test first, optimize second, test again, compare"

**Why This Was Wrong:**
- Can't measure improvement without baseline
- Might optimize wrong things
- No comparison data

**Correct Order:**
1. Baseline test
2. Analyze bottlenecks
3. Optimize specific issues
4. Test again
5. Compare results

### Mistake 3: Not Validating Transitions

**What I Did:**
- Achieved 1382ms (under target!)
- Declared success
- Didn't check transitions

**User's Question:**
> "And you verified the transitions still worked properly right? that was the biggest thing"

**What I Found:**
- 22% of transitions were broken
- 11 out of 49 messages went to wrong nodes
- Complete failure

**Why This Was Critical:**
- Latency improvement is meaningless if logic breaks
- Fast but wrong = failure
- Users get bad experience

**The Learning:**
**ALWAYS validate transitions. 100% match required. No exceptions.**

### Mistake 4: Including Playback Time

**What I Did:**
- Tried to measure audio playback time
- Added delays for "user listening"

**User's Correction:**
> "do not count playback as latency all of this should have been established in the sop"

**Why This Was Wrong:**
- Playback happens AFTER response is ready
- Can't optimize playback (fixed by audio length)
- Not part of generation time

**Correct Measurement:**
- LLM processing: ✅ (we control this)
- TTS generation: ✅ (we control this)
- Audio playback: ❌ (user listens, can't optimize)

### Mistake 5: Using Simple Tests

**What I Did:**
- Created "Hello" test
- Got 1365ms average
- Seemed great!

**User Was Suspicious:**
> "No way the latency is that... Are you measuring this properly as a mirror of the system?"

**User Was Right:**
- Simple tests show scripted responses (0ms)
- Don't trigger KB
- Don't test complex transitions
- Artificially low latencies

**Correct Approach:**
- 8+ nodes deep
- Multiple objections
- Trigger KB queries
- Test variable extraction
- Complex transitions

### Mistake 6: Wrong API Key Source

**What I Did:**
```python
# ❌ WRONG
user = await db.users.find_one({"id": USER_ID})
api_keys = user.get('api_keys', {})  # Empty!
grok_key = api_keys.get('grok')  # None
```

**User's Correction:**
> "there's a grok api key on the kendrickbowman9@gmail.com account in the mogonddb - don't use any emergent keys for this. Obviously it's there otherwise the agent could never make calls with that llm - duh"

**Why This Was Wrong:**
- API keys aren't in user document
- They're in separate api_keys collection
- Obvious in hindsight ("agent could never make calls")

**Correct Approach:**
```python
# ✅ CORRECT
keys = await db.api_keys.find({"user_id": USER_ID}).to_list(50)
for key in keys:
    if key.get('service_name') == 'grok' and key.get('is_active'):
        grok_key = key.get('api_key')
```

### Mistake 7: Not Checking All Databases

**What I Did:**
- Searched test_database
- Agent not found
- Assumed it didn't exist

**User Corrected Me:**
- Had to remind me multiple times
- Agent was in different database

**Why This Was Wrong:**
- MongoDB Atlas has multiple databases
- Agent could be in ai_calling_db or test_database
- Need to check both

**Correct Approach:**
- Always check ALL databases
- Try both ID and name
- Don't assume missing

### Mistake 8: Not Documenting Mistakes

**User's Feedback:**
> "I need the testing sop changed and updated so that a brand new agent that's never seen any of the context here could pick up a test - you have a lot of old invalid things in there and I had to remind you of a lot of stuff"

**Why This Section Exists:**
- Every mistake user caught
- Every correction they made
- Documented so future agents don't repeat

**This is Mistake #8 - Fixed:**
- Creating comprehensive SOP
- Documenting all mistakes
- Including user's exact corrections
- So no one has to remind me again

---

## TROUBLESHOOTING GUIDE

### Issue: Agent Not Found

**Symptoms:**
- MongoDB query returns None
- "Agent not found" error

**Causes & Solutions:**

1. **Environment not loaded**
   ```bash
   # Fix:
   export $(cat .env | grep MONGO_URL | xargs)
   ```

2. **Wrong database**
   ```python
   # Check both:
   for db_name in ['test_database', 'ai_calling_db']:
       agent = await client[db_name].agents.find_one({"id": AGENT_ID})
   ```

3. **Wrong ID**
   ```python
   # Try by name instead:
   agent = await db.agents.find_one({"name": "JK First Caller-optimizer"})
   ```

4. **Wrong structure**
   ```python
   # Check both:
   nodes = agent.get('call_flow', agent.get('nodes', []))
   ```

### Issue: Test Script Fails

**Symptoms:**
- Import errors
- Connection failures
- API errors

**Causes & Solutions:**

1. **Missing dependencies**
   ```bash
   cd /app/backend
   pip install -r requirements.txt
   ```

2. **Backend not running**
   ```bash
   sudo supervisorctl status backend
   sudo supervisorctl restart backend
   ```

3. **API keys missing**
   ```python
   # Check api_keys collection
   keys = await db.api_keys.find({"user_id": USER_ID}).to_list(50)
   ```

4. **Wrong backend URL**
   ```bash
   echo $REACT_APP_BACKEND_URL
   # Should be: http://localhost:8001 or similar
   ```

### Issue: Latency Seems Wrong

**Symptoms:**
- Too low (<1000ms when expecting ~1800ms)
- Too high (>5000ms consistently)
- Inconsistent results

**Causes & Solutions:**

1. **Scripted responses returning instantly**
   - Check: Are you testing deep enough? (8+ nodes)
   - Fix: Use provided test scenarios

2. **Not generating real TTS**
   - Check: Is generate_tts_audio() being called?
   - Fix: Don't simulate, use real API

3. **KB queries timing out**
   - Check: Are KB queries taking >5s?
   - Fix: Check KB service health

4. **Caching affecting results**
   - Check: Are responses cached?
   - Fix: Use unique session IDs per test

### Issue: Transitions Failing

**Symptoms:**
- Validation shows failures
- Users going to wrong nodes
- Logic breaking

**Causes & Solutions:**

1. **Optimization too aggressive**
   - Check: Did you remove >30% of content?
   - Fix: Revert, try 10-20% instead

2. **Removed transition keywords**
   - Check: Are key phrases missing?
   - Fix: Restore keywords, re-optimize

3. **Changed qualification logic**
   - Check: Are if/then conditions altered?
   - Fix: Restore original logic

4. **Broke context for LLM**
   - Check: Is prompt now too vague?
   - Fix: Add back essential context

### Issue: Can't Connect to MongoDB

**Symptoms:**
- Connection timeout
- Authentication failed
- Network error

**Causes & Solutions:**

1. **MONGO_URL not set**
   ```bash
   export $(cat .env | grep MONGO_URL | xargs)
   echo $MONGO_URL  # Verify
   ```

2. **IP not whitelisted**
   - Check: MongoDB Atlas IP whitelist
   - Fix: Add your IP or use 0.0.0.0/0

3. **Wrong credentials**
   - Check: Is password correct in MONGO_URL?
   - Fix: Verify in .env file

4. **Network issues**
   - Check: Can you reach mongodb.net?
   - Fix: Check firewall, DNS

### Issue: Grok API Errors

**Symptoms:**
- 401 Unauthorized
- Rate limit errors
- Invalid model errors

**Causes & Solutions:**

1. **Wrong API key**
   ```python
   # Verify key from api_keys collection
   keys = await db.api_keys.find({"user_id": USER_ID}).to_list(50)
   ```

2. **Invalid model name**
   - Use: "grok-4-0709" (current working model)
   - Not: "grok-beta" or "grok-4.1" (deprecated)

3. **Rate limiting**
   - Check: Are you making too many requests?
   - Fix: Add delays between tests

4. **Quota exceeded**
   - Check: User's Grok API quota
   - Fix: Wait or add credits

---

## FILE LOCATIONS

### Active Files (Use These)

**SOP Documentation:**
- `/app/LATENCY_OPTIMIZATION_SOP.md` - This comprehensive guide
- `/app/test_result.md` - Extended testing protocol (1922 lines)
- `/app/LATENCY_ITERATIONS.md` - Log of all optimization attempts

**Test Scripts:**
- `/app/backend/webhook_latency_tester.py` - Main test script (uses real system)
- `/app/validate_transitions.py` - Transition validation script

**Optimization Scripts:**
- `/app/backend/conservative_optimizer.py` - Safe 20-30% optimizer
- `/app/backend/simple_latency_optimizer.py` - Alternative optimizer

**Data Files:**
- `/app/new_agent_backup.json` - Clean agent backup
- `/app/webhook_latency_test_*.json` - Test results (timestamped)

### Deprecated Files (Ignore These)

**Old Test Scripts:**
- `/app/backend/real_latency_tester.py` - Incomplete (no TTS)
- `/app/backend/accurate_latency_tester.py` - Uses simulation (wrong)
- `/app/backend/latency_tester.py` - Authentication issues

**Old Documentation:**
- `/app/LATENCY_TESTING_SOP.md` - Outdated version
- `/app/TRANSITION_TESTING_GUIDE.md` - Old guide
- `/app/COMPLETE_LATENCY_ANALYSIS.md` - Historical
- `/app/LATENCY_ANALYSIS_REAL_VS_LOGS.md` - Historical
- `/app/OPTIMIZER_TEST_RESULTS.md` - Old results

**Why Deprecated:**
- Built on wrong assumptions
- Used simulation/estimation
- Incomplete measurements
- Outdated approach

---

## CURRENT PROJECT STATUS

### Where We Are

**Date:** 2025-11-24

**Agent:**
- ID: e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4
- Name: JK First Caller-optimizer
- Status: Baseline established, unoptimized

**Baseline Results:**
- Average Latency: 1797ms
- Target: 1500ms
- Gap: 297ms (17% reduction needed)
- LLM Time: 946ms (52.6%)
- TTS Time: 579ms (32.2%)

**Bottlenecks Identified:**
1. LLM processing (946ms avg) - HIGH PRIORITY
2. N_KB_Q&A nodes (2000-3000ms)
3. N200_Super nodes (1800-2500ms)
4. Variable extraction (~700ms overhead)

**Next Steps:**
1. Optimize top 5-10 slowest nodes (20-30% reduction)
2. Shorten system prompt (20-30% reduction)
3. Re-test with webhook_latency_tester.py
4. Validate transitions (100% match required)
5. Check latency improvement
6. Iterate if needed

### Previous Attempts

**Iteration 1:**
- Optimized system prompt: 8518 → 4885 chars
- Optimized 5 nodes by 50-60%
- Result: Never properly tested, wrong agent

**Iteration 2:**
- Too aggressive (50-60% reduction)
- Achieved 1382ms latency ✅
- But 22% transitions broken ❌
- Had to revert - FAILURE

**Iteration 3:**
- Conservative approach (20-30%)
- Only 60 chars reduced (minimal)
- No significant impact

**Current Approach:**
- Fresh start with clean agent copy
- Proper baseline established
- Real test infrastructure
- Transition validation mandatory
- Conservative optimization (20-30%)

### Success Criteria

**Must Have Both:**
1. ✅ Average latency ≤1500ms
2. ✅ 100% transition correctness

**Cannot Accept:**
- ❌ Fast but broken (Iteration 2 mistake)
- ❌ Slow but correct (not meeting target)

**Only Success Is:**
- ✅✅ Fast AND correct

---

## CONCLUSION

This SOP represents everything learned from 20+ hours of optimization work, including all mistakes made and corrections from the user.

**Key Takeaways:**

1. **No Simulation** - Use real system components always
2. **Test First** - Baseline before optimization
3. **Validate Transitions** - 100% match required, no exceptions
4. **Measure Generation** - Not playback
5. **Deep Tests** - 8+ nodes with objections
6. **Right Keys** - Check api_keys collection
7. **All Databases** - Don't assume missing
8. **Document Everything** - Update SOP with learnings

**If You Follow This SOP:**
- You'll avoid all the mistakes I made
- You'll get accurate measurements
- You'll know if optimization works
- You'll catch transition failures
- You'll reach the target safely

**If You Don't Follow This SOP:**
- You'll repeat my mistakes
- You'll get wrong measurements
- You'll break the agent
- You'll waste 20+ hours

**The Choice Is Yours.**

---

*Last Updated: 2025-11-24*
*Version: 2.0*
*Status: ACTIVE*
