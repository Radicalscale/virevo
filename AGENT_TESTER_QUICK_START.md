# Agent Tester - Quick Start Guide

## 🎯 How to Access

### Step 1: Go to the Agents Page
Navigate to: **https://li-ai.org/agents**

### Step 2: Find the Test Button
On each agent card, you'll see **5 buttons** in a row at the bottom:

```
┌─────────────────────────────────────────────────────┐
│  Agent Card: "JK First Caller"                      │
│  Stats: Calls, Latency, Success Rate               │
│                                                     │
│  [🌿] [🧪] [✏️] [📋] [🗑️]                          │
│  Flow  Test Edit Copy Delete                       │
└─────────────────────────────────────────────────────┘
```

**Button Colors:**
- **Purple** 🌿 - Flow (Edit Call Flow)
- **Cyan/Teal** 🧪 - **TEST** ← This is the new button!
- **Blue** ✏️ - Edit (Agent Settings)
- **Green** 📋 - Duplicate
- **Red** 🗑️ - Delete

### Step 3: Click the Test Button
Click the **cyan/teal colored button** (2nd from left) with a flask/beaker icon 🧪

This will open the Agent Tester interface!

---

## 💬 How It Works

### The Interface

Once you click Test, you'll see a screen split into two panels:

```
┌──────────────────────────────────────────┬─────────────────────┐
│  LEFT PANEL (Chat)                       │  RIGHT PANEL        │
│  ════════════════════════                │  (Metrics)          │
│                                          │                     │
│  [Agent Response]                        │  📊 Metrics         │
│  "Hello! Can you help me?"               │  Turns: 2           │
│                                          │  Latency: 1.5s      │
│       [Your Message] ─────────►          │                     │
│       "Yes, I can help"                  │  🎯 Current Node    │
│                                          │  Node: 12345        │
│  [Agent Response]                        │                     │
│  "Great! Tell me more..."                │  🗺️ Transitions     │
│                                          │  1 → 2 → 3 → 4      │
│  ┌─────────────────────────────┐        │                     │
│  │ Type your message...        │        │  📋 Variables       │
│  └─────────────────────────────┘ [Send] │  name: John         │
└──────────────────────────────────────────┴─────────────────────┘
```

### Step-by-Step Usage

**1. Type Your First Message**
```
Type in the input box at the bottom, like:
"Yes, this is John"
```

**2. Press Enter or Click Send**
```
The message is sent to the agent
```

**3. Watch the Agent Respond**
```
You'll see:
- Agent's response appear in a gray chat bubble
- Response latency (e.g., "1.2s")
- Current node ID updating
- Metrics updating on the right
```

**4. Continue the Conversation**
```
Type your next response based on what the agent said
Example: "Sure, I'd love to hear more"
```

**5. Monitor Real-Time Updates**
```
RIGHT PANEL shows:
✅ Total conversation turns
✅ Average response time
✅ Path through nodes
✅ Variables extracted (name, income, etc.)
```

---

## 📝 Example Test Session

### Testing "JK First Caller" Agent

**Turn 1:**
```
YOU: Yes, this is John
AGENT: "Great! Can you help me out real quick?"
└─ Latency: 0.8s | Node: 1763159750250
```

**Turn 2:**
```
YOU: Sure, I can help
AGENT: "I'm calling because you filled out an ad about stacking income..."
└─ Latency: 1.2s | Node: 1763161849799
```

**Turn 3:**
```
YOU: Yes, go ahead
AGENT: [Explains the business model]
└─ Latency: 1.5s | Node: 1763163400676
```

**Metrics Panel Shows:**
```
📊 Metrics:
   Total Turns: 3
   Avg Latency: 1.17s

🎯 Current Node:
   1763163400676

🗺️ Transitions:
   1. 2
   2. 1763159750250
   3. 1763161849799
   4. 1763163400676

📋 Variables:
   customer_name: John
```

---

## 🔄 Reset & Export

### Reset Button (Top Right)
- Clears the conversation
- Keeps the same agent
- Starts fresh

### Export Button (Top Right)
- Downloads test results as JSON
- Includes full conversation
- Includes all metrics
- Useful for sharing or documentation

