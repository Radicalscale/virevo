#!/usr/bin/env python3
"""
Focused test for Collect Input Node backend implementation
"""

import asyncio
import aiohttp
import json

BACKEND_URL = "https://missed-variable.preview.emergentagent.com/api"

async def test_collect_input_focused():
    """Test collect input node with proper flow navigation"""
    
    async with aiohttp.ClientSession() as session:
        # Get existing call flow agent
        async with session.get(f"{BACKEND_URL}/agents") as response:
            agents = await response.json()
            call_flow_agent_id = None
            for agent in agents:
                if agent.get("agent_type") == "call_flow":
                    call_flow_agent_id = agent["id"]
                    break
        
        if not call_flow_agent_id:
            print("❌ No call flow agent found")
            return
        
        print(f"✅ Using call flow agent: {call_flow_agent_id}")
        
        # Create a simple flow that goes directly to collect input
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
                "type": "collect_input",
                "label": "Collect Phone",
                "data": {
                    "variable_name": "user_phone",
                    "input_type": "phone",
                    "prompt_message": "Please provide your phone number.",
                    "error_message": "That doesn't look like a valid phone number. Please try again.",
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
                "type": "conversation",
                "label": "Phone Confirmation",
                "data": {
                    "mode": "script",
                    "content": "Thank you, I have your phone number: {{user_phone}}.",
                    "transitions": []
                }
            }
        ]
        
        # Update flow
        async with session.put(f"{BACKEND_URL}/agents/{call_flow_agent_id}/flow", json=flow_data) as response:
            if response.status == 200:
                print("✅ Flow updated successfully")
            else:
                print(f"❌ Failed to update flow: {response.status}")
                return
        
        # Test 1: Valid phone number
        print("\n📞 Testing valid phone number: +1-234-567-8900")
        request_data = {
            "message": "+1-234-567-8900",
            "conversation_history": []
        }
        
        async with session.post(f"{BACKEND_URL}/agents/{call_flow_agent_id}/process", json=request_data) as response:
            if response.status == 200:
                data = await response.json()
                response_text = data.get('response', '')
                print(f"Response: {response_text}")
                
                if "12345678900" in response_text or "phone number" in response_text.lower():
                    print("✅ Valid phone number processed correctly")
                else:
                    print("❌ Valid phone number not processed correctly")
            else:
                print(f"❌ API call failed: {response.status}")
        
        # Test 2: Invalid phone number
        print("\n📞 Testing invalid phone number: abc123")
        request_data = {
            "message": "abc123",
            "conversation_history": []
        }
        
        async with session.post(f"{BACKEND_URL}/agents/{call_flow_agent_id}/process", json=request_data) as response:
            if response.status == 200:
                data = await response.json()
                response_text = data.get('response', '')
                print(f"Response: {response_text}")
                
                if "valid" in response_text.lower() or "try again" in response_text.lower():
                    print("✅ Invalid phone number rejected correctly")
                else:
                    print("❌ Invalid phone number not handled correctly")
            else:
                print(f"❌ API call failed: {response.status}")
        
        # Test 3: Email validation
        print("\n📧 Testing email validation")
        
        # Create email flow
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
                "type": "collect_input",
                "label": "Collect Email",
                "data": {
                    "variable_name": "user_email",
                    "input_type": "email",
                    "prompt_message": "Please provide your email address.",
                    "error_message": "That doesn't look like a valid email address. Please try again.",
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
                "type": "conversation",
                "label": "Email Confirmation",
                "data": {
                    "mode": "script",
                    "content": "Thank you, I have your email: {{user_email}}.",
                    "transitions": []
                }
            }
        ]
        
        # Update flow for email
        async with session.put(f"{BACKEND_URL}/agents/{call_flow_agent_id}/flow", json=email_flow_data) as response:
            if response.status == 200:
                print("✅ Email flow updated successfully")
            else:
                print(f"❌ Failed to update email flow: {response.status}")
                return
        
        # Test valid email
        print("\n📧 Testing valid email: test@example.com")
        request_data = {
            "message": "test@example.com",
            "conversation_history": []
        }
        
        async with session.post(f"{BACKEND_URL}/agents/{call_flow_agent_id}/process", json=request_data) as response:
            if response.status == 200:
                data = await response.json()
                response_text = data.get('response', '')
                print(f"Response: {response_text}")
                
                if "test@example.com" in response_text:
                    print("✅ Valid email processed correctly")
                else:
                    print("❌ Valid email not processed correctly")
            else:
                print(f"❌ API call failed: {response.status}")
        
        # Test invalid email
        print("\n📧 Testing invalid email: notanemail")
        request_data = {
            "message": "notanemail",
            "conversation_history": []
        }
        
        async with session.post(f"{BACKEND_URL}/agents/{call_flow_agent_id}/process", json=request_data) as response:
            if response.status == 200:
                data = await response.json()
                response_text = data.get('response', '')
                print(f"Response: {response_text}")
                
                if "valid" in response_text.lower() or "try again" in response_text.lower():
                    print("✅ Invalid email rejected correctly")
                else:
                    print("❌ Invalid email not handled correctly")
            else:
                print(f"❌ API call failed: {response.status}")

if __name__ == "__main__":
    asyncio.run(test_collect_input_focused())