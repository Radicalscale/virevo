# QC System Overhaul - Testing Guide

This document provides step-by-step instructions to test every feature of the new QC System.

---

## Pre-Testing Setup

### 1. Login
- Navigate to: `https://li-ai.org` (production) or `http://localhost:3000` (local)
- Login with your credentials
- You should see the sidebar with the new **QC System** section

### 2. Verify Navigation
- [ ] Sidebar shows "QC System" section with ⚡ icon
- [ ] "QC Agents" link with NEW badge
- [ ] "QC Campaigns" link
- [ ] "QC Analytics" link with NEW badge
- [ ] "QC Tester" link
- [ ] Quick create links for Tonality, Language Pattern, Tech Issues agents

---

## Feature 1: QC Agents (CRUD)

### 1.1 View QC Agents List
**Navigate to:** Sidebar → QC Agents (or `/qc/agents`)

- [ ] Page loads with tabs: All, Tonality, Language Pattern, Tech Issues
- [ ] Empty state shows "No QC Agents Yet" with quick-create cards
- [ ] Each tab shows count of agents

### 1.2 Create Tonality QC Agent
**Navigate to:** QC Agents → Click "Tonality Agent" card (or `/qc/agents/new?type=tonality`)

- [ ] Agent type selection shows 4 options (Tonality highlighted)
- [ ] Fill in:
  - Name: "Sales Tonality Analyzer"
  - Description: "Analyzes voice delivery for sales calls"
  - Mode: Custom
  - LLM Provider: Grok
  - LLM Model: Grok 3
- [ ] Click "Save Agent"
- [ ] Redirects to QC Agents list
- [ ] New agent appears in list with correct type badge

### 1.3 Create Language Pattern QC Agent
**Navigate to:** Sidebar → QC System → Language Pattern (or `/qc/agents/new?type=language_pattern`)

- [ ] Create agent with:
  - Name: "Script Quality Checker"
  - Description: "Checks script adherence and patterns"
- [ ] Enable "Check Goal Alignment" in Analysis Rules
- [ ] Save agent

### 1.4 Create Tech Issues QC Agent
**Navigate to:** Sidebar → QC System → Tech Issues (or `/qc/agents/new?type=tech_issues`)

- [ ] Create agent with:
  - Name: "Call Log Analyzer"
  - Description: "Analyzes call logs for technical issues"
- [ ] Enable "Generate AI Coder Prompt" in Analysis Rules
- [ ] Save agent

### 1.5 Edit QC Agent
**Navigate to:** QC Agents → Click on any agent card

- [ ] Agent details load correctly
- [ ] Update name or description
- [ ] Click Save
- [ ] Changes persist

### 1.6 Upload Knowledge Base to QC Agent
**Navigate to:** QC Agent Editor → Knowledge Base tab

- [ ] Click "Upload File"
- [ ] Select a .txt or .md file
- [ ] File appears in KB items list
- [ ] Delete KB item works

### 1.7 Delete QC Agent
**Navigate to:** QC Agents list → Click trash icon on agent card

- [ ] Delete confirmation appears
- [ ] Click delete again to confirm
- [ ] Agent removed from list

---

## Feature 2: QC Campaigns

### 2.1 Create Campaign
**Navigate to:** Sidebar → QC Campaigns → "Create Campaign" button

- [ ] Fill in:
  - Name: "Q4 Sales Campaign"
  - Description: "Test campaign for QC"
- [ ] Click Create
- [ ] Campaign appears in list

### 2.2 View Campaign Details
**Navigate to:** QC Campaigns → Click on campaign card (or `/qc/campaigns/{id}`)

- [ ] Campaign details page loads with tabs:
  - Overview
  - Training Calls
  - Real Calls
  - Patterns
  - Agents
- [ ] Metrics cards show: Real Calls, Training Calls, Patterns, KB Items, QC Agents

### 2.3 Upload Training Calls
**Navigate to:** Campaign Details → Training Calls tab

- [ ] Click "Upload Training Call"
- [ ] Select an audio file (.mp3, .wav)
- [ ] File uploads and appears in list
- [ ] Status shows "Pending" (not processed)
- [ ] Can delete training call

### 2.4 Configure Campaign Settings
**Navigate to:** Campaign Details → Settings button (or `/qc/campaigns/{id}/settings`)

