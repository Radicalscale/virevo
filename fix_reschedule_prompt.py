import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def fix_reschedule_prompt():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    node_reschedule_id = "1763200225645"
    
    # Inject {{results}} into the content to force visibility
    new_content = """## Primary Goal
Handle user objections to proposed alternative appointment times after webhook confirms unavailability. 

## CRITICAL INSTRUCTION: HANDLING WEBHOOK RESPONSE
- You have just received availability data.
- **DATA:** {{results}}
- **INSTRUCTION:** Read the 'result' field from the DATA above.
- **IF DATA SAYS UNAVAILABLE:** Apologize and offer the EXACT times listed in the 'result'.
- **IF DATA SAYS SUCCESS:** Only then confirm the booking.
- **NEVER** confirm if the data says "Apologize".

## Strategic Toolkit
- **Tactic for: "NEXT WEEK" / TIME Deferral** -> "Totally get it... if we found something sooner...?"
- **Tactic for: "I'm busy this week"** -> "I hear you... I literally do not have times next week but have [Time 1] or [Time 2]..."

## Core Logic
1. **Analyze DATA:** Look at the {{results}} value above.
2. **Present Options:** If unavailable, speak the options from the 'result' text.
3. **Handle Response:** If user picks a new time, transition to Calendar-check again (or confirm if instructed).
"""
    
    db['agents'].update_one(
        {'_id': AGENT_ID, 'call_flow.id': node_reschedule_id},
        {'$set': {'call_flow.$.data.content': new_content}}
    )
    print("✅ updated Reschedule node content with variable injection")

if __name__ == "__main__":
    fix_reschedule_prompt()
