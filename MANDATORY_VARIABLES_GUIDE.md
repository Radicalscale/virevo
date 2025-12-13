# Mandatory Variables & Real-Time Extraction Guide

## Overview
This feature ensures your agents reliably collect all necessary information before executing webhooks. It includes mandatory variables, automatic re-prompting, real-time extraction in conversation nodes, and extraction hints to improve accuracy.

---

## 🎯 Key Features

### 1. **Mandatory Variables**
Mark variables as required - webhooks won't execute until these are provided.

### 2. **Automatic Re-Prompting**
If required variables are missing, the agent automatically asks for them using your custom prompt.

### 3. **Real-Time Extraction in Conversation Nodes**
Extract variables as the conversation happens, not just in function nodes.

### 4. **Extraction Hints**
Give the AI guidance on what patterns to look for, improving extraction accuracy.

---

## 📝 How to Configure Variables

### In Function/Webhook Nodes:

Each variable now has these fields:

1. **Variable Name** (required)
   - Example: `appointment_date`
   
2. **Description** (required)
   - What to extract
   - Example: "The date mentioned by user for appointment"
   
3. **Extraction Hint** (optional)
   - Helps AI know what patterns to look for
   - Example: "Look for phrases like tomorrow, next week, specific dates"
   
4. **Required** (checkbox)
   - Check this to make the variable mandatory
   - Webhook won't execute until this is provided
   
5. **Re-prompt Text** (appears when Required is checked)
   - What the agent should say if variable is missing
   - Example: "I need to know the appointment date. When would you like to schedule?"

---

## 🔄 How It Works

### Scenario 1: All Required Variables Provided

```
User: "I want to book an appointment for tomorrow at 3 PM"

Agent: [Extracts appointment_date and appointment_time]
        [All required variables present]
        [Executes webhook immediately]
        "Perfect! I've scheduled your appointment for tomorrow at 3 PM."
```

### Scenario 2: Missing Required Variable

```
User: "I want to book an appointment"

Agent: [Tries to extract appointment_date]
        [Variable missing - is required]
        [Webhook NOT executed]
        "I need to know the appointment date. When would you like to schedule?"

User: "Tomorrow at 3 PM"

Agent: [Extracts appointment_date: "Tomorrow at 3 PM"]
        [All required variables now present]
        [Executes webhook]
        "Great! Your appointment is booked for tomorrow at 3 PM."
```

---

## 🎨 Real-Time Extraction in Conversation Nodes

### Why Use This?

