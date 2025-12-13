#!/usr/bin/env python3
"""
Test the transition optimizer by actually using it in the agent
and verifying transitions work through Agent Tester
"""

import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
import sys

sys.path.append('/app/backend')

mongo_url = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'
db_name = 'test_database'

async def optimize_transition(grok_api_key, condition):
    """Call Grok to optimize transition"""
    optimization_prompt = f"""You are an expert at optimizing transition conditions for real-time voice agents. Your goal is to make transition evaluation FAST while preserving all logic.

**ORIGINAL TRANSITION CONDITION:**
```
{condition}
```

**YOUR TASK:**
1. Reduce verbosity by 40-60% while preserving ALL logic
2. Use pipes (|) for OR, colons (:) for IF-THEN, no spaces between pipes
3. Use abbreviations: "question" → "Q", "objection" → "obj"
4. Remove filler words but keep all examples and conditions
5. Output ONLY the optimized condition

**EXAMPLES:**
"User agrees (yes/sure/okay/agreeing to hear more/consenting to call/asking what this is about). If they add objection/question/statement: address it first, then transition. Basic acknowledgments (go ahead/sure): proceed directly without context handling."
→
"Agrees|consents (yes/sure/okay/what's this). IF obj/Q/statement: address→transition. Basic acks (go ahead/sure): proceed direct."
"""

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {grok_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-4-0709",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert at optimizing transition conditions. You reduce verbosity while preserving all logic."
                    },
                    {"role": "user", "content": optimization_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 500
            }
        )
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        # Clean up markdown
        if optimized.startswith('```'):
            lines = optimized.split('\n')
            optimized = '\n'.join([l for l in lines if not l.startswith('```')]).strip()
        
        return optimized

async def main():
    print("=" * 80)
    print("TRANSITION OPTIMIZER - REAL AGENT TEST")
    print("=" * 80)
    print()
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get Grok API key
    grok_key_doc = await db.api_keys.find_one({"service_name": "grok"})
    if not grok_key_doc:
        print("❌ Need Grok API key")
        return
    grok_api_key = grok_key_doc['api_key']
    
    # Find agent
    agent = await db.agents.find_one({"name": "JK First Caller-copy-copy"})
    if not agent:
        print("❌ Agent not found")
        return
    
    print(f"✅ Found agent: {agent['name']}")
    print(f"   Agent ID: {agent['id']}")
    print()
    
    # Find node with your example transition
    call_flow = agent['call_flow']
    target_node = None
    target_transition = None
    
    for node in call_flow:
        transitions = node.get('data', {}).get('transitions', [])
        for trans in transitions:
            condition = trans.get('condition', '')
            if 'User agrees (yes/sure/okay/agreeing to hear more' in condition:
                target_node = node
                target_transition = trans
                break
        if target_node:
            break
    
    if not target_node:
        print("❌ Could not find target transition")
        return
    
    print(f"📝 Found target node: {target_node['label']}")
    print(f"   Node ID: {target_node['id']}")
    print()
    
    # Get next node details
    next_node_id = target_transition['nextNode']
    next_node_label = "Unknown"
    for node in call_flow:
        if node['id'] == next_node_id:
            next_node_label = node['label']
            break
    
    print(f"🎯 Transition Test:")
    print(f"   From: {target_node['label']}")
    print(f"   To: {next_node_label}")
    print()
    
    original_condition = target_transition['condition']
    print(f"📝 Original Condition ({len(original_condition)} chars):")
    print(f"   {original_condition}")
    print()
    
    # Optimize
    print("🔧 Optimizing...")
    optimized_condition = await optimize_transition(grok_api_key, original_condition)
    print(f"✅ Optimized Condition ({len(optimized_condition)} chars):")
    print(f"   {optimized_condition}")
    reduction = ((len(original_condition) - len(optimized_condition)) / len(original_condition)) * 100
    print(f"   Reduction: {reduction:.1f}%")
    print()
    
    # Now let's provide manual test instructions
    print("=" * 80)
    print("MANUAL TEST INSTRUCTIONS")
    print("=" * 80)
    print()
    print("To test if the optimized transition preserves logic:")
    print()
    print("1. Go to: https://li-ai.org/agents/f251b2d9-aa56-4872-ac66-9a28accd42bb/test")
    print()
    print("2. Enable 'Transition Test Mode' checkbox")
    print()
    print("3. Select from dropdowns:")
    print(f"   - Start From Node: '{target_node['label']}'")
    print(f"   - Expected Next Node: '{next_node_label}'")
    print()
    print("4. Type message: 'yes sure'")
    print()
    print("5. Click Send")
    print()
    print("6. Expected Result: ✅ 'Transition Test Passed'")
    print()
    print("7. Now optimize the transition:")
    print("   - Go to Flow Builder")
    print(f"   - Find node: '{target_node['label']}'")
    print("   - Click ⚡ (Optimize Transition) button")
    print("   - Apply optimized condition")
    print()
    print("8. Go back to Agent Tester and repeat test:")
    print("   - Same dropdown selections")
    print("   - Same message: 'yes sure'")
    print("   - Expected: ✅ Should STILL pass")
    print()
    print("✅ If both tests pass, the optimizer preserved the logic!")
    print()
    
    # Let's also test a simpler one
    print("=" * 80)
    print("ADDITIONAL TEST CASE")
    print("=" * 80)
    print()
    
    # Find a simpler transition
    simple_node = None
    simple_trans = None
    
    for node in call_flow:
        if node['label'] == "Greeting":
            transitions = node.get('data', {}).get('transitions', [])
            if transitions:
                simple_node = node
                simple_trans = transitions[0]
                break
    
    if simple_node:
        print(f"📝 Node: {simple_node['label']}")
        print(f"   Original: {simple_trans['condition']}")
        optimized_simple = await optimize_transition(grok_api_key, simple_trans['condition'])
        print(f"   Optimized: {optimized_simple}")
        print()
        
        # Get next node
        next_id = simple_trans['nextNode']
        next_label = "Unknown"
        for node in call_flow:
            if node['id'] == next_id:
                next_label = node['label']
                break
        
        print(f"   Test: Say 'Yes' and it should go to '{next_label}'")
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
