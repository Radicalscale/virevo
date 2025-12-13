# QC System - Comprehensive Testing Checklist

## 🎯 Overview
This checklist covers all features of the QC Analysis system including Campaign learning capabilities, Batch Analysis, Prediction System, and API Key Management.

**Testing Date:** _____________  
**Tester:** _____________  
**Environment:** Production / Staging  
**Version:** 2.0 (Updated Nov 29, 2025)

---

## ✅ Phase 1: Tech/Latency QC Testing

### Basic Functionality
- [ ] Navigate to Calls page
- [ ] Click purple Zap icon (⚡) on any completed call
- [ ] QC Dashboard loads successfully
- [ ] Tech/Latency tab is default active tab
- [ ] Call details display correctly (phone number, duration, sentiment)

### Log Upload & Analysis
- [ ] Upload log file (.log or .txt format)
- [ ] File upload shows success message
- [ ] Click "Analyze Tech Performance" button
- [ ] Analysis completes without errors
- [ ] Loading state displays correctly during analysis

### Analysis Results Display
- [ ] **Performance Summary Cards:**
  - [ ] Overall performance badge shows correct status
  - [ ] Total nodes count is accurate
  - [ ] Flagged nodes count is correct
  - [ ] Performance percentage calculates correctly
- [ ] **Color Coding:**
  - [ ] Excellent = Green
  - [ ] Good = Blue
  - [ ] Needs Improvement = Yellow
  - [ ] Poor = Red

### Recommendations Section
- [ ] Recommendations display if issues found
- [ ] Recommendations are actionable and specific
- [ ] Blue info box styling is correct
- [ ] Aggregated insights are helpful

### Node-by-Node Breakdown
- [ ] All nodes display in correct order
- [ ] Each node card shows:
  - [ ] Node name/label
  - [ ] TTFS (Time To First Speech) in seconds
  - [ ] Color-coded TTFS value
  - [ ] LLM processing time
  - [ ] TTS generation time
  - [ ] Transition evaluation time
  - [ ] KB retrieval time
- [ ] Flagged nodes (>4s) have red border
- [ ] Alert icon shows on flagged nodes
- [ ] Bottleneck alerts display in red boxes
- [ ] Bottleneck descriptions are clear

### Export Functionality
- [ ] "Export JSON" button works
- [ ] JSON file downloads correctly
- [ ] JSON file contains all analysis data
- [ ] Filename includes call ID and timestamp
- [ ] "Export Report (MD)" button works
- [ ] Markdown file downloads correctly
- [ ] Markdown report is well-formatted
- [ ] Report includes all sections (summary, recommendations, nodes)

### Performance
- [ ] Analysis completes in <30 seconds
- [ ] UI remains responsive during analysis
- [ ] Large log files (>1MB) process without errors
- [ ] Memory usage is acceptable

---

## ✅ Phase 2: Script Quality QC Testing

### Basic Functionality
- [ ] Click "Script Quality" tab
- [ ] Tab content loads correctly
- [ ] Analysis configuration section displays

### Configuration
- [ ] **Analysis Focus Checkboxes:**
  - [ ] "Focus on brevity" checkbox works
  - [ ] "Check goal alignment" checkbox works
  - [ ] "Evaluate naturalness" checkbox works
  - [ ] Selections persist during session

### Analysis Execution
- [ ] Click "Analyze Script Quality"
- [ ] Loading state shows "Analyzing Conversation..."
- [ ] Analysis uses Grok API (backend logs confirm)
- [ ] Analysis completes without timeout
- [ ] Results display correctly

### Summary Dashboard
- [ ] **4 Metric Cards Display:**
  - [ ] Total conversation turns count
  - [ ] Good quality count (green)
  - [ ] Needs improvement count (yellow)
  - [ ] Poor quality count (red)
- [ ] Statistics are accurate
- [ ] Color coding is consistent

### Key Recommendations
- [ ] Top 3 prompt improvements display
- [ ] KB enhancement suggestions show
- [ ] Impact assessment is clear
- [ ] Purple info box styling is correct

