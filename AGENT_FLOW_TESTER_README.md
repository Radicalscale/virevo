# Agent Flow Tester - Documentation

## Overview

The Agent Flow Tester is a powerful tool for testing agent conversation flows **without needing actual phone calls**. It simulates complete conversations by sending text messages to the agent and tracking responses, node transitions, variable extraction, and performance metrics.

## Features

✅ **No Phone Calls Required** - Test agents via text simulation  
✅ **Real Backend Logic** - Uses the actual CallSession and agent processing code  
✅ **Node Transition Tracking** - See exactly which nodes are visited  
✅ **Variable Extraction** - Monitor what variables are extracted during the conversation  
✅ **Latency Measurement** - Track response times for each turn  
✅ **Multiple Scenarios** - Predefined compliant and objection paths  
✅ **Interactive Mode** - Manually type messages to test custom scenarios  
✅ **JSON Export** - Save complete test results for analysis  

## Installation

The tester is already installed at `/app/agent_flow_tester.py`

```bash
chmod +x /app/agent_flow_tester.py
```

## Usage

### Basic Usage - Test with Compliant Scenario

```bash
python3 /app/agent_flow_tester.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --scenario compliant \
  --auto
```

### Interactive Mode - Type Your Own Messages

```bash
python3 /app/agent_flow_tester.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --interactive
```

Then type messages as if you were talking to the agent:
```
👤 YOU: Yes, this is John
🤖 AGENT: [response]

👤 YOU: Tell me more about this
🤖 AGENT: [response]

👤 YOU: quit
```

### Test Objection Handling

```bash
python3 /app/agent_flow_tester.py \
  --agent-id b6b1d141-75a2-43d8-80b8-3decae5c0a92 \
  --scenario objection \
  --auto
```

## Command Line Arguments

| Argument | Required | Description | Example |
|----------|----------|-------------|---------|
| `--agent-id` | Yes | Agent ID to test | `b6b1d141-75a2-43d8-80b8-3decae5c0a92` |
| `--user-id` | No | User ID (defaults to agent owner) | `dcafa642-6136-4096-b77d-a4cb99a62651` |
| `--scenario` | No | Scenario to run: `compliant`, `objection`, `interactive` | `compliant` |
| `--interactive` | No | Run in interactive mode | (flag) |
| `--auto` | No | Auto-continue without pausing between messages | (flag) |

## Predefined Scenarios

### Compliant Path (Happy Path)
Tests a prospect who responds positively at each stage:
1. Confirms name ✅
2. Agrees to help ✅
3. Gives permission for pitch ✅
4. Shows interest ✅
5. Wants extra money ✅
6. Discloses employment status ✅
7. Shares income ($50k) ✅
8. Has side hustle experience (Uber) ✅
9. Made $800/month side income ✅
10. Sees potential in the model ✅

### Objection Path
Tests a prospect with skepticism and objections:
1. Confirms name ✅
2. Shows resistance ("I'm pretty busy") 🚧
3. Time objection ("How much time?") ❓
4. Trust objection ("Is this a scam?") ⚠️
5. Delay objection ("Need to think") ⏸️

## Output

### Real-Time Console Output

```
======================================================================
👤 USER: I make around $50,000 a year
   (Income disclosure)
======================================================================
🤖 AGENT: [Agent's response]

📊 Metrics:
   Latency: 7.69s
   Current Node: 1763176007632
   Should End Call: False
   Variables: {
      "customer_name": "John Smith",
      "employed_yearly_income": "50000"
   }
```

### Summary Report

```
======================================================================
📊 TEST SESSION SUMMARY
======================================================================

🎯 Agent: JK First Caller-copy
   ID: b6b1d141-75a2-43d8-80b8-3decae5c0a92
   Type: call_flow

💬 Conversation Metrics:
   Total Turns: 10
   Total Latency: 19.65s
   Average Latency: 1.97s
   LLM Calls: 10

🗺️  Node Transitions:
   Total Transitions: 10
   Path: 2 → 1763159750250 → 1763161849799 → 1763163400676 → ...

📋 Variables Extracted:
   customer_name: John Smith
   employed_yearly_income: 50000
   side_hustle: 9600

💾 Full results saved to: /app/test_results_[agent_id]_[timestamp].json
```

### JSON Export

Complete test results are saved to `/app/test_results_[agent_id]_[timestamp].json`:

