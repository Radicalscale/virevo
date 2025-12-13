"""
Simple Latency Optimizer - Uses exact same Grok pattern as server.py
Optimizes JK First Caller agent to achieve 1.5s latency target
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


async def optimize_text_with_grok(text: str, grok_key: str, optimization_type: str) -> str:
    """Optimize text using Grok - same pattern as server.py"""
    
    if optimization_type == "system_prompt":
        system_msg = "You are an elite voice agent prompt engineer. You optimize prompts for real-time non-reasoning LLMs by reducing verbosity, preventing hallucinations, and structuring for speed."
        user_msg = f"""Optimize this system prompt for minimum latency while preserving ALL logic:

RULES:
1. Remove redundant instructions
2. Convert paragraphs to bullet points
3. Eliminate flowery language
4. Keep all KB references and variables
5. Reduce by 30-50% while keeping all logic

SYSTEM PROMPT:
{text}

OUTPUT: Return ONLY the optimized prompt, no explanations."""

    elif optimization_type == "node":
        system_msg = "You are an expert at optimizing voice agent node prompts for speed."
        user_msg = f"""Optimize this node prompt for minimum processing time:

RULES:
1. Remove verbose context
2. Use numbered steps not paragraphs
3. Direct imperatives only
4. Keep exact phrasing for spoken text
5. Preserve all SSML tags

NODE CONTENT:
{text}

OUTPUT: Return ONLY the optimized content, no explanations."""

    else:  # transition
        system_msg = "You are an expert at optimizing voice agent transitions for instant evaluation."
        user_msg = f"""Optimize this transition condition for speed:

RULES:
1. Use boolean logic (AND/OR/NOT)
2. Remove explanatory text
3. Use pattern shortcuts (yes|yeah|yep)
4. Combine similar conditions

CONDITION:
{text}

OUTPUT: Return ONLY the optimized condition, no explanations."""
    
    # Use exact same API call pattern as server.py
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
                "temperature": 0.2,
                "max_tokens": 4000
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Grok API error: {response.status_code}")
            return text
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        return optimized


async def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            SIMPLE LATENCY OPTIMIZER - Using Working Infrastructure          ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Get MongoDB connection
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    # Get Grok API key
    print("🔑 Getting Grok API key...")
    grok_key = await get_grok_key()
    print("✅ Grok API key loaded")
    
    # Load agent
    print(f"\n📥 Loading agent {AGENT_ID}...")
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        print("❌ Agent not found")
        return
    
    agent.pop('_id', None)
    print(f"✅ Loaded: {agent.get('name')}")
    
    # Analyze
    system_prompt = agent.get('system_prompt', '')
    call_flow = agent.get('call_flow', [])
    
    print(f"\n📊 Analysis:")
    print(f"   System Prompt: {len(system_prompt):,} chars")
    print(f"   Call Flow Nodes: {len(call_flow)}")
    
    # Find nodes with long content
    long_nodes = []
    for node in call_flow:
        content = node.get('data', {}).get('content', '')
        if len(content) > 300:
            long_nodes.append({
                'node': node,
                'label': node.get('label', 'Unknown'),
                'length': len(content)
            })
    
    long_nodes.sort(key=lambda x: x['length'], reverse=True)
    print(f"   Nodes with long prompts: {len(long_nodes)}")
    
    changes = []
    total_reduction = 0
    
    # Optimize system prompt
    if len(system_prompt) > 1000:
        print(f"\n🎯 Optimizing system prompt ({len(system_prompt):,} chars)...")
        optimized_prompt = await optimize_text_with_grok(system_prompt, grok_key, "system_prompt")
        
        if len(optimized_prompt) < len(system_prompt):
            reduction = len(system_prompt) - len(optimized_prompt)
            total_reduction += reduction
            agent['system_prompt'] = optimized_prompt
            changes.append(f"System prompt: {len(system_prompt):,} → {len(optimized_prompt):,} chars (-{reduction:,})")
            print(f"   ✅ Reduced by {reduction:,} chars")
        else:
            print(f"   ⚠️ No improvement")
    
    # Optimize top 5 nodes
    print(f"\n📝 Optimizing top 5 longest nodes...")
    nodes_optimized = 0
    
    for i, node_info in enumerate(long_nodes[:5]):
        node = node_info['node']
        label = node_info['label']
        original_content = node.get('data', {}).get('content', '')
        
        print(f"   {i+1}. Optimizing: {label[:50]}... ({len(original_content):,} chars)")
        optimized_content = await optimize_text_with_grok(original_content, grok_key, "node")
        
        if len(optimized_content) < len(original_content):
            reduction = len(original_content) - len(optimized_content)
            total_reduction += reduction
            nodes_optimized += 1
            
            # Update in call_flow
            node['data']['content'] = optimized_content
            for idx, cf_node in enumerate(call_flow):
                if cf_node.get('id') == node.get('id'):
                    call_flow[idx] = node
                    break
            
            changes.append(f"Node '{label[:40]}': {len(original_content):,} → {len(optimized_content):,} chars (-{reduction:,})")
            print(f"      ✅ Reduced by {reduction:,} chars")
        else:
            print(f"      ⚠️ No improvement")
    
    agent['call_flow'] = call_flow
    
    # Save if changes made
    if changes:
        print(f"\n💾 Saving optimized agent...")
        result = await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        
        if result.modified_count > 0:
            print(f"✅ Agent saved to MongoDB")
            
            # Log to LATENCY_ITERATIONS.md
            timestamp = datetime.now().isoformat()
            log_entry = f"""
## Iteration 1: Automated Grok Optimization
**Date:** {timestamp}
**Agent:** JK First Caller-copy-copy
**Target:** 1.5s average latency

### Changes Made:
"""
            for change in changes:
                log_entry += f"- {change}\n"
            
            log_entry += f"""
### Metrics:
- **Total Character Reduction:** {total_reduction:,} chars
- **Nodes Optimized:** {nodes_optimized}
- **System Prompt:** {'✅ Optimized' if 'System prompt' in str(changes) else '⏭️ Skipped'}

### Next Steps:
1. Test agent with real phone calls
2. Measure latency improvements  
3. Validate logic preservation
4. Continue optimization if needed

### Status: ✅ Complete - Ready for Testing

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
    print(f"✅ OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
    print(f"\n📊 Summary:")
    print(f"   Total Character Reduction: {total_reduction:,} chars")
    print(f"   Changes Applied: {len(changes)}")
    print(f"\n📞 Next: Test the agent by calling it to measure latency improvements!")


if __name__ == "__main__":
    asyncio.run(main())
