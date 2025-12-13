"""
System Prompt Optimizer - Iteration 6
The system prompt is sent with EVERY LLM call, so optimizing it helps ALL responses
Current: 8518 chars
Target: 6500 chars (24% reduction)
"""
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
import httpx

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"


async def get_grok_key():
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    keys = await db.api_keys.find({"user_id": USER_ID}).to_list(length=50)
    
    for key_doc in keys:
        if key_doc.get('service_name') == 'grok' and key_doc.get('is_active', False):
            return key_doc.get('api_key')
    
    raise Exception("No active Grok API key found")


async def optimize_system_prompt(prompt: str, grok_key: str) -> str:
    system_msg = """Optimize a voice agent system prompt.

PRESERVE 100%:
- All behavior rules
- All variable syntax
- All KB query syntax
- All transition keywords

OPTIMIZE:
- Remove redundant examples (keep 1-2 best)
- Shorten verbose explanations
- Use concise bullet points

TARGET: 20-25% reduction

OUTPUT: Only optimized prompt."""

    user_msg = f"""Optimize this system prompt (20-25% reduction):

{prompt}"""

    async with httpx.AsyncClient(timeout=120.0) as client:
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
            print(f"❌ API error")
            return prompt
        
        result = response.json()
        optimized = result['choices'][0]['message']['content'].strip()
        
        reduction_pct = (len(prompt) - len(optimized)) / len(prompt) * 100
        
        print(f"Reduction: {reduction_pct:.1f}%")
        
        if reduction_pct > 30 or reduction_pct < 15:
            print(f"⚠️ Outside 15-30% range, keeping original")
            return prompt
        
        return optimized


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║        ITERATION 6 - System Prompt Optimization                              ║
║        Affects ALL LLM calls, high impact                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    grok_key = await get_grok_key()
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    agent.pop('_id', None)
    
    with open('/app/agent_backup_iter6.json', 'w') as f:
        json.dump(agent, f, indent=2, default=str)
    print("✅ Backup saved\n")
    
    system_prompt = agent.get('system_prompt', '')
    print(f"Current system prompt: {len(system_prompt)} chars")
    print("🔄 Optimizing...\n")
    
    optimized_prompt = await optimize_system_prompt(system_prompt, grok_key)
    
    if len(optimized_prompt) < len(system_prompt):
        reduction = len(system_prompt) - len(optimized_prompt)
        reduction_pct = (reduction / len(system_prompt)) * 100
        
        agent['system_prompt'] = optimized_prompt
        
        print(f"\n✅ {len(system_prompt)} → {len(optimized_prompt)} chars (-{reduction_pct:.1f}%)")
        
        await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        print("✅ Saved")
        
        with open('/app/OPTIMIZATION_LOG.md', 'a') as f:
            f.write(f"""
## Iteration 6: System Prompt Optimization
**Status:** COMPLETE

### Changes:
- System Prompt: {len(system_prompt)} → {len(optimized_prompt)} chars (-{reduction_pct:.1f}%)
- Affects ALL LLM calls

### Expected Impact:
- Reduces tokens sent with every request
- Should improve LLM latency across all nodes

---

""")
    else:
        print("\n⚠️ No improvement")
    
    print("\nITERATION 6 COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())
