import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

# Node IDs
SOURCE_NODE_LABEL = "N_KB_Q&A_With_StrategicNarrative_V3_Adaptive"
TARGET_NODE_ID = "1763180018981" # Logic Split - Income

def fix_transitions():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent = db['agents'].find_one({'_id': AGENT_ID})
    if not agent:
        print("Agent not found")
        return

    # Helper to find node in nested list
    nodes = agent.get('call_flow', [])
    if not nodes:
        nodes = agent.get('flow', {}).get('nodes', [])
        path_type = 'flow.nodes'
    else:
        path_type = 'call_flow'

    source_node = None
    source_index = -1
    
    for i, n in enumerate(nodes):
        if n.get('label') == SOURCE_NODE_LABEL or n.get('data', {}).get('label') == SOURCE_NODE_LABEL:
            source_node = n
            source_index = i
            break
            
    if not source_node:
        print(f"Source node {SOURCE_NODE_LABEL} not found")
        return

    print(f"Found source node: {source_node.get('id')}")
    
    # Create new transition
    new_transition = {
        "nextNode": TARGET_NODE_ID,
        "condition": "User has answered income questions, provided financial information, or indicates readiness to proceed with the qualification process."
    }
    
    # Ensure data.transitions exists
    if 'data' not in source_node:
        source_node['data'] = {}
    if 'transitions' not in source_node['data']:
        source_node['data']['transitions'] = []
        
    # Check if logic split transition already exists to avoid dupes
    # We check both keys to be safe and clean up if needed
    existing = [t for t in source_node['data']['transitions'] if t.get('nextNode') == TARGET_NODE_ID or t.get('targetId') == TARGET_NODE_ID]
    if existing:
        print("Transition to Logic Split already exists. correcting key and condition.")
        # Fix key if needed
        if 'targetId' in existing[0]:
            del existing[0]['targetId']
        existing[0]['nextNode'] = TARGET_NODE_ID
        existing[0]['condition'] = new_transition['condition']
    else:
        print("Adding new transition to Logic Split - Income.")
        source_node['data']['transitions'].append(new_transition)
        
    # Update specifically the node in the list
    nodes[source_index] = source_node
    
    # Update Agent
    if path_type == 'call_flow':
        result = db['agents'].update_one({'_id': AGENT_ID}, {'$set': {'call_flow': nodes}})
    else:
        result = db['agents'].update_one({'_id': AGENT_ID}, {'$set': {'flow.nodes': nodes}})
        
    print(f"Update Result: {result.modified_count} document(s) modified.")

if __name__ == "__main__":
    fix_transitions()
