# Inbound & Outbound Call Routing System

## Overview
The phone number assignment system now fully supports routing both inbound and outbound calls to designated agents based on phone number assignments.

## How It Works

### 1. Phone Number Management

**UI Location**: Phone Numbers page (sidebar menu)

**Setup Process**:
1. Click the **+** button to add a phone number
2. Enter your Telnyx phone number (e.g., `+15551234567`)
3. Click **Add Number**
4. Select the number from the list
5. Assign agents using the dropdowns:
   - **Inbound call agent**: Handles incoming calls to this number
   - **Outbound call agent**: Used when making calls from this number

**Example Configuration**:
```
Phone Number: +1 (555) 123-4567
├─ Inbound Agent: "Customer Support Bot"
└─ Outbound Agent: "Sales Outreach Bot"
```

---

## 2. Inbound Call Flow (NEW!)

When someone calls your Telnyx number:

```
Caller dials → Telnyx receives call → Webhook to Andromeda → Route to assigned agent
```

**Step-by-Step Process**:

1. **Call Received**: Telnyx receives incoming call
2. **Webhook Sent**: Telnyx sends `call.initiated` event with `direction: "incoming"`
3. **Number Lookup**: System looks up the called number in database
4. **Agent Assignment**: Retrieves `inbound_agent_id` for that number
5. **Call Answered**: System answers call with assigned agent's configuration
6. **Conversation Starts**: Agent begins conversation based on call flow

**Webhook Event**:
```json
{
  "data": {
    "event_type": "call.initiated",
    "payload": {
      "direction": "incoming",
      "from": "+15559876543",  // Caller's number
      "to": "+15551234567",    // Your Telnyx number
      "call_control_id": "v3:..."
    }
  }
}
```

**Backend Logic** (`server.py` - line ~3800):
```python
if event_type == "call.initiated" and direction == "incoming":
    # Look up phone number
    phone_record = await db.phone_numbers.find_one({"number": to_number})
    
    if phone_record and phone_record.get("inbound_agent_id"):
        # Get assigned agent
        agent = await db.agents.find_one({"id": inbound_agent_id})
        
        # Answer call with agent
        await telnyx_service.answer_call(call_control_id, stream_url=...)
```

**What Happens If**:
- ✅ **Agent assigned**: Call is answered and routed to agent
- ❌ **No agent assigned**: Call is rejected with message
- ❌ **Agent not found**: Call is rejected

---

## 3. Outbound Call Flow (Existing)

When your system calls someone:

```
Trigger → Select phone number → Use outbound agent → Make call
```

**Usage**:
- Outbound Call Tester page
- Webhook-triggered calls
- API-initiated calls

**How to Configure**:
The `outbound_agent_id` is used when making calls FROM a specific number. This determines which agent's voice, personality, and flow are used for outbound calls.

---

## 4. Telnyx Configuration Required

### Webhook URL Setup:

In your Telnyx dashboard, configure your phone number(s) to send webhooks to:

```
https://missed-variable.preview.emergentagent.com/api/telnyx/webhook
```

**Steps**:
1. Log in to Telnyx Portal
2. Go to **Call Control Applications**
3. Create or edit your application
4. Set **Webhook URL**: `https://missed-variable.preview.emergentagent.com/api/telnyx/webhook`
5. Enable these events:
   - `call.initiated` ✅
   - `call.answered` ✅
   - `call.hangup` ✅
   - `call.playback.ended` ✅
   - `call.recording.saved` ✅
   - `call.machine.detection.ended` ✅ (if using AMD)
6. Save and associate with your phone numbers

---

## 5. Database Schema

**Phone Numbers Collection**:
```json
{
  "id": "uuid",
  "number": "+15551234567",
  "inbound_agent_id": "agent-uuid-1",
  "inbound_agent_name": "Customer Support Bot",
  "outbound_agent_id": "agent-uuid-2",
  "outbound_agent_name": "Sales Outreach Bot",
  "status": "active",
  "calls_received": 0,
  "created_at": "2025-11-06T10:00:00Z"
}
```

**Key Fields**:
- `inbound_agent_id`: Agent for incoming calls
- `outbound_agent_id`: Agent for outgoing calls
- `inbound_agent_name`: Cached agent name (for UI display)
- `outbound_agent_name`: Cached agent name (for UI display)

---

## 6. API Endpoints

