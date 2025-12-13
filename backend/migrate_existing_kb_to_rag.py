"""
Migration script to index existing KB items with RAG
Run this once to migrate existing knowledge base items to the RAG system
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys

sys.path.insert(0, '/app/backend')

from rag_service import index_knowledge_base

async def migrate_kb_to_rag():
    """Index all existing KB items with RAG"""
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ.get('DB_NAME', 'voice_agent_db')]
    
    print("="*80)
    print("🔄 MIGRATING EXISTING KB TO RAG SYSTEM")
    print("="*80)
    
    # Find all agents with KB items
    all_kb = await db.knowledge_base.find().to_list(length=None)
    
    if not all_kb:
        print("\nℹ️  No KB items found in database")
        return
    
    # Group by agent_id
    agents_kb = {}
    for item in all_kb:
        agent_id = item.get('agent_id')
        if agent_id not in agents_kb:
            agents_kb[agent_id] = []
        agents_kb[agent_id].append(item)
    
    print(f"\n📊 Found {len(agents_kb)} agents with KB items")
    print(f"📊 Total KB items: {len(all_kb)}")
    
    # Index each agent's KB
    for agent_id, kb_items in agents_kb.items():
        print(f"\n{'='*80}")
        print(f"Processing Agent: {agent_id}")
        print(f"{'='*80}")
        
        # Get agent details
        agent = await db.agents.find_one({"id": agent_id})
        if agent:
            print(f"✅ Agent Name: {agent.get('name')}")
        
        print(f"📚 KB Items: {len(kb_items)}")
        for item in kb_items:
            print(f"   - {item.get('source_name')}: {len(item.get('content', ''))} chars")
        
        # Index with RAG
        try:
            chunks_indexed = index_knowledge_base(agent_id, kb_items)
            print(f"✅ Successfully indexed {chunks_indexed} chunks")
        except Exception as e:
            print(f"❌ Error indexing KB for agent {agent_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("✅ MIGRATION COMPLETE")
    print(f"{'='*80}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_kb_to_rag())
