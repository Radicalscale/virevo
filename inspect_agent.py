import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

mongo_url = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'
db_name = 'test_database'

async def main():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    agent = await db.agents.find_one({"name": "JK First Caller-copy-copy"})
    
    if agent:
        print("Agent found!")
        print(f"Keys: {agent.keys()}")
        print()
        
        # Check call_flow structure
        call_flow = agent.get('call_flow', [])
        print(f"Call flow has {len(call_flow)} nodes")
        
        if call_flow:
            print("\nFirst node structure:")
            print(json.dumps(call_flow[0], indent=2, default=str))
            
            print("\nLooking for nodes with transitions...")
            for i, node in enumerate(call_flow[:5]):
                print(f"\nNode {i}: {node.get('label', 'Unnamed')}")
                print(f"  ID: {node.get('id')}")
                print(f"  Type: {node.get('type')}")
                if 'transitions' in node:
                    print(f"  Transitions: {node['transitions']}")
                if 'data' in node and 'transitions' in node.get('data', {}):
                    print(f"  Data.transitions: {node['data']['transitions']}")
    
    client.close()

asyncio.run(main())
