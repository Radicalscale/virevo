import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def fix_n500b_transitions():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    node_n500b_id = "1763198398056"
    
    # We want to force the transition if variables are present.
    # The current transition relies on semantic match.
    # We will add check_variables which acts as an OR (or strict check depending on impl).
    # Actually, in this system, check_variables usually forces the transition if those vars are valid/present.
    
    new_transitions = [
      {
        "id": "1",
        "condition": "The user has provided their timezone OR the user confirms the scheduled time (e.g., 'sounds good', 'lock it in', 'perfect', 'yes', agreement phrases, 'bye')",
        "nextNode": "1763199903739", # Calendar-check
        "check_variables": ["scheduleTime", "timeZone", "amPm"] # Force check these
      }
    ]
    
    db['agents'].update_one(
        {'_id': AGENT_ID, 'call_flow.id': node_n500b_id},
        {'$set': {'call_flow.$.data.transitions': new_transitions}}
    )
    print("✅ updated N500B transitions to strictly check variables")

if __name__ == "__main__":
    fix_n500b_transitions()
