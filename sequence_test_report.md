# Sequence Test Report - Path Integrity Check

**Date:** 2025-12-20 14:59:27
**Agent:** JK First Caller-optimizer3-antigrav

## Summary
- **Total Turns:** 18
- **Sequence Correct:** 7/18
- **Silent Agreements:** 2 ⚠️
- **Skipped Nodes:** 11
- **Turns with Issues:** 8

## ⚠️ Issues Detected

### Turn 1: Greeting
- **User said:** "Yes, this is Mike"
- **Agent said:** "Great, Mike! How can I assist you today?"
- **Issues:**
  - MISSING TOPICS: Expected ['help', 'wondering'], found only 0 matches

### Turn 2: N001B_IntroAndHelpRequest
- **User said:** "Sure, what's up?"
- **Agent said:** "Hey Mike, it's Jake here. I was just wondering if you could help me out for a moment with something quick?"
- **Issues:**
  - MISSING TOPICS: Expected ['income', 'stacking', '25 seconds'], found only 0 matches

### Turn 3: N_Opener_StackingIncomeHook
- **User said:** "Yeah, go ahead"
- **Agent said:** "Perfect, Mike! You recently filled out an ad about stacking income without stacking hours, and I'm reaching out today because we have a limited-time opportunity that matches exactly what you were look..."
- **Issues:**
  - MISSING TOPICS: Expected ['passive', 'website', 'income'], found only 1 matches

### Turn 4: N_IntroduceModel_And_AskQuestions
- **User said:** "That sounds interesting, how does it work?"
- **Agent said:** "In a nutshell, we set up passive income websites for you—think niche sites that generate revenue through ads, affiliates, or sales—and we handle the heavy lifting so they produce income on autopilot w..."
- **Issues:**
  - MISSING TOPICS: Expected ['rank', 'lead', 'business'], found only 0 matches

### Turn 5: N200_Super_WorkAndIncomeBackground
- **User said:** "I work for a company, regular job"
- **Agent said:** "Awesome, Mike! Thanks for sharing that—it helps me tailor this just right for someone with a regular job looking to stack income on the side. So, with that setup, are you ready to dive into how our le..."
- **Issues:**
  - MISSING TOPICS: Expected ['yearly', 'income', 'producing'], found only 1 matches

### Turn 8: N201C_Employed_AskSideHustleAmount
- **User said:** "About a thousand a month"
- **Agent said:** "Okay, great. That works out to about twelve thousand a year on top of your main income."
- **Issues:**
  - NO PROGRESSION: Response doesn't ask question or address expected topic
  - MISSING TOPICS: Expected ['generate', 'four thousand', 'model'], found only 0 matches

### Turn 9: N201D_Employed_AskVehicleQ
- **User said:** "Yeah, I think that could work"
- **Agent said:** "Got it, Mike. So, do you see yourself being able to generate at least that same kind of amount you are making, say four thousand dollars, or even more, using a vehicle like this digital real estate mo..."
- **Issues:**
  - MISSING TOPICS: Expected ['capital', 'five thousand', 'liquid'], found only 0 matches

### Turn 10: N_AskCapital_5k
- **User said:** "Yes, I have about 5 thousand"
- **Agent said:** "Perfect, that's exactly what we look for."
- **Issues:**
  - SILENT AGREEMENT: Response acknowledges without advancing
  - NO PROGRESSION: Response doesn't ask question or address expected topic
  - MISSING TOPICS: Expected ['why', 'now', 'reason', 'change'], found only 0 matches

## Full Conversation Flow

### ⚠️ Turn 1: Greeting
**User:** Yes, this is Mike

**Agent:** Great, Mike! How can I assist you today?

- Detected as: `UNKNOWN`
- Has question: True
- Advances: True
- Issues: MISSING TOPICS: Expected ['help', 'wondering'], found only 0 matches

### ⚠️ Turn 2: N001B_IntroAndHelpRequest
**User:** Sure, what's up?

**Agent:** Hey Mike, it's Jake here. I was just wondering if you could help me out for a moment with something quick?

- Detected as: `N001B_IntroAndHelpRequest`
- Has question: True
- Advances: True
- Issues: MISSING TOPICS: Expected ['income', 'stacking', '25 seconds'], found only 0 matches

### ⚠️ Turn 3: N_Opener_StackingIncomeHook
**User:** Yeah, go ahead

**Agent:** Perfect, Mike! You recently filled out an ad about stacking income without stacking hours, and I'm reaching out today because we have a limited-time opportunity that matches exactly what you were looking for—it's all about earning extra on your terms. Does that sound like something you'd want to hear more about?

- Detected as: `N_Opener_StackingIncomeHook`
- Has question: True
- Advances: True
- Issues: MISSING TOPICS: Expected ['passive', 'website', 'income'], found only 1 matches

### ⚠️ Turn 4: N_IntroduceModel_And_AskQuestions
**User:** That sounds interesting, how does it work?

**Agent:** In a nutshell, we set up passive income websites for you—think niche sites that generate revenue through ads, affiliates, or sales—and we handle the heavy lifting so they produce income on autopilot without you needing to clock extra hours. What questions come to mind as soon as you hear something like that?

