#!/usr/bin/env python3
"""
Comprehensive Agent Transition Tester Backend Testing Script

Extended testing of Agent Transition Tester functionality including:
1. Multiple transition scenarios
2. Edge cases (invalid nodes, failed transitions)
3. Multiple agents testing
4. Detailed validation of all response fields
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional

# Backend URL from frontend .env
BACKEND_URL = "https://tts-guardian.preview.emergentagent.com"

class ComprehensiveAgentTransitionTester:
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
                        self.log_result("Authentication", "PASS", f"Logged in successfully")
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

    def analyze_agent_structure(self, agent: Dict) -> Dict:
        """Analyze agent call flow structure"""
        call_flow = agent.get('call_flow', [])
        
        analysis = {
            'agent_id': agent['id'],
            'agent_name': agent.get('name', 'Unknown'),
            'total_nodes': len(call_flow),
            'nodes_with_transitions': [],
            'all_transitions': [],
            'transition_map': {}
        }
        
        for node in call_flow:
            node_id = node['id']
            node_data = node.get('data', {})
            node_label = node.get('label', node_data.get('label', 'Unnamed'))
            transitions = node_data.get('transitions', [])
            
            if transitions:
                analysis['nodes_with_transitions'].append({
                    'id': node_id,
                    'label': node_label,
                    'transitions': transitions
                })
                
                for transition in transitions:
                    next_node = transition.get('nextNode')
                    condition = transition.get('condition', 'No condition')
                    
                    transition_info = {
                        'from_node': node_id,
                        'from_label': node_label,
                        'to_node': next_node,
                        'condition': condition
                    }
                    
                    # Find target node label
                    for target_node in call_flow:
                        if target_node['id'] == next_node:
                            transition_info['to_label'] = target_node.get('label', target_node.get('data', {}).get('label', 'Unnamed'))
                            break
                    else:
                        transition_info['to_label'] = 'Unknown'
                    
                    analysis['all_transitions'].append(transition_info)
                    analysis['transition_map'][f"{node_id}->{next_node}"] = transition_info
        
        return analysis

    async def test_basic_transition(self, transition_info: Dict) -> bool:
        """Test a basic transition scenario"""
        agent_id = transition_info['agent_id']
        from_node = transition_info['from_node']
        to_node = transition_info['to_node']
        from_label = transition_info['from_label']
        to_label = transition_info['to_label']
        condition = transition_info['condition']
        
        test_name_prefix = f"Transition {from_label}->{to_label}"
        
        # Start session
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Cookie": f"access_token={self.auth_token}"}
                
                start_request = {"start_node_id": from_node}
                response = await client.post(
                    f"{self.backend_url}/api/agents/{agent_id}/test/start",
                    json=start_request,
                    headers=headers
                )
                
                if response.status_code != 200:
                    self.log_result(f"{test_name_prefix} - Start Session", "FAIL", f"Status {response.status_code}")
                    return False
                
                session_data = response.json()
                session_id = session_data.get('session_id')
                
        except Exception as e:
            self.log_result(f"{test_name_prefix} - Start Session", "FAIL", f"Exception: {str(e)}")
            return False
        
        # Send test message
        test_messages = ["yes", "I agree", "sure", "okay", "banana", "strawberry", "tell me more"]
        
        # Try to pick a message that matches the condition
        test_message = "yes"
        condition_lower = condition.lower()
        if "banana" in condition_lower:
            test_message = "banana"
        elif "strawberry" in condition_lower:
            test_message = "strawberry"
        elif "agree" in condition_lower:
            test_message = "I agree"
        elif "more" in condition_lower:
            test_message = "tell me more"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Cookie": f"access_token={self.auth_token}"}
                
                message_request = {
                    "message": test_message,
                    "session_id": session_id,
                    "start_node_id": from_node,
                    "expected_next_node": to_node
                }
                
                response = await client.post(
                    f"{self.backend_url}/api/agents/{agent_id}/test/message",
                    json=message_request,
                    headers=headers
                )
                
                if response.status_code != 200:
                    self.log_result(f"{test_name_prefix} - Send Message", "FAIL", f"Status {response.status_code}")
                    return False
                
                message_response = response.json()
                
                # Validate response
                actual_node = message_response.get('current_node_id')
                transition_test = message_response.get('transition_test', {})
                
                # Test: Correct transition
                if actual_node == to_node:
                    self.log_result(
                        f"{test_name_prefix} - Correct Transition",
                        "PASS",
                        f"Successfully transitioned from {from_label} to {to_label}",
                        to_node,
                        actual_node
                    )
                else:
                    self.log_result(
                        f"{test_name_prefix} - Correct Transition",
                        "FAIL",
                        f"Expected {to_label} but got {message_response.get('current_node_label', 'Unknown')}",
                        to_node,
                        actual_node
                    )
                    return False
                
                # Test: Transition test data
                if transition_test.get('success'):
                    self.log_result(
                        f"{test_name_prefix} - Transition Test Success",
                        "PASS",
                        f"Transition test marked as successful"
                    )
                else:
                    self.log_result(
                        f"{test_name_prefix} - Transition Test Success",
                        "FAIL",
                        f"Transition test failed: {transition_test.get('message', 'No message')}"
                    )
                
                # Test: Response structure completeness
                required_fields = ['session_id', 'agent_response', 'current_node_id', 'current_node_label', 
                                 'node_transitions', 'variables', 'latency', 'detailed_timing', 'metrics']
                missing_fields = [field for field in required_fields if field not in message_response]
                
                if not missing_fields:
                    self.log_result(
                        f"{test_name_prefix} - Response Structure",
                        "PASS",
                        f"All required fields present in response"
                    )
                else:
                    self.log_result(
                        f"{test_name_prefix} - Response Structure",
                        "FAIL",
                        f"Missing fields: {missing_fields}"
                    )
                
                return True
                
        except Exception as e:
            self.log_result(f"{test_name_prefix} - Send Message", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_invalid_scenarios(self, agent_id: str):
        """Test invalid scenarios and edge cases"""
        
        # Test 1: Invalid start node
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Cookie": f"access_token={self.auth_token}"}
                
                start_request = {"start_node_id": "invalid-node-id-999"}
                response = await client.post(
                    f"{self.backend_url}/api/agents/{agent_id}/test/start",
                    json=start_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    # Should still work but log warning about invalid node
                    session_data = response.json()
                    self.log_result(
                        "Invalid Start Node Handling",
                        "PASS",
                        f"System handled invalid start node gracefully"
                    )
                else:
                    self.log_result(
                        "Invalid Start Node Handling",
                        "WARN",
                        f"Invalid start node returned status {response.status_code}"
                    )
                    
        except Exception as e:
            self.log_result("Invalid Start Node Handling", "FAIL", f"Exception: {str(e)}")
        
        # Test 2: Missing session ID
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Cookie": f"access_token={self.auth_token}"}
                
                message_request = {
                    "message": "test message",
                    "session_id": "invalid-session-id-999"
                }
                
                response = await client.post(
                    f"{self.backend_url}/api/agents/{agent_id}/test/message",
                    json=message_request,
                    headers=headers
                )
                
                if response.status_code == 404:
                    self.log_result(
                        "Invalid Session ID Handling",
                        "PASS",
                        f"Correctly returned 404 for invalid session ID"
                    )
                else:
                    self.log_result(
                        "Invalid Session ID Handling",
                        "FAIL",
                        f"Expected 404 but got {response.status_code}"
                    )
                    
        except Exception as e:
            self.log_result("Invalid Session ID Handling", "FAIL", f"Exception: {str(e)}")

    async def run_comprehensive_tests(self):
        """Run comprehensive transition tests"""
        print("🚀 Starting Comprehensive Agent Transition Testing")
        print(f"Backend URL: {self.backend_url}")
        print("=" * 80)
        print()
        
        # Step 1: Authenticate
        if not await self.get_auth_token():
            return False
        
        # Step 2: List agents
        agents = await self.list_agents()
        if not agents:
            return False
        
        # Step 3: Analyze all agents
        suitable_agents = []
        for agent in agents:
            analysis = self.analyze_agent_structure(agent)
            if analysis['all_transitions']:
                suitable_agents.append(analysis)
                print(f"📊 Agent '{analysis['agent_name']}': {analysis['total_nodes']} nodes, {len(analysis['all_transitions'])} transitions")
        
        if not suitable_agents:
            self.log_result("Find Suitable Agents", "FAIL", "No agents with transitions found")
            return False
        
        self.log_result("Analyze Agent Structures", "PASS", f"Found {len(suitable_agents)} agents with transitions")
        
        # Step 4: Test transitions for each suitable agent
        for agent_analysis in suitable_agents:
            agent_name = agent_analysis['agent_name']
            agent_id = agent_analysis['agent_id']
            
            print(f"\n🎯 Testing Agent: {agent_name}")
            print("-" * 50)
            
            # Test up to 3 transitions per agent to avoid overwhelming
            transitions_to_test = agent_analysis['all_transitions'][:3]
            
            for i, transition in enumerate(transitions_to_test):
                print(f"\n  Transition {i+1}: {transition['from_label']} -> {transition['to_label']}")
                print(f"  Condition: {transition['condition']}")
                
                transition['agent_id'] = agent_id  # Add agent_id for testing
                success = await self.test_basic_transition(transition)
                
                if not success:
                    print(f"  ❌ Transition test failed")
                else:
                    print(f"  ✅ Transition test passed")
            
            # Test edge cases for this agent
            print(f"\n  Testing edge cases for {agent_name}...")
            await self.test_invalid_scenarios(agent_id)
        
        return True

    async def run_all_tests(self):
        """Run all tests"""
        success = await self.run_comprehensive_tests()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
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
    tester = ComprehensiveAgentTransitionTester()
    success = await tester.run_all_tests()
    
    # Save detailed results to file
    with open("/app/comprehensive_transition_test_results.json", "w") as f:
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
    
    print(f"📄 Detailed results saved to: /app/comprehensive_transition_test_results.json")
    
    if success:
        print("🎉 All comprehensive tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)