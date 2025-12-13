#!/usr/bin/env python3
"""
Test script to verify transition optimizer preserves logic
Tests with JK First Caller-copy-copy agent
"""

import asyncio
import httpx
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append('/app/backend')
from calling_service import CallSession

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')

async def find_agent_by_name(db, name):
    """Find agent by name"""
    agent = await db.agents.find_one({"name": name})
    return agent

async def optimize_transition(grok_api_key, condition):
    """Call the optimizer API to optimize a transition"""
    optimization_prompt = f"""You are an expert at optimizing transition conditions for real-time voice agents. Your goal is to make transition evaluation FAST while preserving all logic.

**TRANSITION OPTIMIZATION PRINCIPLES:**

**1. Speed is Critical**
- Transition conditions are evaluated on EVERY user message during real-time conversations
- Verbose conditions add 100-300ms latency per evaluation
- Reduce to bare essentials while keeping all logic intact

**2. Structure for Fast Parsing**
- Use SHORT declarative statements, not full sentences
- Lead with the MAIN condition, then qualifiers
- Use pipes (|) for OR conditions: "agrees | consents | positive response"
- Use parentheses for examples: "(yes/sure/okay)"
- Use colons for conditional logic: "IF objection: address first, THEN transition"

**3. Keep All Logic Intact**
- Do NOT remove any conditions or rules
- Preserve all examples and edge cases
- Maintain the decision tree structure
- Keep all "if-then" logic

**4. Formatting for Speed**
- Start with trigger condition in CAPS if critical
- Group similar conditions with pipes, NO SPACES: "agrees | consents" → "agrees|consents"
- Use minimal words: "User agrees" → "Agrees", "question" → "Q"
- Avoid articles (the, a, an): "If they add question" → "IF Q"
- Use abbreviations where clear: "question" → "Q", "objection" → "obj", "address first then transition" → "address→transition"
- Remove filler words: "directly without context handling" → "direct"

**5. Examples of Optimization**

BEFORE (verbose):
"User agrees (yes/sure/okay/agreeing to hear more/consenting to call/asking what this is about). If they add objection/question/statement: address it first, then transition. Basic acknowledgments (go ahead/sure): proceed directly without context handling."

AFTER (optimized):
"Agrees|consents (yes/sure/okay/what's this). IF objection/Q/statement: address→transition. Basic acks (go ahead/sure): proceed direct."

BEFORE:
"The user is asking a question about pricing or wants to know how much it costs or is inquiring about the investment required"

AFTER:
"Price inquiry | cost question (how much/pricing/investment)"

BEFORE:
"If the user expresses any form of objection such as skepticism, doubt, concern about legitimacy, or questions whether this is a scam"

AFTER:
"Objection: skepticism | doubt | legitimacy concern | scam question"

**ORIGINAL TRANSITION CONDITION:**
```
{condition}
```

**YOUR TASK:**
1. Analyze the transition condition's logic and all edge cases
2. Restructure for fastest possible LLM evaluation (aim for 50-70% reduction)
3. Use pipes (|), colons (:), and parentheses () for compact structure
4. Preserve ALL conditions, examples, and if-then logic
5. Lead with main trigger, then qualifiers
6. Output ONLY the optimized condition - no explanations or context

**OUTPUT FORMAT:**
Return just the optimized transition condition text, ready to paste directly into the transition field."""

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
                        "content": "You are an expert at optimizing transition conditions for real-time voice agents. You reduce verbosity while preserving all logic, making evaluations 2-3x faster."
                    },
                    {"role": "user", "content": optimization_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 500
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Grok API error: {response.status_code} - {response.text}")
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        # Remove markdown code blocks if present
        if optimized.startswith('```'):
            lines = optimized.split('\n')
            optimized = '\n'.join(lines[1:-1]).strip()
        
        return optimized

async def test_transition(db, agent, session, user_message, expected_node):
    """Test if a message triggers the expected transition"""
    result = await session.process_user_input(user_message)
    
    current_node = session.current_node_id
    
    # Get node label
    node_label = "Unknown"
    if current_node:
        agent_flow = agent.get('call_flow', [])
        for node in agent_flow:
            if node.get('id') == current_node:
                node_label = node.get('label', 'Unnamed Node')
                break
    
    success = current_node == expected_node
    
    return {
        'success': success,
        'expected_node': expected_node,
        'actual_node': current_node,
        'node_label': node_label,
        'response': result.get('text', ''),
    }

async def main():
    print("=" * 80)
    print("TRANSITION OPTIMIZER LOGIC PRESERVATION TEST")
    print("=" * 80)
    print()
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get Grok API key
    api_keys_collection = db['api_keys']
    grok_key_doc = await api_keys_collection.find_one({"service_name": "grok"})
    
    if not grok_key_doc:
        print("❌ Grok API key not found")
        return
    
    grok_api_key = grok_key_doc.get('api_key')
    print(f"✅ Found Grok API key")
    print()
    
    # Find the agent
    agent_name = "JK First Caller-copy-copy"
    print(f"🔍 Looking for agent: {agent_name}")
    agent = await find_agent_by_name(db, agent_name)
    
    if not agent:
        print(f"❌ Agent '{agent_name}' not found")
        print("\nSearching for similar agents...")
        agents = await db.agents.find({"name": {"$regex": "JK First Caller", "$options": "i"}}).to_list(length=10)
        if agents:
            print("\nFound these agents:")
            for a in agents:
                print(f"  - {a.get('name')}")
        return
    
    print(f"✅ Found agent: {agent.get('name')}")
    print(f"   Agent ID: {agent.get('id')}")
    print()
    
    # Get call flow
    call_flow = agent.get('call_flow', [])
    if not call_flow:
        print("❌ No call flow found")
        return
    
    print(f"📊 Call flow has {len(call_flow)} nodes")
    print()
    
    # Find nodes with transitions (check data.transitions)
    nodes_with_transitions = []
    for node in call_flow:
        transitions = node.get('data', {}).get('transitions', [])
        if transitions and len(transitions) > 0:
            # Filter out empty transitions
            valid_transitions = [t for t in transitions if t.get('condition', '').strip()]
            if valid_transitions:
                nodes_with_transitions.append({
                    'node': node,
                    'transitions': valid_transitions
                })
    
    print(f"🔗 Found {len(nodes_with_transitions)} nodes with transitions")
    print()
    
    if not nodes_with_transitions:
        print("❌ No nodes with valid transitions found")
        return
    
    # Select 2 nodes to test
    test_nodes = nodes_with_transitions[:2]
    
    test_cases = []
    
    for idx, node_data in enumerate(test_nodes, 1):
        node = node_data['node']
        transitions = node_data['transitions']
        
        print(f"\n{'='*80}")
        print(f"TEST CASE {idx}: {node.get('label', 'Unnamed')}")
        print(f"{'='*80}")
        print(f"Node ID: {node.get('id')}")
        print(f"Node Type: {node.get('type')}")
        print(f"Number of transitions: {len(transitions)}")
        print()
        
        # Test the first transition
        if transitions:
            trans = transitions[0]
            original_condition = trans.get('condition', '')
            next_node_id = trans.get('nextNode', '')
            
            if not original_condition or not next_node_id:
                print("⚠️  Skipping - missing condition or next node")
                continue
            
            # Find next node label
            next_node_label = "Unknown"
            for n in call_flow:
                if n.get('id') == next_node_id:
                    next_node_label = n.get('label', 'Unnamed Node')
                    break
            
            print(f"📝 Original Transition Condition ({len(original_condition)} chars):")
            print(f"   {original_condition}")
            print()
            print(f"➡️  Next Node: {next_node_label} ({next_node_id})")
            print()
            
            # Optimize the condition
            print("🔧 Optimizing transition condition...")
            try:
                optimized_condition = await optimize_transition(grok_api_key, original_condition)
                print(f"✅ Optimized Condition ({len(optimized_condition)} chars):")
                print(f"   {optimized_condition}")
                reduction = ((len(original_condition) - len(optimized_condition)) / len(original_condition)) * 100
                print(f"   Reduction: {reduction:.1f}%")
                print()
                
                test_cases.append({
                    'node_id': node.get('id'),
                    'node_label': node.get('label'),
                    'original_condition': original_condition,
                    'optimized_condition': optimized_condition,
                    'next_node_id': next_node_id,
                    'next_node_label': next_node_label
                })
                
            except Exception as e:
                print(f"❌ Error optimizing: {str(e)}")
                continue
    
    if not test_cases:
        print("\n❌ No test cases to run")
        return
    
    # Now test both original and optimized conditions
    print(f"\n{'='*80}")
    print("TESTING TRANSITION LOGIC PRESERVATION")
    print(f"{'='*80}\n")
    
    user_id = agent.get('user_id')
    
    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"RUNNING TEST {idx}: {test_case['node_label']}")
        print(f"{'='*80}\n")
        
        # Test with ORIGINAL condition
        print("🔵 Testing with ORIGINAL condition...")
        print(f"   Condition: {test_case['original_condition'][:80]}...")
        
        # Create a session for testing original
        test_call_id_orig = f"test_orig_{idx}"
        session_orig = CallSession(
            call_id=test_call_id_orig,
            agent_id=agent.get('id'),
            agent_config=agent,
            db=db,
            user_id=user_id,
            knowledge_base=""
        )
        
        # Set current node to the test node
        session_orig.current_node_id = test_case['node_id']
        
        # Create test message based on condition
        # Parse condition for keywords
        condition_lower = test_case['original_condition'].lower()
        if 'yes' in condition_lower or 'sure' in condition_lower or 'agree' in condition_lower:
            test_message = "Yes, sure"
        elif 'price' in condition_lower or 'cost' in condition_lower:
            test_message = "How much does it cost?"
        elif 'question' in condition_lower:
            test_message = "I have a question about this"
        else:
            # Use first word in parentheses if available
            import re
            examples = re.findall(r'\((.*?)\)', test_case['original_condition'])
            if examples:
                first_example = examples[0].split('/')[0].strip()
                test_message = first_example
            else:
                test_message = "Okay"
        
        print(f"   Test message: \"{test_message}\"")
        print(f"   Expected next node: {test_case['next_node_label']}")
        
        result_orig = await test_transition(
            db, agent, session_orig, test_message, test_case['next_node_id']
        )
        
        if result_orig['success']:
            print(f"   ✅ SUCCESS - Transitioned to: {result_orig['node_label']}")
        else:
            print(f"   ❌ FAILED - Went to: {result_orig['node_label']} (expected: {test_case['next_node_label']})")
        print()
        
        # Now update agent with OPTIMIZED condition and test again
        print("🟢 Testing with OPTIMIZED condition...")
        print(f"   Condition: {test_case['optimized_condition'][:80]}...")
        
        # Update the agent config with optimized condition
        import copy
        agent_optimized = copy.deepcopy(agent)
        for node in agent_optimized['call_flow']:
            if node.get('id') == test_case['node_id']:
                if 'data' in node and 'transitions' in node['data']:
                    if node['data']['transitions']:
                        node['data']['transitions'][0]['condition'] = test_case['optimized_condition']
        
        # Create session with optimized config
        test_call_id_opt = f"test_opt_{idx}"
        session_opt = CallSession(
            call_id=test_call_id_opt,
            agent_id=agent.get('id'),
            agent_config=agent_optimized,
            db=db,
            user_id=user_id,
            knowledge_base=""
        )
        
        session_opt.current_node_id = test_case['node_id']
        
        print(f"   Test message: \"{test_message}\"")
        print(f"   Expected next node: {test_case['next_node_label']}")
        
        result_opt = await test_transition(
            db, agent_optimized, session_opt, test_message, test_case['next_node_id']
        )
        
        if result_opt['success']:
            print(f"   ✅ SUCCESS - Transitioned to: {result_opt['node_label']}")
        else:
            print(f"   ❌ FAILED - Went to: {result_opt['node_label']} (expected: {test_case['next_node_label']})")
        print()
        
        # Compare results
        if result_orig['success'] and result_opt['success']:
            print("✅ LOGIC PRESERVED: Both original and optimized work correctly!")
        elif result_orig['success'] and not result_opt['success']:
            print("❌ LOGIC BROKEN: Optimized condition doesn't work!")
        elif not result_orig['success'] and result_opt['success']:
            print("⚠️  IMPROVED: Optimized works but original didn't!")
        else:
            print("⚠️  BOTH FAILED: Neither condition worked (might be test message issue)")
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE")
    print(f"{'='*80}\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
