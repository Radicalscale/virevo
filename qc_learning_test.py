#!/usr/bin/env python3
"""
QC Learning System API Backend Testing Script

Tests the QC Learning System API endpoints as specified in the review request:
1. Health Check: GET /api/health - Verify backend is running
2. Playbook Endpoints (unauthenticated - expect 401):
   - GET /api/qc/learning/agents/{agent_id}/playbook
   - PUT /api/qc/learning/agents/{agent_id}/playbook
   - GET /api/qc/learning/agents/{agent_id}/playbook/history
   - POST /api/qc/learning/agents/{agent_id}/playbook/restore/{version}
3. Learning Control Endpoints (unauthenticated - expect 401):
   - GET /api/qc/learning/agents/{agent_id}/config
   - PUT /api/qc/learning/agents/{agent_id}/config
   - POST /api/qc/learning/agents/{agent_id}/learn
   - GET /api/qc/learning/agents/{agent_id}/stats
4. Analysis Logs Endpoints (unauthenticated - expect 401):
   - GET /api/qc/learning/agents/{agent_id}/analysis-logs
   - PUT /api/qc/learning/agents/{agent_id}/analysis-logs/{log_id}/outcome
5. Patterns Endpoints (unauthenticated - expect 401):
   - GET /api/qc/learning/agents/{agent_id}/patterns
   - DELETE /api/qc/learning/agents/{agent_id}/patterns/{pattern_id}
6. Sessions Endpoint (unauthenticated - expect 401):
   - GET /api/qc/learning/agents/{agent_id}/sessions

All endpoints should return 401 Unauthorized without auth token, confirming they are properly secured.
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

# Backend URL from frontend .env
BACKEND_URL = "https://tts-guardian.preview.emergentagent.com"
TEST_AGENT_ID = "test-agent-123"

class QCLearningSystemTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.test_agent_id = TEST_AGENT_ID
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_result(self, test_name: str, status: str, details: str = "", expected_status: int = None, actual_status: int = None):
        """Log test result"""
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
            
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        # Print result
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            print(f"   {details}")
        if expected_status and actual_status:
            print(f"   Expected: {expected_status}, Got: {actual_status}")
        print()

    async def test_health_check(self):
        """Test 1: Health Check - GET /api/health"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.backend_url}/api/health")
                
                if response.status_code == 200:
                    self.log_result(
                        "Health Check", 
                        "PASS", 
                        f"Backend is running. Response: {response.text[:100]}",
                        200,
                        response.status_code
                    )
                else:
                    self.log_result(
                        "Health Check", 
                        "FAIL", 
                        f"Unexpected status code. Response: {response.text[:100]}",
                        200,
                        response.status_code
                    )
        except Exception as e:
            self.log_result("Health Check", "FAIL", f"Exception: {str(e)}")

    async def test_playbook_endpoints_unauthenticated(self):
        """Test 2: Playbook endpoints without authentication (expect 401)"""
        
        endpoints = [
            ("GET", f"/api/qc/learning/agents/{self.test_agent_id}/playbook", "Get current playbook"),
            ("PUT", f"/api/qc/learning/agents/{self.test_agent_id}/playbook", "Update playbook"),
            ("GET", f"/api/qc/learning/agents/{self.test_agent_id}/playbook/history", "Get version history"),
            ("POST", f"/api/qc/learning/agents/{self.test_agent_id}/playbook/restore/v1", "Restore version")
        ]
        
        # Test data for PUT request
        playbook_data = {
            "content": "Test playbook content",
            "version": "1.0",
            "description": "Test playbook update"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for method, endpoint, description in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(f"{self.backend_url}{endpoint}")
                    elif method == "PUT":
                        response = await client.put(
                            f"{self.backend_url}{endpoint}",
                            json=playbook_data
                        )
                    elif method == "POST":
                        response = await client.post(f"{self.backend_url}{endpoint}")
                    
                    # Check if returns 401 (authentication required)
                    if response.status_code == 401:
                        self.log_result(
                            f"Playbook - {description}",
                            "PASS",
                            f"Correctly requires authentication",
                            401,
                            response.status_code
                        )
                    else:
                        self.log_result(
                            f"Playbook - {description}",
                            "FAIL",
                            f"Should require authentication. Response: {response.text[:100]}",
                            401,
                            response.status_code
                        )
                        
                except Exception as e:
                    self.log_result(f"Playbook - {description}", "FAIL", f"Exception: {str(e)}")

    async def test_learning_control_endpoints_unauthenticated(self):
        """Test 3: Learning Control endpoints without authentication (expect 401)"""
        
        endpoints = [
            ("GET", f"/api/qc/learning/agents/{self.test_agent_id}/config", "Get learning config"),
            ("PUT", f"/api/qc/learning/agents/{self.test_agent_id}/config", "Update config"),
            ("POST", f"/api/qc/learning/agents/{self.test_agent_id}/learn", "Trigger learning"),
            ("GET", f"/api/qc/learning/agents/{self.test_agent_id}/stats", "Get learning stats")
        ]
        
        # Test data for PUT and POST requests
        config_data = {
            "learning_rate": 0.01,
            "batch_size": 32,
            "enabled": True
        }
        
        learn_data = {
            "data_source": "recent_calls",
            "learning_type": "pattern_recognition"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for method, endpoint, description in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(f"{self.backend_url}{endpoint}")
                    elif method == "PUT":
                        response = await client.put(
                            f"{self.backend_url}{endpoint}",
                            json=config_data
                        )
                    elif method == "POST":
                        response = await client.post(
                            f"{self.backend_url}{endpoint}",
                            json=learn_data
                        )
                    
                    # Check if returns 401 (authentication required)
                    if response.status_code == 401:
                        self.log_result(
                            f"Learning Control - {description}",
                            "PASS",
                            f"Correctly requires authentication",
                            401,
                            response.status_code
                        )
                    else:
                        self.log_result(
                            f"Learning Control - {description}",
                            "FAIL",
                            f"Should require authentication. Response: {response.text[:100]}",
                            401,
                            response.status_code
                        )
                        
                except Exception as e:
                    self.log_result(f"Learning Control - {description}", "FAIL", f"Exception: {str(e)}")

    async def test_analysis_logs_endpoints_unauthenticated(self):
        """Test 4: Analysis Logs endpoints without authentication (expect 401)"""
        
        test_log_id = "test-log-123"
        
        endpoints = [
            ("GET", f"/api/qc/learning/agents/{self.test_agent_id}/analysis-logs", "Get analysis logs"),
            ("PUT", f"/api/qc/learning/agents/{self.test_agent_id}/analysis-logs/{test_log_id}/outcome", "Update log outcome")
        ]
        
        # Test data for PUT request
        outcome_data = {
            "outcome": "successful",
            "feedback": "Pattern correctly identified",
            "confidence": 0.95
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for method, endpoint, description in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(f"{self.backend_url}{endpoint}")
                    elif method == "PUT":
                        response = await client.put(
                            f"{self.backend_url}{endpoint}",
                            json=outcome_data
                        )
                    
                    # Check if returns 401 (authentication required)
                    if response.status_code == 401:
                        self.log_result(
                            f"Analysis Logs - {description}",
                            "PASS",
                            f"Correctly requires authentication",
                            401,
                            response.status_code
                        )
                    else:
                        self.log_result(
                            f"Analysis Logs - {description}",
                            "FAIL",
                            f"Should require authentication. Response: {response.text[:100]}",
                            401,
                            response.status_code
                        )
                        
                except Exception as e:
                    self.log_result(f"Analysis Logs - {description}", "FAIL", f"Exception: {str(e)}")

    async def test_patterns_endpoints_unauthenticated(self):
        """Test 5: Patterns endpoints without authentication (expect 401)"""
        
        test_pattern_id = "test-pattern-123"
        
        endpoints = [
            ("GET", f"/api/qc/learning/agents/{self.test_agent_id}/patterns", "Get patterns"),
            ("DELETE", f"/api/qc/learning/agents/{self.test_agent_id}/patterns/{test_pattern_id}", "Delete pattern")
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for method, endpoint, description in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(f"{self.backend_url}{endpoint}")
                    elif method == "DELETE":
                        response = await client.delete(f"{self.backend_url}{endpoint}")
                    
                    # Check if returns 401 (authentication required)
                    if response.status_code == 401:
                        self.log_result(
                            f"Patterns - {description}",
                            "PASS",
                            f"Correctly requires authentication",
                            401,
                            response.status_code
                        )
                    else:
                        self.log_result(
                            f"Patterns - {description}",
                            "FAIL",
                            f"Should require authentication. Response: {response.text[:100]}",
                            401,
                            response.status_code
                        )
                        
                except Exception as e:
                    self.log_result(f"Patterns - {description}", "FAIL", f"Exception: {str(e)}")

    async def test_sessions_endpoint_unauthenticated(self):
        """Test 6: Sessions endpoint without authentication (expect 401)"""
        
        endpoint = f"/api/qc/learning/agents/{self.test_agent_id}/sessions"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.backend_url}{endpoint}")
                
                # Check if returns 401 (authentication required)
                if response.status_code == 401:
                    self.log_result(
                        "Sessions - Get learning sessions",
                        "PASS",
                        f"Correctly requires authentication",
                        401,
                        response.status_code
                    )
                else:
                    self.log_result(
                        "Sessions - Get learning sessions",
                        "FAIL",
                        f"Should require authentication. Response: {response.text[:100]}",
                        401,
                        response.status_code
                    )
                    
        except Exception as e:
            self.log_result("Sessions - Get learning sessions", "FAIL", f"Exception: {str(e)}")

    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting QC Learning System API Backend Testing")
        print(f"Backend URL: {self.backend_url}")
        print(f"Test Agent ID: {self.test_agent_id}")
        print("=" * 60)
        print()
        
        # Run all test suites
        await self.test_health_check()
        await self.test_playbook_endpoints_unauthenticated()
        await self.test_learning_control_endpoints_unauthenticated()
        await self.test_analysis_logs_endpoints_unauthenticated()
        await self.test_patterns_endpoints_unauthenticated()
        await self.test_sessions_endpoint_unauthenticated()
        
        # Print summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
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
        
        return self.passed_tests == self.total_tests

async def main():
    """Main test runner"""
    tester = QCLearningSystemTester()
    success = await tester.run_all_tests()
    
    # Save detailed results to file
    with open("/app/qc_learning_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": tester.total_tests,
                "passed_tests": tester.passed_tests,
                "failed_tests": tester.total_tests - tester.passed_tests,
                "success_rate": (tester.passed_tests/tester.total_tests)*100,
                "backend_url": tester.backend_url,
                "test_agent_id": tester.test_agent_id,
                "test_timestamp": datetime.now().isoformat()
            },
            "detailed_results": tester.results
        }, f, indent=2)
    
    print(f"📄 Detailed results saved to: /app/qc_learning_test_results.json")
    
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())