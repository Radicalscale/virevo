from pymongo import MongoClient
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

def list_nodes():
    db = get_db_connection()
    if db is None:
        return

    collection = db[COLLECTION_NAME]
    nodes = collection.find({}, {"id": 1, "label": 1})
    
    print("Listing all nodes:")
    for n in nodes:
        print(f"ID: {n.get('id')} | Label: {n.get('label')}")

if __name__ == "__main__":
    list_nodes()
