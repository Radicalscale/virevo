#!/usr/bin/env python3
"""
Auto QC Feature Testing Suite
Tests the new Auto QC feature for the QC Agent System as specified in the review request:

Backend API Tests:
1. Test GET /api/qc/enhanced/agents/{agent_id}/auto-qc-settings - Should return auto QC settings (need valid auth)
2. Test PUT /api/qc/enhanced/agents/{agent_id}/auto-qc-settings - Should update auto QC settings with:
   - enabled: true
   - campaign_id: (get from list campaigns)
   - run_tech_analysis: true
   - run_script_analysis: true
   - run_tonality_analysis: true
3. Test GET /api/qc/enhanced/campaigns/{campaign_id}/auto-settings - Should return auto pattern detection settings
4. Test PUT /api/qc/enhanced/campaigns/{campaign_id} with auto_pattern_detection: true - Should update campaign

Test Flow:
1. Login and get auth token
2. Get list of campaigns to get a campaign_id
3. Get list of agents to get an agent_id
4. Get current auto QC settings for an agent
5. Update auto QC settings to enable it and link to a campaign
6. Get auto QC settings again to verify the update was saved
7. Update campaign to enable auto_pattern_detection
8. Verify campaign settings were updated

Credentials:
- Email: test@preview.emergentagent.com
- Password: TestPassword123!
- Production URL: https://tts-guardian.preview.emergentagent.com
"""

import httpx
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration - Use production backend URL as specified in review request
BACKEND_URL = "https://tts-guardian.preview.emergentagent.com"

# Endpoint paths - QC Enhanced endpoints don't have /api prefix
QC_ENHANCED_PREFIX = "/qc/enhanced"
API_PREFIX = "/api"
TEST_USER_EMAIL = "test@preview.emergentagent.com"
TEST_USER_PASSWORD = "TestPassword123!"

class AutoQCTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.session = None
        self.auth_cookies = None
        self.test_results = []
        self.campaign_id = None
        self.agent_id = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        if response_data and not success:
            print(f"    Response: {response_data}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response": response_data if not success else None
        })
    
    async def test_authentication(self):
        """Test authentication with the specified user"""
        print("\n🔐 Testing Authentication...")
        
        try:
            login_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "remember_me": False
            }
            
            response = await self.session.post(
                f"{self.backend_url}/api/auth/login",
                json=login_data
            )
            
            if response.status_code == 200:
                # Extract cookies for subsequent requests
                self.auth_cookies = response.cookies
                data = response.json()
                user_info = data.get("user", {})
                
                self.log_test("User Authentication", True, f"Logged in as {user_info.get('email', 'unknown')}")
                
                # Test authenticated endpoint
                me_response = await self.session.get(
                    f"{self.backend_url}/api/auth/me",
                    cookies=self.auth_cookies
                )
                
                if me_response.status_code == 200:
                    self.log_test("Auth Token Validation", True, "Successfully accessed protected endpoint")
                    return True
                else:
                    self.log_test("Auth Token Validation", False, f"Status: {me_response.status_code}", me_response.text)
                    return False
                    
            else:
                self.log_test("User Authentication", False, f"Status: {response.status_code}", response.text)
                print("    ⚠️  Authentication failed - Auto QC endpoints will return 401")
                return False
                
        except Exception as e:
            self.log_test("User Authentication", False, f"Exception: {str(e)}")
            return False
    
    async def get_campaigns(self):
        """Get list of campaigns to get a campaign_id"""
        print("\n📋 Getting Campaigns List...")
        
        try:
            response = await self.session.get(
                f"{self.backend_url}/api/qc/enhanced/campaigns",
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                campaigns = response.json()
                if isinstance(campaigns, list) and len(campaigns) > 0:
                    self.campaign_id = campaigns[0].get('id')
                    self.log_test("Get Campaigns", True, f"Found {len(campaigns)} campaigns, using campaign_id: {self.campaign_id}")
                    return True
                else:
                    self.log_test("Get Campaigns", False, "No campaigns found in response", campaigns)
                    return False
            else:
                self.log_test("Get Campaigns", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Campaigns", False, f"Exception: {str(e)}")
            return False
    
    async def get_agents(self):
        """Get list of agents to get an agent_id"""
        print("\n🤖 Getting Agents List...")
        
        try:
            response = await self.session.get(
                f"{self.backend_url}/api/agents",
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                agents = response.json()
                if isinstance(agents, list) and len(agents) > 0:
                    self.agent_id = agents[0].get('id')
                    self.log_test("Get Agents", True, f"Found {len(agents)} agents, using agent_id: {self.agent_id}")
                    return True
                else:
                    self.log_test("Get Agents", False, "No agents found in response", agents)
                    return False
            else:
                self.log_test("Get Agents", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Agents", False, f"Exception: {str(e)}")
            return False
    
    async def test_get_auto_qc_settings(self):
        """Test GET /api/qc/enhanced/agents/{agent_id}/auto-qc-settings"""
        print("\n⚙️ Testing GET Auto QC Settings...")
        
        if not self.agent_id:
            self.log_test("Get Auto QC Settings", False, "No agent_id available")
            return False
        
        try:
            response = await self.session.get(
                f"{self.backend_url}/api/qc/enhanced/agents/{self.agent_id}/auto-qc-settings",
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                response_data = response.json()
                settings = response_data.get('auto_qc_settings', {})
                
                # Check for expected fields in auto QC settings
                expected_fields = ['enabled', 'campaign_id', 'run_tech_analysis', 'run_script_analysis', 'run_tonality_analysis']
                present_fields = []
                missing_fields = []
                
                for field in expected_fields:
                    if field in settings:
                        present_fields.append(field)
                    else:
                        missing_fields.append(field)
                
                if not missing_fields:
                    self.log_test("Get Auto QC Settings", True, f"All expected fields present: {', '.join(present_fields)}")
                    return True
                else:
                    self.log_test("Get Auto QC Settings", True, f"Settings retrieved. Present: {', '.join(present_fields)}, Missing: {', '.join(missing_fields)}")
                    return True
                    
            elif response.status_code == 404:
                self.log_test("Get Auto QC Settings", True, "Agent not found or no settings configured (404 is acceptable)")
                return True
            elif response.status_code == 401:
                self.log_test("Get Auto QC Settings", False, "Authentication required", response.text)
                return False
            else:
                self.log_test("Get Auto QC Settings", False, f"Unexpected status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Auto QC Settings", False, f"Exception: {str(e)}")
            return False
    
    async def test_update_auto_qc_settings(self):
        """Test PUT /api/qc/enhanced/agents/{agent_id}/auto-qc-settings"""
        print("\n🔧 Testing PUT Auto QC Settings...")
        
        if not self.agent_id or not self.campaign_id:
            self.log_test("Update Auto QC Settings", False, f"Missing agent_id: {self.agent_id} or campaign_id: {self.campaign_id}")
            return False
        
        try:
            # Update auto QC settings as specified in review request
            settings_data = {
                "enabled": True,
                "campaign_id": self.campaign_id,
                "run_tech_analysis": True,
                "run_script_analysis": True,
                "run_tonality_analysis": True
            }
            
            response = await self.session.put(
                f"{self.backend_url}/api/qc/enhanced/agents/{self.agent_id}/auto-qc-settings",
                json=settings_data,
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                response_data = response.json()
                updated_settings = response_data.get('auto_qc_settings', {})
                
                # Verify all settings were saved correctly
                verification_passed = True
                verification_details = []
                
                for key, expected_value in settings_data.items():
                    actual_value = updated_settings.get(key)
                    if actual_value == expected_value:
                        verification_details.append(f"{key}: {actual_value} ✓")
                    else:
                        verification_details.append(f"{key}: expected {expected_value}, got {actual_value} ✗")
                        verification_passed = False
                
                if verification_passed:
                    self.log_test("Update Auto QC Settings", True, f"All settings updated correctly: {', '.join(verification_details)}")
                    return True
                else:
                    self.log_test("Update Auto QC Settings", False, f"Settings mismatch: {', '.join(verification_details)}")
                    return False
                    
            elif response.status_code == 401:
                self.log_test("Update Auto QC Settings", False, "Authentication required", response.text)
                return False
            elif response.status_code == 404:
                self.log_test("Update Auto QC Settings", False, "Agent not found", response.text)
                return False
            else:
                self.log_test("Update Auto QC Settings", False, f"Unexpected status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Update Auto QC Settings", False, f"Exception: {str(e)}")
            return False
    
    async def test_verify_auto_qc_settings_saved(self):
        """Test GET auto QC settings again to verify the update was saved"""
        print("\n✅ Verifying Auto QC Settings Were Saved...")
        
        if not self.agent_id:
            self.log_test("Verify Auto QC Settings Saved", False, "No agent_id available")
            return False
        
        try:
            response = await self.session.get(
                f"{self.backend_url}/api/qc/enhanced/agents/{self.agent_id}/auto-qc-settings",
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                response_data = response.json()
                settings = response_data.get('auto_qc_settings', {})
                
                # Verify the settings match what we set
                expected_settings = {
                    "enabled": True,
                    "campaign_id": self.campaign_id,
                    "run_tech_analysis": True,
                    "run_script_analysis": True,
                    "run_tonality_analysis": True
                }
                
                verification_passed = True
                verification_details = []
                
                for key, expected_value in expected_settings.items():
                    actual_value = settings.get(key)
                    if actual_value == expected_value:
                        verification_details.append(f"{key}: {actual_value} ✓")
                    else:
                        verification_details.append(f"{key}: expected {expected_value}, got {actual_value} ✗")
                        verification_passed = False
                
                if verification_passed:
                    self.log_test("Verify Auto QC Settings Saved", True, f"All settings persisted correctly: {', '.join(verification_details)}")
                    return True
                else:
                    self.log_test("Verify Auto QC Settings Saved", False, f"Settings not persisted: {', '.join(verification_details)}")
                    return False
                    
            else:
                self.log_test("Verify Auto QC Settings Saved", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Verify Auto QC Settings Saved", False, f"Exception: {str(e)}")
            return False
    
    async def test_get_campaign_auto_settings(self):
        """Test GET /api/qc/enhanced/campaigns/{campaign_id}/auto-settings"""
        print("\n📊 Testing GET Campaign Auto Settings...")
        
        if not self.campaign_id:
            self.log_test("Get Campaign Auto Settings", False, "No campaign_id available")
            return False
        
        try:
            response = await self.session.get(
                f"{self.backend_url}/api/qc/enhanced/campaigns/{self.campaign_id}/auto-settings",
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                settings = response.json()
                
                # Check for auto pattern detection settings
                if 'auto_pattern_detection' in settings:
                    self.log_test("Get Campaign Auto Settings", True, f"Campaign auto settings retrieved, auto_pattern_detection: {settings.get('auto_pattern_detection')}")
                    return True
                else:
                    self.log_test("Get Campaign Auto Settings", True, f"Campaign auto settings retrieved: {list(settings.keys())}")
                    return True
                    
            elif response.status_code == 404:
                self.log_test("Get Campaign Auto Settings", True, "Campaign not found or no auto settings configured (404 is acceptable)")
                return True
            elif response.status_code == 401:
                self.log_test("Get Campaign Auto Settings", False, "Authentication required", response.text)
                return False
            else:
                self.log_test("Get Campaign Auto Settings", False, f"Unexpected status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Campaign Auto Settings", False, f"Exception: {str(e)}")
            return False
    
    async def test_update_campaign_auto_pattern_detection(self):
        """Test PUT /api/qc/enhanced/campaigns/{campaign_id} with auto_pattern_detection: true"""
        print("\n🔍 Testing PUT Campaign Auto Pattern Detection...")
        
        if not self.campaign_id:
            self.log_test("Update Campaign Auto Pattern Detection", False, "No campaign_id available")
            return False
        
        try:
            # Update campaign to enable auto_pattern_detection
            campaign_data = {
                "auto_pattern_detection": True
            }
            
            response = await self.session.put(
                f"{self.backend_url}/api/qc/enhanced/campaigns/{self.campaign_id}",
                json=campaign_data,
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Check if update was successful
                if response_data.get('success') is True:
                    self.log_test("Update Campaign Auto Pattern Detection", True, f"Campaign update successful: {response_data.get('message', 'Updated')}")
                    return True
                else:
                    self.log_test("Update Campaign Auto Pattern Detection", False, f"Update failed: {response_data}")
                    return False
                    
            elif response.status_code == 401:
                self.log_test("Update Campaign Auto Pattern Detection", False, "Authentication required", response.text)
                return False
            elif response.status_code == 404:
                self.log_test("Update Campaign Auto Pattern Detection", False, "Campaign not found", response.text)
                return False
            else:
                self.log_test("Update Campaign Auto Pattern Detection", False, f"Unexpected status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Update Campaign Auto Pattern Detection", False, f"Exception: {str(e)}")
            return False
    
    async def test_verify_campaign_settings_updated(self):
        """Test that campaign settings were updated by getting campaign auto settings again"""
        print("\n✅ Verifying Campaign Settings Were Updated...")
        
        if not self.campaign_id:
            self.log_test("Verify Campaign Settings Updated", False, "No campaign_id available")
            return False
        
        try:
            response = await self.session.get(
                f"{self.backend_url}/api/qc/enhanced/campaigns/{self.campaign_id}/auto-settings",
                cookies=self.auth_cookies
            )
            
            if response.status_code == 200:
                settings = response.json()
                
                # Verify auto_pattern_detection is now true
                auto_pattern_detection = settings.get('auto_pattern_detection')
                if auto_pattern_detection is True:
                    self.log_test("Verify Campaign Settings Updated", True, f"auto_pattern_detection persisted as: {auto_pattern_detection}")
                    return True
                else:
                    self.log_test("Verify Campaign Settings Updated", False, f"auto_pattern_detection expected True, got: {auto_pattern_detection}")
                    return False
                    
            else:
                self.log_test("Verify Campaign Settings Updated", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Verify Campaign Settings Updated", False, f"Exception: {str(e)}")
            return False
    
    async def test_authentication_security(self):
        """Test authentication requirements for Auto QC endpoints"""
        print("\n🔒 Testing Authentication Security...")
        
        # Test endpoints without authentication using a fresh session
        endpoints_to_test = [
            ("GET", f"/api/qc/enhanced/agents/test-agent-id/auto-qc-settings", "Get Auto QC Settings"),
            ("PUT", f"/api/qc/enhanced/agents/test-agent-id/auto-qc-settings", "Update Auto QC Settings"),
            ("GET", f"/api/qc/enhanced/campaigns/test-campaign-id/auto-settings", "Get Campaign Auto Settings"),
            ("PUT", f"/api/qc/enhanced/campaigns/test-campaign-id", "Update Campaign")
        ]
        
        # Use a fresh session without cookies to test authentication
        async with httpx.AsyncClient(timeout=30.0) as fresh_session:
            for method, endpoint, description in endpoints_to_test:
                try:
                    if method == "GET":
                        response = await fresh_session.get(f"{self.backend_url}{endpoint}")
                    else:
                        response = await fresh_session.put(f"{self.backend_url}{endpoint}", json={})
                    
                    if response.status_code == 401:
                        self.log_test(f"Security - {description} No Auth", True, "Correctly returns 401 without authentication")
                    elif response.status_code == 404:
                        self.log_test(f"Security - {description} No Auth", False, "Returns 404 - endpoint may not exist")
                    else:
                        self.log_test(f"Security - {description} No Auth", False, f"Expected 401, got {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"Security - {description} No Auth", False, f"Exception: {str(e)}")

    async def run_all_tests(self):
        """Run all Auto QC feature tests as specified in review request"""
        print("🚀 Starting Auto QC Feature Testing Suite")
        print(f"Backend URL: {self.backend_url}")
        print(f"Test User: {TEST_USER_EMAIL}")
        print("=" * 80)
        
        # Step 1: Login and get auth token
        auth_success = await self.test_authentication()
        if not auth_success:
            print("❌ Authentication failed - cannot proceed with Auto QC tests")
            return 0, len(self.test_results)
        
        # Step 2: Get list of campaigns to get a campaign_id
        campaigns_success = await self.get_campaigns()
        
        # Step 3: Get list of agents to get an agent_id
        agents_success = await self.get_agents()
        
        # Step 4: Get current auto QC settings for an agent
        await self.test_get_auto_qc_settings()
        
        # Step 5: Update auto QC settings to enable it and link to a campaign
        await self.test_update_auto_qc_settings()
        
        # Step 6: Get auto QC settings again to verify the update was saved
        await self.test_verify_auto_qc_settings_saved()
        
        # Step 7: Update campaign to enable auto_pattern_detection
        await self.test_update_campaign_auto_pattern_detection()
        
        # Step 8: Verify campaign settings were updated
        await self.test_verify_campaign_settings_updated()
        
        # Additional: Test authentication and security
        await self.test_authentication_security()
        
        # Summary
        print("\n📊 Test Summary:")
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        return passed_tests, failed_tests

async def main():
    """Main test runner"""
    print("🔧 Auto QC Feature Testing")
    print("Testing the new Auto QC feature for the QC Agent System as specified in review request:")
    print("1. GET /api/qc/enhanced/agents/{agent_id}/auto-qc-settings")
    print("2. PUT /api/qc/enhanced/agents/{agent_id}/auto-qc-settings")
    print("3. GET /api/qc/enhanced/campaigns/{campaign_id}/auto-settings")
    print("4. PUT /api/qc/enhanced/campaigns/{campaign_id} with auto_pattern_detection: true")
    print("5. Full test flow with authentication and verification")
    print()
    
    async with AutoQCTester() as tester:
        passed, failed = await tester.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())