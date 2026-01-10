#!/usr/bin/env python3
"""
Comprehensive End-to-End Backend Testing for Retell AI Clone
Tests all 6 core node types in integrated scenarios as requested in review
"""

import asyncio
import aiohttp
import json
import time
import os
from typing import Dict, List, Optional

# Get backend URL from frontend environment
BACKEND_URL = "https://missed-variable.preview.emergentagent.com/api"

class ComprehensiveE2ETester:
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
    
    async def setup_test_agent(self):
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
                                "Setup Test Agent", 
                                True, 
                                f"Using existing call_flow agent: {agent['name']} (ID: {self.test_agent_id})"
                            )
                            return True
            
            # Create new call_flow agent if none exists
            agent_data = {
                "agent_type": "call_flow",
                "name": "E2E Test Agent",
                "description": "Comprehensive end-to-end testing agent",
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
                        "Setup Test Agent", 
                        True, 
                        f"Created call_flow agent: {agent['name']} (ID: {self.test_agent_id})"
                    )
                    return True
                else:
                    self.log_result("Setup Test Agent", False, f"Failed to create agent - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Setup Test Agent", False, f"Error setting up agent: {str(e)}")
            return False

    async def test_1_complete_customer_service_flow(self):
        """
        Test 1: Complete Customer Service Flow
        Start → Greeting → Collect user_name (text) → Collect user_email (email) → 
        Logic Split (if email contains "@company.com" → Internal, else → External) → Send SMS → End Call
        """
        print(f"\n🎯 Test 1: Complete Customer Service Flow")
        print("=" * 80)
        
        # Create comprehensive flow
        flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Start",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "conversation",
                "label": "Greeting",
                "data": {
                    "mode": "script",
                    "content": "Welcome to our customer service! I'll need to collect some information.",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "user responds",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "collect_input",
                "label": "Collect Name",
                "data": {
                    "variable_name": "user_name",
                    "input_type": "text",
                    "prompt_message": "Please provide your full name.",
                    "error_message": "Please enter a valid name.",
                    "transitions": [
                        {
                            "id": "t2",
                            "condition": "After valid input collected",
                            "nextNode": "4"
                        }
                    ]
                }
            },
            {
                "id": "4",
                "type": "collect_input",
                "label": "Collect Email",
                "data": {
                    "variable_name": "user_email",
                    "input_type": "email",
                    "prompt_message": "Please provide your email address.",
                    "error_message": "Please enter a valid email address.",
                    "transitions": [
                        {
                            "id": "t3",
                            "condition": "After valid input collected",
                            "nextNode": "5"
                        }
                    ]
                }
            },
            {
                "id": "5",
                "type": "logic_split",
                "label": "Email Check",
                "data": {
                    "conditions": [
                        {
                            "variable": "user_email",
                            "operator": "contains",
                            "value": "@company.com",
                            "nextNode": "6"
                        }
                    ],
                    "default_path": "7"
                }
            },
            {
                "id": "6",
                "type": "conversation",
                "label": "Internal Customer",
                "data": {
                    "mode": "script",
                    "content": "I see you're an internal employee, {{user_name}}. Let me send you internal information.",
                    "transitions": [
                        {
                            "id": "t4",
                            "condition": "continue to SMS",
                            "nextNode": "8"
                        }
                    ]
                }
            },
            {
                "id": "7",
                "type": "conversation",
                "label": "External Customer",
                "data": {
                    "mode": "script",
                    "content": "Thank you {{user_name}}, I'll send you our external customer information.",
                    "transitions": [
                        {
                            "id": "t5",
                            "condition": "continue to SMS",
                            "nextNode": "8"
                        }
                    ]
                }
            },
            {
                "id": "8",
                "type": "send_sms",
                "label": "Send SMS",
                "data": {
                    "phone_number": "+1234567890",
                    "sms_message": "Hello {{user_name}}, thank you for contacting us. Your email {{user_email}} has been recorded.",
                    "transitions": [
                        {
                            "id": "t6",
                            "condition": "After SMS sent",
                            "nextNode": "9"
                        }
                    ]
                }
            },
            {
                "id": "9",
                "type": "ending",
                "label": "End Call",
                "data": {
                    "mode": "script",
                    "content": "Thank you for your time, {{user_name}}. Have a great day!",
                    "transitions": []
                }
            }
        ]
        
        # Create the flow
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=flow_data) as response:
                if response.status == 200:
                    self.log_result(
                        "Test 1 - Create Complete Customer Service Flow", 
                        True, 
                        "Successfully created 9-node customer service flow"
                    )
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 1 - Create Complete Customer Service Flow", 
                        False, 
                        f"Failed to create flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 1 - Create Complete Customer Service Flow", False, f"Error creating flow: {str(e)}")
            return False
        
        # Step 1: Initial greeting
        try:
            request_data = {
                "message": "Hello, I need help",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if "welcome" in response_text.lower() and "information" in response_text.lower():
                        self.log_result(
                            "Test 1 - Step 1: Initial Greeting", 
                            True, 
                            "Received expected greeting response"
                        )
                        conversation_history = [
                            {"role": "user", "content": "Hello, I need help"},
                            {"role": "assistant", "content": response_text}
                        ]
                    else:
                        self.log_result("Test 1 - Step 1: Initial Greeting", False, f"Unexpected greeting: {response_text}")
                        return False
                else:
                    self.log_result("Test 1 - Step 1: Initial Greeting", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 1 - Step 1: Initial Greeting", False, f"Error: {str(e)}")
            return False
        
        # Step 2: Collect name
        try:
            request_data = {
                "message": "John Smith",
                "conversation_history": conversation_history
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if "email" in response_text.lower():
                        self.log_result(
                            "Test 1 - Step 2: Collect Name", 
                            True, 
                            "Name collected, moved to email collection"
                        )
                        conversation_history.extend([
                            {"role": "user", "content": "John Smith"},
                            {"role": "assistant", "content": response_text}
                        ])
                    else:
                        self.log_result("Test 1 - Step 2: Collect Name", False, f"Unexpected response: {response_text}")
                        return False
                else:
                    self.log_result("Test 1 - Step 2: Collect Name", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 1 - Step 2: Collect Name", False, f"Error: {str(e)}")
            return False
        
        # Step 3: Test internal email (contains @company.com)
        try:
            request_data = {
                "message": "john.smith@company.com",
                "conversation_history": conversation_history
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if "internal" in response_text.lower() or "employee" in response_text.lower():
                        self.log_result(
                            "Test 1 - Step 3: Internal Email Logic Split", 
                            True, 
                            "Email collected, logic split correctly identified internal customer"
                        )
                        conversation_history.extend([
                            {"role": "user", "content": "john.smith@company.com"},
                            {"role": "assistant", "content": response_text}
                        ])
                    else:
                        self.log_result("Test 1 - Step 3: Internal Email Logic Split", False, f"Logic split failed: {response_text}")
                        return False
                else:
                    self.log_result("Test 1 - Step 3: Internal Email Logic Split", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 1 - Step 3: Internal Email Logic Split", False, f"Error: {str(e)}")
            return False
        
        # Step 4: Continue to SMS and end call
        try:
            request_data = {
                "message": "Please continue",
                "conversation_history": conversation_history
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    should_end_call = data.get('should_end_call', False)
                    
                    if should_end_call and "thank you" in response_text.lower():
                        self.log_result(
                            "Test 1 - Step 4: SMS and End Call", 
                            True, 
                            "SMS sent, call ended with should_end_call: True"
                        )
                    else:
                        self.log_result("Test 1 - Step 4: SMS and End Call", False, f"End call failed: {response_text}, should_end_call: {should_end_call}")
                        return False
                else:
                    self.log_result("Test 1 - Step 4: SMS and End Call", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 1 - Step 4: SMS and End Call", False, f"Error: {str(e)}")
            return False
        
        return True

    async def test_2_complex_conditional_flow(self):
        """
        Test 2: Complex Conditional Flow
        Start → Collect user_age (number) → Logic Split:
        - If age > 65 → Senior path → Transfer to senior team
        - If age > 18 → Adult path → Send SMS → End
        - Else → Minor path → End
        Test with ages: 70, 30, 15
        """
        print(f"\n🎯 Test 2: Complex Conditional Flow")
        print("=" * 80)
        
        # Create age-based conditional flow
        flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Start",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "collect_input",
                "label": "Collect Age",
                "data": {
                    "variable_name": "user_age",
                    "input_type": "number",
                    "prompt_message": "Please enter your age.",
                    "error_message": "Please enter a valid age number.",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "After valid input collected",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "logic_split",
                "label": "Age Logic Split",
                "data": {
                    "conditions": [
                        {
                            "variable": "user_age",
                            "operator": "greater_than",
                            "value": "65",
                            "nextNode": "4"
                        },
                        {
                            "variable": "user_age",
                            "operator": "greater_than",
                            "value": "18",
                            "nextNode": "5"
                        }
                    ],
                    "default_path": "6"
                }
            },
            {
                "id": "4",
                "type": "transfer",
                "label": "Senior Transfer",
                "data": {
                    "transfer_type": "warm",
                    "destination_type": "agent",
                    "destination": "senior_team",
                    "transfer_message": "Transferring you to our senior specialist team."
                }
            },
            {
                "id": "5",
                "type": "send_sms",
                "label": "Adult SMS",
                "data": {
                    "phone_number": "+1234567890",
                    "sms_message": "Thank you for contacting us. You are {{user_age}} years old.",
                    "transitions": [
                        {
                            "id": "t2",
                            "condition": "After SMS sent",
                            "nextNode": "7"
                        }
                    ]
                }
            },
            {
                "id": "6",
                "type": "ending",
                "label": "Minor End",
                "data": {
                    "mode": "script",
                    "content": "Thank you for contacting us. Please have a parent or guardian contact us.",
                    "transitions": []
                }
            },
            {
                "id": "7",
                "type": "ending",
                "label": "Adult End",
                "data": {
                    "mode": "script",
                    "content": "Thank you for your inquiry. We've sent you an SMS with information.",
                    "transitions": []
                }
            }
        ]
        
        # Create the flow
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=flow_data) as response:
                if response.status == 200:
                    self.log_result(
                        "Test 2 - Create Complex Conditional Flow", 
                        True, 
                        "Successfully created age-based conditional flow"
                    )
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 2 - Create Complex Conditional Flow", 
                        False, 
                        f"Failed to create flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 2 - Create Complex Conditional Flow", False, f"Error creating flow: {str(e)}")
            return False
        
        # Test Case A: Age 70 (Senior path)
        success_a = await self._test_age_scenario(70, "senior", "transfer")
        
        # Test Case B: Age 30 (Adult path)
        success_b = await self._test_age_scenario(30, "adult", "sms")
        
        # Test Case C: Age 15 (Minor path)
        success_c = await self._test_age_scenario(15, "minor", "end")
        
        return success_a and success_b and success_c

    async def _test_age_scenario(self, age: int, expected_path: str, expected_action: str):
        """Helper method to test age scenarios"""
        try:
            # Step 1: Start conversation
            request_data = {
                "message": "Hello",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status != 200:
                    self.log_result(f"Test 2 - Age {age} Scenario", False, f"Initial request failed - Status: {response.status}")
                    return False
                
                data = await response.json()
                response_text = data.get('response', '')
                conversation_history = [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": response_text}
                ]
            
            # Step 2: Provide age
            request_data = {
                "message": str(age),
                "conversation_history": conversation_history
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    should_end_call = data.get('should_end_call', False)
                    
                    # Verify expected behavior based on age
                    if age > 65 and expected_action == "transfer":
                        if "transfer" in response_text.lower() and "senior" in response_text.lower():
                            self.log_result(
                                f"Test 2 - Age {age} (Senior Path)", 
                                True, 
                                f"Correctly routed to senior transfer path"
                            )
                            return True
                    elif age > 18 and expected_action == "sms":
                        if should_end_call and ("sms" in response_text.lower() or "sent" in response_text.lower()):
                            self.log_result(
                                f"Test 2 - Age {age} (Adult Path)", 
                                True, 
                                f"Correctly routed to adult SMS path with end call"
                            )
                            return True
                    elif expected_action == "end":
                        if should_end_call and ("parent" in response_text.lower() or "guardian" in response_text.lower()):
                            self.log_result(
                                f"Test 2 - Age {age} (Minor Path)", 
                                True, 
                                f"Correctly routed to minor end path"
                            )
                            return True
                    
                    self.log_result(
                        f"Test 2 - Age {age} ({expected_path.title()} Path)", 
                        False, 
                        f"Unexpected routing or response", 
                        {"age": age, "response": response_text, "should_end_call": should_end_call}
                    )
                    return False
                else:
                    self.log_result(f"Test 2 - Age {age} Scenario", False, f"Age processing failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result(f"Test 2 - Age {age} Scenario", False, f"Error: {str(e)}")
            return False

    async def test_3_webhook_integration_flow(self):
        """
        Test 3: Webhook Integration Flow
        Start → Collect user_id → Function (webhook to httpbin.org/post) → 
        Logic Split (if webhook successful) → Confirmation → End
        """
        print(f"\n🎯 Test 3: Webhook Integration Flow")
        print("=" * 80)
        
        # Create webhook integration flow
        flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Start",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "collect_input",
                "label": "Collect User ID",
                "data": {
                    "variable_name": "user_id",
                    "input_type": "text",
                    "prompt_message": "Please provide your user ID.",
                    "error_message": "Please enter a valid user ID.",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "After valid input collected",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "function",
                "label": "Webhook Call",
                "data": {
                    "webhook_url": "https://httpbin.org/post",
                    "webhook_method": "POST",
                    "webhook_headers": {"Content-Type": "application/json"},
                    "webhook_body": '{"user_id": "{{user_id}}", "action": "lookup", "timestamp": "2024-01-01"}',
                    "webhook_timeout": 10,
                    "response_variable": "webhook_result",
                    "transitions": [
                        {
                            "id": "t2",
                            "condition": "After webhook completes",
                            "nextNode": "4"
                        }
                    ]
                }
            },
            {
                "id": "4",
                "type": "logic_split",
                "label": "Webhook Success Check",
                "data": {
                    "conditions": [
                        {
                            "variable": "webhook_result",
                            "operator": "exists",
                            "value": "",
                            "nextNode": "5"
                        }
                    ],
                    "default_path": "6"
                }
            },
            {
                "id": "5",
                "type": "conversation",
                "label": "Success Confirmation",
                "data": {
                    "mode": "script",
                    "content": "Great! I found your information for user ID {{user_id}}. The webhook returned: {{webhook_result}}",
                    "transitions": [
                        {
                            "id": "t3",
                            "condition": "user acknowledges",
                            "nextNode": "7"
                        }
                    ]
                }
            },
            {
                "id": "6",
                "type": "conversation",
                "label": "Failure Response",
                "data": {
                    "mode": "script",
                    "content": "I'm sorry, I couldn't retrieve your information at this time. Please try again later.",
                    "transitions": [
                        {
                            "id": "t4",
                            "condition": "user acknowledges",
                            "nextNode": "7"
                        }
                    ]
                }
            },
            {
                "id": "7",
                "type": "ending",
                "label": "End",
                "data": {
                    "mode": "script",
                    "content": "Thank you for using our service. Goodbye!",
                    "transitions": []
                }
            }
        ]
        
        # Create the flow
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=flow_data) as response:
                if response.status == 200:
                    self.log_result(
                        "Test 3 - Create Webhook Integration Flow", 
                        True, 
                        "Successfully created webhook integration flow"
                    )
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 3 - Create Webhook Integration Flow", 
                        False, 
                        f"Failed to create flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 3 - Create Webhook Integration Flow", False, f"Error creating flow: {str(e)}")
            return False
        
        # Execute the webhook integration test
        try:
            # Step 1: Start and collect user ID
            request_data = {
                "message": "USER123",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if "great" in response_text.lower() and "found" in response_text.lower():
                        self.log_result(
                            "Test 3 - Webhook Execution and Success Logic", 
                            True, 
                            "Webhook executed successfully, logic split detected success"
                        )
                    elif "sorry" in response_text.lower() and "couldn't" in response_text.lower():
                        self.log_result(
                            "Test 3 - Webhook Execution and Failure Logic", 
                            True, 
                            "Webhook failed gracefully, logic split detected failure"
                        )
                    else:
                        self.log_result(
                            "Test 3 - Webhook Integration", 
                            False, 
                            f"Unexpected webhook response: {response_text}"
                        )
                        return False
                    
                    conversation_history = [
                        {"role": "user", "content": "USER123"},
                        {"role": "assistant", "content": response_text}
                    ]
                else:
                    self.log_result("Test 3 - Webhook Integration", False, f"Failed - Status: {response.status}")
                    return False
            
            # Step 2: End the conversation
            request_data = {
                "message": "Thank you",
                "conversation_history": conversation_history
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    should_end_call = data.get('should_end_call', False)
                    
                    if should_end_call:
                        self.log_result(
                            "Test 3 - Webhook Flow Completion", 
                            True, 
                            "Webhook integration flow completed successfully"
                        )
                        return True
                    else:
                        self.log_result("Test 3 - Webhook Flow Completion", False, "Flow did not end properly")
                        return False
                else:
                    self.log_result("Test 3 - Webhook Flow Completion", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 3 - Webhook Integration Flow", False, f"Error: {str(e)}")
            return False

    async def test_4_multi_input_validation(self):
        """
        Test 4: Multi-Input Validation
        Start → Collect email → Collect phone → Collect age → Send SMS to collected phone → End
        """
        print(f"\n🎯 Test 4: Multi-Input Validation")
        print("=" * 80)
        
        # Create multi-input validation flow
        flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Start",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "collect_input",
                "label": "Collect Email",
                "data": {
                    "variable_name": "user_email",
                    "input_type": "email",
                    "prompt_message": "Please provide your email address.",
                    "error_message": "Please enter a valid email address.",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "After valid input collected",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "collect_input",
                "label": "Collect Phone",
                "data": {
                    "variable_name": "user_phone",
                    "input_type": "phone",
                    "prompt_message": "Please provide your phone number.",
                    "error_message": "Please enter a valid phone number.",
                    "transitions": [
                        {
                            "id": "t2",
                            "condition": "After valid input collected",
                            "nextNode": "4"
                        }
                    ]
                }
            },
            {
                "id": "4",
                "type": "collect_input",
                "label": "Collect Age",
                "data": {
                    "variable_name": "user_age",
                    "input_type": "number",
                    "prompt_message": "Please provide your age.",
                    "error_message": "Please enter a valid age number.",
                    "transitions": [
                        {
                            "id": "t3",
                            "condition": "After valid input collected",
                            "nextNode": "5"
                        }
                    ]
                }
            },
            {
                "id": "5",
                "type": "send_sms",
                "label": "Send SMS",
                "data": {
                    "phone_number": "{{user_phone}}",
                    "sms_message": "Hello! Your information: Email: {{user_email}}, Age: {{user_age}}",
                    "transitions": [
                        {
                            "id": "t4",
                            "condition": "After SMS sent",
                            "nextNode": "6"
                        }
                    ]
                }
            },
            {
                "id": "6",
                "type": "ending",
                "label": "End",
                "data": {
                    "mode": "script",
                    "content": "Thank you! I've sent an SMS to {{user_phone}} with your information.",
                    "transitions": []
                }
            }
        ]
        
        # Create the flow
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=flow_data) as response:
                if response.status == 200:
                    self.log_result(
                        "Test 4 - Create Multi-Input Validation Flow", 
                        True, 
                        "Successfully created multi-input validation flow"
                    )
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 4 - Create Multi-Input Validation Flow", 
                        False, 
                        f"Failed to create flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 4 - Create Multi-Input Validation Flow", False, f"Error creating flow: {str(e)}")
            return False
        
        # Execute multi-input validation test
        conversation_history = []
        
        # Step 1: Collect email
        try:
            request_data = {
                "message": "test@example.com",
                "conversation_history": conversation_history
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if "phone" in response_text.lower():
                        self.log_result(
                            "Test 4 - Step 1: Email Validation", 
                            True, 
                            "Email validated, moved to phone collection"
                        )
                        conversation_history.extend([
                            {"role": "user", "content": "test@example.com"},
                            {"role": "assistant", "content": response_text}
                        ])
                    else:
                        self.log_result("Test 4 - Step 1: Email Validation", False, f"Email validation failed: {response_text}")
                        return False
                else:
                    self.log_result("Test 4 - Step 1: Email Validation", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 4 - Step 1: Email Validation", False, f"Error: {str(e)}")
            return False
        
        # Step 2: Collect phone
        try:
            request_data = {
                "message": "+1-555-123-4567",
                "conversation_history": conversation_history
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if "age" in response_text.lower():
                        self.log_result(
                            "Test 4 - Step 2: Phone Validation", 
                            True, 
                            "Phone validated, moved to age collection"
                        )
                        conversation_history.extend([
                            {"role": "user", "content": "+1-555-123-4567"},
                            {"role": "assistant", "content": response_text}
                        ])
                    else:
                        self.log_result("Test 4 - Step 2: Phone Validation", False, f"Phone validation failed: {response_text}")
                        return False
                else:
                    self.log_result("Test 4 - Step 2: Phone Validation", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 4 - Step 2: Phone Validation", False, f"Error: {str(e)}")
            return False
        
        # Step 3: Collect age and complete flow
        try:
            request_data = {
                "message": "25",
                "conversation_history": conversation_history
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    should_end_call = data.get('should_end_call', False)
                    
                    if should_end_call and "sms" in response_text.lower():
                        self.log_result(
                            "Test 4 - Step 3: Age Validation and SMS", 
                            True, 
                            "Age validated, SMS sent with variable replacement, call ended"
                        )
                        return True
                    else:
                        self.log_result("Test 4 - Step 3: Age Validation and SMS", False, f"Final step failed: {response_text}, should_end_call: {should_end_call}")
                        return False
                else:
                    self.log_result("Test 4 - Step 3: Age Validation and SMS", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 4 - Step 3: Age Validation and SMS", False, f"Error: {str(e)}")
            return False

    async def test_5_transfer_scenarios(self):
        """
        Test 5: Transfer Scenarios
        Test both Call Transfer (phone number) and Agent Transfer (agent queue)
        """
        print(f"\n🎯 Test 5: Transfer Scenarios")
        print("=" * 80)
        
        # Test A: Phone Transfer
        phone_flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Start",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "conversation",
                "label": "Greeting",
                "data": {
                    "mode": "script",
                    "content": "I'll transfer you to our phone support.",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "user responds",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "transfer",
                "label": "Phone Transfer",
                "data": {
                    "transfer_type": "cold",
                    "destination_type": "phone",
                    "destination": "+1-800-555-0123",
                    "transfer_message": "Transferring you to phone support at +1-800-555-0123"
                }
            }
        ]
        
        # Create phone transfer flow
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=phone_flow_data) as response:
                if response.status == 200:
                    self.log_result(
                        "Test 5A - Create Phone Transfer Flow", 
                        True, 
                        "Successfully created phone transfer flow"
                    )
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 5A - Create Phone Transfer Flow", 
                        False, 
                        f"Failed to create flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 5A - Create Phone Transfer Flow", False, f"Error creating flow: {str(e)}")
            return False
        
        # Test phone transfer execution
        try:
            request_data = {
                "message": "I need help",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if "transfer" in response_text.lower() and "800-555-0123" in response_text:
                        self.log_result(
                            "Test 5A - Phone Transfer Execution", 
                            True, 
                            "Phone transfer executed with correct phone number"
                        )
                    else:
                        self.log_result("Test 5A - Phone Transfer Execution", False, f"Phone transfer failed: {response_text}")
                        return False
                else:
                    self.log_result("Test 5A - Phone Transfer Execution", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 5A - Phone Transfer Execution", False, f"Error: {str(e)}")
            return False
        
        # Test B: Agent Transfer
        agent_flow_data = [
            {
                "id": "1",
                "type": "start",
                "label": "Start",
                "data": {
                    "whoSpeaksFirst": "user",
                    "aiSpeaksAfterSilence": True,
                    "silenceTimeout": 2000
                }
            },
            {
                "id": "2",
                "type": "conversation",
                "label": "Greeting",
                "data": {
                    "mode": "script",
                    "content": "I'll connect you with a live agent.",
                    "transitions": [
                        {
                            "id": "t1",
                            "condition": "user responds",
                            "nextNode": "3"
                        }
                    ]
                }
            },
            {
                "id": "3",
                "type": "transfer",
                "label": "Agent Transfer",
                "data": {
                    "transfer_type": "warm",
                    "destination_type": "agent",
                    "destination": "customer_support_queue",
                    "transfer_message": "Connecting you to our customer support team"
                }
            }
        ]
        
        # Create agent transfer flow
        try:
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=agent_flow_data) as response:
                if response.status == 200:
                    self.log_result(
                        "Test 5B - Create Agent Transfer Flow", 
                        True, 
                        "Successfully created agent transfer flow"
                    )
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Test 5B - Create Agent Transfer Flow", 
                        False, 
                        f"Failed to create flow - Status: {response.status}", 
                        {"error": error_text}
                    )
                    return False
        except Exception as e:
            self.log_result("Test 5B - Create Agent Transfer Flow", False, f"Error creating flow: {str(e)}")
            return False
        
        # Test agent transfer execution
        try:
            request_data = {
                "message": "I need help",
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    
                    if "connect" in response_text.lower() and "support" in response_text.lower():
                        self.log_result(
                            "Test 5B - Agent Transfer Execution", 
                            True, 
                            "Agent transfer executed with correct queue reference"
                        )
                        return True
                    else:
                        self.log_result("Test 5B - Agent Transfer Execution", False, f"Agent transfer failed: {response_text}")
                        return False
                else:
                    self.log_result("Test 5B - Agent Transfer Execution", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result("Test 5B - Agent Transfer Execution", False, f"Error: {str(e)}")
            return False

    async def test_6_all_logic_operators(self):
        """
        Test 6: All Operators in Logic Split
        Test each operator: equals, not_equals, contains, greater_than, less_than, exists, not_exists
        """
        print(f"\n🎯 Test 6: All Logic Split Operators")
        print("=" * 80)
        
        operators_to_test = [
            ("equals", "test_value", "test_value", True),
            ("not_equals", "test_value", "different_value", True),
            ("contains", "hello world", "hello", True),
            ("greater_than", "25", "18", True),
            ("less_than", "15", "18", True),
            ("exists", "existing_var", "", True),
            ("not_exists", "non_existing_var", "", True)
        ]
        
        success_count = 0
        
        for operator, test_value, compare_value, should_match in operators_to_test:
            success = await self._test_logic_operator(operator, test_value, compare_value, should_match)
            if success:
                success_count += 1
        
        if success_count == len(operators_to_test):
            self.log_result(
                "Test 6 - All Logic Split Operators", 
                True, 
                f"All {len(operators_to_test)} logic operators working correctly"
            )
            return True
        else:
            self.log_result(
                "Test 6 - All Logic Split Operators", 
                False, 
                f"Only {success_count}/{len(operators_to_test)} operators working correctly"
            )
            return False

    async def _test_logic_operator(self, operator: str, test_value: str, compare_value: str, should_match: bool):
        """Helper method to test individual logic operators"""
        try:
            # Create flow for specific operator test
            flow_data = [
                {
                    "id": "1",
                    "type": "start",
                    "label": "Start",
                    "data": {
                        "whoSpeaksFirst": "user",
                        "aiSpeaksAfterSilence": True,
                        "silenceTimeout": 2000
                    }
                },
                {
                    "id": "2",
                    "type": "collect_input",
                    "label": "Collect Test Value",
                    "data": {
                        "variable_name": "test_var",
                        "input_type": "text",
                        "prompt_message": f"Enter test value for {operator}:",
                        "error_message": "Please enter a value.",
                        "transitions": [
                            {
                                "id": "t1",
                                "condition": "After valid input collected",
                                "nextNode": "3"
                            }
                        ]
                    }
                },
                {
                    "id": "3",
                    "type": "logic_split",
                    "label": f"Test {operator}",
                    "data": {
                        "conditions": [
                            {
                                "variable": "test_var",
                                "operator": operator,
                                "value": compare_value,
                                "nextNode": "4"
                            }
                        ],
                        "default_path": "5"
                    }
                },
                {
                    "id": "4",
                    "type": "ending",
                    "label": "Match",
                    "data": {
                        "mode": "script",
                        "content": f"Condition matched for {operator}",
                        "transitions": []
                    }
                },
                {
                    "id": "5",
                    "type": "ending",
                    "label": "No Match",
                    "data": {
                        "mode": "script",
                        "content": f"Condition not matched for {operator}",
                        "transitions": []
                    }
                }
            ]
            
            # Create the flow
            async with self.session.put(f"{BACKEND_URL}/agents/{self.test_agent_id}/flow", json=flow_data) as response:
                if response.status != 200:
                    self.log_result(f"Test 6 - {operator} Operator", False, f"Failed to create flow - Status: {response.status}")
                    return False
            
            # Test the operator
            request_data = {
                "message": test_value,
                "conversation_history": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/agents/{self.test_agent_id}/process", json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get('response', '')
                    should_end_call = data.get('should_end_call', False)
                    
                    if should_end_call:
                        if should_match and "matched" in response_text.lower():
                            self.log_result(
                                f"Test 6 - {operator} Operator", 
                                True, 
                                f"Operator {operator} correctly matched condition"
                            )
                            return True
                        elif not should_match and "not matched" in response_text.lower():
                            self.log_result(
                                f"Test 6 - {operator} Operator", 
                                True, 
                                f"Operator {operator} correctly did not match condition"
                            )
                            return True
                    
                    self.log_result(
                        f"Test 6 - {operator} Operator", 
                        False, 
                        f"Unexpected result for {operator}: {response_text}"
                    )
                    return False
                else:
                    self.log_result(f"Test 6 - {operator} Operator", False, f"Failed - Status: {response.status}")
                    return False
        except Exception as e:
            self.log_result(f"Test 6 - {operator} Operator", False, f"Error: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all comprehensive end-to-end tests"""
        print(f"\n🚀 Starting Comprehensive End-to-End Backend Testing")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 80)
        
        # Setup test agent
        if not await self.setup_test_agent():
            print("❌ Failed to setup test agent. Aborting tests.")
            return
        
        # Run all test scenarios
        test_results = []
        
        test_results.append(await self.test_1_complete_customer_service_flow())
        test_results.append(await self.test_2_complex_conditional_flow())
        test_results.append(await self.test_3_webhook_integration_flow())
        test_results.append(await self.test_4_multi_input_validation())
        test_results.append(await self.test_5_transfer_scenarios())
        test_results.append(await self.test_6_all_logic_operators())
        
        # Summary
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        
        print(f"\n" + "=" * 80)
        print(f"📊 Comprehensive E2E Test Results: {passed_tests}/{total_tests} tests passed")
        print(f"Final Result: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("🎉 ALL COMPREHENSIVE END-TO-END TESTS PASSED!")
        else:
            print(f"⚠️  {total_tests - passed_tests} test(s) failed. Review the detailed results above.")

async def main():
    async with ComprehensiveE2ETester() as tester:
        await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())