# Agent Tester UI - AI-Powered Testing Upgrade Plan

## Overview

Upgrade the Agent Tester UI to include:
1. **Real TTS measurements** (WebSocket-based, production-identical)
2. **AI-powered testing mode** (LLM acts as the user with configurable skepticism)
3. **Enhanced metrics display** (detailed latency breakdown, TTFB tracking)

---

## Phase 1: Add Real TTS Measurements to UI

### Backend Changes

**File: `/app/backend/agent_test_router.py`**

**Current State:**
- Returns `detailed_timing` with formula-based TTS estimate
- No real TTS measurement

**Changes Needed:**

1. **Add optional real TTS measurement parameter:**
```python
@router.post("/agent_test/{session_id}/send_message")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    measure_real_tts: bool = False  # NEW parameter
):
```

2. **Integrate real TTS measurement:**
```python
# After getting agent response
if measure_real_tts and elevenlabs_api_key:
    # Call real TTS (same as direct_latency_test.py)
    tts_result = await measure_real_tts_time(
        response_text,
        agent_config,
        elevenlabs_api_key
    )
    tts_time = tts_result['tts_time']
    ttfb = tts_result['ttfb']
    tts_method = 'real'
else:
    # Use formula
    tts_time = 0.15 + (word_count * 0.012)
    ttfb = None
    tts_method = 'formula'
```

3. **Return enhanced metrics:**
```python
return {
    "agent_response": response_text,
    "detailed_timing": {
        "llm_time": llm_time,
        "tts_time": tts_time,
        "tts_method": tts_method,
        "ttfb": ttfb,
        "system_overhead": 0.9,
        "total_latency": llm_time + tts_time + 0.9
    },
    "current_node_id": current_node_id,
    "current_node_label": node_label,
    "should_end_call": should_end
}
```

**Estimated Time:** 2 hours

---

### Frontend Changes

**File: `/app/frontend/src/components/AgentTester.jsx`**

**Changes Needed:**

1. **Add TTS measurement toggle:**
```jsx
const [measureRealTTS, setMeasureRealTTS] = useState(false);

// In UI
<div className="settings-section">
  <label>
    <input 
      type="checkbox" 
      checked={measureRealTTS}
      onChange={(e) => setMeasureRealTTS(e.target.checked)}
    />
    Measure Real TTS (costs ~$0.001/turn, 100% accurate)
  </label>
</div>
```

2. **Pass parameter to API:**
```jsx
const response = await fetch(`${backendUrl}/agent_test/${sessionId}/send_message`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    message: userMessage,
    measure_real_tts: measureRealTTS  // NEW
  })
});
```

3. **Enhanced metrics display:**
```jsx
// In message bubble
{msg.detailed_timing && (
  <div className="metrics-detailed">
    <div className="metric-row">
      <span>LLM:</span>
      <span>{msg.detailed_timing.llm_time.toFixed(3)}s</span>
    </div>
    <div className="metric-row">
      <span>TTS ({msg.detailed_timing.tts_method}):</span>
      <span>{msg.detailed_timing.tts_time.toFixed(3)}s</span>
      {msg.detailed_timing.ttfb && (
        <span className="ttfb"> (TTFB: {msg.detailed_timing.ttfb.toFixed(3)}s)</span>
      )}
    </div>
    <div className="metric-row">
      <span>System:</span>
      <span>{msg.detailed_timing.system_overhead.toFixed(3)}s</span>
    </div>
    <div className="metric-row total">
      <span>Total Latency:</span>
      <span className="highlight">{msg.detailed_timing.total_latency.toFixed(3)}s</span>
    </div>
  </div>
)}
```

**Estimated Time:** 2 hours

---

## Phase 2: AI-Powered Testing Mode

### Backend Changes

**File: `/app/backend/agent_test_router.py`**

**New Endpoints:**

