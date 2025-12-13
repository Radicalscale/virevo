# Function/Webhook Node - Dialogue & Execution Controls

## Overview
The Function/Webhook node now supports optional dialogue before webhook execution and flexible execution modes. This allows your AI agent to inform users about actions being taken (like "One moment, checking availability...") while processing webhooks in the background.

---

## New Features

### 1. **Speak During Execution** 
Enable the agent to say something before executing the webhook.

**Use Case:** Inform users that the agent is performing an action
- Example: "Let me check that for you..."
- Example: "One moment while I verify availability..."

**Configuration:**
- Toggle: ON/OFF (Default: OFF)
- When enabled, additional dialogue options appear

---

### 2. **Dialogue Type**
Choose how the agent generates the dialogue message.

#### Static Sentence
- Use exact text you provide
- Predictable, consistent messaging
- Example: "Please hold while I check availability"

#### AI Generated (Prompt)
- AI generates response based on your prompt
- More natural, contextual responses
- Example Prompt: "Tell the user you are checking their appointment availability and ask them to wait"

**Configuration:**
- Dropdown: "Static Sentence" or "AI Generated (Prompt)"
- Text area for entering static text or AI prompt

---

### 3. **Wait for Result**
Control whether the agent waits for the webhook to complete before transitioning to the next node.

#### Wait for Result: ON (Default)
- Webhook executes synchronously
- Agent waits for response before transitioning
- Use when: Next node needs webhook response data

#### Wait for Result: OFF
- Webhook executes asynchronously
- Agent transitions immediately
- Use when: Webhook is fire-and-forget (logging, notifications)

**Configuration:**
- Toggle: ON/OFF (Default: ON)

---

### 4. **Block Interruptions**
Prevent users from interrupting while the AI is speaking the dialogue.

**Configuration:**
- Toggle: ON/OFF (Default: ON)
- When enabled, users cannot interrupt during dialogue playback

---

## Visual Representation

### Node Canvas Display
When "Speak During Execution" is enabled and dialogue text is provided:
- A purple box appears within the node
- Shows dialogue type icon:
  - 💬 for Static Sentence
  - 🤖 for AI Prompt
- Displays preview of dialogue text (first 2 lines)

---

## Configuration Panel

The Function Settings panel now includes:

```
⚙️ Function Behavior
├─ Speak During Execution [Toggle]
│  └─ (When enabled)
│     ├─ Dialogue Type [Dropdown: Static/Prompt]
│     └─ Static Text / AI Prompt [Text Area]
├─ Wait for Result [Toggle]
└─ Block Interruptions [Toggle]
```

---

## Example Use Cases

### Use Case 1: Calendar Availability Check
**Scenario:** User requests appointment booking

**Configuration:**
- Speak During Execution: ✅ ON
- Dialogue Type: Static
- Dialogue Text: "Let me check availability for that time..."
- Wait for Result: ✅ ON
- Block Interruptions: ✅ ON

**Flow:**
1. User: "I'd like to book an appointment for 3 PM tomorrow"
2. Agent says: "Let me check availability for that time..."
3. Webhook executes (checks calendar API)
4. Webhook returns: `{available: true}`
5. Transitions to next node (confirmation)

---

### Use Case 2: Background Logging
**Scenario:** Log user interaction without blocking conversation

**Configuration:**
- Speak During Execution: ❌ OFF
- Wait for Result: ❌ OFF

**Flow:**
1. User provides information
2. Webhook executes async (logs to CRM)
3. Agent immediately transitions to next node
4. Webhook completes in background

---

### Use Case 3: Dynamic Response with Context
**Scenario:** Check inventory and provide contextual response

**Configuration:**
- Speak During Execution: ✅ ON
- Dialogue Type: AI Generated (Prompt)
- AI Prompt: "Tell the user you are checking if we have that product in stock. Be friendly and reassuring."
- Wait for Result: ✅ ON

**Flow:**
1. User: "Do you have the red shirt in size M?"
2. AI generates: "Absolutely! Let me check our inventory for the red shirt in medium size. Just a moment..."
3. Webhook checks inventory
4. Transitions based on result

---

## Backend Implementation Details

### Execution Flow

1. **Dialogue Generation** (if speak_during_execution = true)
   - Static: Uses exact `dialogue_text`
   - Prompt: Calls LLM with `dialogue_text` as prompt
   - Dialogue is spoken to user via TTS

2. **Webhook Execution**
   - If `wait_for_result = true`: Await webhook completion
   - If `wait_for_result = false`: Execute async, continue immediately

3. **Transition**
   - After webhook (or immediately if not waiting)
   - Follows transition conditions
   - Moves to next node

### Logging
- `💬 Generating dialogue before webhook execution (type: static/prompt)`
- `📢 Static dialogue: [text]...`
- `🤖 Generating AI dialogue from prompt: [prompt]...`
- `⏳ Waiting for webhook to complete before transitioning...`
- `🚀 Executing webhook async, transitioning immediately...`

---

## Best Practices

### When to Use Dialogue
✅ **Do use dialogue when:**
- Webhook takes >2 seconds
- User needs to know action is being taken
- Provides better user experience

❌ **Don't use dialogue when:**
- Webhook is instant (<500ms)
- Action is transparent to user
- You want minimal interruption

### When to Wait for Result
✅ **Wait for result when:**
- Next node needs webhook data
- Response determines next transition
- Sequential operations required

❌ **Don't wait when:**
- Fire-and-forget operations (logging, analytics)
- Webhook is slow and result not needed
- Want to maintain conversation flow

---

## Migration Guide

### Existing Function Nodes
All existing function/webhook nodes will continue to work with default behavior:
- `speak_during_execution`: false (no dialogue)
- `wait_for_result`: true (sync execution)
- `block_interruptions`: true

No breaking changes - existing flows remain unchanged.

---

## Troubleshooting

### Dialogue Not Playing
- Check `speak_during_execution` is enabled
- Verify `dialogue_text` is not empty
- Check backend logs for dialogue generation

### Webhook Timing Issues
- If transitions happen before webhook: Enable `wait_for_result`
- If webhook blocks too long: Disable `wait_for_result`
- Check backend logs for execution timing

### AI Prompt Not Working
- Verify `dialogue_type` is set to "prompt"
- Check LLM provider configuration
- Review backend logs for AI generation errors

---

## API Reference

### Node Data Structure
```json
{
  "type": "function",
  "data": {
    "webhook_url": "https://api.example.com/check",
    "webhook_method": "POST",
    "webhook_body": "{\"time\": \"{{appointment_time}}\"}",
    "webhook_timeout": 10,
    "response_variable": "webhook_response",
    "extract_variables": [],
    "speak_during_execution": true,
    "dialogue_type": "static",
    "dialogue_text": "Let me check that for you...",
    "wait_for_result": true,
    "block_interruptions": true,
    "transitions": [...]
  }
}
```

---

## Version History

**v1.0** - Initial dialogue and execution control features
- Speak During Execution toggle
- Static/Prompt dialogue types
- Wait for Result toggle
- Block Interruptions toggle
- Visual dialogue preview on canvas
