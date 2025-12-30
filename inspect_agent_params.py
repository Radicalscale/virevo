import os
import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import pprint

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    agent_id = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
    
    agent = await db.agents.find_one({"id": agent_id})
    if not agent:
        print("Agent not found.")
        return

    print(f"Agent Name: {agent.get('name')}")
    
    nodes = agent.get('nodes', [])
    if isinstance(nodes, list):
        print(f"Node count: {len(nodes)}")
        for i, node in enumerate(nodes):
            # Check for rephrase prompt directly on node or in node['data']
            prompt = node.get('rephrase_prompt')
            dr = node.get('dynamic_rephrase')
            
            # Also check nested 'data' dict if it exists
            node_data = node.get('data', {})
            if not prompt: 
                prompt = node_data.get('rephrase_prompt')
            if not dr:
                dr = node_data.get('dynamic_rephrase')

            if prompt or dr:
                print(f"\nNode {node.get('id')} ('{node.get('label') or node_data.get('label')}'):")
                print(f"  Dynamic Rephrase: {dr}")
                print(f"  Rephrase Prompt: {prompt}")

if __name__ == "__main__":
    asyncio.run(main())
