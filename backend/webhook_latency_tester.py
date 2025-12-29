"""
Webhook-Based Latency Tester - Uses Real System Infrastructure
Sends requests through actual webhook endpoints, measures response generation time
Does NOT include audio playback time (only generation)
"""
import asyncio
import httpx
import time
import os
from datetime import datetime
import json
from motor.motor_asyncio import AsyncIOMotorClient

AGENT_ID = "474917c1-4888-47b8-b76b-f11a18f19d39"  # Jake - Income Stacking Qualifier
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')

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


async def get_agent_info():
    """Get agent info from MongoDB"""
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        raise Exception(f"Agent {AGENT_ID} not found")
    
    agent.pop('_id', None)
    return agent


async def get_auth_token() -> str:
    """Get auth token for the user"""
    # For testing, we'll create a simple JWT or use service-to-service auth
    # For now, we'll directly use the calling service without auth
    return None


async def start_test_session_direct(agent_config: dict, user_id: str) -> dict:
    """Start a test session using the calling service directly"""
    from core_calling_service import CallSession
    
    mongo_url = os.environ.get('MONGO_URL')
    client_db = AsyncIOMotorClient(mongo_url)
    db = client_db['test_database']
    
    session_id = f"test_{int(time.time())}"
    
    session = CallSession(
        call_id=session_id,
        agent_config=agent_config,
        agent_id=agent_config['id'],
        user_id=user_id,
        knowledge_base=agent_config.get('knowledge_base', ''),
        db=db
    )
    
    return {
        "session": session,
        "session_id": session_id
    }


async def send_message_direct(session, message: str, agent_config: dict) -> dict:
    """Send a message and measure response generation time + TTS generation"""
    total_start = time.time()
    
    try:
        # 1. LLM Processing
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
        
        # 2. TTS Generation (using real ElevenLabs/configured TTS)
        tts_start = time.time()
        tts_audio = None
        tts_time = 0
        
        try:
            # Import the actual TTS generation function
            from server import generate_tts_audio
            tts_audio = await generate_tts_audio(response, agent_config)
            tts_time = (time.time() - tts_start) * 1000
        except Exception as tts_error:
            tts_time = (time.time() - tts_start) * 1000
            print(f"         ⚠️ TTS generation error (continuing): {tts_error}")
        
        # Total latency
        total_latency = (time.time() - total_start) * 1000
        
        # Get current node
        current_node_label = "Unknown"
        if hasattr(session, 'current_node_id') and session.current_node_id:
            current_node_label = session.current_node_id
        
        return {
            "success": True,
            "latency_ms": total_latency,
            "llm_ms": llm_time,
            "tts_ms": tts_time,
            "response": response,
            "current_node": current_node_label,
            "response_length": len(response),
            "tts_audio_size": len(tts_audio) if tts_audio else 0
        }
        
    except Exception as e:
        total_latency = (time.time() - total_start) * 1000
        return {
            "success": False,
            "latency_ms": total_latency,
            "error": str(e)
        }


async def run_conversation(conversation: dict, agent: dict) -> dict:
    """Run a full conversation and measure latencies"""
    print(f"\n{'='*80}")
    print(f"🧪 Testing: {conversation['name']}")
    print(f"{'='*80}\n")
    
    # Start session
    try:
        session_data = await start_test_session_direct(agent, USER_ID)
        session = session_data['session']
        session_id = session_data['session_id']
        print(f"✅ Session started: {session_id}\n")
    except Exception as e:
        print(f"❌ Failed to start session: {e}")
        return {
            "name": conversation['name'],
            "error": str(e),
            "messages": []
        }
    
    results = {
        "name": conversation['name'],
        "session_id": session_id,
        "messages": [],
        "total_latency": 0,
        "avg_latency": 0
    }
    
    # Send each message
    for i, msg in enumerate(conversation['messages'], 1):
        print(f"  {i}. User: \"{msg}\"")
        
        try:
            result = await send_message_direct(session, msg, agent)
            
            if result['success']:
                print(f"     ⏱️  Total E2E: {result['latency_ms']:.0f}ms")
                print(f"        LLM: {result.get('llm_ms', 0):.0f}ms | TTS: {result.get('tts_ms', 0):.0f}ms")
                print(f"     📍 Node: {result['current_node'][:50]}")
                print(f"     💬 Response: {result['response'][:80]}...")
                if result.get('tts_audio_size', 0) > 0:
                    print(f"     🔊 TTS Audio: {result['tts_audio_size']:,} bytes")
                print()
                
                results['messages'].append({
                    "message": msg,
                    "latency_ms": result['latency_ms'],
                    "llm_ms": result.get('llm_ms', 0),
                    "tts_ms": result.get('tts_ms', 0),
                    "response": result['response'],
                    "current_node": result['current_node'],
                    "response_length": result['response_length'],
                    "tts_audio_size": result.get('tts_audio_size', 0)
                })
                
                results['total_latency'] += result['latency_ms']
            else:
                print(f"     ❌ Error: {result['error']}")
                print()
                
                results['messages'].append({
                    "message": msg,
                    "error": result['error'],
                    "latency_ms": result['latency_ms']
                })
        
        except Exception as e:
            print(f"     ❌ Exception: {e}")
            print()
            results['messages'].append({
                "message": msg,
                "error": str(e)
            })
    
    if results['messages']:
        successful_msgs = [m for m in results['messages'] if 'error' not in m]
        if successful_msgs:
            results['avg_latency'] = results['total_latency'] / len(successful_msgs)
        
        print(f"  📊 Conversation Summary:")
        print(f"     Messages: {len(results['messages'])}")
        print(f"     Average Response Generation: {results['avg_latency']:.0f}ms")
    
    return results


