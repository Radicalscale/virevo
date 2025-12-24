import os
import sys
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Add backend directory to sys.path to import modules
backend_dir = os.path.join(os.getcwd(), 'backend')
sys.path.append(backend_dir)
load_dotenv(os.path.join(backend_dir, '.env'))

def json_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()
    try:
        return str(o)
    except:
        return str(type(o))

async def fetch_agent_debug(agent_id):
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    if not mongo_url:
        mongo_url = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
        print("⚠️  Using fallback MONGO_URL")
    if not db_name:
        db_name = "test_database"
        
    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        print(f"🔍 Searching DB for agent: {agent_id}")
        
        # We might need to find the user first if the agent collection is sharded strictly by user, 
        # but usually ID is unique enough or we can find it without user_id in checking.
        # However, the previous code showed agent lookups often use user_id. 
        # Let's try finding by ID first.
        agent = await db.agents.find_one({"id": agent_id})
        
        if not agent:
            print("❌ Agent not found by ID alone.")
            return

        print(f"✅ Found Agent: {agent.get('name', 'Unnamed')}")
        
        # Clean up for JSON dump
        agent['_id'] = str(agent['_id'])
        
        print("\n" + "="*30)
        print("AGENT CONFIG REPORT")
        print("="*30)
        print(json.dumps(agent, indent=2, default=json_converter))
        print("="*30)
        
        # Check specific interesting settings
        print("\n🔎 Key Settings Analysis:")
        settings = agent.get('settings', {})
        print(f"- LLM Provider: {settings.get('llm_provider')}")
        print(f"- Model: {agent.get('model')}")
        print(f"- TTS Provider: {settings.get('tts_provider')}")
        print(f"- Dynamic Rephrase (in nodes?): Check flow below")
        
        flow = agent.get('call_flow', [])
        print(f"- Flow Nodes: {len(flow)}")
        for node in flow:
            node_type = node.get('type')
            label = node.get('data', {}).get('label') or node.get('label')
            dynamic = node.get('data', {}).get('dynamic_rephrase')
            mode = node.get('data', {}).get('mode') or node.get('data', {}).get('promptType')
            if node_type == 'conversation' and mode == 'script':
                 print(f"  - Script Node '{label}': dynamic_rephrase={dynamic}")
                 
    except Exception as e:
        print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_agent_debug.py <agent_id>")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    asyncio.run(fetch_agent_debug(agent_id))
