"""
Conservative Prompt Optimizer
Reduces system prompt and node content by 20-30% while preserving all logic
Uses Grok API to intelligently compress prompts
"""
import asyncio
import json
import os
from motor.motor_asyncio import AsyncIOMotorClient
import httpx

AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"  # JK First Caller-optimizer3
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

async def get_grok_key(db):
    """Get Grok API key from database"""
    keys = await db.api_keys.find({"user_id": USER_ID}).to_list(length=50)
    for key_doc in keys:
        if key_doc.get('service_name') == 'grok' and key_doc.get('is_active'):
            return key_doc.get('api_key')
    return None

async def optimize_with_grok(content: str, content_type: str, grok_key: str) -> str:
    """Use Grok to optimize content"""
    
    optimization_prompt = f"""You are an expert at optimizing voice agent prompts. Your task is to reduce the length of this {content_type} by 20-30% while preserving ALL functionality.

CRITICAL RULES:
1. Keep ALL transition logic and keywords
2. Keep ALL variable names and extraction rules
3. Keep ALL conditional logic (if/then statements)
4. Remove verbose explanations and redundant text
5. Convert paragraphs to bullet points where possible
6. Keep technical terms and specific instructions
7. Maintain conversational tone markers

TARGET: Reduce from {len(content)} chars to approximately {int(len(content) * 0.75)} chars (25% reduction)

Original {content_type}:
{content}

Return ONLY the optimized version, no explanations or comments."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {grok_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-4-1-fast-non-reasoning",
                "messages": [
                    {"role": "user", "content": optimization_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4000
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            optimized = result['choices'][0]['message']['content'].strip()
            return optimized
        else:
            print(f"❌ Grok API error: {response.status_code}")
            print(response.text)
            return content

async def main():
    print("="*80)
    print("CONSERVATIVE PROMPT OPTIMIZER")
    print("Target: 20-30% reduction while preserving all logic")
    print("="*80)
    print()
    
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    # Get Grok API key
    print("🔑 Getting Grok API key...")
    grok_key = await get_grok_key(db)
    if not grok_key:
        print("❌ No Grok API key found")
        return
    print("✅ Grok API key found")
    print()
    
    # Load agent
    print(f"📥 Loading agent {AGENT_ID}...")
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        print("❌ Agent not found")
        return
    
    agent.pop('_id', None)
    print(f"✅ Agent loaded: {agent['name']}")
    print(f"   System Prompt: {len(agent.get('system_prompt', ''))} chars")
    print(f"   Call Flow Nodes: {len(agent.get('call_flow', []))}")
    print()
    
    # Backup original
    with open('/app/optimizer3_agent_backup.json', 'w') as f:
        json.dump(agent, f, indent=2, default=str)
    print("💾 Backup saved to /app/optimizer3_agent_backup.json")
    print()
    
    # Optimize system prompt
    print("🔧 Optimizing system prompt...")
    original_prompt = agent.get('system_prompt', '')
    print(f"   Original: {len(original_prompt)} chars")
    
    optimized_prompt = await optimize_with_grok(original_prompt, "system prompt", grok_key)
    print(f"   Optimized: {len(optimized_prompt)} chars")
    print(f"   Reduction: {len(original_prompt) - len(optimized_prompt)} chars ({((len(original_prompt) - len(optimized_prompt)) / len(original_prompt) * 100):.1f}%)")
    agent['system_prompt'] = optimized_prompt
    print()
    
    # Find largest nodes
    flows = agent.get('call_flow', [])
    node_sizes = []
    for i, node in enumerate(flows):
        data = node.get('data', {})
        content = data.get('content', '') or data.get('script', '')
        if content and len(content) > 3000:  # Only optimize large nodes
            node_sizes.append((i, node.get('label', 'unknown'), len(content)))
    
    node_sizes.sort(key=lambda x: x[2], reverse=True)
    
    # Optimize top 10 largest nodes
    print(f"🔧 Optimizing top {min(10, len(node_sizes))} largest nodes...")
    print()
    
    for rank, (idx, label, size) in enumerate(node_sizes[:10], 1):
        node = flows[idx]
        data = node.get('data', {})
        content = data.get('content', '') or data.get('script', '')
        
        print(f"{rank}. {label[:60]}")
        print(f"   Original: {len(content)} chars")
        
        optimized_content = await optimize_with_grok(content, f"node prompt ({label})", grok_key)
        print(f"   Optimized: {len(optimized_content)} chars")
        print(f"   Reduction: {len(content) - len(optimized_content)} chars ({((len(content) - len(optimized_content)) / len(content) * 100):.1f}%)")
        
        # Update the node
        if data.get('content'):
            data['content'] = optimized_content
        elif data.get('script'):
            data['script'] = optimized_content
        
        print()
    
    # Save optimized agent
    print("💾 Saving optimized agent to MongoDB...")
    agent['_id'] = await db.agents.find_one({"id": AGENT_ID}, {"_id": 1})
    agent['_id'] = agent['_id']['_id']
    
    result = await db.agents.replace_one(
        {"id": AGENT_ID},
        agent
    )
    
    if result.modified_count > 0:
        print("✅ Agent updated successfully")
    else:
        print("⚠️ No changes made")
    
    print()
    print("="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print()
    print("Next steps:")
    print("1. Run webhook_latency_tester.py to measure new performance")
    print("2. Compare results with baseline")
    print("3. Validate transitions are still correct")
    print()

if __name__ == "__main__":
    asyncio.run(main())
