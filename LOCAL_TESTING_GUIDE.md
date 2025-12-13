# Local Agent Testing Guide - Avoid 10+ Minute Deployment Cycles

## Problem

Railway deployments take 10+ minutes to test each change. If you need 50 tests to optimize an agent, that's **8+ hours of waiting**.

## Solution

Test agents **locally** in your development environment before deploying to Railway. Make all changes, test them locally, and deploy only when everything works.

## How It Works

The local tester:
- ✅ Uses the **same code** as production (CallSession, LLM calls, etc.)
- ✅ Connects to the **same MongoDB** as production
- ✅ Makes **real LLM API calls**
- ✅ Profiles latency to identify bottlenecks
- ✅ No Redis required (uses in-memory fallback like production does when Redis is unavailable)
- ✅ **Instant feedback** - no deployment needed

## Quick Start

### Test an Agent Interactively

```bash
python3 /app/local_agent_tester.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --interactive \
  --profile
```

Then type messages as if you were the user:
```
👤 YOU: Yeah, this is Mike
🤖 AGENT: Mike Rodriguez?
📊 Metrics: Total Latency: 0.062s

👤 YOU: Sure, what do you need?
🤖 AGENT: This is Jake. I was just wondering...
📊 Metrics: Total Latency: 1.234s
```

### Run a Predefined Scenario

**Compliant Path (10 messages):**
```bash
python3 /app/local_agent_tester.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --scenario compliant \
  --profile \
  --auto
```

**With Objections (5 messages):**
```bash
python3 /app/local_agent_tester.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --scenario objections \
  --profile \
  --auto
```

**Quick Test (3 messages):**
```bash
python3 /app/local_agent_tester.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --scenario quick \
  --profile \
  --auto
```

### Profile Latency

Add `--profile` flag to any command:
```bash
python3 /app/local_agent_tester.py \
  --agent-id YOUR_AGENT_ID \
  --interactive \
  --profile
```

You'll see:
```
🔍 Latency Breakdown:
   Message Processing: 1.234s
   Other Overhead: 0.056s

======================================================================
LATENCY PROFILING SUMMARY
======================================================================

total_turn:
  Average: 1.290s
  Min: 0.062s
  Max: 3.456s
  Samples: 10

process_input:
  Average: 1.234s
  Min: 0.062s
  Max: 3.400s
  Samples: 10
```

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--agent-id` | Agent ID to test (required) | `--agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92` |
| `--user-id` | User ID (optional, defaults to agent owner) | `--user-id dcafa642-6136-4096-b77d` |
| `--scenario` | Predefined scenario: `compliant`, `objections`, `quick` | `--scenario compliant` |
| `--interactive` | Interactive mode (type messages manually) | `--interactive` |
| `--profile` | Enable latency profiling | `--profile` |
| `--auto` | Auto-continue without pausing between messages | `--auto` |

## Workflow: Optimize Then Deploy

### Step 1: Test Locally
```bash
# Run a complete conversation locally
python3 /app/local_agent_tester.py \
  --agent-id YOUR_AGENT_ID \
  --scenario compliant \
  --profile \
  --auto
```

### Step 2: Analyze Latency
Look at the profiling summary:
```
LATENCY PROFILING SUMMARY
======================================================================

total_turn:
  Average: 2.450s  ← TOO SLOW!
  Min: 0.062s
  Max: 5.670s      ← Find out why this turn took 5.6s
  Samples: 10

process_input:
  Average: 2.390s
```

### Step 3: Identify Bottlenecks

Check the conversation log to see which turn was slow:
```bash
cat /app/local_test_YOUR_AGENT_ID_*.json | jq '.conversation[] | select(.latency > 3)'
```

### Step 4: Make Changes

Edit your agent configuration, node prompts, or backend code.

### Step 5: Test Again Locally

```bash
python3 /app/local_agent_tester.py \
  --agent-id YOUR_AGENT_ID \
  --scenario compliant \
  --profile \
  --auto
```

**Repeat steps 2-5 until latency is acceptable.**

### Step 6: Deploy Once

When everything works locally:
```bash
# Push your changes
git add .
git commit -m "Optimized agent latency"
git push

