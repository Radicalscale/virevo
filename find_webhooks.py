import os
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def find_webhooks():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent = db['agents'].find_one({'_id': AGENT_ID})
    if not agent:
        print("Agent not found")
        return

    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    
    found_any = False
    for n in nodes:
        data = n.get('data', {})
        webhook = data.get('webhook_url')
        
        if webhook:
            found_any = True
            print(f"✅ Found Webhook in Node: {data.get('label')} ({n.get('id')})")
            print(f"   URL: {webhook}")
            print(f"   Method: {data.get('webhook_method', 'GET')}")
            print("-" * 50)

    if not found_any:
        print("❌ No webhooks found in any node.")

if __name__ == "__main__":
    find_webhooks()
