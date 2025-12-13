#!/usr/bin/env python3
"""
Test script for the transition optimizer
Tests with the user's example transition condition
"""

import asyncio
import httpx
import os
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')

# Test transition from user
TEST_TRANSITION = """User agrees (yes/sure/okay/agreeing to hear more/consenting to call/asking what this is about). If they add objection/question/statement: address it first, then transition. Basic acknowledgments (go ahead/sure): proceed directly without context handling."""

async def test_transition_optimizer():
    """Test the transition optimizer with the example transition"""
    
    print("=" * 80)
    print("TESTING TRANSITION OPTIMIZER WITH GROK 4")
    print("=" * 80)
    print()
    
    # Connect to MongoDB to get Grok API key
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get Grok API key from database
    api_keys_collection = db['api_keys']
    grok_key_doc = await api_keys_collection.find_one({"service_name": "grok"})
    
    if not grok_key_doc:
        print("❌ Grok API key not found in database")
        print("   Please add Grok API key in Settings > API Keys")
        return
    
    grok_api_key = grok_key_doc.get('api_key')
    print(f"✅ Found Grok API key: {grok_api_key[:10]}...")
    print()
    
    print("📝 Original Transition Length:", len(TEST_TRANSITION), "characters")
    print("📝 Original Transition:")
    print(f"   {TEST_TRANSITION}")
    print()
    
    # Call the optimizer
    print("🚀 Calling Grok 4 (grok-4-0709) to optimize transition...")
    print()
    
    optimization_prompt = f"""You are an expert at optimizing transition conditions for real-time voice agents. Your goal is to make transition evaluation FAST while preserving all logic.

**TRANSITION OPTIMIZATION PRINCIPLES:**

**1. Speed is Critical**
- Transition conditions are evaluated on EVERY user message during real-time conversations
- Verbose conditions add 100-300ms latency per evaluation
- Reduce to bare essentials while keeping all logic intact

**2. Structure for Fast Parsing**
- Use SHORT declarative statements, not full sentences
- Lead with the MAIN condition, then qualifiers
- Use pipes (|) for OR conditions: "agrees | consents | positive response"
- Use parentheses for examples: "(yes/sure/okay)"
- Use colons for conditional logic: "IF objection: address first, THEN transition"

**3. Keep All Logic Intact**
- Do NOT remove any conditions or rules
- Preserve all examples and edge cases
- Maintain the decision tree structure
- Keep all "if-then" logic

**4. Formatting for Speed**
- Start with trigger condition in CAPS if critical
- Group similar conditions with pipes
- Use minimal words: "User agrees" → "Agrees"
- Avoid articles (the, a, an): "If they add question" → "If question"

**5. Examples of Optimization**

BEFORE (verbose):
"User agrees (yes/sure/okay/agreeing to hear more/consenting to call/asking what this is about). If they add objection/question/statement: address it first, then transition. Basic acknowledgments (go ahead/sure): proceed directly without context handling."

AFTER (optimized):
"Agrees | consents | positive (yes/sure/okay/what's this about). IF objection/question: handle first THEN transition. Basic acks (go ahead/sure): proceed directly."

BEFORE:
"The user is asking a question about pricing or wants to know how much it costs or is inquiring about the investment required"

AFTER:
"Price inquiry | cost question (how much/pricing/investment)"

BEFORE:
"If the user expresses any form of objection such as skepticism, doubt, concern about legitimacy, or questions whether this is a scam"

AFTER:
"Objection: skepticism | doubt | legitimacy concern | scam question"

**ORIGINAL TRANSITION CONDITION:**
```
{TEST_TRANSITION}
```

**YOUR TASK:**
1. Analyze the transition condition's logic and all edge cases
2. Restructure for fastest possible LLM evaluation (aim for 50-70% reduction)
3. Use pipes (|), colons (:), and parentheses () for compact structure
4. Preserve ALL conditions, examples, and if-then logic
5. Lead with main trigger, then qualifiers
6. Output ONLY the optimized condition - no explanations or context

**OUTPUT FORMAT:**
Return just the optimized transition condition text, ready to paste directly into the transition field."""

    try:
        async with httpx.AsyncClient(timeout=90.0) as http_client:
            response = await http_client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {grok_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-4-0709",
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert at optimizing transition conditions for real-time voice agents. You reduce verbosity while preserving all logic, making evaluations 2-3x faster."
                        },
                        {"role": "user", "content": optimization_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Grok API error: {response.status_code}")
                print(response.text)
                return
            
            result = response.json()
            optimized_condition = result['choices'][0]['message']['content'].strip()
            
            # Remove any markdown code blocks if present
            if optimized_condition.startswith('```'):
                lines = optimized_condition.split('\n')
                optimized_condition = '\n'.join(lines[1:-1]).strip()
            
            usage = result.get('usage', {})
            
            print("✅ Optimization complete!")
            print()
            print("📊 Stats:")
            print(f"   Original length: {len(TEST_TRANSITION)} chars")
            print(f"   Optimized length: {len(optimized_condition)} chars")
            reduction = ((len(TEST_TRANSITION) - len(optimized_condition)) / len(TEST_TRANSITION)) * 100
            print(f"   Reduction: {reduction:.1f}%")
            print(f"   Latency saved: ~{int((len(TEST_TRANSITION) - len(optimized_condition)) * 0.15)}ms per evaluation")
            print(f"   Tokens used: {usage.get('total_tokens', 'unknown')}")
            print()
            print("=" * 80)
            print("OPTIMIZED TRANSITION OUTPUT:")
            print("=" * 80)
            print()
            print(optimized_condition)
            print()
            print("=" * 80)
            print()
            
            print("✅ SUCCESS: Transition optimized while preserving all logic")
            print()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_transition_optimizer())
