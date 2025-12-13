# Voice Agent Testing Scripts
## Comprehensive Node-by-Node Test Guide

This document provides test scripts for every node in your voice agent call flow. Each section includes:
- **Expected Agent Behavior**: What the agent should say/do
- **Test Responses**: Various user responses to test transitions
- **Objection Handling**: Common objections and expected handling
- **Edge Cases**: Unusual inputs to test robustness

---

# TABLE OF CONTENTS

1. [Greeting Node](#1-greeting-node)
2. [N500B_AskTimezone](#2-n500b_asktimezone)
3. [N_AskForCallbackRange](#3-n_askforcallbackrange)
4. [N_Scheduling_AskTime](#4-n_scheduling_asktime)
5. [N_ConfirmVideoCallEnvironment](#5-n_confirmvideocallenvironment)
6. [Time-Converter (Function)](#6-time-converter-function)
7. [Calendar-check (Function)](#7-calendar-check-function)
8. [N_Scheduling_RescheduleAndHandle](#8-n_scheduling_rescheduleandhandle)
9. [N206_AskAboutPartners](#9-n206_askaboutpartners)
10. [N018_ConfirmPartnerAvailability](#10-n018_confirmpartneravailability)
11. [N_AskAboutReminderSetup](#11-n_askaboutremindersetup)
12. [N_InstructToSetReminder_Now](#12-n_instructtosetreminder_now)
13. [N_SetConfirmationFrame](#13-n_setconfirmationframe)
14. [N201A_Employed_AskYearlyIncome](#14-n201a_employed_askyearlyincome)
15. [N201B_Employed_AskSideHustle](#15-n201b_employed_asksidehustle)
16. [N201C_Employed_AskSideHustleAmount](#16-n201c_employed_asksidehustleamount)
17. [N201D_Employed_AskVehicleQ](#17-n201d_employed_askvehicleq)
18. [N_AskCapital_5k_Direct](#18-n_askcapital_5k_direct)
19. [General Objection Handling](#19-general-objection-handling)
20. [Voicemail/IVR Detection](#20-voicemailivr-detection)
21. [Edge Cases & Stress Tests](#21-edge-cases--stress-tests)

---

# 1. GREETING NODE

## Expected Behavior
Agent opens with a name confirmation (e.g., "Kendrick?" or "Hi, is this [Name]?")

## Test Responses - Positive Confirmation

```
Test 1.1: Simple Yes
User: "Yes"
Expected: Transition to next node (Timezone or Qualification)

Test 1.2: Full Confirmation
User: "Yeah, this is Kendrick"
Expected: Transition to next node

Test 1.3: Speaking Confirmation
User: "Speaking"
Expected: Transition to next node

Test 1.4: Affirmative with Question
User: "Yes, who's calling?"
Expected: Agent introduces themselves, then transitions

Test 1.5: Casual Confirmation
User: "Yep, that's me"
Expected: Transition to next node
```

## Test Responses - Negative/Wrong Person

```
Test 1.6: Wrong Person
User: "No, you have the wrong number"
Expected: Agent apologizes and ends call gracefully

Test 1.7: Different Name
User: "No, this is Michael"
Expected: Agent asks for correct person or apologizes

Test 1.8: Person Not Available
User: "No, Kendrick isn't here right now"
Expected: Agent asks when to call back or leaves message
```

## Objection Handling

```
Test 1.9: Immediate "Not Interested"
User: "Not interested"
Expected: Agent handles objection, attempts to continue

Test 1.10: "Who is this?"
User: "Who is this? How did you get my number?"
Expected: Agent introduces themselves and company

Test 1.11: "Take me off your list"
User: "Take me off your list"
Expected: Agent acknowledges, confirms removal, ends politely

Test 1.12: Busy
User: "I'm busy right now"
Expected: Agent offers to call back at better time

Test 1.13: Suspicious
User: "Is this a scam?"
Expected: Agent reassures and explains purpose
```

## Edge Cases

```
Test 1.14: Silence (3+ seconds)
User: [silence]
Expected: Agent prompts "Hello? Are you there?"

Test 1.15: Background Noise Only
User: [background noise, no speech]
Expected: Agent waits, then prompts

Test 1.16: Mumbled Response
User: "Mmhmm"
Expected: Agent clarifies "Is this [Name]?"

Test 1.17: Cut Off Mid-Sentence
User: "Yes this is—"
Expected: Agent waits for completion or prompts
```

---

# 2. N500B_ASKTIMEZONE

## Expected Behavior
Agent asks about user's timezone for scheduling purposes.

## Test Responses - Clear Timezone

```
Test 2.1: Standard Timezone
User: "Eastern"
Expected: Extract timeZone=EST, transition to next node

Test 2.2: Full Timezone Name
User: "Eastern Standard Time"
Expected: Extract timeZone=EST, transition

Test 2.3: Pacific
User: "Pacific time"
Expected: Extract timeZone=PST, transition

Test 2.4: Central
User: "I'm in Central time"
Expected: Extract timeZone=CST, transition

Test 2.5: Mountain
User: "Mountain timezone"
Expected: Extract timeZone=MST, transition

Test 2.6: City-Based Answer
User: "I'm in New York"
Expected: Infer EST, transition

Test 2.7: State-Based Answer
User: "California"
Expected: Infer PST, transition
```

## Test Responses - Ambiguous

```
Test 2.8: Abbreviated
User: "EST"
Expected: Extract timeZone=EST, transition

Test 2.9: Informal
User: "Same as New York"
Expected: Infer EST, transition

Test 2.10: With Offset
User: "GMT minus 5"
Expected: Extract appropriate timezone

Test 2.11: Unsure
User: "I'm not sure what timezone I'm in"
Expected: Agent asks clarifying question (state/city)
```

## Objection Handling

```
Test 2.12: Privacy Concern
User: "Why do you need to know my timezone?"
Expected: Agent explains scheduling reason

Test 2.13: Deflection
User: "Let's just get to the point"
Expected: Agent explains importance briefly, re-asks

Test 2.14: Refusal
User: "I'd rather not say"
Expected: Agent offers alternative (ask city/state)
```

## Edge Cases

```
Test 2.15: International
User: "I'm in London"
Expected: Handle GMT/BST appropriately

Test 2.16: Multiple Timezones
User: "I travel between Eastern and Pacific"
Expected: Agent asks which is primary/current

Test 2.17: Daylight Saving Confusion
User: "Is that daylight time or standard time?"
Expected: Agent clarifies current time
```

---

# 3. N_ASKFORCALLBACKRANGE

## Expected Behavior
Agent asks for a general time range when user is available for calls.

## Test Responses - Clear Range

```
Test 3.1: Specific Range
User: "Between 10 AM and 3 PM"
Expected: Extract callbackRange, transition

Test 3.2: Morning Preference
User: "Mornings work best for me"
Expected: Extract morning range, transition

Test 3.3: Afternoon Preference
User: "Afternoons, usually after 2"
Expected: Extract afternoon range, transition

Test 3.4: All Day
User: "I'm flexible, anytime during business hours"
Expected: Extract full day range, transition

Test 3.5: Specific Days
User: "Tuesday and Thursday afternoons"
Expected: Extract day and time preferences

Test 3.6: Lunch Exclusion
User: "9 to 5, but not during lunch"
Expected: Note lunch exclusion
```

## Test Responses - Vague

```
Test 3.7: Very Vague
User: "Whenever"
Expected: Agent asks for more specificity

Test 3.8: Evening Only
User: "Only after 6 PM"
Expected: Note evening preference, check if available

Test 3.9: Weekend Only
User: "Only on weekends"
Expected: Check availability for weekends

Test 3.10: Work Schedule
User: "I work 9-5 so after that"
Expected: Extract evening availability
```

## Objection Handling

```
Test 3.11: Busy Schedule
User: "I don't really have time for calls"
Expected: Agent emphasizes brief call, flexibility

Test 3.12: Screening Calls
User: "I don't answer unknown numbers"
Expected: Agent offers to schedule specific time

Test 3.13: Email Preference
User: "Can you just email me instead?"
Expected: Explain why call is beneficial, offer compromise
```

---

# 4. N_SCHEDULING_ASKTIME

## Expected Behavior
Agent asks for a specific date and time for the appointment.

**MANDATORY VARIABLES**: scheduleTime, amPm (must extract before transitioning)

## Test Responses - Complete Time

```
Test 4.1: Full Specification
User: "Tomorrow at 2 PM"
Expected: Extract date and time, transition to confirmation

Test 4.2: Day and Time
User: "Friday at 10 in the morning"
Expected: Extract Friday, 10 AM, transition

Test 4.3: Relative Day
User: "Next Monday at 3"
Expected: Extract next Monday, 3 PM (infer PM for business), transition

Test 4.4: With AM/PM
User: "Thursday at 9 AM"
Expected: Extract Thursday, 9 AM, transition

Test 4.5: 24-Hour Format
User: "Tomorrow at 14:00"
Expected: Convert to 2 PM, transition

Test 4.6: Multiple Options
User: "Either Tuesday at 2 or Wednesday at 10"
Expected: Agent picks first or asks preference
```

## Test Responses - Incomplete (Should Re-prompt)

```
Test 4.7: Day Only
User: "How about Friday?"
Expected: Agent asks "What time works for you on Friday?"

Test 4.8: Time Only
User: "3 PM"
Expected: Agent asks "And what day works best?"

Test 4.9: Vague Time
User: "Afternoon sometime"
Expected: Agent asks for specific time

Test 4.10: Too Far Out
User: "Maybe in a few weeks"
Expected: Agent encourages sooner, asks for specific date

Test 4.11: Unsure
User: "I'm not sure, what do you have available?"
Expected: Agent offers options
```

## Test Responses - Agreement with Agent Suggestion

```
Test 4.12: Simple Agreement
User: "Sure"
Expected: If agent suggested time, extract that time

Test 4.13: Sounds Good
User: "Sounds good"
Expected: Extract previously suggested time

Test 4.14: That Works
User: "That works for me"
Expected: Extract previously suggested time

Test 4.15: Agreement with Modification
User: "Yeah but make it 3 instead of 2"
Expected: Extract modified time
```

## Objection Handling

```
Test 4.16: Too Busy
User: "I'm slammed this week"
Expected: Ask about next week

Test 4.17: Need to Check Calendar
User: "Let me check my calendar... hold on"
Expected: Wait patiently, confirm when ready

Test 4.18: Not Sure About Commitment
User: "I don't know if I want to commit to a time yet"
Expected: Explain benefits, reduce pressure

Test 4.19: Asked for Callback
User: "Can you just call me back sometime?"
Expected: Encourage specific time for better experience
```

## Edge Cases

```
Test 4.20: Past Time
User: "Yesterday at 2"
Expected: Agent clarifies they need future time

Test 4.21: Very Far Future
User: "How about 6 months from now?"
Expected: Agent encourages sooner

Test 4.22: Time Zone Confusion
User: "3 PM your time or my time?"
Expected: Agent clarifies (their timezone)

Test 4.23: Numeric Date
User: "December 15th at 4"
Expected: Parse date correctly
```

---

# 5. N_CONFIRMVIDEOCALLENVIRONMENT

## Expected Behavior
Agent confirms the meeting is via Zoom and user can join from computer.

## Test Responses - Positive Confirmation

```
Test 5.1: Simple Yes
User: "Yes"
Expected: Transition to Time-Converter → Calendar-check

Test 5.2: Confirmation with Detail
User: "Yeah, I'll be at my desk with my computer"
Expected: Transition to booking flow

Test 5.3: Laptop Confirmation
User: "Yep, I have my laptop"
Expected: Transition

Test 5.4: Work Computer
User: "I'll be on my work computer"
Expected: Transition
```

## Test Responses - Concerns

```
Test 5.5: Phone Preference
User: "Can I join from my phone instead?"
Expected: Agent explains computer is preferred, but phone works

Test 5.6: No Zoom
User: "I don't have Zoom installed"
Expected: Agent explains they'll send link, easy to join

Test 5.7: Technical Concerns
User: "I'm not very tech savvy"
Expected: Agent reassures it's simple, offers help

Test 5.8: Privacy Concerns
User: "Do I have to have my camera on?"
Expected: Agent explains camera preference but not required
```

## Objection Handling

```
Test 5.9: Prefers Phone Call
User: "Can't we just do a phone call?"
Expected: Explain benefits of video, offer phone as backup

Test 5.10: Time Change Request
User: "Actually, can we change the time?"
Expected: Transition to rescheduling flow

Test 5.11: Need to Reschedule
User: "Something came up, I need a different day"
Expected: Transition to rescheduling
```

---

# 6. TIME-CONVERTER (FUNCTION)

## Expected Behavior
Function node that converts user's local time to standardized format.
Plays dialogue: "Hang on a sec while I make sure that's available."

## Test Scenarios

```
Test 6.1: Normal Conversion
Input: scheduleTime="tomorrow at 2 PM", timeZone="EST"
Expected: Convert to ISO format, transition to Calendar-check

Test 6.2: DST Handling
Input: scheduleTime="March 15 at 2 PM", timeZone="EST"
Expected: Handle daylight saving correctly

Test 6.3: Weekend Time
Input: scheduleTime="Saturday at 10 AM"
Expected: Process weekend time
```

## User Interruption During Webhook

```
Test 6.4: User Speaks During Wait
User: "Okay" (while webhook executing)
Expected: System waits for webhook completion, doesn't double-process

Test 6.5: User Question During Wait
User: "How long will this take?"
Expected: System queues input, processes after webhook
```

---

# 7. CALENDAR-CHECK (FUNCTION)

## Expected Behavior
Function node that checks calendar availability via webhook.

## Test Scenarios - Available

```
Test 7.1: Time Available
Webhook Response: {"result": "Great! They are all set."}
Expected: Transition to N206_AskAboutPartners (success path)

Test 7.2: Available with Confirmation
Webhook Response: {"result": "Booked for Friday at 2 PM"}
Expected: Transition to success path
```

## Test Scenarios - Not Available

```
Test 7.3: Time Not Available
Webhook Response: {"result": "Apologize, time isn't available. Available slots: Thu 10:30 AM, Fri 9:15 AM"}
Expected: Transition to N_Scheduling_RescheduleAndHandle

Test 7.4: Fully Booked Day
Webhook Response: {"result": "No availability on that day"}
Expected: Transition to reschedule, offer different day
```

---

# 8. N_SCHEDULING_RESCHEDULEANDHANDLE

## Expected Behavior
Agent handles rescheduling when requested time isn't available.
Presents alternative times from webhook response.

## Test Responses - Accept Alternative

```
Test 8.1: Accept First Option
User: "Let's do the Thursday time"
Expected: Extract new time, go back to Time-Converter

Test 8.2: Accept Second Option
User: "Friday at 9:15 works better"
Expected: Extract Friday 9:15, process booking

Test 8.3: General Acceptance
User: "Any of those work"
Expected: Agent picks first available, processes

Test 8.4: Modified Acceptance
User: "Can we do Friday but at 10 instead of 9:15?"
Expected: Extract modified time, re-check availability
```

## Test Responses - Request Different Options

```
Test 8.5: Different Day
User: "Do you have anything next week?"
Expected: Agent checks or offers to check different week

Test 8.6: Different Time of Day
User: "Those are all too early, anything in the afternoon?"
Expected: Agent offers afternoon alternatives

Test 8.7: Specific Request
User: "What about Monday?"
Expected: Agent checks Monday availability
```

## Objection Handling

```
Test 8.8: Frustration
User: "This is getting complicated"
Expected: Agent apologizes, simplifies options

Test 8.9: Give Up
User: "Never mind, let's forget it"
Expected: Agent tries to salvage, offers flexibility

Test 8.10: Callback Request
User: "Just call me back when you have better times"
Expected: Agent tries to lock in something, or schedules callback
```

---

# 9. N206_ASKABOUTPARTNERS

## Expected Behavior
Agent asks if there are business partners or spouse who should be on the call.

## Test Responses - No Partners

```
Test 9.1: Simple No
User: "No, just me"
Expected: Transition to next node (reminder setup)

Test 9.2: Solo Business
User: "It's just my business, no partners"
Expected: Transition

Test 9.3: Spouse Not Involved
User: "My spouse isn't involved in business decisions"
Expected: Transition
```

## Test Responses - Has Partners

```
Test 9.4: Has Spouse
User: "Yes, my wife should be on the call"
Expected: Transition to N018_ConfirmPartnerAvailability

Test 9.5: Business Partner
User: "I have a business partner who handles finances"
Expected: Ask if partner should be on call

Test 9.6: Multiple Partners
User: "There's me and two partners"
Expected: Ask about their availability
```

## Objection Handling

```
Test 9.7: Privacy
User: "Why do you need to know that?"
Expected: Explain importance of decision makers being present

Test 9.8: Partner Won't Be Available
User: "My partner can never make these calls"
Expected: Ask if user can make decisions alone
```

---

# 10. N018_CONFIRMPARTNERAVAILABILITY

## Expected Behavior
Agent confirms that the partner/spouse can also attend at the scheduled time.

## Test Responses

```
Test 10.1: Partner Available
User: "Yes, she can be there"
Expected: Confirm both attending, transition

Test 10.2: Partner Might Be Available
User: "I'll have to check with them"
Expected: Encourage checking, offer to hold or callback

Test 10.3: Partner Not Available
User: "No, they're working at that time"
Expected: Offer to reschedule when both available

Test 10.4: Will Inform Partner
User: "I'll let them know about the call"
Expected: Confirm they'll both be there
```

---

# 11. N_ASKABOUTREMINDERSETUP

## Expected Behavior
Agent asks if user knows how to set a reminder on their phone.

## Test Responses

```
Test 11.1: Knows How
User: "Yeah, I know how"
Expected: Transition to set reminder instruction

Test 11.2: Already Set
User: "I already put it in my calendar"
Expected: Acknowledge, transition

Test 11.3: Doesn't Know
User: "Not really"
Expected: Offer to help/explain

Test 11.4: Will Remember
User: "I'll remember, don't worry"
Expected: Encourage reminder anyway
```

---

# 12. N_INSTRUCTTOSETREMINDER_NOW

## Expected Behavior
Agent asks user to set the reminder right now while on the call.

## Test Responses

```
Test 12.1: Compliant
User: "Okay, I'm setting it now"
Expected: Wait, then confirm

Test 12.2: Already Done
User: "Done, I set it"
Expected: Confirm and transition to closing

Test 12.3: Will Do Later
User: "I'll do it after the call"
Expected: Encourage doing it now, but accept

Test 12.4: Technical Issue
User: "My phone is acting up, can't do it now"
Expected: Understand, move on
```

---

# 13. N_SETCONFIRMATIONFRAME

## Expected Behavior
Agent sets expectations for the upcoming call and next steps.

## Test Responses

```
Test 13.1: Acknowledgment
User: "Sounds good"
Expected: Transition to closing

Test 13.2: Question About Call
User: "What exactly will we discuss?"
Expected: Brief overview, transition

Test 13.3: Concern
User: "Is this going to be a sales pitch?"
Expected: Reassure about value, not pushy
```

---

# 14. N201A_EMPLOYED_ASKYEARLYINCOME

## Expected Behavior
Agent asks about yearly income from employment.

**MANDATORY VARIABLES**: employed_yearly_income

## Test Responses - Clear Income

```
Test 14.1: Exact Amount
User: "I make $50,000 a year"
Expected: Extract employed_yearly_income=50000, transition

Test 14.2: Approximate
User: "About 75k"
Expected: Extract employed_yearly_income=75000, transition

Test 14.3: Range
User: "Between 60 and 70 thousand"
Expected: Extract middle value or ask for specific

Test 14.4: Monthly Conversion
User: "I make $5,000 a month"
Expected: Calculate 60000 yearly, transition

Test 14.5: Hourly Conversion
User: "I make $25 an hour"
Expected: Calculate approximately 52000 yearly

Test 14.6: Speech Pattern
User: "I do about 24k"
Expected: Extract 24000 (NOT 204000)

Test 14.7: With Hesitation
User: "I make about, um, 30 thousand"
Expected: Extract 30000

Test 14.8: Informal
User: "Six figures"
Expected: Extract approximately 100000 or ask for specific
```

## Test Responses - Refusal/Uncomfortable

```
Test 14.9: Privacy Concern
User: "I'd rather not say"
Expected: Explain why needed, offer range options

Test 14.10: Deflection
User: "Why do you need to know that?"
Expected: Explain qualification purposes

Test 14.11: Vague
User: "I do okay"
Expected: Ask for more specific range
```

---

# 15. N201B_EMPLOYED_ASKSIDEHUSTLE

## Expected Behavior
Agent asks if user has any side income/hustle.

## Test Responses

```
Test 15.1: Has Side Hustle
User: "Yeah, I do some freelance work"
Expected: Transition to ask about amount

Test 15.2: No Side Hustle
User: "No, just my main job"
Expected: Skip side hustle amount, transition

Test 15.3: Multiple Side Hustles
User: "I do Uber and some consulting"
Expected: Ask about combined amount

Test 15.4: Rental Income
User: "I have a rental property"
Expected: Treat as side income
```

---

# 16. N201C_EMPLOYED_ASKSIDEHUSTLEAMOUNT

## Expected Behavior
Agent asks how much the side hustle brings in.

## Test Responses

```
Test 16.1: Monthly Amount
User: "About $1,000 a month"
Expected: Extract side_hustle=1000/month

Test 16.2: Yearly Amount
User: "Maybe 15k a year"
Expected: Extract and convert

Test 16.3: Variable
User: "It varies, sometimes $500, sometimes $2000"
Expected: Ask for average or use midpoint

Test 16.4: Just Started
User: "I just started, not much yet"
Expected: Accept low/zero value
```

---

# 17. N201D_EMPLOYED_ASKVEHICLEQ

## Expected Behavior
Agent asks about vehicle ownership for certain programs.

## Test Responses

```
Test 17.1: Owns Vehicle
User: "Yes, I have a car"
Expected: Mark vehicle=yes, transition

Test 17.2: Multiple Vehicles
User: "We have two cars"
Expected: Mark vehicle=yes, transition

Test 17.3: No Vehicle
User: "No, I don't have a car"
Expected: Mark vehicle=no, may affect qualification

Test 17.4: Leased Vehicle
User: "I lease my car"
Expected: Clarify if that counts
```

---

# 18. N_ASKCAPITAL_5K_DIRECT

## Expected Behavior
Agent asks about capital/investment amount for lower tier (5k range).

## Test Responses

```
Test 18.1: Has Capital
User: "I have about $5,000 saved"
Expected: Extract amount, transition

Test 18.2: Limited Capital
User: "Maybe $2,000"
Expected: Extract, discuss options

Test 18.3: No Capital
User: "I don't have any savings right now"
Expected: Discuss financing options

Test 18.4: More Than Expected
User: "I have $20,000"
Expected: May route to higher tier
```

---

# 19. GENERAL OBJECTION HANDLING

## Common Objections (Test at ANY Node)

### Time Objections

```
Test 19.1: "I'm busy right now"
Expected: Offer to schedule callback

Test 19.2: "Can you call back later?"
Expected: Ask for specific time, schedule callback

Test 19.3: "I only have 5 minutes"
Expected: Adapt pace, focus on essentials

Test 19.4: "This is taking too long"
Expected: Apologize, speed up, offer alternative
```

### Interest Objections

```
Test 19.5: "I'm not interested"
Expected: Ask what would make it interesting, try to understand

Test 19.6: "I've heard this before"
Expected: Differentiate, explain unique value

Test 19.7: "Sounds too good to be true"
Expected: Provide credibility, references

Test 19.8: "I don't need this"
Expected: Ask about their situation, find pain points
```

### Trust Objections

```
Test 19.9: "How did you get my number?"
Expected: Explain lead source honestly

Test 19.10: "Is this a scam?"
Expected: Provide company info, credibility

Test 19.11: "I need to research your company first"
Expected: Offer to send info, schedule follow-up

Test 19.12: "Can you send me information?"
Expected: Offer to send, but encourage staying on call
```

### Financial Objections

```
Test 19.13: "I can't afford this"
Expected: Discuss options, payment plans

Test 19.14: "I need to talk to my spouse"
Expected: Offer to include spouse, schedule joint call

Test 19.15: "The economy is bad right now"
Expected: Acknowledge, discuss timing benefits
```

### Decision Objections

```
Test 19.16: "I need to think about it"
Expected: Understand concerns, offer to address

Test 19.17: "I never make decisions on the phone"
Expected: Respect, offer in-person or video alternative

Test 19.18: "Send me something and I'll review"
Expected: Offer to send, schedule follow-up
```

---

# 20. VOICEMAIL/IVR DETECTION

## Test Scenarios

```
Test 20.1: Standard Voicemail
Audio: "The person you're trying to reach is not available. At the tone, please record your message."
Expected: Detect voicemail, hang up automatically

Test 20.2: Personal Voicemail
Audio: "Hi, you've reached John. Leave a message after the beep."
Expected: Detect voicemail, hang up

Test 20.3: Business Voicemail
Audio: "Thank you for calling ABC Company. No one is available to take your call."
Expected: Detect voicemail, hang up

Test 20.4: Press 1 Gatekeeper
Audio: "Press 1 to connect to the caller"
Expected: Detect gatekeeper, send DTMF 1

Test 20.5: IVR Menu
Audio: "Press 1 for sales, press 2 for support"
Expected: Detect IVR, hang up (can't navigate)

Test 20.6: Fax Machine
Audio: [Fax tones]
Expected: AMD detects fax, hang up immediately

Test 20.7: Ring Forever
Audio: [Continuous ringing, no answer]
Expected: Eventually timeout or carrier disconnect
```

---

# 21. EDGE CASES & STRESS TESTS

## Speech Recognition Challenges

```
Test 21.1: Heavy Accent
User: [Heavy accent] "Yes, this is Kendrick"
Expected: Understand and proceed

Test 21.2: Background Noise
User: [Loud background] "I'm in Eastern time"
Expected: Extract timezone despite noise

Test 21.3: Bad Connection
User: [Choppy] "Tom...orrow at... 2"
Expected: Ask for clarification or repeat

Test 21.4: Whispering
User: [Whispered] "Yes"
Expected: Detect speech, may ask to speak up

Test 21.5: Yelling
User: [Loud] "THURSDAY AT NOON!"
Expected: Process normally
```

## Interruption Handling

```
Test 21.6: User Interrupts Agent
Agent: "So I wanted to ask about—"
User: "Wait, before you continue..."
Expected: Agent stops, listens to user

Test 21.7: Rapid Fire Questions
User: "What company? Who are you? Why calling?"
Expected: Agent addresses questions calmly

Test 21.8: User Talks Over
User: [Talking while agent speaks]
Expected: Agent detects interruption, pauses
```

## Emotional States

```
Test 21.9: Angry User
User: "I'm sick of these calls! Stop calling me!"
Expected: Agent de-escalates, offers removal

Test 21.10: Confused User
User: "Wait, what? I don't understand"
Expected: Agent clarifies, slows down

Test 21.11: Suspicious User
User: "This sounds like a scam. I'm recording this."
Expected: Agent remains professional, provides info

Test 21.12: Distracted User
User: "Sorry, what did you say? My kid was yelling"
Expected: Agent repeats patiently
```

## Multi-Turn Complexity

```
Test 21.13: Change Mind Mid-Call
User: "Actually, let's do a different time"
Expected: Agent handles gracefully, re-routes

Test 21.14: Multiple Corrections
User: "No wait, not 2 PM, I meant 3 PM. Actually, 4 PM."
Expected: Agent takes final answer

Test 21.15: Circular Conversation
User: [Keeps asking same question]
Expected: Agent recognizes pattern, addresses root issue

Test 21.16: Tangent
User: [Goes off on unrelated topic]
Expected: Agent listens, then redirects
```

## System Stress

```
Test 21.17: Very Long Response
User: [300+ word response]
Expected: Agent extracts key info, responds appropriately

Test 21.18: Single Word Responses Only
User: "Yes" / "No" / "Fine" / "Okay"
Expected: Agent carries conversation, asks open questions

Test 21.19: Numeric-Heavy Response
User: "Call me at 555-123-4567 extension 890 after 2:30 PM on the 15th"
Expected: Extract all numbers correctly

Test 21.20: Multiple Languages
User: [English with Spanish phrases mixed in]
Expected: Understand context, respond in English
```

---

# TESTING CHECKLIST

## Per-Node Checklist
- [ ] Positive path transition works
- [ ] Negative path transition works
- [ ] Mandatory variables extract correctly
- [ ] Objection handling activates appropriately
- [ ] Edge cases don't break flow
- [ ] Timeout/silence handling works

## Full Flow Checklist
- [ ] Complete happy path works end-to-end
- [ ] Rescheduling flow works
- [ ] Partner inclusion flow works
- [ ] All objection recoveries work
- [ ] Voicemail detection works
- [ ] Gatekeeper bypass works

## Performance Checklist
- [ ] Response latency < 2 seconds
- [ ] No duplicate responses
- [ ] No missed user inputs
- [ ] Transitions happen promptly
- [ ] Webhook timeouts handled gracefully

---

# NOTES FOR TESTERS

1. **Record all tests** - Use call recording for debugging
2. **Log timestamps** - Note when issues occur for log correlation
3. **Test in sequence** - Go through full flows, not just individual nodes
4. **Vary your voice** - Test with different speaking speeds, volumes
5. **Use real phones** - Test on actual phone connections, not just simulators
6. **Check transcripts** - Verify what the system "heard" vs what was said
7. **Monitor logs** - Watch for errors, warnings, unexpected transitions

---

*Document generated: December 2024*
*For agent: JK First Caller-optimizer*
*Total test cases: 200+*
