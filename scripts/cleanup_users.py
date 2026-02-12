
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# You can hardcode your MONGO_URL here if not using env vars
# MONGO_URL = "mongodb+srv://..."

async def cleanup_users():
    mongo_url = os.environ.get("MONGO_URL")
    if not mongo_url:
        mongo_url = input("Enter standard MongoDB connection string: ").strip()
    
    if not mongo_url:
        print("❌ No MongoDB URL provided.")
        return

    try:
        client = AsyncIOMotorClient(mongo_url)
        db_name = os.environ.get("DB_NAME", "virevo")
        db = client[db_name]
        
        # Test connection
        await db.users.find_one()
        print(f"✅ Connected to {db_name}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    print("\n🔍 Scanning for users...")
    users = await db.users.find({}).to_list(length=1000)
    print(f"Found {len(users)} users.")

    if len(users) == 0:
        print("No users found.")
        return

    print("\n--- User List ---")
    for i, u in enumerate(users):
        print(f"{i+1}. {u.get('email', 'No Email')} (ID: {u.get('id', 'No ID')}) - Created: {u.get('created_at', 'Unknown')}")
    print("-----------------")

    confirm = input("\n⚠ Do you want to delete ALL these users? (yes/no/select): ").strip().lower()
    
    if confirm == 'yes':
        result = await db.users.delete_many({})
        print(f"✅ Deleted {result.deleted_count} users.")
        
        # Also clean up associated data (optional)
        cl_result = await db.call_logs.delete_many({})
        print(f"✅ Deleted {cl_result.deleted_count} call logs.")
        
        ak_result = await db.api_keys.delete_many({})
        print(f"✅ Deleted {ak_result.deleted_count} api keys.")

        ag_result = await db.agents.delete_many({})
        print(f"✅ Deleted {ag_result.deleted_count} agents.")
        
    elif confirm == 'select':
        indices = input("Enter numbers to delete (comma separated, e.g. 1, 3, 5): ").strip().split(',')
        ids_to_delete = []
        for idx in indices:
            try:
                i = int(idx.strip()) - 1
                if 0 <= i < len(users):
                    ids_to_delete.append(users[i]['id'])
            except ValueError:
                continue
        
        if not ids_to_delete:
            print("No valid users selected.")
            return
            
        print(f"Deleting {len(ids_to_delete)} users...")
        result = await db.users.delete_many({"id": {"$in": ids_to_delete}})
        print(f"✅ Deleted {result.deleted_count} users.")
        
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    try:
        asyncio.run(cleanup_users())
    except KeyboardInterrupt:
        print("\nCancelled.")
