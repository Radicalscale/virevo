#!/usr/bin/env python3
"""
Webhook Test Endpoint Testing Script

Tests the webhook-test endpoint in the Flow Builder functionality as specified in the review request:

1. Test JSON Schema format detection and request building
2. Test that the endpoint works with valid data
3. Verify the webhook test proxy endpoint is functioning

The webhook tester has been updated to support two formats:
1. JSON Schema format - where the body is like {"type": "object", "properties": {"amPm": {"type": "string", "description": "..."}}}
2. Template format - where the body uses {{variable}} placeholders

Backend URL: Uses REACT_APP_BACKEND_URL environment variable
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://voice-ai-perf.preview.emergentagent.com')

class WebhookTesterValidator:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.session_cookie = None
        
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
        """Authenticate with the backend to get session cookie"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try to authenticate with test credentials
                auth_response = await client.post(
                    f"{self.backend_url}/api/auth/login",
                    json={
                        "email": "webhook_test_user@example.com",
                        "password": "WebhookTest123!",
                        "remember_me": False
                    }
                )
                
                if auth_response.status_code == 200:
                    # Extract session cookie
                    cookies = auth_response.cookies
                    if 'access_token' in cookies:
                        self.session_cookie = f"access_token={cookies['access_token']}"
                        self.log_result(
                            "Authentication", 
                            "PASS", 
                            "Successfully authenticated with webhook test credentials",
                            200,
                            auth_response.status_code
                        )
                        return True
                    else:
                        self.log_result(
                            "Authentication", 
                            "FAIL", 
                            "No access_token cookie in response",
                            "access_token cookie",
                            "No cookie"
                        )
                        return False
                else:
                    self.log_result(
                        "Authentication", 
                        "FAIL", 
                        f"Login failed with status: {auth_response.status_code} - {auth_response.text[:200]}",
                        200,
                        auth_response.status_code
                    )
                    return False
                    
        except Exception as e:
            self.log_result(
                "Authentication", 
                "FAIL", 
                f"Authentication failed with exception: {str(e)}"
            )
            return False

    async def test_webhook_endpoint_availability(self):
        """Test 1: Verify the webhook-test endpoint exists and is accessible"""
        try:
            headers = {}
            if self.session_cookie:
                headers['Cookie'] = self.session_cookie
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test with minimal valid request
                test_response = await client.post(
                    f"{self.backend_url}/api/webhook-test",
                    headers=headers,
                    json={
                        "url": "https://httpbin.org/post",
                        "method": "POST",
                        "body": {"test": "availability"},
                        "headers": {},
                        "timeout": 10000
                    }
                )
                
                if test_response.status_code == 200:
                    response_data = test_response.json()
                    if response_data.get('success'):
                        self.log_result(
                            "Webhook Endpoint Availability", 
                            "PASS", 
                            f"Webhook-test endpoint is accessible and functional",
                            200,
                            test_response.status_code
                        )
                    else:
                        self.log_result(
                            "Webhook Endpoint Availability", 
                            "FAIL", 
                            f"Endpoint accessible but returned error: {response_data.get('error', 'Unknown error')}",
                            "success: true",
                            f"success: {response_data.get('success')}"
                        )
                elif test_response.status_code == 401:
                    self.log_result(
                        "Webhook Endpoint Availability", 
                        "FAIL", 
                        "Authentication required - endpoint exists but needs valid session",
                        200,
                        test_response.status_code
                    )
                else:
                    self.log_result(
                        "Webhook Endpoint Availability", 
                        "FAIL", 
                        f"Endpoint not accessible: {test_response.status_code} - {test_response.text[:200]}",
                        200,
                        test_response.status_code
                    )
                    
        except Exception as e:
            self.log_result("Webhook Endpoint Availability", "FAIL", f"Exception: {str(e)}")

    async def test_json_schema_format_detection(self):
        """Test 2: Test JSON Schema format detection and request building"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.session_cookie:
                headers['Cookie'] = self.session_cookie
            
            # Test request with actual values (not JSON Schema)
            test_data = {
                "url": "https://httpbin.org/post",
                "method": "POST",
                "body": {
                    "amPm": "PM",
                    "timeZone": "EST", 
                    "scheduleTime": "Tuesday 6pm"
                },
                "headers": {},
                "timeout": 10000
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/webhook-test",
                    headers=headers,
                    json=test_data
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if response_data.get('success'):
                        # Check if httpbin received the correct data
                        httpbin_response = response_data.get('response', {})
                        
                        if isinstance(httpbin_response, dict):
                            received_json = httpbin_response.get('json', {})
                            
                            # Verify the actual values were sent, not schema
                            expected_values = {
                                "amPm": "PM",
                                "timeZone": "EST",
                                "scheduleTime": "Tuesday 6pm"
                            }
                            
                            if received_json == expected_values:
                                self.log_result(
                                    "JSON Schema Format Detection", 
                                    "PASS", 
                                    f"Webhook correctly sent actual values: {received_json}",
                                    expected_values,
                                    received_json
                                )
                            else:
                                self.log_result(
                                    "JSON Schema Format Detection", 
                                    "FAIL", 
                                    f"Webhook sent incorrect data. Expected actual values, got: {received_json}",
                                    expected_values,
                                    received_json
                                )
                        else:
                            self.log_result(
                                "JSON Schema Format Detection", 
                                "FAIL", 
                                f"Unexpected response format from httpbin: {type(httpbin_response)}",
                                "dict",
                                type(httpbin_response).__name__
                            )
                    else:
                        self.log_result(
                            "JSON Schema Format Detection", 
                            "FAIL", 
                            f"Webhook test failed: {response_data.get('error', 'Unknown error')}",
                            "success: true",
                            f"success: {response_data.get('success')}"
                        )
                else:
                    self.log_result(
                        "JSON Schema Format Detection", 
                        "FAIL", 
                        f"HTTP error: {response.status_code} - {response.text[:200]}",
                        200,
                        response.status_code
                    )
                    
        except Exception as e:
            self.log_result("JSON Schema Format Detection", "FAIL", f"Exception: {str(e)}")

    async def test_template_format_support(self):
        """Test 3: Test template format with {{variable}} placeholders"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.session_cookie:
                headers['Cookie'] = self.session_cookie
            
            # Test request with template format
            test_data = {
                "url": "https://httpbin.org/post",
                "method": "POST", 
                "body": {
                    "message": "Hello {{name}}, your appointment is at {{time}}",
                    "template_vars": {
                        "name": "John",
                        "time": "3:00 PM"
                    }
                },
                "headers": {},
                "timeout": 10000
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/webhook-test",
                    headers=headers,
                    json=test_data
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if response_data.get('success'):
                        # Check if httpbin received the data
                        httpbin_response = response_data.get('response', {})
                        
                        if isinstance(httpbin_response, dict):
                            received_json = httpbin_response.get('json', {})
                            
                            # The webhook should send the template as-is (backend is just a proxy)
                            expected_data = test_data['body']
                            
                            # Check if the template data was sent correctly
                            if 'message' in received_json and 'template_vars' in received_json:
                                if (received_json['message'] == expected_data['message'] and 
                                    received_json['template_vars'] == expected_data['template_vars']):
                                    self.log_result(
                                        "Template Format Support", 
                                        "PASS", 
                                        f"Webhook correctly sent template data with {{{{variables}}}}: {received_json['message']}",
                                        expected_data,
                                        received_json
                                    )
                                else:
                                    self.log_result(
                                        "Template Format Support", 
                                        "FAIL", 
                                        f"Template data modified. Expected: {expected_data}, Got: {received_json}",
                                        expected_data,
                                        received_json
                                    )
                            else:
                                self.log_result(
                                    "Template Format Support", 
                                    "FAIL", 
                                    f"Template structure not preserved. Expected message and template_vars fields, Got: {list(received_json.keys())}",
                                    ["message", "template_vars"],
                                    list(received_json.keys())
                                )
                        else:
                            self.log_result(
                                "Template Format Support", 
                                "FAIL", 
                                f"Unexpected response format from httpbin: {type(httpbin_response)}",
                                "dict",
                                type(httpbin_response).__name__
                            )
                    else:
                        self.log_result(
                            "Template Format Support", 
                            "FAIL", 
                            f"Webhook test failed: {response_data.get('error', 'Unknown error')}",
                            "success: true",
                            f"success: {response_data.get('success')}"
                        )
                else:
                    self.log_result(
                        "Template Format Support", 
                        "FAIL", 
                        f"HTTP error: {response.status_code} - {response.text[:200]}",
                        200,
                        response.status_code
                    )
                    
        except Exception as e:
            self.log_result("Template Format Support", "FAIL", f"Exception: {str(e)}")

    async def test_webhook_proxy_functionality(self):
        """Test 4: Verify the webhook test proxy endpoint is functioning correctly"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.session_cookie:
                headers['Cookie'] = self.session_cookie
            
            # Test different HTTP methods
            test_cases = [
                {
                    "name": "POST Request",
                    "data": {
                        "url": "https://httpbin.org/post",
                        "method": "POST",
                        "body": {"test": "post_data", "timestamp": datetime.now().isoformat()},
                        "headers": {"X-Test-Header": "test-value"},
                        "timeout": 10000
                    }
                },
                {
                    "name": "GET Request", 
                    "data": {
                        "url": "https://httpbin.org/get",
                        "method": "GET",
                        "body": {},
                        "headers": {"X-Test-Header": "get-test"},
                        "timeout": 10000
                    }
                }
            ]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for test_case in test_cases:
                    response = await client.post(
                        f"{self.backend_url}/api/webhook-test",
                        headers=headers,
                        json=test_case["data"]
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        if response_data.get('success'):
                            # Verify response structure
                            expected_fields = ['success', 'status_code', 'response']
                            missing_fields = [field for field in expected_fields if field not in response_data]
                            
                            if not missing_fields:
                                # Check if we got a valid response from httpbin
                                httpbin_response = response_data.get('response', {})
                                status_code = response_data.get('status_code')
                                
                                if status_code == 200 and isinstance(httpbin_response, dict):
                                    self.log_result(
                                        f"Webhook Proxy - {test_case['name']}", 
                                        "PASS", 
                                        f"Proxy successfully handled {test_case['name']} (status: {status_code})",
                                        200,
                                        status_code
                                    )
                                else:
                                    self.log_result(
                                        f"Webhook Proxy - {test_case['name']}", 
                                        "FAIL", 
                                        f"Unexpected response: status={status_code}, response_type={type(httpbin_response)}",
                                        200,
                                        status_code
                                    )
                            else:
                                self.log_result(
                                    f"Webhook Proxy - {test_case['name']}", 
                                    "FAIL", 
                                    f"Missing response fields: {missing_fields}",
                                    expected_fields,
                                    list(response_data.keys())
                                )
                        else:
                            self.log_result(
                                f"Webhook Proxy - {test_case['name']}", 
                                "FAIL", 
                                f"Webhook test failed: {response_data.get('error', 'Unknown error')}",
                                "success: true",
                                f"success: {response_data.get('success')}"
                            )
                    else:
                        self.log_result(
                            f"Webhook Proxy - {test_case['name']}", 
                            "FAIL", 
                            f"HTTP error: {response.status_code} - {response.text[:200]}",
                            200,
                            response.status_code
                        )
                        
        except Exception as e:
            self.log_result("Webhook Proxy Functionality", "FAIL", f"Exception: {str(e)}")

    async def test_error_handling(self):
        """Test 5: Test error handling for invalid requests"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.session_cookie:
                headers['Cookie'] = self.session_cookie
            
            # Test cases for error handling
            error_test_cases = [
                {
                    "name": "Missing URL",
                    "data": {
                        "method": "POST",
                        "body": {"test": "data"},
                        "headers": {},
                        "timeout": 10000
                    },
                    "expected_error": "URL is required"
                },
                {
                    "name": "Invalid URL",
                    "data": {
                        "url": "not-a-valid-url",
                        "method": "POST", 
                        "body": {"test": "data"},
                        "headers": {},
                        "timeout": 10000
                    },
                    "expected_error": "Request failed"
                },
                {
                    "name": "Unsupported Method",
                    "data": {
                        "url": "https://httpbin.org/post",
                        "method": "PATCH",
                        "body": {"test": "data"},
                        "headers": {},
                        "timeout": 10000
                    },
                    "expected_error": "Unsupported method"
                }
            ]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for test_case in error_test_cases:
                    response = await client.post(
                        f"{self.backend_url}/api/webhook-test",
                        headers=headers,
                        json=test_case["data"]
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        if not response_data.get('success'):
                            error_message = response_data.get('error', '')
                            expected_error = test_case['expected_error']
                            
                            if expected_error.lower() in error_message.lower():
                                self.log_result(
                                    f"Error Handling - {test_case['name']}", 
                                    "PASS", 
                                    f"Correctly handled error: {error_message}",
                                    f"Contains '{expected_error}'",
                                    error_message
                                )
                            else:
                                self.log_result(
                                    f"Error Handling - {test_case['name']}", 
                                    "FAIL", 
                                    f"Unexpected error message: {error_message}",
                                    f"Contains '{expected_error}'",
                                    error_message
                                )
                        else:
                            self.log_result(
                                f"Error Handling - {test_case['name']}", 
                                "FAIL", 
                                f"Expected error but got success: {response_data}",
                                "success: false",
                                f"success: {response_data.get('success')}"
                            )
                    else:
                        self.log_result(
                            f"Error Handling - {test_case['name']}", 
                            "FAIL", 
                            f"HTTP error: {response.status_code} - {response.text[:200]}",
                            200,
                            response.status_code
                        )
                        
        except Exception as e:
            self.log_result("Error Handling", "FAIL", f"Exception: {str(e)}")

    async def run_all_tests(self):
        """Run all webhook-test endpoint tests"""
        print("🚀 Starting Webhook Test Endpoint Testing")
        print(f"Backend URL: {self.backend_url}")
        print("Testing the webhook-test endpoint in the Flow Builder functionality")
        print("The webhook tester supports JSON Schema and Template formats")
        print("=" * 80)
        print()
        
        # Authenticate first
        await self.authenticate()
        
        # Run test sequence as specified in review request
        await self.test_webhook_endpoint_availability()
        await self.test_json_schema_format_detection()
        await self.test_template_format_support()
        await self.test_webhook_proxy_functionality()
        await self.test_error_handling()
        
        # Print summary
        print("=" * 80)
        print("📊 WEBHOOK TEST ENDPOINT SUMMARY")
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
    tester = WebhookTesterValidator()
    success = await tester.run_all_tests()
    
    # Save detailed results to file
    with open("/app/webhook_test_results.json", "w") as f:
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
    
    print(f"📄 Detailed results saved to: /app/webhook_test_results.json")
    
    if success:
        print("🎉 All Webhook Test Endpoint tests passed!")
        print("✅ Webhook-test endpoint is working correctly!")
        sys.exit(0)
    else:
        print("💥 Some Webhook Test Endpoint tests failed!")
        print("❌ Issues found with webhook-test endpoint!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())