**General Tab:**
- [ ] Edit campaign name and description
- [ ] Add custom prompt instructions
- [ ] Toggle analysis rules (brevity, goal alignment, naturalness)

**QC Agents Tab:**
- [ ] See Tonality, Language Pattern, Tech Issues sections
- [ ] Select a QC agent from dropdown for each type
- [ ] "Create X Agent" link appears if no agents of that type exist

**Campaign Agents Tab:**
- [ ] Add agents for each role (First Touch, Follow-up, No Show, 2nd No Show)
- [ ] Remove agent from role
- [ ] See explanation of how multi-agent campaigns work

**Automation Tab:**
- [ ] Toggle Auto Pattern Detection
- [ ] Set "Analyze After N Calls" (e.g., 10)
- [ ] Set "Analyze Every N Calls" (e.g., 5)

**CRM Integration Tab:**
- [ ] Toggle "Enable CRM Integration"
- [ ] Toggle "Auto-Create Leads"
- [ ] Toggle "Auto Re-analyze on Appointment Update"

- [ ] Click "Save Changes"
- [ ] Settings persist after page reload

---

## Feature 3: QC Analytics Dashboard

### 3.1 View Analytics Overview
**Navigate to:** Sidebar → QC Analytics (or `/qc/analytics`)

- [ ] Page loads with:
  - Campaign filter dropdown
  - Date range filter (7d, 30d, 90d, All)
  - Refresh and Export buttons
- [ ] Main metrics: Total Calls, Total Leads, Appointments Set, Showed Up, No Shows

### 3.2 Filter by Campaign
- [ ] Select specific campaign from dropdown
- [ ] Metrics update for that campaign
- [ ] Select "All Campaigns" to see aggregate

### 3.3 View Ratio Metrics
**Click:** Ratio Metrics tab

- [ ] See cards for:
  - Calls to Answer
  - Calls to Book
  - Show Rate (percentage)
  - No Show Rate (percentage)
  - No-Show to Follow-up Booked
  - No-Show Recovery to Showed

### 3.4 View Lead Categories
**Click:** Lead Categories tab

- [ ] See category distribution chart (bar chart)
- [ ] Categories listed with counts

### 3.5 View By Campaign
**Click:** By Campaign tab

- [ ] See all campaigns listed
- [ ] Each shows: Calls, Leads, Appts Set, Showed, No Shows
- [ ] "View Details" button links to campaign page

### 3.6 Export Analytics
- [ ] Click "Export" button
- [ ] JSON file downloads with analytics data

---

## Feature 4: Tonality Analysis & ElevenLabs Directions

### 4.1 Run Tonality Analysis
**Navigate to:** Calls → Select a call with recording → QC Dashboard → Tonality tab

- [ ] Click "Analyze Tonality"
- [ ] Analysis runs (may take 30-60 seconds)
- [ ] Results show:
  - Overall delivery score
  - Node-by-node analysis
  - Tone assessment per turn
  - Energy matching
  - Improved delivery suggestions

### 4.2 View SSML Recommendations
- [ ] SSML/Prosody Recommendations section visible
- [ ] Each recommendation shows turn number and type
- [ ] "Copy" button copies SSML to clipboard

### 4.3 Generate ElevenLabs Emotional Directions
**In Tonality tab results:**

- [ ] Find "ElevenLabs Emotional Directions" section
- [ ] Click "Generate" button
- [ ] See generated:
  - Emotion Tags (warm, professional, etc.)
  - Pacing Instructions
  - Tone Description
  - Line-by-Line Directions
  - Full Copyable Prompt
- [ ] Click "Copy to Clipboard" on the full prompt
- [ ] Verify clipboard contains the prompt

