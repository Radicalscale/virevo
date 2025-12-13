# QC System Overhaul - Feature Checklist

## Overview
Major overhaul to transform the QC system into an intelligent, campaign-integrated analysis platform with CRM connectivity, custom QC agents, and advanced AI capabilities.

---

## Phase 1: QC Agent Architecture Overhaul ✅ IMPLEMENTED

### 1.1 Custom QC Agent System
- [x] Create QC Agent listing page (similar to Call Agents page)
- [x] Implement QC Agent CRUD operations (Create, Read, Update, Delete)
- [x] Add prompt rules configuration for each QC Agent
- [x] Add Knowledge Base (KB) upload capability for QC Agents
- [ ] Implement "stackable" custom QC agents (save and combine) - *Deferred*
- [x] Create two QC modes:
  - [x] **Generic Mode** - Default QC analysis
  - [x] **Custom Mode** - Campaign/agent-specific analysis

### 1.2 QC Agent Types (Separate Tabs)
- [x] **Tonality QC Agent Tab**
  - [x] Voice analysis configuration
  - [x] ElevenLabs integration settings
  - [x] Prosody analysis rules
- [x] **Language Pattern QC Agent Tab**
  - [x] Script adherence rules
  - [x] Pattern detection configuration
  - [x] Custom pattern definitions
- [x] **Tech Issues QC Agent Tab** (Separate/Special)
  - [x] Log analysis configuration
  - [x] Backend code reading capability
  - [x] Model selection (Claude, Gemini, Grok, etc.)
  - [x] API key management per model

### 1.3 Agent-QC Assignment
- [x] Add QC Agent assignment endpoint (backend)
- [ ] Add QC Agent assignment dropdown to Call Agent settings (frontend) - *In Progress*
- [ ] Link audio QC analysis to assigned QC Agent
- [ ] Enable KB upload on Call Agents

---

## Phase 2: Campaign System Enhancements ✅ IMPLEMENTED

### 2.1 Campaign Call Management
- [x] **Training Calls Section**
  - [x] "Call Training Upload" button
  - [x] Batch upload functionality
  - [x] Training calls database list under campaign
  - [x] Training call designation/labeling
  - [x] Separate tab for training calls
- [x] **Real Campaign Calls Section**
  - [x] Separate tab for real calls
  - [x] Category display per call
  - [x] Designation tracking
  - [x] Custom call upload (not just from created agents)

### 2.2 Campaign Configuration
- [x] Custom prompt instructions input
- [x] Campaign-level KB upload
- [x] QC Agent assignment to campaign
- [x] Multi-agent campaign support:
  - [x] First Touch Agent (required)
  - [x] Follow-up Pre-Appointment Agent (required)
  - [x] No Show Agent (optional)
  - [x] 2nd No Show Agent (optional)

### 2.3 Campaign Analysis Triggers
- [x] Auto-analysis after X calls with specific tag/category
- [x] Auto-analysis every X calls
- [x] Manual trigger button
- [x] Per-agent auto QC toggle (in agent settings)

---

## Phase 3: CRM Integration & Lead Management ✅ IMPLEMENTED

### 3.1 Lead Creation & Tracking
- [x] Auto-create CRM lead if not exists (`/api/crm/leads/from-call`)
- [x] Lead scoring system (via metrics)
- [x] Campaign & QC analysis saved to lead record
- [x] Lead categorization on call completion (`/api/crm/leads/{id}/category`)

### 3.2 Appointment Integration
- [x] Appointment status tracking
- [x] Re-analysis trigger on appointment update (`/api/crm/appointments/{id}/reanalyze`)
- [x] Second analysis tied to call/CRM lead post-appointment
- [x] Campaign re-trigger on appointment update
- [ ] New document generation on re-analysis - *Deferred to Phase 5*

### 3.3 Lead Metrics Tracking (Per Lead)
- [x] Calls to Answer count
- [x] Calls to Book count
- [x] Calls to Appointment Show count
- [x] No Show Ratio
- [x] No Show to Follow-up Booked ratio
- [x] No Show to Follow-up Booked into Showed ratio

