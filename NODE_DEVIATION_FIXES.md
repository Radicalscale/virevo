# Node Deviation Fixes - Proposed Solutions

**Agent:** JK First Caller-optimizer3-antigrav  
**Date:** 2025-12-20  
**Issue:** 10/16 nodes deviate from expected scripted flow

---

## Summary of Issues

The LLM is **improvising instead of following scripts**. Root causes:
1. Node prompts lack explicit "MUST SAY" constraints
2. Transition triggers aren't enforced in the prompt
3. Agent skips ahead instead of executing one node at a time

---

## Fix 1: N201C_Employed_AskSideHustleAmount

**Current Problem:** After getting side hustle amount, agent asks general questions instead of transitioning to Vehicle Question.

**Current Output:**
> "Okay, great. A thousand a month works out to about twelve thousand a year. With that in mind, what kind of extra income are you aiming for overall?"

**Expected Output:**
> "Okay, great. And what was that side hustle bringing in for you, say, on a good month?" → Then transition to vehicle question.

### Proposed Fix

Add explicit exit instruction to content:

```diff
## Core Logic
1. Deliver opening exactly: Okay, great. And what was that side hustle bringing in for you, say, on a good month?
2. Listen to user response.
3. If response provides clear income amount:
   - Extract monthly amount.
   - Convert to yearly (e.g., five hundred per month = six thousand per year).
   - Set state: {{side_hustle}} = yearly amount.
-  - Escalate to Global Prompt's Reframe & Drive Engine.
+  - **STOP. DO NOT ASK ANOTHER QUESTION. Exit this node immediately.**
```

---

## Fix 2: N201D_Employed_AskVehicleQ

**Current Problem:** Agent doesn't transition to capital question after positive response.

**Current Output:**
> "Great. So, with the right system and support, you see yourself hitting that four thousand dollars or more per month using this digital real estate model. What excites you most about adding that kind of passive income on top of what you're doing now?"

**Expected:** Should transition to capital question (N_AskCapital_5k).

### Proposed Fix

Add explicit transition enforcement:

```diff
## Core Logic
1. **Start Happy Path:** If loop_count=0, deliver opening.
   Agent says: Got it. So, do you see yourself being able to generate at least that same kind of amount...
+
+## CRITICAL EXIT RULE
+**When user responds affirmatively (yes, yeah, I think so, that could work):**
+- DO NOT ask follow-up questions
+- DO NOT ask what excites them
+- IMMEDIATELY end response
+- Next node will handle capital question
```

---

## Fix 3: N_AskCapital_5k

**Current Problem:** After capital confirmed, agent doesn't transition to "why now" question.

**Current Output:**
> "Great, that's perfect to get started on the right foot. Just to confirm, you're open to moving forward with that investment for the business setup?"

**Expected:** Should transition to N401_AskWhyNow.

### Proposed Fix

```diff
## INSTRUCTION: BRIDGE & PIVOT
1. **BRIDGE:** Acknowledge the user's previous input naturally.
2. **THE PIVOT:** Transition to the capital requirement.
3. **REQUIRED STATEMENT:** You MUST state "for this model, we typically look for about five thousand dollars in liquid capital to get started."
4. **GOAL:** Ask if they have that amount accessible.

+## EXIT RULE (MANDATORY)
+**When user confirms they have $5k (Yes, I do, I have that):**
+- Say ONLY: "Perfect. That's exactly what we look for."
+- DO NOT ask about investment or moving forward
+- DO NOT ask additional questions
+- END YOUR RESPONSE HERE
```

---

## Fix 4: N401_AskWhyNow

**Current Problem:** Agent doesn't deliver the compliment language from the script.

**Current Output:**
> "That's a solid goal—financial freedom through passive income is exactly what our program delivers for folks like you."

**Expected:** Should include "I appreciate" and transition to "You know why?" hook.

### Proposed Fix

```diff
## Core Logic
1. **Opening Gambit (If Starting Fresh):**
   - Deliver exactly: "Okay. Just to understand a bit better, is there a specific reason you're looking to make a change..."

+## RESPONSE TO MOTIVATION (MANDATORY SCRIPT)
+**When user shares genuine motivation (freedom, income, change):**
+Agent MUST say EXACTLY:
+"Okay, I appreciate you sharing that. I have to say, that's actually refreshing to hear. You know why?"
+
+- DO NOT paraphrase this
+- DO NOT add additional commentary
+- DO NOT explain the program
+- SAY EXACTLY THE SCRIPT ABOVE
```

---

## Fix 5: N402_Compliment_And_AskYouKnowWhy

**Current Problem:** Agent improvises instead of using the exact identity affirmation script.

**Current Output:**
> "Because most people wait until they're desperate to make a change..."

**Expected:** Use exact script about "dreams" and "commend".

### Proposed Fix

```diff
## Core Logic
-1. **Deliver Response:** Say exactly: "Okay, I appreciate you sharing that. I have to say, that's actually refreshing to hear. You know why?"
+1. **This node activates AFTER the "You know why?" was delivered in previous node**
+
+## MANDATORY RESPONSE (NO IMPROVISATION)
+Agent MUST say EXACTLY:
+"Well, let me tell you. I sometimes talk to people that clearly will never give themselves permission to go after their dreams. But you're the type of person that is serious and ready to get started, and I commend you for that. So, does this sound like something that could fit what you're after?"
+
+- Use this EXACT wording
+- DO NOT paraphrase
+- DO NOT add explanation about the program here
```

---

## Fix 6: N403_IdentityAffirmation

**Current Problem:** Agent asks about background instead of proposing the deeper dive call.

