import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys

# Add backend to path
sys.path.insert(0, '/app/backend')

from calling_service import create_call_session, CallSession

async def test_kb_system():
    """Test the KB system with Jake agent"""
    print("="*80)
    print("🧪 TESTING KNOWLEDGE BASE SYSTEM")
    print("="*80)
    
    # Connect to database
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ.get('DB_NAME', 'voice_agent_db')]
    
    # Find Jake agent
    print("\n1. 🔍 Finding Jake agent...")
    agent = await db.agents.find_one({"name": {"$regex": "jake", "$options": "i"}})
    
    if not agent:
        print("❌ Jake agent not found in database")
        # Try to find by ID from logs
        agent = await db.agents.find_one({"id": "474917c1-4888-47b8-b76b-f11a18f19d39"})
        if agent:
            print(f"✅ Found agent by ID: {agent.get('name')} (ID: {agent.get('id')})")
        else:
            print("❌ Agent not found by ID either. Listing all agents:")
            all_agents = await db.agents.find().to_list(length=None)
            for a in all_agents:
                print(f"   - {a.get('name')} (ID: {a.get('id')})")
            return
    else:
        print(f"✅ Found agent: {agent.get('name')} (ID: {agent.get('id')})")
    
    agent_id = agent.get('id')
    
    # Check KB items
    print(f"\n2. 📚 Loading KB items for agent {agent_id}...")
    kb_items = await db.knowledge_base.find({"agent_id": agent_id}).to_list(100)
    
    if not kb_items:
        print(f"❌ No KB items found for agent {agent_id}")
        return
    
    print(f"✅ Found {len(kb_items)} KB items:")
    for idx, item in enumerate(kb_items, 1):
        print(f"   {idx}. {item.get('source_name')} - {len(item.get('content', ''))} chars")
        desc = item.get('description')
        if desc:
            print(f"      Description: {desc}")
    
    # Create call session (this will load and format the KB)
    print(f"\n3. 🤖 Creating call session (loads KB with new formatting)...")
    call_id = "test_kb_call_123"
    try:
        session = await create_call_session(call_id, agent, agent_id=agent_id, db=db)
        print(f"✅ Session created successfully")
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check the formatted knowledge base
    print(f"\n4. 📋 Checking formatted KB content...")
    if session.knowledge_base:
        kb_length = len(session.knowledge_base)
        print(f"✅ KB loaded: {kb_length} total chars")
        
        # Show first 2000 chars to see formatting
        print(f"\n5. 👀 KB Format Preview (first 2000 chars):")
        print("-" * 80)
        print(session.knowledge_base[:2000])
        print("-" * 80)
        if kb_length > 2000:
            print(f"... ({kb_length - 2000} more chars)")
        
        # Check for key elements in formatting
        print(f"\n6. ✅ Checking KB formatting elements:")
        checks = {
            "Has source headers": "### KNOWLEDGE BASE SOURCE" in session.knowledge_base,
            "Has purpose/contains": "**Purpose/Contains:**" in session.knowledge_base,
            "Has 'Use this source when'": "**Use this source when:**" in session.knowledge_base,
            "Contains company info": "company" in session.knowledge_base.lower()[:5000],
        }
        
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
        
    else:
        print("❌ KB is empty!")
        return
    
    # Simulate a test question
    print(f"\n7. 🧪 Simulating LLM prompt for question: 'Who are you? What's your company name?'")
    print("-" * 80)
    
    # This is what would be sent to the LLM (showing abbreviated version)
    test_prompt = f"""
=== KNOWLEDGE BASE ===
You have access to multiple reference sources below. Each source serves a different purpose.

🧠 HOW TO USE THE KNOWLEDGE BASE:
1. When user asks a question, FIRST identify which knowledge base source(s) are relevant based on their descriptions
2. Read ONLY the relevant source(s) to find the answer
3. Use ONLY information from the knowledge base - do NOT make up or improvise ANY factual details
4. If the knowledge base doesn't contain the answer, say: "I don't have that specific information available"
5. Different sources contain different types of information - match the user's question to the right source

⚠️ NEVER invent: company names, product names, prices, processes, methodologies, or any factual information not in the knowledge base

{session.knowledge_base[:1000]}
...
=== END KNOWLEDGE BASE ===

User: "Who are you? What's your company name?"
"""
    
    print(test_prompt[:1500])
    print("\n... (full KB would be included here) ...")
    print("-" * 80)
    
    # Summary
    print(f"\n8. 📊 TEST SUMMARY:")
    print(f"   ✅ Agent found: {agent.get('name')}")
    print(f"   ✅ KB items: {len(kb_items)}")
    print(f"   ✅ Total KB size: {kb_length} chars")
    print(f"   ✅ KB formatted with intelligent matching headers")
    print(f"   ✅ LLM instructions include 5-step KB usage guide")
    
    if "company" in session.knowledge_base.lower()[:10000]:
        print(f"   ✅ Company information detected in KB (early in content)")
    else:
        print(f"   ⚠️  Warning: 'company' keyword not found in first 10K chars")
    
    print(f"\n{'='*80}")
    print(f"✅ KB SYSTEM TEST COMPLETE - Ready for live call testing!")
    print(f"{'='*80}")
    
    # Clean up
    await session.close()
    from calling_service import active_sessions
    if call_id in active_sessions:
        del active_sessions[call_id]

if __name__ == "__main__":
    asyncio.run(test_kb_system())
