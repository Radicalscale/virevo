#!/usr/bin/env python3
"""
Agent Flow Tester - Simulate complete conversation flows without phone calls

This script simulates a real conversation with an agent by:
1. Loading agent configuration from MongoDB
2. Creating a test session (simulating CallSession)
3. Sending predetermined messages as if they were user speech
4. Processing responses through the actual backend logic
5. Tracking node transitions and conversation state
6. Measuring latency and performance

Usage:
    python agent_flow_tester.py --agent-id <agent_id> [--scenario <scenario_name>]
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient

# Add backend to path
sys.path.append('/app/backend')

from calling_service import CallSession
from models import Agent

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')


class ConversationScenario:
    """Predefined conversation scenarios for testing"""
    
    COMPLIANT_PATH = [
        {"message": "Yes, this is John", "description": "Confirms name"},
        {"message": "Sure, I can help", "description": "Agrees to help"},
        {"message": "Yes, go ahead", "description": "Gives permission for 25 seconds"},
        {"message": "That sounds interesting, tell me more", "description": "Shows interest"},
        {"message": "Yeah, I'd love some extra money", "description": "Complies with $20k question"},
        {"message": "I'm employed full-time", "description": "Employment status"},
        {"message": "I make around $50,000 a year", "description": "Income disclosure"},
        {"message": "Yes, I did Uber for about 6 months", "description": "Side hustle history"},
        {"message": "I was making about $800 a month", "description": "Side hustle income"},
        {"message": "Yeah, I can definitely see that", "description": "Vehicle question - yes"},
    ]
    
    OBJECTION_PATH = [
        {"message": "Yes, this is John", "description": "Confirms name"},
        {"message": "I don't know, I'm pretty busy", "description": "Initial resistance"},
        {"message": "How much time does this take?", "description": "Time objection"},
        {"message": "Is this a scam?", "description": "Trust objection"},
        {"message": "I need to think about it", "description": "Delay objection"},
    ]
    
    CUSTOM = []  # Can be set programmatically


class AgentFlowTester:
    """Test agent conversation flows without phone calls"""
    
    def __init__(self, agent_id: str, user_id: str = None):
        self.agent_id = agent_id
        self.user_id = user_id
        self.db = None
        self.client = None
        self.agent_config = None
        self.session = None
        self.conversation_log = []
        self.node_transitions = []
        self.metrics = {
            'total_turns': 0,
            'total_latency': 0,
            'llm_calls': 0,
            'node_transitions': 0,
            'variables_extracted': {}
        }
    
    async def setup(self):
        """Initialize database connection and load agent"""
        print("🔧 Setting up Agent Flow Tester...")
        
        # Connect to MongoDB
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        print(f"✅ Connected to MongoDB: {db_name}")
        
        # Load agent configuration
        agent_doc = await self.db.agents.find_one({"id": self.agent_id})
        if not agent_doc:
            raise ValueError(f"Agent {self.agent_id} not found")
        
        self.agent_config = agent_doc
        
        # If no user_id provided, use agent's owner
        if not self.user_id:
            self.user_id = agent_doc.get('user_id')
        
        print(f"✅ Loaded agent: {agent_doc.get('name')}")
        print(f"   Type: {agent_doc.get('agent_type')}")
        print(f"   User ID: {self.user_id}")
        
        # Initialize test session
        test_call_id = f"test_{int(time.time())}"
        
        self.session = CallSession(
            call_id=test_call_id,
            agent_id=self.agent_id,
            agent_config=agent_doc,
            db=self.db,
            user_id=self.user_id,
            knowledge_base=""  # No KB for testing
        )
        
        # Set customer_name in session variables for {{customer_name}} replacement
        self.session.session_variables['customer_name'] = "John Smith"
        
        print(f"✅ Created test session: {test_call_id}")
        print()
    
    async def send_message(self, message: str, description: str = "") -> Dict:
        """Send a message and get agent response"""
        turn_start = time.time()
        
        print(f"\n{'='*70}")
        print(f"👤 USER: {message}")
        if description:
            print(f"   ({description})")
        print('='*70)
        
        try:
            # Process message through agent
            response = await self.session.process_user_input(message)
            
            turn_latency = time.time() - turn_start
            
            # Extract response details
            response_text = response.get('response', '')
            should_end = response.get('should_end_call', False)
            current_node = self.session.current_node_id
            
            print(f"🤖 AGENT: {response_text}")
            print()
            print(f"📊 Metrics:")
            print(f"   Latency: {turn_latency:.2f}s")
            print(f"   Current Node: {current_node}")
            print(f"   Should End Call: {should_end}")
            
            # Track session variables
            if hasattr(self.session, 'session_variables') and self.session.session_variables:
                print(f"   Variables: {json.dumps(self.session.session_variables, indent=6)}")
            
            # Log conversation
            self.conversation_log.append({
                'turn': len(self.conversation_log) + 1,
                'user_message': message,
                'agent_response': response_text,
                'node_id': current_node,
                'latency': turn_latency,
                'should_end': should_end,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Update metrics
            self.metrics['total_turns'] += 1
            self.metrics['total_latency'] += turn_latency
            self.metrics['llm_calls'] += 1
            
            # Track node transition
            if len(self.node_transitions) == 0 or self.node_transitions[-1] != current_node:
                self.node_transitions.append(current_node)
                self.metrics['node_transitions'] += 1
            
            # Update extracted variables
            if hasattr(self.session, 'session_variables'):
                self.metrics['variables_extracted'] = dict(self.session.session_variables)
            
            return {
                'response': response_text,
                'should_end': should_end,
                'node_id': current_node,
                'latency': turn_latency
            }
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                'error': str(e),
                'response': '',
                'should_end': False
            }
    
    async def run_scenario(self, scenario: List[Dict], auto_continue: bool = True):
        """Run a predefined conversation scenario"""
        print(f"\n{'#'*70}")
        print(f"# Running Scenario: {len(scenario)} messages")
        print(f"{'#'*70}\n")
        
        for i, turn in enumerate(scenario, 1):
            message = turn['message']
            description = turn.get('description', '')
            
            result = await self.send_message(message, description)
            
            if result.get('should_end'):
                print("\n🏁 Agent indicated call should end")
                break
            
            if not auto_continue and i < len(scenario):
                input("\nPress Enter to continue to next message...")
        
        # Print summary
        self.print_summary()
    
    async def interactive_mode(self):
        """Interactive mode - manually type messages"""
        print(f"\n{'#'*70}")
        print(f"# Interactive Mode - Type messages to test agent")
        print(f"# Type 'quit' or 'exit' to end")
        print(f"{'#'*70}\n")
        
        while True:
            try:
                user_input = input("\n👤 YOU: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                result = await self.send_message(user_input)
                
                if result.get('should_end'):
                    print("\n🏁 Agent indicated call should end")
                    break
            
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except EOFError:
                break
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test session summary"""
        print(f"\n\n{'='*70}")
        print("📊 TEST SESSION SUMMARY")
        print('='*70)
        
        print(f"\n🎯 Agent: {self.agent_config.get('name')}")
        print(f"   ID: {self.agent_id}")
        print(f"   Type: {self.agent_config.get('agent_type')}")
        
        print(f"\n💬 Conversation Metrics:")
        print(f"   Total Turns: {self.metrics['total_turns']}")
        print(f"   Total Latency: {self.metrics['total_latency']:.2f}s")
        print(f"   Average Latency: {self.metrics['total_latency'] / max(1, self.metrics['total_turns']):.2f}s")
        print(f"   LLM Calls: {self.metrics['llm_calls']}")
        
        print(f"\n🗺️  Node Transitions:")
        print(f"   Total Transitions: {self.metrics['node_transitions']}")
        print(f"   Path: {' → '.join(self.node_transitions)}")
        
        if self.metrics['variables_extracted']:
            print(f"\n📋 Variables Extracted:")
            for var_name, var_value in self.metrics['variables_extracted'].items():
                print(f"   {var_name}: {var_value}")
        
        print(f"\n📝 Full Conversation Log:")
        print(f"   {len(self.conversation_log)} turns")
        
        # Save to file
        output_file = f"/app/test_results_{self.agent_id}_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'agent': {
                    'id': self.agent_id,
                    'name': self.agent_config.get('name'),
                    'type': self.agent_config.get('agent_type')
                },
                'metrics': self.metrics,
                'node_transitions': self.node_transitions,
                'conversation': self.conversation_log
            }, f, indent=2)
        
        print(f"\n💾 Full results saved to: {output_file}")
        print('='*70)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test agent conversation flows')
    parser.add_argument('--agent-id', required=True, help='Agent ID to test')
    parser.add_argument('--user-id', help='User ID (defaults to agent owner)')
    parser.add_argument('--scenario', choices=['compliant', 'objection', 'interactive'], 
                       default='compliant', help='Scenario to run')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('--auto', action='store_true', help='Auto-continue without pausing')
    
    args = parser.parse_args()
    
    # Create tester
    tester = AgentFlowTester(agent_id=args.agent_id, user_id=args.user_id)
    
    try:
        # Setup
        await tester.setup()
        
        # Run scenario
        if args.interactive or args.scenario == 'interactive':
            await tester.interactive_mode()
        elif args.scenario == 'compliant':
            await tester.run_scenario(ConversationScenario.COMPLIANT_PATH, auto_continue=args.auto)
        elif args.scenario == 'objection':
            await tester.run_scenario(ConversationScenario.OBJECTION_PATH, auto_continue=args.auto)
    
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
