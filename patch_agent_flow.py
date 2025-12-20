from pymongo import MongoClient
from bson import ObjectId
import time
import json
import logging

# Setup
client = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db = client['test_database']
agent_id = '6944df147eadbccc46887cdf'

def patch_agent():
    agent = db['agents'].find_one({'_id': ObjectId(agent_id)})
    if not agent:
        print("❌ Agent not found")
        return

    nodes = agent.get('call_flow', [])
    if not nodes:
        nodes = agent.get('flow', {}).get('nodes', [])
        # If still empty, assume call_flow structure
        if not nodes and 'call_flow' in agent:
            nodes = agent['call_flow']

    # Generate ID for new node
    new_node_id = str(int(time.time() * 1000))
    print(f"🆔 New Node ID: {new_node_id}")

    # Create New Node
    new_node = {
        "id": new_node_id,
        "type": "conversation",
        "label": "Greeting_CatchAll_ConfirmName",
        "data": {
            "mode": "script",
            "content": "I apologize, I just want to ensure I have the right person. Am I speaking with {{customer_name}}?",
            "transitions": [
                {
                    "id": str(int(time.time() * 1000) + 1),
                    "condition": "Confirms name (Yes|Speaking|This is he/she|etc)",
                    "target": "1763159750250" # Existing Intro Node
                },
                {
                    "id": str(int(time.time() * 1000) + 2),
                    "condition": "Wrong number (No John here|Wrong number|etc)",
                    "target": "1763159798266" # Existing Wrong Number Node
                }
            ],
            "goal": "Verify user identity strictly.",
            "use_parallel_llm": True,
            "skip_mandatory_precheck": True
        }
    }
    
    # Update 'nextNode' to 'target' in transitions if that's the format used by debug/editor
    # Wait, the JSON dump in Step 943 showed "nextNode" but debug tool prints "target".
    # server.py uses "nextNode". I should use "nextNode" to match Step 943 output.
    
    new_node['data']['transitions'][0]['nextNode'] = "1763159750250"
    new_node['data']['transitions'][1]['nextNode'] = "1763159798266"
    # Remove 'target' key to match schema
    del new_node['data']['transitions'][0]['target']
    del new_node['data']['transitions'][1]['target']

    # Find Greeting Node
    greeting_node = None
    for n in nodes:
        if n.get('label') == 'Greeting' or n.get('id') == '2' or n.get('data', {}).get('label') == 'Greeting':
            greeting_node = n
            break
            
    if not greeting_node:
        print("❌ Greeting node not found")
        return

    print("✅ Found Greeting Node")
    
    # Add Catch-All Transition
    new_transition = {
        "id": str(int(time.time() * 1000) + 3),
        "condition": "Does not conform (Any other response / Resistance)",
        "nextNode": new_node_id
    }
    
    # Append
    greeting_node['data']['transitions'].append(new_transition)
    print("➕ Added Catch-All Transition to Greeting")
    
    # Add New Node to Flow
    nodes.append(new_node)
    print("➕ Added New Node to Flow")
    
    # Save
    if 'call_flow' in agent:
        db['agents'].update_one({'_id': ObjectId(agent_id)}, {'$set': {'call_flow': nodes}})
    else:
        # If nested inside flow.nodes
        db['agents'].update_one({'_id': ObjectId(agent_id)}, {'$set': {'flow.nodes': nodes}})
        
    print("💾 Agent flow updated in MongoDB")

if __name__ == "__main__":
    patch_agent()
