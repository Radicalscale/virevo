#!/usr/bin/env python3
"""
Multi-Tenant API Key Management - Full Flow Testing
Tests user registration, API key storage, retrieval, and multi-tenant isolation
"""

import asyncio
import aiohttp
import json
import time
import os
import uuid
from typing import Dict, List, Optional

# Backend URL from production environment
BACKEND_URL = "https://missed-variable.preview.emergentagent.com/api"

class MultiTenantAPITester:
    def __init__(self):
        self.session = None
        self.test_results = []
        self.test_user_email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
        self.test_password = "TestPassword123!"
        self.auth_token = None
        self.user_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, message: str, details: Dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    async def test_user_registration(self):
        """Test user registration for multi-tenant testing"""
        try:
            user_data = {
                "email": self.test_user_email,
                "password": self.test_password,
                "remember_me": False
            }
            
            async with self.session.post(f"{BACKEND_URL}/auth/signup", json=user_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.user_id = data.get('user', {}).get('id')
                    
                    # Extract auth token from cookies
                    cookies = response.cookies
                    if 'access_token' in cookies:
                        self.auth_token = cookies['access_token'].value
                    
                    self.log_result(
                        "User Registration", 
                        True, 
                        f"Successfully registered test user", 
                        {
                            "email": self.test_user_email,
                            "user_id": self.user_id,
                            "has_auth_token": bool(self.auth_token)
                        }
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("User Registration", False, f"Registration failed: {response.status}", {"error": error_text})
                    return False
        except Exception as e:
            self.log_result("User Registration", False, f"Error during registration: {str(e)}")
            return False
    
    async def test_authenticated_api_key_list(self):
        """Test GET /api/settings/api-keys with authentication"""
        if not self.auth_token:
            self.log_result("Authenticated API Key List", False, "No auth token available")
            return False
        
        try:
            headers = {"Cookie": f"access_token={self.auth_token}"}
            async with self.session.get(f"{BACKEND_URL}/settings/api-keys", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_result(
                        "Authenticated API Key List", 
                        True, 
                        f"Successfully retrieved API key list (initially {len(data)} keys)", 
                        {"keys_count": len(data), "keys": data}
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("Authenticated API Key List", False, f"Failed to list keys: {response.status}", {"error": error_text})
                    return False
        except Exception as e:
            self.log_result("Authenticated API Key List", False, f"Error listing keys: {str(e)}")
            return False
    
    async def test_api_key_creation_grok(self):
        """Test creating a Grok API key"""
        if not self.auth_token:
            self.log_result("API Key Creation - Grok", False, "No auth token available")
            return False
        
        try:
            # Use the actual Grok API key from environment for testing
            grok_key = "xai-mDonAg7JKMuTnRm6k6NF9SxSNTrLpnENRyU5Y0CWzG82NBzKcr5y3eUGnC5Yxu7yZTRpG98ax2ZmE8GL"
            
            key_data = {
                "service_name": "grok",
                "api_key": grok_key
            }
            
            headers = {"Cookie": f"access_token={self.auth_token}"}
            async with self.session.post(f"{BACKEND_URL}/settings/api-keys", json=key_data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_result(
                        "API Key Creation - Grok", 
                        True, 
                        f"Successfully saved Grok API key", 
                        {"response": data, "service": "grok"}
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result("API Key Creation - Grok", False, f"Failed to save Grok key: {response.status}", {"error": error_text})
                    return False
        except Exception as e:
            self.log_result("API Key Creation - Grok", False, f"Error saving Grok key: {str(e)}")
            return False
    
    async def test_api_key_validation_grok(self):
        """Test Grok API key validation"""
        if not self.auth_token:
            self.log_result("API Key Validation - Grok", False, "No auth token available")
            return False
        
        try:
            headers = {"Cookie": f"access_token={self.auth_token}"}
            async with self.session.post(f"{BACKEND_URL}/settings/api-keys/test/grok", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    is_valid = data.get('valid', False)
                    
                    if is_valid:
                        self.log_result(
                            "API Key Validation - Grok", 
                            True, 
                            f"Grok API key validation successful", 
                            {"valid": is_valid, "message": data.get('message')}
                        )
                        return True
                    else:
                        self.log_result("API Key Validation - Grok", False, f"Grok key validation failed", {"response": data})
                        return False
                else:
                    error_text = await response.text()
                    self.log_result("API Key Validation - Grok", False, f"Validation request failed: {response.status}", {"error": error_text})
                    return False
        except Exception as e:
            self.log_result("API Key Validation - Grok", False, f"Error validating Grok key: {str(e)}")
            return False
    
    async def test_verify_grok_key_saved(self):
        """Verify Grok API key was saved correctly"""
        if not self.auth_token:
            self.log_result("Verify Grok Key Saved", False, "No auth token available")
            return False
        
        try:
            headers = {"Cookie": f"access_token={self.auth_token}"}
            async with self.session.get(f"{BACKEND_URL}/settings/api-keys", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Look for Grok key
                    grok_found = False
                    for key_info in data:
                        if key_info.get('service_name') == 'grok':
                            grok_found = True
                            break
                    
                    if grok_found:
                        self.log_result(
                            "Verify Grok Key Saved", 
                            True, 
                            f"Grok API key found in saved configurations", 
                            {"total_keys": len(data), "grok_found": True}
                        )
                        return True
                    else:
                        self.log_result("Verify Grok Key Saved", False, f"Grok key not found in configurations", {"keys": data})
                        return False
                else:
                    error_text = await response.text()
                    self.log_result("Verify Grok Key Saved", False, f"Failed to retrieve keys: {response.status}", {"error": error_text})
                    return False
        except Exception as e:
            self.log_result("Verify Grok Key Saved", False, f"Error verifying saved key: {str(e)}")
            return False
    
    async def test_create_agent_with_grok(self):
        """Test creating an agent that uses Grok LLM provider"""
        if not self.auth_token:
            self.log_result("Create Agent with Grok", False, "No auth token available")
            return False
        
        try:
            agent_data = {
                "name": "Multi-Tenant Test Agent",
                "description": "Agent for testing multi-tenant API key retrieval",
                "agent_type": "single_prompt",
                "system_prompt": "You are a helpful assistant. Keep responses under 50 words.",
                "settings": {
                    "llm_provider": "grok",
                    "tts_provider": "elevenlabs"
                }
            }
            
            headers = {"Cookie": f"access_token={self.auth_token}"}
            async with self.session.post(f"{BACKEND_URL}/agents", json=agent_data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    agent_id = data.get('id')
                    
                    self.log_result(
                        "Create Agent with Grok", 
                        True, 
                        f"Successfully created agent with Grok LLM provider", 
                        {
                            "agent_id": agent_id,
                            "name": data.get('name'),
                            "llm_provider": data.get('settings', {}).get('llm_provider')
                        }
                    )
                    return agent_id
                else:
                    error_text = await response.text()
                    self.log_result("Create Agent with Grok", False, f"Failed to create agent: {response.status}", {"error": error_text})
                    return None
        except Exception as e:
            self.log_result("Create Agent with Grok", False, f"Error creating agent: {str(e)}")
            return None
    
    async def test_agent_message_processing_with_user_keys(self, agent_id: str):
        """Test agent message processing using user's API keys"""
        if not self.auth_token or not agent_id:
            self.log_result("Agent Message Processing with User Keys", False, "Missing auth token or agent ID")
            return False
        
        try:
            message_data = {
                "message": "Tell me a short joke about AI",
                "conversation_history": []
            }
            
            headers = {"Cookie": f"access_token={self.auth_token}"}
            start_time = time.time()
            
            async with self.session.post(f"{BACKEND_URL}/agents/{agent_id}/process", json=message_data, headers=headers) as response:
                end_time = time.time()
                latency = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if response_text and len(response_text) > 10:
                        self.log_result(
                            "Agent Message Processing with User Keys", 
                            True, 
                            f"Agent successfully processed message using user's Grok API key", 
                            {
                                "response_length": len(response_text),
                                "latency": f"{latency:.2f}s",
                                "response_preview": response_text[:100] + "..." if len(response_text) > 100 else response_text
                            }
                        )
                        return True
                    else:
                        self.log_result("Agent Message Processing with User Keys", False, f"Empty or invalid response", {"response": response_text})
                        return False
                else:
                    error_text = await response.text()
                    self.log_result("Agent Message Processing with User Keys", False, f"Message processing failed: {response.status}", {"error": error_text})
                    return False
        except Exception as e:
            self.log_result("Agent Message Processing with User Keys", False, f"Error processing message: {str(e)}")
            return False
    
    async def test_multi_tenant_isolation(self):
        """Test that users can only access their own API keys"""
        try:
            # Create a second test user
            second_user_email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
            user_data = {
                "email": second_user_email,
                "password": self.test_password,
                "remember_me": False
            }
            
            async with self.session.post(f"{BACKEND_URL}/auth/signup", json=user_data) as response:
                if response.status == 200:
                    # Get second user's auth token
                    cookies = response.cookies
                    second_auth_token = cookies.get('access_token').value if 'access_token' in cookies else None
                    
                    if second_auth_token:
                        # Try to access API keys with second user's token
                        headers = {"Cookie": f"access_token={second_auth_token}"}
                        async with self.session.get(f"{BACKEND_URL}/settings/api-keys", headers=headers) as keys_response:
                            if keys_response.status == 200:
                                second_user_keys = await keys_response.json()
                                
                                # Second user should have 0 keys (isolation working)
                                if len(second_user_keys) == 0:
                                    self.log_result(
                                        "Multi-Tenant Isolation", 
                                        True, 
                                        f"Multi-tenant isolation working - Second user sees 0 keys", 
                                        {
                                            "first_user": self.test_user_email,
                                            "second_user": second_user_email,
                                            "second_user_keys": len(second_user_keys),
                                            "isolation_working": True
                                        }
                                    )
                                    return True
                                else:
                                    self.log_result("Multi-Tenant Isolation", False, f"Isolation failed - Second user sees {len(second_user_keys)} keys", {"keys": second_user_keys})
                                    return False
                            else:
                                self.log_result("Multi-Tenant Isolation", False, f"Failed to get second user keys: {keys_response.status}")
                                return False
                    else:
                        self.log_result("Multi-Tenant Isolation", False, "Failed to get second user auth token")
                        return False
                else:
                    self.log_result("Multi-Tenant Isolation", False, f"Failed to create second user: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Multi-Tenant Isolation", False, f"Error testing isolation: {str(e)}")
            return False
    
    async def run_comprehensive_test(self):
        """Run comprehensive multi-tenant API key management test"""
        print(f"\n🚀 MULTI-TENANT API KEY MANAGEMENT - FULL FLOW TESTING")
        print("=" * 80)
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 80)
        
        # Phase 1: User Registration and Authentication
        print(f"\n👤 Phase 1: User Registration and Authentication")
        print("-" * 50)
        
        if not await self.test_user_registration():
            print("❌ User registration failed - cannot continue with authenticated tests")
            return False
        
        # Phase 2: API Key Management
        print(f"\n🔑 Phase 2: API Key Management")
        print("-" * 50)
        
        tests_phase2 = [
            self.test_authenticated_api_key_list(),
            self.test_api_key_creation_grok(),
            self.test_api_key_validation_grok(),
            self.test_verify_grok_key_saved()
        ]
        
        results_phase2 = await asyncio.gather(*tests_phase2, return_exceptions=True)
        
        # Phase 3: Agent Creation and Message Processing
        print(f"\n🤖 Phase 3: Agent Creation and Message Processing")
        print("-" * 50)
        
        agent_id = await self.test_create_agent_with_grok()
        if agent_id:
            await self.test_agent_message_processing_with_user_keys(agent_id)
        
        # Phase 4: Multi-Tenant Isolation
        print(f"\n🔒 Phase 4: Multi-Tenant Isolation")
        print("-" * 50)
        
        await self.test_multi_tenant_isolation()
        
        # Summary
        print(f"\n📈 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print(f"\n✅ Multi-Tenant System Status:")
        print(f"  - User Registration: {'✅ OK' if any('User Registration' in r['test'] and r['success'] for r in self.test_results) else '❌ FAIL'}")
        print(f"  - API Key Storage: {'✅ OK' if any('API Key Creation' in r['test'] and r['success'] for r in self.test_results) else '❌ FAIL'}")
        print(f"  - API Key Retrieval: {'✅ OK' if any('API Key Validation' in r['test'] and r['success'] for r in self.test_results) else '❌ FAIL'}")
        print(f"  - Agent Integration: {'✅ OK' if any('Agent Message Processing' in r['test'] and r['success'] for r in self.test_results) else '❌ FAIL'}")
        print(f"  - Multi-Tenant Isolation: {'✅ OK' if any('Multi-Tenant Isolation' in r['test'] and r['success'] for r in self.test_results) else '❌ FAIL'}")
        
        return success_rate >= 80

async def main():
    """Main test execution"""
    async with MultiTenantAPITester() as tester:
        success = await tester.run_comprehensive_test()
        return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)