### Turn-by-Turn Analysis
For each conversation turn:
- [ ] **Header Section:**
  - [ ] Turn number/node name displays
  - [ ] Quality badge shows (excellent/good/needs_improvement/poor)
  - [ ] Badge color matches quality level
  - [ ] Goal efficiency indicator shows
  - [ ] Efficiency color-coded correctly
- [ ] **Transcript Section:**
  - [ ] User message displays correctly
  - [ ] AI response displays correctly
  - [ ] Formatting is readable
- [ ] **Positives Section:**
  - [ ] Green checkmarks show
  - [ ] Positive points are specific
  - [ ] Grammar is correct
- [ ] **Issues Section:**
  - [ ] Yellow warning icons show
  - [ ] Issues are actionable
  - [ ] Descriptions are clear
- [ ] **Improved Response:**
  - [ ] Shows alternative response
  - [ ] Blue box styling correct
  - [ ] Response is contextually relevant
- [ ] **Prompt Suggestions:**
  - [ ] Purple box styling correct
  - [ ] Type (new_prompt/adjustment/kb_addition) shows
  - [ ] Suggestion text is specific
  - [ ] Reasoning explains why
  - [ ] "Copy Suggestion" button works
  - [ ] Copies to clipboard successfully
  - [ ] Toast notification shows
  - [ ] "Test in Agent Tester" button works
  - [ ] Appropriate message displays

### Analysis Quality
- [ ] LLM analysis is coherent
- [ ] Suggestions are practical
- [ ] No hallucinations or irrelevant content
- [ ] Multiple turns analyzed correctly
- [ ] Analysis time is reasonable (<10s per turn)

---

## ✅ Phase 3: Tonality QC Testing

### Basic Functionality
- [ ] Click "Tonality" tab
- [ ] Tab content loads correctly

### No Recording Available
- [ ] If no recording, shows appropriate message
- [ ] Explains recording is required
- [ ] UI is clear and not confusing

### Recording Available
- [ ] Audio player displays
- [ ] Recording URL is valid
- [ ] Playback works correctly
- [ ] Click "Analyze Voice Delivery"
- [ ] Development notice displays
- [ ] Planned features list shows

### UI Polish
- [ ] Mic icon displays correctly
- [ ] Blue info boxes styled properly
- [ ] Text is readable
- [ ] Layout is clean

---

## ✅ Phase 4: Direct Test Tab

### Navigation
- [ ] Click "Direct Test" tab
- [ ] Tab content loads
- [ ] Message about Agent Tester displays
- [ ] "Open Agent Tester" button works
- [ ] Navigates to correct agent tester
- [ ] Agent ID is preserved in navigation

---

## ✅ Phase 5: Campaign Management

### Campaign List View
- [ ] Navigate to "QC Campaigns" in sidebar
- [ ] Campaign manager loads
- [ ] Header displays correctly
- [ ] "New Campaign" button visible

### Empty State
- [ ] If no campaigns, empty state shows
- [ ] Icon and message display
- [ ] "Create First Campaign" CTA works

### Create Campaign
- [ ] Click "New Campaign" button
- [ ] Modal opens correctly
- [ ] **Form Fields:**
  - [ ] Campaign name input works
  - [ ] Description textarea works
  - [ ] Character limits are reasonable
- [ ] **Analysis Focus Checkboxes:**
  - [ ] Three checkboxes display
  - [ ] All are checked by default
  - [ ] Can be toggled on/off
- [ ] Click "Create Campaign"
- [ ] Validation works (name required)
- [ ] Success toast shows
- [ ] Modal closes
- [ ] New campaign appears in list
- [ ] Backend creates campaign (check DB)

### Campaign Cards
- [ ] Each campaign shows:
  - [ ] Campaign name
  - [ ] Description (or "No description")
  - [ ] Total calls count
  - [ ] Patterns identified count
  - [ ] Delete button (trash icon)
- [ ] Hover effect (purple border) works
- [ ] Stats update when calls added

### Campaign Actions
- [ ] "View Details" button works (placeholder check)
- [ ] Settings button works (placeholder check)
- [ ] Delete button shows confirmation
- [ ] Confirmation warns about data loss
- [ ] Cancel preserves campaign
- [ ] Confirm deletes campaign
- [ ] Success toast shows
- [ ] Campaign removed from list
- [ ] Related data deleted (check DB)