```json
{
  "agent": {
    "id": "b6b1d141-75a2-43d8-80b8-3decae5c0a92",
    "name": "JK First Caller-copy",
    "type": "call_flow"
  },
  "metrics": {
    "total_turns": 10,
    "total_latency": 19.65,
    "llm_calls": 10,
    "node_transitions": 10,
    "variables_extracted": {
      "customer_name": "John Smith",
      "employed_yearly_income": "50000",
      "side_hustle": 9600
    }
  },
  "node_transitions": ["2", "1763159750250", ...],
  "conversation": [
    {
      "turn": 1,
      "user_message": "Yes, this is John",
      "agent_response": "",
      "node_id": "2",
      "latency": 0.00,
      "should_end": false,
      "timestamp": "2025-11-24T04:26:01.286515"
    }
  ]
}
```

## Use Cases

### 1. Test Node Transitions
Verify that transitions work correctly based on user responses:
```bash
python3 /app/agent_flow_tester.py \
  --agent-id YOUR_AGENT_ID \
  --scenario compliant \
  --auto
```

Check the "Node Transitions" section to see the path taken.

### 2. Measure Latency
Identify slow nodes or LLM calls:
```bash
python3 /app/agent_flow_tester.py \
  --agent-id YOUR_AGENT_ID \
  --scenario compliant \
  --auto
```

Review "Average Latency" and individual turn latencies.

### 3. Test Variable Extraction
Verify that variables are extracted correctly:
```bash
python3 /app/agent_flow_tester.py \
  --agent-id YOUR_AGENT_ID \
  --interactive
```

Type messages with specific data (names, dates, amounts) and check "Variables Extracted".

### 4. Test Objection Handling
See how the agent handles objections:
```bash
python3 /app/agent_flow_tester.py \
  --agent-id YOUR_AGENT_ID \
  --scenario objection
```

### 5. Custom Testing
Create your own scenarios by editing the script:
```python
# Add to ConversationScenario class
CUSTOM_SCENARIO = [
    {"message": "Your first message", "description": "Description"},
    {"message": "Your second message", "description": "Description"},
]
```

## How It Works

1. **Loads Agent** - Retrieves agent configuration from MongoDB
2. **Creates Session** - Initializes a CallSession (same as real calls)
3. **Simulates Messages** - Sends text as if it were transcribed speech
4. **Processes Flow** - Uses actual backend logic to determine responses
5. **Tracks State** - Monitors node transitions and variable extraction
6. **Measures Performance** - Records latency for each turn
7. **Exports Results** - Saves complete test data to JSON

## Technical Details

- **Backend Integration**: Uses `calling_service.CallSession` directly
- **Database**: Connects to same MongoDB as production
- **No TTS/STT**: Skips audio generation/transcription (text only)
- **No Webhooks**: Currently skips Telnyx/voice platform calls
- **Session Management**: Creates temporary test sessions with unique IDs

## Limitations

- ⚠️ **Text Only** - No actual audio generation or transcription
- ⚠️ **No Phone Integration** - Telnyx/calling platform not involved
- ⚠️ **Response Text** - Agent responses may be empty (streaming callback not captured)
- ✅ **Flow Works** - Node transitions and variable extraction fully functional

## Recent Test Results

**JK First Caller Agent Test (Compliant Path)**
- ✅ 10 conversation turns completed
- ✅ Average latency: 1.97s per turn
- ✅ All 10 nodes transitioned successfully
- ✅ Variables extracted: customer_name, employed_yearly_income, side_hustle

Path: Greeting → Help Request → Permission → Model Intro → Q&A → Employment → Income → Side Hustle History → Side Hustle Amount → Vehicle Question

## Troubleshooting

### "Agent not found"
- Verify the agent ID exists in the database
- Check you're using the correct database (test_database vs ai_calling_db)

### "Connection error"
- Ensure MongoDB is accessible
- Check MONGO_URL environment variable

### "Empty responses"
- This is expected (streaming responses not captured)
- Node transitions and variables still work correctly

### "Latency too high"
- Check if API keys are configured (OpenAI, etc.)
- Review backend logs for errors
- Test with simpler agents first

## Next Steps

To enhance the tester:
1. **Add TTS Preview** - Generate audio files for responses
2. **Webhook Support** - Actually call external webhooks during tests
3. **Capture Streaming** - Get full agent response text
4. **Batch Testing** - Run multiple scenarios automatically
5. **Comparison Mode** - Compare different agent versions
6. **Performance Benchmarks** - Set latency targets and alerts

## Questions?

For issues or feature requests, document them in the test results JSON or create a new test scenario to reproduce the problem.
