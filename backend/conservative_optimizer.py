"""
Conservative Latency Optimizer - Preserves Transition Logic
Less aggressive optimization: 20-30% reduction vs 50-60%
Focuses on removing fluff while keeping core context
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import httpx

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"


async def get_grok_key():
    """Get user's Grok API key from api_keys collection"""
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    keys = await db.api_keys.find({"user_id": USER_ID}).to_list(length=50)
    
    for key_doc in keys:
        if key_doc.get('service_name') == 'grok' and key_doc.get('is_active', False):
            return key_doc.get('api_key')
    
    raise Exception("No active Grok API key found")


async def conservative_optimize(text: str, grok_key: str, optimization_type: str) -> str:
    """Conservative optimization - preserves more context"""
    
    if optimization_type == "node":
        system_msg = """You are an expert at conservatively optimizing voice agent prompts.

CRITICAL RULES:
1. **Preserve ALL context** that helps transitions evaluate correctly
2. **Keep ALL transition keywords** (income, employed, vehicle, capital, etc.)
3. **Maintain ALL qualification logic** 
4. Only remove:
   - Redundant filler words ("basically", "essentially", "actually")
   - Excessive examples (keep 1-2 key examples)
   - Verbose explanations (make concise but keep the point)
5. Target: 20-30% reduction MAX (not 50-60%)
6. **When in doubt, keep it** - transitions are more important than latency

OUTPUT: Return ONLY the optimized content, no explanations."""

        user_msg = f"""Conservatively optimize this node prompt (max 30% reduction):

NODE CONTENT:
{text}

Remember: Preserve transition keywords and qualification logic!"""

    else:  # system_prompt (already optimized in Iteration 1, skip)
        return text
    
    # Use Grok API
    async with httpx.AsyncClient(timeout=90.0) as client:
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
                "temperature": 0.1,  # Lower temperature for more conservative
                "max_tokens": 4000
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Grok API error: {response.status_code}")
            return text
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        # Validate reduction isn't too aggressive
        reduction_pct = (len(text) - len(optimized)) / len(text) * 100
        if reduction_pct > 35:
            print(f"  ⚠️ Reduction too aggressive ({reduction_pct:.0f}%), keeping more context")
            return text
        
        return optimized


async def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         CONSERVATIVE OPTIMIZER - Preserves Transition Logic                  ║
║         Target: 20-30% reduction (not 50-60%)                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Setup
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    print("🔑 Getting Grok API key...")
    grok_key = await get_grok_key()
    print("✅ Grok API key loaded")
    
    # Load agent
    print(f"\n📥 Loading agent...")
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        print("❌ Agent not found")
        return
    
    agent.pop('_id', None)
    print(f"✅ Loaded: {agent.get('name')}")
    
    # Analyze
    call_flow = agent.get('call_flow', [])
    print(f"\n📊 Call Flow Nodes: {len(call_flow)}")
    
    # Find only the slowest nodes from our test
    target_nodes = [
        "N_KB_Q&A_With_StrategicNarrative_V3_Adaptive",  # 2985ms avg
        "N200_Super_WorkAndIncomeBackground_V3_Adaptive",  # 2143ms avg
        "N201A_Employed_AskYearlyIncome_V8_Adaptive",  # 1201ms
    ]
    
    print(f"\n🎯 Targeting 3 slowest nodes for conservative optimization:")
    for node_name in target_nodes:
        print(f"   - {node_name}")
    
    changes = []
    total_reduction = 0
    nodes_optimized = 0
    
    print(f"\n📝 Optimizing nodes...")
    
    for node in call_flow:
        label = node.get('label', '')
        
        # Only optimize our target nodes
        if label not in target_nodes:
            continue
        
        content = node.get('data', {}).get('content', '')
        if len(content) < 500:
            continue
        
        print(f"\n   Optimizing: {label[:50]}... ({len(content):,} chars)")
        optimized_content = await conservative_optimize(content, grok_key, "node")
        
        if len(optimized_content) < len(content):
            reduction = len(content) - len(optimized_content)
            reduction_pct = (reduction / len(content)) * 100
            
            if reduction_pct > 35:
                print(f"      ⚠️ Skipping - too aggressive ({reduction_pct:.0f}%)")
                continue
            
            node['data']['content'] = optimized_content
            
            # Update in call_flow
            for idx, cf_node in enumerate(call_flow):
                if cf_node.get('id') == node.get('id'):
                    call_flow[idx] = node
                    break
            
            total_reduction += reduction
            nodes_optimized += 1
            changes.append(f"Node '{label[:40]}': {len(content):,} → {len(optimized_content):,} chars (-{reduction:,}, {reduction_pct:.0f}%)")
            print(f"      ✅ Reduced by {reduction:,} chars ({reduction_pct:.0f}%)")
        else:
            print(f"      ⚠️ No improvement")
    
    agent['call_flow'] = call_flow
    
    # Save if changes made
    if changes:
        print(f"\n💾 Saving conservatively optimized agent...")
        result = await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        
        if result.modified_count > 0:
            print(f"✅ Agent saved to MongoDB")
            
            # Log to file
            timestamp = datetime.now().isoformat()
            log_entry = f"""
## Iteration 3: Conservative Optimization (Preserves Transitions)
**Date:** {timestamp}
**Agent:** JK First Caller-copy-copy
**Target:** Reduce latency while maintaining 100% transition accuracy

### Changes Made:
"""
            for change in changes:
                log_entry += f"- {change}\n"
            
            log_entry += f"""
### Metrics:
- **Total Character Reduction:** {total_reduction:,} chars
- **Nodes Optimized:** {nodes_optimized}
- **Reduction Target:** 20-30% per node (conservative)

### Next Steps:
1. Test with real_latency_tester.py
2. **Validate ALL transitions match baseline**
3. Compare latency improvement
4. Only accept if transitions are 100% correct

### Status: ✅ Complete - Ready for Validation Testing

---

"""
            
            with open('/app/LATENCY_ITERATIONS.md', 'a') as f:
                f.write(log_entry)
            
            print(f"✅ Logged to LATENCY_ITERATIONS.md")
        else:
            print(f"⚠️ No changes saved")
    else:
        print(f"\n⚠️ No optimizations applied")
    
    print(f"\n{'='*80}")
    print(f"✅ CONSERVATIVE OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
    print(f"\n📊 Summary:")
    print(f"   Total Character Reduction: {total_reduction:,} chars")
    print(f"   Nodes Optimized: {nodes_optimized}")
    print(f"   Changes Applied: {len(changes)}")
    print(f"\n⚠️  CRITICAL: Must validate transitions before declaring success!")


if __name__ == "__main__":
    asyncio.run(main())
