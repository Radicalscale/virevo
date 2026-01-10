#!/usr/bin/env python3
"""
ADVANCED AGENT DUPLICATION TESTING
Testing agent duplication with complex call flows and configurations.
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
import uuid

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://missed-variable.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class AdvancedDuplicationTester:
    def __init__(self):
        self.user_token = None
        self.user_id = None
        
    async def create_test_user(self, email: str, password: str) -> tuple:
        """Create a test user and return (user_id, auth_token)"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            signup_data = {
                "email": email,
                "password": password,
                "remember_me": True
            }
            
            try:
                response = await client.post(f"{API_BASE}/auth/signup", json=signup_data)
                if response.status_code == 200:
                    set_cookie_header = response.headers.get('set-cookie', '')
                    token = None
                    if 'access_token=' in set_cookie_header:
                        token_part = set_cookie_header.split('access_token=')[1].split(';')[0]
                        token = token_part
                    user_data = response.json()
                    user_id = user_data['user']['id']
                    return user_id, token
                elif response.status_code == 400 and "already registered" in response.text:
                    login_data = {
                        "email": email,
                        "password": password,
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
            headers = {}
            cookies = {"access_token": self.user_token} if self.user_token else {}
            
            try:
                if method.upper() == "GET":
                    response = await client.get(f"{API_BASE}{endpoint}", cookies=cookies, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(f"{API_BASE}{endpoint}", cookies=cookies, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(f"{API_BASE}{endpoint}", cookies=cookies, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(f"{API_BASE}{endpoint}", cookies=cookies, headers=headers, json=data)
                else:
                    response = await client.request(method, f"{API_BASE}{endpoint}", cookies=cookies, headers=headers, json=data)
                
                return response
            except Exception as e:
                print(f"Request error: {str(e)}")
                return None
    
    async def test_complex_agent_duplication(self):
        """Test duplication of agent with complex call flow"""
        print(f"\n{'='*80}")
        print("ADVANCED AGENT DUPLICATION TEST - Complex Call Flow")
        print(f"{'='*80}")
        
        # Setup user
        user_email = f"advanced_dup_test_{uuid.uuid4().hex[:8]}@example.com"
        self.user_id, self.user_token = await self.create_test_user(user_email, "SecurePass123!")
        print(f"✅ Created Test User: {self.user_id[:8]}...")
        
        # Create agent with complex call flow
        agent_data = {
            "name": "Complex Sales Agent",
            "description": "Advanced sales agent with multi-step call flow",
            "voice": "Emily",
            "language": "en",
            "llm_provider": "openai",
            "llm_model": "gpt-4-turbo",
            "stt_provider": "deepgram",
            "tts_provider": "elevenlabs",
            "system_prompt": "You are an expert sales representative. Be professional and persuasive.",
            "first_message": "Hello! I'm calling about our premium services. Do you have a moment to chat?",
            "interruption_threshold": 200,
            "response_delay": 1000,
            "agent_type": "call_flow"
        }
        
        # Create the agent first
        response = await self.make_authenticated_request("POST", "/agents", agent_data)
        if not response or response.status_code != 200:
            print(f"❌ Failed to create agent: {response.status_code if response else 'No response'}")
            return
        
        agent = response.json()
        agent_id = agent['id']
        print(f"✅ Created complex agent: {agent['name']} (ID: {agent_id[:8]}...)")
        
        # Add complex call flow
        call_flow = [
            {
                "id": "start",
                "type": "conversation",
                "label": "Initial Greeting",
                "data": {
                    "content": "Hello! I'm calling about our premium business solutions.",
                    "extract_variables": [
                        {
                            "name": "customer_name",
                            "description": "Customer's name",
                            "mandatory": True,
                            "prompt_message": "May I have your name please?"
                        },
                        {
                            "name": "company_name", 
                            "description": "Customer's company name",
                            "mandatory": False,
                            "prompt_message": "What company do you work for?"
                        }
                    ],
                    "transitions": [
                        {
                            "id": "to_qualification",
                            "condition": "interested",
                            "next_node": "qualification",
                            "check_variables": ["customer_name"]
                        },
                        {
                            "id": "to_objection",
                            "condition": "not_interested",
                            "next_node": "objection_handling"
                        }
                    ]
                }
            },
            {
                "id": "qualification",
                "type": "conversation", 
                "label": "Qualification Questions",
                "data": {
                    "content": "Great! Let me ask a few questions to see how we can best help you.",
                    "extract_variables": [
                        {
                            "name": "budget_range",
                            "description": "Customer's budget range",
                            "mandatory": True,
                            "prompt_message": "What's your budget range for this type of solution?"
                        },
                        {
                            "name": "timeline",
                            "description": "Implementation timeline",
                            "mandatory": True,
                            "prompt_message": "When are you looking to implement this?"
                        }
                    ],
                    "transitions": [
                        {
                            "id": "to_proposal",
                            "condition": "qualified",
                            "next_node": "proposal",
                            "check_variables": ["budget_range", "timeline"]
                        }
                    ]
                }
            },
            {
                "id": "objection_handling",
                "type": "conversation",
                "label": "Handle Objections",
                "data": {
                    "content": "I understand your concerns. Let me share how we've helped similar businesses.",
                    "transitions": [
                        {
                            "id": "to_qualification_retry",
                            "condition": "overcome_objection",
                            "next_node": "qualification"
                        },
                        {
                            "id": "to_followup",
                            "condition": "schedule_followup",
                            "next_node": "schedule_followup"
                        }
                    ]
                }
            },
            {
                "id": "proposal",
                "type": "function",
                "label": "Generate Proposal",
                "data": {
                    "webhook_url": "https://api.example.com/generate-proposal",
                    "method": "POST",
                    "timeout": 10,
                    "webhook_body": {
                        "customer_name": "{{customer_name}}",
                        "company_name": "{{company_name}}",
                        "budget_range": "{{budget_range}}",
                        "timeline": "{{timeline}}"
                    },
                    "response_variable": "proposal_data",
                    "transitions": [
                        {
                            "id": "to_closing",
                            "condition": "proposal_ready",
                            "next_node": "closing"
                        }
                    ]
                }
            },
            {
                "id": "closing",
                "type": "conversation",
                "label": "Close the Deal",
                "data": {
                    "content": "Based on your needs, here's what I recommend: {{proposal_data}}",
                    "transitions": [
                        {
                            "id": "to_success",
                            "condition": "deal_closed",
                            "next_node": "success"
                        }
                    ]
                }
            },
            {
                "id": "schedule_followup",
                "type": "function",
                "label": "Schedule Follow-up",
                "data": {
                    "webhook_url": "https://api.example.com/schedule-meeting",
                    "method": "POST",
                    "timeout": 5,
                    "webhook_body": {
                        "customer_name": "{{customer_name}}",
                        "preferred_time": "{{preferred_time}}"
                    },
                    "response_variable": "meeting_scheduled",
                    "transitions": [
                        {
                            "id": "to_end",
                            "condition": "scheduled",
                            "next_node": "end"
                        }
                    ]
                }
            },
            {
                "id": "success",
                "type": "ending",
                "label": "Deal Closed Successfully",
                "data": {
                    "content": "Excellent! Welcome aboard! You'll receive your contract within 24 hours."
                }
            },
            {
                "id": "end",
                "type": "ending",
                "label": "Call End",
                "data": {
                    "content": "Thank you for your time. Have a great day!"
                }
            }
        ]
        
        # Update agent with call flow
        response = await self.make_authenticated_request("PUT", f"/agents/{agent_id}/flow", call_flow)
        if response and response.status_code == 200:
            print(f"✅ Added complex call flow with {len(call_flow)} nodes")
        else:
            print(f"❌ Failed to add call flow: {response.status_code if response else 'No response'}")
            return
        
        # Now duplicate the agent
        print(f"\n🔄 Duplicating complex agent...")
        response = await self.make_authenticated_request("POST", f"/agents/{agent_id}/duplicate")
        
        if not response or response.status_code != 200:
            print(f"❌ Duplication failed: {response.status_code if response else 'No response'}")
            if response:
                print(f"Error details: {response.text}")
            return
        
        duplicated_agent = response.json()
        print(f"✅ Successfully duplicated agent!")
        print(f"   Original: {agent['name']} (ID: {agent_id[:8]}...)")
        print(f"   Duplicate: {duplicated_agent['name']} (ID: {duplicated_agent['id'][:8]}...)")
        
        # Verify call flow was copied
        response = await self.make_authenticated_request("GET", f"/agents/{duplicated_agent['id']}/flow")
        if response and response.status_code == 200:
            flow_data = response.json()
            duplicated_flow = flow_data.get('flow', [])
            
            if len(duplicated_flow) == len(call_flow):
                print(f"✅ Call flow correctly duplicated ({len(duplicated_flow)} nodes)")
                
                # Verify complex node structures
                complex_nodes_match = True
                for i, node in enumerate(duplicated_flow):
                    original_node = call_flow[i]
                    if node.get('id') != original_node.get('id'):
                        complex_nodes_match = False
                        break
                    if node.get('type') != original_node.get('type'):
                        complex_nodes_match = False
                        break
                    # Check data structure preservation
                    if 'extract_variables' in original_node.get('data', {}):
                        if 'extract_variables' not in node.get('data', {}):
                            complex_nodes_match = False
                            break
                
                if complex_nodes_match:
                    print(f"✅ Complex node structures preserved correctly")
                else:
                    print(f"❌ Complex node structures not preserved correctly")
            else:
                print(f"❌ Call flow not duplicated correctly. Original: {len(call_flow)}, Duplicate: {len(duplicated_flow)}")
        else:
            print(f"❌ Failed to retrieve duplicated agent's call flow")
        
        # Cleanup
        print(f"\n🧹 Cleaning up test data...")
        for test_agent_id in [agent_id, duplicated_agent['id']]:
            response = await self.make_authenticated_request("DELETE", f"/agents/{test_agent_id}")
            if response and response.status_code == 200:
                print(f"✅ Deleted agent: {test_agent_id[:8]}...")
            else:
                print(f"⚠️ Failed to delete agent: {test_agent_id[:8]}...")

async def main():
    """Main test execution"""
    tester = AdvancedDuplicationTester()
    await tester.test_complex_agent_duplication()
    print(f"\n🎯 Advanced agent duplication test completed!")

if __name__ == "__main__":
    asyncio.run(main())