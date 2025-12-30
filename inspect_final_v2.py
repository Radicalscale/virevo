import os
import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    agent_id = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
    
    agent = await db.agents.find_one({"id": agent_id})
    if not agent:
        print("Agent not found")
        return

    # Check call_flow nodes
    call_flow = agent.get('call_flow')
    
    nodes = []
    if isinstance(call_flow, list):
        print("call_flow is a LIST (Likely list of nodes)")
        nodes = call_flow
    elif isinstance(call_flow, dict):
        print("call_flow is a DICT")
        nodes = call_flow.get('nodes', [])
    else:
        print(f"call_flow is {type(call_flow)}")

    print(f"Nodes found: {len(nodes)}")
    
    for node in nodes:
        lbl = node.get('label') or node.get('id')
        p = node.get('rephrase_prompt')
        dr = node.get('dynamic_rephrase')
        
        # Check nested data
        if not p:
            p = node.get('data', {}).get('rephrase_prompt')
        if not dr:
            dr = node.get('data', {}).get('dynamic_rephrase')

        if dr or p:
            print(f"\nNode '{lbl}':")
            print(f"  Dynamic Rephrase: {dr}")
            print(f"  Prompt: \"{p}\"")

if __name__ == "__main__":
    asyncio.run(main())
