"""
Test different KB strategies with REAL LLM calls to find fastest approach
"""
import asyncio
import time
import sys
import os

sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient

async def get_llm_client():
    """Get Grok client"""
    from calling_service import get_llm_client
    return await get_llm_client("grok", api_key=os.environ.get('GROK_API_KEY'))

async def test_strategy(strategy_name, system_prompt, conversation_history, user_message):
    """Test a single strategy and measure latency"""
    print(f"\n{'='*80}")
    print(f"🧪 TESTING: {strategy_name}")
    print(f"{'='*80}")
    print(f"System prompt size: {len(system_prompt)} chars")
    print(f"Conversation history: {len(conversation_history)} messages")
    
    try:
        client = await get_llm_client()
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt}
        ] + conversation_history + [
            {"role": "user", "content": user_message}
        ]
        
        # Time the request
        start = time.time()
        
        response_stream = await client.create_completion(
            messages=messages,
            model="grok-4-fast-non-reasoning",
            temperature=0.7,
            max_tokens=150,
            stream=True
        )
        
        first_token_time = None
        full_response = ""
        
        async for chunk in response_stream:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    if first_token_time is None:
                        first_token_time = time.time()
                    full_response += delta.content
        
        end = time.time()
        
        ttft = (first_token_time - start) * 1000 if first_token_time else 0
        total_time = (end - start) * 1000
        
        print(f"\n📊 Results:")
        print(f"   ⏱️  TTFT (Time to First Token): {ttft:.0f}ms")
        print(f"   ⏱️  Total Time: {total_time:.0f}ms")
        print(f"   📝 Response length: {len(full_response)} chars")
        print(f"   💬 Response: {full_response[:200]}...")
        
        return {
            "strategy": strategy_name,
            "ttft": ttft,
            "total_time": total_time,
            "response": full_response,
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "strategy": strategy_name,
            "success": False,
            "error": str(e)
        }

