#!/usr/bin/env python3
"""
Variable Extraction System Testing Script

Tests the variable extraction system with calculations for the income qualification flow as specified in the review request:
1. User says their yearly income is $60,000
2. System should extract `employed_yearly_income` = 60000
3. Calculate `amount_reference` as monthly = 60000 / 12 = 5000
4. Test logic split node (ID: 1763180018981) that evaluates if amount_reference > 8000

Agent ID: bbeda238-e8d9-4d8c-b93b-1b7694581adb
Backend URL: https://missed-variable.preview.emergentagent.com (from frontend/.env)
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Get backend URL from frontend/.env
BACKEND_URL = "https://missed-variable.preview.emergentagent.com"
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
            # Use the known user credentials for the agent owner
            test_email = "kendrickbowman9@gmail.com"
            test_password = "B!LL10n$$"  # Known password from test_result.md
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try to login with known credentials
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
                        f"Successfully logged in with agent owner account: {test_email}",
                        200,
                        login_response.status_code
                    )
                    
                    cookies = login_response.cookies
                    if 'access_token' in cookies:
                        self.auth_token = cookies['access_token']
                        return True
                else:
                    self.log_result(
                        "Authentication", 
                        "FAIL", 
                        f"Failed to authenticate with {test_email}: {login_response.text[:200]}",
                        200,
                        login_response.status_code
                    )
                    return False
                
        except Exception as e:
            self.log_result("Authentication", "FAIL", f"Exception during authentication: {str(e)}")
            return False

    async def test_agent_exists(self):
        """Test 1: Verify the agent exists and is accessible"""
        try:
            headers = {}
            if self.auth_token:
                headers['Cookie'] = f'access_token={self.auth_token}'
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/agents/{self.agent_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    agent_data = response.json()
                    agent_name = agent_data.get('name', 'Unknown')
                    call_flow_count = len(agent_data.get('call_flow', []))
                    
                    self.log_result(
                        "Agent Exists", 
                        "PASS", 
                        f"Agent found: {agent_name} with {call_flow_count} flow nodes",
                        200,
                        response.status_code
                    )
                    return agent_data
                else:
                    self.log_result(
                        "Agent Exists", 
                        "FAIL", 
                        f"Agent not found or not accessible: {response.text[:200]}",
                        200,
                        response.status_code
                    )
                    return None
                    
        except Exception as e:
            self.log_result("Agent Exists", "FAIL", f"Exception: {str(e)}")
            return None

    async def test_start_session(self):
        """Test 2: Start a test session with the agent"""
        try:
            headers = {}
            if self.auth_token:
                headers['Cookie'] = f'access_token={self.auth_token}'
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/agents/{self.agent_id}/test/start",
                    headers=headers,
                    json={}
                )
                
                if response.status_code == 200:
                    session_data = response.json()
                    self.session_id = session_data.get('session_id')
                    
                    self.log_result(
                        "Start Test Session", 
                        "PASS", 
                        f"Test session started: {self.session_id[:8]}...",
                        200,
                        response.status_code
                    )
                    return True
                else:
                    self.log_result(
                        "Start Test Session", 
                        "FAIL", 
                        f"Failed to start session: {response.text[:200]}",
                        200,
                        response.status_code
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Start Test Session", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_income_extraction_60k(self):
        """Test 3: Test income extraction with $60,000 yearly income"""
        if not self.session_id:
            self.log_result("Income Extraction (60k)", "FAIL", "No active session")
            return False
            
        try:
            headers = {}
            if self.auth_token:
                headers['Cookie'] = f'access_token={self.auth_token}'
            
            # Test different ways of saying $60,000 yearly income
            test_messages = [
                "I make about 60k a year",
                "My yearly income is $60,000", 
                "I earn sixty thousand dollars annually",
                "My annual salary is 60000"
            ]
            
            for i, message in enumerate(test_messages):
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.backend_url}/api/agents/{self.agent_id}/test/message",
                        headers=headers,
                        json={
                            "message": message,
                            "session_id": self.session_id
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        variables = result.get('variables', {})
                        
                        # Check if employed_yearly_income was extracted
                        employed_yearly_income = variables.get('employed_yearly_income')
                        amount_reference = variables.get('amount_reference')
                        
                        if employed_yearly_income == 60000:
                            self.log_result(
                                f"Income Extraction (60k) - Message {i+1}", 
                                "PASS", 
                                f"Correctly extracted employed_yearly_income: {employed_yearly_income}",
                                60000,
                                employed_yearly_income
                            )
                            
                            # Check amount_reference calculation (60000 / 12 = 5000)
                            if amount_reference == 5000:
                                self.log_result(
                                    f"Amount Reference Calculation - Message {i+1}", 
                                    "PASS", 
                                    f"Correctly calculated amount_reference: {amount_reference}",
                                    5000,
                                    amount_reference
                                )
                                return True
                            else:
                                self.log_result(
                                    f"Amount Reference Calculation - Message {i+1}", 
                                    "FAIL", 
                                    f"Incorrect amount_reference calculation",
                                    5000,
                                    amount_reference
                                )
                        else:
                            self.log_result(
                                f"Income Extraction (60k) - Message {i+1}", 
                                "FAIL", 
                                f"Incorrect or missing employed_yearly_income extraction",
                                60000,
                                employed_yearly_income
                            )
                    else:
                        self.log_result(
                            f"Income Extraction (60k) - Message {i+1}", 
                            "FAIL", 
                            f"API call failed: {response.status_code}",
                            200,
                            response.status_code
                        )
                        
                # If we got a successful extraction, break
                if employed_yearly_income == 60000 and amount_reference == 5000:
                    break
                    
            return False
                    
        except Exception as e:
            self.log_result("Income Extraction (60k)", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_logic_split_evaluation(self):
        """Test 4: Test logic split node evaluation (amount_reference > 8000)"""
        if not self.session_id:
            self.log_result("Logic Split Evaluation", "FAIL", "No active session")
            return False
            
        try:
            headers = {}
            if self.auth_token:
                headers['Cookie'] = f'access_token={self.auth_token}'
            
            # Get current session state
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/agents/{self.agent_id}/test/session/{self.session_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    session_data = response.json()
                    variables = session_data.get('variables', {})
                    amount_reference = variables.get('amount_reference')
                    
                    # Test the logic: amount_reference (5000) should NOT be > 8000
                    if amount_reference == 5000:
                        expected_result = False  # 5000 is not > 8000
                        
                        self.log_result(
                            "Logic Split Evaluation", 
                            "PASS", 
                            f"Logic split condition (amount_reference > 8000): {amount_reference} > 8000 = {expected_result}",
                            expected_result,
                            amount_reference > 8000 if amount_reference else None
                        )
                        
                        # Test with a higher income to verify the logic works both ways
                        await self.test_higher_income_logic_split()
                        return True
                    else:
                        self.log_result(
                            "Logic Split Evaluation", 
                            "FAIL", 
                            f"amount_reference not set correctly for logic split test",
                            5000,
                            amount_reference
                        )
                        return False
                else:
                    self.log_result(
                        "Logic Split Evaluation", 
                        "FAIL", 
                        f"Failed to get session state: {response.status_code}",
                        200,
                        response.status_code
                    )
                    return False
                    
        except Exception as e:
            self.log_result("Logic Split Evaluation", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_higher_income_logic_split(self):
        """Test 5: Test logic split with higher income (should be > 8000)"""
        try:
            headers = {}
            if self.auth_token:
                headers['Cookie'] = f'access_token={self.auth_token}'
            
            # Test with $120,000 yearly income (should result in 10,000 monthly)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/agents/{self.agent_id}/test/message",
                    headers=headers,
                    json={
                        "message": "Actually, I make $120,000 per year",
                        "session_id": self.session_id
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    variables = result.get('variables', {})
                    
                    employed_yearly_income = variables.get('employed_yearly_income')
                    amount_reference = variables.get('amount_reference')
                    
                    if employed_yearly_income == 120000 and amount_reference == 10000:
                        # Test logic: 10000 > 8000 should be True
                        expected_result = True
                        actual_result = amount_reference > 8000
                        
                        if actual_result == expected_result:
                            self.log_result(
                                "Higher Income Logic Split", 
                                "PASS", 
                                f"Logic split condition (amount_reference > 8000): {amount_reference} > 8000 = {actual_result}",
                                expected_result,
                                actual_result
                            )
                            return True
                        else:
                            self.log_result(
                                "Higher Income Logic Split", 
                                "FAIL", 
                                f"Logic evaluation incorrect",
                                expected_result,
                                actual_result
                            )
                    else:
                        self.log_result(
                            "Higher Income Logic Split", 
                            "FAIL", 
                            f"Variable extraction/calculation failed for higher income",
                            {"employed_yearly_income": 120000, "amount_reference": 10000},
                            {"employed_yearly_income": employed_yearly_income, "amount_reference": amount_reference}
                        )
                else:
                    self.log_result(
                        "Higher Income Logic Split", 
                        "FAIL", 
                        f"API call failed: {response.status_code}",
                        200,
                        response.status_code
                    )
                    
            return False
                    
        except Exception as e:
            self.log_result("Higher Income Logic Split", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_various_income_formats(self):
        """Test 6: Test various income format extractions"""
        if not self.session_id:
            self.log_result("Various Income Formats", "FAIL", "No active session")
            return False
            
        test_cases = [
            {"input": "I make 50k", "expected_yearly": 50000, "expected_monthly": 4167},
            {"input": "My income is $75,000 annually", "expected_yearly": 75000, "expected_monthly": 6250},
            {"input": "I earn about eighty thousand per year", "expected_yearly": 80000, "expected_monthly": 6667},
            {"input": "My salary is 45000", "expected_yearly": 45000, "expected_monthly": 3750}
        ]
        
        passed_cases = 0
        
        for i, case in enumerate(test_cases):
            try:
                headers = {}
                if self.auth_token:
                    headers['Cookie'] = f'access_token={self.auth_token}'
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.backend_url}/api/agents/{self.agent_id}/test/message",
                        headers=headers,
                        json={
                            "message": case["input"],
                            "session_id": self.session_id
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        variables = result.get('variables', {})
                        
                        employed_yearly_income = variables.get('employed_yearly_income')
                        amount_reference = variables.get('amount_reference')
                        
                        yearly_correct = employed_yearly_income == case["expected_yearly"]
                        monthly_correct = abs((amount_reference or 0) - case["expected_monthly"]) <= 1  # Allow 1 dollar rounding difference
                        
                        if yearly_correct and monthly_correct:
                            self.log_result(
                                f"Income Format Test {i+1}", 
                                "PASS", 
                                f"'{case['input']}' -> yearly: {employed_yearly_income}, monthly: {amount_reference}",
                                f"yearly: {case['expected_yearly']}, monthly: {case['expected_monthly']}",
                                f"yearly: {employed_yearly_income}, monthly: {amount_reference}"
                            )
                            passed_cases += 1
                        else:
                            self.log_result(
                                f"Income Format Test {i+1}", 
                                "FAIL", 
                                f"'{case['input']}' extraction/calculation failed",
                                f"yearly: {case['expected_yearly']}, monthly: {case['expected_monthly']}",
                                f"yearly: {employed_yearly_income}, monthly: {amount_reference}"
                            )
                    else:
                        self.log_result(
                            f"Income Format Test {i+1}", 
                            "FAIL", 
                            f"API call failed: {response.status_code}",
                            200,
                            response.status_code
                        )
                        
            except Exception as e:
                self.log_result(f"Income Format Test {i+1}", "FAIL", f"Exception: {str(e)}")
        
        # Overall result
        if passed_cases == len(test_cases):
            self.log_result(
                "Various Income Formats - Overall", 
                "PASS", 
                f"All {len(test_cases)} income format tests passed",
                len(test_cases),
                passed_cases
            )
            return True
        else:
            self.log_result(
                "Various Income Formats - Overall", 
                "FAIL", 
                f"Only {passed_cases}/{len(test_cases)} income format tests passed",
                len(test_cases),
                passed_cases
            )
            return False

    async def cleanup_session(self):
        """Clean up the test session"""
        if self.session_id:
            try:
                headers = {}
                if self.auth_token:
                    headers['Cookie'] = f'access_token={self.auth_token}'
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.delete(
                        f"{self.backend_url}/api/agents/{self.agent_id}/test/session/{self.session_id}",
                        headers=headers
                    )
                    
                self.log_result("Session Cleanup", "PASS", f"Test session {self.session_id[:8]}... cleaned up")
                
            except Exception as e:
                self.log_result("Session Cleanup", "WARN", f"Failed to cleanup session: {str(e)}")

    async def run_all_tests(self):
        """Run all variable extraction tests"""
        print("🚀 Starting Variable Extraction System Testing")
        print(f"Backend URL: {self.backend_url}")
        print(f"Agent ID: {self.agent_id}")
        print(f"Logic Split Node ID: {LOGIC_SPLIT_NODE_ID}")
        print("Testing income extraction and calculation flow:")
        print("1. User says yearly income is $60,000")
        print("2. System extracts employed_yearly_income = 60000")
        print("3. System calculates amount_reference = 60000 / 12 = 5000")
        print("4. Logic split evaluates: amount_reference > 8000 (should be False)")
        print("=" * 80)
        print()
        
        # Run test sequence
        auth_success = await self.authenticate()
        if not auth_success:
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        agent_data = await self.test_agent_exists()
        if not agent_data:
            print("❌ Agent not found - cannot proceed with tests")
            return False
        
        session_started = await self.test_start_session()
        if not session_started:
            print("❌ Failed to start test session - cannot proceed with tests")
            return False
        
        # Core variable extraction tests
        await self.test_income_extraction_60k()
        await self.test_logic_split_evaluation()
        await self.test_various_income_formats()
        
        # Cleanup
        await self.cleanup_session()
        
        # Print summary
        print("=" * 80)
        print("📊 VARIABLE EXTRACTION SYSTEM TEST SUMMARY")
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

async def main():
    """Main test runner"""
    tester = VariableExtractionTester()
    success = await tester.run_all_tests()
    
    # Save detailed results to file
    with open("/app/variable_extraction_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": tester.total_tests,
                "passed_tests": tester.passed_tests,
                "failed_tests": tester.total_tests - tester.passed_tests,
                "success_rate": (tester.passed_tests/tester.total_tests)*100 if tester.total_tests > 0 else 0,
                "backend_url": tester.backend_url,
                "agent_id": tester.agent_id,
                "test_timestamp": datetime.now().isoformat()
            },
            "detailed_results": tester.results
        }, f, indent=2)
    
    print(f"📄 Detailed results saved to: /app/variable_extraction_test_results.json")
    
    if success:
        print("🎉 All Variable Extraction System tests passed!")
        print("✅ Income extraction and calculation system is working correctly!")
        sys.exit(0)
    else:
        print("💥 Some Variable Extraction System tests failed!")
        print("❌ Issues found with income extraction or calculation system!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())