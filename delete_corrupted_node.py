"""
Script to delete the corrupted node from agent's call_flow in MongoDB.
"""
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Load environment variables
load_dotenv()

AGENT_ID = "6944df147eadbccc46887cdf"
CORRUPTED_NODE_ID = "1766193952955"

async def delete_corrupted_node():
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("ERROR: MONGO_URL environment variable not set")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database()
    
    print(f"Connecting to MongoDB...")
    print(f"Looking for agent: {AGENT_ID}")
    
    # Find the agent
    agent = await db.agents.find_one({"_id": ObjectId(AGENT_ID)})
    
    if not agent:
        print(f"ERROR: Agent with ID {AGENT_ID} not found")
        return
    
    print(f"Found agent: {agent.get('name', 'Unknown')}")
    print(f"call_flow has {len(agent.get('call_flow', []))} nodes")
    
    # Find the corrupted node
    call_flow = agent.get('call_flow', [])
    corrupted_index = None
    for i, node in enumerate(call_flow):
        if node.get('id') == CORRUPTED_NODE_ID:
            corrupted_index = i
            print(f"\nFound corrupted node at index {i}:")
            print(f"  ID: {node.get('id')}")
            print(f"  Type: {node.get('type', 'MISSING')}")
            print(f"  Label: {node.get('label', 'MISSING')}")
            print(f"  Has 'data' field: {'data' in node}")
            print(f"  Keys: {list(node.keys())}")
            break
    
    if corrupted_index is None:
        print(f"\nNode with ID {CORRUPTED_NODE_ID} not found in call_flow")
        return
    
    # Delete the node using $pull
    print(f"\nDeleting node at index {corrupted_index}...")
    result = await db.agents.update_one(
        {"_id": ObjectId(AGENT_ID)},
        {"$pull": {"call_flow": {"id": CORRUPTED_NODE_ID}}}
    )
    
    if result.modified_count > 0:
        print(f"✓ Successfully deleted corrupted node!")
        
        # Verify
        agent_updated = await db.agents.find_one({"_id": ObjectId(AGENT_ID)})
        print(f"Updated call_flow has {len(agent_updated.get('call_flow', []))} nodes")
    else:
        print(f"✗ Failed to delete node (no documents modified)")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(delete_corrupted_node())
