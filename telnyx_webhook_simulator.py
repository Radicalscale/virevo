#!/usr/bin/env python3
"""
Telnyx Webhook Simulator - Test with real webhook flow, no phone calls

Simulates Telnyx webhook events to test the REAL system with all overhead:
- State management
- Redis operations
- Webhook processing
- Queue management
- HTTP overhead

Measures TRUE latency: User stops speaking → Agent starts responding
(Does NOT include audio playback time)

Usage:
    python telnyx_webhook_simulator.py --agent-id <id> --interactive
    python telnyx_webhook_simulator.py --agent-id <id> --scenario compliant --target-latency 2.0
"""

import asyncio
import sys
import os
import time
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import aiohttp

sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient

# Backend URL (local)
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8001')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')


class TelnyxWebhookSimulator:
    """Simulate Telnyx webhooks to test real system with all overhead"""
    
    def __init__(self, agent_id: str, user_id: str = None, target_latency: float = None):
        self.agent_id = agent_id
        self.user_id = user_id
        self.target_latency = target_latency
        
        self.call_id = f"sim_{uuid.uuid4().hex[:16]}"
        self.call_control_id = f"v3:{uuid.uuid4().hex}"
        self.call_session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        self.db = None
        self.client = None
        self.agent_config = None
        
        self.conversation_log = []
        self.latency_measurements = []
        
        self.metrics = {
            'total_turns': 0,
            'total_latency': 0,
            'avg_latency': 0,
            'min_latency': float('inf'),
            'max_latency': 0,
            'target_latency': target_latency
        }
        
        # Track state
        self.agent_speaking = False
        self.user_speaking = False
    
    async def setup(self):
        """Initialize simulator"""
        print("🔧 Setting up Telnyx Webhook Simulator...")
        print(f"   Call ID: {self.call_id}")
        print(f"   Call Control ID: {self.call_control_id}")
        print()
        
        # Connect to MongoDB
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        print(f"✅ Connected to MongoDB: {db_name}")
        
        # Load agent
        agent_doc = await self.db.agents.find_one({"id": self.agent_id})
        if not agent_doc:
            raise ValueError(f"Agent {self.agent_id} not found")
        
        self.agent_config = agent_doc
        if not self.user_id:
            self.user_id = agent_doc.get('user_id')
        
        print(f"✅ Loaded agent: {agent_doc.get('name')}")
        print(f"   Type: {agent_doc.get('agent_type')}")
        print(f"   User ID: {self.user_id}")
        print()
        
        # Send call.initiated webhook
        await self._send_webhook('call.initiated', {
            'call_control_id': self.call_control_id,
            'call_session_id': self.call_session_id,
            'from': '+15555551234',
            'to': agent_doc.get('phone_number', '+15555556789'),
            'direction': 'incoming',
            'state': 'active'
        })
        
        print("✅ Call initiated\n")
    
    async def _send_webhook(self, event_type: str, payload: dict) -> dict:
        """Send webhook to backend and return response"""
        webhook_url = f"{BACKEND_URL}/api/webhooks/telnyx"
        
        # Build Telnyx webhook format
        webhook_data = {
            'data': {
                'event_type': event_type,
                'id': str(uuid.uuid4()),
                'occurred_at': datetime.utcnow().isoformat(),
                'payload': {
                    'call_control_id': self.call_control_id,
                    'call_leg_id': self.call_id,
                    'call_session_id': self.call_session_id,
                    **payload
                }
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=webhook_data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        print(f"⚠️  Webhook response {response.status}: {text[:200]}")
                        return {}
        except Exception as e:
            print(f"❌ Webhook error: {e}")
            return {}
    
    async def process_user_message(self, message: str, description: str = "") -> Dict:
        """
        Process user message through real webhook flow
        
        Measures TRUE latency: User stops speaking → Agent starts responding
        """
        turn_num = len(self.conversation_log) + 1
        
        print(f"\n{'='*80}")
        print(f"🎯 TURN {turn_num}: {message}")
        if description:
            print(f"   ({description})")
        print('='*80)
        
        # Calculate simulated transcription time (not part of latency measurement)
        words = len(message.split())
        transcription_time = 0.05 + (words * 0.01)  # 50ms + 10ms per word
        
        print(f"🎤 Transcribing user speech... ({transcription_time:.3f}s)")
        await asyncio.sleep(transcription_time)
        
        # Mark that user is speaking
        self.user_speaking = True
        
        # Send user.speaking webhook
        await self._send_webhook('user.speaking', {
            'call_control_id': self.call_control_id
        })
        
        # User speaks (simulate the duration)
        speech_duration = words * 0.15  # ~150ms per word
        await asyncio.sleep(speech_duration)
        
        # User STOPS speaking - START LATENCY TIMER
        print(f"\n⏱️  USER STOPPED SPEAKING - Starting latency timer...")
        latency_start = time.time()
        
        self.user_speaking = False
        
        # Send speech.final webhook with transcript
        webhook_response = await self._send_webhook('call.speak.ended', {
            'call_control_id': self.call_control_id,
            'client_state': None
        })
        
        # Now send the actual transcription
        await self._send_webhook('transcription', {
            'call_control_id': self.call_control_id,
            'transcription': {
                'alternatives': [{
                    'transcript': message,
                    'confidence': 0.98
                }],
                'is_final': True
            }
        })
        
        print(f"📨 Sent transcription webhook: '{message}'")
        
        # Wait for agent to start responding (playback.started webhook)
        # In real system, this happens when backend calls Telnyx API to play audio
        
        # Simulate backend processing time
        # The backend will:
        # 1. Process webhook
        # 2. Call LLM
        # 3. Generate TTS
        # 4. Call Telnyx playback API
        
        # For simulation, we wait for a realistic processing time
        # then trigger playback.started
        
        # Poll call_states or wait for expected processing time
        await asyncio.sleep(0.1)  # Small delay for webhook processing
        
        # Check call_logs for the response (backend should have saved it)
        max_wait = 30  # Wait up to 30 seconds for response
        wait_start = time.time()
        agent_response = None
        
        while time.time() - wait_start < max_wait:
            # Check if backend has processed and generated response
            call_log = await self.db.call_logs.find_one(
                {'call_id': self.call_id},
                sort=[('timestamp', -1)]
            )
            
            if call_log:
                transcript = call_log.get('transcript', [])
                # Look for agent response after user message
                for msg in reversed(transcript):
                    if msg.get('role') == 'agent' and msg.get('text'):
                        # Check if this is a new response
                        if not agent_response or msg.get('text') != agent_response:
                            agent_response = msg.get('text')
                            break
                
                if agent_response:
                    break
            
            await asyncio.sleep(0.1)
        
        # AGENT STARTS RESPONDING - END LATENCY TIMER
        latency = time.time() - latency_start
        
        print(f"\n⏱️  AGENT STARTED RESPONDING")
        print(f"⚡ LATENCY: {latency:.3f}s (user stopped → agent started)")
        
        # This is the TRUE latency the user experiences
        self.latency_measurements.append(latency)
        
        # Update metrics
        self.metrics['total_turns'] += 1
        self.metrics['total_latency'] += latency
        self.metrics['avg_latency'] = self.metrics['total_latency'] / self.metrics['total_turns']
        self.metrics['min_latency'] = min(self.metrics['min_latency'], latency)
        self.metrics['max_latency'] = max(self.metrics['max_latency'], latency)
        
        # Send playback.started webhook
        await self._send_webhook('call.playback.started', {
            'call_control_id': self.call_control_id,
            'media_url': 'https://fake-tts-url.com/audio.mp3'
        })
        
        self.agent_speaking = True
        
        # Display results
        print(f"\n🤖 AGENT RESPONSE:")
        print(f"   {agent_response[:200] if agent_response else '(No response captured)'}")
        
        print(f"\n📊 TURN METRICS:")
        print(f"   True Latency: {latency:.3f}s")
        print(f"   Transcription Time: {transcription_time:.3f}s (not counted in latency)")
        print(f"   Speech Duration: {speech_duration:.3f}s (not counted in latency)")
        
        if self.target_latency:
            status = "✅" if latency <= self.target_latency else "❌"
            print(f"   Target: {self.target_latency:.3f}s {status}")
        
        # Simulate agent audio playback (NOT part of latency)
        if agent_response:
            response_words = len(agent_response.split())
            playback_duration = response_words * 0.15
            print(f"\n🔊 Agent speaking for {playback_duration:.3f}s (audio playback, not latency)")
            await asyncio.sleep(playback_duration)
        
        # Send playback.ended webhook
        await self._send_webhook('call.playback.ended', {
            'call_control_id': self.call_control_id,
            'media_url': 'https://fake-tts-url.com/audio.mp3'
        })
        
        self.agent_speaking = False
        
        # Log conversation
        self.conversation_log.append({
            'turn': turn_num,
            'user_message': message,
            'agent_response': agent_response or '(No response)',
            'true_latency': latency,
            'transcription_time': transcription_time,
            'speech_duration': speech_duration,
            'met_target': latency <= self.target_latency if self.target_latency else None,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {
            'response': agent_response,
            'latency': latency,
            'met_target': latency <= self.target_latency if self.target_latency else None
        }
    
    async def run_scenario(self, messages: List[Dict]):
        """Run scenario and track if target latency is met"""
        print(f"\n{'#'*80}")
        print(f"# Running Scenario: {len(messages)} messages")
        if self.target_latency:
            print(f"# Target Latency: {self.target_latency}s per turn")
        print(f"{'#'*80}\n")
        
        for turn in messages:
            result = await self.process_user_message(turn['message'], turn.get('description', ''))
            
            if self.target_latency and result['latency'] > self.target_latency:
                print(f"\n⚠️  Turn exceeded target latency!")
        
        # Print summary
        self.print_summary()
        
        # Return whether we met target
        if self.target_latency:
            met_target = self.metrics['avg_latency'] <= self.target_latency
            return met_target
        
        return True
    
    def print_summary(self):
        """Print summary with latency analysis"""
        print(f"\n\n{'='*80}")
        print("📊 TELNYX WEBHOOK SIMULATION SUMMARY")
        print('='*80)
        
        print(f"\n🎯 Agent: {self.agent_config.get('name')}")
        print(f"   ID: {self.agent_id}")
        print(f"   Call ID: {self.call_id}")
        
        print(f"\n⚡ TRUE LATENCY METRICS (User Stop → Agent Start):")
        print(f"   Average: {self.metrics['avg_latency']:.3f}s")
        print(f"   Min: {self.metrics['min_latency']:.3f}s")
        print(f"   Max: {self.metrics['max_latency']:.3f}s")
        print(f"   Total Turns: {self.metrics['total_turns']}")
        
        if self.target_latency:
            print(f"\n🎯 TARGET ANALYSIS:")
            print(f"   Target: {self.target_latency:.3f}s")
            print(f"   Average: {self.metrics['avg_latency']:.3f}s")
            
            if self.metrics['avg_latency'] <= self.target_latency:
                print(f"   Status: ✅ MET TARGET")
            else:
                diff = self.metrics['avg_latency'] - self.target_latency
                print(f"   Status: ❌ MISSED by {diff:.3f}s")
        
        # Per-turn breakdown
        print(f"\n📊 PER-TURN LATENCY:")
        for log in self.conversation_log:
            turn = log['turn']
            latency = log['true_latency']
            target_met = "✅" if log.get('met_target', True) else "❌"
            print(f"   Turn {turn}: {latency:.3f}s {target_met}")
        
        # Identify slowest turns
        if len(self.conversation_log) > 0:
            sorted_turns = sorted(self.conversation_log, key=lambda x: x['true_latency'], reverse=True)
            print(f"\n🐌 SLOWEST TURNS:")
            for i, log in enumerate(sorted_turns[:3], 1):
                print(f"   {i}. Turn {log['turn']}: {log['true_latency']:.3f}s - '{log['user_message']}'")
        
        # Save results
        output_file = f"/app/telnyx_sim_{self.agent_id}_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'agent': {
                    'id': self.agent_id,
                    'name': self.agent_config.get('name'),
                },
                'call_id': self.call_id,
                'metrics': self.metrics,
                'conversation': self.conversation_log
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print('='*80)
    
    async def cleanup(self):
        """Cleanup resources"""
        # Send call.hangup webhook
        await self._send_webhook('call.hangup', {
            'call_control_id': self.call_control_id,
            'hangup_cause': 'normal_clearing',
            'hangup_source': 'caller'
        })
        
        if self.client:
            self.client.close()
        
        print("\n✅ Call ended and cleaned up")


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
    parser = argparse.ArgumentParser(description='Simulate Telnyx webhooks to test real system')
    parser.add_argument('--agent-id', required=True, help='Agent ID to test')
    parser.add_argument('--scenario', choices=['quick', 'compliant'], default='quick')
    parser.add_argument('--target-latency', type=float, help='Target latency in seconds')
    parser.add_argument('--user-id', help='User ID (optional)')
    
    args = parser.parse_args()
    
    simulator = TelnyxWebhookSimulator(
        agent_id=args.agent_id,
        user_id=args.user_id,
        target_latency=args.target_latency
    )
    
    try:
        await simulator.setup()
        
        scenario = SCENARIOS[args.scenario]
        met_target = await simulator.run_scenario(scenario)
        
        sys.exit(0 if met_target else 1)
    
    finally:
        await simulator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
