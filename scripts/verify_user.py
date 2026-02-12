
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://mongo:VvAstqnjLZVbnVPfmaOERekKMOdwlGaX@gondola.proxy.rlwy.net:43413"
DB_NAME = "virevo"
EMAIL = "Kendrick@outlier-agency.com"

async def check_user():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    user = await db.users.find_one({"email": EMAIL})
    if user:
        print(f"User found: {user['email']}")
        print(f"Hash: {user['password_hash']}")
    else:
        print("User not found")

if __name__ == "__main__":
    asyncio.run(check_user())
