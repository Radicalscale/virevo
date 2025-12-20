import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

# List of IDs to Clean
TARGET_IDS = [
    "1763198305881", # N500A_ProposeDeeperDive_V5_Adaptive
    "1763198398056", # N500B_AskTimezone_V2_FullyTuned
    "1763198517011", # N_AskForCallbackRange_V1_Adaptive
    "1763198584995", # N_Scheduling_AskTime_V2_SmartAmbiguity
]

TOOLKIT_HEADER = "### PREMATURE BOOKING / SCHEDULING REQUESTS:"

def restore_nodes():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent = db['agents'].find_one({'_id': AGENT_ID})
    if not agent:
        print("Agent not found")
        return

    nodes = agent.get('call_flow', [])
    path_type = 'call_flow'
    if not nodes:
        nodes = agent.get('flow', {}).get('nodes', [])
        path_type = 'flow.nodes'

    modified_count = 0
    
    for i, n in enumerate(nodes):
        nid = n.get('id')
        if nid in TARGET_IDS:
            data = n.get('data', {})
            content = data.get('content', '')
            
            if TOOLKIT_HEADER in content:
                print(f"Propagated Toolkit found in {n.get('data', {}).get('label')} ({nid}). Removing...")
                
                # Split and keep only the part before the toolkit
                clean_content = content.split(TOOLKIT_HEADER)[0].strip()
                
                # Update node
                n['data']['content'] = clean_content
                modified_count += 1
            else:
                print(f"Toolkit NOT found in {nid}. Skipping.")
                
            nodes[i] = n

    if modified_count > 0:
        if path_type == 'call_flow':
            db['agents'].update_one({'_id': AGENT_ID}, {'$set': {'call_flow': nodes}})
        else:
            db['agents'].update_one({'_id': AGENT_ID}, {'$set': {'flow.nodes': nodes}})
            
        print(f"Successfully restored {modified_count} nodes.")
    else:
        print("No nodes needed restoration.")

if __name__ == "__main__":
    restore_nodes()
