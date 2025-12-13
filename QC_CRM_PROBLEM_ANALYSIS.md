# QC & CRM Problem Analysis Document
## Using Cracking Creativity Problem-Solving Framework

---

## 1. PROBLEM RESTATEMENT (Multiple Perspectives)

### Original Statement
"QC automation is not triggering for campaigns when the UI checkbox is enabled, and new users are not being added to the CRM."

### Restatement 1 (User Perspective)
When I enable auto-QC on an agent and make a call, no QC analysis appears in the campaign results.

### Restatement 2 (System Perspective)
The post-call automation pipeline (QC + CRM) fails to execute after `call.hangup` webhook.

### Restatement 3 (Data Flow Perspective)
Data from completed calls is not flowing through to the QC analysis system and CRM lead creation.

### Restatement 4 (Root Cause Focus)
The trigger mechanism connecting call completion to QC/CRM automation is broken at some point in the chain.

### Restatement 5 (Symptom-Based)
- Symptom A: QC results don't appear for campaign calls
- Symptom B: New contacts from calls don't create CRM leads
- Symptom C: Campaign call status remains "pending" instead of "analyzed"

---

## 2. PROBLEM DECOMPOSITION (Fishbone Diagram)

```
                                    QC/CRM NOT WORKING
                                           │
        ┌──────────────────────────────────┼──────────────────────────────────┐
        │                                  │                                  │
   [TRIGGER]                         [DATA FLOW]                      [CONFIGURATION]
        │                                  │                                  │
   ├─ call.hangup not firing        ├─ transcript empty              ├─ auto_qc disabled
   ├─ finalize_call_log fails       ├─ call_id mismatch              ├─ campaign_id missing
   ├─ trigger function not called   ├─ user_id not passed            ├─ agent not linked
   └─ async task fails silently     ├─ agent_id missing              └─ QC agents not set
                                    └─ MongoDB query fails
                                           │
                                    [DATABASE]
                                           │
                                    ├─ Duplicate records blocking inserts
                                    ├─ call_logs collection issues
                                    ├─ campaign_calls not populated
                                    └─ Index/query mismatches
```

---

## 3. ASKING "WHY" 5 TIMES (Root Cause Analysis)

### Chain 1: QC Not Triggering

**Why 1:** QC analysis doesn't appear in campaign results
↓
**Why 2:** `run_full_qc_analysis` function is not being called
↓
**Why 3:** `trigger_campaign_qc_for_call` is not executing
↓
**Why 4:** Either: (a) `call.hangup` webhook doesn't trigger it, OR (b) The function exits early due to missing data
↓
**Why 5:** Need to check: 
- Is `call.hangup` webhook being received?
- Is `finalize_call_log` being called?
- Is `trigger_campaign_qc_for_call` being called?
- What does the agent's `auto_qc_settings` contain?

### Chain 2: CRM Leads Not Created

**Why 1:** New contacts from calls are not in CRM leads
↓
**Why 2:** `create_lead_from_call` endpoint is not being called
↓
**Why 3:** The call completion flow doesn't invoke CRM lead creation
↓
**Why 4:** Either: (a) No integration exists, OR (b) Campaign doesn't have `auto_create_leads` enabled
↓
**Why 5:** Need to check:
- Is there code that calls CRM lead creation after call ends?
- Where is the CRM integration point in the call flow?

---

## 4. COMPONENT ANALYSIS

### Component 1: Call Hangup Handler (server.py lines 6510-6570)
```
call.hangup webhook received
    → finalize_call_log(call_control_id, "hangup")
    → trigger_campaign_qc_for_call(call_id, user_id, agent_id) [if auto_qc enabled]
```

**Critical Questions:**
- Is `call_id` passed correctly to `finalize_call_log`? (Line 6519 uses `call_control_id`)
- Does `finalize_call_log` return the actual `call_id` for QC?
- Is the transcript populated before QC runs?

### Component 2: trigger_campaign_qc_for_call (server.py lines 7926-7988)
```
Checks:
    1. Fetch call from call_logs
    2. Fetch agent
    3. Check auto_qc_settings.enabled
    4. Check auto_qc_settings.campaign_id exists
    5. Run run_full_qc_analysis()
```

**Critical Questions:**
- Is the call being found in `call_logs` collection?
- Does the agent have `auto_qc_settings` populated?
- Is `campaign_id` set in `auto_qc_settings`?

### Component 3: CRM Lead Creation
```
Current: crm_router.py has /leads/from-call endpoint
Missing: No automatic invocation after call ends
```

**Critical Finding:**
Looking at the code, there is NO automatic CRM lead creation after calls! The `/leads/from-call` endpoint exists but nothing calls it automatically.

---

## 5. HYPOTHESES TO TEST

### Hypothesis 1: call_id vs call_control_id Mismatch
The `call.hangup` handler uses `call_control_id` but QC functions expect `call_id`. These might be different values.

**Test:** Log both values at hangup and compare.

### Hypothesis 2: Agent auto_qc_settings Not Saved
The UI checkbox might not be correctly saving the `auto_qc_settings` to the agent document.

**Test:** Query the agent document and check if `auto_qc_settings.enabled = true` and `campaign_id` exists.

### Hypothesis 3: Transcript Not Ready When QC Runs
The QC analysis might run before the transcript is fully saved.

**Test:** Check if `finalize_call_log` completes before `trigger_campaign_qc_for_call` runs.