### 4.4 Apply Changes Button
- [ ] Each turn/node shows "Apply Changes in Flow Builder" link
- [ ] Click the link
- [ ] New tab opens with agent flow builder
- [ ] (Should scroll to specific node - verify URL has #node-{id})

### 4.5 Apply All Changes
- [ ] At bottom of Tonality results, see "Open Agent Flow Builder (Apply All Changes)" button
- [ ] Click button
- [ ] New tab opens to flow builder

---

## Feature 5: CRM Lead Categories

### 5.1 View Lead with Category
**Navigate to:** CRM → Click on a lead

- [ ] Lead detail page shows "Category" field
- [ ] Category displayed as badge

### 5.2 Update Lead Category (API Test)
**Using curl or API client:**

```bash
curl -X PUT "https://li-ai.org/api/crm/leads/{lead_id}/category" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"category": "1_appointment_pre_date", "reason": "Appointment scheduled"}'
```

- [ ] Returns success
- [ ] Lead shows updated category

### 5.3 View Leads by Category (API Test)
```bash
curl "https://li-ai.org/api/crm/leads/by-category/new_first_call" \
  -H "Authorization: Bearer {token}"
```

- [ ] Returns list of leads in that category

---

## Feature 6: Appointment Re-Analysis

### 6.1 Trigger Re-Analysis (API Test)
**Prerequisites:** Have an appointment linked to a lead with call history

```bash
curl -X POST "https://li-ai.org/api/crm/appointments/{appt_id}/reanalyze" \
  -H "Authorization: Bearer {token}"
```

- [ ] Returns success with:
  - reanalysis_id
  - outcome (showed/no_show)
  - prediction_accuracy

### 6.2 View Lead Call History (API Test)
```bash
curl "https://li-ai.org/api/crm/leads/{lead_id}/call-history" \
  -H "Authorization: Bearer {token}"
```

- [ ] Returns list of calls with QC analysis for each

---

## Feature 7: AI Interruption System (API Test)

### 7.1 Check for Interruption (Default Framework)
```bash
curl -X POST "https://li-ai.org/api/qc/agents/interruption/check" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_text": "Well you know I was thinking about this the other day and my friend told me about how she had this similar experience where she went to the store and they had all these different options and she could not decide which one to pick because there were so many choices and prices were all different and then the salesperson came over and started talking about warranties and extended coverage plans and she got really confused...",
    "conversation_context": [
      {"role": "agent", "content": "Hi, I am calling about your appointment."},
      {"role": "user", "content": "Oh hi, yes I remember."}
    ],
    "node_goal": "Confirm appointment time",
    "duration_seconds": 45,
    "framework": "default"
  }'
```

- [ ] Returns:
  - should_interrupt: true (text is > 100 words)
  - interruption_phrase: one of the default phrases
  - detected_issues: ["rambling"]

### 7.2 Check for Interruption (Contextual Framework)
```bash
curl -X POST "https://li-ai.org/api/qc/agents/interruption/check" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_text": "I was at the grocery store yesterday and they had these amazing deals on produce...",
    "conversation_context": [
      {"role": "agent", "content": "Let us discuss your insurance coverage."}
    ],
    "node_goal": "Discuss insurance options",
    "duration_seconds": 20,
    "framework": "contextual"
  }'
```

- [ ] Returns:
  - should_interrupt: true (off-topic)
  - interruption_phrase: contextual phrase referencing user's words
  - detected_issues: ["off_topic"]

### 7.3 Get Default Phrases
```bash
curl "https://li-ai.org/api/qc/agents/interruption/phrases" \
  -H "Authorization: Bearer {token}"
```

- [ ] Returns list of default interruption phrases
- [ ] Returns threshold settings

---

## Feature 8: Tech Issues QC Analysis (API Test)

### 8.1 Analyze Tech Issues
**Prerequisites:** Have a Tech Issues QC Agent created

```bash
curl -X POST "https://li-ai.org/api/qc/agents/{tech_agent_id}/analyze-tech-issues" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "{call_id}",
    "call_logs": [
      {"timestamp": "2024-01-01T10:00:00", "level": "ERROR", "message": "TTS timeout after 20 seconds"},
      {"timestamp": "2024-01-01T10:00:05", "level": "ERROR", "message": "Failed to play audio chunk"}
    ]
  }'
```

- [ ] Returns:
  - issue_type (system/prompt/code/etc.)
  - issue_description
  - severity
  - script_reconfiguration_md (if applicable)
  - code_enhancement_md (if applicable)
  - ai_coder_prompt (ready-to-use prompt)
  - recommendations

---

## Feature 9: Training Calls & Custom Calls

### 9.1 Upload Training Call (API Test)
```bash
curl -X POST "https://li-ai.org/api/qc/enhanced/campaigns/{campaign_id}/training-calls" \
  -H "Authorization: Bearer {token}" \
  -F "file=@/path/to/call.mp3" \
  -F "designation=Sales Demo" \
  -F "tags=demo,sales"
```

- [ ] Returns success with training_call_id

### 9.2 Upload Custom Call (API Test)
```bash
curl -X POST "https://li-ai.org/api/qc/enhanced/campaigns/{campaign_id}/custom-calls" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": [{"role": "agent", "content": "Hello"}, {"role": "user", "content": "Hi"}],
    "designation": "Imported Call",
    "category": "new_first_call"
  }'
```

- [ ] Returns success with campaign_call_id

---

## Feature 10: Auto Lead Creation

### 10.1 Create Lead from Call (API Test)
```bash
curl -X POST "https://li-ai.org/api/crm/leads/from-call" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "{call_id}",
    "phone": "+15551234567",
    "campaign_id": "{campaign_id}",
    "agent_id": "{agent_id}",
    "direction": "outbound"
  }'
```

- [ ] If new phone: Creates lead, returns is_new: true
- [ ] If existing phone: Updates lead, returns is_new: false

---

## Quick Reference: All New URLs

| Feature | URL |
|---------|-----|
| QC Agents List | `/qc/agents` |
| Create Tonality Agent | `/qc/agents/new?type=tonality` |
| Create Language Pattern Agent | `/qc/agents/new?type=language_pattern` |
| Create Tech Issues Agent | `/qc/agents/new?type=tech_issues` |
| Edit QC Agent | `/qc/agents/{id}` |
| QC Campaigns | `/qc/campaigns` |
| Campaign Details | `/qc/campaigns/{id}` |
| Campaign Settings | `/qc/campaigns/{id}/settings` |
| QC Analytics Dashboard | `/qc/analytics` |
| QC Tester | `/qc-tester` |
| CRM Leads | `/crm` |

---

## Quick Reference: All New API Endpoints

### QC Agents
- `GET /api/qc/agents` - List all QC agents
- `POST /api/qc/agents` - Create QC agent
- `GET /api/qc/agents/{id}` - Get QC agent
- `PUT /api/qc/agents/{id}` - Update QC agent
- `DELETE /api/qc/agents/{id}` - Delete QC agent
- `POST /api/qc/agents/{id}/kb` - Upload KB file
- `GET /api/qc/agents/{id}/kb` - List KB items
- `POST /api/qc/agents/{id}/emotional-directions` - Generate ElevenLabs directions
- `POST /api/qc/agents/{id}/analyze-tech-issues` - Run tech analysis

### Interruption System
- `POST /api/qc/agents/interruption/check` - Check if should interrupt
- `GET /api/qc/agents/interruption/phrases` - Get default phrases

### Campaigns
- `POST /api/qc/enhanced/campaigns/{id}/training-calls` - Upload training call
- `GET /api/qc/enhanced/campaigns/{id}/training-calls` - List training calls
- `POST /api/qc/enhanced/campaigns/{id}/custom-calls` - Upload custom call
- `POST /api/qc/enhanced/campaigns/{id}/kb` - Upload campaign KB
- `PUT /api/qc/enhanced/campaigns/{id}/agents` - Update multi-agent config

### CRM
- `PUT /api/crm/leads/{id}/category` - Update lead category
- `GET /api/crm/leads/by-category/{category}` - Get leads by category
- `PUT /api/crm/leads/{id}/metrics` - Update lead metrics
- `POST /api/crm/appointments/{id}/reanalyze` - Trigger re-analysis
- `GET /api/crm/leads/{id}/call-history` - Get lead call history
- `POST /api/crm/leads/from-call` - Auto-create lead from call

---

## Testing Checklist Summary

### UI Features
- [ ] QC Agents CRUD (create, edit, delete all 3 types)
- [ ] QC Agent KB upload
- [ ] Campaign creation and management
- [ ] Campaign settings (all 5 tabs)
- [ ] Training calls upload
- [ ] QC Analytics dashboard
- [ ] Tonality emotional directions
- [ ] Apply Changes button

### API Features
- [ ] Interruption check (default framework)
- [ ] Interruption check (contextual framework)
- [ ] Tech issues analysis
- [ ] Lead category update
- [ ] Lead metrics update
- [ ] Appointment re-analysis
- [ ] Auto lead creation from call

---

## Notes

- **Preview Environment**: Some features require production environment due to .env pointing to production URLs
- **Redis/ffmpeg warnings**: Expected in preview environment
- **API Authentication**: All API endpoints require valid JWT token in Authorization header