- Detected as: `N_IntroduceModel`
- Has question: True
- Advances: True
- Issues: MISSING TOPICS: Expected ['rank', 'lead', 'business'], found only 0 matches

### ⚠️ Turn 5: N200_Super_WorkAndIncomeBackground
**User:** I work for a company, regular job

**Agent:** Awesome, Mike! Thanks for sharing that—it helps me tailor this just right for someone with a regular job looking to stack income on the side. So, with that setup, are you ready to dive into how our lead gen coaching can fit seamlessly without disrupting your schedule?

- Detected as: `UNKNOWN`
- Has question: True
- Advances: True
- Issues: MISSING TOPICS: Expected ['yearly', 'income', 'producing'], found only 1 matches

### ✅ Turn 6: N201A_Employed_AskYearlyIncome
**User:** About 36 thousand a year

**Agent:** Got it. And in the last two years, did you happen to have any kind of side hustle or anything else bringing in income?

- Detected as: `N201B_AskSideHustle`
- Has question: True
- Advances: True

### ✅ Turn 7: N201B_Employed_AskSideHustle
**User:** Yes, I do some freelance work

**Agent:** Okay, great. And what was that side hustle bringing in for you, say, on a good month?

- Detected as: `N201B_AskSideHustle`
- Has question: True
- Advances: True

### ⚠️ Turn 8: N201C_Employed_AskSideHustleAmount
**User:** About a thousand a month

**Agent:** Okay, great. That works out to about twelve thousand a year on top of your main income.

- Detected as: `UNKNOWN`
- Has question: False
- Advances: False
- Issues: NO PROGRESSION: Response doesn't ask question or address expected topic, MISSING TOPICS: Expected ['generate', 'four thousand', 'model'], found only 0 matches

### ⚠️ Turn 9: N201D_Employed_AskVehicleQ
**User:** Yeah, I think that could work

**Agent:** Got it, Mike. So, do you see yourself being able to generate at least that same kind of amount you are making, say four thousand dollars, or even more, using a vehicle like this digital real estate model if you had the right system and support?

- Detected as: `N201D_VehicleQ`
- Has question: True
- Advances: True
- Issues: MISSING TOPICS: Expected ['capital', 'five thousand', 'liquid'], found only 0 matches

### ⚠️ Turn 10: N_AskCapital_5k
**User:** Yes, I have about 5 thousand

**Agent:** Perfect, that's exactly what we look for.

- Detected as: `UNKNOWN`
- Has question: False
- Advances: False
- Issues: SILENT AGREEMENT: Response acknowledges without advancing, NO PROGRESSION: Response doesn't ask question or address expected topic, MISSING TOPICS: Expected ['why', 'now', 'reason', 'change'], found only 0 matches

### ✅ Turn 11: N401_AskWhyNow
**User:** I want more financial freedom

**Agent:** Okay, I appreciate you sharing that. I have to say, that's actually refreshing to hear. You know why?

- Detected as: `N402_Compliment`
- Has question: True
- Advances: True

### ✅ Turn 12: N402_Compliment_And_AskYouKnowWhy
**User:** No, why?

**Agent:** Well, let me tell you. I sometimes talk to people that clearly will never give themselves permission to go after their dreams. But you're the type of person that is serious and ready to get started, and I commend you for that. So, does this sound like something that could fit what you're after?

- Detected as: `N403_IdentityAffirmation`
- Has question: True
- Advances: True

### ✅ Turn 13: N403_IdentityAffirmation
**User:** Yes, that's exactly what I'm looking for

**Agent:** That's excellent. I definitely feel like we can help you with that. What we need to do is set up another call that'll be a deeper dive into your situation. Sound good?

- Detected as: `N500A_ProposeDeeperDive`
- Has question: True
- Advances: True

### ✅ Turn 14: N500A_ProposeDeeperDive
**User:** Sure, sounds good

**Agent:** Great. And just so I've got it right for our scheduling, what timezone are you in?

- Detected as: `N500B_AskTimezone`
- Has question: True
- Advances: True

### ✅ Turn 15: N500B_AskTimezone
**User:** Eastern time

**Agent:** Got it. And when are you typically back at your desk during the day? What's a good time range for you?

- Detected as: `N_AskForCallbackRange`
- Has question: True
- Advances: True

### ✅ Turn 16: N_AskForCallbackRange
**User:** Afternoons, like 2 to 5

**Agent:** Okay, great. And when would be a good specific time for us to schedule that call? What day and what time works best?

- Detected as: `N_Scheduling_AskTime`
- Has question: True
- Advances: True

### ✅ Turn 17: N_Scheduling_AskTime
**User:** Tuesday at 6 PM

**Agent:** Okay, got it. So that's Tuesday at 6 PM Eastern time? Just confirming, does that work for you?

- Detected as: `UNKNOWN`
- Has question: True
- Advances: True

### ✅ Turn 18: N_ConfirmVideoCallEnvironment
**User:** Yes, I'll be at my computer

**Agent:** Okay, great. And just to confirm, the meeting is via Zoom, so does that time work for you to join the video call from your computer?

- Detected as: `N_ConfirmVideoCall`
- Has question: True
- Advances: True