# Railway will auto-deploy (10 minutes)
```

## Predefined Scenarios

### Compliant Scenario (10 turns)
```python
1. "Yeah, this is Mike" - Confirm name
2. "Sure, what do you need?" - Agree to help
3. "I guess so, go ahead" - Permission for pitch
4. "That sounds interesting, tell me more" - Show interest
5. "Yeah, I'd love some extra money" - $20k question
6. "I work full-time as a manager" - Employment status
7. "I make around $65,000 a year" - Income disclosure
8. "Yeah, I did Uber Eats for a few months" - Side hustle
9. "I was making about $600 a month" - Side hustle income
10. "Yeah, I can see that working" - Vehicle question
```

### Objections Scenario (5 turns)
```python
1. "Yeah, this is Mike" - Confirm name
2. "I'm pretty busy, what is this?" - Initial resistance
3. "Is this an MLM thing?" - MLM objection
4. "I don't know, sounds sketchy" - Trust objection
5. "I need to think about it" - Delay objection
```

### Quick Scenario (3 turns)
```python
1. "Yeah, this is Mike" - Confirm name
2. "Sure" - Agree to help
3. "Go ahead" - Permission
```

## Output Files

Results are saved to JSON files:
```bash
/app/local_test_YOUR_AGENT_ID_TIMESTAMP.json
```

Example:
```json
{
  "agent": {
    "id": "b6b1d141-75a2-43d8-80b8-3decae5c0a92",
    "name": "JK First Caller-copy",
    "type": "call_flow"
  },
  "metrics": {
    "total_turns": 10,
    "total_latency": 24.50,
    "llm_calls": 10
  },
  "conversation": [
    {
      "turn": 1,
      "user_message": "Yeah, this is Mike",
      "agent_response": "Mike Rodriguez?",
      "node_id": "2",
      "latency": 0.062,
      "should_end": false
    }
  ],
  "profiling": {
    "total_turn": [0.062, 1.234, 2.456, ...],
    "process_input": [0.062, 1.200, 2.400, ...]
  }
}
```

## Interactive Mode Commands

While in interactive mode:
- Type your message and press Enter
- Type `profile` to see latency summary
- Type `quit` or `exit` to end session
- Press Ctrl+C to exit

## Common Use Cases

### 1. Test a New Agent Before Deploying
```bash
python3 /app/local_agent_tester.py \
  --agent-id NEW_AGENT_ID \
  --interactive
```

### 2. Optimize Latency for Existing Agent
```bash
# Test current performance
python3 /app/local_agent_tester.py \
  --agent-id AGENT_ID \
  --scenario compliant \
  --profile \
  --auto

# Make changes to agent configuration

# Test again
python3 /app/local_agent_tester.py \
  --agent-id AGENT_ID \
  --scenario compliant \
  --profile \
  --auto

# Compare results
```

### 3. Test Objection Handling
```bash
python3 /app/local_agent_tester.py \
  --agent-id AGENT_ID \
  --scenario objections \
  --auto
```

### 4. Stress Test with Multiple Scenarios
```bash
# Run all scenarios
for scenario in compliant objections quick; do
  echo "Testing $scenario..."
  python3 /app/local_agent_tester.py \
    --agent-id AGENT_ID \
    --scenario $scenario \
    --profile \
    --auto
done
```

## Comparison: Local vs Railway

| Aspect | Local Testing | Railway Testing |
|--------|---------------|-----------------|
| **Setup Time** | 0 seconds | 10+ minutes |
| **Iteration Speed** | Instant | 10+ minutes per test |
| **Cost** | Free (local) | Uses Railway build minutes |
| **Environment** | Same code, same DB, same APIs | Production environment |
| **Redis** | In-memory fallback | Real Redis |
| **Latency** | Real measurements | Real measurements |
| **50 Tests** | ~30 minutes | ~8+ hours |

## Time Savings Calculation

**Without Local Testing:**
- 50 tests × 10 minutes = **500 minutes (8.3 hours)**

**With Local Testing:**
- 45 tests locally × 1 minute = 45 minutes
- 5 final tests on Railway × 10 minutes = 50 minutes
- **Total: 95 minutes (1.6 hours)**

**Time Saved: 6.7 hours (405 minutes)**

## Technical Details

### What's Different from Production?

**Same as Production:**
- ✅ MongoDB connection
- ✅ Agent configuration
- ✅ LLM API calls (OpenAI, etc.)
- ✅ CallSession logic
- ✅ Node transitions
- ✅ Variable extraction

**Different from Production:**
- ⚠️ No Redis (uses in-memory fallback - same as production does when Redis unavailable)
- ⚠️ No webhooks (Telnyx call events)
- ⚠️ No audio generation (TTS/STT)
- ⚠️ Running locally instead of Railway container

### Environment Variables

The local tester uses:
- `MONGO_URL` - MongoDB connection (same as production)
- `DB_NAME` - Database name (same as production)
- All API keys from your environment (OpenAI, etc.)

Make sure your local environment has the same `.env` file as production.

## Troubleshooting

### "Agent not found"
- Check the agent ID is correct
- Verify agent exists in database
- Ensure you're using the correct DB_NAME

### "Connection error"
- Check MONGO_URL in your environment
- Ensure MongoDB is accessible
- Verify network connectivity

### High latency locally
- Check your internet connection
- Verify API keys are configured
- Test with simpler agent first

### "Module not found"
- Ensure backend dependencies installed: `pip install -r /app/backend/requirements.txt`

## Best Practices

1. **Test locally first** - Make all changes and test before deploying
2. **Use profiling** - Always add `--profile` to identify bottlenecks
3. **Test multiple scenarios** - Run compliant, objections, and edge cases
4. **Compare results** - Test before and after changes
5. **Deploy once** - When everything works locally, deploy to Railway

## Next Steps

1. Run your first local test:
   ```bash
   python3 /app/local_agent_tester.py \
     --agent-id YOUR_AGENT_ID \
     --interactive \
     --profile
   ```

2. Try a scenario:
   ```bash
   python3 /app/local_agent_tester.py \
     --agent-id YOUR_AGENT_ID \
     --scenario compliant \
     --profile \
     --auto
   ```

3. Optimize your agent based on profiling results

4. Deploy when ready!

---

**Remember**: Test locally, deploy once. Save hours of waiting! 🚀
