"""
Smart Optimizer - Targets actual slow nodes from test results
Uses conservative 25-30% reduction to preserve transition logic
"""
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import httpx

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

# Slow nodes identified from baseline test
SLOW_NODE_IDS = [
    "1763161961589",  # 5944ms avg - CRITICAL
    "1763175810279",  # 2782ms avg
    "1763163400676",  # 2405ms avg
    "1763159750250",  # 1318ms avg
    "1763206946898",  # 1901ms avg
]


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


async def optimize_node_content(content: str, grok_key: str, node_info: str) -> str:
    """Optimize node content using Grok"""
    
    system_msg = """You are an expert at conservatively optimizing voice agent node prompts.

CRITICAL RULES FOR VOICE AGENTS:
1. **Preserve ALL transition logic keywords** - these determine conversation flow
2. **Keep ALL qualification criteria** - income, employment, vehicle, capital, etc.
3. **Maintain the speaking style** - conversational, natural voice patterns
4. **Preserve ALL variable names** - {{customer_name}}, {{income}}, etc.
5. **Keep KB reference syntax** - queries that fetch information

WHAT TO OPTIMIZE:
- Convert paragraphs to concise bullets
- Remove redundant examples (keep 1-2 best)
- Eliminate verbose explanations ("because", "in order to", "the reason is")
- Shorten instructions while keeping meaning
- Remove filler words ("basically", "essentially", "actually")

TARGET: 25-30% reduction MAX
PRIORITY: Transition accuracy > latency

OUTPUT: Only the optimized content, no explanations or meta-commentary."""

    user_msg = f"""Conservatively optimize this voice agent node (max 30% reduction):

{node_info}

CONTENT:
{content}

Return ONLY the optimized content."""

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
            print(f"      ❌ Grok API error: {response.status_code} - {response.text}")
            return content
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        # Safety check: Don't allow over 35% reduction
        reduction_pct = (len(content) - len(optimized)) / len(content) * 100
        if reduction_pct > 35:
            print(f"      ⚠️ Reduction too aggressive ({reduction_pct:.0f}%), using original")
            return content
        
        return optimized


