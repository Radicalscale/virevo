import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def scan_nodes():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    agent = db['agents'].find_one({'_id': AGENT_ID})
    
    if not agent:
        print("Agent not found")
        return

    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    
    candidates = []
    
    print(f"{'ID':<25} | {'Label':<50} | {'Mode':<15} | {'Auto-Trans'}")
    print("-" * 100)

    for n in nodes:
        nid = n.get('id')
        data = n.get('data', {})
        label = data.get('label') or n.get('label')
        mode = data.get('mode', 'conversation') # Default to conversation if missing
        auto_trans = data.get('auto_transition_after_response')
        
        # Criteria 1: "Prompts" (Not script)
        # Note: 'prompt' and 'conversation' are LLM generated. 'script' is static TTS.
        if mode == 'script':
            continue

        # Criteria 2: "Don't have automatic transitions"
        if auto_trans:
            continue

        # Criteria 3: "Pre-booking" (Heuristic based on naming)
        # Exclude nodes that clearly ARE booking/closing or post-booking
        if any(x in str(label).lower() for x in ['scheduling', 'calendar', 'confirm', 'closing', 'end', 'bye', 'voicemail']):
            continue

        candidates.append((nid, label, mode))
        print(f"{nid:<25} | {label:<50} | {mode:<15} | {auto_trans}")

    print("-" * 100)
    print(f"Found {len(candidates)} candidate nodes.")

    # Save list for next step
    with open("candidate_nodes.txt", "w") as f:
        for nid, label, mode in candidates:
            f.write(f"{nid},{label}\n")

if __name__ == "__main__":
    scan_nodes()
