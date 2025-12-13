#!/usr/bin/env python3
"""
Comprehensive Jake Agent Tester
Tests transitions, objection handling, and script flow
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import json

# Add the backend directory to the path
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from calling_service import CallSession

# MongoDB setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Jake Agent ID - Get from database dynamically
JAKE_AGENT_ID = None  # Will be fetched from DB

class ConversationTester:
    """Test Jake agent with various conversation paths"""
    
    def __init__(self):
        self.test_results = []
        self.session = None
        self.conversation_history = []
        
    async def setup_session(self, test_name: str):
        """Initialize a new test session"""
        # Fetch the Jake agent configuration by name
        agent = await db.agents.find_one({"name": "Jake - Income Stacking Qualifier"})
        if not agent:
            raise Exception(f"Jake agent not found in database. Please run create_jake_agent.py first.")
        
        # Create a unique call ID for this test
        call_id = f"test_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize session with correct signature
        self.session = CallSession(
            call_id=call_id,
            agent_config=agent,
            agent_id=agent.get('id')
        )
        
        # Manually set test variables
        self.session.session_variables['customer_name'] = 'TestUser'
        self.session.session_variables['from_number'] = '+15551234567'
        self.session.session_variables['to_number'] = '+15559876543'
        
        # Parse the call flow
        self.session.flow_nodes = {node['id']: node for node in agent.get('call_flow', [])}
        self.session.flow_edges = agent.get('call_flow_edges', [])
        self.session.agent_type = agent.get('agent_type', 'call_flow')
        
        # Start at the first node
        start_node = next((node for node in agent.get('call_flow', []) if node['type'] == 'start'), None)
        if start_node:
            # Get the first edge from start node
            first_edge = next((edge for edge in self.session.flow_edges if edge['source'] == start_node['id']), None)
            if first_edge:
                self.session.current_node_id = first_edge['target']
        
        self.conversation_history = []
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        print(f"Call ID: {call_id}")
        print(f"Starting Node: {self.session.current_node_id}")
        print(f"{'='*80}\n")
        
    async def send_message(self, user_input: str) -> str:
        """Send a user message and get agent response"""
        print(f"👤 USER: {user_input}")
        
        # Process the input through the call session
        response_dict = await self.session.process_user_input(user_input)
        
        # Extract text from response
        response_text = response_dict.get('text', str(response_dict)) if isinstance(response_dict, dict) else str(response_dict)
        
        print(f"🤖 JAKE: {response_text}")
        print(f"📍 Current Node: {self.session.current_node_id}")
        print(f"🔢 Node Type: {self.session.flow_nodes.get(self.session.current_node_id, {}).get('type', 'unknown')}")
        print()
        
        # Store in history
        self.conversation_history.append({
            "user": user_input,
            "agent": response_text,
            "node": self.session.current_node_id,
            "node_type": self.session.flow_nodes.get(self.session.current_node_id, {}).get('type', 'unknown')
        })
        
        return response_text
        
    def check_for_repetition(self) -> bool:
        """Check if the agent repeated itself in consecutive messages"""
        if len(self.conversation_history) < 2:
            return False
            
        last_response = self.conversation_history[-1]["agent"]
        prev_response = self.conversation_history[-2]["agent"]
        
        # Check for exact repetition
        if last_response == prev_response:
            return True
            
        # Check for substantial overlap (more than 70% similar)
        last_words = set(last_response.lower().split())
        prev_words = set(prev_response.lower().split())
        
        if len(last_words) > 0:
            overlap = len(last_words.intersection(prev_words)) / len(last_words)
            if overlap > 0.7:
                return True
                
        return False
        
    def check_node_order(self, expected_nodes: List[str]) -> bool:
        """Check if nodes were visited in expected order"""
        visited_nodes = [turn["node"] for turn in self.conversation_history]
        
        # Check if all expected nodes were hit in order
        expected_index = 0
        for node in visited_nodes:
            if expected_index < len(expected_nodes) and node == expected_nodes[expected_index]:
                expected_index += 1
                
        return expected_index == len(expected_nodes)
        
    async def test_objection_on_questions_node(self):
        """
        Test Case 1: Objection when asked "what questions come to mind"
        This is the key issue - when Jake asks about questions, 
        user responds with skepticism/objection
        """
        await self.setup_session("objection_on_questions_node")
        
        # Start the conversation and navigate to Introduce Model node
        await self.send_message("Yes")  # Name confirmation
        await self.send_message("Sure")  # Help request
        await self.send_message("Yes, go ahead")  # Permission - should get us to Introduce Model
        
        # Now we should be at the "Introduce Model" node
        # which asks "What questions come to mind when you hear something like that?"
        
        # Send the critical objection RIGHT AFTER model introduction
        response = await self.send_message("I don't know, what is this some kind of marketing scam?")
        
        # Check for issues
        repeated = self.check_for_repetition()
        
        # The agent should:
        # 1. NOT repeat the previous script
        # 2. Address the objection intelligently
        # 3. Use the global prompt for recovery
        
        result = {
            "test": "objection_on_questions_node",
            "passed": not repeated and "scam" not in response.lower() or "fair" in response.lower(),
            "repeated": repeated,
            "handled_objection": "fair" in response.lower() or "understand" in response.lower(),
            "conversation": self.conversation_history
        }
        
        self.test_results.append(result)
        
        print(f"\n{'='*80}")
        print(f"TEST RESULT: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        print(f"Repeated: {repeated}")
        print(f"Handled Objection: {result['handled_objection']}")
        print(f"{'='*80}\n")
        
        return result
        
    async def test_vague_response(self):
        """
        Test Case 2: Vague response to a question
        Agent should seek clarification, not repeat
        """
        await self.setup_session("vague_response")
        
        await self.send_message("Yes")  # Name confirmation
        await self.send_message("Sure")  # Help request
        await self.send_message("Yes")  # Permission
        
        # Give a vague response to the model introduction
        response = await self.send_message("Hmm, I'm not sure")
        
        repeated = self.check_for_repetition()
        
        result = {
            "test": "vague_response",
            "passed": not repeated,
            "repeated": repeated,
            "sought_clarification": "?" in response or "what" in response.lower(),
            "conversation": self.conversation_history
        }
        
        self.test_results.append(result)
        
        print(f"\n{'='*80}")
        print(f"TEST RESULT: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        print(f"Repeated: {repeated}")
        print(f"{'='*80}\n")
        
        return result
        
    async def test_off_topic_response(self):
        """
        Test Case 3: Off-topic/random response
        Agent should redirect gracefully using global prompt
        """
        await self.setup_session("off_topic_response")
        
        await self.send_message("Yes")  # Name confirmation
        await self.send_message("Sure")  # Help request
        await self.send_message("Yes")  # Permission
        
        # Go off-topic
        response = await self.send_message("Is this about timeshares?")
        
        repeated = self.check_for_repetition()
        
        result = {
            "test": "off_topic_response",
            "passed": not repeated,
            "repeated": repeated,
            "redirected": "no" in response.lower() or "passive income" in response.lower(),
            "conversation": self.conversation_history
        }
        
        self.test_results.append(result)
        
        print(f"\n{'='*80}")
        print(f"TEST RESULT: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        print(f"Repeated: {repeated}")
        print(f"{'='*80}\n")
        
        return result
        
    async def test_multiple_objections_sequence(self):
        """
        Test Case 4: Multiple objections in sequence
        Agent should handle each uniquely without repeating
        """
        await self.setup_session("multiple_objections_sequence")
        
        await self.send_message("Yes")  # Name confirmation
        await self.send_message("Sure")  # Help request
        await self.send_message("Yes")  # Permission
        
        # First objection
        await self.send_message("This sounds like a scam")
        
        # Second objection (if still on same node)
        response = await self.send_message("I don't have time for this")
        
        repeated = self.check_for_repetition()
        
        result = {
            "test": "multiple_objections_sequence",
            "passed": not repeated,
            "repeated": repeated,
            "handled_time_objection": "time" in response.lower() or "quick" in response.lower(),
            "conversation": self.conversation_history
        }
        
        self.test_results.append(result)
        
        print(f"\n{'='*80}")
        print(f"TEST RESULT: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        print(f"Repeated: {repeated}")
        print(f"{'='*80}\n")
        
        return result
        
    async def test_flow_order(self):
        """
        Test Case 5: Verify flow follows correct node order
        Should follow: Name → Intro → Hook → Model → Questions
        """
        await self.setup_session("flow_order")
        
        await self.send_message("Yes")  # Name confirmation
        await self.send_message("Sure, what's up")  # Help request
        await self.send_message("Yes, go ahead")  # Permission
        await self.send_message("How does it work?")  # Question about model
        
        # Check if we progressed through expected nodes
        # We expect to see progression, not jumping around
        nodes_visited = [turn["node"] for turn in self.conversation_history]
        
        # Should not revisit the same node multiple times consecutively
        consecutive_same = False
        for i in range(len(nodes_visited) - 1):
            if nodes_visited[i] == nodes_visited[i + 1]:
                consecutive_same = True
                break
        
        result = {
            "test": "flow_order",
            "passed": not consecutive_same,
            "consecutive_same_node": consecutive_same,
            "nodes_visited": nodes_visited,
            "conversation": self.conversation_history
        }
        
        self.test_results.append(result)
        
        print(f"\n{'='*80}")
        print(f"TEST RESULT: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        print(f"Consecutive Same Node: {consecutive_same}")
        print(f"Nodes Visited: {nodes_visited}")
        print(f"{'='*80}\n")
        
        return result
        
    async def test_no_recall_objection(self):
        """
        Test Case 6: "I don't recall" objection early in call
        """
        await self.setup_session("no_recall_objection")
        
        await self.send_message("Yes")  # Name confirmation
        await self.send_message("Sure")  # Help request
        
        # Hit them with no recall
        response = await self.send_message("I don't remember clicking any ad")
        
        repeated = self.check_for_repetition()
        
        result = {
            "test": "no_recall_objection",
            "passed": not repeated,
            "repeated": repeated,
            "handled_no_recall": "problem" in response.lower() or "income" in response.lower(),
            "conversation": self.conversation_history
        }
        
        self.test_results.append(result)
        
        print(f"\n{'='*80}")
        print(f"TEST RESULT: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        print(f"Repeated: {repeated}")
        print(f"{'='*80}\n")
        
        return result
        
    async def test_not_interested(self):
        """
        Test Case 7: Direct "not interested" objection
        """
        await self.setup_session("not_interested")
        
        await self.send_message("Yes")  # Name confirmation
        
        # Immediate rejection
        response = await self.send_message("I'm not interested")
        
        repeated = self.check_for_repetition()
        
        result = {
            "test": "not_interested",
            "passed": not repeated,
            "repeated": repeated,
            "attempted_recovery": "?" in response or "time" in response.lower(),
            "conversation": self.conversation_history
        }
        
        self.test_results.append(result)
        
        print(f"\n{'='*80}")
        print(f"TEST RESULT: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        print(f"Repeated: {repeated}")
        print(f"{'='*80}\n")
        
        return result
        
    async def test_objection_at_introduce_model(self):
        """
        Test Case 8: Specific test for objecting at Introduce Model node
        This ensures we reach Introduce Model, then object
        """
        await self.setup_session("objection_at_introduce_model")
        
        await self.send_message("Yes")  # Name confirmation
        await self.send_message("Sure")  # Help request
        await self.send_message("Yeah, tell me")  # Permission - explicit agreement
        
        # This should now bring us to Introduce Model node
        # Let's check current node
        print(f"🎯 Expected to be at Introduce Model node, currently at: {self.session.current_node_id}")
        
        # Object with the exact phrase from user's concern
        response = await self.send_message("I don't know, what is this some kind of marketing scam? Hello?")
        
        repeated = self.check_for_repetition()
        
        # Check if agent handled it intelligently vs repeating script
        contains_script = "passive income websites" in response.lower()
        
        result = {
            "test": "objection_at_introduce_model",
            "passed": not repeated and not contains_script,
            "repeated": repeated,
            "repeated_script": contains_script,
            "current_node": self.session.current_node_id,
            "conversation": self.conversation_history
        }
        
        self.test_results.append(result)
        
        print(f"\n{'='*80}")
        print(f"TEST RESULT: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        print(f"Repeated: {repeated}")
        print(f"Repeated Script: {contains_script}")
        print(f"Current Node: {self.session.current_node_id}")
        print(f"{'='*80}\n")
        
        return result
        
    async def run_all_tests(self):
        """Run all test cases"""
        print("\n" + "="*80)
        print("JAKE AGENT COMPREHENSIVE TEST SUITE")
        print("="*80 + "\n")
        
        # Run all tests
        await self.test_objection_on_questions_node()
        await self.test_objection_at_introduce_model()  # NEW: specific introduce model test
        await self.test_vague_response()
        await self.test_off_topic_response()
        await self.test_multiple_objections_sequence()
        await self.test_flow_order()
        await self.test_no_recall_objection()
        await self.test_not_interested()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80 + "\n")
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        
        for result in self.test_results:
            status = "✅ PASSED" if result["passed"] else "❌ FAILED"
            print(f"{status}: {result['test']}")
            if result.get("repeated"):
                print(f"  ⚠️  Agent repeated itself")
            
        print(f"\n{'='*80}")
        print(f"OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        print(f"{'='*80}\n")
        
        # Save detailed results
        with open('/app/jake_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"📄 Detailed results saved to: /app/jake_test_results.json\n")
        
        return self.test_results

async def main():
    """Main test runner"""
    tester = ConversationTester()
    results = await tester.run_all_tests()
    
    # Exit with appropriate code
    failed_tests = [r for r in results if not r["passed"]]
    if failed_tests:
        print(f"\n❌ {len(failed_tests)} test(s) failed. Review the output above.\n")
        sys.exit(1)
    else:
        print(f"\n✅ All tests passed!\n")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
