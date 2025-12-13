#!/usr/bin/env python3
"""
Fix API keys on Railway's MongoDB - store them UNENCRYPTED temporarily
until we fix encryption properly
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Directly set these values
MONGO_URL = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
USER_EMAIL = "kendrickbowman9@gmail.com"

# Your actual API keys (will store as plaintext temporarily)
API_KEYS = {
    "telnyx": "KEY0199EBFE1BCD21C2E7B0F316A3E980CC_vM9JBdNR3gZ1qlUiqziXCN",
    "telnyx_connection_id": "2777245537294877821",
    "openai": "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",
    "elevenlabs": "sk_fd288b72abe95953baafcfbf561d6fe9d2af4dabf5458e12",
    "grok": "xai-mDonAg7JKMuTnRm6k6NF9SxSNTrLpnENRyU5Y0CWzG82NBzKcr5y3eUGnC5Yxu7yZTRpG98ax2ZmE8GL",
    "soniox": "b999f22d7b6989eb2d1f1b7badfd0f77a1d110d238906afee7b6dab97ada01d7",
}

async def fix_keys():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Find user
    user = await db.users.find_one({"email": USER_EMAIL})
    if not user:
        print(f"❌ User {USER_EMAIL} not found!")
        return
    
    user_id = user["id"]
    print(f"✅ Found user: {USER_EMAIL} (ID: {user_id})")
    
    # Store each key as PLAINTEXT (no encryption for now)
    for service_name, api_key_value in API_KEYS.items():
        # Check if exists
        existing = await db.api_keys.find_one({
            "user_id": user_id,
            "service_name": service_name
        })
        
        if existing:
            # Update
            await db.api_keys.update_one(
                {"user_id": user_id, "service_name": service_name},
                {"$set": {
                    "api_key": api_key_value,  # Store as plaintext
                    "encrypted_key": None,
                    "is_active": True
                }}
            )
            print(f"✅ Updated {service_name} (plaintext)")
        else:
            # Create new
            await db.api_keys.insert_one({
                "user_id": user_id,
                "service_name": service_name,
                "api_key": api_key_value,  # Store as plaintext
                "encrypted_key": None,
                "is_active": True
            })
            print(f"✅ Created {service_name} (plaintext)")
    
    print(f"\n✅ All API keys stored as plaintext for user {USER_EMAIL}")
    print("⚠️  Note: Keys are NOT encrypted. Fix encryption later.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(fix_keys())
