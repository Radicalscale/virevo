
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "virevo")

async def list_users():
    if not MONGO_URL:
        print("MONGO_URL not found")
        return

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users_collection = db["users"]

    print(f"Connected to {DB_NAME}")
    
    count = await users_collection.count_documents({})
    print(f"Total users: {count}")

    cursor = users_collection.find({}, {"email": 1, "username": 1, "_id": 1}).limit(20)
    users = await cursor.to_list(length=20)

    print("First 20 users:")
    for user in users:
        print(f"ID: {user['_id']}, Email: {user.get('email')}, Username: {user.get('username')}")

if __name__ == "__main__":
    asyncio.run(list_users())
