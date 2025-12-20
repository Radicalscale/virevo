import asyncio
import sys
import os
import json
import logging
sys.path.insert(0, '/Users/kendrickbowman/Downloads/Andro-main/backend')

from calling_service import CallSession
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)
# Enable calling service logs
logging.getLogger("backend.calling_service").setLevel(logging.INFO)

MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
AGENT_ID = "6944df147eadbccc46887cdf"

async def run_scenario(scenario_file):
    print("=" * 80)
    print(f"RUNNING SCENARIO: {scenario_file}")
    print("=" * 80)
    
    # Load Scenario
    try:
        with open(scenario_file, 'r') as f:
            steps = json.load(f)
    except Exception as e:
        print(f"❌ Error loading scenario file: {e}")
        return

    # Connect DB (Sync client for key lookup efficiency in mock, Async for main app checking)
    # Using Async for main app setup
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    
    # Get Agent
    from bson import ObjectId
    try:
        agent = await db.agents.find_one({"_id": ObjectId(AGENT_ID)})
    except:
        agent = await db.agents.find_one({"_id": AGENT_ID})
        
    if not agent:
        print(f"❌ Agent {AGENT_ID} not found!")
        return

    print(f"✅ Loaded Agent: {agent.get('name')}")

    # DEBUG: Inspect Calendar Node
    try:
        cal_node = next((n for n in agent.get('call_flow', []) if "Calendar" in n.get('label', '') or "Check" in n.get('label', '')), None)
        if cal_node:
            print(f"DEBUG CALENDAR NODE: {cal_node.get('label')} ({cal_node.get('id')})")
            print(f" - Webhook URL: {cal_node.get('metadata', {}).get('webhookUrl')}")
            for t in cal_node.get('transitions', []):
                print(f" - Transition: {t.get('condition')} -> {t.get('next_node_id')}")
        else:
            print("DEBUG: Calendar node not found.")
    except Exception as e:
        print(f"DEBUG ERROR: {e}")

    
    # Define Mock Key Retrieval
    # We need a synchronous DB client for the mock if we want to mimic debug_agent_nodes behavior 
    # strictly, OR just use the async db if we can await it? 
    # CallingSession.get_api_key is async, so we can await async DB calls.
    
    async def mock_get_api_key(key_name: str):
        try:
            # We must import inside function to use env vars set later or ensuring context
            from key_encryption import decrypt_api_key
            
            user_id = agent.get("user_id")
            # Using the async db client from outer scope
            key_doc = await db.api_keys.find_one({
                "user_id": user_id,
                "service_name": key_name,
                "is_active": True
            })
            
            if key_doc and "api_key" in key_doc:
                decrypted = decrypt_api_key(key_doc["api_key"])
                # print(f"   🔑 Decrypted key for {key_name}: {decrypted[:5]}...")
                return decrypted
            else:
                print(f"   ⚠️ Key not found for {key_name}")
                return None
        except Exception as e:
            print(f"   ❌ MockKey Error: {e}")
            return None

    # Init Session with DB for real API key retrieval
    session = CallSession("scenario_test_session", agent, db=db)
    
    # INJECT USER VARIABLES
    session.session_variables.update({
        "callerName": "Kendrick",
        "to_number": "+17708336397",
        "customer_email": "kendrickbowman9@gmail.com"
    })
    
    print("   ⚡ REAL MODE: Using actual Network, Database, and API Keys")
    
    # Run Steps
    for i, step in enumerate(steps):
        user_input = step['user_input']
        expected = step.get('expected_response_contains', [])
        
        print(f"\n[{i+1}] 👤 USER: {user_input}")
        
        # Capture Response
        try:
            response = await session.process_user_input(user_input)
            agent_text = response.get('text', '')
            node_label = response.get('node_label', 'Unknown')
            
            print(f"[{i+1}] 🤖 AGENT ({node_label}): {agent_text}")
            
            # Validation
            if expected:
                passed = False
                for phrase in expected:
                    if phrase.lower() in agent_text.lower():
                        passed = True
                        break
                if passed:
                    print(f"   ✅ Validated: Found expected content.")
                else:
                    print(f"   ⚠️ WARNING: Expected content '{expected}' not found.")
                    
        except Exception as e:
            print(f"   ❌ Error processing step: {e}")
            import traceback
            traceback.print_exc()

                
    print("\n" + "=" * 80)
    print("SCENARIO COMPLETE")
    print("=" * 80)
    client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 run_scenario_test.py <scenario_file.txt>")
    else:
        asyncio.run(run_scenario(sys.argv[1]))
