#!/usr/bin/env python3
"""
Simulate a complete call session to test the Schedule Tester2 agent flow
This bypasses the HTTP API and directly tests the CallSession logic
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from calling_service import CallSession
from motor.motor_asyncio import AsyncIOMotorClient
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_full_flow():
    print("=" * 80)
    print("TESTING SCHEDULE TESTER2 AGENT - FULL FLOW SIMULATION")
    print("=" * 80)
    
    # Connect to MongoDB
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get the Schedule Tester2 agent
    agent_id = "68bbb816-50d0-4d36-ae82-f04473e67483"
    agent = await db.agents.find_one({"id": agent_id})
    
    if not agent:
        print(f"❌ Agent {agent_id} not found!")
        return
    
    print(f"✅ Found agent: {agent.get('name')}")
    print(f"   Agent ID: {agent_id}")
    print()
    
    # Create a call session
    session_id = "test_simulation_session"
    session = CallSession(session_id, agent)
    
    print("=" * 80)
    print("CONVERSATION SIMULATION")
    print("=" * 80)
    
    # Message 1: User says hello
    print("\n📱 USER: Hello")
    print("-" * 80)
    response1 = await session.process_user_input("Hello")
    print(f"🤖 AGENT: {response1.get('text', '')[:200]}")
    print(f"📊 Current node: {session.current_node_id}")
    print(f"📚 History length: {len(session.conversation_history)}")
    
    # Message 2: User provides scheduling info
    print("\n📱 USER: I want to book for November 5th at 3pm Eastern")
    print("-" * 80)
    response2 = await session.process_user_input("I want to book for November 5th at 3pm Eastern")
    print(f"🤖 AGENT: {response2.get('text', '')[:200]}")
    print(f"📊 Current node: {session.current_node_id}")
    print(f"📚 History length: {len(session.conversation_history)}")
    
    print("\n" + "=" * 80)
    print("SESSION VARIABLES")
    print("=" * 80)
    for key, value in session.session_variables.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print("CHECKING CONVERTER WEBHOOK EXECUTION")
    print("=" * 80)
    
    # Check if scheduleTime was updated
    schedule_time = session.session_variables.get("scheduleTime", "NOT SET")
    print(f"📅 scheduleTime value: {schedule_time}")
    
    if "2025-11-" in str(schedule_time):
        print("✅ SUCCESS! scheduleTime was converted to ISO format")
    elif "November" in str(schedule_time):
        print("❌ FAILED! scheduleTime still has unconverted value")
    else:
        print("⚠️  UNKNOWN! scheduleTime has unexpected value")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_full_flow())
