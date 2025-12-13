"""
Migrate platform API keys to main user (kendrickbowman9@gmail.com)
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uuid
import sys

# Add backend to path
sys.path.append('/app/backend')

async def migrate_keys():
    # Read from backend/.env
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
    
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    
    # Find the main user
    user = await db.users.find_one({"email": "kendrickbowman9@gmail.com"})
    if not user:
        print("❌ User kendrickbowman9@gmail.com not found!")
        return
    
    user_id = user['id']
    print(f"✅ Found user: {user['email']} (ID: {user_id})")
    
    # Platform API keys to migrate
    keys_to_migrate = {
        "deepgram": os.environ.get('DEEPGRAM_API_KEY'),
        "openai": os.environ.get('OPENAI_API_KEY'),
        "elevenlabs": os.environ.get('ELEVEN_API_KEY'),
        "grok": os.environ.get('GROK_API_KEY'),
        "hume": os.environ.get('HUME_API_KEY'),
        "assemblyai": os.environ.get('ASSEMBLYAI_API_KEY'),
        "soniox": os.environ.get('SONIOX_API_KEY'),
        "telnyx": os.environ.get('TELNYX_API_KEY'),
    }
    
    print(f"\n📦 Migrating {len(keys_to_migrate)} API keys to user...\n")
    
    migrated = 0
    skipped = 0
    
    for service_name, api_key in keys_to_migrate.items():
        if not api_key:
            print(f"⚠️  Skipping {service_name}: No key in environment")
            skipped += 1
            continue
        
        # Check if key already exists for this user
        existing = await db.api_keys.find_one({
            "service_name": service_name,
            "user_id": user_id
        })
        
        if existing:
            print(f"⏭️  Skipping {service_name}: Key already exists")
            skipped += 1
            continue
        
        # Create new API key document
        key_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "service_name": service_name,
            "api_key": api_key,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db.api_keys.insert_one(key_doc)
        print(f"✅ Migrated {service_name}: {api_key[:20]}...")
        migrated += 1
    
    print(f"\n🎉 Migration complete!")
    print(f"   Migrated: {migrated}")
    print(f"   Skipped: {skipped}")
    
    # List all keys for this user
    print(f"\n📋 API Keys for {user['email']}:")
    keys = await db.api_keys.find({"user_id": user_id}).to_list(100)
    for key in keys:
        print(f"   - {key['service_name']}: {key['api_key'][:20]}...")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_keys())
