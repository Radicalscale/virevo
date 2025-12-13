"""
Encrypt all existing API keys in the database
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import sys

sys.path.append('/app/backend')

async def encrypt_keys():
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
    
    from key_encryption import encrypt_api_key, is_encrypted
    
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    
    print("🔐 Encrypting existing API keys...\n")
    
    # Get all API keys
    keys = await db.api_keys.find({}).to_list(1000)
    
    encrypted_count = 0
    skipped_count = 0
    
    for key_doc in keys:
        service_name = key_doc.get("service_name")
        api_key = key_doc.get("api_key")
        
        if not api_key:
            print(f"⚠️  Skipping {service_name}: No API key")
            skipped_count += 1
            continue
        
        # Check if already encrypted
        if is_encrypted(api_key):
            print(f"⏭️  Skipping {service_name}: Already encrypted")
            skipped_count += 1
            continue
        
        # Encrypt the key
        encrypted_key = encrypt_api_key(api_key)
        
        # Update in database
        await db.api_keys.update_one(
            {"_id": key_doc["_id"]},
            {"$set": {
                "api_key": encrypted_key,
                "updated_at": datetime.utcnow()
            }}
        )
        
        print(f"✅ Encrypted {service_name}: {api_key[:20]}...")
        encrypted_count += 1
    
    print(f"\n🎉 Encryption complete!")
    print(f"   Encrypted: {encrypted_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total: {len(keys)}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(encrypt_keys())
