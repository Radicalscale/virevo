#!/usr/bin/env python3
"""
CRM API ENDPOINTS TESTING
Testing the CRM functionality as requested in the review:

1. Test GET /api/crm/leads - should return empty array initially
2. Test POST /api/crm/leads - create a test lead with specific data
3. Test GET /api/crm/leads/stats - should return stats with 1 lead
4. Test GET /api/crm/qc-config - should return 3 QC agent configs (auto-created)
5. Check if there are any import errors or issues with the CRM router
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

class CRMTestResults:
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
        print(f"CRM API TEST SUMMARY")
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
            print(f"\n✅ ALL CRM API TESTS PASSED!")

class CRMAPITester:
    def __init__(self):
        self.results = CRMTestResults()
        self.user_token = None
        self.user_id = None
        self.test_lead_id = None
        
    async def create_test_user(self) -> tuple:
        """Create a test user and return (user_id, auth_token)"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create unique test user
            test_email = f"crm_test_{uuid.uuid4().hex[:8]}@example.com"
            signup_data = {
                "email": test_email,
                "password": "CRMTest123!",
                "remember_me": True
            }
            
            try:
                response = await client.post(f"{API_BASE}/auth/signup", json=signup_data)
                if response.status_code == 200:
                    # Extract token from Set-Cookie header
                    set_cookie_header = response.headers.get('set-cookie', '')
                    token = None
                    if 'access_token=' in set_cookie_header:
                        token_part = set_cookie_header.split('access_token=')[1].split(';')[0]
                        token = token_part
                    user_data = response.json()
                    user_id = user_data['user']['id']
                    return user_id, token
                elif response.status_code == 400 and "already registered" in response.text:
                    # User exists, try login
                    login_data = {
                        "email": test_email,
                        "password": "CRMTest123!",
                        "remember_me": True
                    }
                    response = await client.post(f"{API_BASE}/auth/login", json=login_data)
                    if response.status_code == 200:
                        set_cookie_header = response.headers.get('set-cookie', '')
                        token = None
                        if 'access_token=' in set_cookie_header:
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
            cookies = {"access_token": self.user_token} if self.user_token else {}
            
            try:
                if method.upper() == "GET":
                    response = await client.get(f"{API_BASE}{endpoint}", cookies=cookies)
                elif method.upper() == "POST":
                    response = await client.post(f"{API_BASE}{endpoint}", cookies=cookies, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(f"{API_BASE}{endpoint}", cookies=cookies, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(f"{API_BASE}{endpoint}", cookies=cookies)
                else:
                    response = await client.request(method, f"{API_BASE}{endpoint}", cookies=cookies, json=data)
                
                return response
            except Exception as e:
                print(f"Request error: {str(e)}")
                return None
    
    async def test_1_get_leads_empty(self):
        """Test 1: GET /api/crm/leads - should return empty array initially"""
        print(f"\n{'='*60}")
        print("TEST 1: GET /api/crm/leads (should be empty initially)")
        print(f"{'='*60}")
        
        response = await self.make_authenticated_request("GET", "/crm/leads")
        
        if not response:
            self.results.add_result("GET /api/crm/leads", False, "No response received")
            return False
        
        if response.status_code == 200:
            leads = response.json()
            if isinstance(leads, list) and len(leads) == 0:
                self.results.add_result("GET /api/crm/leads", True, "Successfully returned empty array")
                return True
            else:
                self.results.add_result("GET /api/crm/leads", False, f"Expected empty array, got: {leads}")
                return False
        else:
            self.results.add_result("GET /api/crm/leads", False, f"Expected 200, got {response.status_code}: {response.text}")
            return False
    
    async def test_2_create_lead(self):
        """Test 2: POST /api/crm/leads - create a test lead with specific data"""
        print(f"\n{'='*60}")
        print("TEST 2: POST /api/crm/leads (create test lead)")
        print(f"{'='*60}")
        
        lead_data = {
            "name": "John Doe",
            "email": "john@test.com",
            "phone": "+1234567890",
            "source": "ad_campaign"
        }
        
        response = await self.make_authenticated_request("POST", "/crm/leads", lead_data)
        
        if not response:
            self.results.add_result("POST /api/crm/leads", False, "No response received")
            return False
        
        if response.status_code == 200:
            lead = response.json()
            # Verify lead data
            if (lead.get("name") == "John Doe" and 
                lead.get("email") == "john@test.com" and 
                lead.get("phone") == "+1234567890" and 
                lead.get("source") == "ad_campaign"):
                
                self.test_lead_id = lead.get("id")
                self.results.add_result("POST /api/crm/leads", True, f"Successfully created lead with ID: {self.test_lead_id}")
                return True
            else:
                self.results.add_result("POST /api/crm/leads", False, f"Lead data mismatch: {lead}")
                return False
        else:
            self.results.add_result("POST /api/crm/leads", False, f"Expected 200, got {response.status_code}: {response.text}")
            return False
    
    async def test_3_get_leads_stats(self):
        """Test 3: GET /api/crm/leads/stats - should return stats with 1 lead"""
        print(f"\n{'='*60}")
        print("TEST 3: GET /api/crm/leads/stats (should show 1 lead)")
        print(f"{'='*60}")
        
        response = await self.make_authenticated_request("GET", "/crm/leads/stats")
        
        if not response:
            self.results.add_result("GET /api/crm/leads/stats", False, "No response received")
            return False
        
        if response.status_code == 200:
            stats = response.json()
            if stats.get("total") == 1:
                self.results.add_result("GET /api/crm/leads/stats", True, f"Successfully returned stats with 1 lead: {stats}")
                return True
            else:
                self.results.add_result("GET /api/crm/leads/stats", False, f"Expected total=1, got: {stats}")
                return False
        else:
            self.results.add_result("GET /api/crm/leads/stats", False, f"Expected 200, got {response.status_code}: {response.text}")
            return False
    
    async def test_4_get_qc_config(self):
        """Test 4: GET /api/crm/qc-config - should return 3 QC agent configs (auto-created)"""
        print(f"\n{'='*60}")
        print("TEST 4: GET /api/crm/qc-config (should auto-create 3 configs)")
        print(f"{'='*60}")
        
        response = await self.make_authenticated_request("GET", "/crm/qc-config")
        
        if not response:
            self.results.add_result("GET /api/crm/qc-config", False, "No response received")
            return False
        
        if response.status_code == 200:
            configs = response.json()
            if isinstance(configs, list) and len(configs) == 3:
                # Verify the 3 expected agent types
                agent_types = [config.get("agent_type") for config in configs]
                expected_types = ["commitment_detector", "conversion_pathfinder", "excellence_replicator"]
                
                if all(agent_type in agent_types for agent_type in expected_types):
                    self.results.add_result("GET /api/crm/qc-config", True, f"Successfully returned 3 QC configs: {agent_types}")
                    return True
                else:
                    self.results.add_result("GET /api/crm/qc-config", False, f"Missing expected agent types. Got: {agent_types}")
                    return False
            else:
                self.results.add_result("GET /api/crm/qc-config", False, f"Expected 3 configs, got {len(configs) if isinstance(configs, list) else 'non-list'}: {configs}")
                return False
        else:
            self.results.add_result("GET /api/crm/qc-config", False, f"Expected 200, got {response.status_code}: {response.text}")
            return False
    
    async def test_5_verify_lead_created(self):
        """Test 5: Verify the lead was actually created by getting leads again"""
        print(f"\n{'='*60}")
        print("TEST 5: Verify lead was created (GET /api/crm/leads again)")
        print(f"{'='*60}")
        
        response = await self.make_authenticated_request("GET", "/crm/leads")
        
        if not response:
            self.results.add_result("Verify Lead Created", False, "No response received")
            return False
        
        if response.status_code == 200:
            leads = response.json()
            if isinstance(leads, list) and len(leads) == 1:
                lead = leads[0]
                if (lead.get("name") == "John Doe" and 
                    lead.get("email") == "john@test.com" and 
                    lead.get("phone") == "+1234567890" and 
                    lead.get("source") == "ad_campaign"):
                    
                    self.results.add_result("Verify Lead Created", True, f"Lead persisted correctly: {lead.get('id')}")
                    return True
                else:
                    self.results.add_result("Verify Lead Created", False, f"Lead data changed: {lead}")
                    return False
            else:
                self.results.add_result("Verify Lead Created", False, f"Expected 1 lead, got {len(leads) if isinstance(leads, list) else 'non-list'}")
                return False
        else:
            self.results.add_result("Verify Lead Created", False, f"Expected 200, got {response.status_code}: {response.text}")
            return False
    
    async def test_6_authentication_required(self):
        """Test 6: Verify all CRM endpoints require authentication"""
        print(f"\n{'='*60}")
        print("TEST 6: Verify authentication is required for CRM endpoints")
        print(f"{'='*60}")
        
        endpoints = [
            ("GET", "/crm/leads"),
            ("POST", "/crm/leads"),
            ("GET", "/crm/leads/stats"),
            ("GET", "/crm/qc-config")
        ]
        
        all_passed = True
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for method, endpoint in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(f"{API_BASE}{endpoint}")
                    elif method == "POST":
                        response = await client.post(f"{API_BASE}{endpoint}", json={})
                    
                    if response.status_code == 401:
                        self.results.add_result(f"Auth Required - {method} {endpoint}", True, "Correctly returned 401 Unauthorized")
                    else:
                        self.results.add_result(f"Auth Required - {method} {endpoint}", False, f"Expected 401, got {response.status_code}")
                        all_passed = False
                        
                except Exception as e:
                    self.results.add_result(f"Auth Required - {method} {endpoint}", False, f"Request failed: {str(e)}")
                    all_passed = False
        
        return all_passed
    
    async def test_7_crm_router_import(self):
        """Test 7: Check if CRM router is properly imported and integrated"""
        print(f"\n{'='*60}")
        print("TEST 7: Check CRM router integration")
        print(f"{'='*60}")
        
        # Test if CRM endpoints are accessible (should get 401 without auth, not 404)
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{API_BASE}/crm/leads")
                
                if response.status_code == 401:
                    self.results.add_result("CRM Router Integration", True, "CRM router is properly integrated (401 Unauthorized)")
                    return True
                elif response.status_code == 404:
                    self.results.add_result("CRM Router Integration", False, "CRM router not found (404 Not Found)")
                    return False
                else:
                    self.results.add_result("CRM Router Integration", True, f"CRM router accessible (got {response.status_code})")
                    return True
                    
            except Exception as e:
                self.results.add_result("CRM Router Integration", False, f"Failed to test CRM router: {str(e)}")
                return False
    
    async def run_comprehensive_crm_test(self):
        """Run all CRM API tests"""
        print(f"\n{'='*80}")
        print("CRM API ENDPOINTS TESTING")
        print(f"Testing Backend URL: {BACKEND_URL}")
        print(f"{'='*80}")
        
        try:
            # First check if CRM router is integrated
            await self.test_7_crm_router_import()
            
            # Test authentication requirements
            await self.test_6_authentication_required()
            
            # Create test user for authenticated tests
            print(f"\nCreating test user for authenticated tests...")
            try:
                self.user_id, self.user_token = await self.create_test_user()
                print(f"✅ Created test user: {self.user_id[:8]}...")
            except Exception as e:
                self.results.add_result("User Creation", False, f"Failed to create test user: {str(e)}")
                self.results.print_summary()
                return self.results
            
            # Run the main CRM tests in sequence
            await self.test_1_get_leads_empty()
            await self.test_2_create_lead()
            await self.test_3_get_leads_stats()
            await self.test_4_get_qc_config()
            await self.test_5_verify_lead_created()
            
        except Exception as e:
            print(f"❌ Critical error during testing: {str(e)}")
            self.results.add_result("Test Execution", False, f"Critical error: {str(e)}")
        
        finally:
            self.results.print_summary()
            return self.results

async def main():
    """Main test execution"""
    tester = CRMAPITester()
    results = await tester.run_comprehensive_crm_test()
    
    # Return exit code based on results
    if results.failed_tests > 0:
        print(f"\n🚨 CRM API ISSUES DETECTED!")
        print(f"   {results.failed_tests} CRM API tests failed.")
        return 1
    else:
        print(f"\n🎉 CRM API TESTING COMPLETE!")
        print(f"   All {results.passed_tests} CRM API tests passed.")
        return 0

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)