### Add Call to Campaign
- [ ] From QC Dashboard, click "Add to Campaign"
- [ ] Modal opens
- [ ] Campaign dropdown populates
- [ ] If no campaigns, shows create button
- [ ] Select campaign from dropdown
- [ ] Click "Add to Campaign"
- [ ] Success toast shows
- [ ] Call is linked (check DB)

### Pattern Analysis
- [ ] Add 2+ calls to a campaign
- [ ] Trigger pattern analysis (API call)
- [ ] Patterns detected correctly
- [ ] Confidence scores calculated
- [ ] Pattern types identified:
  - [ ] Bottlenecks
  - [ ] Recurring issues
  - [ ] Improvement opportunities
  - [ ] Success patterns

### Campaign Report
- [ ] Generate campaign report (API call)
- [ ] Report structure is correct
- [ ] Statistics are accurate
- [ ] Patterns grouped by type
- [ ] High-impact suggestions identified
- [ ] Insights are actionable
- [ ] Recommendations prioritized
- [ ] Impact levels assigned

---

## ✅ Phase 5.5: Batch Analysis (Analyze All Calls)

### Button & UI
- [ ] "Analyze All Calls" button visible in campaign header
- [ ] Button is green with Zap icon
- [ ] Button positioned next to "Analyze Patterns"

### No Pending Calls
- [ ] Click button when all calls analyzed
- [ ] Shows "No pending calls" toast message
- [ ] UI remains responsive

### With Pending Calls
- [ ] Click button with unanalyzed calls
- [ ] Button shows "Analyzing..." loading state
- [ ] Button becomes disabled during analysis
- [ ] Toast shows "Analysis started" with counts
- [ ] Shows number of calls queued
- [ ] Shows number of training calls queued

### Background Processing
- [ ] UI remains responsive during analysis
- [ ] Can navigate away and back
- [ ] Analysis continues in background
- [ ] Results appear after refresh/delay

### Analysis Types
- [ ] Script analysis runs on pending calls
- [ ] Tonality analysis runs on pending calls
- [ ] Results populate correctly per type
- [ ] `script_qc_results` field populated
- [ ] `tonality_qc_results` field populated

### Training Calls Integration
- [ ] Training calls included in batch
- [ ] `qc_analyzed_at` timestamp set
- [ ] `qc_analysis_id` linked correctly

### Force Reanalyze Option
- [ ] Can trigger reanalysis of already-analyzed calls
- [ ] Previous results overwritten
- [ ] New timestamps applied

### Rate Limiting
- [ ] Calls processed with delays (1s between)
- [ ] No API rate limit errors
- [ ] All calls eventually processed

---

## ✅ Phase 5.6: Prediction System

### Script Analysis Predictions
- [ ] Run script analysis on a call
- [ ] Response includes `predictions` object
- [ ] **Prediction Fields Present:**
  - [ ] `show_likelihood` (float 0-1)
  - [ ] `booking_quality` (STRONG/MEDIUM/WEAK)
  - [ ] `risk_factors` (array of strings)
  - [ ] `positive_signals` (array of strings)
  - [ ] `confidence` (float 0-1)
  - [ ] `commitment_strength_score` (float 0-1)
  - [ ] `objection_resolution_score` (float 0-1)

### Tonality Analysis Predictions
- [ ] Run tonality analysis on a call
- [ ] Response includes `predictions` object
- [ ] **Prediction Fields Present:**
  - [ ] `show_likelihood` (float 0-1)
  - [ ] `booking_quality` (STRONG/MEDIUM/WEAK)
  - [ ] `risk_factors` (array of strings)
  - [ ] `positive_signals` (array of strings)
  - [ ] `confidence` (float 0-1)
  - [ ] `emotional_alignment_score` (float 0-1)
  - [ ] `energy_match_score` (float 0-1)

### Prediction Quality
- [ ] High quality conversations → higher show_likelihood
- [ ] More issues → lower show_likelihood
- [ ] More positives → higher show_likelihood
- [ ] More conversation data → higher confidence
- [ ] Risk factors extracted from issues
- [ ] Positive signals extracted from positives

