from pymongo import MongoClient
from bson import ObjectId
import certifi

MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"

def dump_prompt():
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    agent = db[COLLECTION_NAME].find_one({"_id": ObjectId(AGENT_ID)})
    
    if agent and 'system_prompt' in agent:
        with open("dumped_system_prompt.txt", "w") as f:
            f.write(agent['system_prompt'])
        print("✅ Dumped system_prompt to dumped_system_prompt.txt")
    else:
        print("❌ No system_prompt found")

if __name__ == "__main__":
    dump_prompt()
