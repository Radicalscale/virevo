import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def fix_extraction_and_reschedule():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent = db['agents'].find_one({'_id': AGENT_ID})
    if not agent:
        print("Agent not found")
        return

    # 1. Update N500B to extract scheduleTime and amPm
    node_n500b_id = "1763198398056"
    new_extract_vars = [
        {
            "name": "timeZone",
            "description": "The user's timezone. Look for timezone names or abbreviations.",
            "extraction_hint": "Extract timezone mentions: EST, PST, CST, MST, Eastern, Pacific, Central, Mountain, EDT, PDT, etc. Return the timezone string as stated.",
            "mandatory": True,
            "prompt_message": "Ask for the timezone again if you don't have a value."
        },
        {
            "name": "scheduleTime",
            "description": "The specific day and time the user wants to schedule.",
            "extraction_hint": "Extract the full date/time string provided by the user (e.g., 'Tuesday at 2pm', 'Tomorrow at 10am').",
            "mandatory": True,
            "prompt_message": "What day and time works best for you?"
        },
        {
            "name": "amPm",
            "description": "AM or PM indicator for the time.",
            "extraction_hint": "Extract 'am' or 'pm' or infer from context (e.g., 'morning' -> am, 'afternoon' -> pm).",
            "mandatory": True,
            "prompt_message": "Is that morning or afternoon?"
        }
    ]
    
    db['agents'].update_one(
        {'_id': AGENT_ID, 'call_flow.id': node_n500b_id},
        {'$set': {'call_flow.$.data.extract_variables': new_extract_vars}}
    )
    print("✅ updated N500B variable extraction")

    # 2. Update Reschedule Node to READ webhook response
    node_reschedule_id = "1763200225645"
    
    new_content = """## Primary Goal
Handle user objections to proposed alternative appointment times after webhook confirms unavailability. 

## CRITICAL INSTRUCTION: HANDLING WEBHOOK RESPONSE
- You have just received a `webhook_response` variable containing the results of the scheduling attempt.
- **IF THE TIME WAS UNAVAILABLE:** The `webhook_response` will look like `{"results": [{"result": "Apologize... available times are X, Y, Z..."}]}`.
- **YOU MUST READ AND SPEAK THE "RESULT" MESSAGE FROM THE WEBHOOK.**
- **DO NOT** make up your own times. **DO NOT** say "Locked in" if the webhook says unavailable.
- **SAY EXACTLY** what the webhook result tells you to say regarding availability.

## Strategic Toolkit
- **Tactic for: "NEXT WEEK" / TIME Deferral** -> "Totally get it... if we found something sooner...?"
- **Tactic for: "I'm busy this week"** -> "I hear you... I literally do not have times next week but have [Time 1] or [Time 2]..."

## Core Logic
1. **Analyze Webhook Result:** Look at `webhook_response` or session variables updated by it.
2. **Present Options:** If unavailable, apologize and offer the specific slots provided in the webhook response.
3. **Handle Response:** If user picks a new time, transition to Calendar-check again (or confirm if instructed).
"""
    
    db['agents'].update_one(
        {'_id': AGENT_ID, 'call_flow.id': node_reschedule_id},
        {'$set': {'call_flow.$.data.content': new_content}}
    )
    print("✅ updated Reschedule node content")

if __name__ == "__main__":
    fix_extraction_and_reschedule()
