#!/usr/bin/env python3
"""
Test the {{now}} variable in session
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from calling_service import CallSession
from motor.motor_asyncio import AsyncIOMotorClient

async def test_now_variable():
    print("=" * 80)
    print("TESTING {{now}} VARIABLE")
    print("=" * 80)
    
    # Connect to MongoDB
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get any agent
    agent = await db.agents.find_one()
    
    if not agent:
        print("❌ No agents found!")
        return
    
    print(f"✅ Found agent: {agent.get('name')}")
    print()
    
    # Create a call session
    session_id = "test_now_session"
    session = CallSession(session_id, agent)
    
    print("SESSION VARIABLES (automatically set):")
    print("-" * 80)
    for key, value in session.session_variables.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    
    if 'now' in session.session_variables:
        print("✅ SUCCESS! {{now}} variable is set")
        print(f"   Value: {session.session_variables['now']}")
    else:
        print("❌ FAILED! {{now}} variable not found")
    
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_now_variable())
