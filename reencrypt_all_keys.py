#!/usr/bin/env python3
"""
Re-encrypt all API keys with the new proper Fernet encryption key
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Set the NEW encryption key
os.environ['ENCRYPTION_KEY'] = '2dGvDAfEYc_StueBbRHrZWqF2MO6CIZCH5xdLR0YwyY='

# Add backend to path
sys.path.insert(0, '/app/backend')
from key_encryption import encrypt_api_key, decrypt_api_key

async def reencrypt_all_keys():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get all API keys
    all_keys = await db.api_keys.find({}).to_list(1000)
    
    print(f"Found {len(all_keys)} API keys to re-encrypt")
    print("=" * 60)
    
    reencrypted = 0
    for key_doc in all_keys:
        user_id = key_doc.get('user_id')
        service_name = key_doc.get('service_name')
        
        # Get the old encrypted value
        old_value = key_doc.get('encrypted_key') or key_doc.get('api_key')
        
        if not old_value:
            print(f"⚠️  {service_name} (user {user_id[:8]}...) - No key value found, skipping")
            continue
        
        try:
            # Try to decrypt with new key (will fail if encrypted with old key)
            try:
                plaintext_key = decrypt_api_key(old_value)
                print(f"✅ {service_name} - Already encrypted with new key, skipping")
                continue
            except:
                # Decryption failed, assume it's plaintext or encrypted with old key
                # Treat as plaintext
                plaintext_key = old_value
            
            # Re-encrypt with NEW key
            new_encrypted_value = encrypt_api_key(plaintext_key)
            
            # Update in database
            await db.api_keys.update_one(
                {"_id": key_doc["_id"]},
                {"$set": {
                    "encrypted_key": new_encrypted_value,
                    "api_key": None  # Clear old field
                }}
            )
            
            print(f"✅ Re-encrypted {service_name} (user {user_id[:8]}...)")
            reencrypted += 1
            
        except Exception as e:
            print(f"❌ Failed to re-encrypt {service_name}: {e}")
    
    print("=" * 60)
    print(f"📊 Summary: Re-encrypted {reencrypted}/{len(all_keys)} API keys")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(reencrypt_all_keys())