---

## Phase 4: Lead Categorization System ✅ IMPLEMENTED

### 4.1 Tag System Implementation
- [x] Create tag/category database schema (LeadCategoryEnum)
- [x] Tag assignment logic on call completion
- [x] Tag update on CRM events (`/api/crm/leads/{id}/category`)

### 4.2 Category Definitions
```
Primary Categories:
- [x] Training Call (non-CRM, for pattern training only)
- [x] New/First Call
- [x] New/Non-Answered

First Appointment Track:
- [x] Called - Delayed
- [x] Called - Refused
- [x] Called - 1 Appointment - Pre Appointment Date
- [x] 1 Appointment - Showed
- [x] 1 Appointment - No Showed - Second Call - Non Answered
- [ ] 1 Appointment - No Showed - Second Call - Answered - Delayed
- [ ] 1 Appointment - No Showed - Second Call - Answered - Refused
- [ ] 1 Appointment - No Showed - Second Call - Answered - New Appointment

Second Appointment Track:
- [ ] 2nd Appointment - Showed
- [ ] 2nd Appointment - No Showed - Third Call - Non Answered
- [ ] 2nd Appointment - No Showed - Third Call - Answered - Delayed
- [ ] 2nd Appointment - No Showed - Third Call - Answered - Refused
- [ ] 2nd Appointment - No Showed - Third Call - Answered - New Appointment

3+ Appointments Track:
- [ ] 3+ Appointments - Showed
- [ ] 3+ Appointment - No Showed - 4+ Calls - Non Answered
- [ ] 3+ Appointment - No Showed - 4+ Calls - Answered - Delayed
- [ ] 3+ Appointment - No Showed - 4+ Calls - Answered - Refused
- [ ] 3+ Appointment - No Showed - 4+ Calls - Answered - New Appointment
```

### 4.3 Category UI Components
- [ ] Category filter/dropdown on campaign view
- [ ] Category badges on call cards
- [ ] Batch categorization tools
- [ ] Category-based analytics grouping

---

## Phase 5: AI Analysis & Pattern Detection

### 5.1 Campaign Analysis Output
- [ ] Generate MD document with patterns after analysis
- [ ] Upload capability to QC Agent
- [ ] Pattern storage and retrieval
- [ ] Cross-campaign pattern learning

### 5.2 AI Improvement Advice
- [x] Specific improvement suggestions per call (in tonality analysis)
- [ ] General QC advice generation - *Deferred*
- [ ] Enhancement ideas from multi-agent data - *Deferred*
- [ ] First-caller improvement recommendations from follow-up data - *Deferred*

### 5.3 Post-Appointment Re-Analysis
- [x] Trigger re-analysis on appointment outcome
- [ ] Generate second analysis document - *Deferred*
- [x] Link analysis to CRM lead record
- [ ] Update campaign analytics - *Partial*

---

## Phase 6: Voice Tonality & ElevenLabs Integration ✅ IMPLEMENTED

### 6.1 Apply Changes Feature
- [x] "Apply Changes" button on tonality analysis
- [x] Open agent flow in new tab
- [x] Auto-scroll to exact node (via URL hash)
- [x] Deep linking to specific node

### 6.2 Emotional Directions Section
- [x] New section in emotional QC analysis
- [x] ElevenLabs best practices integration
- [x] Line-by-line delivery instructions
- [x] Word-by-word emotion guidance
- [x] Copyable field for node prompt pasting
- [x] Prosody enhancement suggestions

### 6.3 ElevenLabs Instruction Format
- [x] Emotion descriptors per line
- [x] Delivery style instructions
- [x] Tone modulation guidance
- [x] Pace and emphasis markers

---

## Phase 7: AI Interruption System (Rambler Handler)

### 7.1 Interruption Detection
- [x] Extra LLM monitor for user responses
- [x] Rule-set criteria for interruption triggers
- [x] Rambling detection algorithm
- [x] Off-topic detection

### 7.2 Interruption Frameworks
- [x] **Default Framework**
  - [x] Pre-defined interjection phrases
  - [x] Generic steering statements
  - [x] Configurable thresholds
