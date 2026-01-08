# QC Agents Testing Guide

## Overview
This guide walks you through testing the 3 QC agents (Commitment Detector, Conversion Pathfinder, Excellence Replicator) and their integration with the CRM system.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Test (End-to-End)](#quick-test-end-to-end)
3. [Manual Testing Steps](#manual-testing-steps)
4. [Test Scenarios](#test-scenarios)
5. [Verification Checklist](#verification-checklist)
6. [Automated Testing](#automated-testing)
7. [Troubleshooting](#troubleshooting)
8. [Expected Results](#expected-results)

---

## Prerequisites

### 1. Backend is Running
```bash
sudo supervisorctl status backend
# Should show: backend RUNNING
```

### 2. QC Agent Configs Exist
Check that 3 QC agent configs are created for your user:
```bash
# Via API (replace with your backend URL)
curl -X GET "https://voice-overlap-debug.preview.emergentagent.com/api/crm/qc-config" \
  --cookie "access_token=YOUR_TOKEN"

# Expected: 3 configs (commitment_detector, conversion_pathfinder, excellence_replicator)
```

### 3. Lead Exists (Optional but Recommended)
Create a test lead to track QC scores:
```bash
curl -X POST "https://voice-overlap-debug.preview.emergentagent.com/api/crm/leads" \
  -H "Content-Type: application/json" \
  --cookie "access_token=YOUR_TOKEN" \
  -d '{
    "name": "QC Test Lead",
    "phone": "+1234567890",
    "email": "qctest@example.com",
    "source": "ad_campaign"
  }'

# Save the returned lead ID for later
```

---

## Quick Test (End-to-End)

### Step 1: Make a Test Call

**Option A: Via Test Call UI**
1. Go to `/test-call` in your app
2. Select an agent
3. Make a call and have a conversation
4. Hang up

**Option B: Via API (Outbound Call)**
```bash
curl -X POST "https://voice-overlap-debug.preview.emergentagent.com/api/telnyx/call/outbound" \
  -H "Content-Type: application/json" \
  --cookie "access_token=YOUR_TOKEN" \
  -d '{
    "agent_id": "YOUR_AGENT_ID",
    "phone_number": "+1234567890"
  }'
```

### Step 2: Wait for Call to Complete
The QC analysis triggers automatically when the call ends (on `call.hangup` event).

**Check Backend Logs:**
```bash
tail -f /var/log/supervisor/backend.err.log | grep -i "qc\|commitment\|conversion\|excellence"

# You should see:
# 🚀 Triggered QC analysis for call...
# 🔍 Starting QC analysis for call...
# 🔍 Running Commitment Detector...
# 🗺️  Running Conversion Pathfinder...
# ⭐ Running Excellence Replicator...
# ✅ QC analysis completed for call...
# 📊 Scores: Commitment=75, Conversion=82, Excellence=68
```

### Step 3: Verify Results

**Check Call Analytics Database:**
```bash
# Connect to MongoDB and query
mongo

use your_database
db.call_analytics.find().sort({created_at: -1}).limit(1).pretty()

# Should return latest QC analysis with all 3 agent results
```

**Via API:**
```bash
# Get analytics for a specific call
curl -X GET "https://voice-overlap-debug.preview.emergentagent.com/api/crm/analytics/call/CALL_ID" \
  --cookie "access_token=YOUR_TOKEN"
```

### Step 4: Check CRM Lead Update
If you linked the call to a lead, verify scores are updated:

```bash
# Get lead details
curl -X GET "https://voice-overlap-debug.preview.emergentagent.com/api/crm/leads/LEAD_ID" \
  --cookie "access_token=YOUR_TOKEN"

# Check for:
# - commitment_score
# - conversion_score
# - excellence_score
# - show_up_probability
# - total_calls: 1 (incremented)
```

---

## Manual Testing Steps

### Test 1: Commitment Detector

**Goal:** Verify commitment score detection based on language patterns

**Test Conversation:**
```
Agent: "Would you like to schedule an appointment?"
User: "Yes, absolutely! I'm really excited about this."
User: "I'll definitely be there. Let me mark it on my calendar right now."

Expected Result:
- Commitment Score: 75-85 (High)
- Show-up Probability: 75-85%
- Risk Level: low
- Key Factors: ["Strong commitment language detected", "Reached commitment stage"]
```

**Negative Test:**
```
Agent: "Would you like to schedule?"
User: "Uh, I guess so... maybe if I'm free."
User: "I'll have to think about it. Can you call me back?"

Expected Result:
- Commitment Score: 20-35 (Low)
- Show-up Probability: 25-40%
- Risk Level: high
- Action Items: ["URGENT: Call within 1 hour to re-confirm"]
```

### Test 2: Conversion Pathfinder

**Goal:** Verify funnel stage detection and BANT scoring

**Test Conversation (Complete Funnel):**
```
Agent: "Hi, I'm calling about your recent inquiry." (HOOK)
Agent: "What are you currently looking for?" (QUALIFICATION)
User: "I need help with my business growth."
Agent: "Our solution will help you achieve 2x growth in 90 days." (VALUE)
User: "How much does this cost?"
Agent: "Great question! Let me explain..." (OBJECTION HANDLING)
Agent: "Would you like to schedule a demo?" (CLOSING)
User: "Yes!"
Agent: "Perfect! I'll send you a calendar invite." (CONFIRMATION)

Expected Result:
- Funnel Completion: 95-100%
- BANT Score: 70-80 (highly_qualified)
- Diagnosis: "Conversation followed optimal path"
- Missing Stages: [] (empty)
```

**Negative Test (Incomplete Funnel):**
```
Agent: "Hi, I'm calling about..." (HOOK)
Agent: "Can we schedule a demo?" (CLOSING - jumped too fast)
User: "I'm not sure..."

Expected Result:
- Funnel Completion: 33-50%
- BANT Score: 20-40 (poorly_qualified)
- Diagnosis: "CRITICAL: Value never presented. User doesn't know what they're getting."
- Critical Moments: ["missing_stage: value_presentation"]
```

### Test 3: Excellence Replicator

**Goal:** Verify pattern detection for call quality

**Test Conversation (High Quality):**
```
Agent: "I understand your specific situation. For you, this means..."
Agent: "Excellent! Let me explain exactly how this works for your business."
Agent: "The benefit you'll see is a 50% reduction in costs."
Agent: "We have limited spots available this month."

Expected Result:
- Excellence Score: 75-85
- Pattern Analysis:
  - personalization: score 7-10 (high)
  - enthusiasm: score 6-8
  - clarity: score 7-9
  - urgency: score 6-8
  - value_focus: score 7-9
- Recommendations: ["Excellent call! Analyze for replicable patterns"]
```

**Negative Test (Low Quality):**
```
Agent: "We have a solution."
Agent: "It's good."
Agent: "Do you want it?"

Expected Result:
- Excellence Score: 20-35
- Pattern Analysis: All scores 0-3 (low)
- Recommendations: 
  - "Increase personalization"
  - "Show more enthusiasm"
  - "Improve clarity"
  - "Create urgency"
  - "Emphasize value"
```

---

## Test Scenarios

### Scenario 1: High-Quality Appointment Set

**Setup:**
- Lead: "Sarah Johnson" (+15551234567)
- Source: "Facebook Ad Campaign"

**Call Script:**
```
Agent: Hi Sarah! I'm calling about your inquiry from our Facebook ad.
User: Oh yes, I was interested in learning more.
Agent: Great! Tell me, what specifically are you looking to achieve?
User: I need to grow my business revenue.
Agent: Perfect. Our program has helped businesses like yours achieve 2x growth in 90 days. 
       For your specific situation, this means you could see an additional $50k in revenue.
User: That sounds interesting. How much does it cost?
Agent: I understand budget is important. Our program is $5k, and we offer payment plans.
       Given the potential $50k increase, it pays for itself quickly.
User: Okay, that makes sense.
Agent: Would you like to schedule a free strategy session to discuss your specific goals?
User: Yes, absolutely! When can we do this?
Agent: Excellent! How's Tuesday at 2pm?
User: Perfect! I'll mark it down.
Agent: Great! I'm sending you a calendar invite now. You'll receive a reminder 24 hours before.
       I'm really looking forward to helping you achieve your goals!
User: Thank you! See you Tuesday!
```

**Expected QC Results:**
```json
{
  "commitment_score": 85,
  "conversion_score": 92,
  "excellence_score": 88,
  "show_up_probability": 87,
  "risk_level": "low",
  "overall_quality_score": 88,
  "funnel_completion": 100,
  "bant_qualification": "highly_qualified"
}
```

**CRM Lead Update:**
- Status: appointment_set → appointment_confirmed
- Total Calls: 1
- All QC scores updated

### Scenario 2: Poor Quality Call (No Show Risk)

**Call Script:**
```
Agent: Hey, want to schedule something?
User: I guess... maybe.
Agent: How about Tuesday?
User: I don't know if I'll be free.
Agent: Okay, I'll just put you down for Tuesday.
User: Uh, okay.
```

**Expected QC Results:**
```json
{
  "commitment_score": 25,
  "conversion_score": 35,
  "excellence_score": 20,
  "show_up_probability": 28,
  "risk_level": "high",
  "overall_quality_score": 27,
  "funnel_completion": 40,
  "recommendations": [
    "URGENT: Call within 1 hour to re-confirm",
    "CRITICAL: Value never presented",
    "Improve personalization",
    "Create urgency"
  ]
}
```

### Scenario 3: Mid-Quality with Objections

**Call Script:**
```
Agent: Hi, I'd like to discuss our services.
User: I'm really busy right now.
Agent: I understand. This will only take 2 minutes of your time.
User: Okay, go ahead.
Agent: We help businesses like yours grow revenue. Are you interested in growth?
User: Yes, but I've tried programs before and they didn't work.
Agent: I hear you. What didn't work about those programs?
User: They were too generic.
Agent: That's exactly why ours is different. We customize everything to your specific needs.
User: Hmm, okay. How much?
Agent: $3k, but given your revenue potential, you'll see ROI in 60 days.
User: Alright, let me schedule a call to discuss further.
```

**Expected QC Results:**
```json
{
  "commitment_score": 58,
  "conversion_score": 68,
  "excellence_score": 62,
  "show_up_probability": 63,
  "risk_level": "medium",
  "objections_raised": ["timing", "skepticism", "price"],
  "objections_resolved": ["timing", "skepticism"],
  "recommendations": [
    "Send confirmation email within 15 minutes",
    "Include calendar invite"
  ]
}
```

---

## Verification Checklist

### ✅ Backend Integration
- [ ] QC orchestrator loads on backend startup (check logs)
- [ ] `process_qc_analysis()` function exists in server.py
- [ ] Call hangup triggers QC analysis (check logs)
- [ ] Analysis runs asynchronously (doesn't block call processing)

### ✅ Database Storage
- [ ] `call_analytics` collection exists
- [ ] QC analysis documents are created after calls
- [ ] Documents contain all 3 agent results
- [ ] `aggregated_scores` section is populated
- [ ] Recommendations are aggregated

### ✅ CRM Integration
- [ ] Lead scores are updated after call
- [ ] `total_calls` is incremented
- [ ] `commitment_score`, `conversion_score`, `excellence_score` populated
- [ ] `show_up_probability` is set
- [ ] `last_contact` timestamp updated

### ✅ QC Agent Configuration
- [ ] 3 QC agent configs exist per user
- [ ] Each agent has `llm_provider` and `llm_model` set
- [ ] Agents can be enabled/disabled
- [ ] Config API endpoints work

### ✅ Score Accuracy
- [ ] High-commitment language → high commitment score (70+)
- [ ] Weak language → low commitment score (20-40)
- [ ] Complete funnel → high conversion score (80+)
- [ ] Skipped stages → low conversion score (30-50)
- [ ] Quality patterns → appropriate excellence score

---

## Automated Testing

### Backend API Testing Script

Create `test_qc_agents.py`:

```python
#!/usr/bin/env python3
import asyncio
import httpx
import json

BACKEND_URL = "https://voice-overlap-debug.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

async def test_qc_system():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login to get token
        login_response = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": "test@test.com", "password": "test123"}
        )
        
        if login_response.status_code != 200:
            print("❌ Login failed")
            return
        
        cookies = {"access_token": login_response.cookies.get("access_token")}
        print("✅ Logged in")
        
        # 2. Check QC configs
        config_response = await client.get(
            f"{API_BASE}/crm/qc-config",
            cookies=cookies
        )
        
        configs = config_response.json()
        print(f"✅ Found {len(configs)} QC agent configs")
        
        for config in configs:
            print(f"  - {config['agent_type']}: {config['llm_model']} (enabled: {config['enabled']})")
        
        # 3. Create test lead
        lead_response = await client.post(
            f"{API_BASE}/crm/leads",
            cookies=cookies,
            json={
                "name": "QC Test Lead",
                "phone": "+15551234567",
                "email": "qctest@example.com",
                "source": "test"
            }
        )
        
        if lead_response.status_code == 200:
            lead = lead_response.json()
            lead_id = lead['id']
            print(f"✅ Created test lead: {lead_id}")
        else:
            print(f"⚠️ Lead creation failed: {lead_response.text}")
            return
        
        # 4. Simulate call (you'd need to actually make a call here)
        # For now, just check if we can query analytics
        
        # 5. Wait a bit
        await asyncio.sleep(2)
        
        # 6. Check lead was updated
        lead_check = await client.get(
            f"{API_BASE}/crm/leads/{lead_id}",
            cookies=cookies
        )
        
        updated_lead = lead_check.json()
        print(f"\\n📊 Lead QC Scores:")
        print(f"  Commitment: {updated_lead.get('commitment_score', 'N/A')}")
        print(f"  Conversion: {updated_lead.get('conversion_score', 'N/A')}")
        print(f"  Excellence: {updated_lead.get('excellence_score', 'N/A')}")
        print(f"  Show-up Probability: {updated_lead.get('show_up_probability', 'N/A')}%")
        print(f"  Total Calls: {updated_lead.get('total_calls', 0)}")

if __name__ == "__main__":
    asyncio.run(test_qc_system())
```

Run it:
```bash
cd /app
python test_qc_agents.py
```

---

## Troubleshooting

### Issue 1: QC Analysis Not Running

**Symptoms:**
- No logs showing QC analysis
- Lead scores not updating

**Debug Steps:**
```bash
# 1. Check if orchestrator loaded
grep "QC agents orchestrator loaded" /var/log/supervisor/backend.err.log

# 2. Check if call.hangup events are received
tail -f /var/log/supervisor/backend.err.log | grep "call.hangup"

# 3. Check if QC trigger is firing
tail -f /var/log/supervisor/backend.err.log | grep "Triggered QC analysis"

# 4. Check for errors in QC processing
tail -f /var/log/supervisor/backend.err.log | grep -i "error.*qc\|qc.*error"
```

**Common Fixes:**
- Restart backend: `sudo supervisorctl restart backend`
- Verify QC configs exist: Check API endpoint
- Check user_id is available in call_data
- Verify transcript exists in call_log

### Issue 2: Scores Are Always 50 (Neutral)

**Symptoms:**
- All scores are exactly 50
- No meaningful analysis

**Debug Steps:**
```bash
# Check if transcript exists
mongo
db.call_logs.find({}, {call_id: 1, transcript: 1}).limit(1)

# Check call_analytics for actual agent results
db.call_analytics.find().sort({created_at: -1}).limit(1).pretty()
```

**Common Fixes:**
- Verify transcript is populated (not empty)
- Check transcript format (should have "User:" and "Agent:" prefixes)
- Ensure call duration is sufficient (>30 seconds)

### Issue 3: API Key Errors

**Symptoms:**
- Logs show "No API key available"
- Analysis fails silently

**Debug Steps:**
```bash
# Check if Emergent Universal Key is accessible
grep "API key" /var/log/supervisor/backend.err.log

# Try getting key manually
python3 -c "from emergent_integrations_manager import get_emergent_llm_key; print(get_emergent_llm_key())"
```

**Common Fixes:**
- Ensure `emergentintegrations` is installed
- Verify Emergent Universal Key has balance
- Set user's OpenAI API key as fallback

### Issue 4: Lead Not Updating

**Symptoms:**
- QC analysis runs successfully
- But lead scores remain NULL

**Debug Steps:**
```bash
# Check if lead_id is in call_data
mongo
db.call_logs.find({}, {call_id: 1, metadata: 1}).limit(1)

# Check if update query ran
grep "Updated lead.*with QC scores" /var/log/supervisor/backend.err.log
```

**Common Fixes:**
- Ensure lead_id is passed when making calls
- Verify lead exists in database
- Check lead belongs to same user_id

---

## Expected Results

### Successful QC Analysis Logs

```
🚀 Triggered QC analysis for call c_abc123
🔍 Starting QC analysis for call c_abc123
🔍 Running Commitment Detector on call c_abc123
🗺️  Running Conversion Pathfinder on call c_abc123
⭐ Running Excellence Replicator on call c_abc123
✅ QC analysis completed for call c_abc123
📊 Scores: Commitment=75, Conversion=82, Excellence=68
✅ Updated lead lead_xyz789 with QC scores
```

### Sample API Response

**GET /api/crm/analytics/call/{call_id}**
```json
{
  "id": "qc_c_abc123",
  "call_id": "c_abc123",
  "user_id": "user_123",
  "lead_id": "lead_xyz789",
  "agent_id": "agent_456",
  "commitment_analysis": {
    "commitment_analysis": {
      "linguistic_score": 75,
      "behavioral_progression": {
        "highest_stage_reached": "commitment",
        "progression_score": 80
      },
      "objection_handling": {
        "handling_score": 100
      },
      "motivation": {
        "value_score": 7,
        "urgency_score": 6,
        "overall_score": 75
      }
    },
    "show_up_probability": 78,
    "risk_level": "low",
    "action_items": ["Send standard confirmation"]
  },
  "conversion_analysis": {
    "funnel_analysis": {
      "funnel_completion": 92,
      "diagnosis": "Conversation followed optimal path"
    },
    "framework_scores": {
      "bant": {
        "overall_score": 80,
        "qualification_level": "highly_qualified"
      }
    }
  },
  "excellence_analysis": {
    "excellence_score": 68,
    "pattern_analysis": {
      "personalization": {"score": 7},
      "enthusiasm": {"score": 6},
      "clarity": {"score": 8}
    },
    "recommendations": [
      "Continue using this approach"
    ]
  },
  "aggregated_scores": {
    "commitment_score": 75,
    "conversion_score": 82,
    "excellence_score": 68,
    "show_up_probability": 78,
    "risk_level": "low",
    "overall_quality_score": 75
  },
  "recommendations": [
    "Send standard confirmation",
    "Continue using this approach",
    "Analyze for replicable patterns"
  ]
}
```

---

## Performance Testing

### Load Testing Script

Test QC system under load:

```python
import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor

async def simulate_calls(num_calls: int):
    """Simulate multiple calls ending to test QC processing"""
    tasks = []
    
    for i in range(num_calls):
        # Your call simulation here
        pass
    
    results = await asyncio.gather(*tasks)
    print(f"Processed {num_calls} calls")
```

**Expected Performance:**
- Single call analysis: 2-5 seconds
- 10 concurrent calls: <10 seconds total
- No blocking of call processing

---

## Next Steps After Testing

1. **Monitor Production** - Watch QC analysis success rate
2. **Tune Thresholds** - Adjust score weights based on actual results
3. **Build Dashboard** - Visualize QC metrics and trends
4. **Train System** - Use Excellence Replicator to identify top patterns
5. **A/B Testing** - Test prompt variations based on QC recommendations

---

## Support & Resources

- **Backend Logs**: `/var/log/supervisor/backend.err.log`
- **Database**: MongoDB `call_analytics` collection
- **API Docs**: `/api/docs` (FastAPI Swagger UI)
- **QC Architectures**: See `QC_ARCHITECTURE_OVERVIEW.md`

---

**Last Updated**: November 21, 2025
**Version**: 1.0
