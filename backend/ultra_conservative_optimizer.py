"""
Ultra-Conservative Optimizer - 10-15% reduction MAX
Only removes obvious fluff, preserves all context
"""
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import httpx

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

# Target only the highest impact nodes
SLOW_NODE_IDS = [
    "1763161961589",  # 5944ms avg
    "1763175810279",  # 2782ms avg  
]


async def get_grok_key():
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    keys = await db.api_keys.find({"user_id": USER_ID}).to_list(length=50)
    
    for key_doc in keys:
        if key_doc.get('service_name') == 'grok' and key_doc.get('is_active', False):
            return key_doc.get('api_key')
    
    raise Exception("No active Grok API key found")


async def ultra_conservative_optimize(content: str, grok_key: str) -> str:
    """Ultra-conservative: only 10-15% reduction"""
    
    system_msg = """You are optimizing voice agent prompts with EXTREME CAUTION.

ABSOLUTE RULES:
1. **Preserve 100% of transition logic and keywords**
2. **Keep 100% of qualification criteria**
3. **Maintain 100% of variable names and KB syntax**
4. **Preserve speaking style and tone**

ONLY REMOVE:
- Redundant filler words: "basically", "essentially", "actually", "really"
- Extra spaces and line breaks
- Duplicate phrases within the same paragraph
- One or two overly verbose explanations (if truly redundant)

TARGET: **10-15% reduction MAXIMUM** (not more!)

If uncertain about anything, KEEP IT.

OUTPUT: Only the optimized content."""

    user_msg = f"""Ultra-conservatively optimize (MAX 15% reduction):

{content}

Remember: Preserve ALL transition logic!"""

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {grok_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-2-1212",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "temperature": 0.05,  # Very low for consistency
                "max_tokens": 4000
            }
        )
        
        if response.status_code != 200:
            return content
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        # Strict safety check: 10-18% reduction only
        reduction_pct = (len(content) - len(optimized)) / len(content) * 100
        if reduction_pct > 18 or reduction_pct < 5:
            print(f"      ⚠️ Reduction {reduction_pct:.1f}% outside 5-18% range, keeping original")
            return content
        
        return optimized


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║         ULTRA-CONSERVATIVE OPTIMIZER - 10-15% MAX Reduction                  ║
║         Preserves all context, only removes obvious fluff                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    print("🔑 Getting Grok API key...")
    grok_key = await get_grok_key()
    print("✅ Loaded\n")
    
    print("📥 Loading agent...")
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        print("❌ Agent not found")
        return
    
    agent.pop('_id', None)
    
    # Backup
    with open('/app/agent_backup_iteration2.json', 'w') as f:
        json.dump(agent, f, indent=2, default=str)
    print("✅ Backup: /app/agent_backup_iteration2.json\n")
    
    print(f"Agent: {agent.get('name')}")
    print(f"Nodes: {len(agent.get('call_flow', []))}\n")
    
    call_flow = agent.get('call_flow', [])
    changes_log = []
    nodes_optimized = 0
    
    print("="*80)
    print("Optimizing Top 2 Slowest Nodes (Ultra-Conservative)")
    print("="*80)
    
    for node in call_flow:
        node_id = node.get('id', '')
        
        if node_id not in SLOW_NODE_IDS:
            continue
        
        label = node.get('label', 'Unknown')
        content = node.get('data', {}).get('content', '')
        
        if len(content) < 500:
            continue
        
        print(f"\n🎯 {node_id}")
        print(f"   {label[:60]}...")
        print(f"   Current: {len(content):,} chars")
        print(f"   🔄 Optimizing (10-15% target)...")
        
        optimized = await ultra_conservative_optimize(content, grok_key)
        
        if len(optimized) < len(content):
            reduction = len(content) - len(optimized)
            reduction_pct = (reduction / len(content)) * 100
            
            node['data']['content'] = optimized
            nodes_optimized += 1
            
            changes_log.append(f"{node_id}: {len(content):,} → {len(optimized):,} (-{reduction_pct:.1f}%)")
            print(f"   ✅ {len(content):,} → {len(optimized):,} (-{reduction_pct:.1f}%)")
        else:
            print(f"   ⚠️ No improvement")
    
    agent['call_flow'] = call_flow
    
    print("\n" + "="*80)
    print("Saving Changes")
    print("="*80)
    
    if changes_log:
        print(f"\n📊 Changes: {len(changes_log)}")
        for change in changes_log:
            print(f"   - {change}")
        
        print(f"\n💾 Saving...")
        result = await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        
        if result.modified_count > 0:
            print(f"✅ Saved successfully")
            
            # Log
            with open('/app/OPTIMIZATION_LOG.md', 'a') as f:
                f.write(f"""
## Iteration 2: Ultra-Conservative Optimization (10-15% max)
**Timestamp:** {datetime.now().isoformat()}
**Status:** COMPLETE - Ready for Testing

### Changes:
""")
                for change in changes_log:
                    f.write(f"- {change}\n")
                
                f.write(f"""
### Strategy:
- Only top 2 slowest nodes targeted
- 10-15% reduction maximum per node
- Preserves all transition context
- Only removes obvious fluff

### Expected Impact:
- Lower risk of transition failures
- Modest latency improvement (100-200ms)
- May need additional iterations

### Next: Test + Validate Transitions

---

""")
            print(f"✅ Logged")
        else:
            print(f"⚠️ No changes")
    else:
        print(f"\n⚠️ No optimizations applied")
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETE")
    print(f"{'='*80}")
    print(f"""
Changes: {len(changes_log)}
Nodes: {nodes_optimized}

Next: Test and validate transitions
""")


if __name__ == "__main__":
    asyncio.run(main())
