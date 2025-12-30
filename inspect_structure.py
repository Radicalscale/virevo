import os
import sys
import asyncio
import json
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, ObjectId):
        return str(obj)
    return str(obj)

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    agent_id = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
    
    agent = await db.agents.find_one({"id": agent_id})
    if not agent:
        print("Agent not found")
        return

    print("Top Level Keys:", list(agent.keys()))
    
    # Check if 'rephrase_prompt' appears in string dump
    agent_str = str(agent)
    if 'rephrase_prompt' in agent_str:
        print("\nFOUND 'rephrase_prompt' in document string!")
        # Try to locate it
        import re
        matches = re.findall(r"'rephrase_prompt':\s*'([^']*)'", agent_str)
        if matches:
            print("Values found:", matches)
        else:
            print("Couln't extract value nicely with regex, assume nested.")
    else:
        print("\n'rephrase_prompt' NOT found in document string.")

    # Check for 'graph' key
    if 'graph' in agent:
        print("\nFound 'graph' key. Checking keys:", agent['graph'].keys())
        if 'nodes' in agent['graph']:
            print(f"nodes in graph: {len(agent['graph']['nodes'])}")

    # Check for 'start_node_id'
    print(f"\nStart Node ID: {agent.get('start_node_id')}")

if __name__ == "__main__":
    from datetime import date, datetime
    asyncio.run(main())