async def optimize_system_prompt(prompt: str, grok_key: str) -> str:
    """Optimize system prompt"""
    
    system_msg = """You are an expert at optimizing AI system prompts.

RULES:
1. Preserve ALL behavior definitions
2. Keep ALL variable names and KB syntax
3. Maintain conversation flow instructions
4. Remove redundant examples and verbose explanations
5. Target 25% reduction

OUTPUT: Only optimized prompt, no explanations."""

    user_msg = f"""Optimize this system prompt (25% reduction target):

{prompt}"""

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
                "max_tokens": 6000
            }
        )
        
        if response.status_code != 200:
            print(f"      ❌ Grok API error: {response.status_code}")
            return prompt
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        reduction_pct = (len(prompt) - len(optimized)) / len(prompt) * 100
        if reduction_pct > 35 or reduction_pct < 15:
            print(f"      ⚠️ Reduction outside range ({reduction_pct:.0f}%), using original")
            return prompt
        
        return optimized


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              SMART OPTIMIZER - Data-Driven Node Targeting                    ║
║              Targets actual slow nodes from baseline test                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Setup
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    print("🔑 Getting Grok API key...")
    grok_key = await get_grok_key()
    print("✅ Grok API key loaded\n")
    
    # Load agent
    print("📥 Loading agent...")
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        print("❌ Agent not found")
        return
    
    agent.pop('_id', None)
    
    # Save backup
    with open('/app/agent_backup_pre_optimization.json', 'w') as f:
        json.dump(agent, f, indent=2, default=str)
    print("✅ Backup saved to /app/agent_backup_pre_optimization.json\n")
    
    print(f"✅ Agent: {agent.get('name')}")
    print(f"   System Prompt: {len(agent.get('system_prompt', '')):,} chars")
    print(f"   Nodes: {len(agent.get('call_flow', []))}\n")
    
    changes_log = []
    
    # STEP 1: Optimize System Prompt
    print("=" * 80)
    print("STEP 1: Optimizing System Prompt")
    print("=" * 80)
    
    system_prompt = agent.get('system_prompt', '')
    if len(system_prompt) > 5000:
        print(f"Current: {len(system_prompt):,} chars")
        print("🔄 Optimizing...")
        
        optimized_prompt = await optimize_system_prompt(system_prompt, grok_key)
        
        if len(optimized_prompt) < len(system_prompt):
            reduction = len(system_prompt) - len(optimized_prompt)
            reduction_pct = (reduction / len(system_prompt)) * 100
            
            agent['system_prompt'] = optimized_prompt
            changes_log.append(f"System Prompt: {len(system_prompt):,} → {len(optimized_prompt):,} chars (-{reduction:,}, -{reduction_pct:.1f}%)")
            print(f"✅ Reduced: {len(system_prompt):,} → {len(optimized_prompt):,} chars (-{reduction_pct:.1f}%)\n")
        else:
            print("⚠️ No improvement\n")
    else:
        print("⚠️ System prompt already optimized\n")
    
    # STEP 2: Optimize Slow Nodes
    print("=" * 80)
    print("STEP 2: Optimizing Top 5 Slowest Nodes")
    print("=" * 80)
    
    call_flow = agent.get('call_flow', [])
    nodes_optimized = 0
    total_char_reduction = 0
    
    for node in call_flow:
        node_id = node.get('id', '')
        
        # Only optimize our identified slow nodes
        if node_id not in SLOW_NODE_IDS:
            continue
        
        label = node.get('label', 'Unknown')
        content = node.get('data', {}).get('content', '')
        
        if len(content) < 200:
            print(f"\n⏩ Skipping {node_id} ({label[:40]}...) - too short ({len(content)} chars)")
            continue
        
        print(f"\n🎯 Node {node_id}")
        print(f"   Label: {label[:60]}...")
        print(f"   Current: {len(content):,} chars")
        print(f"   🔄 Optimizing...")
        
        node_info = f"Node ID: {node_id}\nLabel: {label}\nCurrent Length: {len(content)} chars"
        optimized_content = await optimize_node_content(content, grok_key, node_info)
        
        if len(optimized_content) < len(content):
            reduction = len(content) - len(optimized_content)
            reduction_pct = (reduction / len(content)) * 100
            
            node['data']['content'] = optimized_content
            nodes_optimized += 1
            total_char_reduction += reduction
            
            changes_log.append(f"Node {node_id} ({label[:30]}...): {len(content):,} → {len(optimized_content):,} chars (-{reduction:,}, -{reduction_pct:.1f}%)")
            print(f"   ✅ Optimized: {len(content):,} → {len(optimized_content):,} chars (-{reduction_pct:.1f}%)")
        else:
            print(f"   ⚠️ No improvement")
    
    agent['call_flow'] = call_flow
    
    # STEP 3: Save if changes made
    print("\n" + "=" * 80)
    print("STEP 3: Saving Changes")
    print("=" * 80)
    
    if changes_log:
        print(f"\n📊 Total Changes: {len(changes_log)}")
        for change in changes_log:
            print(f"   - {change}")
        
        print(f"\n💾 Saving to MongoDB...")
        result = await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        
        if result.modified_count > 0:
            print(f"✅ Agent updated successfully")
            
            # Update optimization log
            timestamp = datetime.now().isoformat()
            log_entry = f"""
## Iteration 1: Smart Content Optimization
**Timestamp:** {timestamp}
**Status:** COMPLETE - Ready for Testing

### Changes Applied:
"""
            for change in changes_log:
                log_entry += f"- {change}\n"
            
            log_entry += f"""
### Metrics:
- Total Character Reduction: {total_char_reduction:,} chars
- Nodes Optimized: {nodes_optimized}
- System Prompt: {"Optimized" if "System Prompt" in str(changes_log) else "Unchanged"}

### Expected Impact:
- Baseline: 2309ms
- Projected: ~1680ms (27% improvement)
- Target: 1500ms

### Next Steps:
1. ✅ Backup created: /app/agent_backup_pre_optimization.json
2. ⏭️  Run latency test: webhook_latency_tester.py
3. ⏭️  **CRITICAL:** Validate transitions (must be 100% match)
4. ⏭️  Compare latency improvement
5. ⏭️  Decision: Keep if transitions work, revert if broken

### Rollback Command (if needed):
```bash
cd /app/backend
python3 << 'EOF'
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def rollback():
    with open('/app/agent_backup_pre_optimization.json', 'r') as f:
        agent = json.load(f)
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    result = await db.agents.update_one(
        {"id": "{AGENT_ID}"},
        {"$set": agent}
    )
    print(f"Rollback complete: {result.modified_count} document updated")

asyncio.run(rollback())
EOF
```

---

"""
            
            with open('/app/OPTIMIZATION_LOG.md', 'a') as f:
                f.write(log_entry)
            
            print(f"✅ Logged to /app/OPTIMIZATION_LOG.md")
        else:
            print(f"⚠️ No changes saved (nothing modified)")
    else:
        print(f"\n⚠️ No optimizations applied")
    
    print("\n" + "=" * 80)
    print("✅ OPTIMIZATION COMPLETE")
    print("=" * 80)
    print(f"""
📊 Summary:
   - Nodes Optimized: {nodes_optimized}
   - Total Character Reduction: {total_char_reduction:,} chars
   - Changes: {len(changes_log)}

⚠️  CRITICAL NEXT STEPS:
   1. Run latency test: cd /app/backend && python3 webhook_latency_tester.py
   2. Validate transitions (100% match required)
   3. Compare with baseline (2309ms)
   4. If transitions fail → rollback immediately
   5. If transitions pass → check if target (1500ms) met

💾 Backup Location: /app/agent_backup_pre_optimization.json
""")


if __name__ == "__main__":
    asyncio.run(main())
