from pymongo import MongoClient
from bson import ObjectId

CLIENT = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB = CLIENT['test_database']
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def check():
    agent = DB['agents'].find_one({'_id': AGENT_ID})
    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    
    qa_id = None
    intro_target = None
    
    for n in nodes:
        label = n.get('data', {}).get('label') or n.get('label')
        nid = n.get('id')
        
        if 'Q&A' in str(label):
             print(f"FOUND Q&A-LIKE: {repr(label)} ID: {nid}")
             qa_id = nid # Grab the last one found
        
        if label == 'N_KB_Q&A_With_StrategicNarrative_V3_Adaptive':
            qa_id = nid
            print(f"✅ FOUND Exact Q&A Node: {label}")
            print(f"   ID: {nid}")
            
        if label == 'N_IntroduceModel_And_AskQuestions_V3_Adaptive':
            intro_target = n.get('data', {}).get('auto_transition_after_response')
            print(f"✅ FOUND Intro Node: {label}")
            print(f"   ID: {nid}")
            print(f"   Target ID: {intro_target}")

    print("-" * 20)
    if qa_id and intro_target:
        if qa_id == intro_target:
            print("✅ ID MATCH! Link is valid.")
        else:
            print(f"❌ ID MISMATCH! Target ({intro_target}) != QA ID ({qa_id})")
    else:
        print("❌ Could not check match (Missing node).")

if __name__ == "__main__":
    check()