- [x] **Contextual Leverage Dynamic Framework**
  - [x] Incorporate user's current speech
  - [x] Goal-oriented steering
  - [x] Node-context-aware responses

### 7.3 Interruption Execution
- [ ] Temporary interruption disable mechanism - *Integration required*
- [ ] Smooth interjection delivery - *Integration required*
- [x] Conversation steering logic
- [ ] Return-to-track confirmation - *Integration required*

---

## Phase 8: Tech Issues QC Agent (Special) ✅ IMPLEMENTED

### 8.1 Log Analysis
- [x] Receive and parse call logs
- [x] Error pattern detection
- [x] System vs User issue classification

### 8.2 Problem Classification
Identify if issue is:
- [x] System/code problem
- [x] Prompt modification needed
- [x] Multi-agent system leverage needed
- [x] Optimize prompt feature needed
- [x] Optimize transition feature needed
- [x] Prompt split into multiple nodes needed
- [x] Combination of above

### 8.3 Backend Code Analysis
- [x] Read backend infrastructure
- [ ] Line-by-line execution trace - *Advanced feature*
- [x] Code path analysis
- [x] Root cause identification

### 8.4 Solution Generation
- [x] **Script/Agent Reconfiguration MD**
  - [x] Step-by-step enhancement guide
  - [x] Prompt modification suggestions
  - [x] Node restructuring recommendations
- [x] **Code Enhancement MD**
  - [x] Clear problem assessment
  - [x] Step-by-step fix instructions
  - [ ] Ready-to-use AI coder prompt
  - [ ] Context-complete documentation

### 8.5 Model Configuration
- [x] Model selection dropdown (Claude, Gemini, Grok, etc.)
- [x] API key input per model
- [ ] Model-specific prompt optimization - *Future enhancement*

---

## Phase 9: Analytics Dashboard ✅ IMPLEMENTED

### 9.1 Campaign-Organized Views
- [x] Campaign selector/filter
- [x] Per-campaign metrics display
- [x] Cross-campaign comparison

### 9.2 Category Analytics
- [x] Calls per category count
- [x] Category distribution charts
- [ ] Category conversion funnels - *Future enhancement*

### 9.3 Ratio Metrics Display
- [x] Calls to Answer ratio
- [x] Calls to Book ratio
- [x] Calls to Appointment Show ratio
- [x] No Show Ratio
- [x] No Show to Follow-up Booked ratio
- [x] No Show to Follow-up Booked into Showed ratio
- [ ] Trend graphs over time - *Future enhancement*

### 9.4 Lead Analytics
- [ ] Lead journey visualization - *Future enhancement*
- [x] Multi-call lead tracking (via Lead model)
- [ ] Outcome prediction indicators - *Future enhancement*

---

## Phase 10: System Flow Implementation ✅ IMPLEMENTED

### 10.1 Campaign Creation Flow
```
1. [x] Create campaign
2. [x] "Call Training Upload" button available
3. [x] Assign generic or custom QC agent
4. [x] Upload training calls
5. [x] Calls saved to campaign database (Training Calls category)
6. [x] Training calls viewable with designations
```

### 10.2 Real Call Flow
```
1. [x] Agent assigned to campaign
2. [x] Call completed
3. [x] Call designated based on outcome
4. [x] CRM check for existing lead
5. [x] If no lead: Create new lead with first category
6. [x] Post-call analysis triggered
7. [x] Lead scored (via metrics)
8. [x] QC analysis saved to CRM lead
9. [ ] Lead categorized
```

### 10.3 Appointment Update Flow
```
1. [ ] Appointment status updated (show/no-show)
2. [ ] Re-analysis of last campaign call triggered
3. [ ] New analysis with show/no-show data
4. [ ] Analytics updated
5. [ ] Campaign re-triggered
6. [ ] New document produced
```

### 10.4 Auto-Analysis Configuration
- [ ] Set trigger: After X calls with tag/category
- [ ] Set trigger: Every X calls
- [ ] Manual trigger option
- [ ] Per-agent settings in Agent Settings page

