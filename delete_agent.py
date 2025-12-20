"""
Delete the entire agent from MongoDB.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGO_URL = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
AGENT_ID = "6944df147eadbccc46887cdf"

async def delete_agent():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["test_database"]  # Correct database name
    
    print(f"Deleting agent: {AGENT_ID}")
    result = await db.agents.delete_one({"_id": ObjectId(AGENT_ID)})
    
    if result.deleted_count > 0:
        print("✓ Agent deleted successfully!")
    else:
        print("✗ Agent not found")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(delete_agent())
