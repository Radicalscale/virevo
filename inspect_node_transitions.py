from pymongo import MongoClient
import os
import sys
from bson import ObjectId

# Setup specific to the user's environment
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = "test_database" 

def inspect_transitions():
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        nodes_collection = db["nodes"]

        # Target Label
        target_label = "N_KB_Q&A_With_StrategicNarrative_V3_Adaptive"
        AGENT_ID = ObjectId('6944df147eadbccc46887cdf')
        
        agent = db['agents'].find_one({'_id': AGENT_ID})
        if not agent:
            print("Agent not found.")
            return

        nodes = agent.get('call_flow', []) or agent.get('flow', {}).get('nodes', [])
        
        # Find node by label
        node = next((n for n in nodes if n.get('label') == target_label or n.get('data', {}).get('label') == target_label), None)
        
        if not node:
            print(f"Node '{target_label}' not found in Agent.")
            return

        nid = node.get('id')
        data = node.get('data', {})
        label = data.get('label') or node.get('label')
        print(f"Node: {label} ({nid})")
        print("Transitions:")
        
        data = node.get("data", {})
        transitions = data.get("transitions", [])
        
        for idx, t in enumerate(transitions):
            target_node_id = t.get("targetId")
            # Find target label
            target_node = nodes_collection.find_one({"id": target_node_id})
            target_label = target_node.get("label", "Unknown") if target_node else "Unknown"
            
            print(f"  {idx}. Target: {target_label} ({target_node_id})")
            print(f"     Condition: {t.get('condition')}")
            print("-" * 40)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_transitions()
