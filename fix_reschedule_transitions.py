from pymongo import MongoClient
from bson import ObjectId
import certifi

# Database connection
MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"
TARGET_LABEL = "N_Scheduling_RescheduleAndHandle_V5_FullyTuned"
CALENDAR_CHECK_ID = "1763199903739"

def get_db_connection():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DB_NAME]
        return db
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def fix_reschedule_transition():
    db = get_db_connection()
    if db is None:
        return

    collection = db[COLLECTION_NAME]
    
    try:
        agent = collection.find_one({"_id": ObjectId(AGENT_ID)})
    except:
        agent = collection.find_one({"_id": AGENT_ID})
        
    if not agent:
        print(f"Agent {AGENT_ID} not found!")
        return

    print(f"✅ Loaded agent: {agent.get('name')}")
    
    nodes = agent.get('call_flow', [])
    target_index = -1
    
    for i, node in enumerate(nodes):
        if node.get('label') == TARGET_LABEL:
            target_index = i
            break
            
    if target_index == -1:
        print(f"❌ Node '{TARGET_LABEL}' not found!")
        return
        
    print(f"✅ Found node at index {target_index}: {nodes[target_index].get('label')}")
    
    # Define new transition
    new_transition = {
        "id": "reschedule_retry_v1",
        "condition": "The user provides a new date/time or selects one of the offered slots.",
        "nextNode": CALENDAR_CHECK_ID,
        "check_variables": ["scheduleTime", "amPm"] # Force extraction validation
    }
    
    # Overwrite transitions (since there are none or we want to ensure this one exists)
    # If there are none, we just set it.
    
    update_path = f"call_flow.{target_index}.transitions"
    
    print(f"Applying update to path: {update_path}")
    result = collection.update_one(
        {"_id": agent["_id"]},
        {"$set": {update_path: [new_transition]}}
    )
    
    if result.modified_count > 0:
        print("✅ Successfully updated transitions.")
    else:
        print("⚠️ Update executed but modified count is 0.")

if __name__ == "__main__":
    fix_reschedule_transition()
