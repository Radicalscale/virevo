import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def fix_n500b_hallucination():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    node_n500b_id = "1763198398056"
    
    # New content that handles the case where Time/Timezone is already present
    new_content = """## Primary Goal
- Confirm the timezone and time for the appointment.
- **CRITICAL:** DO NOT CONFIRM THE BOOKING YET. YOU DO NOT HAVE ACCESS TO THE CALENDAR.
- **CRITICAL:** If the user has provided a time and timezone, say: "Perfect, let me check the calendar for that time real quick. One second."
- **CRITICAL:** NEVER say "Locked in", "Confirmed", or "It's on the calendar". You are ONLY checking availability.

## Entry Context
- Enter this node after {{customer_name}} agrees to schedule the deeper dive call.
- The user may have already provided a time (e.g. "Tuesday at 2pm").

## Strategic Toolkit
- **Tactic for: Vague Response** -> "No problem. What city and state? I can figure it out."
- **Tactic for: "Why does it matter?"** -> "Just strictly for sending the calendar invite to the right time slot."

## Core Logic
1. **Check History:** Does the user's previous message contain a Time and Timezone?
    - **YES:** Say: "Got it, [Time] [Timezone]. Let me just check availability for that real quick. Bear with me." (Then the system will auto-transition).
    - **NO (Missing Timezone):** Say: "Gotcha. And just so I've got it right for our scheduling, what timezone are you in?"
2. **Handle Response:** If they give the timezone, say: "Perfect, thanks. Checking that slot now..."
3. **NEVER** confirm the appointment in this node. The actual confirmation happens in the NEXT node if successful.
"""
    
    db['agents'].update_one(
        {'_id': AGENT_ID, 'call_flow.id': node_n500b_id},
        {'$set': {'call_flow.$.data.content': new_content}}
    )
    print("✅ updated N500B content to prevent premature confirmation")

if __name__ == "__main__":
    fix_n500b_hallucination()
