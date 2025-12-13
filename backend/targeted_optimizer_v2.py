"""
Targeted Optimizer V2 - Learning from Iteration 1
Keep nodes 1763175810279 and 1763206946898 UN-optimized (they got confused)
Optimize the other slow nodes more carefully
"""
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import httpx

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

# Nodes to optimize (EXCLUDING the ones that got confused)
TARGET_NODES = [
    "1763159750250",  # 1318ms avg
    "1763161961589",  # 5944ms avg - but be VERY careful
    "1763163400676",  # 2405ms avg
]

# DO NOT TOUCH these - they need to stay distinct
PROTECTED_NODES = [
    "1763175810279",  # Got confused with next one
    "1763206946898",  # Got confused with previous one
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


async def smart_optimize(content: str, grok_key: str, node_info: str) -> str:
    """Optimize with focus on preserving transition logic"""
    
    system_msg = """You are optimizing voice agent node prompts.

ABSOLUTE PRIORITIES:
1. **Keep ALL transition decision logic intact**
2. **Preserve ALL keywords that distinguish this node from others**
3. **Maintain ALL conditions and if/then statements**
4. **Keep ALL variable names and KB syntax**

WHAT TO OPTIMIZE:
- Remove redundant examples (keep 1 best example)
- Shorten verbose explanations (but keep the core meaning)
- Convert long paragraphs to bullets
- Remove filler words in descriptions (not in speech)

TARGET: 20-25% reduction

CRITICAL: If the content has transition logic or node selection criteria, be EXTRA careful to preserve exact phrasing.

OUTPUT: Only optimized content."""

    user_msg = f"""Optimize this node (20-25% reduction, preserve transition logic):

{node_info}

CONTENT:
{content}"""

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
                "temperature": 0.1,
                "max_tokens": 4000
            }
        )
        
        if response.status_code != 200:
            print(f"      ❌ API error: {response.status_code}")
            return content
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        # Safety: 15-30% reduction
        reduction_pct = (len(content) - len(optimized)) / len(content) * 100
        if reduction_pct > 30 or reduction_pct < 15:
            print(f"      ⚠️ Reduction {reduction_pct:.1f}% outside 15-30% range, keeping original")
            return content
        
        return optimized


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║     TARGETED OPTIMIZER V2 - Learning from Iteration 1 Failure               ║
║     Excludes nodes that got confused, optimizes others carefully             ║
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
    with open('/app/agent_backup_v2.json', 'w') as f:
        json.dump(agent, f, indent=2, default=str)
    print("✅ Backup: /app/agent_backup_v2.json\n")
    
    print(f"Agent: {agent.get('name')}\n")
    
    print("="*80)
    print(f"Optimizing {len(TARGET_NODES)} nodes")
    print(f"PROTECTING {len(PROTECTED_NODES)} nodes from optimization")
    print("="*80)
    print()
    
    for pn in PROTECTED_NODES:
        print(f"  🛡️  PROTECTED: {pn}")
    print()
    
    call_flow = agent.get('call_flow', [])
    changes_log = []
    nodes_optimized = 0
    
    for node in call_flow:
        node_id = node.get('id', '')
        
        # Skip protected nodes
        if node_id in PROTECTED_NODES:
            continue
        
        # Only optimize target nodes
        if node_id not in TARGET_NODES:
            continue
        
        label = node.get('label', 'Unknown')
        content = node.get('data', {}).get('content', '')
        
        if len(content) < 500:
            print(f"\n⏩ {node_id}: too short ({len(content)} chars)")
            continue
        
        print(f"\n🎯 {node_id}")
        print(f"   {label[:60]}...")
        print(f"   Current: {len(content):,} chars")
        print(f"   🔄 Optimizing...")
        
        node_info = f"Node ID: {node_id}\nLabel: {label}\nThis node must remain distinct from nodes {PROTECTED_NODES}"
        optimized = await smart_optimize(content, grok_key, node_info)
        
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
    print("Saving")
    print("="*80)
    print()
    
    if changes_log:
        print(f"📊 Changes: {len(changes_log)}")
        for change in changes_log:
            print(f"   - {change}")
        
        print(f"\n💾 Saving...")
        result = await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        
        if result.modified_count > 0:
            print(f"✅ Saved")
            
            with open('/app/OPTIMIZATION_LOG.md', 'a') as f:
                f.write(f"""
## Iteration 4: Targeted Optimization V2 (Learning from Failure)
**Timestamp:** {datetime.now().isoformat()}
**Status:** COMPLETE - Ready for Testing

### Key Changes from Iteration 1:
- EXCLUDED nodes 1763175810279 & 1763206946898 (they got confused)
- Only optimized 3 other slow nodes
- More careful preservation of transition logic

### Changes:
""")
                for change in changes_log:
                    f.write(f"- {change}\n")
                
                f.write(f"""
### Nodes Optimized: {nodes_optimized}
### Protected: {len(PROTECTED_NODES)} nodes kept original

### Next: Test + Validate Transitions

---

""")
            print(f"✅ Logged")
    else:
        print(f"⚠️ No changes")
    
    print(f"\n{'='*80}")
    print(f"ITERATION 4 COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
