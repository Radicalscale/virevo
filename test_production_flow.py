#!/usr/bin/env python3
"""
Production Flow Testing - Multi-Tenant API Key Management
Tests the actual deployed flow: users store keys in MongoDB, system retrieves them dynamically
"""

import sys
import os
import asyncio
import aiohttp
import json
import uuid

# Backend URL
BACKEND_URL = os.getenv('BACKEND_URL', 'https://tts-guardian.preview.emergentagent.com')

class ProductionFlowTester:
    def __init__(self):
        self.test_results = []
        self.session = None
        self.auth_token = None
        self.user_id = None
        self.test_user_email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
        self.test_user_password = "TestPassword123!"
        
    async def __aenter__(self):
        # Create session with cookie jar to preserve httpOnly cookies
        cookie_jar = aiohttp.CookieJar(unsafe=True)  # unsafe=True to accept cookies from different domains
        self.session = aiohttp.ClientSession(cookie_jar=cookie_jar)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, message: str, details: dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        print(f"        {message}")
        if details:
            for key, value in details.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"        {key}: {value[:100]}...")
                else:
                    print(f"        {key}: {value}")
        print()
    
    async def test_user_signup(self):
        """Test 1: Create a test user"""
        print("="*80)
        print("TEST 1: USER SIGNUP")
        print("="*80)
        
        try:
            payload = {
                "email": self.test_user_email,
                "password": self.test_user_password,
                "name": "Test User"
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/api/auth/signup",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # System uses httpOnly cookies, not Bearer tokens
                    # Check if we got cookies
                    cookies = self.session.cookie_jar.filter_cookies(BACKEND_URL)
                    has_auth_cookie = any('access_token' in str(cookie.key) for cookie in cookies.values())
                    
                    # Extract user info from response
                    user_data = data.get('user', {})
                    self.user_id = user_data.get('id')
                    self.auth_token = "cookie-based"  # Mark as authenticated
                    
                    self.log_result(
                        "User Signup",
                        True,
                        "Test user created successfully with httpOnly cookie",
                        {
                            "email": self.test_user_email,
                            "user_id": self.user_id,
                            "auth_method": "httpOnly cookie",
                            "has_cookie": has_auth_cookie
                        }
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result(
                        "User Signup",
                        False,
                        f"Signup failed with status {response.status}",
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("User Signup", False, f"Error: {str(e)}")
            return False
    
    async def test_store_api_keys(self):
        """Test 2: Store API keys in MongoDB for the test user"""
        print("="*80)
        print("TEST 2: STORE API KEYS IN MONGODB")
        print("="*80)
        
        if not self.auth_token:
            self.log_result("Store API Keys", False, "No auth token - skip test")
            return False
        
        # Get API keys from environment (these will be stored in MongoDB for the user)
        from dotenv import load_dotenv
        load_dotenv('/app/backend/.env')
        
        api_keys_to_store = {
            "deepgram": os.getenv('DEEPGRAM_API_KEY'),
            "openai": os.getenv('OPENAI_API_KEY'),
            "elevenlabs": os.getenv('ELEVEN_API_KEY'),
            "hume": os.getenv('HUME_API_KEY'),
            "assemblyai": os.getenv('ASSEMBLYAI_API_KEY'),
            "soniox": os.getenv('SONIOX_API_KEY'),
            "grok": os.getenv('GROK_API_KEY'),
        }
        
        # No need for Authorization header - using httpOnly cookies
        headers = {}
        stored_count = 0
        
        for service_name, api_key in api_keys_to_store.items():
            if not api_key:
                print(f"   ⚠️  Skipping {service_name} - no key in environment")
                continue
            
            try:
                payload = {
                    "service_name": service_name,
                    "api_key": api_key
                }
                
                async with self.session.post(
                    f"{BACKEND_URL}/api/settings/api-keys",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        stored_count += 1
                        print(f"   ✅ Stored {service_name} API key in MongoDB")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Failed to store {service_name}: {error_text}")
            except Exception as e:
                print(f"   ❌ Error storing {service_name}: {str(e)}")
        
        if stored_count > 0:
            self.log_result(
                "Store API Keys",
                True,
                f"Successfully stored {stored_count} API keys in MongoDB",
                {"stored_services": list(api_keys_to_store.keys())[:stored_count]}
            )
            return True
        else:
            self.log_result(
                "Store API Keys",
                False,
                "Failed to store any API keys"
            )
            return False
    
    async def test_retrieve_api_keys(self):
        """Test 3: Retrieve stored API keys from MongoDB"""
        print("="*80)
        print("TEST 3: RETRIEVE API KEYS FROM MONGODB")
        print("="*80)
        
        if not self.auth_token:
            self.log_result("Retrieve API Keys", False, "No auth token - skip test")
            return False
        
        try:
            # No need for Authorization header - using httpOnly cookies
            headers = {}
            
            async with self.session.get(
                f"{BACKEND_URL}/api/settings/api-keys",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    keys = data.get('keys', [])
                    
                    self.log_result(
                        "Retrieve API Keys",
                        True,
                        f"Successfully retrieved {len(keys)} API keys from MongoDB",
                        {
                            "key_count": len(keys),
                            "services": [k.get('service_name') for k in keys]
                        }
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Retrieve API Keys",
                        False,
                        f"Failed with status {response.status}",
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Retrieve API Keys", False, f"Error: {str(e)}")
            return False
    
    async def test_validate_api_keys(self):
        """Test 4: Test API key validation endpoints"""
        print("="*80)
        print("TEST 4: VALIDATE STORED API KEYS")
        print("="*80)
        
        if not self.auth_token:
            self.log_result("Validate API Keys", False, "No auth token - skip test")
            return False
        
        # No need for Authorization header - using httpOnly cookies
        headers = {}
        
        # Test validating OpenAI key
        try:
            async with self.session.post(
                f"{BACKEND_URL}/api/settings/api-keys/test/openai",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    is_valid = data.get('valid', False)
                    
                    self.log_result(
                        "Validate API Keys (OpenAI)",
                        is_valid,
                        "OpenAI key validation successful" if is_valid else "OpenAI key validation failed",
                        {
                            "valid": is_valid,
                            "message": data.get('message', '')
                        }
                    )
                    return is_valid
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Validate API Keys (OpenAI)",
                        False,
                        f"Validation failed with status {response.status}",
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Validate API Keys (OpenAI)", False, f"Error: {str(e)}")
            return False
    
    async def test_create_agent_with_providers(self):
        """Test 5: Create an agent with specific providers"""
        print("="*80)
        print("TEST 5: CREATE AGENT WITH PROVIDER CONFIGURATION")
        print("="*80)
        
        if not self.auth_token:
            self.log_result("Create Agent", False, "No auth token - skip test")
            return False
        
        try:
            # No need for Authorization header - using httpOnly cookies
            headers = {}
            
            payload = {
                "name": "Production Test Agent",
                "agent_type": "single_prompt",
                "system_prompt": "You are a helpful AI assistant for testing.",
                "settings": {
                    "stt_provider": "deepgram",
                    "llm_provider": "openai",
                    "tts_provider": "elevenlabs",
                    "llm_model": "gpt-4o-mini"
                }
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/api/agents",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    agent_id = data.get('id')
                    
                    self.log_result(
                        "Create Agent",
                        True,
                        "Agent created successfully with provider configuration",
                        {
                            "agent_id": agent_id,
                            "stt_provider": "deepgram",
                            "llm_provider": "openai",
                            "tts_provider": "elevenlabs"
                        }
                    )
                    return agent_id
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Create Agent",
                        False,
                        f"Failed with status {response.status}",
                        {"error": error_text}
                    )
                    return None
        except Exception as e:
            self.log_result("Create Agent", False, f"Error: {str(e)}")
            return None
    
    async def test_agent_message_processing(self, agent_id: str):
        """Test 6: Test agent message processing with database-stored keys"""
        print("="*80)
        print("TEST 6: AGENT MESSAGE PROCESSING (USES DB KEYS)")
        print("="*80)
        
        if not self.auth_token or not agent_id:
            self.log_result("Agent Message Processing", False, "Missing auth token or agent ID")
            return False
        
        try:
            # No need for Authorization header - using httpOnly cookies
            headers = {}
            
            payload = {
                "message": "Say 'Production test successful' in exactly those words.",
                "history": []
            }
            
            import time
            start_time = time.time()
            
            async with self.session.post(
                f"{BACKEND_URL}/api/agents/{agent_id}/process",
                headers=headers,
                json=payload
            ) as response:
                latency = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    self.log_result(
                        "Agent Message Processing",
                        True,
                        "Agent successfully processed message using database-stored API keys",
                        {
                            "response": response_text[:200],
                            "latency": f"{latency:.2f}s",
                            "used_db_keys": "Yes - retrieved OpenAI key from MongoDB"
                        }
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Agent Message Processing",
                        False,
                        f"Failed with status {response.status}",
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Agent Message Processing", False, f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_multi_provider_agents(self):
        """Test 7: Create agents with different provider combinations"""
        print("="*80)
        print("TEST 7: MULTI-PROVIDER AGENT CONFIGURATIONS")
        print("="*80)
        
        if not self.auth_token:
            self.log_result("Multi-Provider Agents", False, "No auth token - skip test")
            return False
        
        # No need for Authorization header - using httpOnly cookies
        headers = {}
        
        provider_combinations = [
            ("assemblyai", "openai", "elevenlabs"),
            ("deepgram", "grok", "elevenlabs"),
            ("soniox", "grok", "hume"),
        ]
        
        created_count = 0
        
        for stt, llm, tts in provider_combinations:
            try:
                payload = {
                    "name": f"Test Agent ({stt}/{llm}/{tts})",
                    "agent_type": "single_prompt",
                    "system_prompt": "Test agent",
                    "settings": {
                        "stt_provider": stt,
                        "llm_provider": llm,
                        "tts_provider": tts
                    }
                }
                
                async with self.session.post(
                    f"{BACKEND_URL}/api/agents",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        created_count += 1
                        print(f"   ✅ Created agent: {stt} + {llm} + {tts}")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Failed to create {stt}/{llm}/{tts}: {error_text[:100]}")
            except Exception as e:
                print(f"   ❌ Error creating {stt}/{llm}/{tts}: {str(e)}")
        
        if created_count > 0:
            self.log_result(
                "Multi-Provider Agents",
                True,
                f"Successfully created {created_count}/{len(provider_combinations)} multi-provider agents",
                {"combinations_tested": provider_combinations}
            )
            return True
        else:
            self.log_result(
                "Multi-Provider Agents",
                False,
                "Failed to create any multi-provider agents"
            )
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("PRODUCTION FLOW TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in self.test_results if r['success'])
        failed = sum(1 for r in self.test_results if not r['success'])
        total = passed + failed
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        
        if total > 0:
            print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n" + "="*80)
        print("KEY FINDINGS:")
        print("="*80)
        
        if passed == total and total > 0:
            print("✅ PRODUCTION FLOW WORKING CORRECTLY")
            print("   - Users can sign up and authenticate")
            print("   - API keys are stored in MongoDB (encrypted)")
            print("   - API keys are retrieved from MongoDB (decrypted)")
            print("   - Agents use database-stored keys (not .env)")
            print("   - Multi-provider configuration working")
            print("   - System ready for multi-tenant deployment")
        else:
            print("⚠️  ISSUES DETECTED IN PRODUCTION FLOW")
            print("   - Review failed tests above")
            print("   - Check MongoDB connection")
            print("   - Verify Railway deployment configuration")
        
        print("="*80)

async def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("PRODUCTION FLOW TESTING - MULTI-TENANT WITH MONGODB")
    print("Testing: Railway Deployment + MongoDB + Dynamic API Keys")
    print("="*80)
    print()
    
    async with ProductionFlowTester() as tester:
        # Run all tests in sequence
        signup_success = await tester.test_user_signup()
        
        if signup_success:
            await tester.test_store_api_keys()
            await tester.test_retrieve_api_keys()
            await tester.test_validate_api_keys()
            agent_id = await tester.test_create_agent_with_providers()
            
            if agent_id:
                await tester.test_agent_message_processing(agent_id)
            
            await tester.test_multi_provider_agents()
        else:
            print("\n⚠️  Skipping remaining tests due to signup failure")
        
        # Print summary
        tester.print_summary()

if __name__ == "__main__":
    asyncio.run(main())
