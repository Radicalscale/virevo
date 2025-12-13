#!/usr/bin/env python3
"""
Migrate API keys from environment variables to user's MongoDB record
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, '/app/backend')
from key_encryption import encrypt_api_key

# Load environment variables
load_dotenv('/app/backend/.env')

async def migrate_api_keys():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # User email
    user_email = "kendrickbowman9@gmail.com"
    
    # Find user
    user = await db.users.find_one({"email": user_email})
    if not user:
        print(f"❌ User {user_email} not found!")
        return
    
    user_id = user["id"]
    print(f"✅ Found user: {user_email} (ID: {user_id})")
    
    # API keys to migrate
    api_keys_to_migrate = {
        "telnyx": os.environ.get('TELNYX_API_KEY'),
        "telnyx_connection_id": os.environ.get('TELNYX_CONNECTION_ID'),
        "openai": os.environ.get('OPENAI_API_KEY'),
        "elevenlabs": os.environ.get('ELEVEN_API_KEY'),
        "grok": os.environ.get('GROK_API_KEY'),
        "soniox": os.environ.get('SONIOX_API_KEY'),
        "deepgram": os.environ.get('DEEPGRAM_API_KEY'),
        "hume": os.environ.get('HUME_API_KEY'),
        "assemblyai": os.environ.get('ASSEMBLYAI_API_KEY'),
    }
    
    # Migrate each key
    migrated = 0
    for service_name, api_key in api_keys_to_migrate.items():
        if not api_key:
            print(f"⚠️  Skipping {service_name} - not set in environment")
            continue
        
        # Check if already exists
        existing = await db.api_keys.find_one({
            "user_id": user_id,
            "service_name": service_name
        })
        
        if existing:
            print(f"⏭️  {service_name} - already exists, skipping")
            continue
        
        # Encrypt and store
        try:
            encrypted_key = encrypt_api_key(api_key)
            
            api_key_doc = {
                "user_id": user_id,
                "service_name": service_name,
                "encrypted_key": encrypted_key,
                "created_at": asyncio.get_event_loop().time()
            }
            
            await db.api_keys.insert_one(api_key_doc)
            print(f"✅ Migrated {service_name}")
            migrated += 1
        except Exception as e:
            print(f"❌ Failed to migrate {service_name}: {e}")
    
    print(f"\n📊 Summary: Migrated {migrated} API keys to user {user_email}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_api_keys())