### Learning System Integration
- [ ] Predictions saved to `qc_analysis_logs`
- [ ] `qc_agent_id` linked in log
- [ ] `campaign_id` linked in log
- [ ] Training call gets `qc_analysis_id` reference
- [ ] Predictions available for learning loop

### Prediction Display (UI)
- [ ] Predictions shown in analysis results
- [ ] show_likelihood displayed as percentage
- [ ] Risk factors listed clearly
- [ ] Positive signals listed clearly
- [ ] Booking quality badge colored correctly

---

## ✅ Phase 5.7: API Key Management

### Service Alias Resolution
- [ ] Request with 'xai' uses Grok key
- [ ] Request with 'x.ai' uses Grok key
- [ ] Request with 'gpt' uses OpenAI key
- [ ] Request with 'gpt-4' uses OpenAI key
- [ ] Request with 'gpt-5' uses OpenAI key
- [ ] Request with 'claude' uses Anthropic key
- [ ] Request with 'google' uses Gemini key

### Key Pattern Matching
- [ ] Keys starting with 'xai-' detected as Grok
- [ ] Keys starting with 'sk-' detected as OpenAI
- [ ] Keys starting with 'sk-proj-' detected as OpenAI
- [ ] Keys starting with 'sk-ant-' detected as Anthropic
- [ ] Keys starting with 'AIza' detected as Gemini
- [ ] Keys starting with 'sk_' detected as ElevenLabs

### Emergent LLM Key Fallback
- [ ] When user has no key, Emergent key used (if available)
- [ ] Works for OpenAI requests
- [ ] Works for Anthropic requests
- [ ] Works for Gemini requests
- [ ] Works for Grok requests
- [ ] Logged as "Using Emergent LLM key"

### Key Retrieval Logging
- [ ] Pattern match logged in backend
- [ ] Fallback usage logged
- [ ] Missing key warning logged with user ID

### Error Handling
- [ ] Missing key returns appropriate error
- [ ] Invalid key format handled
- [ ] Encrypted keys decrypted correctly

---

## ✅ Phase 6: Security & Tenant Isolation

### Tenant Isolation Tests
- [ ] **Test 1: Campaign Access**
  - [ ] User A creates campaign
  - [ ] User B cannot see User A's campaign
  - [ ] Direct API call with User A's campaign ID returns 404 for User B
- [ ] **Test 2: Call Assignment**
  - [ ] User A cannot add User B's calls to campaign
  - [ ] Error message is appropriate
- [ ] **Test 3: Pattern Analysis**
  - [ ] User A's patterns only include their calls
  - [ ] No cross-tenant data leakage
- [ ] **Test 4: Report Generation**
  - [ ] Reports only include user's own data
  - [ ] No aggregate data from other tenants

### Data Integrity
- [ ] Cascade deletion works correctly
- [ ] Deleting campaign removes:
  - [ ] Campaign record
  - [ ] Campaign calls
  - [ ] Campaign suggestions
  - [ ] Campaign patterns
- [ ] Original calls are NOT deleted
- [ ] Other campaigns unaffected

---

## ✅ Integration & Polish Features

### Navigation
- [ ] All tabs accessible from QC Dashboard
- [ ] Tab switching is smooth
- [ ] Active tab highlighted correctly
- [ ] Back button works from all tabs
- [ ] Breadcrumb navigation accurate

### Cross-Tab Functionality
- [ ] Can switch tabs without losing data
- [ ] Analysis results persist during session
- [ ] "Analyze Another" resets state correctly

### Export/Import
- [ ] Tech QC: JSON export works
- [ ] Tech QC: Markdown export works
- [ ] Script QC: Copy to clipboard works
- [ ] Export filenames are descriptive
- [ ] Exported files are valid format

### Error Handling
- [ ] Invalid log file shows error
- [ ] Network errors handled gracefully
- [ ] API errors show user-friendly messages
- [ ] Timeout errors handled
- [ ] Missing data doesn't break UI

### Toast Notifications
- [ ] Success toasts appear
- [ ] Error toasts appear
- [ ] Info toasts appear
- [ ] Toasts auto-dismiss
- [ ] Multiple toasts stack correctly
- [ ] Toast styling is consistent

