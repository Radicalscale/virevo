import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGO_URL = os.environ.get("MONGO_URL") or "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = os.environ.get("DB_NAME", "test_database")

AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"

async def update_agent_transition():
    print(f"🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print(f"🔍 Finding agent {AGENT_ID}...")
    agent = await db.agents.find_one({"id": AGENT_ID})
    
    if not agent:
        print("❌ Agent not found!")
        return

    print(f"✅ Found Agent: {agent.get('name')}")
    
    call_flow = agent.get("call_flow", [])
    greeting_node = None
    
    for node in call_flow:
        if node.get("label") == "Greeting":
            greeting_node = node
            break
            
    if not greeting_node:
        print("❌ Greeting node not found!")
        return
        
    print("📋 Current Greeting Node Transitions:")
    transitions = greeting_node.get("data", {}).get("transitions", [])
    for t in transitions:
        print(f"  - ID: {t.get('id')}, Condition: {t.get('condition')}")
        
    # Find the "Confirms name" transition (Transition 1)
    target_transition = None
    for t in transitions:
        if t.get("id") == "1":
            target_transition = t
            break
            
    if target_transition:
        old_condition = target_transition.get("condition")
        # Update logic: Include greetings and 'verify identity' questions that are answered by the next node ("This is Jake...")
        new_condition = "Confirms name (Yes|Speaking|This is he/she) OR Greetings (Hello|Hi) OR Asks Identity (Who is this?)"
        
        print(f"\n✏️ Updating Transition 1:")
        print(f"  OLD: {old_condition}")
        print(f"  NEW: {new_condition}")
        
        target_transition["condition"] = new_condition
        
        # Update the agent in DB
        result = await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": {"call_flow": call_flow}}
        )
        
        if result.modified_count > 0:
            print("\n✅ Agent updated successfully!")
        else:
            print("\n⚠️ No changes made (maybe already updated?)")
            
    else:
        print("❌ Transition '1' not found in Greeting node!")

if __name__ == "__main__":
    asyncio.run(update_agent_transition())
