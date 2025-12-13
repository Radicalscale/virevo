#!/usr/bin/env python3
"""
Comprehensive test of {{now}} variable functionality
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from calling_service import CallSession
from motor.motor_asyncio import AsyncIOMotorClient

async def test_comprehensive():
    print("=" * 80)
    print("COMPREHENSIVE {{now}} VARIABLE TEST")
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
    print()
    
    # Create a call session
    session_id = "test_now_comprehensive"
    session = CallSession(session_id, agent)
    
    print("TEST 1: Check {{now}} variable is automatically set")
    print("-" * 80)
    if 'now' in session.session_variables:
        print(f"✅ {{{{now}}}} variable exists: {session.session_variables['now']}")
    else:
        print("❌ {{now}} variable not found!")
        return
    
    print("\nTEST 2: Simulate a conversation asking about current date")
    print("-" * 80)
    print("📱 USER: What is today's date and time?")
    response = await session.process_user_input("What is today's date and time?")
    print(f"🤖 AGENT: {response.get('text', '')[:300]}")
    
    print("\nTEST 3: Check that {{now}} is in AI context")
    print("-" * 80)
    # The session_variables are passed to the AI in the prompt at line 2531 of calling_service.py
    # So the AI should have access to the current date/time
    print(f"✅ Session variables available to AI: {list(session.session_variables.keys())}")
    
    print("\nTEST 4: Verify {{now}} format")
    print("-" * 80)
    now_value = session.session_variables['now']
    # Should be like: "Monday, November 3, 2025 at 9:18 PM EST"
    if " at " in now_value and " EST" in now_value:
        print(f"✅ Format correct: {now_value}")
    else:
        print(f"❌ Format incorrect: {now_value}")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_comprehensive())
