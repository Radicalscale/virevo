# QC Agents Scoring Reference

## Quick Score Interpretation Guide

---

## Commitment Score (0-100)

### Score Ranges

| Score | Risk Level | Interpretation | Action |
|-------|-----------|----------------|---------|
| 75-100 | **Low** 🟢 | Strong commitment detected | Send standard confirmation |
| 50-74 | **Medium** 🟡 | Moderate commitment | Send confirmation + reminder with value prop |
| 0-49 | **High** 🔴 | Weak/uncertain commitment | URGENT: Call within 1 hour to re-confirm |

### What Influences This Score?

**Positive Indicators (+):**
- ✅ "Absolutely", "definitely", "for sure"
- ✅ "I will", "I'll be there", "I'm scheduling"
- ✅ "Excited", "looking forward", "can't wait"
- ✅ Exclamation points and enthusiasm
- ✅ Present progressive tense ("I'm doing it now")

**Negative Indicators (-):**
- ❌ "I guess", "maybe", "might", "could"
- ❌ "Try to", "see if", "attempt to"
- ❌ "If I'm free", "if I can", "if possible"
- ❌ "Have to think", "call me back", "not sure"
- ❌ "Let me check" without follow-up

**Example:**
```
User: "Yes, absolutely! I'll definitely be there."
→ Commitment Score: 85 (Strong)

User: "Um, I guess so... maybe if I'm free."
→ Commitment Score: 25 (Weak)
```

---

## Conversion Score (0-100)

### Score Ranges

| Score | Funnel Quality | Interpretation | Action |
|-------|---------------|----------------|---------|
| 80-100 | **Excellent** 🟢 | Complete funnel | Celebrate! Use as training example |
| 60-79 | **Good** 🟡 | Minor gaps | Review missed stages |
| 40-59 | **Needs Work** 🟠 | Significant gaps | Script revision needed |
| 0-39 | **Poor** 🔴 | Critical failures | Complete process overhaul |

### The 6 Funnel Stages

**Required Stages (Must Have):**
1. ✅ **Hook** (20-40s) - Opening, establish relevance
2. ✅ **Qualification** (60-120s) - Understand needs, BANT
3. ✅ **Value Presentation** (60-120s) - Explain benefits
4. ✅ **Closing** (30-60s) - Direct ask for appointment
5. ✅ **Confirmation** (20-40s) - Lock in details

**Optional Stage:**
6. ⭕ **Objection Handling** (30-90s) - Address concerns

### BANT Qualification Framework

| Element | What to Check | Example Questions |
|---------|--------------|-------------------|
| **Budget** | Can they afford? | "What's your budget range?" |
| **Authority** | Can they decide? | "Are you the decision maker?" |
| **Need** | Do they have pain? | "What challenges are you facing?" |
| **Timeline** | When do they need it? | "When do you need to solve this?" |

**BANT Score Interpretation:**
- **Highly Qualified**: 70+ score, all 4 addressed
- **Qualified**: 50-69 score, 3+ addressed
- **Moderately Qualified**: 40-49 score, 2+ addressed
- **Poorly Qualified**: <40 score, <2 addressed

**Example:**
```
✅ Hook: "I'm calling about your inquiry"
✅ Qualification: "What are you looking for?"
✅ Value: "This will help you achieve 2x growth"
✅ Objection: User asks price, agent explains
✅ Closing: "Can we schedule a demo?"
✅ Confirmation: "I'll send calendar invite"
→ Conversion Score: 95 (Excellent)

❌ Hook: "Hi there"
❌ Closing: "Want to schedule?" (jumped too fast)
❌ No value, no qualification, no confirmation
→ Conversion Score: 30 (Poor)
```

---

## Excellence Score (0-100)

### Score Ranges

| Score | Quality Level | Interpretation | Action |
|-------|--------------|----------------|---------|
| 80-100 | **Exceptional** 🟢 | Top performer | Analyze for training |
| 60-79 | **Good** 🟡 | Solid execution | Minor improvements |
| 40-59 | **Average** 🟠 | Needs polish | Multiple improvements needed |
| 0-39 | **Poor** 🔴 | Subpar quality | Comprehensive script review |

### The 5 Excellence Patterns

| Pattern | What It Measures | Target | Examples |
|---------|-----------------|--------|----------|
| **Personalization** | Tailored to caller | 5+ mentions | "For your business...", "Your specific situation..." |
| **Enthusiasm** | Positive energy | 3+ markers | "Great!", "Excellent!", "Perfect!" |
| **Clarity** | Clear communication | 3+ indicators | "Specifically", "Exactly", "Clearly" |
| **Urgency** | Time pressure | 2+ mentions | "Limited spots", "Today only", "Deadline" |
| **Value Focus** | Benefit emphasis | 5+ mentions | "Help you", "Achieve", "Result", "Improve" |

### Pattern Scoring