### Responsive Design
- [ ] Desktop (1920x1080) displays correctly
- [ ] Laptop (1366x768) displays correctly
- [ ] Tablet view is usable
- [ ] Mobile view is readable
- [ ] No horizontal scrolling
- [ ] Text is legible at all sizes

### Performance
- [ ] Page load time <3 seconds
- [ ] Tab switching is instant
- [ ] No memory leaks during use
- [ ] Browser console has no errors
- [ ] Network requests are efficient
- [ ] Large datasets don't freeze UI

---

## ✅ Edge Cases & Error Scenarios

### Data Quality
- [ ] Empty log file handled
- [ ] Corrupted log file handled
- [ ] Very large log file (>10MB) handled
- [ ] Log with no latency data handled
- [ ] Call with no transcript handled
- [ ] Call with no recording handled

### Network Issues
- [ ] Slow connection handled
- [ ] Connection timeout handled
- [ ] API endpoint down handled
- [ ] Partial data received handled

### User Actions
- [ ] Rapid clicking doesn't break UI
- [ ] Switching tabs mid-analysis handled
- [ ] Browser back button works correctly
- [ ] Page refresh preserves state (where appropriate)
- [ ] Multiple browser tabs don't conflict

### LLM Integration
- [ ] Grok API key missing handled
- [ ] API rate limit handled
- [ ] Invalid API response handled
- [ ] JSON parsing errors handled

---

## ✅ Accessibility

### Keyboard Navigation
- [ ] Tab key navigates through elements
- [ ] Enter key activates buttons
- [ ] Escape key closes modals
- [ ] Focus indicators visible

### Screen Reader
- [ ] Important elements have labels
- [ ] Status updates announced
- [ ] Error messages announced

### Visual Accessibility
- [ ] Color contrast meets WCAG AA
- [ ] Text size is readable
- [ ] Icons have text alternatives
- [ ] Status not conveyed by color alone

---

## ✅ Documentation & Help

### User Guidance
- [ ] Empty states are helpful
- [ ] Error messages are clear
- [ ] Tooltips explain features
- [ ] Placeholders guide input

### Technical Documentation
- [ ] API endpoints documented
- [ ] Data models documented
- [ ] Security practices documented
- [ ] Deployment guide available

---

## 📊 Test Results Summary

### Pass/Fail Counts
- **Total Tests:** _____ (estimated 350+)
- **Passed:** _____
- **Failed:** _____
- **Blocked:** _____
- **Pass Rate:** _____%

### New Features Added (v2.0)
- [ ] Batch Analysis (Analyze All Calls) - Phase 5.5
- [ ] Prediction System Integration - Phase 5.6
- [ ] API Key Management Improvements - Phase 5.7

### Critical Issues Found
1. _________________________________
2. _________________________________
3. _________________________________

### Minor Issues Found
1. _________________________________
2. _________________________________
3. _________________________________

### Performance Metrics
- **Average Page Load:** _____ seconds
- **Average Analysis Time (Tech QC):** _____ seconds
- **Average Analysis Time (Script QC):** _____ seconds per turn
- **Average Batch Analysis Time:** _____ seconds per call
- **Memory Usage:** _____ MB

### Browser Compatibility
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

---

## 🔧 Recommended Next Steps

### High Priority
1. _________________________________
2. _________________________________
3. _________________________________

### Medium Priority
1. _________________________________
2. _________________________________
3. _________________________________

### Nice to Have
1. _________________________________
2. _________________________________
3. _________________________________

---

## 📝 Tester Notes

### Positive Observations
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

### Areas for Improvement
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

### User Experience Feedback
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

## ✅ Sign-Off

**Tester Signature:** ___________________  
**Date:** ___________________  
**Status:** [ ] Approved for Release  [ ] Needs Revision

---

## 📋 Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Nov 2025 | Initial checklist for 4-tab QC system |
| 2.0 | Nov 29, 2025 | Added: Phase 5.5 (Batch Analysis), Phase 5.6 (Prediction System), Phase 5.7 (API Key Management) |

---

**End of QC System Testing Checklist**
