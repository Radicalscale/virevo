"""Test if async calls are truly parallel"""
import asyncio
import time
import os
from motor.motor_asyncio import AsyncIOMotorClient
import openai

AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"

async def simple_llm_call(client, prompt_num):
    """Make a simple LLM call"""
    start = time.time()
    try:
        response = await client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[{"role": "user", "content": f"Say 'Test {prompt_num}' in 5 words."}],
            temperature=0.3,
            max_tokens=20
        )
        elapsed = int((time.time() - start) * 1000)
        result = response.choices[0].message.content.strip()
        print(f"  Call {prompt_num}: {elapsed}ms - {result}")
        return result
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        print(f"  Call {prompt_num}: {elapsed}ms - ERROR: {e}")
        return ""

async def main():
    print("Testing TRUE parallel execution with Grok API\n")
    
    # Get Grok API key
    mongo_url = os.environ.get('MONGO_URL')
    client_db = AsyncIOMotorClient(mongo_url)
    db = client_db['test_database']
    
    # Get API key from database
    api_keys = await db.api_keys.find({"user_id": USER_ID, "service_name": "grok"}).to_list(length=10)
    
    if not api_keys:
        print("❌ No Grok API key found")
        return
    
    grok_key = api_keys[0].get('api_key', '')
    print(f"✅ Got Grok API key\n")
    
    # Create Grok client
    grok_client = openai.AsyncOpenAI(
        api_key=grok_key,
        base_url="https://api.x.ai/v1"
    )
    
    # Test 1: Sequential calls
    print("🔹 Test 1: SEQUENTIAL (one after another)")
    seq_start = time.time()
    
    await simple_llm_call(grok_client, 1)
    await simple_llm_call(grok_client, 2)
    await simple_llm_call(grok_client, 3)
    
    seq_total = int((time.time() - seq_start) * 1000)
    print(f"  Total Sequential: {seq_total}ms\n")
    
    # Test 2: Parallel calls
    print("🔹 Test 2: PARALLEL (asyncio.gather)")
    par_start = time.time()
    
    await asyncio.gather(
        simple_llm_call(grok_client, 4),
        simple_llm_call(grok_client, 5),
        simple_llm_call(grok_client, 6)
    )
    
    par_total = int((time.time() - par_start) * 1000)
    print(f"  Total Parallel: {par_total}ms\n")
    
    # Compare
    if par_total < seq_total:
        speedup = ((seq_total - par_total) / seq_total) * 100
        print(f"✅ Parallel is {speedup:.1f}% faster!")
    else:
        print(f"❌ No speedup detected - may not be truly parallel")

if __name__ == "__main__":
    asyncio.run(main())