Each pattern scored 0-10:
- **7-10**: Strong presence ✅
- **4-6**: Moderate presence ⚡
- **0-3**: Weak/absent ❌

**Weighted Formula:**
```
Excellence Score = 
  (Personalization × 25%) +
  (Enthusiasm × 15%) +
  (Clarity × 20%) +
  (Urgency × 20%) +
  (Value Focus × 20%)
```

**Example:**
```
High Quality Call:
"I understand YOUR specific situation. For YOU, this means...
The benefit YOU'LL see is... Excellent! Let me explain EXACTLY...
We have LIMITED spots. This will HELP you ACHIEVE..."

Pattern Scores:
- Personalization: 9/10
- Enthusiasm: 7/10
- Clarity: 8/10
- Urgency: 7/10
- Value Focus: 9/10
→ Excellence Score: 84 (Exceptional)

Low Quality Call:
"We have a product. It's good. Want it?"

Pattern Scores: All 1-2/10
→ Excellence Score: 22 (Poor)
```

---

## Show-Up Probability (0-100%)

### Probability Ranges

| Probability | Confidence | Expected Behavior | Follow-Up Strategy |
|-------------|-----------|-------------------|-------------------|
| 75-100% | **High** 🟢 | Will likely attend | Standard reminder |
| 50-74% | **Medium** 🟡 | 50/50 chance | Enhanced reminder + value |
| 25-49% | **Low** 🟠 | Unlikely to attend | Urgent re-engagement |
| 0-24% | **Very Low** 🔴 | Almost certain no-show | Consider rescheduling |

### Calculation Formula

```
Show-Up Probability = 
  (Commitment Score × 35%) +
  (Behavioral Progression × 20%) +
  (Objection Handling × 25%) +
  (Motivation × 20%)
  ± Metadata Adjustments
```

### Metadata Adjustments

| Factor | Adjustment | Reason |
|--------|-----------|---------|
| Call during business hours (9am-5pm) | +5% | More engaged |
| Call 2-10 minutes duration | +5% | Optimal length |
| Call <1 minute | -10% | Not qualified |
| Call >15 minutes | -5% | Lost focus |
| Historical no-show rate | Variable | Past behavior |

**Example:**
```
Commitment: 75
Progression: 80
Objection Handling: 100
Motivation: 75
Call at 2pm, 5 minutes

Calculation:
= (75×0.35) + (80×0.20) + (100×0.25) + (75×0.20) + 5 + 5
= 26.25 + 16 + 25 + 15 + 10
= 92.25%
→ Show-Up Probability: 92% (High)
```

---

## Overall Quality Score (0-100)

### Master Score Formula

```
Overall Quality = 
  (Commitment × 35%) +
  (Conversion × 35%) +
  (Excellence × 30%)
```

### Quality Tiers

| Score | Rating | Overall Assessment |
|-------|--------|-------------------|
| 90-100 | **A+** | Outstanding - Use for training |
| 80-89 | **A** | Excellent - Minor tweaks only |
| 70-79 | **B** | Good - Some improvement areas |
| 60-69 | **C** | Average - Needs attention |
| 50-59 | **D** | Below average - Significant issues |
| 0-49 | **F** | Poor - Major overhaul needed |

**Example Score Breakdown:**
```
Call #1: The Perfect Call
- Commitment: 88
- Conversion: 95
- Excellence: 87
→ Overall: 90 (A+) ✨

Call #2: The Rushed Call
- Commitment: 45
- Conversion: 52
- Excellence: 38
→ Overall: 45 (F) ⚠️
```

---

## Risk Level Classification

### Three-Tier System

| Risk Level | Show-Up % | Characteristics | Immediate Action |
|-----------|----------|----------------|------------------|
| 🟢 **Low** | 75-100% | Strong commitment, complete funnel, quality execution | Standard confirmation email + 24h reminder |
| 🟡 **Medium** | 50-74% | Moderate signals, some gaps, average quality | Confirmation email + value reminder + calendar invite + 24h SMS |
| 🔴 **High** | 0-49% | Weak/no commitment, major gaps, poor quality | URGENT: Call within 1 hour + personalized SMS + manager review |

---

## Action Item Templates

### Low Risk (75-100% Show-Up Probability)

**Email Template:**
```
Subject: Confirmed: [Meeting Time]

Hi [Name],

Great speaking with you! You're all set for our meeting on [Date] at [Time].

Here's what we'll cover:
- [Specific topic from call]
- [Value point discussed]

Looking forward to it!

[Calendar Invite Attached]
```

**SMS (24h before):**
```
Hi [Name]! Reminder: We're meeting tomorrow at [Time]. 
Looking forward to discussing [specific value point]. See you then!
```

### Medium Risk (50-74% Show-Up Probability)

