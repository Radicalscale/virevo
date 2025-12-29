"""
Test script to compare Regular vs Parallel LLM approaches
Tests on slow nodes to validate performance and transition accuracy
"""
import asyncio
import time
import os
from motor.motor_asyncio import AsyncIOMotorClient
import json
from datetime import datetime

AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

# Test scenarios focused on slow nodes
TEST_SCENARIOS = [
    {
        "name": "Trust Objection (Slow Node)",
        "messages": [
            "Hello",
            "I'm John",
            "This sounds like a scam",
            "How do I know this is real?"
        ],
        "expected_node": "1763161961589"  # N003B_DeframeInitialObjection
    },
    {
        "name": "Side Hustle Question (Slow Node)",
        "messages": [
            "Hello",
            "I'm Sarah",
            "I'm employed",
            "I make 75k per year",
            "Do I need a side hustle?"
        ],
        "expected_node": "1763176486825"  # N201B_Employed_AskSideHustle
    }
]


async def get_agent_from_db():
    """Fetch agent from MongoDB"""
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        raise Exception(f"Agent {AGENT_ID} not found")
    
    agent.pop('_id', None)
    return agent, db


async def test_regular_approach(agent_config, db, messages):
    """Test using regular/current approach"""
    from core_calling_service import CallSession
    
    session_id = f"test_regular_{int(time.time())}"
    
    session = CallSession(
        call_id=session_id,
        agent_config=agent_config,
        agent_id=agent_config['id'],
        user_id=USER_ID,
        knowledge_base=agent_config.get('knowledge_base', ''),
        db=db
    )
    
    results = []
    
    for msg in messages:
        start_time = time.time()
        
        try:
            # Add user message to history
            session.conversation_history.append({
                "role": "user",
                "content": msg
            })
            
            # Process using regular approach
            response = await session._process_call_flow_streaming(msg)
            
            latency = int((time.time() - start_time) * 1000)
            
            # Get current node
            current_node_id = session.current_node_id or "unknown"
            
            results.append({
                "message": msg,
                "response": response,
                "latency_ms": latency,
                "current_node": current_node_id
            })
            
            # Add agent response to history
            session.conversation_history.append({
                "role": "assistant",
                "content": response,
                "_node_id": current_node_id
            })
            
            print(f"  Regular: {msg[:30]:30} | {latency:5}ms | Node: {current_node_id}")
            
        except Exception as e:
            print(f"  ERROR in regular approach: {e}")
            results.append({
                "message": msg,
                "error": str(e),
                "latency_ms": 0
            })
    
    return results


async def test_parallel_approach(agent_config, db, messages):
    """Test using parallel LLM team approach"""
    from core_calling_service import CallSession
    from parallel_llm_team import ParallelLLMTeam
    
    session_id = f"test_parallel_{int(time.time())}"
    
    session = CallSession(
        call_id=session_id,
        agent_config=agent_config,
        agent_id=agent_config['id'],
        user_id=USER_ID,
        knowledge_base=agent_config.get('knowledge_base', ''),
        db=db
    )
    
    # Create parallel team
    parallel_team = ParallelLLMTeam(session)
    
    results = []
    
    for msg in messages:
        start_time = time.time()
        
        try:
            # Add user message to history
            session.conversation_history.append({
                "role": "user",
                "content": msg
            })
            
            # Get current node
            flow_nodes = agent_config.get("call_flow", [])
            
            # Determine current node (simplified logic for testing)
            current_node = None
            if len(session.conversation_history) <= 2:
                # First message - find first conversation node
                for node in flow_nodes:
                    if node.get("type") == "conversation":
                        current_node = node
                        break
            else:
                # Use last node ID from history
                for msg_item in reversed(session.conversation_history):
                    if msg_item.get("role") == "assistant" and "_node_id" in msg_item:
                        node_id = msg_item["_node_id"]
                        for node in flow_nodes:
                            if node.get("id") == node_id:
                                current_node = node
                                break
                        break
            
            if not current_node:
                # Fallback to first conversation node
                for node in flow_nodes:
                    if node.get("type") == "conversation":
                        current_node = node
                        break
            
            # Process using parallel approach
            result = await parallel_team.process_parallel(msg, current_node)
            
            response = result.get('response', '')
            next_node = result.get('next_node', 'LOOP')
            breakdown = result.get('latency_breakdown', {})
            
            latency = int((time.time() - start_time) * 1000)
            
            results.append({
                "message": msg,
                "response": response,
                "latency_ms": latency,
                "current_node": current_node.get('id', 'unknown'),
                "next_node": next_node,
                "breakdown": breakdown
            })
            
            # Add agent response to history
            session.conversation_history.append({
                "role": "assistant",
                "content": response,
                "_node_id": current_node.get('id', 'unknown')
            })
            
            print(f"  Parallel: {msg[:30]:30} | {latency:5}ms | Node: {current_node.get('id', 'unknown')}")
            
        except Exception as e:
            print(f"  ERROR in parallel approach: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "message": msg,
                "error": str(e),
                "latency_ms": 0
            })
    
    return results


