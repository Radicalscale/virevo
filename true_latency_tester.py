#!/usr/bin/env python3
"""
True Latency Tester - Test REAL backend with REAL measurements

This tests your LOCAL backend (with local Redis) exactly like production:
- Sends messages to real Agent Tester API endpoints
- Measures TRUE latency: message sent → response received (NOT audio playback)
- Includes ALL system overhead (Redis, state management, DB writes)
- Iterate back-to-back without deployments

Usage:
    python true_latency_tester.py --agent-id <id> --scenario quick --target 2.0
    python true_latency_tester.py --agent-id <id> --interactive --target 2.0
"""

import asyncio
import sys
import time
import json
import argparse
import aiohttp
from datetime import datetime
from typing import List, Dict

BACKEND_URL = "http://localhost:8001"


class TrueLatencyTester:
    """Test real backend and measure true latency"""
    
    def __init__(self, agent_id: str, target_latency: float = None):
        self.agent_id = agent_id
        self.target_latency = target_latency
        
        self.session_id = None
        self.conversation_log = []
        
        self.metrics = {
            'total_turns': 0,
            'total_latency': 0,
            'avg_latency': 0,
            'min_latency': float('inf'),
            'max_latency': 0,
            'target_latency': target_latency,
            'turns_met_target': 0,
            'turns_missed_target': 0
        }
    
    async def start_session(self):
        """Start test session with real backend"""
        print("🔧 Starting test session with REAL backend...")
        print(f"   Backend: {BACKEND_URL}")
        print(f"   Agent ID: {self.agent_id}")
        if self.target_latency:
            print(f"   Target Latency: {self.target_latency}s")
        print()
        
        url = f"{BACKEND_URL}/api/agents/{self.agent_id}/test/start"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.session_id = data['session_id']
                    print(f"✅ Session started: {self.session_id}")
                    print(f"   Agent: {data.get('agent_name')}")
                    print()
                    return True
                else:
                    text = await response.text()
                    print(f"❌ Failed to start session: {response.status}")
                    print(f"   {text}")
                    return False
    
    async def send_message(self, message: str, description: str = "") -> Dict:
        """
        Send message and measure TRUE latency
        
        TRUE LATENCY = Time from message sent → response received
        EXCLUDES audio playback time
        """
        turn_num = len(self.conversation_log) + 1
        
        print(f"\n{'='*80}")
        print(f"🎯 TURN {turn_num}: {message}")
        if description:
            print(f"   ({description})")
        print('='*80)
        
        if not self.session_id:
            print("❌ No active session. Starting one...")
            if not await self.start_session():
                return {'error': 'Failed to start session'}
        
        url = f"{BACKEND_URL}/api/agents/{self.agent_id}/test/message"
        
        payload = {
            'message': message,
            'session_id': self.session_id
        }
        
        # START LATENCY TIMER - Message sent
        print("⏱️  Sending message to backend...")
        latency_start = time.time()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        text = await response.text()
                        print(f"❌ Error: {response.status} - {text}")
                        return {'error': text}
                    
                    data = await response.json()
                    
                    # END LATENCY TIMER - Response received
                    latency = time.time() - latency_start
                    
                    # Extract response details
                    agent_response = data.get('agent_response', '')
                    current_node = data.get('current_node_id')
                    variables = data.get('variables', {})
                    metrics = data.get('metrics', {})
                    
                    # TRUE LATENCY (excludes any audio playback time)
                    print(f"\n⚡ TRUE LATENCY: {latency:.3f}s")
                    print(f"   (Message sent → Response received)")
                    
                    # Check against target
                    met_target = True
                    if self.target_latency:
                        met_target = latency <= self.target_latency
                        status = "✅" if met_target else "❌"
                        print(f"   Target: {self.target_latency:.3f}s {status}")
                        
                        if met_target:
                            self.metrics['turns_met_target'] += 1
                        else:
                            self.metrics['turns_missed_target'] += 1
                    
                    print(f"\n🤖 AGENT RESPONSE:")
                    print(f"   {agent_response[:200] if agent_response else '(No response)'}")
                    
                    print(f"\n📊 TURN METRICS:")
                    print(f"   Node: {current_node}")
                    print(f"   Backend Avg Latency: {metrics.get('avg_latency', 0):.3f}s")
                    print(f"   Total Turns: {metrics.get('total_turns', 0)}")
                    
                    if variables:
                        vars_to_show = {k: v for k, v in variables.items() if k != 'now' and v}
                        if vars_to_show:
                            print(f"   Variables: {json.dumps(vars_to_show, indent=14)}")
                    
                    # Update metrics
                    self.metrics['total_turns'] += 1
                    self.metrics['total_latency'] += latency
                    self.metrics['avg_latency'] = self.metrics['total_latency'] / self.metrics['total_turns']
                    self.metrics['min_latency'] = min(self.metrics['min_latency'], latency)
                    self.metrics['max_latency'] = max(self.metrics['max_latency'], latency)
                    
                    # Log conversation
                    self.conversation_log.append({
                        'turn': turn_num,
                        'user_message': message,
                        'agent_response': agent_response,
                        'true_latency': latency,
                        'node_id': current_node,
                        'met_target': met_target,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
                    return {
                        'response': agent_response,
                        'latency': latency,
                        'met_target': met_target,
                        'node_id': current_node
                    }
            
            except Exception as e:
                print(f"❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
                return {'error': str(e)}
    
    async def run_scenario(self, messages: List[Dict]):
        """Run predefined scenario"""
        print(f"\n{'#'*80}")
        print(f"# Running Scenario: {len(messages)} messages")
        if self.target_latency:
            print(f"# Target Latency: {self.target_latency}s per turn")
        print(f"{'#'*80}\n")
        
        for turn in messages:
            result = await self.send_message(turn['message'], turn.get('description', ''))
            
            if result.get('error'):
                print(f"\n⚠️  Error occurred, stopping scenario")
                break
        
        # Print summary
        self.print_summary()
        
        # Return whether we met target
        if self.target_latency:
            met_target = self.metrics['avg_latency'] <= self.target_latency
            return met_target
        
        return True
    
    async def interactive_mode(self):
        """Interactive testing"""
        print(f"\n{'#'*80}")
        print(f"# Interactive Mode - Type messages to test")
        print(f"# Commands: 'quit' to exit, 'reset' to clear session")
        print(f"{'#'*80}\n")
        
        while True:
            try:
                user_input = input("\n👤 YOU: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if user_input.lower() == 'reset':
                    await self.reset_session()
                    continue
                
                if not user_input:
                    continue
                
                await self.send_message(user_input)
            
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except EOFError:
                break
        
        # Print summary
        self.print_summary()
    
    async def reset_session(self):
        """Reset test session"""
        if not self.session_id:
            print("No active session to reset")
            return
        
        url = f"{BACKEND_URL}/api/agents/{self.agent_id}/test/reset"
        payload = {'session_id': self.session_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    print("✅ Session reset")
                    self.conversation_log = []
                    self.metrics = {
                        'total_turns': 0,
                        'total_latency': 0,
                        'avg_latency': 0,
                        'min_latency': float('inf'),
                        'max_latency': 0,
                        'target_latency': self.target_latency,
                        'turns_met_target': 0,
                        'turns_missed_target': 0
                    }
                else:
                    print(f"❌ Failed to reset: {response.status}")
    
    def print_summary(self):
        """Print detailed summary"""
        print(f"\n\n{'='*80}")
        print("📊 TRUE LATENCY TEST SUMMARY")
        print('='*80)
        
        print(f"\n🎯 Agent ID: {self.agent_id}")
        print(f"   Session: {self.session_id}")
        print(f"   Environment: LOCAL (with local Redis)")
        
        print(f"\n⚡ TRUE LATENCY METRICS (Message Sent → Response Received):")
        print(f"   Average: {self.metrics['avg_latency']:.3f}s")
        print(f"   Min: {self.metrics['min_latency']:.3f}s")
        print(f"   Max: {self.metrics['max_latency']:.3f}s")
        print(f"   Total Turns: {self.metrics['total_turns']}")
        
        if self.target_latency:
            print(f"\n🎯 TARGET ANALYSIS:")
            print(f"   Target: {self.target_latency:.3f}s")
            print(f"   Average: {self.metrics['avg_latency']:.3f}s")
            print(f"   Turns Met Target: {self.metrics['turns_met_target']}")
            print(f"   Turns Missed Target: {self.metrics['turns_missed_target']}")
            
            if self.metrics['avg_latency'] <= self.target_latency:
                print(f"   Status: ✅ TARGET MET")
            else:
                diff = self.metrics['avg_latency'] - self.target_latency
                print(f"   Status: ❌ MISSED by {diff:.3f}s")
        
        # Per-turn breakdown
        if self.conversation_log:
            print(f"\n📊 PER-TURN LATENCY:")
            for log in self.conversation_log:
                turn = log['turn']
                latency = log['true_latency']
                target_met = "✅" if log.get('met_target', True) else "❌"
                msg = log['user_message'][:40]
                print(f"   Turn {turn}: {latency:.3f}s {target_met} - '{msg}'")
            
            # Identify slowest turns
            sorted_turns = sorted(self.conversation_log, key=lambda x: x['true_latency'], reverse=True)
            print(f"\n🐌 SLOWEST TURNS:")
            for i, log in enumerate(sorted_turns[:3], 1):
                print(f"   {i}. Turn {log['turn']}: {log['true_latency']:.3f}s - '{log['user_message']}'")
        
        # Save results
        output_file = f"/app/latency_test_{self.agent_id}_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'agent_id': self.agent_id,
                'session_id': self.session_id,
                'environment': 'local_with_redis',
                'backend_url': BACKEND_URL,
                'metrics': self.metrics,
                'conversation': self.conversation_log
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print('='*80)
        
        # Recommendations
        if self.target_latency and self.metrics['avg_latency'] > self.target_latency:
            print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
            print(f"   1. Check which turns were slowest (see above)")
            print(f"   2. Look at those nodes in your agent configuration")
            print(f"   3. Consider: Convert 'prompt' nodes to 'script' nodes")
            print(f"   4. Consider: Reduce response text length")
            print(f"   5. Consider: Simplify system prompts")
            print(f"   6. Run test again after changes (instant feedback!)")
            print()


# Scenarios
SCENARIOS = {
    'quick': [
        {"message": "Yeah, this is Mike", "description": "Confirm name"},
        {"message": "Sure", "description": "Agree"},
        {"message": "Go ahead", "description": "Permission"},
    ],
    
    'compliant': [
        {"message": "Yeah, this is Mike", "description": "Confirm name"},
        {"message": "Sure, what do you need?", "description": "Agree to help"},
        {"message": "I guess so, go ahead", "description": "Permission"},
        {"message": "That sounds interesting", "description": "Interest"},
        {"message": "Yeah, I'd love extra money", "description": "$20k question"},
    ]
}


async def main():
    parser = argparse.ArgumentParser(description='Test real backend with true latency measurements')
    parser.add_argument('--agent-id', required=True, help='Agent ID to test')
    parser.add_argument('--scenario', choices=['quick', 'compliant'], help='Predefined scenario')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--target', type=float, help='Target latency in seconds')
    
    args = parser.parse_args()
    
    tester = TrueLatencyTester(
        agent_id=args.agent_id,
        target_latency=args.target
    )
    
    try:
        # Start session
        if not await tester.start_session():
            sys.exit(1)
        
        # Run scenario or interactive
        if args.interactive:
            await tester.interactive_mode()
        elif args.scenario:
            scenario = SCENARIOS[args.scenario]
            met_target = await tester.run_scenario(scenario)
            sys.exit(0 if met_target else 1)
        else:
            print("❌ Must specify --scenario or --interactive")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
