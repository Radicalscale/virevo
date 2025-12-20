from pymongo import MongoClient
from bson import ObjectId
import certifi
import json

MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"

def dump_node_names():
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    agent = db[COLLECTION_NAME].find_one({"_id": ObjectId(AGENT_ID)})
    
    nodes = []
    if agent:
        for n in agent.get('call_flow', []):
            nodes.append({
                "id": n['id'],
                "name": n.get('name'),
                "type": n.get('type'),
                "text": n.get('text', '')[:50]
            })
    
    print(json.dumps(nodes, indent=2))

if __name__ == "__main__":
    dump_node_names()