async def main():
    """Run comparison tests"""
    print("=" * 80)
    print("PARALLEL LLM TEAM - Comparison Test")
    print("=" * 80)
    
    # Load agent
    print("\n📦 Loading agent from MongoDB...")
    agent_config, db = await get_agent_from_db()
    print(f"✅ Agent loaded: {agent_config.get('name')}")
    print(f"   Nodes: {len(agent_config.get('call_flow', []))}")
    print(f"   System prompt: {len(agent_config.get('system_prompt', ''))} chars")
    
    all_results = []
    
    for scenario in TEST_SCENARIOS:
        print(f"\n{'=' * 80}")
        print(f"📝 Testing Scenario: {scenario['name']}")
        print(f"{'=' * 80}")
        
        messages = scenario['messages']
        
        # Test 1: Regular Approach
        print(f"\n🔹 Running REGULAR approach...")
        regular_results = await test_regular_approach(agent_config, db, messages)
        
        # Calculate average latency
        regular_latencies = [r['latency_ms'] for r in regular_results if 'latency_ms' in r and r['latency_ms'] > 0]
        regular_avg = sum(regular_latencies) / len(regular_latencies) if regular_latencies else 0
        
        print(f"\n   Regular Average: {regular_avg:.0f}ms")
        
        # Test 2: Parallel Approach
        print(f"\n🔹 Running PARALLEL approach...")
        parallel_results = await test_parallel_approach(agent_config, db, messages)
        
        # Calculate average latency
        parallel_latencies = [r['latency_ms'] for r in parallel_results if 'latency_ms' in r and r['latency_ms'] > 0]
        parallel_avg = sum(parallel_latencies) / len(parallel_latencies) if parallel_latencies else 0
        
        print(f"\n   Parallel Average: {parallel_avg:.0f}ms")
        
        # Compare
        if regular_avg > 0 and parallel_avg > 0:
            improvement = ((regular_avg - parallel_avg) / regular_avg) * 100
            print(f"\n   💡 Improvement: {improvement:+.1f}% {'(FASTER ✅)' if improvement > 0 else '(SLOWER ❌)'}")
        
        # Store results
        all_results.append({
            "scenario": scenario['name'],
            "regular": {
                "results": regular_results,
                "avg_latency_ms": regular_avg
            },
            "parallel": {
                "results": parallel_results,
                "avg_latency_ms": parallel_avg
            }
        })
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/app/parallel_llm_test_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "agent_id": AGENT_ID,
            "results": all_results
        }, f, indent=2)
    
    print(f"\n{'=' * 80}")
    print(f"📊 Results saved to: {output_file}")
    print(f"{'=' * 80}")
    
    # Summary
    print(f"\n📈 SUMMARY:")
    for result in all_results:
        print(f"\n  {result['scenario']}:")
        print(f"    Regular:  {result['regular']['avg_latency_ms']:.0f}ms")
        print(f"    Parallel: {result['parallel']['avg_latency_ms']:.0f}ms")
        
        reg_avg = result['regular']['avg_latency_ms']
        par_avg = result['parallel']['avg_latency_ms']
        
        if reg_avg > 0 and par_avg > 0:
            improvement = ((reg_avg - par_avg) / reg_avg) * 100
            print(f"    Improvement: {improvement:+.1f}% {'✅' if improvement > 0 else '❌'}")


if __name__ == "__main__":
    asyncio.run(main())
