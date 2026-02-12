
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime
import uuid

# Original Atlas MongoDB (used by old project 'respectful-wholeness')
MONGO_URL = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "virevo"

EMAIL = "kendrick@outlier-agency.com"
PASSWORD = "B!LL10n$$"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def setup():
    print(f"🔌 Connecting to Atlas MongoDB...")
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to Atlas successfully.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    db = client[DB_NAME]
    
    # List all databases
    dbs = await client.list_database_names()
    print(f"📁 Databases: {dbs}")
    
    # Check collections in virevo db
    collections = await db.list_collection_names()
    print(f"📁 Collections in '{DB_NAME}': {collections}")
    
    # Check for existing users
    user_count = await db.users.count_documents({})
    print(f"👥 Total users in '{DB_NAME}': {user_count}")
    
    # Check for our target user
    existing = await db.users.find_one({"email": {"$regex": f"^{EMAIL}$", "$options": "i"}})
    
    if existing:
        print(f"✅ User '{EMAIL}' already exists!")
        print(f"   ID: {existing.get('id', 'N/A')}")
        print(f"   Active: {existing.get('is_active', 'N/A')}")
        # Update password
        password_hash = pwd_context.hash(PASSWORD)
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": password_hash, "is_active": True}}
        )
        print(f"🔑 Password updated to: {PASSWORD}")
    else:
        print(f"⚠️  User '{EMAIL}' NOT found. Creating...")
        password_hash = pwd_context.hash(PASSWORD)
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
        print(f"🔑 Password: {PASSWORD}")
    
    # List all users
    print("\n📋 All users:")
    async for user in db.users.find({}, {"email": 1, "is_active": 1, "_id": 0}):
        print(f"   - {user.get('email', 'N/A')} (active: {user.get('is_active', 'N/A')})")

if __name__ == "__main__":
    asyncio.run(setup())