---

## 🎯 What Can You Test?

### 1. **Happy Path (Compliant User)**
Test when user says "yes" to everything:
```
YOU: Yes, this is me
YOU: Sure, I'm interested
YOU: That sounds great
YOU: I make $50,000 a year
YOU: Yes, I can see that working
```

### 2. **Objection Handling**
Test when user pushes back:
```
YOU: I'm not sure about this
YOU: Is this a scam?
YOU: I don't have time
YOU: That's too expensive
```

### 3. **Edge Cases**
Test unusual responses:
```
YOU: Maybe
YOU: I need to think about it
YOU: Can you call back later?
YOU: I'm not interested
```

### 4. **Variable Extraction**
Test if agent captures data correctly:
```
YOU: I make around $50,000 a year
Expected: variable "employed_yearly_income" = "50000"

YOU: My name is Sarah Johnson
Expected: variable "customer_name" = "Sarah Johnson"
```

### 5. **Node Transitions**
Verify agent follows correct path:
```
Expected: Node A → Node B → Node C
Actual: Check "Node Transitions" panel
```

---

## 💡 Pro Tips

### ✅ DO:
- **Test early and often** - Catch issues before deployment
- **Type realistically** - Include typos, variations, hesitations
- **Check all paths** - Test both positive and negative responses
- **Monitor latency** - Identify slow nodes that need optimization
- **Export important tests** - Save successful test runs as documentation

### ❌ DON'T:
- Don't skip edge cases - Test objections and unusual responses
- Don't ignore metrics - High latency = user frustration
- Don't test only happy path - Real users push back

---

## 🔍 Understanding the Metrics

### Total Turns
```
Number of back-and-forth exchanges
Turn 1 = You → Agent
Turn 2 = You → Agent
Total: 2 turns
```

### Average Latency
```
How long agent takes to respond (on average)
Good: < 2 seconds
Okay: 2-3 seconds
Slow: > 3 seconds (needs optimization)
```

### Node Transitions
```
Shows the exact path through your call flow
Example: 2 → 1763159750250 → 1763161849799

Use this to:
- Verify transitions work correctly
- Debug unexpected paths
- Understand conversation flow
```

### Variables Extracted
```
Data the agent captured from the conversation
Example:
- customer_name: "John Smith"
- employed_yearly_income: "50000"
- side_hustle: 9600

Use this to:
- Verify data extraction works
- Check variable names are correct
- Ensure values are formatted properly
```

---

## ❓ FAQ

### Q: Where is the Test button?
**A:** On the Agents page (`/agents`), each agent card has 5 buttons at the bottom. The Test button is the **2nd button from the left** (cyan/teal color with flask icon 🧪)

### Q: Can I test any agent?
**A:** Yes! Works with all call_flow and single_prompt agents. Not limited to specific agents.

### Q: Do I need to make a phone call?
**A:** No! This is text-based testing. No phone calls required.

### Q: Are responses real or simulated?
**A:** Real! It uses the actual backend logic and makes real LLM calls, just like production.

### Q: Can I save my test sessions?
**A:** Yes! Click the "Export" button to download test results as JSON.

### Q: Why are some responses empty?
**A:** This can happen with streaming responses. The node transitions and metrics still work correctly.

### Q: How do I test a different scenario?
**A:** Click "Reset" to clear the conversation and start fresh with new messages.

### Q: Can multiple people test the same agent?
**A:** Yes! Each user gets their own isolated test session.

---

## 🚀 Quick Access

### From Agents Page:
```
1. Go to https://li-ai.org/agents
2. Find your agent
3. Click the cyan 🧪 Test button (2nd from left)
4. Start typing messages!
```

### Direct URL:
```
https://li-ai.org/agents/{agent_id}/test

Replace {agent_id} with your agent's ID
Example: https://li-ai.org/agents/b6b1d141-75a2-43d8-80b8-3decae5c0a92/test
```

---

## 📞 Need Help?

If you have issues:
1. Check you're logged in
2. Verify the agent belongs to you
3. Try refreshing the page
4. Check backend logs for errors
5. Export and share test results for debugging

---

**Happy Testing! 🎉**