Extract variables **as the conversation happens** instead of waiting until a function node. This:
- Makes extraction more accurate (captures info from specific conversation turns)
- Reduces LLM context burden (doesn't need to search entire conversation)
- Enables early validation (know what's missing before webhook)

### How to Set Up:

1. Open any **Conversation node**
2. Find the **"📊 Extract Variables (Real-Time)"** section
3. Add variables you want to extract during this conversation
4. Conversation nodes **don't support** Required/Re-prompt (those are only for function nodes)

### Example Use Case:

**Conversation Node 1: "Ask about appointment details"**
- Extract Variables:
  - `appointment_date` - "The date user wants to book"
  - `appointment_time` - "The time user wants to book"

**Conversation Node 2: "Ask about contact info"**
- Extract Variables:
  - `customer_name` - "User's full name"
  - `customer_phone` - "User's phone number"

**Function Node: "Schedule Appointment"**
- Extract Variables (all marked Required):
  - `appointment_date` ✅ Required
  - `appointment_time` ✅ Required
  - `customer_name` ✅ Required
  - `customer_phone` ✅ Required

Since these were already extracted in earlier conversation nodes, the function node will have them all available and execute immediately!

---

## 💡 Extraction Hints

Extraction hints guide the AI on **what patterns to look for**, improving accuracy.

### Examples:

#### Date Extraction
```
Variable: appointment_date
Description: The date mentioned by user for appointment
Extraction Hint: Look for phrases like tomorrow, next week, specific dates (MM/DD/YYYY), day names (Monday, Tuesday)
```

#### Time Extraction
```
Variable: appointment_time
Description: The time user wants to book
Extraction Hint: Look for time formats like 3 PM, 15:00, three o'clock, morning/afternoon/evening
```

#### Name Extraction
```
Variable: customer_name
Description: User's full name
Extraction Hint: Look for formal names (First Last), or when user says "my name is", "I'm", "this is"
```

#### Email Extraction
```
Variable: customer_email
Description: User's email address
Extraction Hint: Look for email format (user@domain.com), or when user says "email is", "send to"
```

#### Product Extraction
```
Variable: product_name
Description: The product they want to order
Extraction Hint: Look for specific product names, SKUs, or when user says "I want", "I'd like to order"
```

---

## 🚀 Complete Example: Appointment Booking Flow

### Conversation Node: "Greeting"
```
Mode: Prompt
Content: Greet the user and ask what service they need

Extract Variables: (none - just greeting)
```

### Conversation Node: "Collect Appointment Info"
```
Mode: Prompt
Content: Ask when they'd like to schedule their appointment

Extract Variables:
  - appointment_date
    Description: The date mentioned by user
    Hint: Look for tomorrow, next week, specific dates, day names
    
  - appointment_time
    Description: The time they want to book
    Hint: Look for time formats like 3 PM, 15:00, morning/afternoon
```

### Conversation Node: "Collect Contact Info"
```
Mode: Prompt
Content: Ask for their name and phone number for confirmation

Extract Variables:
  - customer_name
    Description: User's full name
    Hint: Look for formal names or "my name is"
    
  - customer_phone
    Description: User's phone number
    Hint: Look for phone formats (XXX-XXX-XXXX) or when user says "phone is"
```

### Function Node: "Check Availability"
```
Webhook URL: https://your-api.com/check-availability
Method: POST

Extract Variables:
  - appointment_date ✅ Required
    Re-prompt: "I need the date for your appointment. When would you like to schedule?"
    
  - appointment_time ✅ Required
    Re-prompt: "What time works best for you?"
    
  - customer_name ✅ Required
    Re-prompt: "I need your name to complete the booking. What's your name?"
    
  - customer_phone ✅ Required
    Re-prompt: "Could you provide a phone number for confirmation?"

Wait for Result: ON
```

---

## 🔍 How Variables Are Extracted

### Priority Order:

1. **Check session variables first**
   - If variable already exists (from earlier nodes or call start), use it
   - No LLM call needed

2. **Extract from current message**
   - Use LLM to extract from user's most recent message
   - Uses extraction hints if provided
   - Only extracts variables not already in session

3. **Validate required variables** (Function nodes only)
   - Before webhook execution, check all required variables
   - If any missing, return re-prompt message
   - Stay on same node until all required variables provided

---

## 📊 Backend Logging

Watch for these log messages to see the system working:

### Real-Time Extraction (Conversation Nodes):
```
🔍 Real-time extraction: Processing 2 variables
  ✓ appointment_date: 2025-11-05 (extracted in real-time)
  ✓ appointment_time: 3 PM (extracted in real-time)
✅ Real-time extraction complete: 2 variables
```

### Pre-populated Variables:
```
✓ to_number: +17708336397 (already in session)
✓ customer_email: john@example.com (already in session)
```

### Missing Required Variables:
```
❌ Required variable missing: appointment_date
🚫 Cannot execute webhook: 1 required variables missing
💬 Re-prompting for missing variables: I need to know the appointment date...
🔁 Webhook requires re-prompt - staying on same node
```

### Successful Execution:
```
✅ All 4 variables already available in session
🌐 Calling webhook: POST https://your-api.com/schedule
✅ Webhook response: 200 OK
```

---

## 🎯 Best Practices

### 1. Mark Critical Variables as Required
Only mark variables as **Required** if the webhook absolutely needs them.
- ✅ appointment_date (critical for booking)
- ✅ customer_email (needed for confirmation)
- ❌ customer_notes (nice to have, but optional)

### 2. Write Clear Re-Prompts
Make re-prompts conversational and specific:
- ✅ "I need to know the appointment date. When would you like to schedule?"
- ❌ "Missing appointment_date"

### 3. Use Extraction Hints
Provide specific patterns to improve accuracy:
- ✅ "Look for time formats like 3 PM, 15:00, three o'clock"
- ❌ "Extract time"

### 4. Extract Early in Conversation Nodes
Don't wait until function nodes to extract - capture information as soon as it's mentioned:
- Extract `appointment_date` when asking about scheduling
- Extract `customer_name` when asking for contact info
- Extract `product_name` when discussing products

### 5. Layer Your Extraction
Use multiple conversation nodes to extract different categories:
- Node 1: Service/Product details
- Node 2: Date/Time preferences
- Node 3: Contact information
- Function Node: Validate all and execute

---

## 🐛 Troubleshooting

### Variable Not Extracting
- Check extraction hint is specific enough
- Verify description clearly explains what to extract
- Review conversation logs to see what LLM is receiving

### Re-Prompt Loop
- Make sure user is actually providing the variable
- Check if extraction hint helps AI recognize the format
- Verify variable name matches in all nodes

### Webhook Executing Without All Variables
- Confirm Required checkbox is checked
- Verify webhook uses schema format (JSON with properties)
- Check backend logs for validation messages

---

## 🆕 Migration from Old System

Old agents without these new fields will continue to work:
- Variables without `required` field default to optional
- Variables without `reprompt_text` get auto-generated prompts
- Variables without `extraction_hint` still work (just less accurate)
- Conversation nodes without extract_variables behave as before

No breaking changes - all existing flows remain functional!

---

## 📖 API Reference

### Variable Configuration Object

```typescript
{
  name: string,                  // Variable name (e.g., "appointment_date")
  description: string,            // What to extract
  extraction_hint?: string,       // Optional: Pattern guidance for AI
  required?: boolean,             // Function nodes only: Is this mandatory?
  reprompt_text?: string          // Function nodes only: What to ask if missing
}
```

### Webhook Response (with missing variables)

```typescript
{
  success: false,
  message: string,                // Re-prompt text to speak to user
  missing_variables: string[],    // List of variable names missing
  requires_reprompt: true         // Flag to stay on same node
}
```

---

**This feature makes your agents significantly more reliable and user-friendly! 🎉**
