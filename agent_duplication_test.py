#!/usr/bin/env python3
"""
AGENT DUPLICATION FEATURE TESTING
Testing the newly implemented agent duplication functionality.

This test verifies:
1. Agent duplication endpoint functionality
2. Proper data copying (settings, call flows, etc.)
3. Name modification with "-copy" suffix
4. Stats reset to defaults
5. Authentication and ownership validation
6. Error handling for non-existent agents
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
import uuid

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://voice-ai-perf.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class AgentDuplicationTestResults:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.results = []
        
    def add_result(self, test_name: str, passed: bool, details: str):
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        result = f"{status}: {test_name} - {details}"
        self.results.append(result)
        print(result)
        
    def print_summary(self):
        print(f"\n{'='*80}")
        print(f"AGENT DUPLICATION TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")
        print(f"{'='*80}")
        
        if self.failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if "❌ FAIL" in result:
                    print(f"  {result}")
        else:
            print(f"\n✅ ALL AGENT DUPLICATION TESTS PASSED!")

class AgentDuplicationTester:
    def __init__(self):
        self.results = AgentDuplicationTestResults()
        self.user_token = None
        self.user_id = None
        self.test_agent_id = None
        self.duplicated_agent_id = None
        
    async def create_test_user(self, email: str, password: str) -> tuple:
        """Create a test user and return (user_id, auth_token)"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to create user
            signup_data = {
                "email": email,
                "password": password,
                "remember_me": True
            }
            
            try:
                response = await client.post(f"{API_BASE}/auth/signup", json=signup_data)
                if response.status_code == 200:
                    # Extract token from Set-Cookie header manually
                    set_cookie_header = response.headers.get('set-cookie', '')
                    token = None
                    if 'access_token=' in set_cookie_header:
                        # Extract token value from set-cookie header
                        token_part = set_cookie_header.split('access_token=')[1].split(';')[0]
                        token = token_part
                    user_data = response.json()
                    user_id = user_data['user']['id']
                    return user_id, token
                elif response.status_code == 400 and "already registered" in response.text:
                    # User exists, try login
                    login_data = {
                        "email": email,
                        "password": password,
                        "remember_me": True
                    }
                    response = await client.post(f"{API_BASE}/auth/login", json=login_data)
                    if response.status_code == 200:
                        # Extract token from Set-Cookie header manually
                        set_cookie_header = response.headers.get('set-cookie', '')
                        token = None
                        if 'access_token=' in set_cookie_header:
                            # Extract token value from set-cookie header
                            token_part = set_cookie_header.split('access_token=')[1].split(';')[0]
                            token = token_part
                        user_data = response.json()
                        user_id = user_data['user']['id']
                        return user_id, token
                    else:
                        raise Exception(f"Login failed: {response.status_code} - {response.text}")
                else:
                    raise Exception(f"Signup failed: {response.status_code} - {response.text}")
            except Exception as e:
                raise Exception(f"User creation failed: {str(e)}")
    
    async def make_authenticated_request(self, method: str, endpoint: str, data: dict = None):
        """Make authenticated request with user token"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {}
            cookies = {"access_token": self.user_token} if self.user_token else {}
            
            try:
                if method.upper() == "GET":
                    response = await client.get(f"{API_BASE}{endpoint}", cookies=cookies, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(f"{API_BASE}{endpoint}", cookies=cookies, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(f"{API_BASE}{endpoint}", cookies=cookies, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(f"{API_BASE}{endpoint}", cookies=cookies, headers=headers, json=data)
                else:
                    response = await client.request(method, f"{API_BASE}{endpoint}", cookies=cookies, headers=headers, json=data)
                
                return response
            except Exception as e:
                print(f"Request error: {str(e)}")
                return None
    
    async def setup_test_user(self):
        """Create a test user for the duplication tests"""
        print(f"\n{'='*60}")
        print("SETUP: Creating Test User")
        print(f"{'='*60}")
        
        try:
            user_email = f"agent_dup_test_{uuid.uuid4().hex[:8]}@example.com"
            self.user_id, self.user_token = await self.create_test_user(user_email, "SecurePass123!")
            
            print(f"✅ Created Test User: {self.user_id[:8]}...")
            self.results.add_result("Test User Creation", True, f"User ID: {self.user_id[:8]}...")
            
        except Exception as e:
            self.results.add_result("Test User Creation", False, f"Failed: {str(e)}")
            return False
        
        return True
    
    async def create_test_agent(self):
        """Create a test agent with some configuration for duplication testing"""
        print(f"\nCreating test agent with configuration...")
        
        # Create agent with basic configuration
        agent_data = {
            "name": "Test Agent for Duplication",
            "description": "This is a test agent with various configurations for duplication testing",
            "voice": "Rachel",
            "language": "en",
            "llm_provider": "openai",
            "llm_model": "gpt-4-turbo",
            "stt_provider": "deepgram",
            "tts_provider": "elevenlabs",
            "system_prompt": "You are a helpful AI assistant for testing purposes. Always be polite and professional.",
            "first_message": "Hello! I'm a test agent. How can I help you today?",
            "interruption_threshold": 150,
            "response_delay": 800
        }
        
        response = await self.make_authenticated_request("POST", "/agents", agent_data)
        
        if response and response.status_code == 200:
            agent = response.json()
            self.test_agent_id = agent['id']
            self.results.add_result(
                "Test Agent Creation",
                True,
                f"Created agent '{agent['name']}' with ID: {self.test_agent_id[:8]}..."
            )
            return agent
        else:
            error_details = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_body = response.text
                    error_details += f", Body: {error_body}"
                except:
                    pass
            self.results.add_result(
                "Test Agent Creation",
                False,
                f"Failed to create agent: {error_details}"
            )
            return None
    
    async def test_agent_duplication_success(self, original_agent):
        """Test successful agent duplication"""
        print(f"\nTesting agent duplication...")
        
        response = await self.make_authenticated_request("POST", f"/agents/{self.test_agent_id}/duplicate")
        
        if not response:
            self.results.add_result("Agent Duplication Request", False, "No response received")
            return None
        
        if response.status_code != 200:
            self.results.add_result(
                "Agent Duplication Request", 
                False, 
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            return None
        
        self.results.add_result("Agent Duplication Request", True, "Successfully duplicated agent")
        
        try:
            duplicated_agent = response.json()
            self.duplicated_agent_id = duplicated_agent['id']
            
            # Test 1: Different ID (new UUID)
            if duplicated_agent['id'] != original_agent['id']:
                self.results.add_result(
                    "Different Agent ID",
                    True,
                    f"Original: {original_agent['id'][:8]}..., Duplicate: {duplicated_agent['id'][:8]}..."
                )
            else:
                self.results.add_result("Different Agent ID", False, "IDs are the same")
            
            # Test 2: Name with "-copy" suffix
            expected_name = f"{original_agent['name']}-copy"
            if duplicated_agent['name'] == expected_name:
                self.results.add_result(
                    "Name with -copy Suffix",
                    True,
                    f"Name correctly changed to: '{duplicated_agent['name']}'"
                )
            else:
                self.results.add_result(
                    "Name with -copy Suffix",
                    False,
                    f"Expected '{expected_name}', got '{duplicated_agent['name']}'"
                )
            
            # Test 3: Same settings as original
            settings_to_check = [
                'description', 'voice', 'language', 'llm_provider', 'llm_model',
                'stt_provider', 'tts_provider', 'system_prompt', 'first_message',
                'interruption_threshold', 'response_delay'
            ]
            
            settings_match = True
            mismatched_settings = []
            
            for setting in settings_to_check:
                if setting in original_agent and setting in duplicated_agent:
                    if original_agent[setting] != duplicated_agent[setting]:
                        settings_match = False
                        mismatched_settings.append(f"{setting}: '{original_agent[setting]}' vs '{duplicated_agent[setting]}'")
            
            if settings_match:
                self.results.add_result(
                    "Settings Preservation",
                    True,
                    f"All {len(settings_to_check)} settings correctly copied"
                )
            else:
                self.results.add_result(
                    "Settings Preservation",
                    False,
                    f"Mismatched settings: {', '.join(mismatched_settings)}"
                )
            
            # Test 4: Same call_flow as original
            original_flow = original_agent.get('call_flow', [])
            duplicated_flow = duplicated_agent.get('call_flow', [])
            
            if original_flow == duplicated_flow:
                self.results.add_result(
                    "Call Flow Preservation",
                    True,
                    f"Call flow correctly copied ({len(original_flow)} nodes)"
                )
            else:
                self.results.add_result(
                    "Call Flow Preservation",
                    False,
                    f"Call flows don't match. Original: {len(original_flow)} nodes, Duplicate: {len(duplicated_flow)} nodes"
                )
            
            # Test 5: Reset stats to defaults
            expected_stats = {
                'calls_handled': 0,
                'avg_latency': 0.0,
                'success_rate': 0.0
            }
            
            duplicated_stats = duplicated_agent.get('stats', {})
            stats_reset = True
            stats_issues = []
            
            for stat_key, expected_value in expected_stats.items():
                if duplicated_stats.get(stat_key) != expected_value:
                    stats_reset = False
                    stats_issues.append(f"{stat_key}: expected {expected_value}, got {duplicated_stats.get(stat_key)}")
            
            if stats_reset:
                self.results.add_result(
                    "Stats Reset to Defaults",
                    True,
                    "All stats correctly reset to 0"
                )
            else:
                self.results.add_result(
                    "Stats Reset to Defaults",
                    False,
                    f"Stats not properly reset: {', '.join(stats_issues)}"
                )
            
            return duplicated_agent
            
        except Exception as e:
            self.results.add_result("Agent Duplication Response Parsing", False, f"Error parsing response: {str(e)}")
            return None
    
    async def test_duplicated_agent_in_list(self):
        """Test that the duplicated agent appears in the agents list"""
        print(f"\nTesting duplicated agent appears in agents list...")
        
        response = await self.make_authenticated_request("GET", "/agents")
        
        if not response or response.status_code != 200:
            self.results.add_result(
                "Agents List Retrieval",
                False,
                f"Failed to get agents list: {response.status_code if response else 'No response'}"
            )
            return
        
        try:
            agents = response.json()
            
            # Find both original and duplicated agents
            original_found = False
            duplicate_found = False
            
            for agent in agents:
                if agent['id'] == self.test_agent_id:
                    original_found = True
                elif agent['id'] == self.duplicated_agent_id:
                    duplicate_found = True
            
            if original_found and duplicate_found:
                self.results.add_result(
                    "Duplicated Agent in List",
                    True,
                    f"Both original and duplicated agents found in list ({len(agents)} total agents)"
                )
            elif duplicate_found:
                self.results.add_result(
                    "Duplicated Agent in List",
                    True,
                    "Duplicated agent found in list (original may have been deleted)"
                )
            else:
                self.results.add_result(
                    "Duplicated Agent in List",
                    False,
                    f"Duplicated agent not found in list. Original found: {original_found}"
                )
                
        except Exception as e:
            self.results.add_result("Duplicated Agent in List", False, f"Error parsing agents list: {str(e)}")
    
    async def test_duplicate_nonexistent_agent(self):
        """Test error handling when trying to duplicate a non-existent agent"""
        print(f"\nTesting duplication of non-existent agent...")
        
        fake_agent_id = str(uuid.uuid4())
        response = await self.make_authenticated_request("POST", f"/agents/{fake_agent_id}/duplicate")
        
        if response and response.status_code == 404:
            self.results.add_result(
                "Non-existent Agent Duplication",
                True,
                "Correctly returned 404 for non-existent agent"
            )
        else:
            self.results.add_result(
                "Non-existent Agent Duplication",
                False,
                f"Expected 404, got {response.status_code if response else 'No response'}"
            )
    
    async def test_authentication_required(self):
        """Test that authentication is required for duplication"""
        print(f"\nTesting authentication requirement...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{API_BASE}/agents/{self.test_agent_id}/duplicate")
                
                if response.status_code == 401:
                    self.results.add_result(
                        "Authentication Required",
                        True,
                        "Correctly returned 401 Unauthorized without authentication"
                    )
                else:
                    self.results.add_result(
                        "Authentication Required",
                        False,
                        f"Expected 401, got {response.status_code}"
                    )
            except Exception as e:
                self.results.add_result(
                    "Authentication Required",
                    False,
                    f"Request failed: {str(e)}"
                )
    
    async def test_user_ownership_validation(self):
        """Test that users can only duplicate their own agents"""
        print(f"\nTesting user ownership validation...")
        
        # Create a second user
        try:
            user2_email = f"agent_dup_test2_{uuid.uuid4().hex[:8]}@example.com"
            user2_id, user2_token = await self.create_test_user(user2_email, "SecurePass123!")
            
            # Try to duplicate the first user's agent with second user's token
            async with httpx.AsyncClient(timeout=30.0) as client:
                cookies = {"access_token": user2_token}
                response = await client.post(f"{API_BASE}/agents/{self.test_agent_id}/duplicate", cookies=cookies)
                
                if response.status_code == 404:
                    self.results.add_result(
                        "User Ownership Validation",
                        True,
                        "Correctly returned 404 when trying to duplicate another user's agent"
                    )
                else:
                    self.results.add_result(
                        "User Ownership Validation",
                        False,
                        f"Expected 404, got {response.status_code}: {response.text}"
                    )
                    
        except Exception as e:
            self.results.add_result(
                "User Ownership Validation",
                False,
                f"Failed to test ownership validation: {str(e)}"
            )
    
    async def cleanup_test_data(self):
        """Clean up test agents"""
        print(f"\nCleaning up test data...")
        
        agents_to_delete = [self.test_agent_id, self.duplicated_agent_id]
        
        for agent_id in agents_to_delete:
            if agent_id:
                response = await self.make_authenticated_request("DELETE", f"/agents/{agent_id}")
                if response and response.status_code == 200:
                    print(f"✅ Deleted agent: {agent_id[:8]}...")
                else:
                    print(f"⚠️ Failed to delete agent: {agent_id[:8]}...")
    
    async def run_comprehensive_duplication_test(self):
        """Run all agent duplication test phases"""
        print(f"\n{'='*80}")
        print("AGENT DUPLICATION FEATURE TESTING")
        print(f"Testing Backend URL: {BACKEND_URL}")
        print(f"{'='*80}")
        
        try:
            # Setup
            if not await self.setup_test_user():
                return self.results
            
            # Create test agent
            original_agent = await self.create_test_agent()
            if not original_agent:
                return self.results
            
            # Test duplication functionality
            duplicated_agent = await self.test_agent_duplication_success(original_agent)
            
            if duplicated_agent:
                # Test that duplicated agent appears in list
                await self.test_duplicated_agent_in_list()
            
            # Test error handling
            await self.test_duplicate_nonexistent_agent()
            await self.test_authentication_required()
            await self.test_user_ownership_validation()
            
            # Cleanup
            await self.cleanup_test_data()
            
        except Exception as e:
            print(f"❌ Critical error during testing: {str(e)}")
            self.results.add_result("Test Execution", False, f"Critical error: {str(e)}")
        
        finally:
            self.results.print_summary()
            return self.results

async def main():
    """Main test execution"""
    tester = AgentDuplicationTester()
    results = await tester.run_comprehensive_duplication_test()
    
    # Return exit code based on results
    if results.failed_tests > 0:
        print(f"\n🚨 AGENT DUPLICATION TESTS FAILED!")
        print(f"   {results.failed_tests} tests failed out of {results.total_tests}.")
        return 1
    else:
        print(f"\n🎉 AGENT DUPLICATION TESTS PASSED!")
        print(f"   All {results.passed_tests} tests passed successfully.")
        return 0

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)