1. **Start AI Test Session:**
```python
class AITestConfig(BaseModel):
    agent_id: str
    skepticism_level: str  # "compliant", "neutral", "skeptical", "very_skeptical"
    max_turns: int = 15
    target_latency: float = 2.0

@router.post("/agent_test/ai/start")
async def start_ai_test(config: AITestConfig):
    """
    Start an AI-powered test session
    
    Returns:
        {
            "session_id": "ai_test_xxx",
            "status": "running",
            "turn": 0
        }
    """
    session_id = f"ai_test_{int(time.time())}"
    
    # Initialize session
    ai_test_sessions[session_id] = {
        "agent_id": config.agent_id,
        "skepticism_level": config.skepticism_level,
        "max_turns": config.max_turns,
        "target_latency": config.target_latency,
        "current_turn": 0,
        "conversation_history": [],
        "metrics": [],
        "status": "running"
    }
    
    return {"session_id": session_id, "status": "running", "turn": 0}
```

2. **Get Next AI Turn:**
```python
@router.post("/agent_test/ai/{session_id}/next_turn")
async def ai_next_turn(session_id: str):
    """
    Execute one turn of AI testing:
    1. Generate AI user response (based on agent's last message + skepticism)
    2. Send to agent
    3. Get agent response with metrics
    4. Return both
    """
    session = ai_test_sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    if session['status'] != 'running':
        return {"status": session['status'], "message": "Test completed"}
    
    # Generate AI user response
    ai_response = await generate_ai_user_response(
        conversation_history=session['conversation_history'],
        skepticism_level=session['skepticism_level'],
        agent_last_message=session['conversation_history'][-1] if session['conversation_history'] else None
    )
    
    # Send to agent and get response
    agent_response = await send_message_to_agent(session['agent_id'], ai_response)
    
    # Update session
    session['current_turn'] += 1
    session['conversation_history'].append({
        "turn": session['current_turn'],
        "user": ai_response,
        "agent": agent_response['text'],
        "metrics": agent_response['metrics']
    })
    
    # Check if should end
    if agent_response['should_end'] or session['current_turn'] >= session['max_turns']:
        session['status'] = 'completed'
    
    return {
        "turn": session['current_turn'],
        "user_message": ai_response,
        "agent_response": agent_response['text'],
        "metrics": agent_response['metrics'],
        "status": session['status'],
        "should_continue": session['status'] == 'running'
    }
```

3. **AI Response Generator:**
```python
async def generate_ai_user_response(
    conversation_history: list,
    skepticism_level: str,
    agent_last_message: dict
) -> str:
    """
    Use LLM to generate realistic user response based on:
    - Conversation context
    - Skepticism level
    - Agent's last message
    """
    
    # Define personas for each skepticism level
    PERSONAS = {
        "compliant": {
            "description": "Friendly, interested prospect who agrees easily",
            "traits": ["Asks clarifying questions", "Expresses interest", "Minimal objections"],
            "example_responses": [
                "That sounds interesting, tell me more",
                "Sure, I'd be open to that",
                "Yeah, I could see that working"
            ]
        },
        "neutral": {
            "description": "Average prospect, needs some convincing",
            "traits": ["Asks practical questions", "Some hesitation", "Wants proof"],
            "example_responses": [
                "How does that work exactly?",
                "I'm not sure, can you explain more?",
                "What's the catch?"
            ]
        },
        "skeptical": {
            "description": "Doubtful prospect with common objections",
            "traits": ["Questions credibility", "Brings up MLM concerns", "Needs lots of proof"],
            "example_responses": [
                "This sounds like a pyramid scheme",
                "I've heard this before, why is this different?",
                "How do I know this isn't a scam?"
            ]
        },
        "very_skeptical": {
            "description": "Highly resistant, aggressive objections",
            "traits": ["Hostile tone", "Immediate rejection", "Personal attacks"],
            "example_responses": [
                "Who gave you my number? Take me off your list",
                "This is definitely a scam, I'm reporting you",
                "I'm not interested in your BS"
            ]
        }
    }
    
    persona = PERSONAS[skepticism_level]
    
    # Build conversation context
    context = "\n".join([
        f"Turn {h['turn']}: User: {h['user']}\nAgent: {h['agent']}"
        for h in conversation_history[-3:]  # Last 3 turns for context
    ])
    
    # Generate response using LLM
    prompt = f"""You are simulating a realistic phone conversation as a prospect being called.

PERSONA: {persona['description']}
TRAITS: {', '.join(persona['traits'])}

CONVERSATION SO FAR:
{context}

AGENT JUST SAID: "{agent_last_message['agent'] if agent_last_message else 'Starting call...'}"

Generate a realistic, natural response (10-20 words) that:
1. Sounds like spoken language (use contractions, filler words like "um", "uh")
2. Matches the {skepticism_level} persona
3. Responds to what the agent just said
4. Moves the conversation forward naturally

CRITICAL: 
- Keep it SHORT (10-20 words max)
- Use natural speech patterns
- Don't be overly formal
- Match the emotional tone of the persona

Response:"""
    
    # Call LLM (use gpt-4o-mini for speed)
    response = await call_llm(
        prompt=prompt,
        model="gpt-4o-mini",
        max_tokens=50,
        temperature=0.8  # Higher temp for variety
    )
    
    return response.strip()
```

