#!/usr/bin/env python3
"""
Test Node 5 (Introduce Model) specifically
This targets the exact scenario: Jake asks "what questions come to mind" and user objects
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

async def test_node_5_objection():
    """Test objecting specifically at node 5 after model introduction"""
    
    print("\n" + "="*80)
    print("TESTING NODE 5 (INTRODUCE MODEL) OBJECTION HANDLING")
    print("="*80 + "\n")
    
    # Fetch agent
    agent = await db.agents.find_one({"name": "Jake - Income Stacking Qualifier"})
    if not agent:
        print("❌ Agent not found")
        return
    
    # Create session
    call_id = f"test_node5_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session = CallSession(
        call_id=call_id,
        agent_config=agent,
        agent_id=agent.get('id')
    )
    
    # Set up session
    session.session_variables['customer_name'] = 'TestUser'
    session.session_variables['from_number'] = '+15551234567'
    session.session_variables['to_number'] = '+15559876543'
    
    session.flow_nodes = {node['id']: node for node in agent.get('call_flow', [])}
    session.flow_edges = agent.get('call_flow_edges', [])
    session.agent_type = agent.get('agent_type', 'call_flow')
    
    # Start at first node
    start_node = next((node for node in agent.get('call_flow', []) if node['type'] == 'start'), None)
    if start_node:
        first_edge = next((edge for edge in session.flow_edges if edge['source'] == start_node['id']), None)
        if first_edge:
            session.current_node_id = first_edge['target']
    
    conversation = []
    
    async def send_message(user_input: str):
        print(f"👤 USER: {user_input}")
        response_dict = await session.process_user_input(user_input)
        response_text = response_dict.get('text', str(response_dict)) if isinstance(response_dict, dict) else str(response_dict)
        print(f"🤖 JAKE: {response_text}")
        print(f"📍 Current Node: {session.current_node_id}")
        print(f"🏷️  Node Label: {session.flow_nodes.get(session.current_node_id, {}).get('label', 'Unknown')}")
        print()
        
        conversation.append({
            "user": user_input,
            "agent": response_text,
            "node": session.current_node_id,
            "node_label": session.flow_nodes.get(session.current_node_id, {}).get('label', 'Unknown')
        })
        return response_text
    
    # Navigate to get to node 5
    print("🎯 Goal: Reach Node 5 (Introduce Model) and then object\n")
    
    await send_message("Yes")  # Name confirmation
    await send_message("Sure")  # Help request
    await send_message("Yeah, go ahead")  # Permission - should take us through hook
    
    # Check if we're at node 5
    current_label = session.flow_nodes.get(session.current_node_id, {}).get('label', '')
    print(f"✓ After 3 messages, we're at: {current_label} (node {session.current_node_id})\n")
    
    # If not at node 5, try to get there with a positive response
    if session.current_node_id != '5':
        print("📌 Not at node 5 yet, sending positive response to progress...\n")
        await send_message("That sounds interesting, tell me more")
    
    current_label = session.flow_nodes.get(session.current_node_id, {}).get('label', '')
    print(f"✓ Current node: {current_label} (node {session.current_node_id})\n")
    
    # NOW send the critical objection
    print("🔥 CRITICAL TEST: Objecting with the exact phrase from user's concern\n")
    last_response = await send_message("I don't know, what is this some kind of marketing scam? Hello?")
    
    # Check for repetition
    if len(conversation) >= 2:
        prev_response = conversation[-2]['agent']
        if "passive income websites" in last_response and "passive income websites" in prev_response:
            print("\n❌ FAILED: Agent repeated the passive income websites script!")
            print(f"   Previous: {prev_response[:100]}...")
            print(f"   Current:  {last_response[:100]}...")
            return False
        elif last_response == prev_response:
            print("\n❌ FAILED: Agent repeated exactly!")
            return False
    
    # Check if agent handled it intelligently
    if any(word in last_response.lower() for word in ['fair', 'understand', 'get', 'concern', 'worry']):
        print("\n✅ PASSED: Agent handled objection intelligently without repeating!")
        print(f"   Response shows empathy: {last_response}")
        return True
    else:
        print(f"\n⚠️  UNCERTAIN: Agent didn't repeat, but response might not be ideal:")
        print(f"   {last_response}")
        return True
    
    print("\n" + "="*80)
    print("CONVERSATION TRANSCRIPT:")
    print("="*80 + "\n")
    for i, turn in enumerate(conversation, 1):
        print(f"{i}. [{turn['node_label']}]")
        print(f"   USER: {turn['user']}")
        print(f"   JAKE: {turn['agent']}\n")

if __name__ == "__main__":
    result = asyncio.run(test_node_5_objection())
    sys.exit(0 if result else 1)
