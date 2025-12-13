# Production Environment Changes Tracking

## Purpose
This document tracks all changes made to connect the preview environment to production MongoDB for testing QC functionality with real data from `kendrickbowman9@gmail.com`.

## Original Configuration (SAVE BEFORE MODIFYING)

### Backend .env (Original)
```
MONGO_URL="mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME="test_database"
BACKEND_URL=https://api.li-ai.org
```

### Frontend .env (Original)
```
REACT_APP_BACKEND_URL=https://tts-guardian.preview.emergentagent.com
```

---

## ⚠️ CRITICAL: Telnyx Webhook URL Changes

### Change 7: BACKEND_URL for Telnyx Webhooks (ACTIVE)
- **File**: `/app/backend/.env`
- **Original Value**: `BACKEND_URL=https://api.li-ai.org`
- **New Value**: `BACKEND_URL=https://tts-guardian.preview.emergentagent.com`
- **Reason**: Telnyx webhooks and WebSocket audio streams were being sent to production server instead of this preview environment. This prevented call transcripts from being captured and auto-QC from running properly.
- **Impact**: 
  - Telnyx call webhooks will now be sent to this preview environment
  - Audio streaming will connect to `wss://qc-dashboard-4.preview.emergentagent.com/api/telnyx/audio-stream`
  - Call transcripts will be captured locally
  - Auto-QC will run on this environment
- **Date**: 2025-12-02
- **TO REVERSE**: Change `BACKEND_URL=https://tts-guardian.preview.emergentagent.com` back to `BACKEND_URL=https://api.li-ai.org` in `/app/backend/.env` and restart backend

### Change 8: Agent "Who Speaks First" Configuration (ACTIVE)
- **Database**: `test_database.agents` collection
- **Agent ID**: `bbeda238-e8d9-4d8c-b93b-1b7694581adb` (JK First Caller-optimizer3)
- **Original Value**: `whoSpeaksFirst: "user"`
- **New Value**: `whoSpeaksFirst: "ai"`
- **Reason**: When set to "user", the agent waits silently for user to speak first. The `aiSpeaksAfterSilence` feature is defined but not implemented in the backend, causing the agent to remain silent indefinitely.
- **Date**: 2025-12-02
- **TO REVERSE**: Run this MongoDB command:
  ```javascript
  db.agents.updateOne(
    {id: "bbeda238-e8d9-4d8c-b93b-1b7694581adb"},
    {$set: {"call_flow.0.data.whoSpeaksFirst": "user"}}
  )
  ```

### Change 9: Enhanced QC Pipeline - Score Syncing (CODE CHANGE)
- **File**: `/app/backend/server.py` - `process_qc_analysis()` function
- **What Changed**: Added code to sync QC scores after analysis:
  1. Updates `campaign_calls` collection with `auto_analyzed=True`, `analyzed_at`, and `qc_scores`
  2. Syncs scores to `leads` collection (commitment, conversion, excellence, show_up_probability, risk_level)
  3. Auto-updates lead status based on risk level (low→qualified, medium→contacted, high→needs_followup)
- **Reason**: QC orchestrator was storing results in `call_analytics` but not syncing to `campaign_calls` or `leads`
- **Date**: 2025-12-02
- **TO REVERSE**: Remove the score syncing code blocks after line 7326 in server.py (after "QC analysis completed" log)

### Change 10: Auto Campaign QC Trigger (CODE CHANGE)
- **File**: `/app/backend/server.py`
- **What Changed**: 
  1. Added import: `from qc_enhanced_router import ... run_full_qc_analysis`
  2. Added new function `trigger_campaign_qc_for_call()` 
  3. Added call to this function in the hangup handler
- **What It Does**:
  - Checks agent's `auto_qc_settings.enabled` flag
  - Gets `campaign_id` from agent's auto_qc_settings
  - Runs `run_full_qc_analysis()` which performs Tech/Script/Tonality analysis
  - Stores detailed results in `campaign_calls` collection
- **Reason**: Campaign QC (Tech/Script/Tonality) was not being triggered automatically - only the QC Orchestrator (Commitment/Conversion/Excellence) was running
- **Date**: 2025-12-02
- **TO REVERSE**: Remove the `trigger_campaign_qc_for_call()` function and its call in the hangup handler

### Change 11: Auto QC Uses Same Analysis as Manual (CODE CHANGE)
- **File**: `/app/backend/qc_enhanced_router.py` - `run_full_qc_analysis()` function
- **What Changed**: 
  - Replaced `auto_qc_analyze_transcript()` with `analyze_script_with_llm()` 
  - Replaced `auto_qc_analyze_tonality()` with `analyze_tonality_with_llm()`
- **Reason**: Auto QC was producing different output format than manual QC. Now both use the same analysis functions and produce identical formats.
- **Date**: 2025-12-02
- **TO REVERSE**: Restore the original `auto_qc_analyze_transcript` and `auto_qc_analyze_tonality` calls