async def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              WEBHOOK LATENCY TESTER - Real System Testing                    ║
║              Uses actual API endpoints, no simulation                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    print(f"📡 Backend URL: {BACKEND_URL}")
    print(f"🎯 Agent ID: {AGENT_ID}")
    
    # Get agent info
    print(f"\n📥 Loading agent...")
    agent = await get_agent_info()
    print(f"✅ Agent: {agent.get('name')}")
    print(f"✅ System Prompt: {len(agent.get('system_prompt', '')):,} chars")
    print(f"✅ Nodes: {len(agent.get('call_flow', []))}")
    
    # Run all conversations
    all_results = []
    
    for conversation in TEST_CONVERSATIONS:
        result = await run_conversation(conversation, agent)
        all_results.append(result)
        await asyncio.sleep(2)  # Small delay between conversations
    
    # Calculate overall stats
    print(f"\n{'='*80}")
    print(f"📊 OVERALL RESULTS")
    print(f"{'='*80}\n")
    
    all_latencies = []
    for conv in all_results:
        for msg in conv['messages']:
            if 'latency_ms' in msg and 'error' not in msg:
                all_latencies.append(msg['latency_ms'])
    
    # Calculate component breakdowns
    llm_times = []
    tts_times = []
    
    for conv in all_results:
        for msg in conv['messages']:
            if 'llm_ms' in msg and 'error' not in msg:
                llm_times.append(msg['llm_ms'])
            if 'tts_ms' in msg and 'error' not in msg:
                tts_times.append(msg['tts_ms'])
    
    if all_latencies:
        avg_latency = sum(all_latencies) / len(all_latencies)
        min_latency = min(all_latencies)
        max_latency = max(all_latencies)
        avg_llm = sum(llm_times) / len(llm_times) if llm_times else 0
        avg_tts = sum(tts_times) / len(tts_times) if tts_times else 0
        
        print(f"  📈 Full E2E Time (LLM + TTS Generation):")
        print(f"     Average: {avg_latency:.0f}ms")
        print(f"     Min: {min_latency:.0f}ms")
        print(f"     Max: {max_latency:.0f}ms")
        print(f"     Total Messages: {len(all_latencies)}")
        
        print(f"\n  📊 Component Breakdown:")
        print(f"     Avg LLM: {avg_llm:.0f}ms ({(avg_llm/avg_latency)*100:.1f}%)")
        print(f"     Avg TTS: {avg_tts:.0f}ms ({(avg_tts/avg_latency)*100:.1f}%)")
        
        print(f"\n  🎯 Target: 1500ms")
        
        if avg_latency <= 1500:
            print(f"     Status: ✅ MEETS TARGET (under by {1500-avg_latency:.0f}ms)")
        else:
            print(f"     Status: ❌ ABOVE TARGET (over by {avg_latency-1500:.0f}ms)")
            print(f"\n  💡 Optimization Needed:")
            if avg_llm > 700:
                print(f"     - LLM time high ({avg_llm:.0f}ms) - optimize prompts/transitions")
            if avg_tts > 500:
                print(f"     - TTS time high ({avg_tts:.0f}ms) - shorten responses")
        
        print(f"\n  📋 Per-Conversation Averages:")
        for conv in all_results:
            if conv.get('avg_latency', 0) > 0:
                print(f"     - {conv['name']}: {conv['avg_latency']:.0f}ms")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/app/webhook_latency_test_{timestamp}.json"
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "agent_id": AGENT_ID,
        "agent_name": agent.get('name'),
        "system_prompt_length": len(agent.get('system_prompt', '')),
        "backend_url": BACKEND_URL,
        "overall_stats": {
            "avg_latency_ms": avg_latency if all_latencies else 0,
            "min_latency_ms": min_latency if all_latencies else 0,
            "max_latency_ms": max_latency if all_latencies else 0,
            "target_latency_ms": 1500,
            "meets_target": avg_latency <= 1500 if all_latencies else False,
            "total_messages": len(all_latencies)
        },
        "conversations": all_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n  💾 Results saved to: {results_file}")
    
    print(f"\n{'='*80}")
    print(f"✅ WEBHOOK TESTING COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
