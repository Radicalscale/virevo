"""
Transition-Focused Optimizer
Optimizes transition conditions (not node content) to reduce evaluation time
This should preserve conversation flow since we're not changing prompts
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import httpx

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"


async def get_grok_key():
    """Get user's Grok API key"""
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    keys = await db.api_keys.find({"user_id": USER_ID}).to_list(length=50)
    
    for key_doc in keys:
        if key_doc.get('service_name') == 'grok' and key_doc.get('is_active', False):
            return key_doc.get('api_key')
    
    raise Exception("No active Grok API key found")


async def optimize_transition(condition: str, grok_key: str) -> str:
    """Optimize a transition condition for faster evaluation"""
    
    system_msg = """You are an expert at optimizing transition logic for instant evaluation.

RULES:
1. Convert verbose conditions into concise boolean logic
2. Use pattern matching: "yes|yeah|yep" instead of multiple OR conditions
3. Remove explanatory text - just the logic
4. Use keywords efficiently
5. Preserve EXACT matching intent

OUTPUT: Return ONLY the optimized condition, no explanations."""

    user_msg = f"""Optimize this transition condition:

{condition}

Make it faster to evaluate while preserving exact logic."""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {grok_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-4-0709",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
        )
        
        if response.status_code != 200:
            return condition
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        return optimized


async def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              TRANSITION OPTIMIZER - Faster Logic Evaluation                  ║
║              Optimizes conditions, not prompts                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Setup
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    print("🔑 Getting Grok API key...")
    grok_key = await get_grok_key()
    
    # Load agent
    print(f"\n📥 Loading agent...")
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        print("❌ Agent not found")
        return
    
    agent.pop('_id', None)
    call_flow = agent.get('call_flow', [])
    
    # Find all transitions with conditions
    transitions_to_optimize = []
    for node in call_flow:
        node_label = node.get('label', '')
        transitions = node.get('data', {}).get('transitions', [])
        
        for trans in transitions:
            condition = trans.get('condition', '')
            if len(condition) > 50:  # Only optimize substantial conditions
                transitions_to_optimize.append({
                    'node': node,
                    'node_label': node_label,
                    'transition': trans,
                    'condition_length': len(condition)
                })
    
    transitions_to_optimize.sort(key=lambda x: x['condition_length'], reverse=True)
    
    print(f"\n📊 Found {len(transitions_to_optimize)} transitions to optimize")
    print(f"   Optimizing top 10 longest transitions...\n")
    
    changes = []
    total_reduction = 0
    
    for i, trans_info in enumerate(transitions_to_optimize[:10]):
        node = trans_info['node']
        transition = trans_info['transition']
        original_condition = transition.get('condition', '')
        
        print(f"   {i+1}. Node: {trans_info['node_label'][:40]}...")
        print(f"      Original: {len(original_condition)} chars")
        
        optimized_condition = await optimize_transition(original_condition, grok_key)
        
        if len(optimized_condition) < len(original_condition):
            reduction = len(original_condition) - len(optimized_condition)
            reduction_pct = (reduction / len(original_condition)) * 100
            
            transition['condition'] = optimized_condition
            
            # Update in node
            node_transitions = node.get('data', {}).get('transitions', [])
            for idx, t in enumerate(node_transitions):
                if t.get('id') == transition.get('id'):
                    node_transitions[idx] = transition
                    break
            
            node['data']['transitions'] = node_transitions
            
            # Update in call_flow
            for idx, cf_node in enumerate(call_flow):
                if cf_node.get('id') == node.get('id'):
                    call_flow[idx] = node
                    break
            
            total_reduction += reduction
            changes.append(f"Transition in '{trans_info['node_label'][:30]}': {len(original_condition)} → {len(optimized_condition)} chars (-{reduction})")
            print(f"      ✅ Optimized: {len(optimized_condition)} chars (-{reduction}, {reduction_pct:.0f}%)\n")
        else:
            print(f"      ⚠️ No improvement\n")
    
    agent['call_flow'] = call_flow
    
    # Save
    if changes:
        print(f"💾 Saving...")
        result = await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        
        if result.modified_count > 0:
            print(f"✅ Saved to MongoDB")
            
            # Log
            timestamp = datetime.now().isoformat()
            log_entry = f"""
## Iteration 4: Transition Logic Optimization
**Date:** {timestamp}
**Strategy:** Optimize transition conditions (not node content)
**Rationale:** Node optimization broke transitions, so optimize the transitions themselves

### Changes Made:
"""
            for change in changes:
                log_entry += f"- {change}\n"
            
            log_entry += f"""
### Metrics:
- **Total Reduction:** {total_reduction} chars
- **Transitions Optimized:** {len(changes)}

### Expected Impact:
- Faster transition evaluation (less LLM processing)
- Should NOT break flow (node prompts unchanged)
- More conservative approach than node optimization

### Next Steps:
1. Test with real_latency_tester.py
2. Validate ALL transitions still work
3. Measure latency improvement

### Status: ✅ Complete - Ready for Testing

---

"""
            
            with open('/app/LATENCY_ITERATIONS.md', 'a') as f:
                f.write(log_entry)
            
            print(f"✅ Logged")
    
    print(f"\n{'='*80}")
    print(f"✅ TRANSITION OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
    print(f"\n📊 Summary:")
    print(f"   Transitions Optimized: {len(changes)}")
    print(f"   Total Reduction: {total_reduction} chars")


if __name__ == "__main__":
    asyncio.run(main())
