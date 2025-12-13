#!/usr/bin/env python3
"""
Soniox STT + Grok LLM Integration Testing
Tests the specific integration requested in the review
"""

import asyncio
import aiohttp
import json
import time
import os
from typing import Dict, List, Optional

# Backend URL - using local port 8001 where our backend is running
BACKEND_URL = "http://127.0.0.1:8001/api"

class SonioxGrokTester:
    def __init__(self):
        self.session = None
        self.test_results = []
        self.user_session = None
        self.authenticated = False
        
    async def __aenter__(self):
        # Create session with cookie jar for authentication
        jar = aiohttp.CookieJar()
        self.session = aiohttp.ClientSession(cookie_jar=jar)
        
        # Try to authenticate
        await self.authenticate()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def authenticate(self):
        """Authenticate with the backend API"""
        try:
            # First try to create a test user
            signup_data = {
                "email": "soniox_test@example.com",
                "password": "testpassword123",
                "remember_me": True
            }
            
            async with self.session.post(f"{BACKEND_URL}/auth/signup", json=signup_data) as response:
                if response.status == 200:
                    self.authenticated = True
                    print("✅ Created and authenticated test user")
                    return True
                elif response.status == 400:
                    # User might already exist, try to login
                    pass
                else:
                    print(f"❌ Signup failed with status {response.status}")
            
            # Try to login with existing user
            login_data = {
                "email": "soniox_test@example.com", 
                "password": "testpassword123",
                "remember_me": True
            }
            
            async with self.session.post(f"{BACKEND_URL}/auth/login", json=login_data) as response:
                if response.status == 200:
                    self.authenticated = True
                    print("✅ Authenticated with existing test user")
                    return True
                else:
                    print(f"❌ Login failed with status {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            return False
    
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
    
    async def test_api_key_retrieval(self):
        """Test SCENARIO 1: API Key Retrieval Test"""
        print(f"\n🔑 SCENARIO 1: API Key Retrieval Test")
        print("=" * 60)
        
        try:
            async with self.session.get(f"{BACKEND_URL}/settings/api-keys") as response:
                if response.status == 200:
                    api_keys = await response.json()
                    
                    # Check for Soniox key
                    soniox_key_found = False
                    grok_key_found = False
                    
                    for key in api_keys:
                        if key.get('service_name') == 'soniox':
                            soniox_key_found = True
                        elif key.get('service_name') in ['grok', 'xai']:
                            grok_key_found = True
                    
                    # Log results
                    if soniox_key_found:
                        self.log_result(
                            "Soniox API Key Exists", 
                            True, 
                            "Soniox API key found in user's saved keys"
                        )
                    else:
                        self.log_result(
                            "Soniox API Key Exists", 
                            False, 
                            "No Soniox API key found for user"
                        )
                    
                    if grok_key_found:
                        self.log_result(
                            "Grok API Key Exists", 
                            True, 
                            "Grok API key found in user's saved keys"
                        )
                    else:
                        self.log_result(
                            "Grok API Key Exists", 
                            False, 
                            "No Grok API key found for user"
                        )
                    
                    self.log_result(
                        "API Key Retrieval", 
                        True, 
                        f"Retrieved {len(api_keys)} API keys successfully", 
                        {
                            "total_keys": len(api_keys),
                            "soniox_found": soniox_key_found,
                            "grok_found": grok_key_found,
                            "services": [key.get('service_name') for key in api_keys]
                        }
                    )
                    
                    return soniox_key_found and grok_key_found
                    
                elif response.status == 401:
                    self.log_result("API Key Retrieval", False, "Authentication required - user not logged in")
                    return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "API Key Retrieval", 
                        False, 
                        f"Failed to retrieve API keys - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
                    
        except Exception as e:
            self.log_result("API Key Retrieval", False, f"Error retrieving API keys: {str(e)}")
            return False
    
    async def test_soniox_key_validation(self):
        """Test SCENARIO 2: Soniox API Key Validation Test"""
        print(f"\n🎤 SCENARIO 2: Soniox API Key Validation Test")
        print("=" * 60)
        
        try:
            async with self.session.post(f"{BACKEND_URL}/settings/api-keys/test/soniox") as response:
                if response.status == 200:
                    validation_result = await response.json()
                    is_valid = validation_result.get('valid', False)
                    message = validation_result.get('message', '')
                    error = validation_result.get('error', '')
                    
                    if is_valid:
                        self.log_result(
                            "Soniox API Key Validation", 
                            True, 
                            f"Soniox API key is valid: {message}", 
                            validation_result
                        )
                        return True
                    else:
                        self.log_result(
                            "Soniox API Key Validation", 
                            False, 
                            f"Soniox API key validation failed: {error}", 
                            validation_result
                        )
                        return False
                        
                elif response.status == 404:
                    self.log_result("Soniox API Key Validation", False, "No Soniox API key found to validate")
                    return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Soniox API Key Validation", 
                        False, 
                        f"Validation request failed - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Soniox API Key Validation", False, f"Error validating Soniox key: {str(e)}")
            return False
    
    async def test_grok_key_validation(self):
        """Test Grok API Key Validation"""
        print(f"\n🧠 Testing Grok API Key Validation")
        print("=" * 50)
        
        try:
            async with self.session.post(f"{BACKEND_URL}/settings/api-keys/test/grok") as response:
                if response.status == 200:
                    validation_result = await response.json()
                    is_valid = validation_result.get('valid', False)
                    message = validation_result.get('message', '')
                    error = validation_result.get('error', '')
                    
                    if is_valid:
                        self.log_result(
                            "Grok API Key Validation", 
                            True, 
                            f"Grok API key is valid: {message}", 
                            validation_result
                        )
                        return True
                    else:
                        self.log_result(
                            "Grok API Key Validation", 
                            False, 
                            f"Grok API key validation failed: {error}", 
                            validation_result
                        )
                        return False
                        
                elif response.status == 404:
                    self.log_result("Grok API Key Validation", False, "No Grok API key found to validate")
                    return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Grok API Key Validation", 
                        False, 
                        f"Validation request failed - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Grok API Key Validation", False, f"Error validating Grok key: {str(e)}")
            return False
    
    async def test_agent_configuration(self):
        """Test SCENARIO 3: Agent Configuration Test"""
        print(f"\n⚙️ SCENARIO 3: Agent Configuration Test")
        print("=" * 60)
        
        try:
            # Get all agents
            async with self.session.get(f"{BACKEND_URL}/agents") as response:
                if response.status == 200:
                    agents = await response.json()
                    
                    # Look for agents with Soniox STT + Grok LLM configuration
                    soniox_grok_agents = []
                    
                    for agent in agents:
                        settings = agent.get('settings', {})
                        stt_provider = settings.get('stt_provider')
                        llm_provider = settings.get('llm_provider')
                        tts_provider = settings.get('tts_provider')
                        
                        if stt_provider == 'soniox' and llm_provider == 'grok':
                            soniox_grok_agents.append({
                                'id': agent.get('id'),
                                'name': agent.get('name'),
                                'stt_provider': stt_provider,
                                'llm_provider': llm_provider,
                                'tts_provider': tts_provider
                            })
                    
                    if soniox_grok_agents:
                        self.log_result(
                            "Agent Configuration Check", 
                            True, 
                            f"Found {len(soniox_grok_agents)} agents with Soniox STT + Grok LLM configuration", 
                            {
                                "agents_found": len(soniox_grok_agents),
                                "agent_details": soniox_grok_agents
                            }
                        )
                        return soniox_grok_agents[0]['id']  # Return first agent ID for testing
                    else:
                        # Check if any agents exist at all
                        if agents:
                            agent_configs = []
                            for agent in agents[:3]:  # Show first 3 agents
                                settings = agent.get('settings', {})
                                agent_configs.append({
                                    'name': agent.get('name'),
                                    'stt_provider': settings.get('stt_provider', 'not_set'),
                                    'llm_provider': settings.get('llm_provider', 'not_set'),
                                    'tts_provider': settings.get('tts_provider', 'not_set')
                                })
                            
                            self.log_result(
                                "Agent Configuration Check", 
                                False, 
                                f"No agents found with Soniox STT + Grok LLM configuration. Found {len(agents)} total agents", 
                                {
                                    "total_agents": len(agents),
                                    "sample_configurations": agent_configs
                                }
                            )
                        else:
                            self.log_result(
                                "Agent Configuration Check", 
                                False, 
                                "No agents found in the system"
                            )
                        return None
                        
                elif response.status == 401:
                    self.log_result("Agent Configuration Check", False, "Authentication required - user not logged in")
                    return None
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Agent Configuration Check", 
                        False, 
                        f"Failed to retrieve agents - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return None
                    
        except Exception as e:
            self.log_result("Agent Configuration Check", False, f"Error checking agent configuration: {str(e)}")
            return None
    
    async def test_agent_details(self, agent_id: str):
        """Test detailed agent configuration"""
        print(f"\n🔍 Testing Agent Details for ID: {agent_id}")
        print("=" * 60)
        
        try:
            async with self.session.get(f"{BACKEND_URL}/agents/{agent_id}") as response:
                if response.status == 200:
                    agent = await response.json()
                    settings = agent.get('settings', {})
                    
                    # Check all required fields
                    stt_provider = settings.get('stt_provider')
                    llm_provider = settings.get('llm_provider')
                    tts_provider = settings.get('tts_provider')
                    
                    required_fields = {
                        'stt_provider': stt_provider,
                        'llm_provider': llm_provider,
                        'tts_provider': tts_provider
                    }
                    
                    missing_fields = [field for field, value in required_fields.items() if not value]
                    
                    if not missing_fields:
                        self.log_result(
                            "Agent Required Fields Check", 
                            True, 
                            f"Agent has all required provider fields configured", 
                            {
                                "agent_name": agent.get('name'),
                                "stt_provider": stt_provider,
                                "llm_provider": llm_provider,
                                "tts_provider": tts_provider
                            }
                        )
                        
                        # Verify specific Soniox + Grok configuration
                        if stt_provider == 'soniox' and llm_provider == 'grok':
                            self.log_result(
                                "Soniox + Grok Configuration Verified", 
                                True, 
                                f"Agent correctly configured with Soniox STT and Grok LLM", 
                                {
                                    "agent_name": agent.get('name'),
                                    "agent_id": agent_id,
                                    "configuration": "soniox_stt + grok_llm"
                                }
                            )
                            return True
                        else:
                            self.log_result(
                                "Soniox + Grok Configuration Verified", 
                                False, 
                                f"Agent not configured with Soniox STT + Grok LLM combination", 
                                {
                                    "expected": "stt_provider: soniox, llm_provider: grok",
                                    "actual": f"stt_provider: {stt_provider}, llm_provider: {llm_provider}"
                                }
                            )
                            return False
                    else:
                        self.log_result(
                            "Agent Required Fields Check", 
                            False, 
                            f"Agent missing required provider fields: {missing_fields}", 
                            {
                                "missing_fields": missing_fields,
                                "current_config": required_fields
                            }
                        )
                        return False
                        
                elif response.status == 404:
                    self.log_result("Agent Details Check", False, f"Agent {agent_id} not found")
                    return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Agent Details Check", 
                        False, 
                        f"Failed to retrieve agent details - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Agent Details Check", False, f"Error checking agent details: {str(e)}")
            return False
    
    async def test_simulated_call_flow(self, agent_id: str):
        """Test SCENARIO 4: Simulated Call Flow Test"""
        print(f"\n📞 SCENARIO 4: Simulated Call Flow Test")
        print("=" * 60)
        
        try:
            # Test message processing with the Soniox + Grok agent
            test_message = "Hello, can you help me with my account?"
            request_data = {
                "message": test_message,
                "conversation_history": []
            }
            
            start_time = time.time()
            async with self.session.post(f"{BACKEND_URL}/agents/{agent_id}/process", json=request_data) as response:
                end_time = time.time()
                latency = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check response format
                    has_response = 'response' in data
                    has_latency = 'latency' in data
                    response_text = data.get('response', '')
                    reported_latency = data.get('latency', 0)
                    
                    if has_response and has_latency and response_text:
                        self.log_result(
                            "Soniox + Grok Message Processing", 
                            True, 
                            f"Agent with Soniox STT + Grok LLM responded successfully in {latency:.2f}s", 
                            {
                                "user_message": test_message,
                                "ai_response": response_text[:150] + "..." if len(response_text) > 150 else response_text,
                                "measured_latency": f"{latency:.2f}s",
                                "reported_latency": f"{reported_latency:.2f}s",
                                "response_length": len(response_text),
                                "agent_id": agent_id
                            }
                        )
                        
                        # Test a follow-up message to verify conversation continuity
                        await self.test_follow_up_message(agent_id, test_message, response_text)
                        
                        return True
                    else:
                        self.log_result(
                            "Soniox + Grok Message Processing", 
                            False, 
                            "Invalid response format from Soniox + Grok agent", 
                            {
                                "has_response": has_response,
                                "has_latency": has_latency,
                                "response_empty": not response_text,
                                "full_response": data
                            }
                        )
                        return False
                        
                elif response.status == 404:
                    self.log_result("Soniox + Grok Message Processing", False, f"Agent {agent_id} not found")
                    return False
                elif response.status == 500:
                    error_text = await response.text()
                    # Check for specific error messages mentioned in review request
                    if "No STT provider configured" in error_text:
                        self.log_result(
                            "Soniox + Grok Message Processing", 
                            False, 
                            "❌ No STT provider configured - agent missing stt_provider", 
                            {"error": error_text}
                        )
                    elif "No LLM provider configured" in error_text:
                        self.log_result(
                            "Soniox + Grok Message Processing", 
                            False, 
                            "❌ No LLM provider configured - agent missing llm_provider", 
                            {"error": error_text}
                        )
                    elif "No Soniox API key found" in error_text:
                        self.log_result(
                            "Soniox + Grok Message Processing", 
                            False, 
                            "❌ No Soniox API key found - key not saved or encrypted wrong", 
                            {"error": error_text}
                        )
                    elif "Failed to decrypt key" in error_text:
                        self.log_result(
                            "Soniox + Grok Message Processing", 
                            False, 
                            "❌ Failed to decrypt key - encryption key issues", 
                            {"error": error_text}
                        )
                    else:
                        self.log_result(
                            "Soniox + Grok Message Processing", 
                            False, 
                            f"Server error - Status: {response.status}", 
                            {"error": error_text}
                        )
                    return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Soniox + Grok Message Processing", 
                        False, 
                        f"Processing failed - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Soniox + Grok Message Processing", False, f"Error processing message: {str(e)}")
            return False
    
    async def test_follow_up_message(self, agent_id: str, first_message: str, first_response: str):
        """Test follow-up message to verify conversation continuity"""
        try:
            follow_up_message = "What are the main features of your service?"
            request_data = {
                "message": follow_up_message,
                "conversation_history": [
                    {"role": "user", "content": first_message},
                    {"role": "assistant", "content": first_response}
                ]
            }
            
            start_time = time.time()
            async with self.session.post(f"{BACKEND_URL}/agents/{agent_id}/process", json=request_data) as response:
                end_time = time.time()
                latency = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if response_text and len(response_text) > 20:
                        self.log_result(
                            "Soniox + Grok Follow-up Message", 
                            True, 
                            f"Follow-up message processed successfully in {latency:.2f}s", 
                            {
                                "follow_up_message": follow_up_message,
                                "response_length": len(response_text),
                                "latency": f"{latency:.2f}s",
                                "conversation_continuity": "maintained"
                            }
                        )
                        return True
                    else:
                        self.log_result(
                            "Soniox + Grok Follow-up Message", 
                            False, 
                            "Follow-up response too short or empty", 
                            {"response": response_text}
                        )
                        return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Soniox + Grok Follow-up Message", 
                        False, 
                        f"Follow-up processing failed - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Soniox + Grok Follow-up Message", False, f"Error processing follow-up: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all Soniox + Grok integration tests"""
        print("🚀 Starting Soniox STT + Grok LLM Integration Tests")
        print("=" * 80)
        
        # Check authentication first
        if not self.authenticated:
            print("❌ Authentication failed - cannot run tests")
            return False
        
        # Test 1: API Key Retrieval
        keys_available = await self.test_api_key_retrieval()
        
        # Test 2: API Key Validation
        soniox_valid = await self.test_soniox_key_validation()
        grok_valid = await self.test_grok_key_validation()
        
        # Test 3: Agent Configuration
        agent_id = await self.test_agent_configuration()
        
        # Test 4: Agent Details (if agent found)
        agent_configured = False
        if agent_id:
            agent_configured = await self.test_agent_details(agent_id)
        
        # Test 5: Simulated Call Flow (if agent properly configured)
        call_flow_success = False
        if agent_id and agent_configured:
            call_flow_success = await self.test_simulated_call_flow(agent_id)
        
        # Summary
        print("\n" + "=" * 80)
        print("🏁 SONIOX + GROK INTEGRATION TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Expected Success Indicators
        print(f"\n✅ EXPECTED SUCCESS INDICATORS:")
        print(f"   Soniox key retrieved: {'✅' if keys_available else '❌'}")
        print(f"   Grok key retrieved: {'✅' if keys_available else '❌'}")
        print(f"   Soniox key validates: {'✅' if soniox_valid else '❌'}")
        print(f"   Grok key validates: {'✅' if grok_valid else '❌'}")
        print(f"   Agent properly configured: {'✅' if agent_configured else '❌'}")
        print(f"   Call flow working: {'✅' if call_flow_success else '❌'}")
        
        # Failed tests details
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['message']}")
        
        return passed_tests == total_tests

async def main():
    """Main test execution"""
    async with SonioxGrokTester() as tester:
        success = await tester.run_all_tests()
        return success

if __name__ == "__main__":
    asyncio.run(main())