### Change 12: Frontend QC Display Fixes - REVERTED
- **Files**: TonalityTab.jsx, ScriptQualityTab.jsx
- **Status**: Reverted via git checkout - frontend now expects original format only
- **Date**: 2025-12-02

### Change 13: Implemented aiSpeaksAfterSilence Feature (CODE CHANGE)
- **File**: `/app/backend/server.py`
- **What Changed**: 
  1. Added reading of `aiSpeaksAfterSilence` and `silenceTimeout` from agent's start node settings
  2. When `whoSpeaksFirst: user` + `aiSpeaksAfterSilence: true`, schedules a delayed greeting task
  3. After `silenceTimeout` ms, if user hasn't spoken, AI speaks the greeting
  4. Added `user_has_spoken` flag tracking in `on_final_transcript` to cancel pending silence greeting
- **Settings Read from Flow Builder UI**:
  - `whoSpeaksFirst`: "ai" | "user"
  - `aiSpeaksAfterSilence`: true | false
  - `silenceTimeout`: milliseconds (default 2000)
- **Date**: 2025-12-02
- **TO REVERSE**: Remove the aiSpeaksAfterSilence logic blocks in the call.answered handler

### Change 14: Auto Appointment Detection from Calls (CODE CHANGE)
- **Files**: 
  - `/app/backend/server.py` - Added `auto_detect_appointment_from_call()` function
  - `/app/backend/crm_router.py` - Added detection and manual update endpoints
- **New Endpoints**:
  1. `POST /api/crm/calls/{call_id}/detect-appointment` - Manually trigger appointment detection on a call
  2. `POST /api/crm/appointments/{appt_id}/outcome` - Update appointment outcome (showed/no_show/cancelled)
- **What It Does**:
  - Automatically analyzes call transcripts for appointment indicators
  - Uses LLM to detect appointment scheduling with confidence score
  - Auto-creates appointment records when detected (confidence > 70%)
  - Updates lead status to "appointment_set"
  - Stores detection info (date, time, confidence, indicators)
- **Keywords Detected**: appointment, schedule, book, meeting, tomorrow, next week, days of week, am/pm, etc.
- **Date**: 2025-12-02
- **TO REVERSE**: Remove the `auto_detect_appointment_from_call()` function and related CRM endpoints

### Change 15: Webhook Tester UI in Flow Builder (CODE CHANGE)
- **Files**: 
  - `/app/frontend/src/components/FlowBuilder.jsx` - Added webhook tester panel
  - `/app/backend/server.py` - Added `/api/webhook-test` proxy endpoint
- **What It Does**:
  - Adds expandable "Webhook Tester" section to Function nodes in Flow Builder
  - Allows inputting test values for variables ({{variable_name}})
  - Sends test request through backend proxy to avoid CORS
  - Displays request/response with timing info
  - Shows how to use response variables in transitions
- **Date**: 2025-12-02
- **TO REVERSE**: Remove webhook tester state/UI from FlowBuilder.jsx and remove /api/webhook-test endpoint

### Change 16: Campaign Call Deletion Feature (CODE CHANGE)
- **Files**: 
  - `/app/frontend/src/components/CampaignDetailsPage.jsx` - Added delete mode UI
  - `/app/frontend/src/services/api.js` - Added `deleteCampaignCalls` API function
  - `/app/backend/qc_enhanced_router.py` - Added `/campaigns/{id}/delete-calls` endpoint
- **What It Does**:
  - "Delete Calls" button enters delete mode with checkboxes
  - Select individual calls or "Select All"
  - Confirmation dialog before deletion
  - Removes calls from: campaign_calls, call_analytics, qc_analysis_logs
  - Updates call_logs to remove campaign references (preserves original call)
  - Updates campaign stats after deletion
- **Date**: 2025-12-02
- **TO REVERSE**: Remove delete-related state/functions/UI from CampaignDetailsPage.jsx, remove API function, remove backend endpoint

---

## Current Status
- **MongoDB**: Already connected to production database (andramada.rznsqrc.mongodb.net/test_database)
- **User Found**: kendrickbowman9@gmail.com (ID: dcafa642-6136-4096-b77d-a4cb99a62651)
- **Campaigns**: 1 ("Test %" with ID: b7bd9ce7-2722-4c61-a2fc-ca1fb127d7b8)
- **Campaign Calls**: 2 calls in campaign_calls collection
- **Call Logs**: 427 total
- **QC Agents**: 3 agents

## Changes Made

