#!/usr/bin/env python3
"""
Update Greeting Prompt - Stubborn Verification
===========================================
Updates the instructions for the "Greeting" node to prevent
"pseudo-transitions" where the agent introduces itself before
confirming the user's identity.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Agent ID from logs (Call v3:ih...)
AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"

# Connection string (from apply_node_fixes.py)
MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'

def update_greeting_node():
    if not MONGO_URL:
        print("❌ MONGO_URL not found")
        return

    try:
        client = MongoClient(MONGO_URL)
        db = client['test_database']
        agents_collection = db['agents']
        
        agent = agents_collection.find_one({"id": AGENT_ID})
        if not agent:
            # Try searching by _id if string ID fails
            from bson import ObjectId
            try:
                agent = agents_collection.find_one({"_id": ObjectId(AGENT_ID)})
            except:
                pass
        
        if not agent:
            print(f"❌ Agent {AGENT_ID} not found")
            return

        print(f"✅ Found agent: {agent.get('name')} (ID: {AGENT_ID})")
        
        nodes = agent.get('call_flow', [])
        greeting_node_idx = -1
        greeting_node = None
        
        if nodes:
            print("DEBUG: Structure of Node 0:")
            print(nodes[0])
        
        # Find Greeting node
        for i, node in enumerate(nodes):
            label = node.get('label') or node.get('data', {}).get('label', '')
            print(f"Node {i}: {label}")  # Debug print
            if 'Greeting' in label or 'Start' in label or 'Opening' in label:
                greeting_node_idx = i
                greeting_node = node
                print(f"✅ Potential Match: {label}")
                # Don't break immediately, prefer "Greeting" over "Start" if both exist?
                # Actually, let's look for exact substring match "Greeting" first.
                if "Greeting" in label:
                    break
        
        if greeting_node_idx == -1:
            print("❌ Greeting node not found. Available nodes:")
            for n in nodes:
                print(f"- {n.get('data', {}).get('label', 'No Label')}")
            return
            
        print(f"✅ Found Greeting node at index {greeting_node_idx}")
        
        # Current Content
        current_content = greeting_node.get('data', {}).get('content', '')
        print("\n--- Current Content Snippet ---")
        print(current_content[:200] + "...")
        
        # NEW Content - Appending the Stubborn Instruction at the TOP
        stubborn_instruction = """## STRICT VERIFICATION REQUIRED
Your ONLY goal is to verify you are speaking to {{customer_name}}.
If the user says 'Hello', 'Hi', or 'Who is this?', do NOT introduce yourself fully.
REPEAT the verification: "I'm looking for {{customer_name}}, is that you?"
Do NOT proceed to the pitch until you have explicit confirmation (Yes, Speaking).

"""
        # Check if already applied
        if "STRICT VERIFICATION REQUIRED" in current_content:
            print("\n⚠️  Fix already applied! Skipping.")
            return

        new_content = stubborn_instruction + current_content
        
        # Apply update
        result = agents_collection.update_one(
            {"id": AGENT_ID},
            {"$set": {f"call_flow.{greeting_node_idx}.data.content": new_content}}
        )
        
        if result.modified_count > 0:
            print("\n✅ SUCCESSFULLY UPDATED Greeting Node Content")
        else:
            print("\n❌ Update failed (no document modified)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_greeting_node()
