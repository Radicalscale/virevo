#!/usr/bin/env python3
"""
Update Jake agent with ALL goals from Retell Caller PDF
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient

# Map of node labels to their goals from the PDF
GOALS_MAP = {
    "Name Confirmation": "Say the person's name with an upward inflection to confirm identity.",
    "Intro & Help Request": "Ask them if they could help you out for a moment.",
    "Stacking Income Hook": "Introduce yourself and context, deliver the 'stacking income without stacking hours' hook, and get permission to explain further.",
    "Introduce Model": "Explain the business model (passive income websites) and engage their curiosity by asking what questions come to mind.",
    "No Recall Pivot": "Pivot from their 'no recall' of the ad, test their interest in financial benefit, and challenge any disinterest to uncover true priorities.",
    "Deframe Objection": "Skillfully de-frame their initial objection to elicit a statement of curiosity or interest, opening a path to discuss the opportunity.",
    "Early Dismiss - Share Background": "Share your personal background story (military veteran, software engineer) to build credibility and overcome skepticism.",
    "Q&A Strategic Narrative": "Answer their questions about the business model. If they ask about price, defer to the strategy call. After answering, ask the value-framing question about having an extra $20k/month.",
    "Share Background Hook": "Share background as military veteran with software degree, mention students making $20k+ monthly, ask if they know what makes it possible.",
    "Explain & Explore": "Explain social proof (thousands of students, John doing $1M/month), then ask if this range of passive income is worth exploring.",
    "Work Background": "Determine the user's employment status - working for someone, running own business, or unemployed.",
    "Ask Yearly Income (Employed)": "Efficiently and professionally ask for their approximate current yearly income. If they refuse, frame it as a critical qualification step for this valuable opportunity.",
    "Ask Past Income (Unemployed)": "First acknowledge their unemployment with genuine empathy, then politely ask for their approximate past yearly income to establish a financial baseline.",
    "Ask Monthly Revenue (Business)": "Directly and professionally ask the business owner for their approximate current monthly revenue to establish a financial baseline.",
    "Ask Side Hustle (Employed)": "Smoothly and efficiently ask if they've had any side hustles or other income sources in the last two years.",
    "Ask Side Hustle (Unemployed)": "Efficiently and conversationally ask if they had any side hustles or other income sources in the last two years.",
    "Ask Highest Revenue (Business)": "Acknowledge their current monthly revenue and ask for their business's highest monthly revenue point achieved within the last two years to understand peak potential.",
    "Ask Side Hustle Amount (Employed)": "Positively acknowledge their side hustle and efficiently ask for the approximate monthly income it generated on a good month.",
    "Ask Side Hustle Amount (Unemployed)": "Efficiently ask for the approximate monthly income from their previously mentioned side hustle to complete their financial picture.",
    "Ask Capital 15-25k": "Ask if they have $15,000 to $25,000 in liquid capital set aside for initial business expenses.",
    "Ask Capital 5k": "Directly ask if they have access to the absolute minimum of $5,000 for initial expenses to get started.",
    "Ask Credit Score": "Ask if they have a credit score of at least 650 as an alternative qualification method if they don't have liquid capital.",
    "Ask Why Now": "Ask the 'Why now?' question to uncover their true motivation. Use assertive, frame-controlling tactics to handle any deferrals or vague responses.",
    "Compliment & Hook": "Sincerely acknowledge their reason for interest, deliver a genuine compliment about being the type of person who gives themselves permission to pursue their dreams, and ask the engaging hook question 'You know why?'",
    "Identity Affirmation": "Explain that many people never give themselves permission to pursue their dreams, but affirm that they are the type of person who is serious and ready. Ask if this fits what they're after.",
    "Propose Deeper Dive": "Confidently affirm that we can help them, propose scheduling a deeper dive call as the clear next step, and secure their agreement.",
    "Ask Timezone": "Ask for their timezone to ensure correct scheduling.",
    "Ask Schedule Time": "Ask for a preferred appointment time and intelligently handle AM/PM ambiguity based on common sense rules for a smooth scheduling experience.",
    "Confirm Video Call Setup": "Confirm that the scheduled time works for them to join the Zoom video call from their computer.",
    "Ask About Partners": "Ask if there's anyone else who would be involved in their business decision, like a spouse or business partners.",
    "Confirm Partner Available": "Confirm that their partner can 100% be available on the call at the scheduled time. If not, reschedule.",
    "Introduce Pre-Call Video": "Explain that Kendrick requires everyone to watch a short 12-minute overview video before the call so they have the basics down and can dive deep.",
    "Ask Watch Now": "Ask if they can watch the overview video right after hanging up this call.",
    "Reinforce Video Value": "Reinforce the video's importance by stating that Kendrick's strategy sessions are usually $1,000, but the fee is completely waived because they'll have seen the overview.",
    "Request Text Reply": "Ask them to reply 'Got it' to the text message with the video link so you know they received it.",
    "End Call": "Deliver a final, professional closing statement confirming they're all set, mention the confirmation email, and terminate the call warmly.",
    "Wrong Number": "Apologize for having the wrong number and end the call politely.",
    "Not Interested": "Acknowledge their lack of interest, thank them for their time, and end the call gracefully.",
    "Disqualified": "Acknowledge that they don't meet the financial requirements, state it's not the right fit at this time, thank them, and end call."
}

async def update_all_goals():
    print("=" * 80)
    print("UPDATING ALL JAKE AGENT NODES WITH GOALS FROM PDF")
    print("=" * 80)
    
    # Connect to MongoDB
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent_id = "04b9509d-cfd9-4e3e-9146-f805c858b823"
    
    # Get the agent
    agent = await db.agents.find_one({"id": agent_id})
    if not agent:
        print(f"❌ Agent {agent_id} not found!")
        return
    
    print(f"✅ Found agent: {agent.get('name')}")
    print()
    
    # Update nodes with goals
    call_flow = agent.get("call_flow", [])
    updates_made = 0
    
    for node in call_flow:
        node_type = node.get("type")
        label = node.get("label", "")
        node_data = node.get("data", {})
        
        # Add goals to conversation and ending nodes
        if node_type in ["conversation", "ending"]:
            if label in GOALS_MAP:
                goal = GOALS_MAP[label]
                node_data["goal"] = goal
                updates_made += 1
                print(f"  ✅ {label}")
            else:
                print(f"  ⚠️  No goal mapped for: {label}")
    
    # Save updates
    if updates_made > 0:
        await db.agents.update_one(
            {"id": agent_id},
            {"$set": {"call_flow": call_flow}}
        )
        print(f"\n✅ Updated {updates_made} nodes with goals from PDF")
    else:
        print("\n⚠️  No updates made")
    
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(update_all_goals())
