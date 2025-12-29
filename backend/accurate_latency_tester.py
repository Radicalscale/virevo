"""
Accurate Latency Tester - Mirrors Real Production System
Includes ALL components: STT, LLM, TTS, streaming delays
"""
import asyncio
import time
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
from datetime import datetime

from core_calling_service import CallSession

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

# Real system timing constants (from actual call logs)
STT_PROCESSING_TIME = 0.150  # 150ms average for speech-to-text
TTS_CHARS_PER_SECOND = 15    # ~15 chars/second for TTS generation
TTS_STARTUP_OVERHEAD = 0.200  # 200ms TTS service startup
AUDIO_STREAMING_DELAY = 0.050 # 50ms for audio packet streaming


TEST_SCENARIOS = [
    {
        "name": "Deep Objection Handling - Time Objection",
        "messages": [
            "Hello",
            "My name is John",
            "I don't have time for this",
            "What is this even about?",
            "I'm still not interested",
            "Why should I care?",
            "I need to think about it",
            "Can you call me back later?",
            "Actually, tell me more about the income potential"
        ]
    },
    {
        "name": "Deep Objection Handling - Not Interested Path",
        "messages": [
            "Hello",
            "I'm David",
            "I'm not interested",
            "What would this cost me?",
            "That's too expensive",
            "I don't think this is for me",
            "Why are you calling me?",
            "I already have something similar",
            "Okay, maybe I'll hear you out",
            "Tell me about the requirements"
        ]
    },
    {
        "name": "Deep Objection Handling - Skeptical Path",
        "messages": [
            "Hello",
            "This is Sarah",
            "This sounds like a scam",
            "How do I know this is real?",
            "Do you have any proof this works?",
            "I've been burned before",
            "Why should I trust you?",
            "What's the catch?",
            "Tell me about the success stories",
            "Alright, I'm listening"
        ]
    },
    {
        "name": "Rapid-Fire Mixed Objections",
        "messages": [
            "Hello",
            "I'm Mike",
            "I'm busy right now",
            "And I don't have money",
            "Plus I don't trust these things",
            "What even is this?",
            "Sounds complicated",
            "I'm not qualified",
            "Why me?",
            "Give me the quick version"
        ]
    },
    {
        "name": "Positive Engagement After Objections",
        "messages": [
            "Hello",
            "This is Jennifer",
            "I'm not sure about this",
            "What are the requirements?",
            "I'm employed",
            "I make around 75k per year",
            "Yes, I have a vehicle",
            "I do have some capital available",
            "When would this start?",
            "Okay, I'm interested in learning more"
        ]
    }
]


async def get_agent_and_user():
    """Load agent and user from MongoDB"""
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    user = await db.users.find_one({"id": USER_ID})
    
    if not agent or not user:
        raise Exception("Agent or user not found")
    
    agent.pop('_id', None)
    return agent, user, db


def simulate_tts_time(text: str) -> float:
    """Calculate realistic TTS generation time based on text length"""
    # Remove SSML tags for character count
    import re
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    char_count = len(clean_text)
    
    # TTS generation time = startup + (chars / rate)
    tts_time = TTS_STARTUP_OVERHEAD + (char_count / TTS_CHARS_PER_SECOND)
    
    return tts_time


