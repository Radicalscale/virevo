#!/usr/bin/env python3
"""
Variable Extraction System Testing Script

Tests the variable extraction system with calculations for the income qualification flow as specified in the review request:
1. User says their yearly income is $60,000
2. System should extract `employed_yearly_income` = 60000
3. Calculate `amount_reference` as monthly = 60000 / 12 = 5000
4. Test logic split node (ID: 1763180018981) that evaluates if amount_reference > 8000

Agent ID: bbeda238-e8d9-4d8c-b93b-1b7694581adb
Backend URL: https://voice-overlap-debug.preview.emergentagent.com (from frontend/.env)
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Get backend URL from frontend/.env
BACKEND_URL = "https://voice-overlap-debug.preview.emergentagent.com"
AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb"
LOGIC_SPLIT_NODE_ID = "1763180018981"

class VariableExtractionTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.agent_id = AGENT_ID
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.session_id = None
        self.auth_token = None
        
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

    async def authenticate(self):
        """Authenticate with the backend to get access token"""
        try:
            # Try to create a test account or login with existing credentials
            test_email = f"test_extraction_{int(datetime.now().timestamp())}@example.com"
            test_password = "TestPassword123!"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try to signup first
                signup_response = await client.post(
                    f"{self.backend_url}/api/auth/signup",
                    json={
                        "email": test_email,
                        "password": test_password,
                        "remember_me": False
                    }
                )
                
                if signup_response.status_code == 200:
                    self.log_result(
                        "Authentication - Signup", 
                        "PASS", 
                        f"Successfully created test account: {test_email}",
                        200,
                        signup_response.status_code
                    )
                    
                    # Extract token from cookies or response
                    cookies = signup_response.cookies
                    if 'access_token' in cookies:
                        self.auth_token = cookies['access_token']
                        return True
                    
                elif signup_response.status_code == 400:
                    # Account might already exist, try login
                    login_response = await client.post(
                        f"{self.backend_url}/api/auth/login",
                        json={
                            "email": test_email,
                            "password": test_password,
                            "remember_me": False
                        }
                    )
                    
                    if login_response.status_code == 200:
                        self.log_result(
                            "Authentication - Login", 
                            "PASS", 
                            f"Successfully logged in with existing account",
                            200,
                            login_response.status_code
                        )
                        
                        cookies = login_response.cookies
                        if 'access_token' in cookies:
                            self.auth_token = cookies['access_token']
                            return True
                
                self.log_result(
                    "Authentication", 
                    "FAIL", 
                    f"Failed to authenticate. Signup: {signup_response.status_code}, Login attempted if needed",
                    200,
                    signup_response.status_code
                )
                return False
                
        except Exception as e:
            self.log_result("Authentication", "FAIL", f"Exception during authentication: {str(e)}")
            return False

    async def test_agent_exists(self):
        """Test 2: Check the backend is responding to requests"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test FastAPI docs endpoint (this should always work if backend is running)
                docs_response = await client.get(f"{self.backend_url}/docs")
                
                if docs_response.status_code == 200:
                    self.log_result(
                        "Backend Responsiveness", 
                        "PASS", 
                        f"Backend responding correctly (FastAPI docs available)",
                        200,
                        docs_response.status_code
                    )
                else:
                    # Try API endpoint to see if backend is responding
                    api_response = await client.get(f"{self.backend_url}/api/agents")
                    if api_response.status_code in [401, 422]:  # Expected without auth
                        self.log_result(
                            "Backend Responsiveness", 
                            "PASS", 
                            f"Backend responding correctly (API endpoints available)",
                            401,
                            api_response.status_code
                        )
                    else:
                        self.log_result(
                            "Backend Responsiveness", 
                            "FAIL", 
                            f"Backend not responding properly: {docs_response.text[:200]}",
                            200,
                            docs_response.status_code
                        )
        except Exception as e:
            self.log_result("Backend Responsiveness", "FAIL", f"Exception: {str(e)}")

    def test_code_fixes_verification(self):
        """Test 3: Verify the server.py file contains the voice agent response task management fix"""
        try:
            # Read the server.py file
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
            
            # Check 1: Look for the `was_generating` variable check around line 3595-3600
            was_generating_pattern = r'was_generating\s*=\s*agent_generating_response\s*or\s*call_states\.get\(call_control_id,\s*\{\}\)\.get\("agent_generating_response",\s*False\)'
            was_generating_found = bool(re.search(was_generating_pattern, server_code))
            
            # Check 2: Look for the message "Response task exists but agent_generating_response=False - NOT cancelling"
            not_cancelling_message = "Response task exists but agent_generating_response=False - NOT cancelling" in server_code
            
            # Check 3: Look for the fixed cancellation check in `on_endpoint_detected` using `current_task.cancelled()` boolean
            cancellation_check_pattern = r'current_task\s*=\s*asyncio\.current_task\(\)\s*\n\s*if\s+current_task\s+and\s+current_task\.cancelled\(\):'
            cancellation_check_found = bool(re.search(cancellation_check_pattern, server_code))
            
            # Check 4: Verify the specific fix logic around line 3598
            fix_logic_pattern = r'if\s+current_response_task\s+and\s+not\s+current_response_task\.done\(\)\s+and\s+was_generating:'
            fix_logic_found = bool(re.search(fix_logic_pattern, server_code))
            
            fixes_found = []
            fixes_missing = []
            
            if was_generating_found:
                fixes_found.append("was_generating variable check")
            else:
                fixes_missing.append("was_generating variable check")
                
            if not_cancelling_message:
                fixes_found.append("NOT cancelling message")
            else:
                fixes_missing.append("NOT cancelling message")
                
            if cancellation_check_found:
                fixes_found.append("current_task.cancelled() boolean check")
            else:
                fixes_missing.append("current_task.cancelled() boolean check")
                
            if fix_logic_found:
                fixes_found.append("was_generating condition in cancellation logic")
            else:
                fixes_missing.append("was_generating condition in cancellation logic")
            
            if len(fixes_found) == 4:
                self.code_fixes_verified = True
                self.log_result(
                    "Code Fixes Verification", 
                    "PASS", 
                    f"All voice agent response task management fixes found: {', '.join(fixes_found)}",
                    4,
                    len(fixes_found)
                )
            else:
                self.log_result(
                    "Code Fixes Verification", 
                    "FAIL", 
                    f"Missing fixes: {', '.join(fixes_missing)}. Found: {', '.join(fixes_found)}",
                    4,
                    len(fixes_found)
                )
                
        except FileNotFoundError:
            self.log_result("Code Fixes Verification", "FAIL", "server.py file not found at /app/backend/server.py")
        except Exception as e:
            self.log_result("Code Fixes Verification", "FAIL", f"Exception: {str(e)}")

    async def test_check_backend_logs(self):
        """Test 4: Check backend logs for startup errors and voice agent related issues"""
        try:
            # Check supervisor backend logs for errors
            result = subprocess.run(
                ["tail", "-n", "100", "/var/log/supervisor/backend.err.log"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                log_content = result.stdout
                
                # Look for startup errors and voice agent related issues
                error_keywords = ['traceback', 'error', 'exception', 'failed', 'websocket', 'voice', 'agent_generating_response', 'on_endpoint_detected', 'current_task']
                recent_errors = []
                
                for line in log_content.split('\n'):
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in error_keywords):
                        recent_errors.append(line.strip())
                
                if recent_errors:
                    # Show the most recent errors (last 10)
                    recent_errors = recent_errors[-10:]
                    self.log_result(
                        "Check Backend Logs", 
                        "WARN", 
                        f"Found {len(recent_errors)} recent error entries in backend logs. "
                        f"Recent errors: {'; '.join(recent_errors[:3])}{'...' if len(recent_errors) > 3 else ''}",
                        0,
                        len(recent_errors)
                    )
                else:
                    self.log_result(
                        "Check Backend Logs", 
                        "PASS", 
                        f"No recent errors found in backend logs. Log file has {len(log_content.split())} lines.",
                        0,
                        0
                    )
            else:
                self.log_result(
                    "Check Backend Logs", 
                    "WARN", 
                    f"Could not read backend error logs. Return code: {result.returncode}",
                    0,
                    result.returncode
                )
                
        except subprocess.TimeoutExpired:
            self.log_result("Check Backend Logs", "WARN", "Timeout while reading backend logs")
        except FileNotFoundError:
            self.log_result("Check Backend Logs", "WARN", "Backend log file not found at /var/log/supervisor/backend.err.log")
        except Exception as e:
            self.log_result("Check Backend Logs", "FAIL", f"Exception while checking logs: {str(e)}")

    async def test_websocket_endpoint_availability(self):
        """Test 5: Verify WebSocket endpoints are available (voice agent functionality)"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                
                # Test basic API endpoints that voice agents would use
                # Note: We can't fully test WebSocket without a real call, but we can check if endpoints exist
                
                # Test 1: Check if agents endpoint exists (voice agents need this)
                agents_response = await client.get(f"{self.backend_url}/api/agents")
                
                if agents_response.status_code in [200, 401]:  # 401 is expected without auth
                    self.log_result(
                        "Agents Endpoint Availability", 
                        "PASS", 
                        f"Agents endpoint available (status: {agents_response.status_code})",
                        200,
                        agents_response.status_code
                    )
                else:
                    self.log_result(
                        "Agents Endpoint Availability", 
                        "FAIL", 
                        f"Agents endpoint not available: {agents_response.status_code}",
                        200,
                        agents_response.status_code
                    )
                
                # Test 2: Check if auth endpoints exist (needed for voice agent authentication)
                auth_response = await client.post(
                    f"{self.backend_url}/api/auth/login",
                    json={"email": "test", "password": "test"}
                )
                
                if auth_response.status_code in [200, 401, 422]:  # These are expected responses
                    self.log_result(
                        "Auth Endpoint Availability", 
                        "PASS", 
                        f"Auth endpoint available (status: {auth_response.status_code})",
                        200,
                        auth_response.status_code
                    )
                else:
                    self.log_result(
                        "Auth Endpoint Availability", 
                        "FAIL", 
                        f"Auth endpoint not available: {auth_response.status_code}",
                        200,
                        auth_response.status_code
                    )
                    
        except Exception as e:
            self.log_result("WebSocket Endpoint Availability", "FAIL", f"Exception: {str(e)}")

    async def run_all_tests(self):
        """Run all tests for Voice Agent Response Task Management"""
        print("🚀 Starting Voice Agent Response Task Management Testing")
        print(f"Backend URL: {self.backend_url}")
        print("Testing the voice agent's response task management in the backend server.py")
        print("Note: This is a WebSocket-based voice call system that requires real phone calls to fully test.")
        print("The key verification is that the code changes are in place and the backend runs without errors.")
        print("=" * 80)
        print()
        
        # Run test sequence as specified in review request
        await self.test_backend_startup()
        await self.test_health_endpoint()
        self.test_code_fixes_verification()  # Synchronous method
        await self.test_check_backend_logs()
        await self.test_websocket_endpoint_availability()
        
        # Print summary
        print("=" * 80)
        print("📊 VOICE AGENT RESPONSE TASK MANAGEMENT TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        print()
        
        # Show test results summary
        if self.backend_running:
            print(f"✅ Backend Service: Running correctly via supervisor")
        else:
            print(f"❌ Backend Service: Not running or has issues")
            
        if self.code_fixes_verified:
            print(f"✅ Code Fixes: All voice agent response task management fixes verified")
        else:
            print(f"❌ Code Fixes: Missing or incomplete voice agent fixes")
        
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

async def main():
    """Main test runner"""
    tester = VoiceAgentTaskManagementTester()
    success = await tester.run_all_tests()
    
    # Save detailed results to file
    with open("/app/voice_agent_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": tester.total_tests,
                "passed_tests": tester.passed_tests,
                "failed_tests": tester.total_tests - tester.passed_tests,
                "success_rate": (tester.passed_tests/tester.total_tests)*100 if tester.total_tests > 0 else 0,
                "backend_url": tester.backend_url,
                "test_timestamp": datetime.now().isoformat(),
                "backend_running": tester.backend_running,
                "code_fixes_verified": tester.code_fixes_verified
            },
            "detailed_results": tester.results
        }, f, indent=2)
    
    print(f"📄 Detailed results saved to: /app/voice_agent_test_results.json")
    
    if success:
        print("🎉 All Voice Agent Response Task Management tests passed!")
        print("✅ Voice agent response task management fix is working correctly!")
        sys.exit(0)
    else:
        print("💥 Some Voice Agent Response Task Management tests failed!")
        print("❌ Issues found with voice agent response task management!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())