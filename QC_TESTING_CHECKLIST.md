# QC Intelligence System - Comprehensive Testing Checklist

> **Version**: 2.0  
> **Created**: November 2025  
> **Last Updated**: November 29, 2025  
> **Purpose**: Verify 100% operational status of all QC features

---

## How to Use This Checklist

- ✅ = Passed
- ❌ = Failed (note the issue)
- ⏭️ = Skipped (note why)
- 🔄 = Needs retest

**Testing Order**: Follow sections in order - later tests depend on earlier ones.

---

## Table of Contents

1. [Pre-Flight Checks](#1-pre-flight-checks)
2. [QC Agents - CRUD Operations](#2-qc-agents---crud-operations)
3. [QC Agent Configuration](#3-qc-agent-configuration)
4. [Knowledge Base](#4-knowledge-base)
5. [Learning System - Playbooks](#5-learning-system---playbooks)
6. [Learning System - Brain Prompts](#6-learning-system---brain-prompts)
7. [Learning System - Configuration](#7-learning-system---configuration)
8. [Campaigns - CRUD Operations](#8-campaigns---crud-operations)
9. [Campaign - QC Agent Assignment](#9-campaign---qc-agent-assignment)
10. [Training Calls - Upload & Management](#10-training-calls---upload--management)
11. [Training Calls - Outcome Tracking](#11-training-calls---outcome-tracking)
12. [Tech Issues Agent](#12-tech-issues-agent)
13. [QC Analysis - Tonality & Language Pattern](#13-qc-analysis---tonality--language-pattern)
14. [Prediction System & Learning Integration](#14-prediction-system--learning-integration)
15. [Learning Loop - End to End](#15-learning-loop---end-to-end)
16. [Patterns & Stats](#16-patterns--stats)
17. [API Key Management](#17-api-key-management)
18. [Edge Cases & Error Handling](#18-edge-cases--error-handling)
19. [Stress Tests](#19-stress-tests)
20. [UI/UX Verification](#20-uiux-verification)

---

## 1. Pre-Flight Checks

### 1.1 System Health
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 1.1.1 | Backend health endpoint | `GET /api/health` returns `{"status": "healthy"}` | | |
| 1.1.2 | Database connected | Health shows `"database": "connected"` | | |
| 1.1.3 | Frontend loads | Home page renders without errors | | |
| 1.1.4 | Authentication works | Can log in with valid credentials | | |
| 1.1.5 | Sidebar navigation | All QC menu items visible and clickable | | |

### 1.2 API Keys Configured
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 1.2.1 | Grok API key exists | Key present in API Keys page | | |
| 1.2.2 | API key is valid | Test call to Grok succeeds | | |
| 1.2.3 | OpenAI key (if used) | Key present and valid | | |
| 1.2.4 | Emergent LLM key fallback | Works when user key missing | | |

---

## 2. QC Agents - CRUD Operations

### 2.1 Create QC Agents
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 2.1.1 | Create Tonality Agent | Agent created, appears in list | | |
| 2.1.2 | Create Language Pattern Agent | Agent created, appears in list | | |
| 2.1.3 | Create Tech Issues Agent | Agent created, appears in list | | |
| 2.1.4 | Create Generic Agent | Agent created, appears in list | | |
| 2.1.5 | Create with minimal fields | Only name required, defaults applied | | |
| 2.1.6 | Create with all fields | All fields saved correctly | | |

### 2.2 Read QC Agents
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 2.2.1 | List all agents | All created agents appear | | |
| 2.2.2 | Filter by type (Tonality tab) | Only tonality agents shown | | |
| 2.2.3 | Filter by type (Language tab) | Only language pattern agents shown | | |
| 2.2.4 | Filter by type (Tech tab) | Only tech issues agents shown | | |
| 2.2.5 | View agent details | All fields display correctly | | |
| 2.2.6 | Agent details page loads | No console errors | | |

### 2.3 Update QC Agents
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 2.3.1 | Update name | Name changes, saved | | |
| 2.3.2 | Update description | Description changes, saved | | |
| 2.3.3 | Update LLM provider | Provider changes, saved | | |
| 2.3.4 | Update LLM model | Model changes, saved | | |
| 2.3.5 | Toggle active status | Status toggles correctly | | |
| 2.3.6 | Update system prompt | Prompt saved, persists on reload | | |

### 2.4 Delete QC Agents
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 2.4.1 | Delete agent | Agent removed from list | | |
| 2.4.2 | Delete confirmation | Confirmation dialog appears | | |
| 2.4.3 | Cancel delete | Agent not deleted | | |
| 2.4.4 | Delete agent with assignments | Appropriate warning/handling | | |

---

## 3. QC Agent Configuration

### 3.1 General Tab
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 3.1.1 | Name field | Editable, saves | | |
| 3.1.2 | Description field | Editable, saves | | |
| 3.1.3 | Agent type display | Shows correct type (read-only) | | |
| 3.1.4 | Active toggle | Works, saves state | | |

### 3.2 Prompt & Instructions Tab
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 3.2.1 | System prompt field | Large textarea, saves | | |
| 3.2.2 | Analysis focus field | Saves custom focus areas | | |
| 3.2.3 | Custom criteria field | Saves custom criteria | | |
| 3.2.4 | Output format field | Saves format instructions | | |
| 3.2.5 | Default prompt loads | Type-specific default appears | | |
| 3.2.6 | Long prompt (5000+ chars) | Saves without truncation | | |

### 3.3 LLM Settings Tab
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 3.3.1 | Provider dropdown | Shows available providers | | |
| 3.3.2 | Select Grok | Saves provider as grok | | |
| 3.3.3 | Select OpenAI | Saves provider as openai | | |
| 3.3.4 | Model dropdown | Shows models for selected provider | | |
| 3.3.5 | Change model | Saves model selection | | |

### 3.4 Analysis Rules Tab (Type-Specific)
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 3.4.1 | Tonality rules display | Tonality-specific options shown | | |
| 3.4.2 | Language pattern rules | Language-specific options shown | | |
| 3.4.3 | Tech issues rules | Tech-specific options shown | | |
| 3.4.4 | Generic agent message | Shows "use prompt" message | | |

---

## 4. Knowledge Base

### 4.1 KB Upload
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 4.1.1 | Upload PDF | File uploads, appears in list | | |
| 4.1.2 | Upload TXT | File uploads, appears in list | | |
| 4.1.3 | Upload MD | File uploads, appears in list | | |
| 4.1.4 | Upload multiple files | All files appear | | |
| 4.1.5 | Large file (10MB+) | Uploads or shows size error | | |
| 4.1.6 | Invalid file type | Error message shown | | |

### 4.2 KB Management
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 4.2.1 | View KB list | All uploaded files shown | | |
| 4.2.2 | File name displayed | Correct filename shown | | |
| 4.2.3 | Delete KB item | Item removed from list | | |
| 4.2.4 | KB count badge | Shows correct count | | |

---

## 5. Learning System - Playbooks

### 5.1 Playbook View (Tonality/Language Pattern Agents Only)
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 5.1.1 | Learning tab visible | Tab shows for tonality agent | | |
| 5.1.2 | Learning tab visible | Tab shows for language pattern agent | | |
| 5.1.3 | Learning tab hidden | Tab NOT shown for tech issues agent | | |
| 5.1.4 | Playbook tab loads | Shows current playbook | | |
| 5.1.5 | Default playbook | Initial playbook has default content | | |
| 5.1.6 | Playbook version shown | Shows "v1" or current version | | |

### 5.2 Playbook Editing
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 5.2.1 | Edit button | Switches to edit mode | | |
| 5.2.2 | Textarea appears | Can edit markdown content | | |
| 5.2.3 | Save changes | Changes persist | | |
| 5.2.4 | Cancel edit | Reverts to original | | |
| 5.2.5 | "User edited" badge | Shows after manual edit | | |
| 5.2.6 | Long playbook (10000+ chars) | Saves without truncation | | |

### 5.3 Playbook History
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 5.3.1 | History tab loads | Shows version list | | |
| 5.3.2 | Versions listed | All versions shown with dates | | |
| 5.3.3 | Current version marked | Badge shows which is current | | |
| 5.3.4 | View old version | Can view full content | | |
| 5.3.5 | Restore version | Creates new version from old | | |
| 5.3.6 | Restore confirmation | New version becomes current | | |

---

## 6. Learning System - Brain Prompts

### 6.1 Brain Prompts View
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 6.1.1 | Brains tab loads | Shows both brains | | |
| 6.1.2 | Reflection Brain shown | Card with description | | |
| 6.1.3 | Training Brain shown | Card with description | | |
| 6.1.4 | Default prompts loaded | Shows default for agent type | | |
| 6.1.5 | "Customized" badge | Shows when prompts modified | | |

### 6.2 Brain Prompts Preview
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 6.2.1 | Preview Reflection Brain | Shows full prompt preview | | |
| 6.2.2 | Preview Training Brain | Shows full prompt preview | | |
| 6.2.3 | System prompt shown | Visible in preview | | |
| 6.2.4 | Prefix shown | Custom prefix visible | | |
| 6.2.5 | Dynamic content placeholder | Shows "[Generated...]" | | |
| 6.2.6 | Suffix shown | Custom suffix visible | | |

### 6.3 Brain Prompts Editing
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 6.3.1 | Edit Reflection Brain | Opens edit fields | | |
| 6.3.2 | Edit system prompt | Field editable | | |
| 6.3.3 | Edit prefix | Field editable | | |
| 6.3.4 | Edit suffix | Field editable | | |
| 6.3.5 | Edit Training Brain | Opens edit fields | | |
| 6.3.6 | Custom instructions | Field editable | | |
| 6.3.7 | Save brain prompts | Changes persist | | |
| 6.3.8 | Reset to defaults | Clears custom prompts | | |

---

## 7. Learning System - Configuration

### 7.1 Learning Settings
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 7.1.1 | Settings tab loads | Shows configuration options | | |
| 7.1.2 | Enable/disable toggle | Works, saves state | | |
| 7.1.3 | Mode: Manual | Selectable, saves | | |
| 7.1.4 | Mode: Auto | Selectable, saves | | |
| 7.1.5 | Mode: Every X | Selectable, saves | | |
| 7.1.6 | Trigger count (Every X) | Number input works | | |
| 7.1.7 | Outcomes counter shown | Shows count since last learning | | |

### 7.2 Manual Learning Trigger
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 7.2.1 | "Train Now" button visible | Button shown | | |
| 7.2.2 | Button disabled (< 5 outcomes) | Disabled with message | | |
| 7.2.3 | Click Train Now | Triggers learning | | |
| 7.2.4 | Loading state | Shows "Training..." | | |
| 7.2.5 | Success message | Toast with results | | |
| 7.2.6 | Playbook updated | New version created | | |

### 7.3 Learning Stats
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 7.3.1 | Stats cards display | 4 stat cards shown | | |
| 7.3.2 | Playbook version | Correct number | | |
| 7.3.3 | Prediction accuracy | Shows percentage or N/A | | |
| 7.3.4 | Patterns learned | Shows count | | |
| 7.3.5 | Verified outcomes | Shows count | | |
| 7.3.6 | Stats refresh | Update after learning | | |

---

## 8. Campaigns - CRUD Operations

### 8.1 Create Campaigns
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 8.1.1 | Navigate to Campaigns page | Page loads | | |
| 8.1.2 | Create campaign button | Opens create form | | |
| 8.1.3 | Create with name only | Campaign created | | |
| 8.1.4 | Create with all fields | All fields saved | | |
| 8.1.5 | Campaign appears in list | New campaign visible | | |

### 8.2 Read Campaigns
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 8.2.1 | List all campaigns | All campaigns shown | | |
| 8.2.2 | Campaign details page | Loads without error | | |
| 8.2.3 | Shows call count | Correct count displayed | | |
| 8.2.4 | Shows training call count | Correct count displayed | | |

### 8.3 Update Campaigns
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 8.3.1 | Edit campaign name | Saves changes | | |
| 8.3.2 | Edit description | Saves changes | | |
| 8.3.3 | Update settings | Saves changes | | |

### 8.4 Delete Campaigns
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 8.4.1 | Delete empty campaign | Campaign removed | | |
| 8.4.2 | Delete with training calls | Confirmation shown | | |
| 8.4.3 | Cancel delete | Campaign not deleted | | |

---

## 9. Campaign - QC Agent Assignment

### 9.1 Assign Agents to Campaign
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 9.1.1 | Settings tab loads | Shows agent assignment UI | | |
| 9.1.2 | Tonality agent dropdown | Shows available tonality agents | | |
| 9.1.3 | Assign tonality agent | Saves assignment | | |
| 9.1.4 | Language pattern dropdown | Shows available LP agents | | |
| 9.1.5 | Assign language pattern agent | Saves assignment | | |
| 9.1.6 | Tech issues dropdown | Shows available tech agents | | |
| 9.1.7 | Assign tech issues agent | Saves assignment | | |
| 9.1.8 | Unassign agent | Clears assignment | | |

### 9.2 Auto Analysis Settings
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 9.2.1 | Enable auto analysis | Toggle works | | |
| 9.2.2 | Select agents for auto | Checkboxes work | | |
| 9.2.3 | Save auto settings | Settings persist | | |

---

## 10. Training Calls - Upload & Management

### 10.1 Upload Training Calls
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 10.1.1 | Training Calls tab loads | Shows upload UI | | |
| 10.1.2 | Upload audio file (MP3) | File uploads | | |
| 10.1.3 | Upload audio file (WAV) | File uploads | | |
| 10.1.4 | Set designation on upload | Saves designation | | |
| 10.1.5 | Set tags on upload | Saves tags | | |
| 10.1.6 | Set outcome: Showed | Outcome saved | | |
| 10.1.7 | Set outcome: No Show | Outcome saved | | |
| 10.1.8 | Set outcome: Unknown | Outcome saved (default) | | |
| 10.1.9 | Training call appears in list | New call visible | | |

### 10.2 Training Call List
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 10.2.1 | List displays | All training calls shown | | |
| 10.2.2 | Filename shown | Correct filename | | |
| 10.2.3 | File size shown | Correct size | | |
| 10.2.4 | Designation shown | If set | | |
| 10.2.5 | Outcome buttons visible | Showed/No Show/Unknown | | |
| 10.2.6 | Current outcome highlighted | Correct button highlighted | | |
| 10.2.7 | Processed status | Badge shows status | | |

### 10.3 Delete Training Calls
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 10.3.1 | Delete button visible | Trash icon shown | | |
| 10.3.2 | Delete training call | Call removed from list | | |
| 10.3.3 | Count updates | Campaign count decrements | | |

---

## 11. Training Calls - Outcome Tracking

### 11.1 Set Outcome Before Analysis
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 11.1.1 | Upload with "Showed" | outcome = "showed" saved | | |
| 11.1.2 | Upload with "No Show" | outcome = "no_show" saved | | |
| 11.1.3 | outcome_known_before_analysis | Set to true | | |

### 11.2 Update Outcome After Analysis
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 11.2.1 | Click "Showed" button | Outcome updates to showed | | |
| 11.2.2 | Click "No Show" button | Outcome updates to no_show | | |
| 11.2.3 | Click "Unknown" button | Outcome updates to unknown | | |
| 11.2.4 | Button highlights change | Selected button highlighted | | |
| 11.2.5 | Toast notification | Shows success message | | |
| 11.2.6 | Learning trigger message | Shows if learning triggered | | |

### 11.3 Outcome → Learning Link
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 11.3.1 | Outcome updates analysis log | qc_analysis_logs updated | | |
| 11.3.2 | Prediction accuracy calculated | accuracy field populated | | |
| 11.3.3 | QC agent counter increments | outcomes_since_last_learning++ | | |
| 11.3.4 | Auto mode triggers learning | Learning runs automatically | | |
| 11.3.5 | Every X mode counts | Triggers at threshold | | |

---

## 12. Tech Issues Agent - Analysis & Detection

### 12.1 Tech Issues Agent Setup
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 12.1.1 | Create Tech Issues Agent | Agent created successfully | | |
| 12.1.2 | No Learning tab shown | Learning & Memory tab hidden | | |
| 12.1.3 | Tech-specific rules tab | Shows tech config options | | |
| 12.1.4 | Can configure detection thresholds | Settings save correctly | | |

### 12.2 Tech Issues Detection Types
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 12.2.1 | Audio quality detection | Identifies poor audio quality | | |
| 12.2.2 | Background noise detection | Flags excessive background noise | | |
| 12.2.3 | Echo detection | Identifies echo/feedback | | |
| 12.2.4 | Latency/delay detection | Flags call latency issues | | |
| 12.2.5 | Dropped audio detection | Identifies audio dropouts | | |
| 12.2.6 | Volume issues | Flags too quiet/loud audio | | |
| 12.2.7 | Connection stability | Identifies connection problems | | |

### 12.3 Tech Issues Analysis Output
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 12.3.1 | Issues list returned | Array of detected issues | | |
| 12.3.2 | Severity levels | Each issue has severity | | |
| 12.3.3 | Timestamps | Issues have time markers | | |
| 12.3.4 | Recommendations | Suggestions for fixes | | |
| 12.3.5 | Overall quality score | Summary score provided | | |

### 12.4 Tech Issues - No Learning Verification
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 12.4.1 | GET /brain-prompts returns 400 | "Tech Issues agents don't support learning" | | |
| 12.4.2 | POST /learn returns 400 | "Tech Issues agents don't support learning" | | |
| 12.4.3 | GET /playbook returns 400 | Error or empty | | |
| 12.4.4 | No patterns created | Tech agent has no patterns | | |

### 12.5 Tech Issues in Campaigns
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 12.5.1 | Assign tech agent to campaign | Assignment saves | | |
| 12.5.2 | Run tech analysis on training call | Analysis runs | | |
| 12.5.3 | Tech results stored | Results saved to DB | | |
| 12.5.4 | Outcome tracking NOT linked | No learning trigger | | |

---

## 13. QC Analysis - Tonality & Language Pattern

### 13.1 Analyze Training Call
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 13.1.1 | Select training call | Can select for analysis | | |
| 13.1.2 | Select QC agent | Can choose agent | | |
| 13.1.3 | Run analysis | Analysis runs | | |
| 13.1.4 | Results displayed | Scores, recommendations shown | | |
| 13.1.5 | Predictions shown | show_likelihood visible | | |
| 13.1.6 | Risk factors shown | List of risk factors | | |
| 13.1.7 | Positive signals shown | List of positive signals | | |

### 13.2 Analysis Logging
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 13.2.1 | Analysis log created | Entry in qc_analysis_logs | | |
| 13.2.2 | Campaign ID linked | campaign_id populated | | |
| 13.2.3 | Training call linked | qc_analysis_id on training call | | |
| 13.2.4 | Predictions stored | predictions object saved | | |
| 13.2.5 | is_training_data = true | Flag set correctly | | |

### 13.3 Batch Analysis (Analyze All Calls)
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 13.3.1 | "Analyze All Calls" button visible | Green button in campaign header | | |
| 13.3.2 | Click button (no pending) | Shows "No pending calls" message | | |
| 13.3.3 | Click button (with pending) | Shows "Analysis started" + counts | | |
| 13.3.4 | Loading state | Button shows "Analyzing..." | | |
| 13.3.5 | Progress updates | Results update after delay | | |
| 13.3.6 | Calls get analyzed | script_qc_results populated | | |
| 13.3.7 | Training calls analyzed | qc_analyzed_at set | | |
| 13.3.8 | Force reanalyze option | Re-processes all calls | | |
| 13.3.9 | Background processing | UI remains responsive | | |
| 13.3.10 | Rate limiting | Calls processed with delays | | |

---

## 14. Prediction System & Learning Integration

### 14.1 Script Analysis Predictions
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 14.1.1 | Predictions generated | predictions object in response | | |
| 14.1.2 | show_likelihood field | Float between 0-1 | | |
| 14.1.3 | booking_quality field | STRONG/MEDIUM/WEAK | | |
| 14.1.4 | risk_factors list | Array of identified risks | | |
| 14.1.5 | positive_signals list | Array of positive indicators | | |
| 14.1.6 | confidence score | Float between 0-1 | | |
| 14.1.7 | commitment_strength_score | Float between 0-1 | | |
| 14.1.8 | objection_resolution_score | Float between 0-1 | | |

### 14.2 Tonality Analysis Predictions
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 14.2.1 | Predictions generated | predictions object in response | | |
| 14.2.2 | show_likelihood field | Float between 0-1 | | |
| 14.2.3 | emotional_alignment_score | Float between 0-1 | | |
| 14.2.4 | energy_match_score | Float between 0-1 | | |
| 14.2.5 | risk_factors list | Tonality-specific risks | | |
| 14.2.6 | positive_signals list | Tonality-specific positives | | |

### 14.3 Prediction → Learning System Link
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 14.3.1 | Analysis log with predictions | qc_analysis_logs contains predictions | | |
| 14.3.2 | qc_agent_id linked | Agent ID stored in log | | |
| 14.3.3 | Training call updated | qc_analysis_id set on training call | | |
| 14.3.4 | Campaign ID linked | campaign_id in analysis log | | |
| 14.3.5 | Outcome comparison | Actual vs predicted tracked | | |

### 14.4 Prediction Quality Metrics
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 14.4.1 | High quality → high show_likelihood | Correlation verified | | |
| 14.4.2 | Issues → lower show_likelihood | Penalty applied | | |
| 14.4.3 | Positives → higher show_likelihood | Bonus applied | | |
| 14.4.4 | More data → higher confidence | Confidence scales | | |

---

## 15. Learning Loop - End to End

### 15.1 Full Learning Cycle Test
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 15.1.1 | Create QC Agent (Tonality) | Agent created | | |
| 15.1.2 | Set learning mode: Manual | Setting saved | | |
| 15.1.3 | Create Campaign | Campaign created | | |
| 15.1.4 | Assign QC agent to campaign | Assignment saved | | |
| 15.1.5 | Upload 5+ training calls | Calls uploaded | | |
| 15.1.6 | Set outcomes (mix showed/no show) | Outcomes set | | |
| 15.1.7 | Run QC analysis on each | Analyses complete | | |
| 15.1.8 | Click "Train Now" | Learning runs | | |
| 15.1.9 | Playbook updates | New version created | | |
| 15.1.10 | Patterns identified | Patterns in list | | |
| 15.1.11 | Campaign patterns present | Campaign-specific patterns | | |

### 15.2 Auto Learning Test
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 15.2.1 | Set learning mode: Auto | Setting saved | | |
| 15.2.2 | Upload training call with outcome | Call uploaded | | |
| 15.2.3 | Run analysis | Analysis complete | | |
| 15.2.4 | Update outcome (if unknown) | Outcome updated | | |
| 15.2.5 | Learning auto-triggers | Learning runs automatically | | |
| 15.2.6 | Toast shows "learning triggered" | Notification appears | | |

### 15.3 Every X Learning Test
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 15.3.1 | Set learning mode: Every X (3) | Setting saved | | |
| 15.3.2 | Update 1st outcome | Counter = 1 | | |
| 15.3.3 | Update 2nd outcome | Counter = 2 | | |
| 15.3.4 | Update 3rd outcome | Counter = 3, learning triggers | | |
| 15.3.5 | Counter resets | Counter = 0 after learning | | |

---

## 16. Patterns & Stats

### 16.1 Patterns View
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 16.1.1 | Patterns tab loads | Shows patterns list | | |
| 16.1.2 | Victory patterns section | Green section with patterns | | |
| 16.1.3 | Defeat patterns section | Red section with patterns | | |
| 16.1.4 | Pattern signal shown | Description visible | | |
| 16.1.5 | Pattern impact shown | Percentage visible | | |
| 16.1.6 | Sample size shown | Count visible | | |
| 16.1.7 | Confidence shown | Percentage visible | | |

### 16.2 Pattern Management
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 16.2.1 | Delete pattern | Pattern removed | | |
| 16.2.2 | Pattern count updates | Stats reflect deletion | | |

### 16.3 Learning Sessions History
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 16.3.1 | Sessions list loads | Shows session history | | |
| 16.3.2 | Session type shown | Manual/Auto/Every X | | |
| 16.3.3 | Timestamp shown | Date and time | | |
| 16.3.4 | Analyses count shown | Number reviewed | | |
| 16.3.5 | Patterns identified shown | Count of new patterns | | |
| 16.3.6 | Playbook versions shown | Before → After | | |
| 16.3.7 | Success/failure indicator | Checkmark or X | | |

---

## 17. API Key Management

### 17.1 Service Alias Resolution
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 17.1.1 | 'xai' resolves to 'grok' | Grok key returned | | |
| 17.1.2 | 'x.ai' resolves to 'grok' | Grok key returned | | |
| 17.1.3 | 'gpt' resolves to 'openai' | OpenAI key returned | | |
| 17.1.4 | 'gpt-4' resolves to 'openai' | OpenAI key returned | | |
| 17.1.5 | 'gpt-5' resolves to 'openai' | OpenAI key returned | | |
| 17.1.6 | 'claude' resolves to 'anthropic' | Anthropic key returned | | |
| 17.1.7 | 'google' resolves to 'gemini' | Gemini key returned | | |

### 17.2 Key Pattern Matching
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 17.2.1 | 'xai-' prefix → grok | Detected as Grok key | | |
| 17.2.2 | 'sk-' prefix → openai | Detected as OpenAI key | | |
| 17.2.3 | 'sk-proj-' prefix → openai | Detected as OpenAI key | | |
| 17.2.4 | 'sk-ant-' prefix → anthropic | Detected as Anthropic key | | |
| 17.2.5 | 'AIza' prefix → gemini | Detected as Gemini key | | |
| 17.2.6 | 'sk_' prefix → elevenlabs | Detected as ElevenLabs key | | |

### 17.3 Emergent LLM Key Fallback
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 17.3.1 | No user key, has EMERGENT_LLM_KEY | Fallback used | | |
| 17.3.2 | Works for OpenAI | Text/Image generation works | | |
| 17.3.3 | Works for Anthropic | Text generation works | | |
| 17.3.4 | Works for Gemini | Text generation works | | |
| 17.3.5 | Works for Grok | Text generation works | | |

### 17.4 Key Retrieval Logging
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 17.4.1 | Pattern match logged | Log shows match type | | |
| 17.4.2 | Fallback logged | Log shows "Using Emergent LLM key" | | |
| 17.4.3 | Not found logged | Warning logged with user ID | | |

---

## 18. Edge Cases & Error Handling

### 18.1 Empty States
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 18.1.1 | No QC agents | Empty state message | | |
| 18.1.2 | No campaigns | Empty state message | | |
| 18.1.3 | No training calls | Empty state message | | |
| 18.1.4 | No patterns | Empty state message | | |
| 18.1.5 | No playbook history | Empty state message | | |
| 18.1.6 | No learning sessions | Empty state message | | |

### 18.2 Validation Errors
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 18.2.1 | Create agent without name | Error message | | |
| 18.2.2 | Create campaign without name | Error message | | |
| 18.2.3 | Invalid outcome value | Error/ignored | | |
| 18.2.4 | Upload invalid file type | Error message | | |
| 18.2.5 | Learning with < 5 outcomes | Disabled + message | | |

### 18.3 Permission Errors
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 18.3.1 | Access other user's agent | 404 error | | |
| 18.3.2 | Access other user's campaign | 404 error | | |
| 18.3.3 | Unauthenticated API call | 401 error | | |

### 18.4 API Failures
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 18.4.1 | LLM API timeout | Graceful error | | |
| 18.4.2 | LLM API error | Error message shown | | |
| 18.4.3 | Database error | Error handled | | |

### 16.5 Tech Issues Agent Edge Cases
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 16.5.1 | No Learning tab | Tab hidden for tech agent | | |
| 16.5.2 | Learning API returns error | 400 error for tech agent | | |
| 16.5.3 | Brain prompts API returns error | 400 error for tech agent | | |

---

### 18.5 Tech Issues Agent Edge Cases
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 18.5.1 | No Learning tab | Tab hidden for tech agent | | |
| 18.5.2 | Learning API returns error | 400 error for tech agent | | |
| 18.5.3 | Brain prompts API returns error | 400 error for tech agent | | |

---

## 19. Stress Tests

### 19.1 Volume Tests
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 19.1.1 | Create 50 QC agents | All created, list loads | | |
| 19.1.2 | Create 20 campaigns | All created, list loads | | |
| 19.1.3 | Upload 100 training calls | All uploaded | | |
| 19.1.4 | 500+ analysis logs | Learning still works | | |
| 19.1.5 | Long playbook (50KB) | Saves and loads | | |

### 19.2 Concurrent Operations
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 19.2.1 | Rapid outcome updates | All save correctly | | |
| 19.2.2 | Multiple learning triggers | Handled gracefully | | |
| 19.2.3 | Edit while learning runs | No corruption | | |
| 19.2.4 | Batch analysis + manual analysis | Both complete | | |

### 19.3 Data Integrity
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 19.3.1 | Delete agent with assignments | Assignments cleaned up | | |
| 19.3.2 | Delete campaign with training calls | Calls orphaned/deleted | | |
| 19.3.3 | Playbook version sequence | Versions increment correctly | | |
| 19.3.4 | Pattern deduplication | No duplicate patterns | | |

---

## 20. UI/UX Verification

### 20.1 Navigation
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 20.1.1 | QC Agents link works | Navigates correctly | | |
| 20.1.2 | Campaigns link works | Navigates correctly | | |
| 20.1.3 | Back navigation | Returns to previous page | | |
| 20.1.4 | Breadcrumbs (if any) | Show correct path | | |

### 20.2 Loading States
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 20.2.1 | Agent list loading | Shows spinner/skeleton | | |
| 20.2.2 | Campaign details loading | Shows spinner/skeleton | | |
| 20.2.3 | Playbook loading | Shows spinner | | |
| 20.2.4 | Learning in progress | Shows "Training..." | | |
| 20.2.5 | Batch analysis in progress | Shows "Analyzing..." | | |

### 20.3 Toast Notifications
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 20.3.1 | Success toast | Green/success styling | | |
| 20.3.2 | Error toast | Red/destructive styling | | |
| 20.3.3 | Toast dismisses | Auto-dismisses or clickable | | |
| 20.3.4 | Batch analysis started toast | Shows queued counts | | |

### 20.4 Responsive Design
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 20.4.1 | Desktop view | Layout correct | | |
| 20.4.2 | Tablet view | Layout adapts | | |
| 20.4.3 | Mobile view | Layout adapts | | |

### 20.5 Dark Mode (if applicable)
| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 20.5.1 | All components themed | Consistent dark theme | | |
| 20.5.2 | Text readable | Good contrast | | |
| 20.5.3 | Badges visible | Clear visibility | | |

---

## Test Summary

| Section | Total Tests | Passed | Failed | Skipped |
|---------|-------------|--------|--------|---------|
| 1. Pre-Flight | 9 | | | |
| 2. QC Agents CRUD | 16 | | | |
| 3. Agent Config | 17 | | | |
| 4. Knowledge Base | 10 | | | |
| 5. Playbooks | 17 | | | |
| 6. Brain Prompts | 16 | | | |
| 7. Learning Config | 13 | | | |
| 8. Campaigns CRUD | 12 | | | |
| 9. Agent Assignment | 10 | | | |
| 10. Training Calls | 14 | | | |
| 11. Outcome Tracking | 11 | | | |
| 12. Tech Issues Agent | 20 | | | |
| 13. QC Analysis (Tonality/LP) | 20 | | | |
| 14. Prediction System | 22 | | | |
| 15. Learning Loop E2E | 22 | | | |
| 16. Patterns & Stats | 16 | | | |
| 17. API Key Management | 20 | | | |
| 18. Edge Cases | 17 | | | |
| 19. Stress Tests | 13 | | | |
| 20. UI/UX | 19 | | | |
| **TOTAL** | **314** | | | |

---

## Issues Found

| # | Section | Test # | Description | Severity | Status |
|---|---------|--------|-------------|----------|--------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | | | |
| Developer | | | |
| Product Owner | | | |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Nov 2025 | Initial checklist creation |
| 2.0 | Nov 29, 2025 | Added: Section 14 (Prediction System), Section 17 (API Key Management), Batch Analysis tests, Tech Issues edge cases, Updated test counts (224 → 314) |

---

*Generated for QC Intelligence System v2.0*
