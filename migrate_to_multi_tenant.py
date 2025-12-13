"""
Migration script to add user authentication and assign existing data to demo user
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import sys

# Add backend to path
sys.path.append('/app/backend')

from auth_models import User
from auth_utils import hash_password

ROOT_DIR = Path('/app/backend')
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

DEMO_EMAIL = "kendrickbowman9@gmail.com"
DEMO_PASSWORD = "B!LL10n$$"

async def migrate():
    print("🚀 Starting migration to multi-tenant system...")
    
    # Step 1: Create demo user if not exists
    print("\n📝 Step 1: Creating demo user...")
    existing_user = await db.users.find_one({"email": DEMO_EMAIL})
    
    if existing_user:
        demo_user_id = existing_user['id']
        print(f"✅ Demo user already exists: {DEMO_EMAIL} (ID: {demo_user_id})")
    else:
        demo_user = User(
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD)
        )
        await db.users.insert_one(demo_user.model_dump())
        demo_user_id = demo_user.id
        print(f"✅ Created demo user: {DEMO_EMAIL} (ID: {demo_user_id})")
    
    # Step 2: Add user_id to all agents
    print("\n📝 Step 2: Migrating agents...")
    agents = await db.agents.find().to_list(None)
    for agent in agents:
        if 'user_id' not in agent:
            await db.agents.update_one(
                {"id": agent['id']},
                {"$set": {"user_id": demo_user_id}}
            )
            print(f"  ✅ Added user_id to agent: {agent.get('name', agent['id'])}")
    print(f"✅ Migrated {len(agents)} agents")
    
    # Step 3: Add user_id to all phone numbers
    print("\n📝 Step 3: Migrating phone numbers...")
    phone_numbers = await db.phone_numbers.find().to_list(None)
    for phone in phone_numbers:
        if 'user_id' not in phone:
            await db.phone_numbers.update_one(
                {"id": phone['id']},
                {"$set": {"user_id": demo_user_id}}
            )
            print(f"  ✅ Added user_id to phone number: {phone.get('number', phone['id'])}")
    print(f"✅ Migrated {len(phone_numbers)} phone numbers")
    
    # Step 4: Add user_id to all calls
    print("\n📝 Step 4: Migrating calls...")
    calls = await db.calls.find().to_list(None)
    for call in calls:
        if 'user_id' not in call:
            await db.calls.update_one(
                {"id": call['id']},
                {"$set": {"user_id": demo_user_id}}
            )
            print(f"  ✅ Added user_id to call: {call['id']}")
    print(f"✅ Migrated {len(calls)} calls")
    
    # Step 5: Add user_id to all call logs
    print("\n📝 Step 5: Migrating call logs...")
    call_logs = await db.call_logs.find().to_list(None)
    for log in call_logs:
        if 'user_id' not in log and 'id' in log:
            await db.call_logs.update_one(
                {"id": log['id']},
                {"$set": {"user_id": demo_user_id}}
            )
        elif 'user_id' not in log and '_id' in log:
            # Use MongoDB's _id if custom id doesn't exist
            await db.call_logs.update_one(
                {"_id": log['_id']},
                {"$set": {"user_id": demo_user_id}}
            )
    print(f"✅ Migrated {len(call_logs)} call logs")
    
    # Step 6: Add user_id to all knowledge base items
    print("\n📝 Step 6: Migrating knowledge base items...")
    kb_items = await db.knowledge_base.find().to_list(None)
    for kb in kb_items:
        if 'user_id' not in kb:
            await db.knowledge_base.update_one(
                {"id": kb['id']},
                {"$set": {"user_id": demo_user_id}}
            )
            print(f"  ✅ Added user_id to KB: {kb.get('source_name', kb['id'])}")
    print(f"✅ Migrated {len(kb_items)} knowledge base items")
    
    # Step 7: Add user_id to all API keys
    print("\n📝 Step 7: Migrating API keys...")
    api_keys = await db.api_keys.find().to_list(None)
    for key in api_keys:
        if 'user_id' not in key:
            if 'id' in key:
                await db.api_keys.update_one(
                    {"id": key['id']},
                    {"$set": {"user_id": demo_user_id}}
                )
            else:
                await db.api_keys.update_one(
                    {"_id": key['_id']},
                    {"$set": {"user_id": demo_user_id}}
                )
            print(f"  ✅ Added user_id to API key: {key.get('service_name', 'unknown')}")
    print(f"✅ Migrated {len(api_keys)} API keys")
    
    print("\n" + "="*60)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"\n📧 Demo account email: {DEMO_EMAIL}")
    print(f"🔑 Demo account password: {DEMO_PASSWORD}")
    print(f"👤 Demo user ID: {demo_user_id}")
    print(f"\n📊 Summary:")
    print(f"  - Agents: {len(agents)}")
    print(f"  - Phone Numbers: {len(phone_numbers)}")
    print(f"  - Calls: {len(calls)}")
    print(f"  - Call Logs: {len(call_logs)}")
    print(f"  - Knowledge Base Items: {len(kb_items)}")
    print(f"  - API Keys: {len(api_keys)}")

if __name__ == "__main__":
    asyncio.run(migrate())
