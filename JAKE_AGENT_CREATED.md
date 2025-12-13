# Jake - Income Stacking Qualifier Agent ✅

## Agent Created Successfully

**Agent ID:** `04b9509d-cfd9-4e3e-9146-f805c858b823`  
**Name:** Jake - Income Stacking Qualifier  
**Type:** Call Flow Agent  
**Status:** Active

## Access the Agent

🎯 **Edit in UI:** `/agents/04b9509d-cfd9-4e3e-9146-f805c858b823/edit`

Or go to your agents list and look for "Jake - Income Stacking Qualifier"

## Agent Overview

This is a comprehensive qualification agent designed to:
- Qualify prospects for a passive income opportunity
- Handle various objections (trust, time, interest)
- Assess financial capability (income, capital, credit)
- Uncover motivation ("Why now?")
- Schedule strategy calls with video pre-work

## Flow Structure

### Total Nodes: 41

- **Start Node:** 1
- **Conversation Nodes:** 35
- **Logic Split Nodes:** 1  
- **Ending Nodes:** 4

## Call Flow Overview

### 1. Opening & Triage (Nodes 1-11)
- **Name Confirmation** - Confirms prospect's name with upward inflection
- **Intro & Help Request** - "This is Jake. I was just, um, wondering if you could possibly help me out for a moment?"
- **Stacking Income Hook** - Introduces the "stacking income without stacking hours" concept
- **Objection Handling** - Handles "no recall", "not interested", "no time", and trust concerns
- **Share Background** - Jake's credentials (military veteran, software engineer)
- **Social Proof** - Mentions thousands of students, best student doing $1M/month

### 2. Business Model Introduction (Nodes 5, 9)
- **Introduce Model** - "In a nutshell, we set up passive income websites, and we let them produce income for you"
- **Q&A Strategic Narrative** - Answers questions, deflects pricing to later call
- **Value Framing** - "Would you honestly be upset if you had an extra twenty thousand dollars a month coming in?"

### 3. Work & Income Background (Nodes 12-21)
- **Employment Status** - Determines if employed, unemployed, or business owner
- **Income Assessment** - Gathers yearly income or monthly revenue
- **Side Hustle Discovery** - Asks about additional income sources

### 4. Financial Qualification (Nodes 20-24)
- **Logic Split** - Routes based on income level (>$96k/year or >$8k/month → higher track)
- **Capital Assessment (15-25k)** - For high-income prospects
- **Capital Assessment (5k)** - Minimum required capital
- **Credit Score (650+)** - Fallback if no liquid capital
- **Disqualification** - Polite exit if not financially qualified

### 5. Motivation & Commitment (Nodes 25-27)
- **Why Now?** - "Is there a specific reason you're looking to make a change right now?"
- **Identity Affirmation** - "You're the type of person that is serious and ready to get started"
- **Value Fit** - Confirms the concept resonates

### 6. Scheduling (Nodes 28-33)
- **Propose Deeper Dive** - Sets up strategy call
- **Timezone Collection** - Gets timezone for scheduling
- **Time Selection** - Asks for specific time
- **Video Call Confirmation** - Confirms they can join Zoom from computer
- **Partner Check** - Asks if spouse/partner needs to be on call

### 7. Pre-Call Video & Close (Nodes 34-38)
- **Introduce Video** - 12-minute overview video
- **Fee Waiver Frame** - "$1000 strategy session fee waived"
- **Text Confirmation** - Asks to reply to text with video link
- **Final Close** - "You are all set then, {{customer_name}}. Have a great rest of your day. Goodbye."

## Key Features

### Variable Extraction
The agent automatically extracts:
- `customer_name` - Used throughout conversation
- `yearly_income` - For employed prospects
- `past_yearly_income` - For unemployed prospects  
- `monthly_revenue` - For business owners
- `highest_revenue` - Peak business revenue
- `side_hustle_income` - Additional income
- `motivation` - Why they want change now
- `timeZone` - For scheduling
- `scheduleTime` - Preferred call time

### Smart Routing
- **Income-based logic split** - Routes high earners to premium capital track
- **Employment path routing** - Different questions for employed vs unemployed vs business owners
- **Partner availability** - Reschedules if partner can't make it

### Objection Handling
Built-in responses for:
- "I don't recall the ad"
- "Not interested"
- "No time"
- "Sounds like a scam"
- "I'm too busy"

### Disqualification Paths
Graceful exits for:
- Wrong number
- Not financially qualified
- Not motivated/interested

## Conversation Style

The agent is designed with a natural, conversational style:
- Uses filler words ("um", "uh") for authenticity
- Pauses appropriately
- Builds rapport through storytelling
- Acknowledges objections empathetically
- Uses social proof strategically

## Technical Configuration

- **LLM:** GPT-4 Turbo (OpenAI)
- **TTS:** ElevenLabs (Turbo v2.5)
- **Voice:** Rachel (ID: J5iaaqzR5zn6HFG4jV3b)
- **STT:** Deepgram
- **Temperature:** 0.7
- **Max Tokens:** 500

## Next Steps

1. **Edit in UI** - Go to `/agents/04b9509d-cfd9-4e3e-9146-f805c858b823/edit`
2. **Customize Variables** - Add your specific `customer_name` values
3. **Test the Flow** - Use the test caller or outbound caller
4. **Adjust Scripts** - Modify any scripts to match your brand voice
5. **Add Webhooks** - Add function nodes if you need to integrate with your CRM

## Notes

- All transitions are properly wired and will work in the UI
- The flow follows the exact structure from your call_flow.md
- Scripts are taken directly from the bot.py node definitions
- The agent uses `{{customer_name}}` variable which should be passed when initiating calls
- Logic split at node 20 checks income to route to appropriate capital questions

## Created From

- **Source:** call_flow.md, bot.py, Retell Caller.pdf
- **Date:** Based on your previous campaign's working flow
- **Nodes:** 41 total nodes covering complete qualification process

The agent is now **fully editable in your UI** and ready for testing! 🎉
