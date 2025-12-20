#!/usr/bin/env python3
"""Rebuild the antigrav test agent with all optimizations."""

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone

MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'

# The optimized node contents
NODE_15K_CONTENT = """## INSTRUCTION: BRIDGE & PIVOT
1. **BRIDGE:** Acknowledge the user's previous input naturally (e.g. validate their revenue/situation). 
   - CONSTRAINT: Do NOT use stock phrases like "Okay", "Got it", or "I understand".
2. **THE PIVOT:** Transition to the capital requirement. 
3. **REQUIRED STATEMENT:** You MUST state that "for this specific model, it helps to have about fifteen to twenty-five thousand dollars in liquid capital for setup and runway."
4. **GOAL:** Ask if they generally have that range accessible."""

NODE_5K_CONTENT = """## INSTRUCTION: BRIDGE & PIVOT
1. **BRIDGE:** Acknowledge the user's previous input naturally.
   - CONSTRAINT: Do NOT use stock phrases like "Okay", "Got it", or "I understand".
2. **THE PIVOT:** Transition to the capital requirement.
3. **REQUIRED STATEMENT:** You MUST state that "for this model, we typically look for about five thousand dollars in liquid capital to get started."
4. **GOAL:** Ask if they have that amount accessible."""

def main():
    client = MongoClient(MONGO_URL)
    db = client['test_database']
    
    # Find source agent
    source = db['agents'].find_one({'name': 'JK First Caller-optimizer3'})
    if not source:
        source = db['agents'].find_one({'name': 'JK First Caller'})
    
    if not source:
        print("❌ No source agent found")
        return
    
    print(f"✅ Found source: {source['name']}")
    
    # Check if antigrav already exists
    existing = db['agents'].find_one({'name': 'JK First Caller-optimizer3-antigrav'})
    if existing:
        print(f"⚠️ Antigrav agent already exists (ID: {existing['_id']})")
        agent_id = existing['_id']
        call_flow = existing.get('call_flow', [])
    else:
        # Create copy
        new_agent = dict(source)
        del new_agent['_id']
        new_agent['name'] = 'JK First Caller-optimizer3-antigrav'
        new_agent['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        result = db['agents'].insert_one(new_agent)
        agent_id = result.inserted_id
        call_flow = new_agent.get('call_flow', [])
        print(f"✅ Created new agent: {agent_id}")
    
    # Apply optimizations to call_flow
    updates = 0
    for node in call_flow:
        label = node.get('data', {}).get('label') or node.get('label')
        
        if label == 'N_AskCapital_15k_V1_Adaptive':
            node['data']['content'] = NODE_15K_CONTENT
            node['data']['script'] = ''
            node['data']['mode'] = 'prompt'
            updates += 1
            print(f"  ✅ Updated N_AskCapital_15k")
            
        elif label == 'N_AskCapital_5k_V1_Adaptive':
            node['data']['content'] = NODE_5K_CONTENT
            node['data']['script'] = ''
            node['data']['mode'] = 'prompt'
            updates += 1
            print(f"  ✅ Updated N_AskCapital_5k")
    
    # Save changes
    if updates > 0:
        db['agents'].update_one(
            {'_id': agent_id},
            {'$set': {'call_flow': call_flow, 'updated_at': datetime.now(timezone.utc).isoformat()}}
        )
        print(f"✅ Saved {updates} node updates")
    
    print(f"\n🎉 Agent ready: {agent_id}")
    client.close()

if __name__ == '__main__':
    main()
