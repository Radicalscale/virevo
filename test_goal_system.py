#!/usr/bin/env python3
"""
Test the goal system - verify agent continues conversation when transitions don't match
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from calling_service import CallSession
from motor.motor_asyncio import AsyncIOMotorClient

async def test_goal_system():
    print("=" * 80)
    print("TESTING GOAL SYSTEM - NO FREEZE ON UNMATCHED TRANSITIONS")
    print("=" * 80)
    
    # Connect to MongoDB
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get Jake agent
    agent_id = "04b9509d-cfd9-4e3e-9146-f805c858b823"
    agent = await db.agents.find_one({"id": agent_id})
    
    if not agent:
        print(f"❌ Agent {agent_id} not found!")
        return
    
    print(f"✅ Found agent: {agent.get('name')}")
    print()
    
    # Create a call session
    session_id = "test_goal_system"
    session = CallSession(session_id, agent)
    
    # Set a customer name
    session.session_variables['customer_name'] = "John"
    
    print("SCENARIO: Testing prompt-mode node with goal when user gives unexpected response")
    print("-" * 80)
    
    # Simulate the conversation to get to a prompt node
    print("📱 Step 1: Simulate greeting flow to reach Q&A node...")
    
    # Fast-forward by manually setting the current node to Q&A node (node 9)
    flow_nodes = agent.get("call_flow", [])
    qa_node = None
    for node in flow_nodes:
        if node.get("label") == "Q&A Strategic Narrative":
            qa_node = node
            break
    
    if not qa_node:
        print("❌ Could not find Q&A Strategic Narrative node")
        return
    
    print(f"✅ Found Q&A node (ID: {qa_node.get('id')})")
    session.current_node_id = qa_node.get("id")
    
    # Add some conversation history
    session.conversation_history = [
        {"role": "assistant", "content": "In a nutshell, we set up passive income websites, and we let them produce income for you. What questions come to mind?"},
        {"role": "user", "content": "Hello?"}
    ]
    
    print("\n📱 USER says something unexpected: 'Hello?'")
    print("   (This doesn't match any transition - should use GOAL to continue)")
    print("-" * 80)
    
    # Process the message
    response = await session.process_user_input("Hello?")
    
    print(f"\n🤖 AGENT: {response.get('text', '')[:300]}")
    print(f"\n📊 Current node after response: {session.current_node_id}")
    print(f"   (Should still be on Q&A node: {qa_node.get('id')})")
    
    if session.current_node_id == qa_node.get("id"):
        print("\n✅ SUCCESS! Agent stayed on current node and used goal to continue conversation")
    else:
        print(f"\n❌ FAILED! Agent transitioned to different node instead of using goal")
    
    # Check if response is reasonable
    if response.get('text') and len(response.get('text', '')) > 20:
        print("✅ Agent generated a meaningful response (not frozen)")
    else:
        print("❌ Agent response seems empty or frozen")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_goal_system())