**Estimated Time:** 6 hours

---

### Frontend Changes

**File: `/app/frontend/src/components/AgentTester.jsx`**

**New UI Components:**

1. **Mode Selector:**
```jsx
const [testMode, setTestMode] = useState('manual'); // 'manual' or 'ai'
const [skepticismLevel, setSkepticismLevel] = useState('neutral');
const [aiTestStatus, setAiTestStatus] = useState('idle'); // 'idle', 'running', 'completed'

<div className="test-mode-selector">
  <button 
    className={testMode === 'manual' ? 'active' : ''}
    onClick={() => setTestMode('manual')}
  >
    Manual Testing
  </button>
  <button 
    className={testMode === 'ai' ? 'active' : ''}
    onClick={() => setTestMode('ai')}
  >
    AI Testing
  </button>
</div>
```

2. **AI Testing Controls:**
```jsx
{testMode === 'ai' && (
  <div className="ai-test-controls">
    <h3>AI Test Configuration</h3>
    
    <div className="skepticism-selector">
      <label>Skepticism Level:</label>
      <select 
        value={skepticismLevel}
        onChange={(e) => setSkepticismLevel(e.target.value)}
        disabled={aiTestStatus === 'running'}
      >
        <option value="compliant">😊 Compliant (Easy prospect)</option>
        <option value="neutral">😐 Neutral (Average prospect)</option>
        <option value="skeptical">🤔 Skeptical (Doubtful prospect)</option>
        <option value="very_skeptical">😠 Very Skeptical (Hostile prospect)</option>
      </select>
    </div>
    
    <div className="persona-description">
      {PERSONA_DESCRIPTIONS[skepticismLevel]}
    </div>
    
    <div className="ai-test-actions">
      {aiTestStatus === 'idle' && (
        <button 
          className="start-ai-test"
          onClick={startAITest}
        >
          🤖 Start AI Test
        </button>
      )}
      
      {aiTestStatus === 'running' && (
        <button 
          className="stop-ai-test"
          onClick={stopAITest}
        >
          ⏸️ Stop Test
        </button>
      )}
      
      {aiTestStatus === 'completed' && (
        <button 
          className="restart-ai-test"
          onClick={restartAITest}
        >
          🔄 Run Again
        </button>
      )}
    </div>
  </div>
)}
```

