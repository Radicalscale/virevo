# Agent Tester UI - Complete Documentation

## Overview

The Agent Tester UI is a powerful web-based tool for testing conversation agents without making actual phone calls. It provides a chat-like interface where you can simulate user responses and see real-time agent behavior, node transitions, variable extraction, and performance metrics.

## Features

✅ **Works with ANY Agent** - Test any call_flow or single_prompt agent  
✅ **Real-Time Chat Interface** - Natural conversation-style testing  
✅ **Live Metrics Dashboard** - See latency, node transitions, and variables as you chat  
✅ **Node Transition Tracking** - Visual path through your call flow  
✅ **Variable Extraction Monitoring** - Watch what data the agent captures  
✅ **Session Management** - Start, reset, and export test sessions  
✅ **Export Results** - Download complete test data as JSON  

## Access

### From Agents Page
1. Go to `/agents`
2. Find the agent you want to test
3. Click the **🧪 Test** button (cyan/teal colored)

### Direct URL
Navigate to: `/agents/{agent_id}/test`

## Interface Layout

### Left Panel (2/3 width) - Conversation
- **Chat Interface**: Messages displayed in chat bubbles
  - Blue bubbles (right): Your messages
  - Gray bubbles (left): Agent responses
- **Message Info**: Each agent response shows:
  - Latency time (e.g., "2.34s")
  - Current node ID
- **Input Field**: Type your message at the bottom
- **Send Button**: Submit your message (or press Enter)

### Right Panel (1/3 width) - Metrics

#### 1. Metrics Card
- **Total Turns**: Number of conversation exchanges
- **Avg Latency**: Average response time per turn
- **Total Latency**: Cumulative time spent

#### 2. Current Node Card
- Shows the node ID the agent is currently on
- Updates after each message

#### 3. Node Transitions Card
- Numbered list of all nodes visited
- Scroll to see full path through the flow
- Helps identify conversation patterns

#### 4. Variables Extracted Card
- All variables captured by the agent
- Shows variable name and current value
- Updates in real-time as variables are extracted

## Usage Flow

### 1. Start Testing
**Option A:** Click Test button from Agents page  
**Option B:** Navigate directly to `/agents/{agent_id}/test`

### 2. Send Messages
- Type your message in the input field
- Press Enter or click Send button
- Wait for agent response
- Repeat to continue conversation

### 3. Monitor Progress
- Watch node transitions in real-time
- See variables being extracted
- Track latency for performance tuning

### 4. Reset or Export
- **Reset**: Clear conversation and start fresh
- **Export**: Download complete test results as JSON

## Example Test Flow

### Testing JK First Caller Agent

```
YOU: Yes, this is John
AGENT: "Great! Can you help me out with something?"
Node: 1763159750250 | Latency: 1.2s

YOU: Sure, I can help
AGENT: "I'm calling because you filled out an ad..."
Node: 1763161849799 | Latency: 0.8s

YOU: Yes, go ahead
AGENT: [Model introduction]
Node: 1763163400676 | Latency: 1.5s
```

**Metrics Panel Shows:**
- Total Turns: 3
- Avg Latency: 1.17s
- Variables: { customer_name: "John" }
- Node Path: 2 → 1763159750250 → 1763161849799 → 1763163400676

## Key Features Explained

### 1. Session Management

**Auto-Start**: First message automatically starts a session  
**Persistent**: Session stays active until you reset or leave  
**Reset**: Clears conversation but keeps same agent  

### 2. Real-Time Updates

Every response updates:
- ✅ Conversation history
- ✅ Current node
- ✅ Node transitions list
- ✅ Variables extracted
- ✅ Metrics calculations

### 3. Variable Tracking

The agent extracts variables as you chat:
```
Turn 1: { customer_name: "John" }
Turn 3: { customer_name: "John", employed_yearly_income: "50000" }
Turn 5: { customer_name: "John", employed_yearly_income: "50000", side_hustle: 9600 }
```

### 4. Export Functionality

Downloaded JSON contains:
```json
{
  "agent": {
    "id": "...",
    "name": "JK First Caller",
    "type": "call_flow"
  },
  "session_id": "...",
  "conversation": [...],
  "metrics": {...},
  "node_transitions": [...],
  "variables": {...},
  "timestamp": "2025-11-24T04:00:00.000Z"
}
```

## API Endpoints (Backend)

### POST `/api/agents/{agent_id}/test/start`
Start a new test session
- **Returns**: session_id, agent info

### POST `/api/agents/{agent_id}/test/message`
Send a message in active session
- **Body**: `{ message, session_id }`
- **Returns**: Full session state + response

### GET `/api/agents/{agent_id}/test/session/{session_id}`
Get current session state
- **Returns**: Conversation, metrics, variables

### POST `/api/agents/{agent_id}/test/reset`
Reset session (clear conversation)
- **Body**: `{ session_id }`