async def run_tests():
    """Run all strategy tests"""
    print("="*80)
    print("🔬 LATENCY STRATEGY TESTING - Finding Fastest Approach")
    print("="*80)
    
    # Get Jake's actual KB
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ.get('DB_NAME', 'voice_agent_db')]
    
    agent_id = "474917c1-4888-47b8-b76b-f11a18f19d39"
    kb_items = await db.knowledge_base.find({"agent_id": agent_id}).to_list(100)
    
    # Format full KB
    full_kb = ""
    if kb_items:
        kb_texts = []
        for idx, item in enumerate(kb_items, 1):
            source_name = item.get("source_name", "Unknown")
            content = item.get("content", "")
            kb_texts.append(f"### SOURCE {idx}: {source_name}\n{content}\n")
        full_kb = "\n".join(kb_texts)
    
    print(f"\n📚 Loaded Jake's KB: {len(kb_items)} items, {len(full_kb)} chars total")
    
    # Base system prompt (no KB)
    base_prompt = """You are Jake, a sales representative conducting a phone conversation.

COMMUNICATION STYLE:
- Speak naturally and conversationally
- Keep responses concise (1-2 sentences)
- Be friendly and professional

STRICT RULES:
- NO format markers or meta-text
- Just speak naturally as a human would"""
    
    # Conversation history (simulating a call in progress)
    conversation = [
        {"role": "assistant", "content": "This is Jake. I was wondering if you could help me out for a moment?"},
        {"role": "user", "content": "Sure, what's up?"},
    ]
    
    # Test messages - different types
    test_messages = {
        "simple_chat": "Yeah, with what?",  # Simple acknowledgment - NO KB needed
        "factual_question": "Who are the founders of your company?",  # Needs KB
        "casual": "Sure, go ahead",  # Simple - NO KB needed
    }
    
    # ============================================================
    # STRATEGY 1: NO KB - Simple Chat (What we should use for "yeah with what")
    # ============================================================
    result1a = await test_strategy(
        "Strategy 1a: NO KB - Simple Chat Response",
        base_prompt,
        conversation,
        test_messages["simple_chat"]
    )
    
    await asyncio.sleep(2)
    
    # ============================================================
    # STRATEGY 1b: NO KB - Factual Question (Will be wrong but fast)
    # ============================================================
    result1b = await test_strategy(
        "Strategy 1b: NO KB - Factual Question (baseline speed)",
        base_prompt,
        conversation,
        test_messages["factual_question"]
    )
    
    await asyncio.sleep(2)  # Brief pause between tests
    
    # ============================================================
    # STRATEGY 2: FULL KB - Factual Question (Current slow approach)
    # ============================================================
    full_kb_prompt = base_prompt + f"\n\n=== KNOWLEDGE BASE ===\n{full_kb}\n=== END KNOWLEDGE BASE ==="
    
    result2a = await test_strategy(
        "Strategy 2a: FULL KB (412KB) - Factual Question",
        full_kb_prompt,
        conversation,
        test_messages["factual_question"]
    )
    
    await asyncio.sleep(2)
    
    # ============================================================
    # STRATEGY 2b: FULL KB - Simple Chat (Should be unnecessary)
    # ============================================================
    result2b = await test_strategy(
        "Strategy 2b: FULL KB (412KB) - Simple Chat (wasteful)",
        full_kb_prompt,
        conversation,
        test_messages["simple_chat"]
    )
    
    await asyncio.sleep(2)
    
    # ============================================================
    # STRATEGY 3: SMART ROUTING - Only use KB when needed
    # ============================================================
    print(f"\n{'='*80}")
    print(f"🧪 TESTING: Strategy 3: SMART ROUTING (KB only when needed)")
    print(f"{'='*80}")
    print("Testing both simple chat AND factual question...")
    
    # 3a: Simple chat - NO KB
    result3a = await test_strategy(
        "Strategy 3a: SMART - Simple Chat (NO KB)",
        base_prompt,
        conversation,
        test_messages["simple_chat"]
    )
    
    await asyncio.sleep(2)
    
    # 3b: Factual question - WITH small KB
    small_kb_smart = ""
    if kb_items:
        small_kb_smart = kb_items[0].get('content', '')[:30000]  # 30K company info
    
    smart_prompt = base_prompt + f"\n\n=== COMPANY INFO ===\n{small_kb_smart}\n=== END ==="
    result3b = await test_strategy(
        "Strategy 3b: SMART - Factual Question (30KB KB)",
        smart_prompt,
        conversation,
        test_messages["factual_question"]
    )
    
    await asyncio.sleep(2)
    
    # ============================================================
    # STRATEGY 4: Small KB excerpt (company info only)
    # ============================================================
    # Get just the company info (first KB item)
    small_kb = ""
    if kb_items:
        small_kb = kb_items[0].get('content', '')[:20000]  # First 20K chars of company info
    
    small_kb_prompt = base_prompt + f"\n\n=== COMPANY INFO ===\n{small_kb}\n=== END INFO ==="
    
    result4 = await test_strategy(
        "Strategy 4: Small KB (20KB company info only)",
        small_kb_prompt,
        conversation,
        test_messages["factual_question"]
    )
    
    await asyncio.sleep(2)
    
    # ============================================================
    # STRATEGY 5: KB as separate system message (multi-message)
    # ============================================================
    print(f"\n{'='*80}")
    print(f"🧪 TESTING: Strategy 5: KB as Separate System Message")
    print(f"{'='*80}")
    
    try:
        client_obj = await get_llm_client()
        start = time.time()
        
        messages_multi = [
            {"role": "system", "content": base_prompt},
            {"role": "system", "content": f"=== KNOWLEDGE BASE ===\n{small_kb}\n=== END ==="}
        ] + conversation + [
            {"role": "user", "content": test_messages["factual_question"]}
        ]
        
        response_stream = await client_obj.create_completion(
            messages=messages_multi,
            model="grok-4-fast-non-reasoning",
            temperature=0.7,
            max_tokens=150,
            stream=True
        )
        
        first_token_time = None
        full_response = ""
        
        async for chunk in response_stream:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    if first_token_time is None:
                        first_token_time = time.time()
                    full_response += delta.content
        
        end = time.time()
        ttft = (first_token_time - start) * 1000 if first_token_time else 0
        total_time = (end - start) * 1000
        
        print(f"\n📊 Results:")
        print(f"   ⏱️  TTFT: {ttft:.0f}ms")
        print(f"   ⏱️  Total Time: {total_time:.0f}ms")
        print(f"   💬 Response: {full_response[:200]}...")
        
        result5 = {
            "strategy": "Strategy 5: Separate System Messages",
            "ttft": ttft,
            "total_time": total_time,
            "success": True
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        result5 = {"strategy": "Strategy 5", "success": False}
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print(f"\n\n{'='*80}")
    print(f"📊 FINAL RESULTS SUMMARY")
    print(f"{'='*80}")
    
    results = [result1a, result1b, result2a, result2b, result3a, result3b, result4, result5]
    successful = [r for r in results if r.get('success')]
    
    if successful:
        # Sort by total time
        successful.sort(key=lambda x: x.get('total_time', float('inf')))
        
        print(f"\n🏆 RANKING (Fastest to Slowest):\n")
        for i, result in enumerate(successful, 1):
            ttft = result.get('ttft', 0)
            total = result.get('total_time', 0)
            print(f"{i}. {result['strategy']}")
            print(f"   ⏱️  TTFT: {ttft:.0f}ms | Total: {total:.0f}ms")
        
        best = successful[0]
        print(f"\n✅ WINNER: {best['strategy']}")
        print(f"   ⏱️  {best.get('total_time', 0):.0f}ms total latency")
        print(f"\n💡 RECOMMENDATION: Use this strategy for production")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
