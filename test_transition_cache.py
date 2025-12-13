#!/usr/bin/env python3
"""
Test the transition cache optimization with the exact sequence from the call
"""
import asyncio
import time
import sys
import os

sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from calling_service import CallSession

# Test sequence from actual call
TEST_CONVERSATION = [
    {
        "user_input": "Sure....",
        "expected_cache": "HIT",  # Should hit cache (starts with "sure")
        "description": "User agrees to initial prompt"
    },
    {
        "user_input": "Yeah. Why are you calling me?",
        "expected_cache": "HIT",  # This was the slow one - should now hit cache!
        "description": "User agrees but asks question (previously took 5.5s)"
    },
    {
        "user_input": "Yeah tell me more",
        "expected_cache": "HIT",
        "description": "User wants more info"
    },
    {
        "user_input": "No thanks",
        "expected_cache": "HIT",
        "description": "User declines (negative cache)"
    },
    {
        "user_input": "I'm not sure yet",
        "expected_cache": "MISS",  # Complex response, should use LLM
        "description": "Complex response requiring LLM evaluation"
    }
]

async def get_agent_and_flow(agent_id: str):
    """Fetch agent and flow configuration"""
    mongo_url = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
    client = AsyncIOMotorClient(mongo_url)
    db = client["test_database"]
    
    agent = await db.agents.find_one({"id": agent_id})
    if not agent:
        return None, None
    
    flow_id = agent.get('flow_id')
    if flow_id:
        flow = await db.flows.find_one({"id": flow_id})
        return agent, flow
    
    return agent, None

