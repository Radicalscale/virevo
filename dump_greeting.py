from pymongo import MongoClient
from bson import ObjectId
import certifi
import json

MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"
GREETING_NODE_ID = "2"

def dump_greeting():
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    agent = db[COLLECTION_NAME].find_one({"_id": ObjectId(AGENT_ID)})
    
    greeting = next((n for n in agent['call_flow'] if n['id'] == GREETING_NODE_ID), None)
    if greeting:
        print(json.dumps(greeting.get('transitions', []), indent=2))
    else:
        print("Greeting not found")

if __name__ == "__main__":
    dump_greeting()
