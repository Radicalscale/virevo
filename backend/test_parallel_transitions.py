"""
Test parallel approach transition accuracy against baseline
CRITICAL: Must maintain 100% transition accuracy (19/19 matches)
"""
import asyncio
import time
import os
from motor.motor_asyncio import AsyncIOMotorClient
import json
from datetime import datetime

AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

TEST_CONVERSATIONS = [
    {
        "name": "Objection Handling Flow",
        "messages": [
            "Hello",
            "My name is John",
            "I don't have time for this",
            "What is this about?",
            "I'm still not interested",
            "Why should I care?",
            "I need to think about it",
            "Actually tell me more"
        ]
    },
    {
        "name": "Qualification Flow",
        "messages": [
            "Hello",
            "I'm Sarah",
            "What are the requirements?",
            "I'm employed",
            "I make 70k per year",
            "Yes I have a vehicle"
        ]
    },
    {
        "name": "Skeptical Prospect",
        "messages": [
            "Hello",
            "This is Mike",
            "This sounds like a scam",
            "How do I know this is real?",
            "Do you have proof?"
        ]
    }
]


async def run_regular_test(agent_config, db):
    """Run test with regular approach"""
    from core_calling_service import CallSession
    
    results = []
    
    for conv in TEST_CONVERSATIONS:
        session_id = f"regular_{int(time.time())}"
        
        session = CallSession(
            call_id=session_id,
            agent_config=agent_config,
            agent_id=agent_config['id'],
            user_id=USER_ID,
            knowledge_base=agent_config.get('knowledge_base', ''),
            db=db
        )
        
        conv_results = []
        
        for msg in conv['messages']:
            try:
                session.conversation_history.append({"role": "user", "content": msg})
                
                start = time.time()
                response = await session._process_call_flow_streaming(msg)
                latency = int((time.time() - start) * 1000)
                
                current_node_id = session.current_node_id or "unknown"
                
                conv_results.append({
                    "message": msg,
                    "node": current_node_id,
                    "latency_ms": latency
                })
                
                session.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "_node_id": current_node_id
                })
                
            except Exception as e:
                print(f"  ERROR: {e}")
                conv_results.append({"message": msg, "node": "ERROR", "error": str(e)})
        
        results.append({"conversation": conv['name'], "results": conv_results})
    
    return results


async def run_parallel_test(agent_config, db):
    """Run test with parallel approach"""
    from core_calling_service import CallSession
    from parallel_llm_team import ParallelLLMTeam
    
    results = []
    flow_nodes = agent_config.get("call_flow", [])
    
    for conv in TEST_CONVERSATIONS:
        session_id = f"parallel_{int(time.time())}"
        
        session = CallSession(
            call_id=session_id,
            agent_config=agent_config,
            agent_id=agent_config['id'],
            user_id=USER_ID,
            knowledge_base=agent_config.get('knowledge_base', ''),
            db=db
        )
        
        team = ParallelLLMTeam(session)
        
        conv_results = []
        
        for msg in conv['messages']:
            try:
                session.conversation_history.append({"role": "user", "content": msg})
                
                # Determine current node (simplified)
                current_node = None
                if len(session.conversation_history) <= 2:
                    # First message
                    for node in flow_nodes:
                        if node.get("type") == "conversation":
                            current_node = node
                            break
                else:
                    # Get last node from history
                    for hist_msg in reversed(session.conversation_history):
                        if hist_msg.get("role") == "assistant" and "_node_id" in hist_msg:
                            node_id = hist_msg["_node_id"]
                            for node in flow_nodes:
                                if node.get("id") == node_id:
                                    current_node = node
                                    break
                            break
                
                if not current_node:
                    for node in flow_nodes:
                        if node.get("type") == "conversation":
                            current_node = node
                            break
                
                start = time.time()
                result = await team.process_parallel(msg, current_node)
                latency = int((time.time() - start) * 1000)
                
                response = result.get('response', '')
                next_node_id = result.get('next_node', 'LOOP')
                
                print(f"    DEBUG: next_node_id='{next_node_id}', current='{current_node.get('id')}'")
                
                # Determine which node to record
                # If next_node is LOOP, stay on current node
                # Otherwise, transition to next_node
                if next_node_id == "LOOP" or not next_node_id:
                    resulting_node_id = current_node.get('id', 'unknown')
                else:
                    resulting_node_id = next_node_id
                
                conv_results.append({
                    "message": msg,
                    "node": resulting_node_id,
                    "latency_ms": latency
                })
                
                session.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "_node_id": resulting_node_id
                })
                
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
                conv_results.append({"message": msg, "node": "ERROR", "error": str(e)})
        
        results.append({"conversation": conv['name'], "results": conv_results})
    
    return results


async def main():
    print("=" * 80)
    print("TRANSITION ACCURACY TEST: Regular vs Parallel")
    print("=" * 80)
    
    # Load agent
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    agent.pop('_id', None)
    
    print(f"\n✅ Agent: {agent.get('name')}")
    print(f"   Testing {sum(len(c['messages']) for c in TEST_CONVERSATIONS)} messages across 3 conversations\n")
    
    # Run regular test
    print("🔹 Running REGULAR approach...")
    regular_results = await run_regular_test(agent, db)
    print("   ✅ Regular complete\n")
    
    # Run parallel test
    print("🔹 Running PARALLEL approach...")
    parallel_results = await run_parallel_test(agent, db)
    print("   ✅ Parallel complete\n")
    
    # Compare transitions
    print("=" * 80)
    print("TRANSITION COMPARISON:")
    print("=" * 80)
    
    total_messages = 0
    total_matches = 0
    
    for reg_conv, par_conv in zip(regular_results, parallel_results):
        conv_name = reg_conv['conversation']
        print(f"\n📝 {conv_name}:")
        
        for reg_msg, par_msg in zip(reg_conv['results'], par_conv['results']):
            total_messages += 1
            
            msg_text = reg_msg['message']
            reg_node = reg_msg.get('node', 'unknown')
            par_node = par_msg.get('node', 'unknown')
            
            match = reg_node == par_node
            if match:
                total_matches += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"  {status} '{msg_text[:30]:30}' | Reg: {reg_node[:20]:20} | Par: {par_node[:20]:20}")
    
    # Final verdict
    print(f"\n{'=' * 80}")
    print(f"FINAL RESULT:")
    print(f"{'=' * 80}")
    print(f"Transitions matched: {total_matches}/{total_messages}")
    print(f"Accuracy: {(total_matches/total_messages)*100:.1f}%")
    
    if total_matches == total_messages:
        print(f"\n🎉 SUCCESS! 100% transition accuracy maintained!")
    else:
        print(f"\n❌ FAILED! Only {total_matches}/{total_messages} transitions match")
        print(f"   {total_messages - total_matches} transitions broke")
    
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(main())
