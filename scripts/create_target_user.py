
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime
import uuid

# Public MongoDB URL from Railway
MONGO_URL = "mongodb://mongo:VvAstqnjLZVbnVPfmaOERekKMOdwlGaX@gondola.proxy.rlwy.net:43413"
DB_NAME = "virevo"

EMAIL = "kendrickbowman9@gmail.com"
PASSWORD = "B!LL10n$$"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

async def upsert_user():
    print(f"🔌 Connecting to MongoDB...")
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        print("✅ Connected successfully.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # Check if exists
    existing = await db.users.find_one({"email": EMAIL})
    
    password_hash = get_password_hash(PASSWORD)
    
    if existing:
        print(f"⚠️  User {EMAIL} exists. Updating password...")
        await db.users.update_one(
            {"email": EMAIL},
            {"$set": {"password_hash": password_hash, "is_active": True}}
        )
        print(f"✅ Updated password for {EMAIL}")
    else:
        # Create User
        print(f"🆕 Creating user {EMAIL}...")
        new_user = {
            "id": str(uuid.uuid4()),
            "email": EMAIL,
            "password_hash": password_hash,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "is_superuser": True
        }
        await db.users.insert_one(new_user)
        print(f"🎉 Created user: {EMAIL}")

if __name__ == "__main__":
    asyncio.run(upsert_user())
