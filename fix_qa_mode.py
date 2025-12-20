from pymongo import MongoClient
from bson import ObjectId

CLIENT = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB = CLIENT['test_database']
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

QA_LABEL = "N_KB_Q&A_With_StrategicNarrative_V3_Adaptive"

def fix():
    agent = DB['agents'].find_one({'_id': AGENT_ID})
    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    
    updated = False
    for n in nodes:
        label = n.get('data', {}).get('label') or n.get('label')
        if label == QA_LABEL:
            print(f"🔧 Updating {label} to conversation mode")
            n['data']['mode'] = 'conversation'
            updated = True
            
    if updated:
        if 'call_flow' in agent:
            DB['agents'].update_one({'_id': AGENT_ID}, {"$set": {"call_flow": nodes}})
        else:
            DB['agents'].update_one({'_id': AGENT_ID}, {"$set": {"flow.nodes": nodes}})
        print("✅ Update Saved.")
    else:
        print("❌ Node not found.")

if __name__ == "__main__":
    fix()
