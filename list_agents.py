"""
Script to list all agents in the database
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def list_agents():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client.call_agent_db
    
    # Find all agents
    agents = await db.agents.find().to_list(length=None)
    
    print(f"Found {len(agents)} agent(s):\n")
    
    for agent in agents:
        print(f"{'='*60}")
        print(f"ID: {agent.get('id', 'N/A')}")
        print(f"Name: {agent.get('name', 'N/A')}")
        print(f"Description: {agent.get('description', 'N/A')[:100]}...")
        print(f"Type: {agent.get('agent_type', 'N/A')}")
        print(f"Status: {agent.get('status', 'N/A')}")
        prompt = agent.get('system_prompt', '')
        print(f"Global Prompt Length: {len(prompt)} chars")
        if prompt:
            print(f"Global Prompt Preview: {prompt[:200]}...")
        print()

if __name__ == "__main__":
    asyncio.run(list_agents())
