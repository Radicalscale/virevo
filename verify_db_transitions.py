from pymongo import MongoClient
from bson import ObjectId
import certifi
import json

MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"
CONFIRM_NAME_NODE_ID = "1766180529241"

def check_transitions():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        agent = collection.find_one({"_id": ObjectId(AGENT_ID)})
        if not agent:
            print("❌ Agent not found")
            return

        print(f"✅ Found Agent: {agent.get('name')}")
        
        target_node = None
        for node in agent.get('call_flow', []):
            if node['id'] == CONFIRM_NAME_NODE_ID:
                target_node = node
                break
        
        if not target_node:
            print("❌ Confirm Name Node not found")
            
        print(f"✅ Found Node: {target_node.get('name', 'Unknown')}")
        print("Transitions:")
        for i, t in enumerate(target_node.get('transitions', [])):
            print(f"  {i}: {t.get('condition')[:50]}... -> {t.get('nextNode')}")

        print("\n--- ALL NODES MAP ---")
        for n in agent.get('call_flow', []):
            print(f"ID: {n['id']} | Name: {n.get('name', 'Unnamed')} | Type: {n.get('type')}")

        print("\n--- AGENT KEYS ---")
        print(list(agent.keys()))
        if 'system_prompt' in agent:
             print(f"System Prompt Length: {len(agent['system_prompt'])}")


    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_transitions()
