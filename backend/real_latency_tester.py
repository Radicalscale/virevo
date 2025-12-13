"""
Real Latency Tester - Uses Actual WebSocket Infrastructure
Mimics real phone calls through the actual calling_service.py flow
Tests latency as close to production as possible
"""
import asyncio
import time
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
from datetime import datetime

# Import the ACTUAL calling service
from calling_service import CallSession

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

# Test scenarios - conversations that hit different nodes
# CRITICAL: These scenarios go 8+ nodes deep with objections to test:
# - Objection handling logic
# - KB retrieval during objections
# - Complex transition evaluation
# - Real-world latency under stress

TEST_SCENARIOS = [
    {
        "name": "Deep Objection Handling - Time Objection",
        "description": "Tests objection handling + KB retrieval + transition logic together",
        "messages": [
            "Hello",  # Initial greeting, agent asks for name
            "My name is John",  # Agent confirms name, introduces purpose
            "I don't have time for this",  # TIME OBJECTION - tests objection handling
            "What is this even about?",  # KB QUERY during objection
            "I'm still not interested",  # PERSISTENT OBJECTION
            "Why should I care?",  # CHALLENGE - needs KB + persuasion
            "I need to think about it",  # STALL OBJECTION
            "Can you call me back later?",  # CALLBACK REQUEST objection
            "Actually, tell me more about the income potential"  # TRANSITION to value discussion
        ],
        "expected_behaviors": [
            "greeting",
            "name_confirmation", 
            "objection_handling",
            "kb_retrieval",
            "objection_persistence",
            "value_reframe",
            "objection_stall",
            "objection_callback",
            "value_discussion"
        ]
    },
    {
        "name": "Deep Objection Handling - Not Interested Path",
        "description": "Tests 'not interested' objection with multiple pivots",
        "messages": [
            "Hello",
            "I'm David",
            "I'm not interested",  # NOT INTERESTED objection
            "What would this cost me?",  # PRICE objection during early rejection
            "That's too expensive",  # PRICE PUSHBACK
            "I don't think this is for me",  # DISMISSAL
            "Why are you calling me?",  # CHALLENGE + potential KB query
            "I already have something similar",  # COMPETITION objection
            "Okay, maybe I'll hear you out",  # BREAKTHROUGH - transition to engagement
            "Tell me about the requirements"  # QUALIFICATION phase
        ],
        "expected_behaviors": [
            "greeting",
            "name_confirmation",
            "objection_not_interested",
            "objection_price_early",
            "objection_price_pushback",
            "objection_dismissal",
            "objection_challenge",
            "objection_competition",
            "engagement_breakthrough",
            "qualification"
        ]
    },
    {
        "name": "Deep Objection Handling - Skeptical Path", 
        "description": "Tests skepticism, proof requests, and trust-building",
        "messages": [
            "Hello",
            "This is Sarah",
            "This sounds like a scam",  # TRUST objection
            "How do I know this is real?",  # PROOF REQUEST - needs KB
            "Do you have any proof this works?",  # SOCIAL PROOF request
            "I've been burned before",  # PAST EXPERIENCE objection
            "Why should I trust you?",  # TRUST CHALLENGE
            "What's the catch?",  # SKEPTICISM - looking for hidden costs
            "Tell me about the success stories",  # KB QUERY for testimonials
            "Alright, I'm listening"  # ENGAGEMENT after trust built
        ],
        "expected_behaviors": [
            "greeting",
            "name_confirmation",
            "objection_scam",
            "objection_proof",
            "objection_social_proof",
            "objection_past_experience",
            "objection_trust",
            "objection_catch",
            "kb_testimonials",
            "engagement"
        ]
    },
    {
        "name": "Rapid-Fire Mixed Objections",
        "description": "Tests agent handling multiple objection types in quick succession",
        "messages": [
            "Hello",
            "I'm Mike",
            "I'm busy right now",  # TIME
            "And I don't have money",  # MONEY
            "Plus I don't trust these things",  # TRUST
            "What even is this?",  # KB QUERY
            "Sounds complicated",  # COMPLEXITY objection
            "I'm not qualified",  # SELF-DOUBT objection
            "Why me?",  # TARGETING objection
            "Give me the quick version"  # ENGAGEMENT but time-constrained
        ],
        "expected_behaviors": [
            "greeting",
            "name_confirmation",
            "objection_time",
            "objection_money",
            "objection_trust",
            "kb_query",
            "objection_complexity",
            "objection_qualification",
            "objection_targeting",
            "quick_value_prop"
        ]
    },
    {
        "name": "Positive Engagement After Objections",
        "description": "Tests transition from objections to qualification",
        "messages": [
            "Hello",
            "This is Jennifer",
            "I'm not sure about this",  # SOFT OBJECTION
            "What are the requirements?",  # INFO SEEKING
            "I'm employed",  # QUALIFICATION - employment status
            "I make around 75k per year",  # QUALIFICATION - income
            "Yes, I have a vehicle",  # QUALIFICATION - vehicle
            "I do have some capital available",  # QUALIFICATION - capital
            "When would this start?",  # TIMELINE question - KB query
            "Okay, I'm interested in learning more"  # STRONG ENGAGEMENT
        ],
        "expected_behaviors": [
            "greeting",
            "name_confirmation",
            "objection_soft",
            "info_seeking",
            "qualification_employment",
            "qualification_income",
            "qualification_vehicle",
            "qualification_capital",
            "kb_timeline",
            "next_steps"
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
    return agent, user


async def run_conversation_test(scenario: dict, agent: dict, user: dict, db) -> dict:
    """Run a single conversation test scenario using REAL calling infrastructure"""
    
    print(f"\n{'='*80}")
    print(f"🧪 Testing Scenario: {scenario['name']}")
    print(f"{'='*80}")
    
    # Create a REAL CallSession - same as what happens in production
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
    
    # Process each message in the scenario
    for i, user_message in enumerate(scenario['messages']):
        print(f"\n  Message {i+1}: \"{user_message}\"")
        
        message_start = time.time()
        
        try:
            # Use the ACTUAL processing method from calling_service.py
            # This goes through the full flow: node selection, LLM call, streaming, etc.
            response = await session.process_user_input(user_message)
            
            message_latency = (time.time() - message_start) * 1000  # milliseconds
            
            # Handle None response
            if response is None:
                response = "[No response generated]"
            
            # Convert to string if it's not already
            if not isinstance(response, str):
                response = str(response)
            
            # Get current node from session
            current_node_id = session.current_node_id if hasattr(session, 'current_node_id') else None
            current_node_label = "Unknown"
            
            if current_node_id:
                for node in agent.get('call_flow', []):
                    if node.get('id') == current_node_id:
                        current_node_label = node.get('label', 'Unknown')
                        break
            
            print(f"    ⏱️  Latency: {message_latency:.0f}ms")
            print(f"    📍 Node: {current_node_label}")
            print(f"    💬 Response: {response[:100]}...")
            
            scenario_results['messages'].append({
                "user_message": user_message,
                "agent_response": response,
                "latency_ms": message_latency,
                "node_id": current_node_id,
                "node_label": current_node_label
            })
            
            scenario_results['total_latency'] += message_latency
            scenario_results['nodes_visited'].append(current_node_label)
            
        except Exception as e:
            message_latency = (time.time() - message_start) * 1000
            print(f"    ❌ Error: {e}")
            print(f"    ⏱️  Latency before error: {message_latency:.0f}ms")
            scenario_results['errors'].append({
                "message": user_message,
                "error": str(e),
                "latency_ms": message_latency
            })
    
    # Calculate averages
    if scenario_results['messages']:
        scenario_results['avg_latency'] = scenario_results['total_latency'] / len(scenario_results['messages'])
    
    print(f"\n  📊 Scenario Summary:")
    print(f"     Average Latency: {scenario_results['avg_latency']:.0f}ms")
    print(f"     Total Latency: {scenario_results['total_latency']:.0f}ms")
    print(f"     Messages: {len(scenario_results['messages'])}")
    print(f"     Errors: {len(scenario_results['errors'])}")
    
    return scenario_results


async def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              REAL LATENCY TESTER - Production-Like Testing                  ║
║              Uses Actual WebSocket Infrastructure & Calling Service          ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Setup database connection
    mongo_url = os.environ.get('MONGO_URL')
    mongo_client = AsyncIOMotorClient(mongo_url)
    db = mongo_client['test_database']
    
    # Load agent and user
    print("📥 Loading agent and user from MongoDB...")
    agent, user = await get_agent_and_user()
    print(f"✅ Loaded agent: {agent.get('name')}")
    print(f"✅ System Prompt: {len(agent.get('system_prompt', '')):,} chars")
    print(f"✅ Call Flow Nodes: {len(agent.get('call_flow', []))}")
    
    # Run all test scenarios
    all_results = []
    
    for scenario in TEST_SCENARIOS:
        result = await run_conversation_test(scenario, agent, user, db)
        all_results.append(result)
        
        # Small delay between scenarios
        await asyncio.sleep(1)
    
    # Calculate overall statistics
    print(f"\n{'='*80}")
    print(f"📊 OVERALL TEST RESULTS")
    print(f"{'='*80}")
    
    all_latencies = []
    total_messages = 0
    total_errors = 0
    
    for result in all_results:
        for msg in result['messages']:
            all_latencies.append(msg['latency_ms'])
        total_messages += len(result['messages'])
        total_errors += len(result['errors'])
    
    avg_latency = 0
    min_latency = 0
    max_latency = 0
    
    if all_latencies:
        avg_latency = sum(all_latencies) / len(all_latencies)
        min_latency = min(all_latencies)
        max_latency = max(all_latencies)
        
        print(f"\n  Average Latency: {avg_latency:.0f}ms")
        print(f"  Min Latency: {min_latency:.0f}ms")
        print(f"  Max Latency: {max_latency:.0f}ms")
        print(f"  Total Messages: {total_messages}")
        print(f"  Total Errors: {total_errors}")
        
        # Target analysis
        target_latency = 1500  # 1.5 seconds
        if avg_latency <= target_latency:
            print(f"\n  ✅ TARGET MET! Average latency {avg_latency:.0f}ms is under {target_latency}ms")
        else:
            difference = avg_latency - target_latency
            improvement_needed = (difference / avg_latency) * 100
            print(f"\n  ⚠️  ABOVE TARGET: Need {difference:.0f}ms improvement ({improvement_needed:.1f}% reduction)")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/app/latency_test_results_{timestamp}.json"
    
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "agent_id": AGENT_ID,
        "agent_name": agent.get('name'),
        "system_prompt_length": len(agent.get('system_prompt', '')),
        "call_flow_nodes": len(agent.get('call_flow', [])),
        "overall_stats": {
            "avg_latency_ms": avg_latency if all_latencies else 0,
            "min_latency_ms": min_latency if all_latencies else 0,
            "max_latency_ms": max_latency if all_latencies else 0,
            "total_messages": total_messages,
            "total_errors": total_errors,
            "target_latency_ms": 1500,
            "meets_target": avg_latency <= 1500 if all_latencies else False
        },
        "scenarios": all_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n  💾 Detailed results saved to: {results_file}")
    
    # Append summary to LATENCY_ITERATIONS.md
    log_entry = f"""
## Test Run: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Agent:** {agent.get('name')} ({AGENT_ID})

### Results:
- **Average Latency:** {avg_latency:.0f}ms
- **Min Latency:** {min_latency:.0f}ms  
- **Max Latency:** {max_latency:.0f}ms
- **Target:** 1500ms
- **Status:** {'✅ MEETS TARGET' if avg_latency <= 1500 else f'⚠️ NEEDS {(avg_latency - 1500):.0f}ms IMPROVEMENT'}

### Test Scenarios:
"""
    
    for result in all_results:
        log_entry += f"- {result['scenario']}: {result['avg_latency']:.0f}ms avg\n"
    
    log_entry += f"\n### Detailed Results: `{results_file}`\n\n---\n\n"
    
    with open('/app/LATENCY_ITERATIONS.md', 'a') as f:
        f.write(log_entry)
    
    print(f"  ✅ Summary logged to LATENCY_ITERATIONS.md")
    
    print(f"\n{'='*80}")
    print(f"✅ TESTING COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
