"""Quick test of parallel LLM approach on one scenario"""
import asyncio
import time
import os
from motor.motor_asyncio import AsyncIOMotorClient

AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

async def main():
    print("🚀 Quick Parallel LLM Test\n")
    
    # Load agent
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    agent.pop('_id', None)
    
    print(f"✅ Agent: {agent.get('name')}\n")
    
    # Create session
    from calling_service import CallSession
    from parallel_llm_team import ParallelLLMTeam
    
    session = CallSession(
        call_id="test_quick",
        agent_config=agent,
        agent_id=agent['id'],
        user_id=USER_ID,
        knowledge_base=agent.get('knowledge_base', ''),
        db=db
    )
    
    # Create parallel team
    team = ParallelLLMTeam(session)
    
    # Test single message
    test_message = "How do I know this is real?"
    
    # Get first conversation node
    flow_nodes = agent.get("call_flow", [])
    current_node = None
    for node in flow_nodes:
        if node.get("type") == "conversation":
            current_node = node
            break
    
    print(f"📝 Testing message: '{test_message}'")
    print(f"🎯 Node: {current_node.get('label')}\n")
    
    start = time.time()
    result = await team.process_parallel(test_message, current_node)
    elapsed = int((time.time() - start) * 1000)
    
    print(f"⏱️  Total Time: {elapsed}ms")
    print(f"💬 Response: {result.get('response')}")
    print(f"\n📊 Breakdown:")
    breakdown = result.get('latency_breakdown', {})
    print(f"   Parallel Specialists: {breakdown.get('parallel_specialists_ms')}ms")
    print(f"   Master Synthesis: {breakdown.get('master_synthesis_ms')}ms")
    print(f"   Total: {breakdown.get('total_ms')}ms")
    
    print(f"\n🎯 Team Results:")
    team_results = result.get('team_results', {})
    print(f"   Intent: {team_results.get('intent')}")
    print(f"   DISC: {team_results.get('disc')}")
    print(f"   Tactic: {team_results.get('tactic')}")
    print(f"   KB Results: {len(team_results.get('kb_results', []))} items")
    print(f"   Next Node: {team_results.get('next_node')}")

if __name__ == "__main__":
    asyncio.run(main())
