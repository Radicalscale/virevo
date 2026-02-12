
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# Public MongoDB URL from Railway
MONGO_URL = "mongodb://mongo:VvAstqnjLZVbnVPfmaOERekKMOdwlGaX@gondola.proxy.rlwy.net:43413"
DB_NAME = "virevo"

# Handle both cases just in case
EMAILS = ["Kendrick@outlier-agency.com", "kendrick@outlier-agency.com"]
PASSWORD = "B!LL10n$$"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

async def update_password():
    print(f"🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    password_hash = get_password_hash(PASSWORD)
    
    for email in EMAILS:
        result = await db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": password_hash}}
        )
        if result.matched_count > 0:
            print(f"✅ Updated password for {email} to '{PASSWORD}'")
        else:
            print(f"ℹ️  User {email} not found (skipped).")

if __name__ == "__main__":
    asyncio.run(update_password())