### Change 1: Fixed QC data merging logic (lines 1115-1140)
- **File**: `/app/backend/qc_enhanced_router.py`
- **Lines**: 1115-1140
- **Original**: Blindly overwrote call_logs data with campaign_calls data even if campaign_calls had empty node_analyses
- **New**: Only use campaign_calls data if it has meaningful content (non-empty node_analyses). Falls back to call_logs data otherwise.
- **Reason**: Campaign batch analysis was storing empty node_analyses, overwriting good data from individual call analysis
- **Date**: 2025-12-01

### Change 2: Fixed campaign QC results endpoint (lines 177-252)
- **File**: `/app/backend/qc_enhanced_router.py`
- **Lines**: 177-252
- **Original**: Only loaded from campaign_calls collection without checking for empty results
- **New**: Merges with call_logs data when campaign_calls has empty node_analyses
- **Reason**: QC Results tab was showing calls as "Analyzed" but with no actual data
- **Date**: 2025-12-01

### Change 3: Fixed batch analysis error handling (lines 5339-5393)
- **File**: `/app/backend/qc_enhanced_router.py`
- **Lines**: 5339-5393
- **Original**: When `analyze_script_with_llm` threw an exception, it set `node_analyses = []` and continued storing empty results
- **New**: Now stores an error result with proper error message and skips saving empty success results
- **Reason**: Batch "Analyze All" was silently failing and marking calls as "completed" with empty data
- **Date**: 2025-12-01

### Change 4: Fixed "Analyze Again" button not re-analyzing (Frontend)
- **Files**: 
  - `/app/frontend/src/components/ScriptQualityTab.jsx`
  - `/app/frontend/src/components/TonalityTab.jsx`
- **Problem**: Clicking "Analyze Again" would instantly show the same saved results without running a new analysis
- **Root Cause**: `useEffect` was immediately restoring `savedResults` after `setScriptAnalysis(null)` was called
- **Fix**: Added `forceReanalyze` state flag that prevents `useEffect` from restoring saved results during reanalysis
- **Date**: 2025-12-01

### Change 5: Added Reset Analysis Functionality
- **Files**: 
  - `/app/backend/qc_enhanced_router.py` - Added two new endpoints
  - `/app/frontend/src/services/api.js` - Added API functions
  - `/app/frontend/src/components/CampaignDetailsPage.jsx` - Added UI buttons
- **New Endpoints**:
  - `POST /api/qc/enhanced/campaigns/{campaign_id}/reset-all-analysis` - Reset all calls in campaign
  - `POST /api/qc/enhanced/campaigns/{campaign_id}/calls/{call_id}/reset-analysis` - Reset single call
- **UI Changes**:
  - Added "Reset All" button (red) next to "Refresh" in QC Results tab header
  - Added individual reset button (trash icon) in the actions column for each call
- **Date**: 2025-12-01

### Change 6: Fixed LLM Provider Configuration for Script Analysis
- **File**: `/app/backend/qc_enhanced_router.py`
- **Lines**: 3644-3685
- **Problem**: When OpenAI was selected as provider, the code was still using Grok API URL with an OpenAI API key, causing HTTP 400 errors
- **Root Cause**: `api_configs` dictionary only had 'grok' configuration, defaulting to Grok for all providers
- **Fix**: 
  - Added proper OpenAI config with URL and model mappings (gpt-5 → gpt-4o)
  - Added Anthropic config with proper headers and request format
  - Added model fallback mappings (grok-3 → gpt-4o for OpenAI)
- **Date**: 2025-12-01

## How to Reverse All Changes

To reverse these changes, restore the original merging logic in qc_enhanced_router.py:
1. At line 1115, change back to simple if/overwrite logic
2. At line 177, remove the call_logs merging logic

Or use git to restore:
```bash
cd /app/backend
git checkout qc_enhanced_router.py
sudo supervisorctl restart backend
```

## Testing Results

### Test 1: QC Results API Endpoint (PASS)
- **Test**: Campaign QC results listing with data merging
- **Result**: ✅ PASS
- **Details**: 
  - First call now shows `has_script_qc: True` (was showing empty before)
  - `script_summary` shows actual data: 7 turns, 2 good quality, 5 needs improvement
  - Backend logs confirm merging logic: "Merged script_qc_results from call_logs"
- **Date**: 2025-12-01

### Test 2: Individual Call QC Data Fetch (PASS)
- **Test**: `/api/qc/enhanced/calls/fetch` endpoint
- **Result**: ✅ PASS
- **Details**:
  - `node_analyses count: 7` (was 0 before the fix)
  - `overall_quality: needs_improvement` (was showing nothing)
  - Turn-by-turn analysis data is now accessible
- **Date**: 2025-12-01

### Test 3: UI Screenshot Test (INCONCLUSIVE)
- **Test**: Preview environment frontend verification
- **Result**: ⚠️ Cookie/session issues in preview environment
- **Details**: Preview environment has known auth session persistence issues
- **Recommendation**: User should test in production after deployment
- **Date**: 2025-12-01

---
Last Updated: 2025-12-01
