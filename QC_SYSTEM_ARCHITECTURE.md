# QC Intelligence System - Complete Architecture & Workflow Guide

> **Version**: 2.0  
> **Last Updated**: November 2025  
> **Status**: Production Ready

---

## Table of Contents

1. [System Overview](#system-overview)
2. [QC Agent Types](#qc-agent-types)
3. [Campaign Integration](#campaign-integration)
4. [Learning & Memory Architecture](#learning--memory-architecture)
5. [Brain System](#brain-system)
6. [Playbook System](#playbook-system)
7. [Database Schema](#database-schema)
8. [API Reference](#api-reference)
9. [Workflows](#workflows)
10. [Customization Guide](#customization-guide)
11. [UI Components](#ui-components)

---

## System Overview

The QC Intelligence System is an AI-powered quality control platform for analyzing sales calls. It features:

- **Multiple QC Agent Types**: Specialized agents for different analysis focuses
- **Learning System**: Agents improve over time based on appointment outcomes
- **Memory Architecture**: Multi-layered memory system inspired by combat AI learning
- **Customizable Brains**: Transparent, editable prompts for the learning AI
- **Campaign Integration**: Patterns learned per campaign context
- **CRM Integration**: Triggers re-analysis when appointment outcomes change

```
┌─────────────────────────────────────────────────────────────────────┐
│                        QC INTELLIGENCE SYSTEM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐            │
│  │   Tonality   │   │   Language   │   │    Tech      │            │
│  │    Agent     │   │   Pattern    │   │   Issues     │            │
│  │              │   │    Agent     │   │    Agent     │            │
│  └──────┬───────┘   └──────┬───────┘   └──────────────┘            │
│         │                  │                                        │
│         └────────┬─────────┘                                        │
│                  │                                                   │
│         ┌───────▼────────┐                                          │
│         │ Learning System │◄──── Appointment Outcomes               │
│         └───────┬────────┘                                          │
│                 │                                                    │
│    ┌────────────┼────────────┐                                      │
│    │            │            │                                      │
│    ▼            ▼            ▼                                      │
│ ┌──────┐  ┌──────────┐  ┌──────────┐                               │
│ │Memory│  │ Patterns │  │ Playbook │                               │
│ │ Logs │  │          │  │          │                               │
│ └──────┘  └──────────┘  └──────────┘                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## QC Agent Types

### 1. Tonality Agent 🎤

**Purpose**: Analyzes voice quality and emotional delivery

**Focus Areas**:
- Vocal warmth and energy levels
- Emotional resonance and pacing
- Confidence signals in voice
- Energy matching with customer
- Tone shifts during objections and close

**Supports Learning**: ✅ Yes

**Default Analysis Criteria**:
```
- Opening warmth (1-10)
- Energy matching score
- Emotional close strength
- Confidence level during objections
- Pacing consistency
```

---

### 2. Language Pattern Agent 📝

**Purpose**: Analyzes conversation tactics and script quality

**Focus Areas**:
- Commitment language strength
- Objection handling techniques
- Confirmation step completeness
- Closing technique effectiveness
- Script adherence

**Supports Learning**: ✅ Yes

**Default Analysis Criteria**:
```
- Time/date confirmation present
- Objection resolution completeness
- Commitment strength ("I will" vs "I'll try")
- Value proposition recap
- Close technique used
```

---

### 3. Tech Issues Agent 🔧

**Purpose**: Identifies technical problems in calls

**Focus Areas**:
- Audio quality issues
- Connection problems
- Background noise
- Latency/lag
- Recording quality

**Supports Learning**: ❌ No (diagnostic only)

---

## Campaign Integration

Campaigns are the central hub that connects calls, QC agents, training data, and learning.

### Campaign ↔ QC System Relationship

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAMPAIGN INTEGRATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           CAMPAIGN                                   │   │
│  │  • Name, Description                                                 │   │
│  │  • Target Audience                                                   │   │
│  │  • Assigned QC Agents                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│           ┌────────────────────────┼────────────────────────┐               │
│           │                        │                        │               │
│           ▼                        ▼                        ▼               │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │  LIVE CALLS     │    │ TRAINING CALLS  │    │ QC AGENTS       │        │
│  │                 │    │                 │    │                 │        │
│  │ • From agents   │    │ • Uploaded      │    │ • Tonality      │        │
│  │ • Auto-analyzed │    │ • Known outcome │    │ • Lang Pattern  │        │
│  │ • Outcome TBD   │    │ • Historical    │    │ • Tech Issues   │        │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘        │
│           │                      │                      │                   │
│           └──────────────────────┼──────────────────────┘                   │
│                                  │                                          │
│                                  ▼                                          │
│                    ┌─────────────────────────┐                              │
│                    │    QC ANALYSIS LOGS     │                              │
│                    │                         │                              │
│                    │ • Predictions           │                              │
│                    │ • Scores                │                              │
│                    │ • Campaign context      │                              │
│                    └────────────┬────────────┘                              │
│                                 │                                           │
│                                 │ Outcome Updated                           │
│                                 ▼                                           │
│                    ┌─────────────────────────┐                              │
│                    │    LEARNING SYSTEM      │                              │
│                    │                         │                              │
│                    │ • Global patterns       │                              │
│                    │ • CAMPAIGN patterns     │◄─── Scoped to this campaign │
│                    │ • Playbook updates      │                              │
│                    └─────────────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Campaign Data Model

```javascript
{
  id: "campaign-uuid",
  name: "Solar Sales Q4 2025",
  description: "Residential solar panel sales campaign",
  user_id: "user-uuid",
  
  // QC Agent Assignments
  agent_assignments: {
    tonality_agent_id: "qc-agent-uuid",
    language_pattern_agent_id: "qc-agent-uuid",
    tech_issues_agent_id: "qc-agent-uuid"
  },
  
  // Auto QC Settings
  auto_analysis_settings: {
    enabled: true,
    analyze_on_call_complete: true,
    qc_agents: ["tonality", "language_pattern"]
  },
  
  // Call Counts
  total_calls: 150,
  total_training_calls: 25,
  
  // Campaign-specific prompts/context
  campaign_context: "Residential solar sales to homeowners...",
  
  created_at: datetime
}
```

### Training Calls in Campaigns

Training calls are historical recordings uploaded to a campaign where **you already know the outcome**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRAINING CALL FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1: Upload Training Call                                               │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  POST /api/qc/enhanced/campaigns/{id}/training-calls               │    │
│  │                                                                     │    │
│  │  Body:                                                              │    │
│  │  - file: audio_recording.mp3                                       │    │
│  │  - designation: "First Touch" (optional)                           │    │
│  │  - tags: "high-value, solar" (optional)                            │    │
│  │  - outcome: "showed" | "no_show" | "unknown"  ◄── SET BEFOREHAND   │    │
│  │  - outcome_notes: "Customer mentioned price concerns"              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  STEP 2: Run QC Analysis                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  QC Agent analyzes the training call                               │    │
│  │                                                                     │    │
│  │  If outcome was set:                                               │    │
│  │  → AI KNOWS the result during analysis                             │    │
│  │  → Can immediately identify patterns                               │    │
│  │                                                                     │    │
│  │  Output:                                                            │    │
│  │  - predictions: { show_likelihood: 0.72, risk_factors: [...] }    │    │
│  │  - scores: { warmth: 8, confidence: 7, ... }                       │    │
│  │  - recommendations: [...]                                          │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  STEP 3: Update Outcome (if not set before)                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  PUT /api/qc/enhanced/campaigns/{id}/training-calls/{call}/outcome │    │
│  │                                                                     │    │
│  │  Body:                                                              │    │
│  │  - outcome: "showed" | "no_show"                                   │    │
│  │  - outcome_notes: "Customer attended, bought premium package"      │    │
│  │  - trigger_learning: true                                          │    │
│  │                                                                     │    │
│  │  This automatically:                                               │    │
│  │  1. Updates linked QC analysis log                                 │    │
│  │  2. Calculates prediction accuracy                                 │    │
│  │  3. Triggers learning (if enabled)                                 │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  STEP 4: Learning Triggered                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Reflection Brain analyzes:                                        │    │
│  │  - This training call + all others with outcomes                   │    │
│  │  - Identifies campaign-specific patterns                           │    │
│  │                                                                     │    │
│  │  Training Brain generates:                                         │    │
│  │  - Updated playbook with campaign patterns                         │    │
│  │                                                                     │    │
│  │  Playbook now includes:                                            │    │
│  │  ## CAMPAIGN-SPECIFIC: Solar Sales Q4                              │    │
│  │  - Price objection → use ROI frame (+18% show rate)               │    │
│  │  - Mention "spouse" → confirm both will attend                     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Training Call Data Model

```javascript
{
  id: "training-call-uuid",
  campaign_id: "campaign-uuid",
  user_id: "user-uuid",
  
  // File info
  filename: "call_2025_01_15.mp3",
  file_size: 2048576,
  
  // Classification
  designation: "First Touch",  // "First Touch", "Follow-up", "No-Show Call"
  tags: ["high-value", "price-objection"],
  
  // Transcript (extracted from audio)
  transcript: [...],
  duration: 342,  // seconds
  
  // OUTCOME TRACKING
  outcome: "showed" | "no_show" | "unknown",
  outcome_notes: "Customer mentioned they almost cancelled",
  outcome_set_at: "2025-01-15T10:30:00Z",
  outcome_known_before_analysis: true,  // Was outcome set BEFORE QC ran?
  
  // QC Analysis Linkage
  qc_analysis_id: "analysis-uuid",  // Links to qc_analysis_logs
  qc_analyzed_at: "2025-01-15T11:00:00Z",
  
  processed: true,
  created_at: "2025-01-15T09:00:00Z"
}
```

### Campaign-Specific Patterns

When the learning system runs, it identifies patterns that are **specific to a campaign**:

```markdown
## Playbook Section: CAMPAIGN-SPECIFIC PATTERNS

### Campaign: Solar Sales Q4 2025
Context: Residential solar panel sales to homeowners

Victory Patterns (this campaign):
- "ROI calculation discussed" → +22% show rate
- "Both spouses confirmed" → +35% show rate
- "Installation timeline mentioned" → +15% show rate

Defeat Patterns (this campaign):
- "Price quoted without context" → +28% no-show rate
- "Only one decision-maker on call" → +20% no-show rate
- "No follow-up call scheduled" → +25% no-show rate

### Campaign: Medicare Enrollment 2025
Context: Medicare supplement insurance sales

Victory Patterns (this campaign):
- "Current coverage reviewed" → +18% show rate
- "Appointment reminder set" → +30% show rate

Defeat Patterns (this campaign):
- "Benefits not personalized" → +22% no-show rate
```

### How Campaigns Feed the Learning Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CAMPAIGN → LEARNING INTEGRATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   CAMPAIGNS                         QC AGENTS                               │
│   ─────────                         ─────────                               │
│   ┌──────────────┐                 ┌──────────────┐                        │
│   │ Campaign A   │──assigns───────►│ Tonality     │                        │
│   │ (Solar)      │                 │ Agent        │                        │
│   │              │──assigns───────►│              │                        │
│   └──────────────┘                 └──────┬───────┘                        │
│   ┌──────────────┐                        │                                 │
│   │ Campaign B   │──assigns───────────────┤                                 │
│   │ (Medicare)   │                        │                                 │
│   └──────────────┘                        │                                 │
│                                           ▼                                 │
│                               ┌────────────────────┐                        │
│                               │  LEARNING SYSTEM   │                        │
│                               │                    │                        │
│                               │  Patterns stored:  │                        │
│                               │  - Global          │                        │
│                               │  - Campaign A      │                        │
│                               │  - Campaign B      │                        │
│                               └────────────────────┘                        │
│                                           │                                 │
│                                           ▼                                 │
│                               ┌────────────────────┐                        │
│                               │     PLAYBOOK       │                        │
│                               │                    │                        │
│                               │ Contains:          │                        │
│                               │ - Global patterns  │                        │
│                               │ - Campaign A sect  │                        │
│                               │ - Campaign B sect  │                        │
│                               └────────────────────┘                        │
│                                                                              │
│   When analyzing a call from Campaign A:                                    │
│   → Playbook includes Campaign A specific patterns                          │
│   → Global patterns also apply                                              │
│   → Campaign B patterns NOT included (different context)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Points: Campaigns & Learning

| Aspect | How It Works |
|--------|--------------|
| **Agent Assignment** | Each campaign can assign specific QC agents for analysis |
| **Training Calls** | Uploaded to campaigns with known outcomes to seed learning |
| **Pattern Scope** | Patterns are tagged with `campaign_id` for campaign-specific learning |
| **Playbook Injection** | When analyzing, playbook includes relevant campaign patterns |
| **Cross-Campaign** | Same QC agent can learn from multiple campaigns, patterns stay scoped |
| **Outcome Source** | Training calls → manual outcome setting → triggers learning |

---

## Learning & Memory Architecture

Inspired by combat AI learning systems, the QC agents use a multi-layered memory architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ACTIVE MEMORY (Injected into every analysis)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    QC PLAYBOOK                           │   │
│  │  • Victory patterns (what predicts "showed")             │   │
│  │  • Defeat patterns (what predicts "no-show")             │   │
│  │  • Pre-analysis checklist                                │   │
│  │  • Scoring calibration                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ▲                                     │
│                            │ Generated by                        │
│                            │                                     │
│  DEEP MEMORY (Analytical findings)                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  LEARNED PATTERNS                        │   │
│  │  • Transferable principles (work everywhere)             │   │
│  │  • Campaign-specific patterns                            │   │
│  │  • Agent-specific patterns                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ▲                                     │
│                            │ Identified from                     │
│                            │                                     │
│  RAW EXPERIENCE (All analysis data)                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  ANALYSIS LOGS                           │   │
│  │  • Every QC analysis with predictions                    │   │
│  │  • Linked to appointment outcomes                        │   │
│  │  • Accuracy tracking                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Learning Loop

```
┌──────────────────────────────────────────────────────────────────┐
│                      THE LEARNING LOOP                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   1. EXPERIENCE                    2. REFLECTION                  │
│   ┌────────────────┐               ┌────────────────┐            │
│   │ QC Analysis    │               │ Reflection     │            │
│   │ runs on call   │───────────────│ Brain analyzes │            │
│   │                │  Outcome      │ outcomes vs    │            │
│   │ Predictions:   │  Known        │ predictions    │            │
│   │ • Show: 72%    │◄──────────────│                │            │
│   │ • Risks: [...]│               │ Identifies:    │            │
│   └────────────────┘               │ • Patterns     │            │
│                                    │ • Errors       │            │
│                                    └───────┬────────┘            │
│                                            │                      │
│   4. APPLICATION                   3. INSTRUCTION                 │
│   ┌────────────────┐               ┌───────▼────────┐            │
│   │ Next Analysis  │               │ Training Brain │            │
│   │ uses updated   │◄──────────────│ generates new  │            │
│   │ playbook       │               │ playbook       │            │
│   │                │               │                │            │
│   │ More accurate! │               │ Synthesizes    │            │
│   └────────────────┘               │ lessons        │            │
│                                    └────────────────┘            │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Brain System

The learning system uses two specialized AI "brains":

### Reflection Brain 🧠

**Purpose**: Analyzes QC results against actual outcomes to identify patterns

**Triggered By**: 
- Appointment outcome recorded (showed/no-show)
- Manual learning trigger
- Scheduled learning (every X outcomes)

**Inputs**:
- Analysis logs with predictions
- Known appointment outcomes
- Existing patterns

**Outputs**:
- Victory patterns (correlate with "showed")
- Defeat patterns (correlate with "no-show")
- Campaign-specific patterns
- Calibration adjustments

**Customizable Prompts**:
```
┌─────────────────────────────────────────────────────────────┐
│ REFLECTION BRAIN PROMPT STRUCTURE                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [System Prompt]                                             │
│  "You are an expert QC analyst specializing in..."          │
│                                                              │
│  [Custom Prefix]           ◄── Your custom instructions     │
│  "Focus on these specific patterns..."                      │
│                                                              │
│  [Dynamic Content]         ◄── Auto-generated               │
│  • Current accuracy stats                                   │
│  • Showed examples                                          │
│  • No-show examples                                         │
│  • Existing patterns                                        │
│  • Analysis task                                            │
│                                                              │
│  [Custom Suffix]           ◄── Your custom instructions     │
│  "Prioritize patterns related to..."                        │
│                                                              │
│  [Custom Instructions]     ◄── Applied to both brains       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Training Brain 🎓

**Purpose**: Synthesizes patterns into actionable playbooks

**Triggered By**: After Reflection Brain completes

**Inputs**:
- All learned patterns
- Current playbook
- Accuracy data

**Outputs**:
- Updated playbook with:
  - Philosophy section
  - Pre-analysis checklist
  - Victory/defeat patterns
  - Campaign-specific guidance
  - Anti-patterns (mistakes to avoid)
  - Scoring calibration

**Customizable Prompts**: Same structure as Reflection Brain

---

## Playbook System

### Playbook Structure

```markdown
# QC Playbook v{version}
Agent Type: {tonality/language_pattern}
Training Data: {N} analyses, {M} verified outcomes
Historical Accuracy: {X}%

## 1. CORE PHILOSOPHY
[How to approach analysis - 2-3 sentences]

## 2. PRE-ANALYSIS CHECKLIST
□ Check item 1
□ Check item 2
□ Check item 3

## 3. VICTORY PATTERNS (Predict "Showed")
- Pattern 1: +15% show rate
- Pattern 2: +12% show rate

## 4. DEFEAT PATTERNS (Predict "No-Show")
- Pattern 1: +20% no-show rate
- Pattern 2: +18% no-show rate

## 5. CAMPAIGN-SPECIFIC PATTERNS
### Campaign: {name}
- Specific pattern for this campaign

## 6. COMMON MISTAKES (Anti-Patterns)
- DON'T do this
- DON'T do that

## 7. SCORING CALIBRATION
- Base show likelihood: 50%
- Adjust UP when: [conditions]
- Adjust DOWN when: [conditions]
```

### Playbook Versioning

- Every learning session creates a new version
- Full history preserved
- Any version can be restored
- Manual edits tracked separately

---

## Database Schema

### Collections

```javascript
// QC Agents
qc_agents: {
  id: String,
  user_id: String,
  name: String,
  description: String,
  agent_type: "tonality" | "language_pattern" | "tech_issues",
  
  // LLM Config
  llm_provider: String,  // "grok", "openai", etc.
  llm_model: String,
  
  // Analysis Config
  system_prompt: String,
  analysis_focus: String,
  custom_criteria: String,
  output_format_instructions: String,
  
  // Learning Config
  learning_config: {
    mode: "manual" | "auto" | "every_x",
    trigger_count: Number,
    is_enabled: Boolean,
    outcomes_since_last_learning: Number,
    total_learning_sessions: Number,
    last_learning_at: DateTime
  },
  
  // Brain Prompts (custom overrides)
  brain_prompts: {
    reflection_system_prompt: String,
    reflection_prefix: String,
    reflection_suffix: String,
    training_system_prompt: String,
    training_prefix: String,
    training_suffix: String,
    custom_instructions: String
  },
  
  // Knowledge Base
  kb_items: [String],  // KB item IDs
  
  created_at: DateTime,
  updated_at: DateTime
}

// QC Playbooks (Active Memory)
qc_playbooks: {
  id: String,
  qc_agent_id: String,
  user_id: String,
  agent_type: String,
  
  version: Number,
  is_current: Boolean,
  
  content: {
    philosophy: String,
    pre_analysis_checklist: [String],
    victory_patterns: [{signal, impact, description}],
    defeat_patterns: [{signal, impact, description}],
    campaign_patterns: {campaign_id: [patterns]},
    anti_patterns: [String],
    scoring_calibration: Object,
    raw_markdown: String
  },
  
  // Stats
  training_data_count: Number,
  verified_outcomes_count: Number,
  prediction_accuracy: Number,
  patterns_count: Number,
  
  // Edit tracking
  is_auto_generated: Boolean,
  user_edited: Boolean,
  last_edited_by: "system" | "user",
  
  created_at: DateTime,
  updated_at: DateTime
}

// QC Analysis Logs (Raw Experience)
qc_analysis_logs: {
  id: String,
  qc_agent_id: String,
  qc_agent_type: String,
  user_id: String,
  
  // What was analyzed
  call_id: String,
  campaign_id: String,
  lead_id: String,
  call_agent_id: String,
  
  // Analysis output
  analysis_content: Object,
  scores: Object,
  recommendations: [String],
  
  // PREDICTIONS (critical for learning)
  predictions: {
    show_likelihood: Number,  // 0-1
    booking_quality: "strong" | "medium" | "weak",
    risk_factors: [String],
    positive_signals: [String],
    confidence: Number
  },
  
  // POST-OUTCOME (filled when known)
  actual_outcome: "showed" | "no_show" | "rescheduled" | "cancelled" | "pending",
  outcome_updated_at: DateTime,
  prediction_accuracy: Number,
  missed_signals: [String],
  correct_signals: [String],
  
  // Flags
  is_training_data: Boolean,
  has_been_reviewed: Boolean,
  
  analyzed_at: DateTime
}

// Learned Patterns (Deep Memory)
qc_patterns: {
  id: String,
  qc_agent_id: String,
  user_id: String,
  
  pattern_type: "victory" | "defeat" | "campaign_specific" | "transferable",
  agent_type: String,
  
  // Scope
  scope: "global" | "campaign:{id}" | "call_agent:{id}",
  campaign_id: String,
  
  // The pattern
  signal: String,
  description: String,
  
  // Statistical backing
  correlation: Number,  // -1 to 1
  confidence: Number,   // 0 to 1
  sample_size: Number,
  
  // Impact
  outcome_impact: "showed" | "no_show",
  impact_percentage: Number,
  
  is_active: Boolean,
  discovered_at: DateTime
}

// Learning Sessions
qc_learning_sessions: {
  id: String,
  qc_agent_id: String,
  user_id: String,
  agent_type: String,
  
  session_type: "reflection" | "lesson_generation" | "full",
  trigger: "auto" | "every_x" | "manual",
  
  // Inputs
  analyses_reviewed_count: Number,
  analyses_reviewed_ids: [String],
  outcomes_included: {showed: Number, no_show: Number},
  
  // Outputs
  patterns_identified: Number,
  new_patterns: [String],
  playbook_version_before: Number,
  playbook_version_after: Number,
  playbook_diff_summary: String,
  
  // Results
  success: Boolean,
  error_message: String,
  accuracy_before: Number,
  accuracy_after: Number,
  
  started_at: DateTime,
  completed_at: DateTime,
  duration_seconds: Number
}
```

---

## API Reference

### QC Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/qc/agents` | List all QC agents |
| POST | `/api/qc/agents` | Create QC agent |
| GET | `/api/qc/agents/{id}` | Get agent details |
| PUT | `/api/qc/agents/{id}` | Update agent |
| DELETE | `/api/qc/agents/{id}` | Delete agent |

### Learning & Memory

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/qc/learning/agents/{id}/playbook` | Get current playbook |
| PUT | `/api/qc/learning/agents/{id}/playbook` | Update playbook |
| GET | `/api/qc/learning/agents/{id}/playbook/history` | Get version history |
| POST | `/api/qc/learning/agents/{id}/playbook/restore/{v}` | Restore version |
| GET | `/api/qc/learning/agents/{id}/config` | Get learning config |
| PUT | `/api/qc/learning/agents/{id}/config` | Update learning config |
| POST | `/api/qc/learning/agents/{id}/learn` | Trigger learning |
| GET | `/api/qc/learning/agents/{id}/stats` | Get learning stats |

### Brain Prompts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/qc/learning/agents/{id}/brain-prompts` | Get brain prompts |
| PUT | `/api/qc/learning/agents/{id}/brain-prompts` | Update prompts |
| POST | `/api/qc/learning/agents/{id}/brain-prompts/preview` | Preview full prompt |

### Analysis Logs & Patterns

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/qc/learning/agents/{id}/analysis-logs` | Get analysis logs |
| PUT | `/api/qc/learning/agents/{id}/analysis-logs/{log}/outcome` | Update outcome |
| GET | `/api/qc/learning/agents/{id}/patterns` | Get learned patterns |
| DELETE | `/api/qc/learning/agents/{id}/patterns/{pattern}` | Delete pattern |
| GET | `/api/qc/learning/agents/{id}/sessions` | Get learning sessions |

### Training Calls

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/qc/enhanced/campaigns/{id}/training-calls` | Upload training call (with optional outcome) |
| GET | `/api/qc/enhanced/campaigns/{id}/training-calls` | List training calls |
| GET | `/api/qc/enhanced/campaigns/{id}/training-calls/{call_id}` | Get training call details |
| PUT | `/api/qc/enhanced/campaigns/{id}/training-calls/{call_id}/outcome` | Update outcome (triggers learning) |
| DELETE | `/api/qc/enhanced/campaigns/{id}/training-calls/{call_id}` | Delete training call |

---

## Workflows

### Workflow 1: Creating a New QC Agent

```
1. Navigate to QC Agents page
2. Click "Create New Agent"
3. Select agent type:
   - Tonality (voice analysis)
   - Language Pattern (tactics analysis)
   - Tech Issues (diagnostic only)
4. Configure:
   - Name and description
   - LLM provider and model
   - System prompt (or use default)
   - Analysis focus
   - Custom criteria
5. Save agent
6. Initial playbook auto-created (defaults)
```

### Workflow 2: Running QC Analysis

```
1. Call completes and recording available
2. Select QC agent for analysis
3. Agent runs analysis with:
   - Current playbook injected as context
   - Custom prompts/criteria applied
4. Analysis generates:
   - Scores
   - Recommendations
   - PREDICTIONS (show_likelihood, risk_factors, etc.)
5. Results saved to qc_analysis_logs
6. Linked to campaign/lead if applicable
```

### Workflow 3: Learning from Outcomes

```
TRIGGER: Appointment outcome recorded (showed/no-show)

1. Analysis log updated with actual_outcome
2. Prediction accuracy calculated
3. Check learning mode:
   
   AUTO MODE:
   └─► Immediately trigger learning session
   
   EVERY_X MODE:
   └─► Increment counter
       └─► If counter >= threshold, trigger learning
   
   MANUAL MODE:
   └─► No automatic action

4. LEARNING SESSION:
   a. Reflection Brain analyzes:
      - All logs with outcomes
      - Identifies patterns
      - Calculates accuracy
   
   b. Training Brain generates:
      - New playbook version
      - Updated patterns
      - Calibration adjustments

5. New playbook becomes active
6. Old playbook archived
7. Agent is now "smarter"
```

### Workflow 4: Training Calls with Known Outcomes

Training calls are audio files you upload where you ALREADY KNOW the outcome.
This is perfect for seeding the learning system with historical data.

```
OPTION A: Set Outcome BEFORE Analysis
─────────────────────────────────────
1. Navigate to Campaign → Training Calls tab
2. Upload training call audio file
3. Set outcome during upload:
   - Showed (customer attended)
   - No Show (customer didn't attend)
   - Unknown (outcome not known)
4. Run QC analysis on the call
5. AI KNOWS the outcome during analysis
   → Can learn immediately what patterns led to this outcome

OPTION B: Set/Update Outcome AFTER Analysis
───────────────────────────────────────────
1. Upload training call (outcome unknown initially)
2. Run QC analysis
3. Later, update the outcome:
   - Click "Showed" / "No Show" / "Unknown" button
4. System automatically:
   - Updates the linked analysis log
   - Calculates prediction accuracy
   - Triggers learning if enabled
   → Agent learns from its prediction error

TRAINING CALL DATA MODEL:
{
  "id": "uuid",
  "filename": "call_recording.mp3",
  "outcome": "showed" | "no_show" | "unknown",
  "outcome_notes": "Customer mentioned they almost cancelled",
  "outcome_set_at": "2025-01-15T10:30:00Z",
  "outcome_known_before_analysis": true,
  "qc_analysis_id": "linked-analysis-uuid"
}
```

### Workflow 5: Customizing Brain Prompts

```
1. Navigate to QC Agent → Learning & Memory → Brains tab
2. View current prompts:
   - Click "Preview" to see full prompt
3. Customize:
   - Edit System Prompt (personality/role)
   - Edit Prefix (added before dynamic content)
   - Edit Suffix (added after dynamic content)
   - Add Custom Instructions (apply to both brains)
4. Save changes
5. Next learning session uses custom prompts
```

### Workflow 6: Manual Playbook Editing

```
1. Navigate to QC Agent → Learning & Memory → Playbook tab
2. Click "Edit Playbook"
3. Modify markdown content:
   - Add custom patterns
   - Adjust calibration
   - Add campaign-specific notes
4. Save changes
5. Playbook marked as "user edited"
6. Can restore previous versions if needed
```

---

## Customization Guide

### Customizing QC Analysis Behavior

**1. System Prompt**
```
Location: QC Agent Editor → Prompt & Instructions tab
Purpose: Core instructions for how the agent should analyze calls
```

**2. Analysis Focus**
```
Location: QC Agent Editor → Prompt & Instructions tab
Purpose: Specific areas to prioritize in analysis
Example: "Focus on how objections are handled and commitment language"
```

**3. Custom Criteria**
```
Location: QC Agent Editor → Prompt & Instructions tab
Purpose: Specific scoring rubrics or evaluation criteria
Example: "Rate warmth 1-10, Rate confidence 1-10"
```

**4. Output Format Instructions**
```
Location: QC Agent Editor → Prompt & Instructions tab
Purpose: How the analysis should be formatted
Example: "Return JSON with scores, recommendations, and risk_factors"
```

### Customizing Learning Behavior

**1. Learning Mode**
```
Location: QC Agent → Learning & Memory → Learning Settings
Options:
- Manual: Only learn when you click "Train"
- Auto: Learn after every appointment outcome
- Every X: Learn after X outcomes recorded
```

**2. Brain Prompts**
```
Location: QC Agent → Learning & Memory → Brains tab

Reflection Brain customizations:
- System prompt: Change the brain's "personality"
- Prefix: Add instructions before analysis data
- Suffix: Add instructions after analysis data

Training Brain customizations:
- System prompt: Change how playbooks are generated
- Prefix/Suffix: Guide playbook structure
```

**3. Custom Instructions**
```
Location: QC Agent → Learning & Memory → Brains tab
Applied to: Both brains
Example: "Always prioritize patterns related to confirmation steps"
```

### Customizing Playbooks

**1. Manual Editing**
```
Location: QC Agent → Learning & Memory → Playbook tab
Click "Edit Playbook" to modify the raw markdown
```

**2. Version Management**
```
Location: QC Agent → Learning & Memory → History tab
- View all previous versions
- Click "Restore" to revert to any version
```

---

## UI Components

### QC Agents Page (`/qc-agents`)
- List all QC agents by type (tabs)
- Create new agents
- Quick actions (edit, delete, duplicate)

### QC Agent Editor (`/qc-agents/:id` or `/qc-agents/new`)
**Tabs**:
1. **General**: Name, description, type, status
2. **Prompt & Instructions**: System prompt, focus, criteria, format
3. **Knowledge Base**: Upload documents for context
4. **LLM Settings**: Provider, model selection
5. **Analysis Rules**: Type-specific configurations
6. **Learning & Memory** (if supports learning):
   - Playbook tab
   - Brains tab
   - Learning Settings tab
   - Patterns tab
   - History tab

### Campaign Integration
- Assign QC agents to campaigns
- Training calls separate from live calls
- Auto-analysis settings per campaign

---

## Default Brain Prompts

### Tonality Agent - Reflection Brain

```
SYSTEM: You are an expert voice tonality and emotional intelligence analyst.
Your specialty is identifying patterns in HOW things are said, not just WHAT is said.
Focus on: vocal warmth, energy levels, pacing, emotional resonance, confidence signals.

PREFIX: ## TONALITY-SPECIFIC GUIDANCE
When analyzing these QC results, focus on VOICE patterns:
- Emotional tone at key moments (open, objection, close)
- Energy matching between agent and customer
- Pacing changes that signal confidence or anxiety
- Warmth indicators in voice quality

SUFFIX: ## TONALITY PATTERN PRIORITIES
Prioritize patterns related to:
1. Opening warmth and its correlation with outcomes
2. How agents handle emotional objections
3. Close confidence vs desperation signals
4. Energy synchronization throughout the call
```

### Language Pattern Agent - Reflection Brain

```
SYSTEM: You are an expert sales conversation analyst.
Your specialty is identifying tactical patterns in sales conversations - 
what words, phrases, and structures lead to successful outcomes.
Focus on: commitment language, objection handling techniques, confirmation steps, closing tactics.

PREFIX: ## LANGUAGE PATTERN GUIDANCE
When analyzing these QC results, focus on TACTICAL patterns:
- Specific phrases that correlate with shows vs no-shows
- Objection handling techniques and their effectiveness
- Confirmation and commitment language strength
- Closing technique variations and outcomes

SUFFIX: ## LANGUAGE PATTERN PRIORITIES
Prioritize patterns related to:
1. Confirmation language (explicit time/date vs vague)
2. Commitment strength indicators ("I will" vs "I'll try")
3. Objection resolution completeness
4. Close technique effectiveness
```

---

## Quick Reference

### Learning Modes

| Mode | When Learning Triggers | Best For |
|------|----------------------|----------|
| Manual | Only when you click "Train" | Full control, low volume |
| Auto | After every outcome | High volume, continuous learning |
| Every X | After X outcomes | Balanced, batch learning |

### Prediction Fields

| Field | Type | Description |
|-------|------|-------------|
| show_likelihood | 0-1 | Probability appointment will show |
| booking_quality | Enum | "strong", "medium", "weak" |
| risk_factors | Array | What might cause no-show |
| positive_signals | Array | What predicts show |
| confidence | 0-1 | How confident in prediction |

### Pattern Types

| Type | Description |
|------|-------------|
| victory | Patterns that predict "showed" |
| defeat | Patterns that predict "no-show" |
| campaign_specific | Only applies to specific campaign |
| transferable | Works across all contexts |

---

## Troubleshooting

### Learning Not Triggering

1. Check learning mode (Settings → Learning Mode)
2. Verify `is_enabled` is true
3. For `every_x`, check if threshold reached
4. Ensure at least 5 outcomes recorded

### Playbook Not Updating

1. Check if learning session completed successfully
2. View learning sessions in History tab
3. Check for errors in session details

### Brain Prompts Not Applied

1. Verify prompts saved (check for success toast)
2. Prompts apply on NEXT learning session
3. Manual trigger to test immediately

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           QC INTELLIGENCE SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FRONTEND (React)                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  QCAgents.jsx    QCAgentEditor.jsx    QCPlaybookManager.jsx         │   │
│  │                                                                      │   │
│  │  • List agents    • Edit settings      • View playbook              │   │
│  │  • Create new     • Configure prompts  • Edit brains                │   │
│  │  • Delete         • Manage KB          • Trigger learning           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    │ API Calls                               │
│                                    ▼                                         │
│  BACKEND (FastAPI)                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  qc_agent_router.py          qc_learning_router.py                  │   │
│  │  • CRUD operations           • Playbook management                   │   │
│  │  • KB uploads                • Learning control                      │   │
│  │  • Analysis triggers         • Brain prompts                         │   │
│  │                              • Pattern management                    │   │
│  │                                                                      │   │
│  │  qc_learning_service.py                                             │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐      │   │
│  │  │ ReflectionBrain│  │ TrainingBrain  │  │LearningOrchestrator│     │   │
│  │  │                │  │                │  │                    │     │   │
│  │  │ Analyzes       │  │ Generates      │  │ Coordinates        │     │   │
│  │  │ outcomes       │──│ playbooks      │──│ learning loop      │     │   │
│  │  └────────────────┘  └────────────────┘  └──────────────────┘      │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    │ Database Operations                     │
│                                    ▼                                         │
│  DATABASE (MongoDB)                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  qc_agents    qc_playbooks    qc_analysis_logs    qc_patterns       │   │
│  │                                                                      │   │
│  │  qc_learning_sessions                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Files Reference

### Backend
- `backend/qc_agent_models.py` - QC Agent data models
- `backend/qc_agent_router.py` - QC Agent CRUD API
- `backend/qc_learning_models.py` - Learning/memory models + defaults
- `backend/qc_learning_service.py` - Brain logic + orchestrator
- `backend/qc_learning_router.py` - Learning API endpoints

### Frontend
- `frontend/src/components/QCAgents.jsx` - Agent list page
- `frontend/src/components/QCAgentEditor.jsx` - Agent editor
- `frontend/src/components/QCPlaybookManager.jsx` - Learning UI
- `frontend/src/services/api.js` - API client functions

---

*Documentation generated for QC Intelligence System v2.0*
