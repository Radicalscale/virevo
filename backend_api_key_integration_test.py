#!/usr/bin/env python3
"""
API Key Resolution Integration Test

This script tests the actual get_user_api_key function in a real environment
by setting up a temporary database connection and testing the complete flow.
"""

import asyncio
import os
import sys
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, '/app/backend')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_api_key_resolution_integration():
    """Test API key resolution with real database connection"""
    print("🔗 Starting API Key Resolution Integration Test")
    print("=" * 60)
    
    try:
        # Load environment and connect to database
        from dotenv import load_dotenv
        load_dotenv('/app/backend/.env')
        
        mongo_url = os.environ.get('MONGO_URL')
        if not mongo_url:
            print("❌ MONGO_URL not found in environment")
            return False
        
        # Connect to database
        client = AsyncIOMotorClient(mongo_url)
        db_name = os.environ.get('DB_NAME', 'test_database')
        db = client[db_name]
        
        # Import and set up the function
        from qc_enhanced_router import get_user_api_key, set_db
        set_db(db)
        
        print(f"✅ Connected to database: {db_name}")
        
        # Test user ID (we'll use a test user)
        test_user_id = "api-key-test-user-123"
        
        # Test 1: Service alias resolution with no keys (should return None)
        print("\n=== Test 1: No Keys Found ===")
        result = await get_user_api_key(test_user_id, 'xai')
        if result is None:
            print("✅ No keys found returns None (correct)")
        else:
            print(f"❌ Expected None but got: {result}")
            return False
        
        # Test 2: Test with Emergent LLM key fallback
        print("\n=== Test 2: Emergent LLM Key Fallback ===")
        
        # Set up Emergent key
        test_emergent_key = "test-emergent-key-12345"
        os.environ['EMERGENT_LLM_KEY'] = test_emergent_key
        
        try:
            result = await get_user_api_key(test_user_id, 'openai')
            if result == test_emergent_key:
                print(f"✅ Emergent fallback working: {result[:20]}...")
            else:
                print(f"❌ Expected Emergent key but got: {result}")
                return False
        finally:
            # Clean up
            if 'EMERGENT_LLM_KEY' in os.environ:
                del os.environ['EMERGENT_LLM_KEY']
        
        # Test 3: Create a test API key and verify retrieval
        print("\n=== Test 3: Direct Key Retrieval ===")
        
        # Insert a test key
        test_key_doc = {
            "id": f"test-key-{datetime.now().timestamp()}",
            "user_id": test_user_id,
            "service_name": "grok",
            "api_key": "xai-test-integration-key-12345",
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        
        try:
            # Insert test key
            await db.api_keys.insert_one(test_key_doc)
            print("✅ Test key inserted")
            
            # Test direct retrieval
            result = await get_user_api_key(test_user_id, 'grok')
            if result == test_key_doc["api_key"]:
                print(f"✅ Direct key retrieval working: {result[:20]}...")
            else:
                print(f"❌ Expected test key but got: {result}")
                return False
            
            # Test alias resolution
            result = await get_user_api_key(test_user_id, 'xai')
            if result == test_key_doc["api_key"]:
                print(f"✅ Alias resolution working: xai → grok → {result[:20]}...")
            else:
                print(f"❌ Alias resolution failed, expected test key but got: {result}")
                return False
                
        finally:
            # Clean up test key
            await db.api_keys.delete_many({"user_id": test_user_id})
            print("✅ Test key cleaned up")
        
        # Test 4: Pattern matching with multiple keys
        print("\n=== Test 4: Pattern Matching ===")
        
        # Insert multiple test keys with different patterns
        test_keys = [
            {
                "id": f"test-key-openai-{datetime.now().timestamp()}",
                "user_id": test_user_id,
                "service_name": "unknown_service_1",
                "api_key": "sk-test-pattern-match-openai",
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "id": f"test-key-anthropic-{datetime.now().timestamp()}",
                "user_id": test_user_id,
                "service_name": "unknown_service_2", 
                "api_key": "sk-ant-test-pattern-match-anthropic",
                "is_active": True,
                "created_at": datetime.utcnow()
            }
        ]
        
        try:
            # Insert test keys
            await db.api_keys.insert_many(test_keys)
            print("✅ Pattern matching test keys inserted")
            
            # Test OpenAI pattern matching
            result = await get_user_api_key(test_user_id, 'openai')
            if result == "sk-test-pattern-match-openai":
                print(f"✅ OpenAI pattern matching working: {result[:20]}...")
            else:
                print(f"❌ OpenAI pattern matching failed, got: {result}")
                return False
            
            # Test Anthropic pattern matching
            result = await get_user_api_key(test_user_id, 'anthropic')
            if result == "sk-ant-test-pattern-match-anthropic":
                print(f"✅ Anthropic pattern matching working: {result[:20]}...")
            else:
                print(f"❌ Anthropic pattern matching failed, got: {result}")
                return False
                
        finally:
            # Clean up test keys
            await db.api_keys.delete_many({"user_id": test_user_id})
            print("✅ Pattern matching test keys cleaned up")
        
        print("\n" + "=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("=" * 60)
        
        print("\n📋 VERIFIED FUNCTIONALITY:")
        print("✅ Database connection and function setup")
        print("✅ Service alias resolution (xai → grok)")
        print("✅ Emergent LLM key fallback for supported services")
        print("✅ Direct key retrieval by service name")
        print("✅ Key pattern matching (sk-, sk-ant- prefixes)")
        print("✅ Proper cleanup and error handling")
        
        return True
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close database connection
        try:
            client.close()
            print("\n✅ Database connection closed")
        except:
            pass

async def main():
    """Main test runner"""
    success = await test_api_key_resolution_integration()
    
    if success:
        print("\n🎯 API Key Resolution integration test completed successfully!")
        return 0
    else:
        print("\n💥 API Key Resolution integration test failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)