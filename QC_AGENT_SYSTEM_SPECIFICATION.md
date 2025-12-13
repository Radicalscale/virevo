# QC Agent System - Complete Feature Specification

## 🎯 Overview
Enhanced QC Agent system with 4 toggleable sections for comprehensive call quality analysis and optimization.

---

## 1️⃣ Technical Performance QC Agent (Latency Analysis)

### Purpose
Analyze call logs to identify technical bottlenecks and latency issues node-by-node.

### Core Functionality
- **Input:** Call log file extracted at end of call
- **Analysis Target:** Time To First Speech (TTFS) - excludes total TTS build time
- **Alert Threshold:** Only flags latency exceeding 4 seconds

### Breakdown Structure
**For Each Node:**
- ✅ **Node Name/ID** - Clear identification
- ✅ **Latency Components (Separated):**
  - LLM processing time
  - Transition evaluation time
  - Variable extraction time
  - Knowledge Base retrieval time
  - TTS generation time (first audio chunk)
  - Telnyx overhead
  - System overhead
- ✅ **Total TTS Build Time** - Displayed separately (not counted in TTFS alert)
- ✅ **TTFS Metric** - The critical metric for alerts

### Output Format
- 📊 **Organized by node** - Sequential flow through conversation
- 🚨 **Flagged Issues** - Only nodes exceeding 4s TTFS threshold
- 🎯 **Specific Bottleneck Identification:**
  - "KB retrieval taking 2.3s - consider optimizing KB structure"
  - "Transition evaluation 1.8s - simplify conditions or use auto-transition"
  - "LLM response 5.2s - prompt too complex, reduce context"
  - "TTS generation 1.5s - response too long, break into smaller chunks"

### User-Friendly Presentation
- ✅ Formatted like human log analysis (clear, readable)
- ✅ Color-coded severity (green <2s, yellow 2-4s, red >4s)
- ✅ Actionable recommendations for each bottleneck
- ✅ Summary section with overall call performance

---

## 2️⃣ Script Optimization QC Agent (Conversation Quality)

### Purpose
Analyze conversation quality and suggest sharper, more effective responses to reach node goals faster.

### Customization
- **User-Defined Rules** - Specific speech patterns to look for
- **Context Input** - Campaign context, product details, target avatar
- **Learning Parameters** - What constitutes "snappy", "hyper-relevant", "dialed"

### Per-Node Analysis Structure

