#!/usr/bin/env python3
"""
Test the repetition fix - simulate the exact scenario from the logs
"""

import asyncio
import os
import sys
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from calling_service import CallSession
from datetime import datetime

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

async def test_repetition_scenario():
    """Test the exact scenario that caused repetition"""
    
    print("\n" + "="*80)
    print("TESTING REPETITION FIX")
    print("="*80 + "\n")
    
    # Fetch agent
    agent = await db.agents.find_one({"id": "474917c1-4888-47b8-b76b-f11a18f19d39"})
    if not agent:
        print("❌ Agent not found")
        return False
    
    # Create session
    call_id = f"test_repetition_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session = CallSession(
        call_id=call_id,
        agent_config=agent,
        agent_id=agent.get('id')
    )
    
    # Set up session
    session.session_variables['customer_name'] = 'Kendrick'
    session.session_variables['customer_email'] = 'kendrickbowman9@gmail.com'
    session.session_variables['from_number'] = '+14048000152'
    session.session_variables['to_number'] = '+17708336397'
    session.session_variables['phone_number'] = '+17708336397'
    
    session.flow_nodes = {node['id']: node for node in agent.get('call_flow', [])}
    session.flow_edges = agent.get('call_flow_edges', [])
    session.agent_type = agent.get('agent_type', 'call_flow')
    
    # Start at first node
    start_node = next((node for node in agent.get('call_flow', []) if node['type'] == 'start'), None)
    if start_node:
        first_edge = next((edge for edge in session.flow_edges if edge['source'] == start_node['id']), None)
        if first_edge:
            session.current_node_id = first_edge['target']
    
    async def send_message(user_input: str):
        print(f"👤 USER: {user_input}")
        response_dict = await session.process_user_input(user_input)
        response_text = response_dict.get('text', str(response_dict)) if isinstance(response_dict, dict) else str(response_dict)
        print(f"🤖 JAKE: {response_text}")
        print(f"📍 Node: {session.current_node_id} ({session.flow_nodes.get(session.current_node_id, {}).get('label', 'Unknown')})")
        print()
        return response_text
    
    # Navigate to node 5 (Introduce Model)
    print("🎯 Navigating to Node 5 (Introduce Model)...\n")
    
    await send_message("Yes")  # Name
    await send_message("Sure")  # Help request
    await send_message("Yes, go ahead")  # Permission
    
    # We should now be at node 5, and it should say the "in a nutshell" line
    response1 = await send_message("Tell me more")
    
    # Check if we're at node 5
    if session.current_node_id != '5':
        print(f"⚠️ Not at node 5, at {session.current_node_id} instead")
    
    print("="*80)
    print("🔥 CRITICAL TEST: User objects with 'marketing scam' question")
    print("="*80 + "\n")
    
    # NOW the critical test - user objects
    response2 = await send_message("What is this? Some kind of marketing scam?")
    
    # Check for repetition
    print("\n" + "="*80)
    print("REPETITION CHECK")
    print("="*80 + "\n")
    
    # Check if "in a nutshell" phrase appears in response2
    if "in a nutshell" in response2.lower():
        print("❌ FAILED: Agent repeated 'in a nutshell' phrase!")
        print(f"   Response: {response2}")
        return False
    
    # Check if response2 is substantially different from response1
    words1 = set(response1.lower().split())
    words2 = set(response2.lower().split())
    if words1 and words2:
        overlap = len(words1.intersection(words2)) / len(words1)
        print(f"📊 Word overlap between responses: {overlap*100:.1f}%")
        
        if overlap > 0.6:
            print("❌ FAILED: Responses have >60% overlap (likely repetition)")
            print(f"   Response 1: {response1[:150]}...")
            print(f"   Response 2: {response2[:150]}...")
            return False
    
    # Check if response shows empathy/handling of objection
    empathy_words = ['understand', 'get', 'fair', 'concern', 'worry', 'skeptical', 'question']
    has_empathy = any(word in response2.lower() for word in empathy_words)
    
    if has_empathy:
        print("✅ PASSED: Response shows empathy and addresses objection")
        print(f"   Response: {response2}")
        return True
    else:
        print("⚠️ UNCERTAIN: No repetition, but response could be more empathetic")
        print(f"   Response: {response2}")
        return True

if __name__ == "__main__":
    result = asyncio.run(test_repetition_scenario())
    sys.exit(0 if result else 1)