### DELETE `/api/agents/{agent_id}/test/session/{session_id}`
Delete session completely

## Technical Details

### Backend
- **File**: `/app/backend/agent_test_router.py`
- **Storage**: In-memory sessions (per server instance)
- **Session Logic**: Uses CallSession class (same as real calls)
- **Processing**: Real LLM calls, actual node transitions

### Frontend
- **File**: `/app/frontend/src/components/AgentTester.jsx`
- **Route**: `/agents/:id/test`
- **State Management**: React useState
- **API Calls**: Fetch API with credentials

## Use Cases

### 1. Test Call Flow Logic
Verify that transitions work correctly:
```
Test: "I'm interested" → Should go to qualification node
Test: "Not interested" → Should go to objection handler
```

### 2. Optimize Response Latency
Identify slow nodes:
```
Node A: 0.8s ✅ Fast
Node B: 3.2s ⚠️ Slow - needs optimization
Node C: 1.1s ✅ Fast
```

### 3. Verify Variable Extraction
Ensure agent captures correct data:
```
Input: "I make $50,000 a year"
Expected: { employed_yearly_income: "50000" }
Actual: { employed_yearly_income: "50000" } ✅
```

### 4. Test Objection Handling
See how agent responds to pushback:
```
YOU: "Is this a scam?"
AGENT: [Should handle objection gracefully]
```

### 5. Debug Node Transitions
Understand unexpected behavior:
```
Expected path: A → B → C → D
Actual path: A → B → E → D
Issue: Condition not matching correctly
```

## Comparison: UI vs CLI

| Feature | UI Tester | CLI Tester (`agent_flow_tester.py`) |
|---------|-----------|--------------------------------------|
| **Access** | Web browser | Command line |
| **UI** | ✅ Beautiful chat interface | ❌ Terminal text |
| **Real-Time** | ✅ Live updates | ❌ Batch results |
| **Metrics** | ✅ Visual dashboard | ✅ Summary at end |
| **Interactive** | ✅ Type freely | ✅ Interactive mode available |
| **Export** | ✅ Download JSON | ✅ Auto-save JSON |
| **Scenarios** | ❌ Manual only | ✅ Predefined scenarios |
| **Automation** | ❌ Manual testing | ✅ Can script tests |

## Troubleshooting

### "Failed to start test session"
- ✅ Check you're logged in
- ✅ Verify agent belongs to your account
- ✅ Check backend logs for errors

### "Empty agent responses"
- ⚠️ This is expected in some cases
- ✅ Node transitions still work correctly
- ✅ Variables still extracted
- ✅ Streaming responses not fully captured yet

### "Session not found"
- ✅ Click Reset to create new session
- ✅ Sessions are per-server (cleared on restart)

### High latency
- ⏱️ First message often slower (cold start)
- ⏱️ Subsequent messages faster
- ⏱️ Check API keys configured correctly

## Future Enhancements

Potential improvements:
- [ ] Save test sessions to database
- [ ] Replay saved conversations
- [ ] Compare agent versions
- [ ] Batch testing with scenarios
- [ ] Performance benchmarks and alerts
- [ ] Visual flow diagram with highlighting
- [ ] TTS audio preview for responses
- [ ] Export to various formats (PDF, CSV)

## Best Practices

### 1. Test Early, Test Often
- Test after every flow change
- Verify transitions before deployment
- Check edge cases

### 2. Use Realistic Messages
- Type like real users would
- Include typos and variations
- Test objections and questions

### 3. Track Metrics
- Note avg latency for baselines
- Identify slow nodes
- Compare before/after changes

### 4. Export Important Tests
- Save successful test runs
- Document edge cases
- Share with team

### 5. Test All Paths
- Happy path (compliant)
- Objection paths
- Edge cases and errors

## Security Notes

- ✅ Requires authentication
- ✅ Users can only test their own agents
- ✅ Sessions isolated per user
- ✅ No phone system involved (safer testing)

## Performance

- **Session Storage**: In-memory (fast but not persistent)
- **Concurrent Sessions**: Supports multiple users
- **API Calls**: Real LLM calls (same as production)
- **Database**: Reads agent config, no writes during tests

## Keyboard Shortcuts

- **Enter**: Send message
- **Escape**: (Future) Clear input field
- **Ctrl+R**: (Use Reset button instead)

## Related Documentation

- **CLI Tester**: `/app/AGENT_FLOW_TESTER_README.md`
- **Backend API**: `/app/backend/agent_test_router.py`
- **Frontend Component**: `/app/frontend/src/components/AgentTester.jsx`

## Questions & Feedback

For issues or feature requests:
1. Test the problematic scenario
2. Export the test results
3. Share the JSON with description of issue

---

**Version**: 1.0  
**Last Updated**: November 24, 2025  
**Status**: ✅ Production Ready