**Display Format:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Node: [Node Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📜 ACTUAL TRANSCRIPT:
User: [what they said]
AI: [what agent said]
User: [follow-up]
AI: [response]

💡 FEEDBACK & IMPROVEMENT:
- [Specific issue identified]
- [Why current response is suboptimal]
- [Better response example]

📝 PROMPT ANALYSIS:
Current Prompt: [shows actual node prompt]

🔧 SUGGESTIONS:
1. Entirely New Prompt: [complete rewrite]
2. Adjusted Prompt: [specific edits to existing]
3. KB Enhancement: [suggest KB additions with draft content]

[Save New Prompt Button]
[Test Changes Button] → Opens existing tester
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Bulk Actions
- 🚀 **Auto-Enhance All Nodes** - AI analyzes entire call
  - Generates optimized prompts for every node
  - Suggests transition improvements
  - Creates new KB content as needed
  - Saves as new copy agent for testing
  - Generates MD document for enhanced KB

### Campaign Feature (Multi-Call Learning)

**Database Structure:**
- Campaign ID grouping multiple calls
- Tracks all AI suggestions across calls
- Identifies patterns across conversations
- Links copy agents to campaigns

**Pattern Recognition:**
- Analyzes suggestions across multiple calls
- Identifies recurring bottlenecks
- Spots consistent weak points
- Recognizes successful patterns

**Campaign Report Generation:**
```
📊 CAMPAIGN REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Campaign: [Name]
Calls Analyzed: [Count]
Date Range: [Start - End]

🎯 PATTERN INSIGHTS:
- [Recurring issue across X calls]
- [Successful pattern in Y calls]
- [Node Z consistently underperforming]

🔧 CONSOLIDATED SUGGESTIONS:
- [High-impact changes based on patterns]
- [KB content gaps identified]
- [Transition logic improvements]

🤖 GENERATED AGENT:
[AI creates entirely new optimized agent]
- Based on collective learnings
- Incorporates best responses
- Includes enhanced KB
- Pre-configured transitions
[Deploy Copy Agent Button]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Campaign Setup:**
- Assign calls to campaigns
- Define campaign-level rules
- Set learning parameters
- Configure success metrics

---

## 3️⃣ Tonality & Delivery QC Agent (Audio Analysis)

### Purpose
Analyze actual audio recordings to assess and improve AI voice delivery quality.

### Input
- **Audio Recording** - Full call audio
- **Node Transcripts** - Text of what was said in each node
- **Sync Data** - Which node said which lines

### Customization
- **General Tonality Rules** - User-defined delivery guidelines
- **Reference Recordings** - Upload examples of ideal delivery
- **Voice Guidelines** - Link to ElevenLabs best practices
- **Brand Voice Standards** - Specific requirements (warm, professional, energetic, etc.)

### Per-Node Analysis Structure

**Display Format:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Node: [Node Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎧 AUDIO PLAYBACK:
[Embedded audio player for this node's section]
Timestamp: [00:32 - 00:58]

📜 TRANSCRIPT:
AI: "In a nutshell, we set up passive income 
     websites and you bank the monthly fees 
     they pay you."

🎭 DELIVERY ANALYSIS:
✅ Positives:
- Clear enunciation
- Good pacing on key phrase "passive income"

⚠️ Issues Detected:
- Monotone delivery on "bank the monthly fees"
- Missing emphasis on value proposition
- Slight rush at end of sentence

🔧 SSML/PROSODY RECOMMENDATIONS:
<speak>
  In a nutshell, we set up 
  <prosody rate="95%">passive income websites</prosody>
  <break time="300ms"/>
  and you bank 
  <prosody pitch="+5%">the monthly fees</prosody> 
  they pay you.
</speak>

📚 ELEVENLABS BEST PRACTICES:
- Add emphasis tags on key value words
- Use breaks for dramatic effect
- Adjust pitch for important phrases
[Link to ElevenLabs Voice Control Docs]

🎯 SPECIFIC SUGGESTIONS:
1. Slow down on "passive income" (+5% emphasis)
2. Add 300ms pause before value proposition
3. Raise pitch slightly on "monthly fees"
4. More energy in closing phrase

[Apply Changes to Node Button]
[Preview Changes Button]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Advanced Features
- **Emotion Detection** - Identify flat/monotone sections
- **Pacing Analysis** - Flag rushed or dragged sections
- **Emphasis Tracking** - Ensure key phrases have proper stress
- **Client vs AI Comparison** - Analyze user reactions to different deliveries
- **Pattern Recognition** - "User engagement drops when AI uses monotone"

### Output Types
- Per-node delivery scorecard
- Overall call tonality assessment
- Client reaction analysis (pauses, interruptions, engagement)
- Comparative analysis across calls in campaign

---

## 4️⃣ Direct Node Testing Agent (Existing Feature)

### Current Functionality
- Manual message input to test individual nodes
- Real-time response testing
- Metrics tracking
- Variable extraction verification

### Integration with Other QC Agents
- **From Script QC** → "Test Changes" button opens this agent
- **From Tonality QC** → "Preview Changes" uses TTS preview
- **Quick Access** - Always available for manual testing

---

## 🎨 UI/UX Structure

### Main QC Interface Layout
```
┌─────────────────────────────────────────────────┐
│  QC AGENT - Call Analysis Dashboard            │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Tech/Latency] [Script Quality] [Tonality] [Direct Test]
│       ▲                                         │
│     Active                                      │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Content specific to selected tab]            │
│                                                 │
│  - Collapsible sections per node               │
│  - Color-coded metrics                         │
│  - Action buttons contextual to analysis       │
│  - Export/Share functionality                  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Tab-Specific Features