### Create Phone Number
```bash
POST /api/phone-numbers
{
  "number": "+15551234567",
  "inbound_agent_id": "optional-uuid",
  "outbound_agent_id": "optional-uuid"
}
```

### List Phone Numbers
```bash
GET /api/phone-numbers
```

### Update Agent Assignments
```bash
PUT /api/phone-numbers/{number_id}
{
  "inbound_agent_id": "new-agent-uuid",
  "outbound_agent_id": "another-agent-uuid"
}
```

### Delete Phone Number
```bash
DELETE /api/phone-numbers/{number_id}
```

---

## 7. Testing

### Test Inbound Routing:

1. **Setup**:
   - Add your Telnyx number in Phone Numbers page
   - Assign an inbound agent (e.g., "Jake - Income Stacking Qualifier")
   - Ensure Telnyx webhook is configured

2. **Test**:
   - Call your Telnyx number from any phone
   - You should hear the assigned agent's greeting
   - Conversation should follow the agent's call flow

3. **Verify**:
   - Check "Calls" page to see the inbound call logged
   - Direction should show "Inbound"
   - Agent name should match assigned inbound agent

### Test Outbound Routing:

1. **Setup**:
   - Assign an outbound agent to a phone number
   - Go to "Test Call" page

2. **Test**:
   - Enter a phone number to call
   - Select the agent (should use outbound_agent_id)
   - Make the call

3. **Verify**:
   - Call should use the outbound agent's voice and flow
   - "Calls" page shows outbound call with correct agent

---

## 8. Troubleshooting

### Issue: Incoming calls not being answered

**Check**:
1. ✅ Telnyx webhook URL is configured correctly
2. ✅ Phone number is added to system
3. ✅ Inbound agent is assigned
4. ✅ Check backend logs: `tail -f /var/log/supervisor/backend.out.log`

**Expected Logs**:
```
📨 Telnyx webhook received: {...}
🎯 Event type: call.initiated, Call ID: v3:...
📞 Call initiated - Direction: incoming, From: +1555..., To: +1555...
📥 Incoming call to +15551234567 from +15559876543
✅ Found assigned inbound agent: Customer Support Bot (ID: ...)
📞 Answering call: v3:...
✅ Inbound call answered: v3:...
```

### Issue: Call is rejected

**Reasons**:
- ❌ No inbound agent assigned to the called number
- ❌ Assigned agent doesn't exist in database

**Fix**:
1. Go to Phone Numbers page
2. Select the number
3. Assign an inbound agent
4. Save and try again

### Issue: Wrong agent answers

**Check**:
- Verify the correct inbound agent is assigned
- Check call logs to see which agent was used
- Ensure agent hasn't been deleted

---

## 9. Call Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     INCOMING CALL                           │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Telnyx Network│
                    └────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │ Webhook: /api/telnyx/webhook           │
        │ Event: call.initiated (direction=in)   │
        └────────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │ Lookup phone number in database        │
        │ SELECT * FROM phone_numbers            │
        │ WHERE number = to_number               │
        └────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
    ┌─────────────────────┐   ┌──────────────────┐
    │ Agent Assigned?     │   │ No Agent?        │
    │ Get inbound_agent   │   │ Reject Call      │
    └─────────────────────┘   └──────────────────┘
                │
                ▼
    ┌─────────────────────┐
    │ Answer Call         │
    │ Start Streaming     │
    │ Create Session      │
    └─────────────────────┘
                │
                ▼
    ┌─────────────────────┐
    │ Agent Speaks        │
    │ User Responds       │
    │ Conversation...     │
    └─────────────────────┘
```

---

## 10. Summary

**What You Get**:
- ✅ Full inbound call routing based on phone number
- ✅ Separate agent assignments for inbound vs outbound
- ✅ Automatic call rejection if no agent assigned
- ✅ Call logging with direction tracking
- ✅ Easy management via UI

**Next Steps**:
1. Add your Telnyx numbers to the system
2. Assign inbound and outbound agents
3. Configure Telnyx webhook URL
4. Test with a live call!

---

## Files Modified

**Backend**:
- `/app/backend/server.py` - Added inbound call handler (~100 lines)
- `/app/backend/telnyx_service.py` - Updated `answer_call()`, added `reject_call()`
- `/app/backend/models.py` - Updated PhoneNumber model

**Frontend**:
- `/app/frontend/src/components/PhoneNumbers.jsx` - Complete rewrite with dual agent assignment

---

**Status**: ✅ FULLY IMPLEMENTED AND DEPLOYED
