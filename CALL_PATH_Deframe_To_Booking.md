# Call Flow Path: Deframe Objection → Booked Appointment

**Customer Profile:**
- **Employment:** Employee (w/ side hustle)
- **Main Job Income:** $3,000/month ($36,000/year)
- **Side Hustle Income:** $1,000/month ($12,000/year)
- **Total Yearly Income:** $48,000 (`employed_yearly_income` + `side_hustle`)
- **Amount Reference:** $4,000/month (48k ÷ 12)
- **Liquid Capital Available:** $5,000 ✅

---

## 🗺️ Path Overview

```
[6] Deframe Objection
    ↓ (curiosity/interest shown)
[9] Introduce Model & Ask Questions
    ↓ (agrees to hear more)
[13] N200 - Work & Income Background
    ↓ (indicates employed)
[14] N201A - Ask Yearly Income  ➡️  Extract: employed_yearly_income = $36,000
    ↓ (provides income)
[17] N201B - Ask Side Hustle
    ↓ (says YES has side hustle)
[18] N201C - Ask Side Hustle Amount  ➡️  Extract: side_hustle = $12,000
    ↓ (provides amount)
[19] N201D - Vehicle Question (Employed)
    ↓ (affirms potential)
[20] Logic Split - Income  ➡️  Routes to $5k capital path
    ↓
[29] N_AskCapital_5k  ➡️  Ask for $5k capital
    ↓ (says YES has $5k)
[28] N401 - Ask Why Now
    ↓ (shares motivation)
[33] N402 - Compliment & "You Know Why?"
    ↓ (any response)
[34] N403 - Identity Affirmation & Value Fit
    ↓ (confirms value fit)
[35] N500A - Propose Deeper Dive
    ↓ (agrees to schedule)
[36] N500B - Ask Timezone  ➡️  Extract: timeZone
    ↓ (provides timezone)
[37] Ask Callback Range  ➡️  Extract: callbackrange
    ↓ (provides range)
[38] Schedule Time  ➡️  Extract: scheduleTime, amPm
    ↓ (provides specific time)
[39] Confirm Video Call Environment
    ↓ (confirms Zoom capability)
[40] Time-Converter (Webhook)
    ↓
[41] Calendar-Check (Webhook)
    ↓ (time available)
[45] Set Confirmation Frame
    ↓
[51-57] Reminder & Confirmation Sequence
    ↓
[58-60] Video Assignment
    ↓
[62] End Call - Final
```

---

## 📍 Detailed Node-by-Node Path

### Step 1: [6] N003B_DeframeInitialObjection_V7_GoalOriented
**Goal:** De-frame user's initial objection to elicit curiosity or interest

**Agent Strategy:**
- Classify DISC style quickly from utterance
- Deploy 1-2 sentence tactic adapted to their style
- Ask one-sided question to spark curiosity

**Customer Response Needed:** Curiosity or interest statement
- Examples: "Tell me more", "How does it work?", "Okay", "Maybe"

**Transition → [9]** when interest/curiosity detected

---

### Step 2: [9] N_IntroduceModel_And_AskQuestions_V3_Adaptive
**Goal:** Introduce the passive income model and gauge interest

**Script:**
> "Okay, in a nutshell, we set up passive income websites, and we let them produce income for you. What questions come to mind as soon as you hear something like that?"

**Customer Response Needed:** Questions or acknowledgment

**Transition → [13]** after addressing questions

---

### Step 3: [13] N200_Super_WorkAndIncomeBackground_V3_Adaptive
**Goal:** Determine employment status (employee vs. business owner vs. unemployed)

**Script:**
> "Alright, love that! So, are you working for someone right now or do you run your own business?"

**Customer Response Needed:** "I work for someone" / "I have a job"

**Transition → [14]** (Employee path)

---

### Step 4: [14] N201A_Employed_AskYearlyIncome_V8_Adaptive
**Goal:** Get approximate yearly income

**Script:**
> "Got it. And what's that job producing for you yearly, approximately?"

**Customer Response:** "$36k" / "About $3,000 a month"

**Variables Extracted:**
- `employed_yearly_income` = 36000
- `amount_reference` = 3000 (36k ÷ 12)

**Transition → [17]** after income disclosed

---

### Step 5: [17] N201B_Employed_AskSideHustle_V4_FullyTuned
**Goal:** Ask about side hustle income

**Script:**
> "And in the last two years, did you happen to have any kind of side hustle or anything else bringing in income?"

**Customer Response:** "Yes, I do some freelance work on the side"

**Transition → [18]** (YES to side hustle)

---

### Step 6: [18] N201C_Employed_AskSideHustleAmount_V3_FullyTuned
**Goal:** Get side hustle income amount

**Script:**
> "Okay, great. And what was that side hustle bringing in for you, say, on a good month?"

**Customer Response:** "About $1,000 a month"

**Variables Extracted:**
- `side_hustle` = 12000 ($1k × 12)
- `amount_reference` = 4000 ((36k + 12k) ÷ 12)

**Transition → [19]** after amount provided

---

### Step 7: [19] N201D_Employed_AskVehicleQ_V5_Adaptive
**Goal:** Get customer to affirm belief in generating $4,000+/month with this model

**Script:**
> "Got it. So, do you see yourself being able to generate at least that same kind of amount you're making, say four thousand dollars, or even more, using a vehicle like this digital real estate model if you had the right system and support?"

**Customer Response Needed:** Affirmative response
- "Yes", "I think so", "That would be great"

**Variables Extracted:**
- `has_discussed_income_potential` = true

**Transition → [20]** on affirmative response

---