3. **AI Test Execution:**
```jsx
const startAITest = async () => {
  setAiTestStatus('running');
  setConversation([]);
  
  // Start AI test session
  const response = await fetch(`${backendUrl}/agent_test/ai/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_id: agentId,
      skepticism_level: skepticismLevel,
      max_turns: 15,
      target_latency: 2.0
    })
  });
  
  const { session_id } = await response.json();
  
  // Run conversation loop
  let shouldContinue = true;
  while (shouldContinue && aiTestStatus === 'running') {
    const turnResponse = await fetch(
      `${backendUrl}/agent_test/ai/${session_id}/next_turn`,
      { method: 'POST' }
    );
    
    const turn = await turnResponse.json();
    
    // Add user message
    setConversation(prev => [...prev, {
      role: 'user',
      message: turn.user_message,
      timestamp: new Date().toISOString(),
      isAI: true  // Flag to style differently
    }]);
    
    // Wait a bit for realism
    await sleep(500);
    
    // Add agent response
    setConversation(prev => [...prev, {
      role: 'agent',
      message: turn.agent_response,
      timestamp: new Date().toISOString(),
      metrics: turn.metrics
    }]);
    
    shouldContinue = turn.should_continue;
    
    // Wait before next turn
    await sleep(1000);
  }
  
  setAiTestStatus('completed');
};
```

4. **Enhanced Message Display:**
```jsx
// Differentiate AI-generated user messages
<div className={`message ${msg.role} ${msg.isAI ? 'ai-generated' : ''}`}>
  {msg.isAI && (
    <span className="ai-badge">🤖 AI</span>
  )}
  <div className="message-content">{msg.message}</div>
  {/* ... metrics ... */}
</div>
```

**Estimated Time:** 6 hours

---

## Phase 3: Enhanced Metrics & Visualization

### Frontend Enhancements

**File: `/app/frontend/src/components/AgentTester.jsx`**

**New Features:**

1. **Running Metrics Summary:**
```jsx
const [runningMetrics, setRunningMetrics] = useState({
  totalTurns: 0,
  avgLatency: 0,
  avgLLM: 0,
  avgTTS: 0,
  turnsMeetingTarget: 0
});

// Update after each turn
const updateRunningMetrics = (newMetrics) => {
  setRunningMetrics(prev => {
    const totalTurns = prev.totalTurns + 1;
    return {
      totalTurns,
      avgLatency: (prev.avgLatency * prev.totalTurns + newMetrics.total_latency) / totalTurns,
      avgLLM: (prev.avgLLM * prev.totalTurns + newMetrics.llm_time) / totalTurns,
      avgTTS: (prev.avgTTS * prev.totalTurns + newMetrics.tts_time) / totalTurns,
      turnsMeetingTarget: prev.turnsMeetingTarget + (newMetrics.total_latency <= 2.0 ? 1 : 0)
    };
  });
};

// Display
<div className="metrics-summary">
  <h3>Running Metrics</h3>
  <div className="metric-grid">
    <div className="metric">
      <span className="label">Avg Latency</span>
      <span className={`value ${runningMetrics.avgLatency <= 2.0 ? 'good' : 'bad'}`}>
        {runningMetrics.avgLatency.toFixed(3)}s
      </span>
    </div>
    <div className="metric">
      <span className="label">Avg LLM</span>
      <span className="value">{runningMetrics.avgLLM.toFixed(3)}s</span>
    </div>
    <div className="metric">
      <span className="label">Avg TTS</span>
      <span className="value">{runningMetrics.avgTTS.toFixed(3)}s</span>
    </div>
    <div className="metric">
      <span className="label">Success Rate</span>
      <span className="value">
        {((runningMetrics.turnsMeetingTarget / runningMetrics.totalTurns) * 100).toFixed(0)}%
      </span>
    </div>
  </div>