### Hypothesis 4: Duplicate Call Logs Blocking Updates
If there are duplicate records in `call_logs`, the wrong one might be updated.

**Test:** Query call_logs for any duplicate entries by phone number or call_id.

### Hypothesis 5: CRM Lead Creation Not Integrated
There's no code that automatically creates CRM leads after calls.

**Test:** Search for any invocation of `/leads/from-call` or `create_lead_from_call` in the call flow.

---

## 6. INVESTIGATION PLAN (Priority Order)

### Step 1: Verify Webhook Chain
```bash
# Add logging to track the full flow:
1. call.hangup received
2. finalize_call_log called with what parameters
3. trigger_campaign_qc_for_call called with what parameters
4. run_full_qc_analysis called or not
```

### Step 2: Check Agent Configuration
```python
# Query to verify agent has correct auto_qc_settings:
db.agents.findOne({id: "agent_id"}, {auto_qc_settings: 1})
# Expected: {enabled: true, campaign_id: "xxx", run_tech_analysis: true, ...}
```

### Step 3: Check Call Log Data
```python
# Verify call_logs has required data for QC:
db.call_logs.findOne({call_id: "xxx"}, {transcript: 1, user_id: 1, agent_id: 1})
# Expected: transcript populated, user_id and agent_id present
```

### Step 4: Check for Duplicate Records
```python
# Find any duplicates:
db.call_logs.aggregate([
    {$group: {_id: "$to_number", count: {$sum: 1}}},
    {$match: {count: {$gt: 1}}}
])
```

### Step 5: Add CRM Lead Creation Hook
```python
# In finalize_call_log, after QC trigger, add:
asyncio.create_task(auto_create_crm_lead(call_id, user_id, agent_id))
```

---

## 7. KEY CODE LOCATIONS TO INVESTIGATE

| File | Function | Line | Purpose |
|------|----------|------|---------|
| server.py | `call.hangup` handler | 6510-6570 | Entry point after call ends |
| server.py | `finalize_call_log` | 5797-5875 | Updates call_logs, triggers QC |
| server.py | `trigger_campaign_qc_for_call` | 7926-7988 | Decides whether to run QC |
| qc_enhanced_router.py | `run_full_qc_analysis` | 5728+ | Actual QC analysis execution |
| crm_router.py | `create_lead_from_call` | 1050-1123 | CRM lead creation (not auto-invoked!) |

---

## 8. IMMEDIATE ACTIONS

### Action 1: Add Comprehensive Logging
Add debug logs at every step of the post-call flow to trace exactly where it fails.

### Action 2: Verify Agent Configuration
Check if the agent's `auto_qc_settings` is properly saved when the UI checkbox is enabled.

### Action 3: Add CRM Auto-Creation
Add a call to create CRM leads automatically after calls complete.

### Action 4: Fix call_id Resolution
Ensure `finalize_call_log` returns/uses the correct `call_id` for downstream functions.

---

## 9. SUCCESS CRITERIA

1. After enabling auto-QC on an agent and making a call:
   - Logs show `trigger_campaign_qc_for_call` being called
   - QC results appear in campaign dashboard
   - Campaign call status shows "analyzed"

2. After completing a call:
   - New contact is created as a CRM lead (if not exists)
   - Existing lead is updated with call history

---

## 10. NEXT STEPS

1. **First:** Run investigation queries to verify hypotheses
2. **Second:** Add logging to trace the exact failure point
3. **Third:** Apply fixes based on findings
4. **Fourth:** Test end-to-end flow
5. **Fifth:** Verify CRM integration works

---

## 11. FIXES APPLIED (December 2025)

### Root Cause Identified
The issue was that when a call ends (hangup event), the data retrieval from Redis/in-memory was failing because:
1. **Redis is unavailable** in the testing environment (connection error)
2. **In-memory fallback** sometimes had missing or incomplete data
3. Critical fields like `user_id`, `agent_id`, and `to_number` were `None` at hangup time

### Fix: MongoDB Fallback for Missing Data
Added a fallback mechanism in the `call.hangup` handler (server.py lines ~6521-6570) to query MongoDB `call_logs` collection when Redis/memory data is incomplete:

```python
# FALLBACK: If critical data is missing, try to get from call_logs in MongoDB
if not user_id or not agent_id or not to_number:
    logger.info(f"📇 [HANGUP] Missing data from cache, checking MongoDB call_logs...")
    call_log = await db.call_logs.find_one({
        "$or": [
            {"call_id": call_control_id},
            {"id": call_control_id}
        ]
    })
    if call_log:
        if not user_id:
            user_id = call_log.get("user_id")
        if not agent_id:
            agent_id = call_log.get("agent_id")
        if not to_number:
            to_number = call_log.get("to_number")
```

### Debug Endpoint Added
Added `/api/debug/test-post-call-automation/{call_id}` endpoint for manual testing of the post-call automation pipeline.

### Verification Results
- ✅ QC automation working: Tech, Script, and Tonality analyses complete successfully
- ✅ CRM lead creation working: New leads created, existing leads updated with call count
- ✅ Pattern detection working: Automatic pattern detection runs after QC analysis
- ✅ All data persisted to MongoDB correctly

### Test Command
```bash
curl -s -b /tmp/cookies.txt -X POST "http://localhost:8001/api/debug/test-post-call-automation/{call_id}"
```