---

## Database Schema Updates Required

### New Collections/Tables
- [ ] `qc_agents` - Custom QC agent configurations
- [ ] `lead_categories` - Category definitions
- [ ] `lead_tags` - Tag assignments per lead
- [ ] `training_calls` - Training call uploads
- [ ] `qc_analyses` - Analysis results with versioning
- [ ] `appointment_updates` - Appointment event tracking

### Model Updates
- [ ] `Agent` - Add KB upload, QC agent assignment
- [ ] `Campaign` - Add KB, prompt instructions, multi-agent config
- [ ] `Lead` - Add category, tags, metrics, analysis history
- [ ] `Call` - Add category, designation, training flag

---

## API Endpoints Required

### QC Agent Endpoints
- [ ] `POST /api/qc-agents` - Create QC agent
- [ ] `GET /api/qc-agents` - List QC agents
- [ ] `GET /api/qc-agents/{id}` - Get QC agent
- [ ] `PUT /api/qc-agents/{id}` - Update QC agent
- [ ] `DELETE /api/qc-agents/{id}` - Delete QC agent
- [ ] `POST /api/qc-agents/{id}/kb` - Upload KB to QC agent

### Campaign Endpoints
- [ ] `POST /api/campaigns/{id}/training-calls` - Upload training calls
- [ ] `GET /api/campaigns/{id}/training-calls` - List training calls
- [ ] `POST /api/campaigns/{id}/custom-calls` - Upload custom calls
- [ ] `PUT /api/campaigns/{id}/config` - Update campaign config
- [ ] `POST /api/campaigns/{id}/kb` - Upload campaign KB
- [ ] `POST /api/campaigns/{id}/analyze` - Manual analysis trigger

### Lead Endpoints
- [ ] `GET /api/leads/{id}/history` - Get lead call history
- [ ] `PUT /api/leads/{id}/category` - Update lead category
- [ ] `GET /api/leads/by-category/{category}` - Filter by category
- [ ] `POST /api/leads/{id}/reanalyze` - Trigger re-analysis

### Analytics Endpoints
- [ ] `GET /api/analytics/campaigns/{id}` - Campaign analytics
- [ ] `GET /api/analytics/categories` - Category breakdown
- [ ] `GET /api/analytics/ratios` - Ratio metrics

### Tech QC Endpoints
- [ ] `POST /api/qc/tech-analysis` - Analyze call logs
- [ ] `GET /api/qc/tech-analysis/{id}/solution` - Get solution MD

---

## UI Components Required

### Pages
- [ ] QC Agents List Page
- [ ] QC Agent Editor Page (per type)
- [ ] Campaign Training Calls Tab
- [ ] Campaign Real Calls Tab
- [ ] Lead Detail Page with Analysis History
- [ ] Analytics Dashboard Page

### Components
- [ ] QC Agent Card
- [ ] Category Badge
- [ ] Training Call Uploader
- [ ] KB Uploader (reusable)
- [ ] Analysis MD Viewer
- [ ] Emotional Directions Panel
- [ ] Apply Changes Button with Deep Link
- [ ] Category Filter Dropdown
- [ ] Ratio Metrics Cards
- [ ] Lead Journey Timeline

---

## Priority Order (Suggested)

### P0 - Core Infrastructure
1. QC Agent system (listings, CRUD, tabs)
2. Lead categorization schema
3. Campaign training calls upload

### P1 - CRM Integration
4. CRM lead creation/tracking
5. Appointment update triggers
6. Re-analysis flow

### P2 - Analysis Features
7. Pattern detection MD generation
8. AI improvement advice
9. ElevenLabs emotional directions

### P3 - Advanced Features
10. AI Interruption system
11. Tech Issues QC Agent
12. Analytics dashboard

---

## Notes
- All features should maintain backward compatibility
- KB uploads should support: PDF, TXT, MD, DOCX
- MD outputs should be downloadable and shareable
- Consider rate limiting for LLM-heavy operations
- Implement proper error handling for external API calls