async def run_conversation_test(scenario: dict, agent: dict, user: dict, db) -> dict:
    """Run conversation with FULL E2E timing simulation"""
    
    print(f"\n{'='*80}")
    print(f"🧪 Testing Scenario: {scenario['name']}")
    print(f"{'='*80}")
    
    session = CallSession(
        call_id=f"test-{int(time.time())}",
        agent_config=agent,
        agent_id=agent['id'],
        user_id=user['id'],
        knowledge_base=agent.get('knowledge_base', ''),
        db=db
    )
    
    scenario_results = {
        "scenario": scenario['name'],
        "messages": [],
        "total_latency": 0,
        "avg_latency": 0,
        "nodes_visited": [],
        "errors": []
    }
    
    for i, user_message in enumerate(scenario['messages']):
        print(f"\n  Message {i+1}: \"{user_message}\"")
        
        # Start timing
        total_start = time.time()
        
        # 1. STT Processing (simulate speech-to-text delay)
        stt_start = time.time()
        await asyncio.sleep(STT_PROCESSING_TIME)
        stt_time = time.time() - stt_start
        
        # 2. LLM Processing (actual call to process_user_input)
        llm_start = time.time()
        try:
            response = await session.process_user_input(user_message)
            llm_time = time.time() - llm_start
            
            if response is None:
                response = "[No response]"
            if not isinstance(response, str):
                # It's returning a dict, extract text
                if isinstance(response, dict):
                    response = response.get('text', str(response))
                else:
                    response = str(response)
            
        except Exception as e:
            llm_time = time.time() - llm_start
            print(f"    ❌ LLM Error: {e}")
            response = "[Error]"
            scenario_results['errors'].append({
                "message": user_message,
                "error": str(e)
            })
        
        # 3. TTS Generation (simulate text-to-speech conversion)
        tts_start = time.time()
        tts_time = simulate_tts_time(response)
        await asyncio.sleep(tts_time)
        
        # 4. Audio Streaming (simulate streaming delay)
        streaming_start = time.time()
        await asyncio.sleep(AUDIO_STREAMING_DELAY)
        streaming_time = time.time() - streaming_start
        
        # Total E2E latency
        total_latency = (time.time() - total_start) * 1000  # milliseconds
        
        # Get node info
        current_node_id = session.current_node_id if hasattr(session, 'current_node_id') else None
        current_node_label = "Unknown"
        
        if current_node_id:
            for node in agent.get('call_flow', []):
                if node.get('id') == current_node_id:
                    current_node_label = node.get('label', 'Unknown')
                    break
        
        # Log detailed breakdown
        print(f"    📊 Timing Breakdown:")
        print(f"       STT: {stt_time*1000:.0f}ms")
        print(f"       LLM: {llm_time*1000:.0f}ms")
        print(f"       TTS: {tts_time*1000:.0f}ms ({len(response)} chars)")
        print(f"       Streaming: {streaming_time*1000:.0f}ms")
        print(f"    ⏱️  Total E2E: {total_latency:.0f}ms")
        print(f"    📍 Node: {current_node_label[:50]}")
        print(f"    💬 Response: {response[:80]}...")
        
        scenario_results['messages'].append({
            "user_message": user_message,
            "agent_response": response,
            "latency_ms": total_latency,
            "breakdown": {
                "stt_ms": stt_time * 1000,
                "llm_ms": llm_time * 1000,
                "tts_ms": tts_time * 1000,
                "streaming_ms": streaming_time * 1000
            },
            "node_id": current_node_id,
            "node_label": current_node_label,
            "response_length": len(response)
        })
        
        scenario_results['total_latency'] += total_latency
        scenario_results['nodes_visited'].append(current_node_label)
    
    if scenario_results['messages']:
        scenario_results['avg_latency'] = scenario_results['total_latency'] / len(scenario_results['messages'])
    
    print(f"\n  📊 Scenario Summary:")
    print(f"     Average E2E Latency: {scenario_results['avg_latency']:.0f}ms")
    print(f"     Messages: {len(scenario_results['messages'])}")
    
    return scenario_results