</div>
```

2. **Latency Chart (Simple Bar Chart):**
```jsx
<div className="latency-chart">
  <h3>Latency per Turn</h3>
  <div className="bars">
    {conversation.filter(m => m.role === 'agent').map((msg, idx) => (
      <div key={idx} className="bar-container">
        <div 
          className={`bar ${msg.metrics?.total_latency > 2.0 ? 'over-target' : 'good'}`}
          style={{ height: `${(msg.metrics?.total_latency / 5) * 100}%` }}
          title={`Turn ${idx + 1}: ${msg.metrics?.total_latency.toFixed(3)}s`}
        />
        <span className="bar-label">{idx + 1}</span>
      </div>
    ))}
  </div>
  <div className="target-line" style={{ bottom: '40%' }}>
    <span>Target: 2.0s</span>
  </div>
</div>
```

3. **Bottleneck Identification:**
```jsx
const identifyBottleneck = (metrics) => {
  const { llm_time, tts_time, system_overhead } = metrics;
  const max = Math.max(llm_time, tts_time, system_overhead);
  
  if (max === llm_time) return { component: 'LLM', time: llm_time, color: 'red' };
  if (max === tts_time) return { component: 'TTS', time: tts_time, color: 'orange' };
  return { component: 'System', time: system_overhead, color: 'blue' };
};

