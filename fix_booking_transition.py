import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def fix_booking_transition():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent = db['agents'].find_one({'_id': AGENT_ID})
    if not agent:
        print("Agent not found")
        return

    # Target Node: N500B_AskTimezone_V2_FullyTuned
    node_id = "1763198398056"
    
    # New Target: Calendar-check (The Webhook Node)
    new_next_node = "1763199903739" 
    
    # Update logic
    result = db['agents'].update_one(
        {
            '_id': AGENT_ID, 
            'call_flow.id': node_id
        },
        {
            '$set': {
                'call_flow.$.data.transitions.0.nextNode': new_next_node
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"✅ Successfully updated N500B transition to point to Calendar-check ({new_next_node})")
    else:
        print("❌ Failed to update node (id not found in call_flow?)")
        # Try flow.nodes fallback just in case
        result = db['agents'].update_one(
            {
                '_id': AGENT_ID, 
                'flow.nodes.id': node_id
            },
            {
                '$set': {
                    'flow.nodes.$.data.transitions.0.nextNode': new_next_node
                }
            }
        )
        if result.modified_count > 0:
            print(f"✅ Successfully updated N500B transition in flow.nodes")
        else:
            print("❌ Failed to update in flow.nodes either.")

if __name__ == "__main__":
    fix_booking_transition()