### Step 8: [20] Logic Split - Income
**Logic:** Routes based on yearly income
- Income > $75k → N_AskCapital_15k (asks for $15-25k)
- Income ≤ $75k → N_AskCapital_5k (asks for $5k)

**With $48k total income → Routes to [29] N_AskCapital_5k**

---

### Step 9: [29] N_AskCapital_5k_V1_Adaptive
**Goal:** Confirm $5k liquid capital available

**Script:**
> "For this model, we typically look for about five thousand dollars in liquid capital to get started. Would that be accessible for you?"

**Customer Response:** "Yes, I have that" ✅

**Transition → [28]** (capital confirmed)

---

### Step 10: [28] N401_AskWhyNow_Initial_V10_AssertiveFrame
**Goal:** Uncover motivation for change

**Script:**
> "Okay. Just to understand a bit better, is there a specific reason you're looking to make a change or explore something like this right now, as opposed to say, six months from now?"

**Customer Response:** Shares motivation (freedom, extra income, etc.)

**Transition → [33]** on motivation shared

---

### Step 11: [33] N402_Compliment_And_AskYouKnowWhy_V5_FullyTuned
**Goal:** Acknowledge motivation and build curiosity

**Script:**
> "Okay, I appreciate you sharing that. I have to say, that's actually refreshing to hear. You know why?"

**Customer Response:** Any response (e.g., "Why?", "No")

**Transition → [34]**

---

### Step 12: [34] N403_IdentityAffirmation_And_ValueFitQuestion_V8_GoalAligned
**Goal:** Affirm their ambition and confirm value fit

**Script:**
> "Well, let me tell you. I sometimes talk to people that clearly will never give themselves permission to go after their dreams. But you're the type of person that is serious and ready to get started, and I commend you for that. So, does this sound like something that could fit what you're after?"

**Customer Response Needed:** Affirmative value confirmation
- "Yes", "That's exactly what I'm looking for"

**Transition → [35]** on value confirmation

---

### Step 13: [35] N500A_ProposeDeeperDive_V5_Adaptive
**Goal:** Get consent to schedule appointment (NOT scheduling yet)

**Script:**
> "Okay, that's excellent. I definitely feel like we can help you with that. What we need to do is set up another call that'll be a deeper dive into your situation. Sound good?"

**Customer Response:** "Yes" / "Sure" / "Sounds good"

**Transition → [36]** on agreement

---

### Step 14: [36] N500B_AskTimezone_V2_FullyTuned
**Goal:** Get timezone for accurate scheduling

**Script:**
> "Gotcha. And just so I've got it right for our scheduling, what timezone are you in?"

**Customer Response:** "Eastern" / "PST" / etc.

**Variables Extracted:**
- `timeZone` = "EST" (or provided value)

**Transition → [37]**

---

### Step 15: [37] N_AskForCallbackRange_V1_Adaptive
**Goal:** Get typical available time range

**Script:**
> "Okay. And when are you typically back at your desk during the day. What's a good time range for you?"

**Customer Response:** "Afternoons work best" / "Between 2 and 5"

**Variables Extracted:**
- `callbackrange` = "2pm-5pm" (or provided range)

**Transition → [38]**

---

### Step 16: [38] N_Scheduling_AskTime_V2_SmartAmbiguity
**Goal:** Lock in specific date and time

**Script:**
> "Okay, great! And when would be a good time for us to schedule that call?"

**Customer Response:** "Tuesday at 6 PM"

**Variables Extracted:**
- `scheduleTime` = "Tuesday 6 PM"
- `amPm` = "PM"

**Transition → [39]**

---

### Step 17: [39] N_ConfirmVideoCallEnvironment_V1_Adaptive
**Goal:** Confirm Zoom video call capability

**Script:**
> "Okay, great. And just to confirm, the meeting is via Zoom, so does that time work for you to join the video call from your computer?"

**Customer Response:** "Yes" / "That works"

**Transition → [40] Time-Converter**

---

### Steps 18-20: Webhook Processing
1. **[40] Time-Converter** - Converts time to standardized format
2. **[41] Calendar-Check** - Verifies availability
3. Routes to rescheduling if needed OR continues to confirmation

---

### Steps 21-25: Confirmation & Video Assignment
1. **[45] Set Confirmation Frame** - Confirms appointment
2. **[51-57] Reminder Sequence** - Sets up reminder, confirms text receipt
3. **[58-60] Video Assignment** - Assigns pre-call video
4. **[62] End Call** - Final closing

---

## 📊 Variables Collected Along Path

| Variable | Value | Collected At |
|----------|-------|--------------|
| `employed_yearly_income` | 36000 | Node 14 |
| `side_hustle` | 12000 | Node 18 |
| `amount_reference` | 4000 | Node 18 (calculated) |
| `has_discussed_income_potential` | true | Node 19 |
| `timeZone` | (customer provides) | Node 36 |
| `callbackrange` | (customer provides) | Node 37 |
| `scheduleTime` | (customer provides) | Node 38 |
| `amPm` | PM | Node 38 |

---

## 🎯 Key Transition Points

1. **Objection → Interest**: Deframe must elicit curiosity
2. **Employment Classification**: Routes to correct income path
3. **Capital Qualification**: $5k available = continues
4. **Why Now**: Must share genuine motivation
5. **Value Fit**: Must confirm this fits their goals
6. **Scheduling Consent**: Must agree BEFORE asking details
7. **Time Specifics**: Day + Time + AM/PM required
8. **Zoom Confirmation**: Must be at computer

---

## ⚠️ Potential Exit Points

- **[4] Wrong Number** - Wrong person
- **[31] Financially Not Qualified** - No capital, no credit
- **[32] End Call Request** - User wants to end call
- **Reschedule flows** - If calendar conflict
