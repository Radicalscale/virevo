"""
Iteration 5 - Building on Success
Iteration 4 worked! Now optimize MORE nodes while still protecting the confused ones
"""
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import httpx

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

# Add more nodes to optimize (still protecting the two that get confused)
TARGET_NODES = [
    "1763161961589",  # 5944ms - try again with better prompt
    "1763163400676",  # 2405ms - try again
    "1763161849799",  # Has SSML breaks, optimize
    "1763162097194",  # Optimize
    "1763162101860",  # Optimize
    "1763164236511",  # Optimize
]

# STILL DO NOT TOUCH
PROTECTED_NODES = [
    "1763175810279",
    "1763206946898",
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


async def optimize_node(content: str, grok_key: str) -> str:
    system_msg = """Optimize voice agent node content.

PRESERVE 100%:
- All transition logic
- All keywords
- All variable names
- All if/then conditions

OPTIMIZE:
- Remove redundant examples
- Shorten verbose explanations
- Use bullets instead of paragraphs

TARGET: 20% reduction

OUTPUT: Only optimized content."""

    user_msg = f"""Optimize (20% reduction target):

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
            return content
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        reduction_pct = (len(content) - len(optimized)) / len(content) * 100
        if reduction_pct > 30 or reduction_pct < 10:
            return content
        
        return optimized


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ITERATION 5 - Building on Iter 4 Success                           ║
║           Optimize MORE nodes, keep protecting the confused pair             ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    grok_key = await get_grok_key()
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    agent.pop('_id', None)
    
    with open('/app/agent_backup_iter5.json', 'w') as f:
        json.dump(agent, f, indent=2, default=str)
    print("✅ Backup saved\n")
    
    call_flow = agent.get('call_flow', [])
    changes = []
    
    print(f"Targeting {len(TARGET_NODES)} nodes\n")
    
    for node in call_flow:
        node_id = node.get('id', '')
        
        if node_id in PROTECTED_NODES:
            continue
        
        if node_id not in TARGET_NODES:
            continue
        
        content = node.get('data', {}).get('content', '')
        
        if len(content) < 300:
            continue
        
        print(f"🎯 {node_id}: {len(content)} chars", end=" ")
        
        optimized = await optimize_node(content, grok_key)
        
        if len(optimized) < len(content):
            reduction = len(content) - len(optimized)
            reduction_pct = (reduction / len(content)) * 100
            
            node['data']['content'] = optimized
            changes.append(f"{node_id}: -{reduction_pct:.1f}%")
            print(f"→ {len(optimized)} (-{reduction_pct:.1f}%) ✅")
        else:
            print(f"→ no change")
    
    agent['call_flow'] = call_flow
    
    if changes:
        print(f"\n💾 Saving {len(changes)} optimizations...")
        await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        print("✅ Saved")
        
        with open('/app/OPTIMIZATION_LOG.md', 'a') as f:
            f.write(f"""
## Iteration 5: Expanding Optimization
**Status:** COMPLETE

### Changes: {len(changes)}
""")
            for change in changes:
                f.write(f"- {change}\n")
            f.write("\n---\n\n")
    else:
        print("\n⚠️ No changes")
    
    print(f"\nITERATION 5 DONE: {len(changes)} nodes optimized")


if __name__ == "__main__":
    asyncio.run(main())
