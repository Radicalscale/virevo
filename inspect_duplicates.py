import os
import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
# Check both DBs
DBS = ['test_database', 'ai_calling_db']

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    agent_id = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
    
    for db_name in DBS:
        print(f"\nScanning DB: {db_name}")
        db = client[db_name]
        cursor = db.agents.find({"id": agent_id})
        count = 0
        async for agent in cursor:
            count += 1
            print(f"  Found Agent instance #{count}")
            print(f"  Name: {agent.get('name')}")
            nodes = agent.get('nodes', [])
            print(f"  Node count: {len(nodes)}")
            
            if len(nodes) > 0:
                for node in nodes:
                    lbl = node.get('label')
                    p = node.get('rephrase_prompt')
                    dr = node.get('dynamic_rephrase')
                    
                    # Check nested data
                    if not p:
                        p = node.get('data', {}).get('rephrase_prompt')
                    if not dr:
                        dr = node.get('data', {}).get('dynamic_rephrase')

                    if dr or p:
                        print(f"    Node '{lbl}':")
                        print(f"      Dynamic Rephrase: {dr}")
                        print(f"      Prompt: {p}")
        
        if count == 0:
            print("  No agents found with that ID.")

if __name__ == "__main__":
    asyncio.run(main())
