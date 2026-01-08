#!/usr/bin/env python3
"""
Post-Call Automation QC and CRM Functionality Testing Script

Tests the Post-Call Automation fix for QC and CRM functionality as specified in the review request:
1. Debug Endpoint Basic Functionality - POST /api/debug/test-post-call-automation/{call_id}
2. QC Automation Verification - Check MongoDB for auto_analyzed, tech_qc_results, script_qc_results, tonality_qc_results
3. CRM Lead Verification - Check MongoDB for lead updates
4. Call Without Auto-QC Enabled - Test with different call_id

Backend URL: From REACT_APP_BACKEND_URL environment variable
Auth: Login as kendrickbowman9@gmail.com / B!LL10n$$
Database: test_database in MongoDB
"""

import asyncio
import httpx
import json
import sys
import os
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://voice-overlap-debug.preview.emergentagent.com')
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = "test_database"

# Test credentials and data
TEST_EMAIL = "kendrickbowman9@gmail.com"
TEST_PASSWORD = "B!LL10n$$"

# Test call IDs from review request
CALL_ID_WITH_QC = "v3:Igz2lQ_-bloUgpjkG4Tz5WlivVCPFk5s_3ONVBRKV286vGhLBbUuhw"
CALL_ID_WITHOUT_QC = "v3:q3mKpHEA6WwfpwWPQLWaMQX3vq8JNyUz1ZSzV7ZsanzFMFatBp0jCg"
CAMPAIGN_ID = "b7bd9ce7-2722-4c61-a2fc-ca1fb127d7b8"
PHONE_NUMBER = "+17708336397"

class PostCallAutomationTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.auth_cookies = None
        self.mongo_client = None
        self.db = None
        
    def log_result(self, test_name: str, status: str, details: str = "", expected: Any = None, actual: Any = None):
        """Log test result"""
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
            
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "expected": expected,
            "actual": actual,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        # Print result
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            print(f"   {details}")
        if expected is not None and actual is not None:
            print(f"   Expected: {expected}, Got: {actual}")
        print()

    async def setup_mongodb_connection(self):
        """Setup MongoDB connection"""
        try:
            if not MONGO_URL:
                self.log_result("MongoDB Setup", "FAIL", "MONGO_URL environment variable not set")
                return False
                
            self.mongo_client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.mongo_client[DB_NAME]
            
            # Test connection
            await self.db.command("ping")
            self.log_result("MongoDB Setup", "PASS", f"Connected to MongoDB database: {DB_NAME}")
            return True
            
        except Exception as e:
            self.log_result("MongoDB Setup", "FAIL", f"Failed to connect to MongoDB: {str(e)}")
            return False

    async def authenticate(self):
        """Authenticate with the backend"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                login_data = {
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "remember_me": False
                }
                
                response = await client.post(
                    f"{self.backend_url}/api/auth/login",
                    json=login_data
                )
                
                if response.status_code == 200:
                    # Extract cookies from response
                    self.auth_cookies = response.cookies
                    self.log_result(
                        "Authentication", 
                        "PASS", 
                        f"Successfully authenticated as {TEST_EMAIL}",
                        200,
                        response.status_code
                    )
                    return True
                else:
                    self.log_result(
                        "Authentication", 
                        "FAIL", 
                        f"Authentication failed: {response.text}",
                        200,
                        response.status_code
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Authentication", "FAIL", f"Exception during authentication: {str(e)}")
            return False

    async def test_debug_endpoint_with_qc(self):
        """Test 1: Debug Endpoint Basic Functionality with QC enabled call"""
        try:
            # URL encode the call_id (colon needs to be encoded)
            encoded_call_id = urllib.parse.quote(CALL_ID_WITH_QC, safe='')
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/debug/test-post-call-automation/{encoded_call_id}",
                    cookies=self.auth_cookies
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # The endpoint returns steps as an array, not individual keys
                    steps = data.get("steps", [])
                    step_names = [step.get("step") for step in steps]
                    
                    # Verify response contains all required steps
                    required_steps = ["find_call", "check_agent_qc_settings", "trigger_campaign_qc", "trigger_crm_update"]
                    missing_steps = []
                    
                    for step in required_steps:
                        if step not in step_names:
                            missing_steps.append(step)
                    
                    # Check if status is success
                    status_ok = data.get("status") == "success"
                    
                    if not missing_steps and status_ok:
                        self.log_result(
                            "Debug Endpoint - QC Enabled Call", 
                            "PASS", 
                            f"All required steps present: {step_names}, Status: {data.get('status')}",
                            "success",
                            data.get("status")
                        )
                        return data
                    else:
                        issues = []
                        if missing_steps:
                            issues.append(f"Missing steps: {missing_steps}")
                        if not status_ok:
                            issues.append(f"Status not success: {data.get('status')}")
                        
                        self.log_result(
                            "Debug Endpoint - QC Enabled Call", 
                            "FAIL", 
                            f"Issues found: {'; '.join(issues)}. Steps found: {step_names}",
                            "All steps + success status",
                            f"Missing: {missing_steps}, Status: {data.get('status')}"
                        )
                        return None
                else:
                    self.log_result(
                        "Debug Endpoint - QC Enabled Call", 
                        "FAIL", 
                        f"HTTP error: {response.text}",
                        200,
                        response.status_code
                    )
                    return None
                    
        except Exception as e:
            self.log_result("Debug Endpoint - QC Enabled Call", "FAIL", f"Exception: {str(e)}")
            return None

    async def test_qc_automation_verification(self):
        """Test 2: QC Automation Verification in MongoDB"""
        try:
            if self.db is None:
                self.log_result("QC Automation Verification", "FAIL", "MongoDB connection not available")
                return False
                
            # Query MongoDB for the campaign call
            campaign_call = await self.db.campaign_calls.find_one({
                "call_id": CALL_ID_WITH_QC,
                "campaign_id": CAMPAIGN_ID
            })
            
            if not campaign_call:
                self.log_result(
                    "QC Automation Verification", 
                    "FAIL", 
                    f"Campaign call not found in MongoDB for call_id: {CALL_ID_WITH_QC}, campaign_id: {CAMPAIGN_ID}"
                )
                return False
            
            # Verify required fields
            issues = []
            
            # Check auto_analyzed
            if not campaign_call.get("auto_analyzed"):
                issues.append("auto_analyzed is not true")
            
            # Check tech_qc_results
            tech_qc = campaign_call.get("tech_qc_results")
            if not tech_qc or not tech_qc.get("overall_performance"):
                issues.append("tech_qc_results missing or no overall_performance")
            
            # Check script_qc_results
            script_qc = campaign_call.get("script_qc_results")
            if not script_qc or not script_qc.get("node_analyses"):
                issues.append("script_qc_results missing or no node_analyses array")
            
            # Check tonality_qc_results
            tonality_qc = campaign_call.get("tonality_qc_results")
            if not tonality_qc or not tonality_qc.get("node_analyses"):
                issues.append("tonality_qc_results missing or no node_analyses array")
            
            if not issues:
                self.log_result(
                    "QC Automation Verification", 
                    "PASS", 
                    f"All QC fields verified: auto_analyzed={campaign_call.get('auto_analyzed')}, "
                    f"tech_qc has overall_performance, script_qc has {len(script_qc.get('node_analyses', []))} analyses, "
                    f"tonality_qc has {len(tonality_qc.get('node_analyses', []))} analyses"
                )
                return True
            else:
                self.log_result(
                    "QC Automation Verification", 
                    "FAIL", 
                    f"QC verification issues: {'; '.join(issues)}"
                )
                return False
                
        except Exception as e:
            self.log_result("QC Automation Verification", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_crm_lead_verification(self):
        """Test 3: CRM Lead Verification in MongoDB"""
        try:
            if self.db is None:
                self.log_result("CRM Lead Verification", "FAIL", "MongoDB connection not available")
                return False
                
            # Query MongoDB for the lead
            lead = await self.db.leads.find_one({
                "phone": PHONE_NUMBER
            })
            
            if not lead:
                self.log_result(
                    "CRM Lead Verification", 
                    "FAIL", 
                    f"Lead not found in MongoDB for phone: {PHONE_NUMBER}"
                )
                return False
            
            # Verify required fields
            issues = []
            
            # Check total_calls > 0
            total_calls = lead.get("total_calls", 0)
            if total_calls <= 0:
                issues.append(f"total_calls is {total_calls}, should be > 0")
            
            # Check last_contact is recent (within last 24 hours for this test)
            last_contact = lead.get("last_contact")
            if not last_contact:
                issues.append("last_contact is missing")
            else:
                # Check if it's a recent timestamp (basic check)
                if isinstance(last_contact, str):
                    try:
                        from datetime import datetime, timedelta
                        last_contact_dt = datetime.fromisoformat(last_contact.replace('Z', '+00:00'))
                        if datetime.now().replace(tzinfo=last_contact_dt.tzinfo) - last_contact_dt > timedelta(days=1):
                            issues.append(f"last_contact is not recent: {last_contact}")
                    except:
                        # If parsing fails, just note it exists
                        pass
            
            # Check source is "outbound_call"
            source = lead.get("source")
            if source != "outbound_call":
                issues.append(f"source is '{source}', should be 'outbound_call'")
            
            if not issues:
                self.log_result(
                    "CRM Lead Verification", 
                    "PASS", 
                    f"Lead verified: total_calls={total_calls}, last_contact={last_contact}, source={source}"
                )
                return True
            else:
                self.log_result(
                    "CRM Lead Verification", 
                    "FAIL", 
                    f"Lead verification issues: {'; '.join(issues)}"
                )
                return False
                
        except Exception as e:
            self.log_result("CRM Lead Verification", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_debug_endpoint_without_qc(self):
        """Test 4: Call Without Auto-QC Enabled"""
        try:
            # URL encode the call_id (colon needs to be encoded)
            encoded_call_id = urllib.parse.quote(CALL_ID_WITHOUT_QC, safe='')
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/debug/test-post-call-automation/{encoded_call_id}",
                    cookies=self.auth_cookies
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # The endpoint returns steps as an array
                    steps = data.get("steps", [])
                    step_dict = {step.get("step"): step for step in steps}
                    
                    # Verify expected behavior for call without auto-QC
                    issues = []
                    
                    # Should have find_call: success
                    find_call_step = step_dict.get("find_call")
                    if not find_call_step or find_call_step.get("status") != "success":
                        issues.append(f"find_call should be 'success', got '{find_call_step.get('status') if find_call_step else 'None'}'")
                    
                    # Should have check_agent_qc_settings showing auto_qc_enabled: false
                    qc_settings_step = step_dict.get("check_agent_qc_settings")
                    if qc_settings_step and qc_settings_step.get("status") == "success":
                        qc_data = qc_settings_step.get("data", {})
                        auto_qc_enabled = qc_data.get("auto_qc_enabled")
                        if auto_qc_enabled is not False:
                            issues.append(f"auto_qc_enabled should be false, got {auto_qc_enabled}")
                    else:
                        issues.append(f"check_agent_qc_settings step missing or failed")
                    
                    # Should have trigger_campaign_qc: skipped
                    campaign_qc_step = step_dict.get("trigger_campaign_qc")
                    if not campaign_qc_step or campaign_qc_step.get("status") != "skipped":
                        issues.append(f"trigger_campaign_qc should be 'skipped', got '{campaign_qc_step.get('status') if campaign_qc_step else 'None'}'")
                    
                    # Should have trigger_crm_update: triggered (CRM should still work)
                    crm_update_step = step_dict.get("trigger_crm_update")
                    if not crm_update_step or crm_update_step.get("status") != "triggered":
                        issues.append(f"trigger_crm_update should be 'triggered', got '{crm_update_step.get('status') if crm_update_step else 'None'}'")
                    
                    if not issues:
                        self.log_result(
                            "Debug Endpoint - No Auto-QC Call", 
                            "PASS", 
                            f"Correct behavior: find_call=success, auto_qc_enabled=false, campaign_qc=skipped, crm_update=triggered"
                        )
                        return True
                    else:
                        self.log_result(
                            "Debug Endpoint - No Auto-QC Call", 
                            "FAIL", 
                            f"Issues found: {'; '.join(issues)}"
                        )
                        return False
                else:
                    self.log_result(
                        "Debug Endpoint - No Auto-QC Call", 
                        "FAIL", 
                        f"HTTP error: {response.text}",
                        200,
                        response.status_code
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Debug Endpoint - No Auto-QC Call", "FAIL", f"Exception: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all Post-Call Automation tests"""
        print("🚀 Starting Post-Call Automation QC and CRM Functionality Testing")
        print(f"Backend URL: {self.backend_url}")
        print(f"Database: {DB_NAME}")
        print(f"Test User: {TEST_EMAIL}")
        print("=" * 80)
        print()
        
        # Setup MongoDB connection
        mongo_ok = await self.setup_mongodb_connection()
        if not mongo_ok:
            print("❌ Cannot proceed without MongoDB connection")
            return False
        
        # Authenticate
        auth_ok = await self.authenticate()
        if not auth_ok:
            print("❌ Cannot proceed without authentication")
            return False
        
        # Run test sequence as specified in review request
        print("Running Test 1: Debug Endpoint Basic Functionality...")
        await self.test_debug_endpoint_with_qc()
        
        print("Running Test 2: QC Automation Verification...")
        await self.test_qc_automation_verification()
        
        print("Running Test 3: CRM Lead Verification...")
        await self.test_crm_lead_verification()
        
        print("Running Test 4: Call Without Auto-QC Enabled...")
        await self.test_debug_endpoint_without_qc()
        
        # Print summary
        print("=" * 80)
        print("📊 POST-CALL AUTOMATION TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        print()
        
        # Show failed tests
        failed_tests = [r for r in self.results if r["status"] == "FAIL"]
        if failed_tests:
            print("❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
            print()
        
        # Show warnings
        warning_tests = [r for r in self.results if r["status"] == "WARN"]
        if warning_tests:
            print("⚠️  WARNINGS:")
            for test in warning_tests:
                print(f"  - {test['test']}: {test['details']}")
            print()
        
        # Show passed tests
        passed_tests = [r for r in self.results if r["status"] == "PASS"]
        if passed_tests:
            print("✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"  - {test['test']}: {test['details']}")
            print()
        
        return self.passed_tests == self.total_tests

    async def cleanup(self):
        """Cleanup resources"""
        if self.mongo_client:
            self.mongo_client.close()

async def main():
    """Main test runner"""
    tester = PostCallAutomationTester()
    
    try:
        success = await tester.run_all_tests()
        
        # Save detailed results to file
        with open("/app/post_call_automation_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": tester.total_tests,
                    "passed_tests": tester.passed_tests,
                    "failed_tests": tester.total_tests - tester.passed_tests,
                    "success_rate": (tester.passed_tests/tester.total_tests)*100 if tester.total_tests > 0 else 0,
                    "backend_url": tester.backend_url,
                    "test_timestamp": datetime.now().isoformat()
                },
                "detailed_results": tester.results
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/post_call_automation_test_results.json")
        
        if success:
            print("🎉 All Post-Call Automation tests passed!")
            print("✅ Post-Call Automation QC and CRM functionality is working correctly!")
            return True
        else:
            print("💥 Some Post-Call Automation tests failed!")
            print("❌ Issues found with Post-Call Automation functionality!")
            return False
            
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)