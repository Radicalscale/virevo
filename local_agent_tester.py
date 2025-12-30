#!/usr/bin/env python3
"""
Local Agent Tester - Test agents locally before deploying to Railway

This script allows you to:
1. Test agents in your local environment (no Railway deployment needed)
2. Profile latency and identify bottlenecks
3. Test with real MongoDB and LLM calls
4. Iterate quickly without 10+ minute deployment cycles

Usage:
    python local_agent_tester.py --agent-id <agent_id> --interactive
    python local_agent_tester.py --agent-id <agent_id> --scenario compliant
    python local_agent_tester.py --agent-id <agent_id> --profile-latency
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import List, Dict, Optional
import argparse

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from motor.motor_asyncio import AsyncIOMotorClient
from core_calling_service import CallSession

# MongoDB connection (same as production)
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')


class LatencyProfiler:
    """Profile latency at different stages of agent processing"""
    
    def __init__(self):
        self.timings = {}
        self.current_turn = 0
    
    def start_timing(self, label: str):
        """Start timing a specific operation"""
        self.timings[label] = time.time()
    
    def end_timing(self, label: str) -> float:
        """End timing and return duration"""
        if label in self.timings:
            duration = time.time() - self.timings[label]
            return duration
        return 0.0
    
    def record(self, label: str, duration: float):
        """Record a timing measurement"""
        # Check if key exists and is a list (for accumulated measurements)
        if label not in self.timings or not isinstance(self.timings[label], list):
            self.timings[label] = []
        self.timings[label].append(duration)
    
    def summary(self):
        """Print latency summary"""
        print("\n" + "="*70)
        print("LATENCY PROFILING SUMMARY")
        print("="*70)
        
        for label, durations in self.timings.items():
            if isinstance(durations, list) and durations:
                avg = sum(durations) / len(durations)
                min_d = min(durations)
                max_d = max(durations)
                print(f"\n{label}:")
                print(f"  Average: {avg:.3f}s")
                print(f"  Min: {min_d:.3f}s")
                print(f"  Max: {max_d:.3f}s")
                print(f"  Samples: {len(durations)}")


class LocalAgentTester:
    """Test agent locally with latency profiling"""
    
    def __init__(self, agent_id: str, user_id: str = None, profile: bool = False):
        self.agent_id = agent_id
        self.user_id = user_id
        self.profile = profile
        self.profiler = LatencyProfiler() if profile else None
        
        self.db = None
        self.client = None
        self.agent_config = None
        self.session = None
        self.conversation_log = []
        self.metrics = {
            'total_turns': 0,
            'total_latency': 0,
            'llm_calls': 0,
            'node_transitions': 0
        }
    
    async def setup(self):
        """Initialize database and load agent"""
        print("🔧 Setting up Local Agent Tester...")
        
        # Connect to MongoDB (same as production)
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
        
        # Initialize test session (same as production)
        test_call_id = f"local_test_{int(time.time())}"
        
        self.session = CallSession(
            call_id=test_call_id,
            agent_id=self.agent_id,
            agent_config=agent_doc,
            db=self.db,
            user_id=self.user_id,
            knowledge_base=""
        )
        
        # Set test customer name
        self.session.session_variables['customer_name'] = "Mike Rodriguez"
        
        print(f"✅ Created local test session: {test_call_id}")
        
        if self.profile:
            print(f"📊 Latency profiling ENABLED")
        
        print()
    
    async def send_message(self, message: str, description: str = "") -> Dict:
        """Send a message and get agent response with latency profiling"""
        turn_start = time.time()
        
        print(f"\n{'='*70}")
        print(f"👤 USER: {message}")
        if description:
            print(f"   ({description})")
        print('='*70)
        
        try:
            # Profile different stages
            if self.profile:
                self.profiler.start_timing('total_turn')
                self.profiler.start_timing('process_input')
            
            # Process message through agent (same as production)
            result = await self.session.process_user_input(message)
            
            if self.profile:
                process_latency = self.profiler.end_timing('process_input')
                self.profiler.record('process_input', process_latency)
            
            turn_latency = time.time() - turn_start
            
            if self.profile:
                self.profiler.end_timing('total_turn')
                self.profiler.record('total_turn', turn_latency)
            
            # Extract response details
            if result:
                response_text = result.get('text', '')
                should_end = result.get('end_call', False)
                actual_latency = result.get('latency', turn_latency)
            else:
                response_text = '(Error processing message)'
                should_end = False
                actual_latency = turn_latency
            
            current_node = self.session.current_node_id
            
            print(f"🤖 AGENT: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
            print()
            print(f"📊 Metrics:")
            print(f"   Total Latency: {turn_latency:.3f}s")
            print(f"   Process Latency: {actual_latency:.3f}s")
            print(f"   Current Node: {current_node}")
            print(f"   Should End Call: {should_end}")
            
            # Track session variables
            if hasattr(self.session, 'session_variables') and self.session.session_variables:
                vars_to_show = {k: v for k, v in self.session.session_variables.items() 
                               if k != 'now' and v}  # Skip 'now' and empty values
                if vars_to_show:
                    print(f"   Variables: {json.dumps(vars_to_show, indent=14)}")
            
            # Latency breakdown
            if self.profile:
                print(f"\n🔍 Latency Breakdown:")
                print(f"   Message Processing: {process_latency:.3f}s")
                print(f"   Other Overhead: {turn_latency - process_latency:.3f}s")
            
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
    
    async def run_scenario(self, messages: List[Dict], auto_continue: bool = True):
        """Run a predefined conversation scenario"""
        print(f"\n{'#'*70}")
        print(f"# Running Scenario: {len(messages)} messages")
        print(f"{'#'*70}\n")
        
        for i, turn in enumerate(messages, 1):
            message = turn['message']
            description = turn.get('description', '')
            
            result = await self.send_message(message, description)
            
            if result.get('should_end'):
                print("\n🏁 Agent indicated call should end")
                break
            
            if not auto_continue and i < len(messages):
                input("\nPress Enter to continue to next message...")
        
        # Print summary
        self.print_summary()
    
    async def interactive_mode(self):
        """Interactive mode - manually type messages"""
        print(f"\n{'#'*70}")
        print(f"# Interactive Mode - Type messages to test agent")
        print(f"# Commands: 'quit' or 'exit' to end, 'profile' for latency summary")
        print(f"{'#'*70}\n")
        
        while True:
            try:
                user_input = input("\n👤 YOU: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if user_input.lower() == 'profile' and self.profile:
                    self.profiler.summary()
                    continue
                
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
        print("📊 LOCAL TEST SESSION SUMMARY")
        print('='*70)
        
        print(f"\n🎯 Agent: {self.agent_config.get('name')}")
        print(f"   ID: {self.agent_id}")
        print(f"   Type: {self.agent_config.get('agent_type')}")
        
        print(f"\n💬 Conversation Metrics:")
        print(f"   Total Turns: {self.metrics['total_turns']}")
        print(f"   Total Latency: {self.metrics['total_latency']:.2f}s")
        if self.metrics['total_turns'] > 0:
            print(f"   Average Latency: {self.metrics['total_latency'] / self.metrics['total_turns']:.2f}s")
        print(f"   LLM Calls: {self.metrics['llm_calls']}")
        
        if hasattr(self.session, 'session_variables') and self.session.session_variables:
            vars_to_show = {k: v for k, v in self.session.session_variables.items() 
                           if k != 'now' and v}
            if vars_to_show:
                print(f"\n📋 Variables Extracted:")
                for var_name, var_value in vars_to_show.items():
                    print(f"   {var_name}: {var_value}")
        
        # Latency profiling summary
        if self.profile:
            self.profiler.summary()
        
        # Save to file
        output_file = f"/app/local_test_{self.agent_id}_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'agent': {
                    'id': self.agent_id,
                    'name': self.agent_config.get('name'),
                    'type': self.agent_config.get('agent_type')
                },
                'metrics': self.metrics,
                'conversation': self.conversation_log,
                'profiling': self.profiler.timings if self.profile else None
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print('='*70)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()


# Predefined scenarios
SCENARIOS = {
    'compliant': [
        {"message": "Yeah, this is Mike", "description": "Confirm name"},
        {"message": "Sure, what do you need?", "description": "Agree to help"},
        {"message": "I guess so, go ahead", "description": "Permission for pitch"},
        {"message": "That sounds interesting, tell me more", "description": "Show interest"},
        {"message": "Yeah, I'd love some extra money", "description": "$20k question"},
        {"message": "I work full-time as a manager", "description": "Employment status"},
        {"message": "I make around $65,000 a year", "description": "Income disclosure"},
        {"message": "Yeah, I did Uber Eats for a few months", "description": "Side hustle"},
        {"message": "I was making about $600 a month", "description": "Side hustle income"},
        {"message": "Yeah, I can see that working", "description": "Vehicle question"},
    ],
    
    'objections': [
        {"message": "Yeah, this is Mike", "description": "Confirm name"},
        {"message": "I'm pretty busy, what is this?", "description": "Initial resistance"},
        {"message": "Is this an MLM thing?", "description": "MLM objection"},
        {"message": "I don't know, sounds sketchy", "description": "Trust objection"},
        {"message": "I need to think about it", "description": "Delay objection"},
    ],
    
    'quick': [
        {"message": "Yeah, this is Mike", "description": "Confirm name"},
        {"message": "Sure", "description": "Agree to help"},
        {"message": "Go ahead", "description": "Permission"},
    ]
}


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test agent locally before deploying')
    parser.add_argument('--agent-id', required=True, help='Agent ID to test')
    parser.add_argument('--user-id', help='User ID (defaults to agent owner)')
    parser.add_argument('--scenario', choices=['compliant', 'objections', 'quick'], 
                       help='Predefined scenario to run')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--profile', action='store_true', help='Enable latency profiling')
    parser.add_argument('--auto', action='store_true', help='Auto-continue without pausing')
    
    args = parser.parse_args()
    
    # Create tester
    tester = LocalAgentTester(
        agent_id=args.agent_id, 
        user_id=args.user_id,
        profile=args.profile
    )
    
    try:
        # Setup
        await tester.setup()
        
        # Run scenario or interactive
        if args.interactive or not args.scenario:
            await tester.interactive_mode()
        else:
            scenario = SCENARIOS[args.scenario]
            await tester.run_scenario(scenario, auto_continue=args.auto)
    
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