// Display in message
{msg.metrics && (
  <div className="bottleneck-indicator">
    <span className="label">Bottleneck:</span>
    <span 
      className="bottleneck"
      style={{ color: identifyBottleneck(msg.metrics).color }}
    >
      {identifyBottleneck(msg.metrics).component} 
      ({identifyBottleneck(msg.metrics).time.toFixed(3)}s)
    </span>
  </div>
)}
```

**Estimated Time:** 4 hours

---

## Phase 4: Styling & Polish

### CSS Updates

**File: `/app/frontend/src/components/AgentTester.css` (or inline styles)**

**New Styles:**

```css
/* AI Testing Mode */
.test-mode-selector {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.test-mode-selector button {
  flex: 1;
  padding: 12px;
  border: 2px solid #ddd;
  background: white;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.test-mode-selector button.active {
  background: #4CAF50;
  color: white;
  border-color: #4CAF50;
}

/* Skepticism Selector */
.skepticism-selector {
  margin: 20px 0;
}

.skepticism-selector select {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 2px solid #ddd;
  font-size: 16px;
}

.persona-description {
  padding: 15px;
  background: #f5f5f5;
  border-radius: 8px;
  margin: 15px 0;
  font-style: italic;
  color: #666;
}

/* AI Generated Badge */
.message.ai-generated {
  border-left: 3px solid #2196F3;
}

.ai-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #2196F3;
  color: white;
  border-radius: 12px;
  font-size: 12px;
  margin-right: 8px;
}

/* Enhanced Metrics */
.metrics-detailed {
  margin-top: 10px;
  padding: 10px;
  background: #f9f9f9;
  border-radius: 6px;
  font-size: 13px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  margin: 4px 0;
}

.metric-row.total {
  border-top: 1px solid #ddd;
  padding-top: 8px;
  margin-top: 8px;
  font-weight: bold;
}

.ttfb {
  font-size: 11px;
  color: #666;
}

/* Running Metrics Summary */
.metrics-summary {
  position: sticky;
  top: 0;
  background: white;
  border: 2px solid #ddd;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  z-index: 10;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-top: 10px;
}

.metric {
  text-align: center;
}

.metric .label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.metric .value {
  display: block;
  font-size: 24px;
  font-weight: bold;
}

.metric .value.good {
  color: #4CAF50;
}

.metric .value.bad {
  color: #f44336;
}

/* Latency Chart */
.latency-chart {
  margin: 20px 0;
  padding: 20px;
  background: white;
  border: 2px solid #ddd;
  border-radius: 8px;
  position: relative;
  height: 200px;
}

.bars {
  display: flex;
  gap: 10px;
  height: 150px;
  align-items: flex-end;
}

.bar-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.bar {
  width: 100%;
  background: #4CAF50;
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
}

.bar.over-target {
  background: #f44336;
}

.bar-label {
  margin-top: 5px;
  font-size: 12px;
  color: #666;
}

.target-line {
  position: absolute;
  left: 20px;
  right: 20px;
  border-top: 2px dashed #666;
  pointer-events: none;
}

.target-line span {
  position: absolute;
  right: 0;
  top: -20px;
  font-size: 12px;
  color: #666;
}

/* Bottleneck Indicator */
.bottleneck-indicator {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #eee;
  font-size: 12px;
}

.bottleneck {
  font-weight: bold;
  margin-left: 5px;
}
```

**Estimated Time:** 3 hours

---

## Implementation Timeline

### Total Estimated Time: 23 hours

**Week 1 (8 hours):**
- Day 1-2: Phase 1 - Real TTS measurements (4 hours)
  - Backend integration (2h)
  - Frontend display (2h)

**Week 2 (15 hours):**
- Day 3-4: Phase 2 - AI Testing Backend (6 hours)
  - Endpoints (3h)
  - AI response generator (3h)
- Day 5-6: Phase 2 - AI Testing Frontend (6 hours)
  - UI components (3h)
  - Test execution flow (3h)
- Day 7: Phase 3 - Enhanced Metrics (4 hours)
  - Running metrics (2h)
  - Charts and visualizations (2h)

**Week 3 (3 hours):**
- Day 8: Phase 4 - Styling & Polish (3 hours)

---

## Testing Checklist

### Phase 1 Testing
- [ ] Real TTS measurement toggle works
- [ ] Metrics display correctly shows real vs formula
- [ ] TTFB is tracked and displayed
- [ ] Formula fallback works when API key missing

### Phase 2 Testing
- [ ] AI test starts successfully for each skepticism level
- [ ] Conversation flows naturally (10-15 turns)
- [ ] AI responses are realistic and match persona
- [ ] Test stops correctly when agent ends call
- [ ] Test stops at max turns
- [ ] User can stop test mid-conversation

### Phase 3 Testing
- [ ] Running metrics update correctly
- [ ] Charts display properly
- [ ] Bottleneck identification is accurate
- [ ] Success rate calculation is correct

### Phase 4 Testing
- [ ] UI is responsive
- [ ] Styling looks professional
- [ ] Animations work smoothly
- [ ] Dark/light mode compatible (if applicable)

---

## Risk Mitigation

### Potential Issues

1. **AI responses too generic/boring**
   - Solution: Add more detailed personas with example responses
   - Use higher temperature (0.8-0.9) for variety
   - Include conversation context in prompts

2. **AI test runs too fast**
   - Solution: Add realistic delays between turns (500ms-1s)
   - Show "AI is typing..." indicator

3. **TTS measurements slow down UI**
   - Solution: Make TTS measurement optional (default off)
   - Show loading indicator during measurement
   - Cache results for same response text

4. **API costs add up quickly**
   - Solution: Display cost estimate before starting
   - Add warning if > 10 tests per session
   - Provide formula-based mode as default

---

## Success Metrics

### Key Performance Indicators

1. **Accuracy**: Real TTS measurements within ±50ms of production
2. **Usability**: Users can start AI test in < 30 seconds
3. **Quality**: AI responses rated "realistic" by users > 80% of time
4. **Performance**: UI remains responsive during AI tests
5. **Adoption**: Users run AI tests > 50% of manual tests

---

## Future Enhancements (Out of Scope)

- Export test results as JSON/CSV
- Compare multiple test runs side-by-side
- Custom skepticism level definitions
- Multi-turn conversation branching
- Voice-to-voice testing (real audio in/out)
- A/B testing different agent configurations
- Automated regression testing suite

---

## Conclusion

This upgrade will transform the Agent Tester from a manual tool into a powerful automated testing and optimization platform. Users will be able to:

1. **Measure real performance** with production-identical TTS
2. **Automate testing** with AI-powered conversations
3. **Identify bottlenecks** quickly with detailed metrics
4. **Optimize faster** by testing different skepticism levels

**Recommended Approach:** Implement in phases, testing thoroughly after each phase before moving to the next.
