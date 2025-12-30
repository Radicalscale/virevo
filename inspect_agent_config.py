import os
import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    agent_id = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
    
    print(f"Connecting to {DB_NAME}...")
    agent = await db.agents.find_one({"id": agent_id})
    if not agent:
        print(f"Agent {agent_id} not found in {DB_NAME}")
        # Try prod db just in case
        db = client['ai_calling_db']
        print(f"Checking ai_calling_db...")
        agent = await db.agents.find_one({"id": agent_id})
        if not agent:
            print("Agent not found in either DB")
            return

    print(f"Agent: {agent.get('name')}")
    nodes = agent.get('nodes', [])
    print(f"Found {len(nodes)} nodes")
    
    for node in nodes:
        data = node.get('data', {}) # Nodes usually have a data dict
        # Sometimes structure is flat, sometimes nested. Let's check both or dump keys
        
        label = data.get('label') or node.get('label')
        node_id = node.get('id')
        
        # Check wherever dynamic_rephrase might be
        rephrase = data.get('dynamic_rephrase') or node.get('dynamic_rephrase')
        prompt = data.get('rephrase_prompt') or node.get('rephrase_prompt')
        
        if rephrase:
            print(f"Node '{label}' ({node_id}):")
            print(f"  Dynamic Rephrase: ENABLED")
            print(f"  Rephrase Prompt: \"{prompt}\"")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
