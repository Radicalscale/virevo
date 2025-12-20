from pymongo import MongoClient
from bson import ObjectId
import certifi
import json

MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"
CONFIRM_NAME_NODE_ID = "1766180529241"
TARGET_NODE_ID = "1763159750250" # N001B_IntroAndHelpRequest_Only

def get_db_connection():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DB_NAME]
        return db
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def fix_deadlock():
    db = get_db_connection()
    if db is None:
        return

    collection = db[COLLECTION_NAME]
    agent = collection.find_one({"_id": ObjectId(AGENT_ID)})
    
    if not agent:
        print("Agent not found.")
        return

    # Find Node
    target_node = None
    node_index = -1
    for i, node in enumerate(agent['call_flow']):
        if node['id'] == CONFIRM_NAME_NODE_ID:
            target_node = node
            node_index = i
            break
            
    if not target_node:
        print("Confirm Name node not found.")
        return

    print("✅ Found Confirm Name Node.")

    # Create the Rescue Transition
    rescue_transition = {
        "id": "confirm_name_rescue_v1",
        "condition": "User asks a question, raises an objection, or ignores the name confirmation request (e.g. 'What is this?', 'Is this a scam?', 'How much?'). Proceed to Intro.",
        "nextNode": TARGET_NODE_ID
    }

    # Insert at the END of current list (Low Priority / Catch-All for non-matches)
    # But wait, the current list has "Wrong number" and "Confirm Name".
    # If the LLM returned -1, nothing matched.
    # So we need to cover the "Everything else" case.
    
    current_transitions = target_node.get('transitions', [])
    
    # Check if already exists
    exists = False
    for t in current_transitions:
        if t.get('nextNode') == TARGET_NODE_ID:
            print("⚠️ Rescue transition already exists. Updating it.")
            t.update(rescue_transition)
            exists = True
            break
    
    if not exists:
        print("➕ Adding Rescue Transition.")
        current_transitions.append(rescue_transition)

    # Update Node
    agent['call_flow'][node_index]['transitions'] = current_transitions

    # Write back
    result = collection.update_one(
        {"_id": ObjectId(AGENT_ID)},
        {"$set": {"call_flow": agent['call_flow']}}
    )

    if result.modified_count > 0:
        print(f"✅ Successfully patched ConfirmName node. Transitions count: {len(current_transitions)}")
    else:
        print("⚠️ No changes made.")

if __name__ == "__main__":
    fix_deadlock()
