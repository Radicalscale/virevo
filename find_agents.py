"""
Find all databases and agents to locate the corrupted one.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"

async def find_agents():
    client = AsyncIOMotorClient(MONGO_URL)
    
    # List all databases
    dbs = await client.list_database_names()
    print(f"Available databases: {dbs}")
    
    # Check each database for agents collection
    for db_name in dbs:
        db = client[db_name]
        collections = await db.list_collection_names()
        if 'agents' in collections:
            print(f"\n=== Database '{db_name}' has agents collection ===")
            count = await db.agents.count_documents({})
            print(f"Total agents: {count}")
            
            # List all agents
            async for agent in db.agents.find({}, {"_id": 1, "name": 1}):
                print(f"  ID: {agent['_id']}, Name: {agent.get('name', 'N/A')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(find_agents())
