from pymongo import MongoClient
from bson import ObjectId
import certifi

# Database connection
MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"
TARGET_LABEL = "N500A_ProposeDeeperDive_V5_Adaptive"
N500B_ID = "1763198398056"

def get_db_connection():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DB_NAME]
        return db
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def fix_n500a_transition():
    db = get_db_connection()
    if db is None:
        return

    collection = db[COLLECTION_NAME]
    
    # Try finding by ObjectId or String ID
    try:
        agent = collection.find_one({"_id": ObjectId(AGENT_ID)})
    except:
        agent = collection.find_one({"_id": AGENT_ID})
        
    if not agent:
        print(f"Agent {AGENT_ID} not found!")
        return

    print(f"✅ Loaded agent: {agent.get('name')}")
    
    # Locate the node in call_flow
    nodes = agent.get('call_flow', [])
    target_index = -1
    target_node = None
    
    for i, node in enumerate(nodes):
        if node.get('label') == TARGET_LABEL:
            target_index = i
            target_node = node
            break
            
    if target_index == -1:
        print(f"❌ Node '{TARGET_LABEL}' not found in agent's call_flow!")
        return
        
    print(f"✅ Found node at index {target_index}: {target_node.get('label')} (ID: {target_node.get('id')})")
    
    current_transitions = target_node.get("transitions", [])
    print("Current transitions:")
    for t in current_transitions:
        print(f" - {t}")
        
    # Check if fix already exists
    # for t in current_transitions:
    #    if t.get("nextNode") == N500B_ID:
    #        print("Combine/Fix already present. Skipping update to avoid duplication.")
    #        return

    # Create new transition
    new_transition = {
        "id": "fix_time_proposal_v1",
        "condition": "User mentions a time (e.g. 'tomorrow', '2pm'), a day, asks to schedule, or agrees to the proposal. ANY scheduling intent.",
        "nextNode": N500B_ID
    }
    
    # Prepend new transition
    updated_transitions = [new_transition] + current_transitions
    
    # Construct update query
    update_path = f"call_flow.{target_index}.transitions"
    
    print(f"Applying update to path: {update_path}")
    result = collection.update_one(
        {"_id": agent["_id"]},
        {"$set": {update_path: updated_transitions}}
    )
    
    if result.modified_count > 0:
        print("✅ Successfully updated transitions.")
    else:
        print("⚠️ Update executed but modified count is 0 (maybe no changes detected).")

if __name__ == "__main__":
    fix_n500a_transition()
