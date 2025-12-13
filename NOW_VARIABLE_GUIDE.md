# {{now}} Variable - Current Date/Time Reference

## Overview

The `{{now}}` variable provides the current date and time in **Eastern Time (EST/EDT)** to help AI agents understand the actual current date, regardless of the LLM's training data cutoff.

## Format

```
Monday, November 3, 2025 at 9:19 PM EST
```

- Full day name (Monday, Tuesday, etc.)
- Full month name (January, February, etc.)
- Day of month (1-31)
- Year (4 digits)
- Time in 12-hour format with AM/PM
- Timezone abbreviation (EST or EDT depending on daylight saving time)

## Automatic Availability

The `{{now}}` variable is **automatically available** in every call session:

1. ✅ **Automatically created** when a call session starts
2. ✅ **Automatically updated** on every user message (stays current during long calls)
3. ✅ **Available in AI context** - The AI can reference it to know the current date/time
4. ✅ **Available for variable replacement** - Can be used in scripts, prompts, and webhook bodies

## Usage Examples

### 1. In Conversation Prompts

The AI automatically has access to `{{now}}` in its context:

```
User: "What's today's date?"
AI: "Today is Monday, November 3, 2025 at 9:19 PM EST."
```

### 2. In Scripts (Variable Replacement)

```
Hello! Today is {{now}}. How can I help you?
```

Becomes:
```
Hello! Today is Monday, November 3, 2025 at 9:19 PM EST. How can I help you?
```

### 3. In Node Instructions

```
Ask the user when they want to schedule their appointment. 
Keep in mind that today is {{now}}.
```

### 4. In Webhook Bodies

```json
{
  "customer_name": "{{customer_name}}",
  "appointment_time": "{{scheduleTime}}",
  "request_time": "{{now}}"
}
```

### 5. For Date Logic

```
You need to schedule appointments. Today is {{now}}.
When the user says "tomorrow", calculate the actual date based on today.
When they say "next week", add 7 days to today's date.
```

## Benefits

### ✅ No Training Data Confusion
Without `{{now}}`, an LLM might think it's still 2023 or 2024 based on its training cutoff:
```
User: "What's tomorrow's date?"
AI (without {{now}}): "Tomorrow is October 14, 2023"  ❌ WRONG
AI (with {{now}}):    "Tomorrow is November 4, 2025"  ✅ CORRECT
```

### ✅ Accurate Relative Date Handling
```
User: "I want to schedule for next Tuesday"
AI: "Based on today being Monday, November 3, 2025, next Tuesday would be November 11, 2025."
```

### ✅ Context-Aware Responses
```
User: "Is your office open now?"
AI: "It's currently 9:19 PM EST on Monday. Our office hours are 9 AM - 5 PM weekdays, so we're closed right now."
```

## Technical Details

### Implementation
- **Location**: `/app/backend/calling_service.py`
- **Class**: `CallSession.__init__()` (line 88-103)
- **Updates**: `CallSession.process_user_input()` (line 189-203)

### Timezone
- **Fixed timezone**: America/New_York (Eastern Time)
- **Daylight Saving**: Automatically handles EST (winter) and EDT (summer)
- **Library**: Python `pytz` library

### Session Scope
- Each call session gets its own `{{now}}` variable
- Updates every time the user sends a message
- Stays accurate even for multi-hour calls

## Testing

Run the test script to verify functionality:

```bash
cd /app
python test_now_variable.py
```

Or test in a conversation:
```bash
python test_now_comprehensive.py
```

## Notes

- The variable updates on **every user message**, ensuring it's always current
- Format is designed to be **human-readable** for both users and the AI
- Timezone is **always EST/EDT** (Eastern Time) as requested
- The variable is in `session_variables`, so it's included in AI context automatically
