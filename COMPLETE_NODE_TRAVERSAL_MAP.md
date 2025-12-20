# Complete Node Traversal Map

This document outlines the specific conversation paths required to trigger **every single node** in the Agent's flow (67 Nodes). By executing these 5 scenarios, you will verify 100% of the logic graph.

## 🟢 Scenario A: The "Happy Path" (Standard Booking + Video)
**Goal:** Verify the core sales flow, scheduling, and post-call video assignment.
**Nodes Covered:** ~40%
**Path:**
1.  **Greeting:** "Yes, this is [Name]."
2.  **Intro:** "Sure, what's this about?"
3.  **Opener:** "That sounds interesting."
4.  **Model:** "How does it work?" -> "I work in [Field]."
5.  **Q&A/Narrative:** "What about cost?" -> "ROI?" -> "I have capital."
6.  **Background:** "I run my own business." -> "I have savings."
7.  **Scheduling:** "Tuesday at 2pm."
8.  **Confirmation:** "Yes, I can make that."
9.  **Video Assignment:** "I'll watch the video." -> "Yes, I see the value." -> "I commit to watching it."
10. **End Call:** "Goodbye."

## 🔴 Scenario B: Disqualification & Early Exits
**Goal:** Verify "Gatekeeper" logic and polite rejection nodes.
**Nodes Covered:** ~20%
**Branches:**
1.  **Wrong Number:**
    -   **Start:** Greeting -> "Wrong number."
    -   **Node:** `N_WrongNumber_Exit`.
2.  **Not Interested (Early):**
    -   **Start:** Opener -> "Not interested."
    -   **Node:** `N_Objection_NotInterested` -> `N_EndCall`.
3.  **Financial Disqualification:**
    -   **Start:** Background -> "I have no savings" -> "I have no access to capital."
    -   **Node:** `N_Disqualified_Financial` -> Polite Exit.
4.  **Employment Disqualification:**
    -   **Start:** Background -> "I am unemployed."
    -   **Node:** `N_Disqualified_Unemployed` -> Polite Exit.

## 🟡 Scenario C: Resistance & Loop Handling
**Goal:** Verify Objection Handlers, Partner Logic, and Rescheduling.
**Nodes Covered:** ~25%
**Branches:**
1.  **Greeting Resistance:**
    -   **Start:** Greeting -> "I don't believe you."
    -   **Node:** `Greeting_CatchAll_ConfirmName` -> "Yes it's me."
2.  **MLM/Scam Logic:**
    -   **Start:** Intro/Hook -> "Is this MLM?" -> "What are you selling?"
    -   **Node:** `N003B_DeframeInitialObjection`.
3.  **Partner/Spouse Check:**
    -   **Start:** Scheduling -> "I need to check with my wife."
    -   **Node:** `N018_ConfirmPartnerAvailability`.
    -   **Branch 1:** "She's available." -> Proceed.
    -   **Branch 2:** "She's busy then." -> `N_Scheduling_RescheduleAndHandle`.

## 🔵 Scenario D: Shortcuts & Direct Access
**Goal:** Verify Intent Recognition jumps.
**Nodes Covered:** ~10%
**Branches:**
1.  **Appointment Shortcut:**
    -   **Start:** Greeting -> "I want to book an appointment."
    -   **Jump:** Skips Intro/Qual -> Direct to `N_Scheduling_AskTime`.
2.  **Finance Shortcut:**
    -   **Start:** Greeting -> "Let's talk about finances."
    -   **Jump:** Direct to `N200_Super_WorkAndIncomeBackground`.

## 🟣 Scenario E: Tech Edge Cases (Calendar/Voicemail)
**Goal:** Verify backend mechanics.
**Nodes Covered:** ~5%
**Branches:**
1.  **Voicemail:**
    -   **Trigger:** System detects beep/silence at start.
    -   **Node:** `N_Voicemail_Drop`.
2.  **Time Unavailable:**
    -   **Start:** Scheduling -> [Provide Occupied Time].
    -   **Node:** `Calendar-check` (returns False) -> `N_Scheduling_RescheduleAndHandle` ("That time is taken...").
