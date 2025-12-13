"""Final test: Compare one complex message Regular vs Parallel"""
import asyncio
import time
import os
from motor.motor_asyncio import AsyncIOMotorClient

AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

async def test_regular():
    """Test regular approach on complex node"""
    from calling_service import CallSession
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    agent.pop('_id', None)
    
    session = CallSession(
        call_id="test_reg",
        agent_config=agent,
        agent_id=agent['id'],
        user_id=USER_ID,
        knowledge_base=agent.get('knowledge_base', ''),
        db=db
    )
    
    # Simulate conversation up to complex node
    session.conversation_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "{{customer_name}}?", "_node_id": "2"},
        {"role": "user", "content": "I'm John"},
        {"role": "assistant", "content": "This is Jake...", "_node_id": "1763159750250"},
    ]
    
    test_message = "How do I know this is real?"
    
    start = time.time()
    response = await session._process_call_flow_streaming(test_message)
    elapsed = int((time.time() - start) * 1000)
    
    return {"latency_ms": elapsed, "response": response}

async def test_parallel():
    """Test parallel approach"""
    from calling_service import CallSession
    from parallel_llm_team import ParallelLLMTeam
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    agent.pop('_id', None)
    
    session = CallSession(
        call_id="test_par",
        agent_config=agent,
        agent_id=agent['id'],
        user_id=USER_ID,
        knowledge_base=agent.get('knowledge_base', ''),
        db=db
    )
    
    # Same conversation state
    session.conversation_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "{{customer_name}}?", "_node_id": "2"},
        {"role": "user", "content": "I'm John"},
        {"role": "assistant", "content": "This is Jake...", "_node_id": "1763159750250"},
    ]
    
    team = ParallelLLMTeam(session)
    
    # Get a complex node
    flow_nodes = agent.get("call_flow", [])
    complex_node = None
    for node in flow_nodes:
        if node.get("id") == "1763161961589":  # Known slow node
            complex_node = node
            break
    
    if not complex_node:
        complex_node = flow_nodes[5]  # Fallback
    
    test_message = "How do I know this is real?"
    
    start = time.time()
    result = await team.process_parallel(test_message, complex_node)
    elapsed = int((time.time() - start) * 1000)
    
    return {"latency_ms": elapsed, "response": result.get('response'), "breakdown": result.get('latency_breakdown')}

async def main():
    print("=" * 60)
    print("FINAL COMPARISON: Regular vs Parallel")
    print("=" * 60)
    
    print("\n🔹 Testing REGULAR approach...")
    reg_result = await test_regular()
    print(f"   Latency: {reg_result['latency_ms']}ms")
    print(f"   Response: {reg_result['response'][:100]}...")
    
    print("\n🔹 Testing PARALLEL approach...")
    par_result = await test_parallel()
    print(f"   Latency: {par_result['latency_ms']}ms")
    print(f"   Response: {par_result['response'][:100] if par_result['response'] else 'None'}...")
    print(f"   Breakdown: {par_result['breakdown']}")
    
    print("\n" + "=" * 60)
    print("COMPARISON:")
    print(f"Regular:  {reg_result['latency_ms']:>6}ms")
    print(f"Parallel: {par_result['latency_ms']:>6}ms")
    
    if reg_result['latency_ms'] > 0 and par_result['latency_ms'] > 0:
        improvement = ((reg_result['latency_ms'] - par_result['latency_ms']) / reg_result['latency_ms']) * 100
        if improvement > 0:
            print(f"\n✅ Parallel is {improvement:.1f}% FASTER")
        else:
            print(f"\n❌ Parallel is {abs(improvement):.1f}% SLOWER")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
