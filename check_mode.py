from pymongo import MongoClient
from bson import ObjectId

CLIENT = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB = CLIENT['test_database']
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def check():
    agent = DB['agents'].find_one({'_id': AGENT_ID})
    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    for n in nodes:
        label = n.get('data', {}).get('label') or n.get('label')
        if label in ['N_IntroduceModel_And_AskQuestions_V3_Adaptive', 'N_KB_Q&A_With_StrategicNarrative_V3_Adaptive']:
            print(f"{label} Mode: {n.get('data', {}).get('mode')}")

if __name__ == "__main__":
    check()
