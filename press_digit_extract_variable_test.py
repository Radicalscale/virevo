#!/usr/bin/env python3
"""
Press Digit and Extract Variable Node Testing for Retell AI Clone
Tests the Press Digit (DTMF) and Extract Variable node implementations
"""

import asyncio
import aiohttp
import json
import time
import os
from typing import Dict, List, Optional

# Get backend URL from frontend environment
BACKEND_URL = "https://tts-guardian.preview.emergentagent.com/api"

class PressDigitExtractVariableTester:
    def __init__(self):
        self.session = None
        self.test_results = []
        self.test_agent_id = None
        
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
    
    async def setup_call_flow_agent(self):
        """Create or find a call_flow agent for testing"""
        try:
            # Check for existing call_flow agents
            async with self.session.get(f"{BACKEND_URL}/agents") as response:
                if response.status == 200:
                    agents = await response.json()
                    for agent in agents:
                        if agent.get("agent_type") == "call_flow":
                            self.test_agent_id = agent["id"]
                            self.log_result(
                                "Setup Call Flow Agent", 
                                True, 
                                f"Found existing call_flow agent: {agent['name']} (ID: {self.test_agent_id})"
                            )
                            return True
            
            # Create new call_flow agent if none exists
            agent_data = {
                "agent_type": "call_flow",
                "name": "Press Digit & Extract Variable Test Agent",
                "description": "AI agent for testing press digit and extract variable nodes",
                "voice": "Rachel",
                "language": "English",
                "model": "gpt-4-turbo",
                "system_prompt": "",
                "call_flow": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents", json=agent_data) as response:
                if response.status == 200:
                    agent = await response.json()
                    self.test_agent_id = agent['id']
                    self.log_result(
                        "Setup Call Flow Agent", 
                        True, 
                        f"Created call_flow agent: {agent['name']} (ID: {self.test_agent_id})"
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Setup Call Flow Agent", 
                        False, 
                        f"Failed to create agent - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Setup Call Flow Agent", False, f"Error setting up agent: {str(e)}")
            return False

    async def test_press_digit_node_implementation(self):
        """Test Press Digit Node implementation as requested in review"""
        print(f"\n🔢 Testing Press Digit Node Implementation")
        print("=" * 60)
        
        # Test 1: Create Flow with Press Digit as specified in review request
        flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Begin",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "press_digit",
                "label": "Press Digit Menu",
                "data": {
                    "prompt_message": "Press 1 for Option 1, 2 for Option 2, or 0 for Operator",
                    "digit_mappings": {
                        "1": "3",  # Option 1 node
                        "2": "4",  # Option 2 node
                        "0": "5"   # Operator node
                    }
                }
            },
            {
                "id": "3",
                "type": "conversation",
                "label": "Option 1",
                "data": {
                    "mode": "script",
                    "content": "You selected Option 1. How can I help you?",
                    "transitions": []
                }
            },
            {
                "id": "4",
                "type": "conversation",
                "label": "Option 2", 
                "data": {
                    "mode": "script",
                    "content": "You selected Option 2. What do you need?",
                    "transitions": []
                }
            },
            {
                "id": "5",
                "type": "conversation",
                "label": "Operator",
                "data": {
                    "mode": "script",
                    "content": "Connecting you to an operator. Please hold.",
                    "transitions": []
                }
            },
            {
                "id": "6",
                "type": "ending",
                "label": "End",
                "data": {
                    "mode": "script",
                    "content": "Thank you for calling. Goodbye!",
                    "transitions": []
                }
            }
        ]
        
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=flow_data) as response:
                if response.status == 200:
                    self.log_result(
                        "Test 1 - Create Flow with Press Digit", 
                        True, 
                        "Successfully created flow: Start → Press Digit (map 1→Option1, 2→Option2, 0→Operator) → End"
                    )
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 1 - Create Flow with Press Digit", 
                        False, 
                        f"Failed to create flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 1 - Create Flow with Press Digit", False, f"Error creating flow: {str(e)}")
            return False
        
        # Test 2: Test Valid Digit Input - "1"
        try:
            request_data = {
                "message": "1",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    # Should route to Option 1 node
                    expected_response = "You selected Option 1. How can I help you?"
                    if expected_response in response_text or ("option 1" in response_text.lower() and "help" in response_text.lower()):
                        self.log_result(
                            "Test 2 - Valid Digit Input (1)", 
                            True, 
                            f"Digit '1' correctly routed to Option1 node", 
                            {"user_input": "1", "response": response_text, "latency": data.get('latency')}
                        )
                    else:
                        self.log_result(
                            "Test 2 - Valid Digit Input (1)", 
                            False, 
                            f"Digit '1' routing failed", 
                            {"expected": expected_response, "received": response_text}
                        )
                        return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 2 - Valid Digit Input (1)", 
                        False, 
                        f"Failed to process digit - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 2 - Valid Digit Input (1)", False, f"Error testing digit 1: {str(e)}")
            return False
        
        # Test 3: Test Multiple Digits - "2", "0", "*", "#"
        digit_tests = [
            {"digit": "2", "expected_node": "Option 2", "expected_text": "You selected Option 2"},
            {"digit": "0", "expected_node": "Operator", "expected_text": "Connecting you to an operator"},
            {"digit": "*", "expected_node": "None", "expected_text": "no action is configured"},
            {"digit": "#", "expected_node": "None", "expected_text": "no action is configured"}
        ]
        
        for test_case in digit_tests:
            try:
                request_data = {
                    "message": test_case["digit"],
                    "conversation_history": []
                }
                
                async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get('response', '')
                        
                        # Check if response matches expected behavior
                        if test_case["expected_node"] == "None":
                            # Unmapped digits should return appropriate message
                            if "no action" in response_text.lower() or "not configured" in response_text.lower():
                                self.log_result(
                                    f"Test 3 - Multiple Digits ('{test_case['digit']}')", 
                                    True, 
                                    f"Unmapped digit '{test_case['digit']}' correctly handled", 
                                    {"digit": test_case["digit"], "response": response_text}
                                )
                            else:
                                self.log_result(
                                    f"Test 3 - Multiple Digits ('{test_case['digit']}')", 
                                    False, 
                                    f"Unmapped digit '{test_case['digit']}' not handled correctly", 
                                    {"expected": "no action configured", "received": response_text}
                                )
                                return False
                        else:
                            # Mapped digits should route to correct nodes
                            if test_case["expected_text"].lower() in response_text.lower():
                                self.log_result(
                                    f"Test 3 - Multiple Digits ('{test_case['digit']}')", 
                                    True, 
                                    f"Digit '{test_case['digit']}' correctly routed to {test_case['expected_node']}", 
                                    {"digit": test_case["digit"], "response": response_text}
                                )
                            else:
                                self.log_result(
                                    f"Test 3 - Multiple Digits ('{test_case['digit']}')", 
                                    False, 
                                    f"Digit '{test_case['digit']}' routing failed", 
                                    {"expected": test_case["expected_text"], "received": response_text}
                                )
                                return False
                    else:
                        error_text = await response.text()
                        self.log_result(
                            f"Test 3 - Multiple Digits ('{test_case['digit']}')", 
                            False, 
                            f"Failed to process digit - Status: {response.status}", 
                            {"error": error_text}
                        )
                        return False
            except Exception as e:
                self.log_result(f"Test 3 - Multiple Digits ('{test_case['digit']}')", False, f"Error testing digit: {str(e)}")
                return False
        
        # Test 4: Test Invalid Input - "hello"
        try:
            request_data = {
                "message": "hello",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    # Should return prompt message asking for digit
                    expected_prompt = "Press 1 for Option 1, 2 for Option 2, or 0 for Operator"
                    if expected_prompt in response_text or ("press" in response_text.lower() and "digit" in response_text.lower()):
                        self.log_result(
                            "Test 4 - Invalid Input (hello)", 
                            True, 
                            f"Invalid input correctly returns prompt message", 
                            {"user_input": "hello", "response": response_text}
                        )
                    else:
                        self.log_result(
                            "Test 4 - Invalid Input (hello)", 
                            False, 
                            f"Invalid input handling failed", 
                            {"expected_prompt": expected_prompt, "received": response_text}
                        )
                        return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 4 - Invalid Input (hello)", 
                        False, 
                        f"Failed to process invalid input - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 4 - Invalid Input (hello)", False, f"Error testing invalid input: {str(e)}")
            return False
        
        return True

    async def test_extract_variable_node_implementation(self):
        """Test Extract Variable Node implementation as requested in review"""
        print(f"\n📋 Testing Extract Variable Node Implementation")
        print("=" * 60)
        
        # Test 5: Create Flow with Extract Variable as specified in review request
        flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Begin",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "extract_variable",
                "label": "Extract Name",
                "data": {
                    "variable_name": "customer_name",
                    "extraction_prompt": "Extract the customer's full name",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "After successful extraction",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "conversation",
                "label": "Confirmation",
                "data": {
                    "mode": "script",
                    "content": "Thank you, {{customer_name}}. I have your name recorded.",
                    "transitions": [
                        {
                            "id": "t2",
                            "condition": "user wants to end",
                            "nextNode": "4"
                        }
                    ]
                }
            },
            {
                "id": "4",
                "type": "ending",
                "label": "End",
                "data": {
                    "mode": "script",
                    "content": "Goodbye, {{customer_name}}!",
                    "transitions": []
                }
            }
        ]
        
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=flow_data) as response:
                if response.status == 200:
                    self.log_result(
                        "Test 5 - Create Flow with Extract Variable", 
                        True, 
                        "Successfully created flow: Start → Extract Variable (extract user name) → Confirmation → End"
                    )
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 5 - Create Flow with Extract Variable", 
                        False, 
                        f"Failed to create flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 5 - Create Flow with Extract Variable", False, f"Error creating flow: {str(e)}")
            return False
        
        # Test 6: Test Successful Extraction - "My name is John Smith"
        try:
            request_data = {
                "message": "My name is John Smith",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    # Should extract "John Smith" and transition to confirmation node
                    if "john smith" in response_text.lower() and ("thank you" in response_text.lower() or "recorded" in response_text.lower()):
                        self.log_result(
                            "Test 6 - Successful Extraction (Name)", 
                            True, 
                            f"Successfully extracted 'John Smith' and transitioned to confirmation", 
                            {"user_input": "My name is John Smith", "response": response_text, "latency": data.get('latency')}
                        )
                    else:
                        self.log_result(
                            "Test 6 - Successful Extraction (Name)", 
                            False, 
                            f"Name extraction or transition failed", 
                            {"expected": "John Smith in confirmation", "received": response_text}
                        )
                        return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 6 - Successful Extraction (Name)", 
                        False, 
                        f"Failed to process extraction - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 6 - Successful Extraction (Name)", False, f"Error testing name extraction: {str(e)}")
            return False
        
        # Test 7: Test Email Extraction
        email_flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Begin",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "extract_variable",
                "label": "Extract Email",
                "data": {
                    "variable_name": "user_email",
                    "extraction_prompt": "Extract the email address",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "After successful extraction",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "conversation",
                "label": "Email Confirmation",
                "data": {
                    "mode": "script",
                    "content": "Got your email: {{user_email}}",
                    "transitions": []
                }
            }
        ]
        
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=email_flow_data) as response:
                if response.status == 200:
                    request_data = {
                        "message": "Contact me at john@example.com",
                        "conversation_history": []
                    }
                    
                    async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_text = data.get('response', '')
                            
                            # Should extract "john@example.com"
                            if "john@example.com" in response_text.lower():
                                self.log_result(
                                    "Test 7 - Email Extraction", 
                                    True, 
                                    f"Successfully extracted 'john@example.com'", 
                                    {"user_input": "Contact me at john@example.com", "response": response_text}
                                )
                            else:
                                self.log_result(
                                    "Test 7 - Email Extraction", 
                                    False, 
                                    f"Email extraction failed", 
                                    {"expected": "john@example.com", "received": response_text}
                                )
                                return False
                        else:
                            error_text = await response.text()
                            self.log_result(
                                "Test 7 - Email Extraction", 
                                False, 
                                f"Failed to process email extraction - Status: {response.status}", 
                                {"error": error_text}
                            )
                            return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 7 - Email Extraction", 
                        False, 
                        f"Failed to create email flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 7 - Email Extraction", False, f"Error testing email extraction: {str(e)}")
            return False
        
        # Test 8: Test Date Extraction
        date_flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Begin",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "extract_variable",
                "label": "Extract Date",
                "data": {
                    "variable_name": "meeting_date",
                    "extraction_prompt": "Extract the meeting date",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "After successful extraction",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "conversation",
                "label": "Date Confirmation",
                "data": {
                    "mode": "script",
                    "content": "Meeting scheduled for: {{meeting_date}}",
                    "transitions": []
                }
            }
        ]
        
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=date_flow_data) as response:
                if response.status == 200:
                    request_data = {
                        "message": "Let's meet on Friday",
                        "conversation_history": []
                    }
                    
                    async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_text = data.get('response', '')
                            
                            # Should extract "Friday"
                            if "friday" in response_text.lower():
                                self.log_result(
                                    "Test 8 - Date Extraction", 
                                    True, 
                                    f"Successfully extracted 'Friday'", 
                                    {"user_input": "Let's meet on Friday", "response": response_text}
                                )
                            else:
                                self.log_result(
                                    "Test 8 - Date Extraction", 
                                    False, 
                                    f"Date extraction failed", 
                                    {"expected": "Friday", "received": response_text}
                                )
                                return False
                        else:
                            error_text = await response.text()
                            self.log_result(
                                "Test 8 - Date Extraction", 
                                False, 
                                f"Failed to process date extraction - Status: {response.status}", 
                                {"error": error_text}
                            )
                            return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 8 - Date Extraction", 
                        False, 
                        f"Failed to create date flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 8 - Date Extraction", False, f"Error testing date extraction: {str(e)}")
            return False
        
        # Test 9: Test Failed Extraction
        try:
            request_data = {
                "message": "I don't want to provide that information",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    # Should return error message asking to repeat
                    if ("couldn't find" in response_text.lower() or "please provide" in response_text.lower() or 
                        "repeat" in response_text.lower() or "again" in response_text.lower()):
                        self.log_result(
                            "Test 9 - Failed Extraction", 
                            True, 
                            f"Failed extraction correctly handled with error message", 
                            {"user_input": "I don't want to provide that information", "response": response_text}
                        )
                    else:
                        self.log_result(
                            "Test 9 - Failed Extraction", 
                            False, 
                            f"Failed extraction not handled correctly", 
                            {"expected": "error message asking to repeat", "received": response_text}
                        )
                        return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 9 - Failed Extraction", 
                        False, 
                        f"Failed to process failed extraction - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 9 - Failed Extraction", False, f"Error testing failed extraction: {str(e)}")
            return False
        
        # Test 10: Variable Replacement - Test using extracted variable in next node
        variable_replacement_flow = [
            {
                "id": "1",
                "type": "start",
                "label": "Begin",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "extract_variable",
                "label": "Extract Customer Name",
                "data": {
                    "variable_name": "customer_name",
                    "extraction_prompt": "Extract the customer's full name",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "After successful extraction",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "conversation",
                "label": "Personalized Response",
                "data": {
                    "mode": "script",
                    "content": "Hello {{customer_name}}, welcome to our service! How can I assist you today?",
                    "transitions": []
                }
            }
        ]
        
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=variable_replacement_flow) as response:
                if response.status == 200:
                    request_data = {
                        "message": "Hi, I'm Sarah Johnson",
                        "conversation_history": []
                    }
                    
                    async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_text = data.get('response', '')
                            
                            # Should extract "Sarah Johnson" and use it in the personalized response
                            if "sarah johnson" in response_text.lower() and "welcome" in response_text.lower():
                                self.log_result(
                                    "Test 10 - Variable Replacement", 
                                    True, 
                                    f"Variable replacement working correctly in conversation script", 
                                    {"user_input": "Hi, I'm Sarah Johnson", "response": response_text}
                                )
                            else:
                                self.log_result(
                                    "Test 10 - Variable Replacement", 
                                    False, 
                                    f"Variable replacement failed", 
                                    {"expected": "Sarah Johnson in welcome message", "received": response_text}
                                )
                                return False
                        else:
                            error_text = await response.text()
                            self.log_result(
                                "Test 10 - Variable Replacement", 
                                False, 
                                f"Failed to process variable replacement test - Status: {response.status}", 
                                {"error": error_text}
                            )
                            return False
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 10 - Variable Replacement", 
                        False, 
                        f"Failed to create variable replacement flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 10 - Variable Replacement", False, f"Error testing variable replacement: {str(e)}")
            return False
        
        return True

    async def run_all_tests(self):
        """Run all Press Digit and Extract Variable tests"""
        print("🚀 Starting Press Digit and Extract Variable Node Testing")
        print("=" * 60)
        
        # Setup
        if not await self.setup_call_flow_agent():
            return False
        
        # Run tests
        press_digit_success = await self.test_press_digit_node_implementation()
        extract_variable_success = await self.test_extract_variable_node_implementation()
        
        # Print summary
        print(f"\n📊 Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")
        
        return passed_tests == total_tests

async def main():
    """Main test execution"""
    async with PressDigitExtractVariableTester() as tester:
        success = await tester.run_all_tests()
        return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)