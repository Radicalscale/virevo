import os
import sys
import json
import asyncio
import base64
from datetime import datetime

# Add backend directory to sys.path to import modules
backend_dir = os.path.join(os.getcwd(), 'backend')
sys.path.append(backend_dir)

try:
    import telnyx
    from dotenv import load_dotenv
    from motor.motor_asyncio import AsyncIOMotorClient
    # Try importing key_encryption
    try:
        from key_encryption import decrypt_api_key
    except ImportError:
        decrypt_api_key = None
        
except ImportError as e:
    print(f"❌ Error: Missing dependencies: {e}")
    sys.exit(1)

# Load environment variables
load_dotenv(os.path.join(backend_dir, '.env'))

# JSON converter for datetime objects
def json_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)

async def get_details_from_db(call_control_id):
    """
    Retrieve:
    1. The API Key (decrypted)
    2. The full Call Log record (for debugging)
    """
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    # documentation fallbacks
    if not mongo_url:
        mongo_url = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
        print("⚠️  Using fallback MONGO_URL")
    if not db_name:
        db_name = "test_database"
        
    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # 1. FIND THE RECORD
        print(f"🔍 Searching DB for call: {call_control_id}")
        
        # Try call_logs first (Webhooks)
        record = await db.call_logs.find_one({"call_id": call_control_id})
        collection_source = "call_logs"
        
        if not record:
            # Try calls (Internal)
            record = await db.calls.find_one({"id": call_control_id})
            collection_source = "calls"
            
        if not record:
            print("❌ Call not found in DB.")
            return None, None
            
        print(f"✅ Found record in '{collection_source}'")
        
        # 2. GET USER ID to fetch Key
        user_id = record.get('user_id')
        agent_id = record.get('agent_id')
        
        if not user_id and agent_id:
             agent = await db.agents.find_one({"id": agent_id})
             if agent:
                 user_id = agent.get('user_id')
        
        if not user_id:
            print("❌ Could not determine User ID from record.")
            record['_id'] = str(record['_id'])
            return None, record

        # 3. GET API KEY
        key_doc = await db.api_keys.find_one({
            "user_id": user_id,
            "service_name": "telnyx",
            "is_active": True
        })
        
        api_key = None
        if key_doc and key_doc.get("api_key"):
            encrypted = key_doc.get("api_key")
            if decrypt_api_key:
                try:
                    # Look for encryption key in likely env vars if not set
                    if not os.environ.get('ENCRYPTION_KEY'):
                         # Fallback for dev - typically not safe but we are debugging
                         pass
                    api_key = decrypt_api_key(encrypted)
                except Exception:
                    api_key = encrypted # Fallback to raw if decryption fails (might be unencrypted)
            else:
                api_key = encrypted

        # Prepare record for JSON output
        record['_id'] = str(record['_id'])
        
        return api_key, record
             
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return None, None

async def fetch_call_debug_info(call_control_id):
    debug_data = {
        "call_control_id": call_control_id,
        "timestamp": datetime.utcnow().isoformat(),
        "db_record": None,
        "telnyx_api_record": None,
        "recordings": [],
        "errors": []
    }

    # 1. Get DB Record & Key
    api_key, db_record = await get_details_from_db(call_control_id)
    debug_data["db_record"] = db_record
    
    # Override with env key if present
    env_key = os.environ.get('TELNYX_API_KEY')
    if env_key:
        api_key = env_key
        
    if not api_key:
        print("❌ Connect failed: No API Key found.")
        # Print what we have
        print(json.dumps(debug_data, indent=2, default=json_converter))
        return

    # 2. Fetch Telnyx Data
    try:
        client = telnyx.Telnyx(api_key=api_key)
        
        print("📡 Fetching Telnyx API Data...")
        try:
            call = client.calls.retrieve(call_control_id)
            debug_data["telnyx_api_record"] = call
        except Exception as e:
            debug_data["errors"].append(f"Call API Fetch Error: {e}")
            
        print("📼 Fetching Recordings...")
        try:
            recs = client.recordings.list(filter={"call_control_id": call_control_id})
            debug_data["recordings"] = [r for r in recs.data]
        except Exception as e:
             debug_data["errors"].append(f"Recording API Fetch Error: {e}")
             
    except Exception as e:
        debug_data["errors"].append(f"Telnyx Client Error: {e}")

    # Output
    print("\n" + "="*30)
    print("DEBUG REPORT")
    print("="*30)
    
    def robust_converter(o):
        if isinstance(o, datetime):
            return o.isoformat()
        try:
            return o.to_dict()
        except:
            return str(o)
            
    print(json.dumps(debug_data, indent=2, default=robust_converter))
    print("="*30)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_call_debug.py <call_control_id>")
        sys.exit(1)
    
    call_id = sys.argv[1]
    asyncio.run(fetch_call_debug_info(call_id))