**Tech/Latency Tab:**
- 📊 Timeline visualization of call latency
- 🎯 Click nodes to see detailed breakdown
- 📥 Export performance report
- 🔄 Compare with previous calls

**Script Quality Tab:**
- 📝 Node-by-node conversation review
- 💡 Inline suggestions and comparisons
- 🚀 Bulk action buttons
- 📊 Campaign analytics dashboard

**Tonality Tab:**
- 🎧 Audio player with node sync
- 🎭 Visual waveform with annotations
- 🔊 Before/after preview player
- 📚 Quick reference to voice guidelines

**Direct Test Tab:**
- 💬 Chat-like testing interface (existing)
- 🔄 Quick switch from other tabs
- 📊 Real-time metrics

---

## 🗄️ Backend Database Structure

### Campaign System
```
campaigns:
  - id
  - name
  - user_id
  - created_at
  - rules (JSON)
  - learning_parameters (JSON)
  - linked_agents [] (array of agent IDs)

campaign_calls:
  - id
  - campaign_id
  - call_id
  - analyzed_at
  - qc_results (JSON)

campaign_suggestions:
  - id
  - campaign_id
  - suggestion_type
  - node_id
  - suggestion_text
  - frequency_count
  - impact_score
  - created_at

campaign_patterns:
  - id
  - campaign_id
  - pattern_type
  - description
  - affected_nodes []
  - evidence_calls []
  - confidence_score
```

---

## 🚀 Implementation Priority

### Phase 1: Core Infrastructure ✅ START HERE
1. Extract and store call logs with node-level data
2. Create toggleable QC tab interface
3. Backend endpoints for each QC agent type
4. Database schema setup

### Phase 2: Tech/Latency QC
1. Log parsing and latency calculation
2. TTFS metric separation
3. Bottleneck identification logic
4. User-friendly report generation

### Phase 3: Script Quality QC
1. LLM-based conversation analysis
2. Prompt suggestion engine
3. KB enhancement recommendations
4. Per-node optimization interface

### Phase 4: Campaign System
1. Database schema implementation
2. Pattern recognition algorithms
3. Multi-call aggregation
4. Campaign report generation
5. Automated agent creation from learnings

### Phase 5: Tonality QC
1. Audio-to-node synchronization
2. Delivery analysis algorithms
3. SSML/Prosody suggestion engine
4. Audio playback interface with annotations

### Phase 6: Integration & Polish
1. Cross-tab navigation
2. Export/import functionality
3. Comparison tools
4. Mobile responsiveness

---

## 🎯 Success Metrics

### Per QC Agent
- **Tech QC:** Average TTFS reduction over time
- **Script QC:** Response effectiveness improvement (conversion rates)
- **Tonality QC:** Delivery quality scores, user engagement metrics
- **Campaign Learning:** Agent performance improvement across iterations

### Overall System
- Time saved in manual QC review
- Number of optimization actions taken
- Agent performance improvement trajectory
- User adoption and satisfaction scores

---

## 📝 Technical Notes

### Call Log Structure Requirements
Each call log must include:
- Node-level timestamps
- Latency breakdowns (LLM, TTS, KB, transitions)
- Full transcript with speaker labels
- Audio recording URLs
- Variable extraction events
- Session metadata

### API Key Requirements
- User's OpenAI/Grok API key for analysis
- Access to call recordings (Telnyx)
- ElevenLabs API for TTS preview (optional)

### Performance Considerations
- Asynchronous processing for long calls
- Caching of analysis results
- Incremental campaign pattern updates
- Efficient audio streaming for tonality analysis

---

This comprehensive QC system provides end-to-end call quality analysis and continuous improvement capabilities, enabling users to systematically optimize every aspect of their AI agents.
