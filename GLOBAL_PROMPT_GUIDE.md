# Global Prompt Feature Documentation

## What is a Global Prompt?

A **Global Prompt** (also called `system_prompt` in the database) is a universal set of instructions that applies across ALL nodes in your call flow agent. Think of it as the agent's personality, character traits, and behavioral guidelines that persist no matter which node they're currently in.

## How It Works

### Layer Structure

```
┌─────────────────────────────────────┐
│   GLOBAL PROMPT (Universal)         │  ← Always active
│   - Persona & character traits      │
│   - Universal behavior rules         │
│   - Recovery strategies              │
│   - Communication style              │
└─────────────────────────────────────┘
           ↓ Applied to ↓
┌─────────────────────────────────────┐
│   NODE-SPECIFIC CONTENT (Local)     │  ← Changes per node
│   - Script: exact text to say       │
│   - Prompt: specific instructions   │
│   - Goal: what to accomplish        │
└─────────────────────────────────────┘
```

### Usage Scenarios

1. **Script Mode Nodes**
   - Normally: Says exact script text
   - When repeating (transition not matched): Uses global prompt + node goal to generate intelligent recovery response

2. **Prompt Mode Nodes**
   - Always: Uses global prompt as foundation + node instructions as task

3. **Recovery from Confusion**
   - When user says something unexpected
   - Agent uses global prompt to stay in character while handling the situation

## Benefits

### ✅ Consistent Personality
Without global prompt:
- Node 1: Agent sounds professional
- Node 2: Agent sounds casual
- Node 3: Agent sounds robotic

With global prompt:
- ALL nodes: Agent maintains "Jake" personality consistently

### ✅ Intelligent Recovery
Without global prompt:
```
Agent: "What's your yearly income?"
User: "I don't know, maybe 50k?"
Agent: "Sorry, I didn't quite catch that. What's your yearly income?"  ❌ Robotic
```

With global prompt + goal:
```
Agent: "What's your yearly income?"
User: "I don't know, maybe 50k?"
Agent: "Okay, so around 50k - that's totally fine. We're just getting a ballpark figure here."  ✅ Natural
```

### ✅ Fallback Strategy
Global prompt provides guidelines for:
- Handling interruptions
- Responding to objections
- Managing confusion
- Staying on track

## Example Global Prompts

### For Jake (Income Stacking Qualifier)

```
# WHO YOU ARE
You are Jake, a military veteran with a software engineering degree who now helps people explore passive income opportunities. You're conversational, empathetic, and genuine - never pushy or salesy.

# YOUR PERSONALITY
- Warm and approachable with a slight hesitant style ("um", "uh")
- Direct when needed but always respectful
- You listen more than you talk
- You validate concerns before addressing them

# YOUR COMMUNICATION STYLE
- Use natural filler words occasionally ("uh", "um", "you know")
- Keep responses concise (1-3 sentences usually)
- Ask follow-up questions to show you're listening
- Acknowledge before redirecting ("I hear you, and...")

# HANDLING OBJECTIONS
When someone pushes back:
1. Acknowledge their concern genuinely
2. Ask a question to understand deeper ("What's your biggest concern about that?")
3. Share relevant experience if appropriate
4. Guide back to the conversation goal

# RECOVERY STRATEGY
If user response doesn't match what you need:
- Never just repeat the question robotically
- Acknowledge what they said first
- Rephrase or provide context
- Make it feel like natural conversation flow

# STRICT RULES
- NEVER break character
- NO sales pressure tactics
- NO rushing through questions
- ALWAYS respect "not interested" responses
- STAY on task but make it feel natural
```

### For Customer Service Agent

```
# WHO YOU ARE
You are a helpful customer service representative for [Company Name]. Your goal is to solve customer issues efficiently while making them feel heard and valued.

# YOUR PERSONALITY
- Patient and empathetic
- Solution-oriented
- Professional but friendly
- Calm under pressure

# YOUR COMMUNICATION STYLE
- Listen actively and summarize to show understanding
- Provide clear, step-by-step guidance
- Set proper expectations
- Follow up to ensure resolution

# HANDLING FRUSTRATION
When customers are upset:
1. Validate their frustration ("I completely understand why this is frustrating")
2. Apologize when appropriate ("I'm sorry for the inconvenience")
3. Focus on what you CAN do, not what you can't
4. Provide specific next steps and timelines

# RECOVERY STRATEGY
If you don't understand or misheard:
- Politely ask for clarification
- Repeat back what you think you heard
- Never fake understanding
```

## Implementation

### Adding Global Prompt to Existing Agent

1. **Via UI** (if available in AgentForm):
   - Go to agent settings
   - Find "Global Prompt" or "System Prompt" field
   - Add your universal instructions
   - Save

2. **Via Database**:
```python
await db.agents.update_one(
    {"id": "your-agent-id"},
    {"$set": {"system_prompt": "Your global prompt here..."}}
)
```

### Best Practices

1. **Keep it focused**: 200-500 words is usually enough
2. **Be specific about persona**: Give concrete personality traits
3. **Include recovery strategies**: Tell the agent HOW to handle confusion
4. **Set boundaries**: Define what the agent should/shouldn't do
5. **Use examples**: Show the agent what good looks like

## Technical Details

### Where It's Applied

- **File**: `/app/backend/calling_service.py`
- **Function**: `_process_node_content()`
- **Lines**: ~2573-2589 (prompt mode) and ~1078-1162 (script recovery)

### Caching

The global prompt is marked for caching with Anthropic's prompt caching:
```python
{"role": "system", "content": cached_system_prompt, "cache_control": {"type": "ephemeral"}}
```

This means:
- ✅ Global prompt is cached across multiple turns
- ✅ Reduces API costs
- ✅ Improves response latency

### Priority Order

When AI generates a response:
1. **Global Prompt** (foundation)
2. **Session Variables** (context)
3. **Node Goal/Content** (task)
4. **Conversation History** (last 5 messages)

## Testing Global Prompt

```python
# Test script to verify global prompt is being used
cd /app && python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def test():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_database
    
    agent = await db.agents.find_one({"id": "your-agent-id"})
    global_prompt = agent.get("system_prompt", "")
    
    if global_prompt:
        print(f"✅ Global prompt found ({len(global_prompt)} chars)")
        print(f"\nPreview:\n{global_prompt[:300]}...")
    else:
        print("❌ No global prompt set")
    
    client.close()

asyncio.run(test())
EOF
```

## Migration Notes

- **Backwards Compatible**: Agents without global prompts will use default conversational AI behavior
- **No Breaking Changes**: Existing flows continue to work
- **Opt-In**: Global prompt is optional

## Comparison with Retell AI

| Feature | Retell AI | Your System |
|---------|-----------|-------------|
| Global instructions | ✅ "General Prompt" | ✅ `system_prompt` |
| Per-node overrides | ✅ Yes | ✅ Via goals |
| Recovery strategies | ✅ Built-in | ✅ Customizable in global prompt |
| Caching | ✅ Yes | ✅ Anthropic caching |

## Summary

The Global Prompt feature gives you fine-grained control over your agent's personality and behavior across all nodes, while allowing node-specific tasks to layer on top. It's especially powerful for:

1. **Maintaining consistent character** throughout the call
2. **Intelligent recovery** from unexpected user responses
3. **Providing fallback strategies** for edge cases
4. **Setting behavioral boundaries** and guidelines

Use it to create agents that feel natural, stay in character, and handle real-world conversation complexity gracefully.
