import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def fix_transition_condition():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent = db['agents'].find_one({'_id': AGENT_ID})
    if not agent:
        print("Agent not found")
        return

    # Target Node: N500B_AskTimezone_V2_FullyTuned
    node_id = "1763198398056"
    
    # New condition: Accept timezone OR booking confirmation
    new_condition = "The user has provided their timezone OR the user confirms the scheduled time (e.g., 'sounds good', 'lock it in', 'perfect', 'yes', agreement phrases)"
    
    # Update logic - update first transition's condition
    result = db['agents'].update_one(
        {
            '_id': AGENT_ID, 
            'call_flow.id': node_id
        },
        {
            '$set': {
                'call_flow.$.data.transitions.0.condition': new_condition
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"✅ Successfully updated N500B transition condition")
        print(f"   New condition: {new_condition}")
    else:
        print("❌ Failed to update node")

if __name__ == "__main__":
    fix_transition_condition()
