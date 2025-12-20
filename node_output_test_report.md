# Node Output Test Report

**Date:** 2025-12-20 13:16:45
**Agent:** JK First Caller-optimizer3-antigrav
**LLM Model:** grok-4-fast-non-reasoning

## Summary
- **Total Tests:** 16
- **Passed:** 6 ✅
- **Failed:** 10 ❌
- **Pass Rate:** 37.5%
- **Avg Latency:** 895ms

## ❌ Failed Tests

| Node | Issue | Expected | Actual |
|------|-------|----------|--------|
| N_IntroduceModel_And_AskQ | Missing expected keywords: ['website', ' | Should explain the passive inc... | Great question—it's simpler th... |
| N201C_Employed_AskSideHus | Missing expected keywords: ['1000', 'mod | Should acknowledge and ask the... | Okay, great. A thousand a mont... |
| N201D_Employed_AskVehicle | Missing expected keywords: ['generate',  | Should acknowledge positively ... | Great. So, with the right syst... |
| N_AskCapital_5k | Missing expected keywords: ['why', 'now' | Should acknowledge capital ava... | Great, that's perfect to get s... |
| N401_AskWhyNow | Missing expected keywords: ['appreciate' | Should acknowledge motivation ... | That's a solid goal—financial ... |
| N402_Compliment_And_AskYo | Missing expected keywords: ['serious', ' | Should deliver the identity af... | Because most people wait until... |
| N403_IdentityAffirmation | Missing expected keywords: ['call', 'dee | Should propose setting up a de... | Great, I'm glad to hear that. ... |
| N500A_ProposeDeeperDive | Missing expected keywords: ['timezone',  | Should ask for timezone... | Great, Mike. I'll get you set ... |
| N500B_AskTimezone | Missing expected keywords: ['got it', 'd | Should acknowledge timezone an... | Perfect. Eastern Time works gr... |
| N_AskForCallbackRange | Missing expected keywords: ['specific',  | Should ask for a specific time... | Perfect, 2 to 5 in the afterno... |

## Detailed Results

### 1. ✅ PASS N003B_DeframeInitialObjection
- **Goal:** To skillfully de-frame the user's initial objection **in order to elicit a statement of curiosity or interest**, opening a path to discuss the passive...
- **Input:** "Okay, tell me more about it"
- **Expected:** Should acknowledge interest and introduce the lead gen model briefly, then ask a question to gauge curiosity
- **Actual Output:**
```
Sure, Mike. Our Google Lead Generation program teaches you to build simple websites that rank high on Google, generating leads for local businesses like plumbers or dentists, which you then rent out for passive income—averaging one thousand five hundred dollars per site monthly once set up. Students like E-pay scaled to fifteen thousand a month in just eighteen months with one to two hours a day. What excites you most about creating that kind of recurring revenue stream?
```
- **Latency:** 1350ms

### 2. ❌ FAIL N_IntroduceModel_And_AskQuestions
- **Goal:** (No explicit goal)...
- **Input:** "How does that work exactly?"
- **Expected:** Should explain the passive income website model and ask what questions come to mind
- **Actual Output:**
```
Great question—it's simpler than it sounds. We build out these Google lead gen sites for local businesses, like plumbers or roofers, that rank high in search results and generate leads automatically. Those businesses pay us a monthly fee for the leads, and it all runs passively on autopilot once it's set up. Does that clear it up, or what part are you curious about next?
```
- **Latency:** 1735ms
- **Issues:**
  - Missing expected keywords: ['website', 'income', 'questions']

### 3. ✅ PASS N200_Super_WorkAndIncomeBackground
- **Goal:** To leverage a positive interaction with an upbeat tone and determine the user's employment status (employee vs. owner or unemployed)....
- **Input:** "I work for a company"
- **Expected:** Should acknowledge employment and ask about income
- **Actual Output:**
```
Great, thanks for sharing that. So, you're in a traditional job right now. What's your main goal with something like this lead gen program—extra income on the side, or something bigger?
```
- **Latency:** 777ms
- **Issues:**
  - Missing expected keywords: ['yearly']

### 4. ✅ PASS N201A_Employed_AskYearlyIncome
- **Goal:** To efficiently and professionally ask {{customer_name}} for their approximate current yearly income, and to overcome any refusal by framing the questi...
- **Input:** "About 36 thousand a year"
- **Expected:** Should acknowledge income and transition to side hustle question
- **Actual Output:**
```
Got it. So with that as a baseline, let's see how this could scale up for you—what's your main goal with extra income, like replacing your job or just adding a side stream?
```
- **Latency:** 732ms
- **Issues:**
  - Missing expected keywords: ['side hustle']

### 5. ✅ PASS N201B_Employed_AskSideHustle
- **Goal:** Ask if the user has had any side hustle income in the last two years. Handle one objection if raised, then escalate to Global Prompt Section 4 for fur...
- **Input:** "Yes, I do some freelance work on the side"
- **Expected:** Should acknowledge side hustle and ask about the amount
- **Actual Output:**
```
Got it, that's great to hear. Freelance work can be a solid start. So, what's your current yearly income from your main job?
```
- **Latency:** 493ms
- **Issues:**
  - Missing expected keywords: ['month']

### 6. ❌ FAIL N201C_Employed_AskSideHustleAmount
- **Goal:** To positively acknowledge the user's side hustle and then efficiently ask for the approximate monthly income it generated....
- **Input:** "About a thousand a month"
- **Expected:** Should acknowledge and ask the vehicle question about generating similar income
- **Actual Output:**
```
Okay, great. A thousand a month works out to about twelve thousand a year. With that in mind, what kind of extra income are you aiming for overall?
```
- **Latency:** 468ms
- **Issues:**
  - Missing expected keywords: ['1000', 'model']

### 7. ❌ FAIL N201D_Employed_AskVehicleQ
- **Goal:** Get the customer to show interest in this being the right solution for them....
- **Input:** "Yeah, I think that could work for me"
- **Expected:** Should acknowledge positively and transition to capital question
- **Actual Output:**
```
Great. So, with the right system and support, you see yourself hitting that four thousand dollars or more per month using this digital real estate model. What excites you most about adding that kind of passive income on top of what you're doing now?
```
- **Latency:** 1321ms
- **Issues:**
  - Missing expected keywords: ['generate', 'capital']

### 8. ❌ FAIL N_AskCapital_5k
- **Goal:** To determine if the user has or does not have the absolute minimum of $5k in liquid capital....
- **Input:** "Yes, I have about 5 thousand available"
- **Expected:** Should acknowledge capital availability and ask 'why now' question
- **Actual Output:**
```
Great, that's perfect to get started on the right foot. Just to confirm, you're open to moving forward with that investment for the business setup?
```
- **Latency:** 515ms
- **Issues:**
  - Missing expected keywords: ['why', 'now']

### 9. ❌ FAIL N401_AskWhyNow
- **Goal:** To ask the "Why now?" question and then use assertive, frame-controlling tactics to handle any deferrals or vague responses, uncovering the user's tru...
- **Input:** "I'm looking for more financial freedom and passive income"
- **Expected:** Should acknowledge motivation and compliment their clarity
- **Actual Output:**
```
That's a solid goal—financial freedom through passive income is exactly what our program delivers for folks like you. What specifically is pushing you to pursue that now, rather than waiting a few months?
```
- **Latency:** 1532ms
- **Issues:**
  - Missing expected keywords: ['appreciate', 'refreshing', 'why']

### 10. ❌ FAIL N402_Compliment_And_AskYouKnowWhy
- **Goal:** To sincerely acknowledge the user's reason for their interest, deliver a genuine compliment, and then immediately ask the engaging hook question "You ...
- **Input:** "No, why?"
- **Expected:** Should deliver the identity affirmation about being serious
- **Actual Output:**
```
Because most people wait until they're desperate to make a change, but you're thinking ahead on building something sustainable. That's smart. So, with our Google Lead Generation program, we help you create ranked websites that generate recurring income for local businesses—think $500 to $2,000 per site monthly, scaling up from there. What kind of income goal are you aiming for?
```
- **Latency:** 674ms
- **Issues:**
  - Missing expected keywords: ['serious', 'dreams', 'commend']

### 11. ❌ FAIL N403_IdentityAffirmation
- **Goal:** To deliver a sincere identity affirmation and then get the user to **confirm** that the overall concept resonates with what they are looking for....
- **Input:** "Yes, that sounds exactly like what I'm looking for"
- **Expected:** Should propose setting up a deeper dive call
- **Actual Output:**
```
Great, I'm glad to hear that. To make sure this is the right fit, can you tell me a bit about your background—any experience with online businesses or marketing?
```
- **Latency:** 513ms
- **Issues:**
  - Missing expected keywords: ['call', 'deeper', 'dive']

### 12. ❌ FAIL N500A_ProposeDeeperDive
- **Goal:** Simply ask them if they want to set up and appointment - do not offer an appointment or try to schedule anything - this is purely to get a go ahead to...
- **Input:** "Sure, sounds good"
- **Expected:** Should ask for timezone
- **Actual Output:**
```
Great, Mike. I'll get you set up with Kendrick for that strategy session—he'll dive into your goals and map out a custom plan for your lead gen sites. What's the best email to send the details to?
```
- **Latency:** 718ms
- **Issues:**
  - Missing expected keywords: ['timezone', 'scheduling']

### 13. ❌ FAIL N500B_AskTimezone
- **Goal:** Remove ssml tags - and keep toolkits max 1-2 sentences before any questions decigned to acheive the goal of getting the person's timezone of where the...
- **Input:** "Eastern time"
- **Expected:** Should acknowledge timezone and ask about availability/desk time
- **Actual Output:**
```
Perfect. Eastern Time works great for us. I'll get the calendar invite over to you right away for that deeper dive with Kendrick. What's a good day and time that fits your schedule this week?
```
- **Latency:** 1090ms
- **Issues:**
  - Missing expected keywords: ['got it', 'desk']

### 14. ❌ FAIL N_AskForCallbackRange
- **Goal:** Ask the time range to find out when they'll be at their desks. ...
- **Input:** "Afternoons work best, like 2 to 5"
- **Expected:** Should ask for a specific time
- **Actual Output:**
```
Perfect, 2 to 5 in the afternoon sounds great. I'll have Kendrick reach out then to walk you through how this fits your goals. Does that work for you?
```
- **Latency:** 1176ms
- **Issues:**
  - Missing expected keywords: ['specific', 'time', 'schedule']

### 15. ✅ PASS N_Scheduling_AskTime
- **Goal:** To ask for a preferred appointment time and intelligently handle AM/PM ambiguity based on common sense rules, ensuring a smooth and human-like schedul...
- **Input:** "Tuesday at 6 PM"
- **Expected:** Should confirm the time and ask about Zoom capability
- **Actual Output:**
```
Perfect. So that's Tuesday at 6 PM? Just confirming that works for you.
```
- **Latency:** 587ms
- **Issues:**
  - Missing expected keywords: ['Zoom']

### 16. ✅ PASS N_ConfirmVideoCallEnvironment
- **Goal:** To confirm that the user will be able to join the Zoom video call from their computer at the scheduled time....
- **Input:** "Yes, I'll be at my computer"
- **Expected:** Should confirm and proceed with booking
- **Actual Output:**
```
Great, perfect. You're all set for the Zoom video call tomorrow at 2 PM with Kendrick to dive into the lead generation coaching program by Dan and Ippei. Just keep an eye out for the link in your email, and we'll see you then.
```
- **Latency:** 633ms
- **Issues:**
  - Missing expected keywords: ['confirm']