**Current Output:**
> "Great, I'm glad to hear that. To make sure this is the right fit, can you tell me a bit about your background—any experience with online businesses or marketing?"

**Expected:** Propose setting up deeper dive call.

### Proposed Fix

```diff
## Core Logic
-1. **Deliver Opening if Fresh:** If no prior response, use Opening Gambit.
+## MANDATORY EXIT SCRIPT
+**When user confirms value fit (yes, that's what I'm looking for, sounds good):**
+
+Agent MUST say:
+"That's excellent. I definitely feel like we can help you with that. What we need to do is set up another call that'll be a deeper dive into your situation. Sound good?"
+
+- DO NOT ask about their background
+- DO NOT ask qualifying questions
+- GO DIRECTLY TO PROPOSING THE CALL
```

---

## Fix 7: N500A_ProposeDeeperDive

**Current Problem:** Agent jumps to email instead of asking for timezone.

**Current Output:**
> "Great, Mike. I'll get you set up with Kendrick for that strategy session—he'll dive into your goals and map out a custom plan for your lead gen sites. What's the best email to send the details to?"

**Expected:** Ask for timezone first.

### Proposed Fix

```diff
## Core Logic
1. **Opening Gambit (If Fresh Start):** Deliver exactly.
   - Agent says: "Okay, that's excellent. I definitely feel like we can help you with that. What we need to do is set up another call that'll be a deeper dive into your situation. Sound good?"

+## NEXT STEP AFTER AGREEMENT (MANDATORY)
+**When user agrees (sure, sounds good, yes):**
+
+Agent MUST say EXACTLY:
+"Great. And just so I've got it right for our scheduling, what timezone are you in?"
+
+- DO NOT mention email
+- DO NOT mention Kendrick yet
+- DO NOT provide any other details
+- ASK ONLY ABOUT TIMEZONE
```

---

## Fix 8: N500B_AskTimezone

**Current Problem:** Agent jumps to scheduling instead of asking about desk availability.

**Current Output:**
> "Perfect. Eastern Time works great for us. I'll get the calendar invite over to you right away for that deeper dive with Kendrick. What's a good day and time that fits your schedule this week?"

**Expected:** Ask about when they're at their desk.

### Proposed Fix

```diff
## Core Logic
1. **Initial Query:** Say exactly: "Gotcha. And just so I've got it right for our scheduling, what timezone are you in?"

+## AFTER TIMEZONE RECEIVED (MANDATORY NEXT STEP)
+**When user provides timezone:**
+
+Agent MUST say EXACTLY:
+"Got it. And when are you typically back at your desk during the day? What's a good time range for you?"
+
+- DO NOT mention calendar invite yet
+- DO NOT ask for specific day/time yet
+- ASK ONLY ABOUT DESK TIME RANGE
```

---

## Fix 9: N_AskForCallbackRange

**Current Problem:** Agent accepts range instead of asking for specific time.

**Current Output:**
> "Perfect, 2 to 5 in the afternoon sounds great. I'll have Kendrick reach out then to walk you through how this fits your goals. Does that work for you?"

**Expected:** Ask for specific day and time.

### Proposed Fix

```diff
## Core Logic
- **Step 1: Deliver Opening Gambit** → Say exactly: Okay. And when are you typically back at your desk during the day. What's a good time range for you?

+## AFTER TIME RANGE RECEIVED (MANDATORY)
+**When user provides a range (afternoons, 2-5, mornings):**
+
+Agent MUST say:
+"Okay, great! And when would be a good specific time for us to schedule that call? What day and what time works?"
+
+- DO NOT confirm you'll have Kendrick reach out
+- DO NOT end the scheduling process
+- GET A SPECIFIC DAY AND TIME
```

---

## Fix 10: N_IntroduceModel_And_AskQuestions

**Current Problem:** Agent explains but doesn't use exact script language.

**Current Output:**
> "Great question—it's simpler than it sounds. We build out these Google lead gen sites..."

**Expected:** Use exact script about "passive income websites".

### Proposed Fix

This is a script node, should deliver exactly:

```diff
## Mode: script

-Okay, in a nutshell, we set up passive income websites, and we let them produce income for you. What questions come to mind as soon as you hear something like that?
+**DELIVER EXACTLY (NO MODIFICATION):**
+"Okay, in a nutshell, we set up passive income websites, and we let them produce income for you. What questions come to mind as soon as you hear something like that?"
+
+This is a SCRIPT node. Do not paraphrase or explain further. Deliver this exact line.
```

---

## Implementation Priority

1. **High Priority (Breaks Flow):**
   - N403_IdentityAffirmation - Skips to wrong topic
   - N500A_ProposeDeeperDive - Skips timezone
   - N_AskForCallbackRange - Doesn't get specific time

2. **Medium Priority (Wrong Language):**
   - N401_AskWhyNow - Missing compliment
   - N402_Compliment - Wrong script
   - N201D_VehicleQ - Asks extra questions

3. **Lower Priority (Minor Deviation):**
   - N201C_SideHustleAmount - Slight flow issue
   - N_AskCapital_5k - Extra confirmation
   - N500B_AskTimezone - Jumps ahead slightly

---

## Recommended Global Prompt Addition

Add this to the global prompt to enforce stricter node adherence:

```
## NODE EXECUTION RULES (CRITICAL)
1. Each node has ONE primary goal. Achieve it and STOP.
2. Do NOT ask follow-up questions beyond the node's stated goal.
3. Do NOT explain the program unless the node explicitly says to.
4. When a node says "SAY EXACTLY" - use those exact words, no paraphrasing.
5. After achieving the node goal, END your response. The next node will continue.
6. NEVER skip ahead to future node topics (timezone, scheduling, email) prematurely.
```
