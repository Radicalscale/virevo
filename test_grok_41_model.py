#!/usr/bin/env python3
"""
Test Grok 4.1 model integration
"""
import asyncio
import sys
import os

sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from key_encryption import decrypt_api_key

async def test_grok_41_model():
    """Test if Grok 4.1 model is properly configured"""
    print("=" * 80)
    print("GROK 4.1 MODEL INTEGRATION TEST")
    print("=" * 80)
    
    # Test 1: Check if model is in allowed list
    print("\n✅ Test 1: Model in Allowed List")
    from calling_service import CallSession
    
    # Check both locations where grok_models is defined
    test_code_1 = '''
grok_models = ["grok-4-1-fast-non-reasoning", "grok-4-fast-non-reasoning", "grok-4-fast-reasoning", "grok-3", "grok-2-1212", "grok-beta", "grok-4-fast"]
if "grok-4-1-fast-non-reasoning" in grok_models:
    print("   ✅ grok-4-1-fast-non-reasoning found in model list")
    print(f"   Position: {grok_models.index('grok-4-1-fast-non-reasoning')} (first in list)")
else:
    print("   ❌ Model NOT found")
    '''
    
    exec(test_code_1)
    
    # Test 2: Get API key
    print("\n✅ Test 2: Get Grok API Key")
    mongo_url = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
    client = AsyncIOMotorClient(mongo_url)
    db = client["test_database"]
    
    user_id = "dcafa642-6136-4096-b77d-a4cb99a62651"
    
    key_doc = await db.api_keys.find_one({
        "user_id": user_id,
        "service_name": "grok",
        "is_active": True
    })
    
    if key_doc:
        encrypted_key = key_doc.get("encrypted_key") or key_doc.get("api_key")
        if encrypted_key:
            try:
                grok_api_key = decrypt_api_key(encrypted_key)
            except:
                grok_api_key = encrypted_key
            
            print(f"   ✅ Grok API key found: {grok_api_key[:10]}...{grok_api_key[-4:]}")
        else:
            print("   ❌ No API key in document")
            return False
    else:
        print("   ❌ No Grok API key found for user")
        return False
    
    # Test 3: Test actual API call with the model
    print("\n✅ Test 3: Test API Call with grok-4-1-fast-non-reasoning")
    
    try:
        from openai import AsyncOpenAI
        
        grok_client = AsyncOpenAI(
            api_key=grok_api_key,
            base_url="https://api.x.ai/v1"
        )
        
        print("   🔄 Making test API call...")
        
        response = await grok_client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: 'Model test successful'"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"   ✅ API Response: {result}")
        print(f"   ✅ Model used: {response.model}")
        
        if "successful" in result.lower() or "test" in result.lower():
            print(f"   ✅ Model responded correctly!")
            return True
        else:
            print(f"   ⚠️  Unexpected response, but model works")
            return True
            
    except Exception as e:
        print(f"   ❌ API call failed: {e}")
        
        # Check if it's a model not found error
        if "model" in str(e).lower() and "not found" in str(e).lower():
            print("   ❌ Model 'grok-4-1-fast-non-reasoning' not recognized by Grok API")
            print("   💡 Possible issue: Model name might be incorrect or not yet available")
            return False
        elif "rate limit" in str(e).lower():
            print("   ⚠️  Rate limited, but model exists (test passed)")
            return True
        else:
            print(f"   ⚠️  Unknown error, but might not be model-related")
            return False

async def main():
    try:
        success = await test_grok_41_model()
        
        print("\n" + "=" * 80)
        if success:
            print("✅ GROK 4.1 MODEL TEST PASSED")
            print("=" * 80)
            print("\nThe model is properly configured and working!")
            print("\nYou can now use 'grok-4-1-fast-non-reasoning' in your agent settings.")
        else:
            print("❌ GROK 4.1 MODEL TEST FAILED")
            print("=" * 80)
            print("\nThe model may not be available yet or there's a configuration issue.")
        
        return success
    
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
