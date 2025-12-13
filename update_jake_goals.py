#!/usr/bin/env python3
"""
Update Jake agent to add goals to prompt-mode nodes
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient

async def update_agent():
    print("=" * 80)
    print("UPDATING JAKE AGENT WITH GOALS")
    print("=" * 80)
    
    # Connect to MongoDB
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent_id = "04b9509d-cfd9-4e3e-9146-f805c858b823"
    
    # Get the agent
    agent = await db.agents.find_one({"id": agent_id})
    if not agent:
        print(f"❌ Agent {agent_id} not found!")
        return
    
    print(f"✅ Found agent: {agent.get('name')}")
    
    # Update specific nodes with goals
    call_flow = agent.get("call_flow", [])
    updates_made = 0
    
    for node in call_flow:
        node_id = node.get("id")
        node_type = node.get("type")
        node_data = node.get("data", {})
        mode = node_data.get("mode", "")
        
        # Only add goals to prompt-mode conversation nodes
        if node_type == "conversation" and mode == "prompt":
            # Check if goal already exists
            if not node_data.get("goal"):
                # Add appropriate goal based on node
                label = node.get("label", "")
                
                if label == "Deframe Objection":
                    node_data["goal"] = "Handle their objection by asking questions to understand their concern. Once they show any curiosity or openness, guide them to want to learn more about the opportunity."
                    updates_made += 1
                elif label == "Q&A Strategic Narrative":
                    node_data["goal"] = "Answer their questions about the business model. If they ask about price, defer to the strategy call. After answering, ask the value-framing question about having an extra $20k/month."
                    updates_made += 1
                
                print(f"  ✅ Added goal to node: {label}")
    
    # Save updates
    if updates_made > 0:
        await db.agents.update_one(
            {"id": agent_id},
            {"$set": {"call_flow": call_flow}}
        )
        print(f"\n✅ Updated {updates_made} nodes with goals")
    else:
        print("\n✅ No updates needed - all prompt nodes have goals or are script-based")
    
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(update_agent())
