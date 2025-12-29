"""
Custom Test: Skeptical Person with KB and Objection Handling
Tests the optimized agent with realistic skeptical prospect behavior
"""
import asyncio
import httpx
import time
import os
from datetime import datetime
import json
from motor.motor_asyncio import AsyncIOMotorClient

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')

# Skeptical person conversation that triggers KB and objections
SKEPTICAL_CONVERSATION = [
    "Hello",
    "My name is Sarah",
    "What is this about?",  # Should trigger KB query
    "This sounds like a scam",  # Objection handling
    "How do I know this is legit?",  # Another objection + KB
    "Why should I trust you?",  # Trust objection
    "What proof do you have?",  # Evidence request (KB query)
    "I need to think about it",  # Stall objection
    "How much does it cost?",  # Price objection (KB)
    "That's too expensive",  # Price objection handling
]


async def get_agent_info():
    """Get agent from MongoDB"""
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        raise Exception(f"Agent {AGENT_ID} not found")
    
    agent.pop('_id', None)
    return agent


async def start_test_session(agent_config: dict) -> dict:
    """Start test session"""
    from core_calling_service import CallSession
    
    mongo_url = os.environ.get('MONGO_URL')
    client_db = AsyncIOMotorClient(mongo_url)
    db = client_db['test_database']
    
    session_id = f"skeptical_test_{int(time.time())}"
    
    session = CallSession(
        call_id=session_id,
        agent_config=agent_config,
        agent_id=agent_config['id'],
        user_id=USER_ID,
        knowledge_base=agent_config.get('knowledge_base', ''),
        db=db
    )
    
    return {
        "session": session,
        "session_id": session_id
    }


async def send_message(session, message: str, agent_config: dict) -> dict:
    """Send message and measure latency"""
    total_start = time.time()
    
    try:
        # LLM Processing
        llm_start = time.time()
        response = await session.process_user_input(message)
        llm_time = (time.time() - llm_start) * 1000
        
        if response is None:
            response = "[No response]"
        if not isinstance(response, str):
            if isinstance(response, dict):
                response = response.get('text', str(response))
            else:
                response = str(response)
        
        # TTS Generation
        tts_start = time.time()
        tts_audio = None
        tts_time = 0
        
        try:
            from server import generate_tts_audio
            tts_audio = await generate_tts_audio(response, agent_config)
            tts_time = (time.time() - tts_start) * 1000
        except Exception as e:
            tts_time = (time.time() - tts_start) * 1000
            print(f"         ⚠️ TTS error: {e}")
        
        total_latency = (time.time() - total_start) * 1000
        
        current_node = "Unknown"
        if hasattr(session, 'current_node_id') and session.current_node_id:
            current_node = session.current_node_id
        
        # Check if KB was triggered
        kb_triggered = hasattr(session, 'last_kb_query') and session.last_kb_query
        
        return {
            "success": True,
            "latency_ms": total_latency,
            "llm_ms": llm_time,
            "tts_ms": tts_time,
            "response": response,
            "current_node": current_node,
            "response_length": len(response),
            "tts_audio_size": len(tts_audio) if tts_audio else 0,
            "kb_triggered": kb_triggered
        }
        
    except Exception as e:
        total_latency = (time.time() - total_start) * 1000
        return {
            "success": False,
            "latency_ms": total_latency,
            "error": str(e)
        }


async def run_skeptical_test():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║          SKEPTICAL PERSON TEST - KB & Objection Handling                     ║
║          Testing optimized agent with realistic skeptical prospect           ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Load agent
    print("📥 Loading agent...")
    agent = await get_agent_info()
    print(f"✅ Agent: {agent.get('name')}")
    print(f"   System Prompt: {len(agent.get('system_prompt', '')):,} chars")
    print(f"   Nodes: {len(agent.get('call_flow', []))}")
    print()
    
    # Start session
    print("="*80)
    print("🧪 Starting Skeptical Prospect Test")
    print("="*80)
    print()
    
    session_data = await start_test_session(agent)
    session = session_data["session"]
    session_id = session_data["session_id"]
    
    print(f"✅ Session started: {session_id}")
    print()
    
    results = []
    kb_queries = 0
    objection_nodes = 0
    
    for i, message in enumerate(SKEPTICAL_CONVERSATION, 1):
        print(f"  {i}. User: \"{message}\"")
        
        result = await send_message(session, message, agent)
        
        if result["success"]:
            results.append(result)
            
            if result.get("kb_triggered"):
                kb_queries += 1
                kb_indicator = " 🔍 KB"
            else:
                kb_indicator = ""
            
            # Check if objection handling node
            node = result["current_node"]
            if "Objection" in str(node) or "Deframe" in str(node):
                objection_nodes += 1
                objection_indicator = " ⚠️ OBJECTION"
            else:
                objection_indicator = ""
            
            print(f"     ⏱️  Total E2E: {result['latency_ms']:.0f}ms")
            print(f"        LLM: {result['llm_ms']:.0f}ms | TTS: {result['tts_ms']:.0f}ms")
            print(f"     📍 Node: {result['current_node']}{kb_indicator}{objection_indicator}")
            print(f"     💬 Response: {result['response'][:80]}...")
            print(f"     🔊 TTS Audio: {result['tts_audio_size']:,} bytes")
            print()
        else:
            print(f"     ❌ Error: {result.get('error')}")
            print()
    
    # Calculate stats
    print("="*80)
    print("📊 SKEPTICAL PROSPECT TEST RESULTS")
    print("="*80)
    print()
    
    if results:
        latencies = [r['latency_ms'] for r in results]
        llm_times = [r['llm_ms'] for r in results]
        tts_times = [r['tts_ms'] for r in results]
        
        avg_latency = sum(latencies) / len(latencies)
        avg_llm = sum(llm_times) / len(llm_times)
        avg_tts = sum(tts_times) / len(tts_times)
        
        print(f"  📈 Average Response Generation: {avg_latency:.0f}ms")
        print(f"     LLM: {avg_llm:.0f}ms ({avg_llm/avg_latency*100:.1f}%)")
        print(f"     TTS: {avg_tts:.0f}ms ({avg_tts/avg_latency*100:.1f}%)")
        print()
        print(f"  📊 Range:")
        print(f"     Min: {min(latencies):.0f}ms")
        print(f"     Max: {max(latencies):.0f}ms")
        print()
        print(f"  🎯 Target: 1500ms")
        if avg_latency <= 1500:
            print(f"     Status: ✅ BELOW TARGET (under by {1500 - avg_latency:.0f}ms)")
        else:
            print(f"     Status: ❌ ABOVE TARGET (over by {avg_latency - 1500:.0f}ms)")
        print()
        print(f"  🔍 Knowledge Base Queries: {kb_queries}")
        print(f"  ⚠️  Objection Handling Nodes: {objection_nodes}")
        print(f"  📝 Total Messages: {len(results)}")
        print()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/app/skeptical_test_{timestamp}.json"
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": AGENT_ID,
            "agent_name": agent.get('name'),
            "session_id": session_id,
            "scenario": "Skeptical Prospect with KB and Objections",
            "messages": results,
            "overall_stats": {
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "avg_llm_ms": avg_llm,
                "avg_tts_ms": avg_tts,
                "kb_queries": kb_queries,
                "objection_nodes": objection_nodes,
                "total_messages": len(results),
                "target_latency_ms": 1500,
                "meets_target": avg_latency <= 1500
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(test_results, f, indent=2)
        
        print(f"  💾 Results saved to: {filename}")
        print()
    
    print("="*80)
    print("✅ SKEPTICAL PROSPECT TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(run_skeptical_test())
