from pymongo import MongoClient
from bson import ObjectId
import json

CLIENT = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB = CLIENT['test_database']
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def dump():
    agent = DB['agents'].find_one({'_id': AGENT_ID})
    print(f"Agent Name: {agent.get('agentName')}")
    print(f"Keys: {list(agent.keys())}")
    
    if 'call_flow' in agent:
        print(f"call_flow count: {len(agent['call_flow'])}")
        # Check first node ID
        n0 = agent['call_flow'][0]
        print(f"Node 0 ID: {n0.get('id')}")
        print(f"Node 0 Keys: {list(n0.keys())}")
        if 'data' in n0:
             print(f"Node 0 Data Keys: {list(n0['data'].keys())}")
             print(f"Node 0 Data ID: {n0['data'].get('id')}")

    if 'flow' in agent:
        print(f"flow.nodes count: {len(agent['flow'].get('nodes', []))}")

dump()