**Email Template:**
```
Subject: Excited for Our Meeting + Quick Reminder

Hi [Name],

Thanks for scheduling our meeting for [Date] at [Time]!

Quick reminder of the value you'll get:
✅ [Benefit 1 from call]
✅ [Benefit 2 from call]  
✅ [Specific result they mentioned wanting]

This is going to help you [their goal]. Don't miss it!

[Calendar Invite with Clear Instructions]
```

**SMS (24h before):**
```
Hi [Name]! Don't forget: [Time] tomorrow. We're covering 
[specific benefit]. This will help you [goal]. Excited! 🚀
```

### High Risk (0-49% Show-Up Probability)

**Immediate Call Script:**
```
"Hi [Name], I wanted to follow up on our call earlier. 
I sensed you had some concerns. Can we talk about those? 
I want to make sure this is the right fit for you..."

[Address specific objections]
[Re-explain value]
[Re-confirm or reschedule]
```

**SMS (Immediate):**
```
Hi [Name], wanted to confirm you're still good for [Day] at [Time]? 
Had a thought about [their specific need] - let's discuss! 
Reply YES to confirm or call me to reschedule.
```

---

## Critical Moments Detection

### High-Severity Issues

| Issue Type | What It Means | Fix Priority |
|-----------|---------------|--------------|
| 🔴 **Objection Ignored** | User raised concern, agent continued script | CRITICAL |
| 🔴 **Value Never Presented** | Skipped value proposition entirely | CRITICAL |
| 🔴 **No Closing Attempt** | Never asked for appointment | CRITICAL |
| 🟠 **Premature Close** | Asked before qualifying/presenting value | HIGH |
| 🟠 **No Confirmation** | Didn't lock in details | HIGH |
| 🟡 **Generic Pitch** | Not personalized to caller | MEDIUM |

### Recovery Actions by Issue

| Issue | What Happened | Recovery Strategy |
|-------|--------------|------------------|
| Objection Ignored | "Too expensive" → Agent kept pitching | Call back: "I realized I didn't address your budget concern..." |
| Value Skipped | Jumped to schedule without explaining | Email: "Here's what you'll get from our meeting..." |
| No Close | Conversation ended without ask | Call back: "Let's schedule that session we discussed..." |

---

## Benchmarking Standards

### Industry Standards (Based on Analysis)

| Metric | Poor | Average | Good | Excellent |
|--------|------|---------|------|-----------|
| Commitment Score | <40 | 40-60 | 60-80 | 80+ |
| Conversion Score | <50 | 50-70 | 70-85 | 85+ |
| Excellence Score | <40 | 40-60 | 60-75 | 75+ |
| Show-Up Rate | <40% | 40-60% | 60-80% | 80%+ |
| Call Duration | <2 min | 2-4 min | 4-8 min | 6-10 min |
| BANT Addressed | 0-1 | 2 | 3 | 4 |

### Top Performer Characteristics

**What 90+ Overall Quality Calls Have:**
- ✅ Commitment Score: 80+
- ✅ Funnel Completion: 95-100%
- ✅ All 4 BANT elements addressed
- ✅ 3+ objections handled successfully
- ✅ 5+ personalization mentions
- ✅ High urgency creation
- ✅ Clear value articulation
- ✅ Enthusiastic tone
- ✅ Details confirmed at end

---

## Quick Diagnostic Decision Tree

```
Call Ended
    ↓
Is Commitment Score > 70?
    YES → Is Conversion Score > 70?
        YES → Is Excellence Score > 60?
            YES → 🎉 Great call! Standard follow-up
            NO → ⚡ Good result, but improve execution
        NO → ⚠️ Commitment without process = risky
    NO → Is Conversion Score > 70?
        YES → 🤔 Good process, but user not committed = re-engage
        NO → 🚨 Poor call overall = urgent intervention
```

---

## Training & Improvement Priorities

### If Commitment Score is Low:
1. Use more definitive language
2. Create urgency
3. Confirm user understanding
4. Get micro-commitments
5. Address objections immediately

### If Conversion Score is Low:
1. Follow all funnel stages
2. Ask BANT questions
3. Don't skip value presentation
4. Always ask for appointment
5. Confirm details at end

### If Excellence Score is Low:
1. Personalize more (use "you", caller's situation)
2. Show enthusiasm
3. Be clearer in explanations
4. Create time pressure
5. Focus on benefits, not features

---

## API Response Field Mapping

When querying `/api/crm/analytics/call/{call_id}`:

```json
{
  "aggregated_scores": {
    "commitment_score": 75,        // → Commitment Score
    "conversion_score": 82,         // → Conversion Score  
    "excellence_score": 68,         // → Excellence Score
    "show_up_probability": 78,     // → Show-Up %
    "risk_level": "low",           // → Risk Level
    "overall_quality_score": 75    // → Overall Quality
  }
}
```

---

**Quick Reference Card Version 1.0**  
**Last Updated**: November 21, 2025
