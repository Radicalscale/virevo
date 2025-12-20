from pymongo import MongoClient
from bson import ObjectId
import certifi

# Database connection
MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"
TARGET_LABEL = "N_Scheduling_RescheduleAndHandle_V5_FullyTuned"

def get_db_connection():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DB_NAME]
        return db
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def check_reschedule_transitions_embedded():
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
    target_node = None
    
    for node in nodes:
        if node.get('label') == TARGET_LABEL:
            target_node = node
            break
            
    if target_node:
        print(f"✅ Found node: {target_node.get('label')} (ID: {target_node.get('id')})")
        print("Transitions:")
        for t in target_node.get("transitions", []):
            print(f" - {t}")
    else:
        print(f"❌ Node '{TARGET_LABEL}' not found in agent's call_flow!")

if __name__ == "__main__":
    check_reschedule_transitions_embedded()
