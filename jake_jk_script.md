# JK First Caller Agent - Complete Script

**Agent Name:** JK First Caller-copy  
**Agent ID:** b6b1d141-75a2-43d8-80b8-3decae5c0a92  
**Total Nodes in Flow:** 51  
**Script Path (Compliant):** 10 nodes  

---

## Overview

This document contains the conversation script for the JK First Caller agent following the **compliant path** (happy path where the prospect responds positively). The agent uses a mix of scripted responses and AI-powered dynamic responses based on conversation context.

---

## 1. Greeting

**[Script Mode]**

```
{{customer_name}}?
```

*Goal: Say the customer's name*

**Expected Response:** Customer confirms their name (e.g., "Yes", "Speaking", "This is he/she")

---

## 2. Node Prompt: N001B_IntroAndHelpRequest_Only (V3 - Follows Name Confirmation)

**[Prompt Mode - AI Dynamic Response]**

**Goal:** Ask them if they could help you out.

**Context:** This is a pattern interrupt. The AI will dynamically ask the customer if they can "help you out" - creating curiosity and engagement.

---

## 3. Node ID: N_Opener_StackingIncomeHook_V3_CreativeTactic

**[Script Mode]**

```
Well, uh... I don't know if you could yet, but, I'm calling because you filled out 
an ad about stacking income without stacking hours. 

I know this call is out of the blue, but do you have just 25 seconds for me to 
explain why I'm reaching out today specifically?
```

**Key Elements:**
- Acknowledges the form fill
- Creates urgency with "25 seconds"
- Low commitment ask
- Uses SSML tags for natural pauses and pacing

---

## 4. N_IntroduceModel_And_AskQuestions_V3_Adaptive

**[Prompt Mode - AI Dynamic Response]**

**Goal:** To deliver a concise, high-level summary of the business model and then proactively ask an open-ended question to surface the user's initial thoughts or concerns.

**What the AI Does:**
- Explains the income stacking model at a high level
- Asks an open-ended question to gauge interest
- Surfaces any objections or concerns early

---

## 5. N_KB_Q&A_With_StrategicNarrative_V3_Adaptive

**[Prompt Mode - AI Dynamic Response]**

**Goal:** To dynamically answer the user's questions using the `qualifier setter` KB, ensure the core income potential has been discussed, and then deliver the "$20k" value-framing question. 

**Must Achieve:** Get a response from them that has the pattern of them wanting to have extra money or not being upset about having extra money.

**Compliant Responses:**
- "Yeah I'd love some extra money"
- "No I wouldn't be against it"
- "Who would be?" (rhetorical agreement)

**Non-Compliant:** "Depends", "I don't know" - the AI must persist to get them to establish they want extra money.

**Key Question:** "Would an extra $20,000 a year upset you?"

---

## 6. N200_Super_WorkAndIncomeBackground_V3_Adaptive

**[Prompt Mode - AI Dynamic Response]**

**Goal:** To leverage a positive interaction with an upbeat tone and determine the user's employment status (employee vs. owner).

**What the AI Asks:**
- Are you currently employed?
- Do you own a business?

**Purpose:** Qualification - determines which path to follow next

---

## 7. N201A_Employed_AskYearlyIncome_V8_Adaptive

**[Prompt Mode - AI Dynamic Response]**

**Goal:** To efficiently and professionally ask {{customer_name}} for their approximate current yearly income, and to overcome any refusal by framing the question as a critical qualification step for a valuable opportunity.

**What the AI Does:**
- Asks for approximate yearly income
- If they refuse, reframes it as necessary for qualification
- Positions it as protecting the prospect's time

**Expected Answer:** Annual income range (e.g., "$45,000", "around $60k")

---

## 8. N201B_Employed_AskSideHustle_V4_FullyTuned

**[Prompt Mode - AI Dynamic Response]**

**Goal:** To smoothly and efficiently ask {{customer_name}} if they have had any side hustles or other income sources in the last two years.

**What the AI Asks:**
- Have you had any side hustles in the last 2 years?
- Any other income sources?

**Purpose:** Establishes entrepreneurial experience and additional income context

---

## 9. N201C_Employed_AskSideHustleAmount_V3_FullyTuned

**[Prompt Mode - AI Dynamic Response]**

**Goal:** To positively acknowledge the user's side hustle and then efficiently ask for the approximate monthly income it generated.

**What the AI Does:**
- Acknowledges their side hustle positively
- Asks for monthly income from that source

**Expected Answer:** Monthly income amount (e.g., "$500/month", "around a thousand")

---

## 10. N201D_Employed_AskVehicleQ_V5_Adaptive

**[Prompt Mode - AI Dynamic Response]**

**Goal:** To ask {{customer_name}} the "Vehicle Question" with a confident, solution-oriented tone, gauging if they can envision this model as a way to generate income comparable to or exceeding their current earnings.

**The Vehicle Question:** Can you see using this model to generate income comparable to or exceeding what you currently make?

**Uses Variable:** [Amount_Reference] - calculated from their stated income

**Purpose:** Final qualification - do they see themselves succeeding with this model?

---

## Script Analysis

### Total Conversation Flow:
1. ✅ Name confirmation
2. ✅ Pattern interrupt ("help me out")
3. ✅ Permission to pitch (25 seconds)
4. ✅ Model introduction
5. ✅ Q&A with $20k value frame
6. ✅ Employment status
7. ✅ Current income qualification
8. ✅ Side hustle history
9. ✅ Side hustle income
10. ✅ Vehicle question (vision close)

### Key Features:
- **Hybrid Approach:** Mix of scripted and AI-powered responses
- **Progressive Qualification:** Each node gathers more qualifying information
- **Compliance Building:** Starts with small yeses, builds to bigger commitments
- **Value Framing:** "$20k extra" positions the opportunity
- **Natural Flow:** AI handles objections and questions dynamically

### Variables Extracted:
- `customer_name` - prospect's name
- `yearly_income` - current annual income
- `side_hustle_income` - monthly side hustle earnings
- `[Amount_Reference]` - calculated comparison amount

---

## Notes

This is the **compliant path** - the happy path where the prospect says "yes" at each stage. The actual agent has **51 total nodes** handling objections, wrong numbers, callbacks, and other branches.

The script is designed for a cold call converting leads who filled out a form about "stacking income without stacking hours" - likely a business opportunity or coaching offer.
