from pymongo import MongoClient
import os
import certifi

# Database connection
MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "nodes"

def get_db_connection():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DB_NAME]
        return db
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def display_node_info(node_id):
    db = get_db_connection()
    if db is None:
        return

    try:
        node = db[COLLECTION_NAME].find_one({"id": node_id})
        
        if node:
            print(f"Found Node: {node.get('label', 'Unknown')} (ID: {node_id})")
            print("-" * 50)
            
            # Print specific fields
            print(f"Type: {node.get('type')}")
            print(f"Mode: {node.get('mode')}")
            print(f"Content: \n{node.get('content')}")
            
            print("-" * 50)
            print("Transitions:")
            for t in node.get("transitions", []):
                print(f"  - ID: {t.get('id')}")
                print(f"    Condition: {t.get('condition')}")
                print(f"    Next Node: {t.get('nextNode')}")
                print(f"    Check Variables: {t.get('check_variables')}")
            
        else:
            print(f"Node with ID {node_id} not found.")

    except Exception as e:
        print(f"Error retrieving node: {e}")

if __name__ == "__main__":
    display_node_info("1763198305881") # N500A_ProposeDeeperDive_V5_Adaptive