async def test_transition_cache():
    """Test the transition cache with actual conversation sequence"""
    print("=" * 80)
    print("TRANSITION CACHE OPTIMIZATION TEST")
    print("=" * 80)
    
    agent_id = "b6b1d141-75a2-43d8-80b8-3decae5c0a92"
    
    print(f"\n🔍 Loading agent and flow...")
    agent, flow = await get_agent_and_flow(agent_id)
    
    if not agent:
        print(f"❌ Agent not found: {agent_id}")
        return False
    
    if not flow:
        print(f"⚠️  No flow found for agent")
        return False
    
    print(f"✅ Loaded: {agent.get('name')}")
    print(f"   Flow: {flow.get('name')}")
    
    # Initialize call session
    call_session = CallSession(
        call_id="test_call_123",
        agent_config=agent,
        flow_config=flow
    )
    
    # Get flow nodes
    flow_nodes = flow.get('nodes', [])
    
    # Find a node with transitions for testing
    test_node = None
    for node in flow_nodes:
        node_data = node.get('data', {})
        if node_data.get('transitions') and len(node_data.get('transitions', [])) > 0:
            test_node = node
            break
    
    if not test_node:
        print("⚠️  No node with transitions found in flow")
        return False
    
    print(f"\n🎯 Test node: {test_node.get('data', {}).get('label', 'Unknown')}")
    print(f"   Transitions: {len(test_node.get('data', {}).get('transitions', []))}")
    
    # Run tests
    print("\n" + "=" * 80)
    print("TESTING CONVERSATION SEQUENCE")
    print("=" * 80)
    
    results = []
    
    for i, test_case in enumerate(TEST_CONVERSATION, 1):
        user_input = test_case['user_input']
        expected = test_case['expected_cache']
        description = test_case['description']
        
        print(f"\n--- Test {i}: {description}")
        print(f"    User: \"{user_input}\"")
        print(f"    Expected: Cache {expected}")
        
        # Time the transition evaluation
        start_time = time.time()
        
        try:
            next_node = await call_session._follow_transition(
                test_node,
                user_input,
                flow_nodes
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Determine if cache was hit based on timing
            # Cache hits should be < 50ms, LLM calls are > 500ms
            cache_hit = elapsed_ms < 50
            
            if cache_hit:
                status = "✅ CACHE HIT"
                color = "\033[92m"  # Green
            else:
                status = "⚠️  CACHE MISS (LLM call)"
                color = "\033[93m"  # Yellow
            reset = "\033[0m"
            
            print(f"    {color}Result: {status} - {elapsed_ms}ms{reset}")
            
            if next_node:
                next_label = next_node.get('data', {}).get('label', 'Unknown')
                print(f"    → Transition to: {next_label}")
            else:
                print(f"    → Stayed on same node")
            
            # Check if result matches expectation
            if expected == "HIT" and cache_hit:
                match = "✅ PASS"
            elif expected == "MISS" and not cache_hit:
                match = "✅ PASS"
            else:
                match = "❌ FAIL"
            
            print(f"    {match} - Expected {expected}, got {'HIT' if cache_hit else 'MISS'}")
            
            results.append({
                'test': f"Test {i}",
                'input': user_input,
                'expected': expected,
                'actual': 'HIT' if cache_hit else 'MISS',
                'time_ms': elapsed_ms,
                'passed': (expected == "HIT" and cache_hit) or (expected == "MISS" and not cache_hit)
            })
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results.append({
                'test': f"Test {i}",
                'input': user_input,
                'expected': expected,
                'actual': 'ERROR',
                'time_ms': 0,
                'passed': False
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    print(f"\n{passed}/{total} tests passed\n")
    
    for result in results:
        status = "✅" if result['passed'] else "❌"
        print(f"{status} {result['test']}: {result['actual']} ({result['time_ms']}ms)")
        if not result['passed'] and result['actual'] != 'ERROR':
            print(f"   Expected {result['expected']}, got {result['actual']}")
    
    # Performance analysis
    print("\n" + "=" * 80)
    print("PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    cache_hits = [r for r in results if r['actual'] == 'HIT']
    cache_misses = [r for r in results if r['actual'] == 'MISS']
    
    if cache_hits:
        avg_hit_time = sum(r['time_ms'] for r in cache_hits) / len(cache_hits)
        max_hit_time = max(r['time_ms'] for r in cache_hits)
        print(f"\n✅ Cache Hits: {len(cache_hits)}")
        print(f"   Avg time: {avg_hit_time:.0f}ms")
        print(f"   Max time: {max_hit_time:.0f}ms")
    
    if cache_misses:
        avg_miss_time = sum(r['time_ms'] for r in cache_misses) / len(cache_misses)
        max_miss_time = max(r['time_ms'] for r in cache_misses)
        print(f"\n⚠️  Cache Misses: {len(cache_misses)}")
        print(f"   Avg time: {avg_miss_time:.0f}ms")
        print(f"   Max time: {max_miss_time:.0f}ms")
        
        if cache_hits:
            time_saved = avg_miss_time - avg_hit_time
            print(f"\n💡 Time saved per cache hit: ~{time_saved:.0f}ms")
    
    # Specific check for the problematic input
    problematic_test = next((r for r in results if "Why are you calling me" in r['input']), None)
    if problematic_test:
        print("\n" + "=" * 80)
        print("PROBLEMATIC INPUT ANALYSIS")
        print("=" * 80)
        print(f"\nInput: \"{problematic_test['input']}\"")
        print(f"Previous timing: 696ms (LLM evaluation)")
        print(f"Current timing: {problematic_test['time_ms']}ms")
        
        if problematic_test['actual'] == 'HIT':
            improvement = 696 - problematic_test['time_ms']
            pct = (improvement / 696) * 100
            print(f"✅ Improvement: {improvement}ms saved ({pct:.0f}% faster)")
        else:
            print(f"❌ Still using LLM evaluation (expected cache hit)")
    
    return passed == total

async def main():
    """Run the test"""
    try:
        success = await test_transition_cache()
        
        if success:
            print("\n" + "=" * 80)
            print("✅ ALL TESTS PASSED!")
            print("=" * 80)
            print("\nThe transition cache optimization is working correctly.")
            print("Expected performance improvement: 30-40% on affirmative responses.")
        else:
            print("\n" + "=" * 80)
            print("⚠️  SOME TESTS FAILED")
            print("=" * 80)
            print("\nReview the results above for details.")
        
        return success
    
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
