#!/usr/bin/env python3
"""
Agent Transition Tester Backend Testing Script

Tests the Agent Transition Tester functionality as specified in the review request:
1. Find an agent with a call_flow that has at least 2 nodes with transitions defined
2. Start a test session with a specific start_node_id
3. Send a message that should trigger a transition
4. Verify that:
   - The response is from the NEXT node, not the start node
   - The current_node_id in the response is the transitioned-to node
   - The transition_test result shows correct "From Node" and "To Node" info

Backend URL: Use REACT_APP_BACKEND_URL from /app/frontend/.env
API Endpoints:
- POST /api/agents/{agent_id}/test/start (body: {"start_node_id": "..."})
- POST /api/agents/{agent_id}/test/message (body: {"message": "...", "session_id": "...", "start_node_id": "...", "expected_next_node": "..."})
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional

# Backend URL from frontend .env
BACKEND_URL = "https://missed-variable.preview.emergentagent.com"

class AgentTransitionTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.auth_token = None
        
    def log_result(self, test_name: str, status: str, details: str = "", expected: str = None, actual: str = None):
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
        if expected and actual:
            print(f"   Expected: {expected}, Got: {actual}")
        print()

    async def get_auth_token(self):
        """Get authentication token for testing"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try test credentials first
                login_data = {
                    "email": "test@preview.emergentagent.com",
                    "password": "TestPassword123!",
                    "remember_me": False
                }
                
                response = await client.post(
                    f"{self.backend_url}/api/auth/login",
                    json=login_data
                )
                
                if response.status_code == 200:
                    cookies = response.cookies
                    if 'access_token' in cookies:
                        self.auth_token = cookies['access_token']
                        self.log_result("Authentication", "PASS", f"Logged in with test@preview.emergentagent.com")
                        return True
                
                # Try alternative credentials
                login_data = {
                    "email": "kendrickbowman9@gmail.com", 
                    "password": "B!LL10n$$",
                    "remember_me": False
                }
                
                response = await client.post(
                    f"{self.backend_url}/api/auth/login",
                    json=login_data
                )
                
                if response.status_code == 200:
                    cookies = response.cookies
                    if 'access_token' in cookies:
                        self.auth_token = cookies['access_token']
                        self.log_result("Authentication", "PASS", f"Logged in with kendrickbowman9@gmail.com")
                        return True
                
                self.log_result("Authentication", "FAIL", f"Login failed with status {response.status_code}")
                return False
                        
        except Exception as e:
            self.log_result("Authentication", "FAIL", f"Exception: {str(e)}")
            return False

    async def list_agents(self) -> List[Dict]:
        """List available agents"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Cookie": f"access_token={self.auth_token}"}
                response = await client.get(f"{self.backend_url}/api/agents", headers=headers)
                
                if response.status_code == 200:
                    agents = response.json()
                    self.log_result("List Agents", "PASS", f"Found {len(agents)} agents")
                    return agents
                else:
                    self.log_result("List Agents", "FAIL", f"Status {response.status_code}: {response.text[:100]}")
                    return []
                    
        except Exception as e:
            self.log_result("List Agents", "FAIL", f"Exception: {str(e)}")
            return []

    def find_suitable_agent(self, agents: List[Dict]) -> Optional[Dict]:
        """Find an agent with call_flow that has at least 2 nodes with transitions"""
        for agent in agents:
            call_flow = agent.get('call_flow', [])
            
            if len(call_flow) < 2:
                continue
                
            # Check if nodes have transitions
            nodes_with_transitions = []
            for node in call_flow:
                node_data = node.get('data', {})
                transitions = node_data.get('transitions', [])
                if transitions and len(transitions) > 0:
                    nodes_with_transitions.append(node)
            
            if len(nodes_with_transitions) >= 1:
                # Found a suitable agent
                agent_info = {
                    'agent': agent,
                    'total_nodes': len(call_flow),
                    'nodes_with_transitions': len(nodes_with_transitions),
                    'suitable_nodes': nodes_with_transitions
                }
                
                self.log_result(
                    "Find Suitable Agent", 
                    "PASS", 
                    f"Agent '{agent.get('name')}' has {len(call_flow)} nodes, {len(nodes_with_transitions)} with transitions"
                )
                return agent_info
        
        self.log_result("Find Suitable Agent", "FAIL", "No agents found with suitable call flow structure")
        return None

    async def test_transition_functionality(self, agent_info: Dict):
        """Test the core transition functionality"""
        agent = agent_info['agent']
        agent_id = agent['id']
        agent_name = agent.get('name', 'Unknown')
        suitable_nodes = agent_info['suitable_nodes']
        
        if not suitable_nodes:
            self.log_result("Transition Test Setup", "FAIL", "No nodes with transitions found")
            return
        
        # Pick the first node with transitions
        start_node = suitable_nodes[0]
        start_node_id = start_node['id']
        start_node_label = start_node.get('label', start_node.get('data', {}).get('label', 'Unnamed'))
        transitions = start_node.get('data', {}).get('transitions', [])
        
        if not transitions:
            self.log_result("Transition Test Setup", "FAIL", f"Node {start_node_label} has no transitions")
            return
        
        # Pick the first transition
        first_transition = transitions[0]
        expected_next_node = first_transition.get('nextNode')
        transition_condition = first_transition.get('condition', 'No condition')
        
        if not expected_next_node:
            self.log_result("Transition Test Setup", "FAIL", f"Transition has no nextNode defined")
            return
        
        # Find the target node label
        expected_node_label = "Unknown"
        for node in agent['call_flow']:
            if node['id'] == expected_next_node:
                expected_node_label = node.get('label', node.get('data', {}).get('label', 'Unnamed'))
                break
        
        print(f"🎯 Testing transition from '{start_node_label}' to '{expected_node_label}'")
        print(f"   Start Node ID: {start_node_id}")
        print(f"   Expected Next Node ID: {expected_next_node}")
        print(f"   Transition Condition: {transition_condition}")
        print()
        
        # Step 1: Start test session with specific start_node_id
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Cookie": f"access_token={self.auth_token}"}
                
                start_request = {"start_node_id": start_node_id}
                response = await client.post(
                    f"{self.backend_url}/api/agents/{agent_id}/test/start",
                    json=start_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    session_data = response.json()
                    session_id = session_data.get('session_id')
                    returned_start_node = session_data.get('start_node_id')
                    current_node_id = session_data.get('current_node_id')
                    
                    if returned_start_node == start_node_id:
                        self.log_result(
                            "Start Session with Node", 
                            "PASS", 
                            f"Session started with start_node_id: {start_node_id}",
                            start_node_id,
                            returned_start_node
                        )
                    else:
                        self.log_result(
                            "Start Session with Node", 
                            "FAIL", 
                            f"Start node mismatch",
                            start_node_id,
                            returned_start_node
                        )
                        return
                else:
                    self.log_result(
                        "Start Session with Node", 
                        "FAIL", 
                        f"Status {response.status_code}: {response.text[:200]}"
                    )
                    return
                    
        except Exception as e:
            self.log_result("Start Session with Node", "FAIL", f"Exception: {str(e)}")
            return
        
        # Step 2: Send a message that should trigger the transition
        # Create a test message that should match the transition condition
        test_messages = [
            "yes",
            "I agree", 
            "sure",
            "okay",
            "tell me more",
            "I'm interested",
            "go ahead"
        ]
        
        # Try to create a message that matches the condition
        test_message = "yes"  # Default
        condition_lower = transition_condition.lower()
        if "yes" in condition_lower or "agree" in condition_lower:
            test_message = "yes"
        elif "interested" in condition_lower:
            test_message = "I'm interested"
        elif "more" in condition_lower:
            test_message = "tell me more"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Cookie": f"access_token={self.auth_token}"}
                
                message_request = {
                    "message": test_message,
                    "session_id": session_id,
                    "start_node_id": start_node_id,
                    "expected_next_node": expected_next_node
                }
                
                response = await client.post(
                    f"{self.backend_url}/api/agents/{agent_id}/test/message",
                    json=message_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    message_response = response.json()
                    
                    # Extract key information
                    actual_current_node = message_response.get('current_node_id')
                    actual_node_label = message_response.get('current_node_label', 'Unknown')
                    agent_response = message_response.get('agent_response', '')
                    transition_test = message_response.get('transition_test', {})
                    
                    print(f"📨 Sent message: '{test_message}'")
                    print(f"🤖 Agent response: '{agent_response[:100]}...'")
                    print(f"📍 Current node: {actual_current_node} ({actual_node_label})")
                    print()
                    
                    # Test 1: Verify response comes from NEXT node, not start node
                    if actual_current_node != start_node_id:
                        self.log_result(
                            "Response from Next Node (not start)", 
                            "PASS", 
                            f"Response came from {actual_node_label}, not start node",
                            f"Not {start_node_id}",
                            actual_current_node
                        )
                    else:
                        self.log_result(
                            "Response from Next Node (not start)", 
                            "FAIL", 
                            f"Response still from start node {start_node_label}",
                            f"Not {start_node_id}",
                            actual_current_node
                        )
                    
                    # Test 2: Verify current_node_id is the transitioned-to node
                    if actual_current_node == expected_next_node:
                        self.log_result(
                            "Current Node ID Correct", 
                            "PASS", 
                            f"Transitioned to expected node {expected_node_label}",
                            expected_next_node,
                            actual_current_node
                        )
                    else:
                        self.log_result(
                            "Current Node ID Correct", 
                            "FAIL", 
                            f"Expected {expected_node_label} but got {actual_node_label}",
                            expected_next_node,
                            actual_current_node
                        )
                    
                    # Test 3: Verify transition_test result shows correct From/To info
                    if transition_test:
                        test_start_node = transition_test.get('start_node')
                        test_actual_node = transition_test.get('actual_node')
                        test_expected_node = transition_test.get('expected_node')
                        test_success = transition_test.get('success', False)
                        
                        if test_start_node == start_node_id and test_actual_node == expected_next_node:
                            self.log_result(
                                "Transition Test Result Correct", 
                                "PASS", 
                                f"Transition test shows FROM {transition_test.get('start_label')} TO {transition_test.get('actual_label')}",
                                f"FROM {start_node_id} TO {expected_next_node}",
                                f"FROM {test_start_node} TO {test_actual_node}"
                            )
                        else:
                            self.log_result(
                                "Transition Test Result Correct", 
                                "FAIL", 
                                f"Transition test data incorrect: {transition_test}",
                                f"FROM {start_node_id} TO {expected_next_node}",
                                f"FROM {test_start_node} TO {test_actual_node}"
                            )
                        
                        # Test 4: Verify transition success flag
                        if test_success:
                            self.log_result(
                                "Transition Success Flag", 
                                "PASS", 
                                f"Transition marked as successful",
                                "True",
                                str(test_success)
                            )
                        else:
                            self.log_result(
                                "Transition Success Flag", 
                                "FAIL", 
                                f"Transition marked as failed: {transition_test.get('message', 'No message')}",
                                "True",
                                str(test_success)
                            )
                    else:
                        self.log_result(
                            "Transition Test Result Present", 
                            "FAIL", 
                            "No transition_test data in response"
                        )
                    
                    # Additional verification: Check conversation history
                    conversation = message_response.get('conversation', [])
                    if conversation:
                        last_turn = conversation[-1]
                        turn_node_id = last_turn.get('node_id')
                        turn_node_label = last_turn.get('node_label', 'Unknown')
                        
                        if turn_node_id == expected_next_node:
                            self.log_result(
                                "Conversation History Node Correct", 
                                "PASS", 
                                f"Last conversation turn shows correct node: {turn_node_label}",
                                expected_next_node,
                                turn_node_id
                            )
                        else:
                            self.log_result(
                                "Conversation History Node Correct", 
                                "FAIL", 
                                f"Conversation history shows wrong node: {turn_node_label}",
                                expected_next_node,
                                turn_node_id
                            )
                    
                else:
                    self.log_result(
                        "Send Test Message", 
                        "FAIL", 
                        f"Status {response.status_code}: {response.text[:200]}"
                    )
                    
        except Exception as e:
            self.log_result("Send Test Message", "FAIL", f"Exception: {str(e)}")

    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Agent Transition Tester Backend Testing")
        print(f"Backend URL: {self.backend_url}")
        print("=" * 80)
        print()
        
        # Step 1: Authenticate
        if not await self.get_auth_token():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Step 2: List agents
        agents = await self.list_agents()
        if not agents:
            print("❌ No agents found - cannot proceed with tests")
            return False
        
        # Step 3: Find suitable agent
        agent_info = self.find_suitable_agent(agents)
        if not agent_info:
            print("❌ No suitable agents found - cannot proceed with tests")
            return False
        
        # Step 4: Test transition functionality
        await self.test_transition_functionality(agent_info)
        
        # Print summary
        print("=" * 80)
        print("📊 TEST SUMMARY")
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
        
        return self.passed_tests == self.total_tests

async def main():
    """Main test runner"""
    tester = AgentTransitionTester()
    success = await tester.run_all_tests()
    
    # Save detailed results to file
    with open("/app/agent_transition_test_results.json", "w") as f:
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
    
    print(f"📄 Detailed results saved to: /app/agent_transition_test_results.json")
    
    if success:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)