async def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ACCURATE LATENCY TESTER - Full E2E Simulation                      ║
║           Includes: STT + LLM + TTS + Streaming (mirrors production)        ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    print(f"⚙️  Timing Configuration:")
    print(f"   STT Processing: {STT_PROCESSING_TIME*1000:.0f}ms per message")
    print(f"   TTS Generation: {TTS_CHARS_PER_SECOND} chars/sec + {TTS_STARTUP_OVERHEAD*1000:.0f}ms startup")
    print(f"   Streaming Delay: {AUDIO_STREAMING_DELAY*1000:.0f}ms")
    
    # Load agent and user
    print(f"\n📥 Loading agent...")
    agent, user, db = await get_agent_and_user()
    print(f"✅ Agent: {agent.get('name')}")
    print(f"✅ System Prompt: {len(agent.get('system_prompt', '')):,} chars")
    print(f"✅ Call Flow Nodes: {len(agent.get('call_flow', []))}")
    
    # Run all scenarios
    all_results = []
    
    for scenario in TEST_SCENARIOS:
        result = await run_conversation_test(scenario, agent, user, db)
        all_results.append(result)
        await asyncio.sleep(1)
    
    # Calculate overall stats
    print(f"\n{'='*80}")
    print(f"📊 OVERALL E2E TEST RESULTS")
    print(f"{'='*80}")
    
    all_latencies = []
    stt_total = 0
    llm_total = 0
    tts_total = 0
    streaming_total = 0
    total_messages = 0
    
    for result in all_results:
        for msg in result['messages']:
            all_latencies.append(msg['latency_ms'])
            stt_total += msg['breakdown']['stt_ms']
            llm_total += msg['breakdown']['llm_ms']
            tts_total += msg['breakdown']['tts_ms']
            streaming_total += msg['breakdown']['streaming_ms']
        total_messages += len(result['messages'])
    
    if all_latencies:
        avg_latency = sum(all_latencies) / len(all_latencies)
        min_latency = min(all_latencies)
        max_latency = max(all_latencies)
        
        print(f"\n  📈 E2E Latency:")
        print(f"     Average: {avg_latency:.0f}ms")
        print(f"     Min: {min_latency:.0f}ms")
        print(f"     Max: {max_latency:.0f}ms")
        print(f"     Target: 1500ms")
        
        if avg_latency <= 1500:
            print(f"     Status: ✅ MEETS TARGET (under by {1500-avg_latency:.0f}ms)")
        else:
            print(f"     Status: ❌ ABOVE TARGET (over by {avg_latency-1500:.0f}ms)")
        
        print(f"\n  📊 Component Breakdown (averages):")
        print(f"     STT: {stt_total/total_messages:.0f}ms ({(stt_total/total_messages/avg_latency)*100:.1f}%)")
        print(f"     LLM: {llm_total/total_messages:.0f}ms ({(llm_total/total_messages/avg_latency)*100:.1f}%)")
        print(f"     TTS: {tts_total/total_messages:.0f}ms ({(tts_total/total_messages/avg_latency)*100:.1f}%)")
        print(f"     Streaming: {streaming_total/total_messages:.0f}ms ({(streaming_total/total_messages/avg_latency)*100:.1f}%)")
        
        print(f"\n  🎯 Optimization Targets:")
        if llm_total/total_messages > 500:
            print(f"     ⚠️  LLM time is high ({llm_total/total_messages:.0f}ms) - optimize prompts")
        if tts_total/total_messages > 600:
            print(f"     ⚠️  TTS time is high ({tts_total/total_messages:.0f}ms) - responses too long")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/app/accurate_latency_test_{timestamp}.json"
    
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "agent_id": AGENT_ID,
        "agent_name": agent.get('name'),
        "system_prompt_length": len(agent.get('system_prompt', '')),
        "overall_stats": {
            "avg_latency_ms": avg_latency if all_latencies else 0,
            "min_latency_ms": min_latency if all_latencies else 0,
            "max_latency_ms": max_latency if all_latencies else 0,
            "avg_stt_ms": stt_total/total_messages if total_messages else 0,
            "avg_llm_ms": llm_total/total_messages if total_messages else 0,
            "avg_tts_ms": tts_total/total_messages if total_messages else 0,
            "avg_streaming_ms": streaming_total/total_messages if total_messages else 0,
            "target_latency_ms": 1500,
            "meets_target": avg_latency <= 1500 if all_latencies else False
        },
        "scenarios": all_results,
        "timing_config": {
            "stt_processing_ms": STT_PROCESSING_TIME * 1000,
            "tts_chars_per_second": TTS_CHARS_PER_SECOND,
            "tts_startup_ms": TTS_STARTUP_OVERHEAD * 1000,
            "streaming_delay_ms": AUDIO_STREAMING_DELAY * 1000
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n  💾 Results saved to: {results_file}")
    
    print(f"\n{'='*80}")
    print(f"✅ ACCURATE E2E TESTING COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
