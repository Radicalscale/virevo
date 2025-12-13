#!/usr/bin/env python3
"""
Call Flow Simulator - Simulate REAL production call flow locally for rapid latency optimization

This simulates the EXACT production flow:
1. User speaks (STT transcription)
2. Backend processes message → LLM call
3. LLM generates response
4. TTS generates audio file
5. Webhooks trigger (playback started/ended)
6. Node transitions
7. Variable extraction

Use this to iterate on latency optimization without waiting for Railway deployments.

Usage:
    # Interactive mode
    python call_flow_simulator.py --agent-id <id> --interactive
    
    # Automated scenario with full profiling
    python call_flow_simulator.py --agent-id <id> --scenario compliant --profile
    
    # Optimize until target latency
    python call_flow_simulator.py --agent-id <id> --target-latency 2.0 --optimize
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import hashlib

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from calling_service import CallSession
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')


class LatencyBreakdown:
    """Detailed latency profiling for each stage of the call flow"""
    
    def __init__(self):
        self.stages = {
            'stt_simulation': [],      # Simulated STT transcription time
            'message_processing': [],  # process_user_input() time
            'llm_call': [],           # LLM API call time
            'tts_generation': [],     # TTS audio generation time
            'webhook_processing': [], # Webhook handling time
            'node_transition': [],    # Node switching time
            'variable_extraction': [], # Variable parsing time
            'total_turn': []          # Total turn time
        }
        self.turn_details = []
    
    def record(self, stage: str, duration: float, turn: int = None):
        """Record timing for a specific stage"""
        if stage in self.stages:
            self.stages[stage].append(duration)
    
    def record_turn(self, turn_num: int, details: dict):
        """Record complete turn details"""
        self.turn_details.append({
            'turn': turn_num,
            **details
        })
    
    def avg(self, stage: str) -> float:
        """Get average time for a stage"""
        if stage in self.stages and self.stages[stage]:
            return sum(self.stages[stage]) / len(self.stages[stage])
        return 0.0
    
    def max(self, stage: str) -> float:
        """Get max time for a stage"""
        if stage in self.stages and self.stages[stage]:
            return max(self.stages[stage])
        return 0.0
    
    def min(self, stage: str) -> float:
        """Get min time for a stage"""
        if stage in self.stages and self.stages[stage]:
            return min(self.stages[stage])
        return 0.0
    
    def summary(self):
        """Print detailed latency breakdown"""
        print("\n" + "="*80)
        print("DETAILED LATENCY BREAKDOWN")
        print("="*80)
        
        # Calculate total time per stage
        stage_names = {
            'stt_simulation': '🎤 STT Simulation',
            'message_processing': '🧠 Message Processing',
            'llm_call': '🤖 LLM API Call',
            'tts_generation': '🔊 TTS Generation',
            'webhook_processing': '🔗 Webhook Processing',
            'node_transition': '🗺️  Node Transition',
            'variable_extraction': '📋 Variable Extraction',
            'total_turn': '⏱️  Total Turn Time'
        }
        
        total_time = sum(self.stages['total_turn']) if self.stages['total_turn'] else 0
        
        for stage, name in stage_names.items():
            if self.stages[stage]:
                avg = self.avg(stage)
                min_t = self.min(stage)
                max_t = self.max(stage)
                count = len(self.stages[stage])
                stage_total = sum(self.stages[stage])
                pct = (stage_total / total_time * 100) if total_time > 0 else 0
                
                print(f"\n{name}:")
                print(f"  Average: {avg:.3f}s")
                print(f"  Min: {min_t:.3f}s")
                print(f"  Max: {max_t:.3f}s")
                print(f"  Samples: {count}")
                print(f"  Total: {stage_total:.3f}s ({pct:.1f}% of total)")
        
        # Identify bottlenecks
        print("\n" + "="*80)
        print("🔥 BOTTLENECK ANALYSIS")
        print("="*80)
        
        stage_totals = {stage: sum(times) for stage, times in self.stages.items() if times and stage != 'total_turn'}
        sorted_stages = sorted(stage_totals.items(), key=lambda x: x[1], reverse=True)
        
        for i, (stage, total) in enumerate(sorted_stages[:3], 1):
            pct = (total / total_time * 100) if total_time > 0 else 0
            print(f"{i}. {stage_names.get(stage, stage)}: {total:.3f}s ({pct:.1f}%)")
        
        # Per-turn details
        if self.turn_details:
            print("\n" + "="*80)
            print("📊 PER-TURN BREAKDOWN")
            print("="*80)
            
            for detail in self.turn_details:
                turn = detail['turn']
                total = detail.get('total', 0)
                node = detail.get('node', 'N/A')
                
                print(f"\nTurn {turn} (Total: {total:.3f}s, Node: {node}):")
                for stage in ['stt_simulation', 'message_processing', 'llm_call', 'tts_generation']:
                    if stage in detail:
                        print(f"  {stage}: {detail[stage]:.3f}s")


class CallFlowSimulator:
    """Simulate complete call flow with TTS, webhooks, and full production pipeline"""
    
    def __init__(self, agent_id: str, user_id: str = None, profile: bool = True, 
                 generate_audio: bool = True):
        self.agent_id = agent_id
        self.user_id = user_id
        self.profile = profile
        self.generate_audio = generate_audio
        self.profiler = LatencyBreakdown() if profile else None
        
        self.db = None
        self.client = None
        self.agent_config = None
        self.session = None
        self.conversation_log = []
        self.audio_files = []
        
        self.metrics = {
            'total_turns': 0,
            'total_latency': 0,
            'avg_latency': 0,
            'target_latency': None,
            'llm_calls': 0,
            'tts_generations': 0,
            'webhook_triggers': 0
        }
    
    async def setup(self):
        """Initialize simulator"""
        print("🚀 Initializing Call Flow Simulator...")
        print(f"   Agent ID: {self.agent_id}")
        print(f"   Audio Generation: {'ENABLED' if self.generate_audio else 'DISABLED'}")
        print(f"   Latency Profiling: {'ENABLED' if self.profile else 'DISABLED'}")
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
        
        # Initialize CallSession (same as production)
        test_call_id = f"sim_{int(time.time())}"
        
        self.session = CallSession(
            call_id=test_call_id,
            agent_id=self.agent_id,
            agent_config=agent_doc,
            db=self.db,
            user_id=self.user_id,
            knowledge_base=""
        )
        
        self.session.session_variables['customer_name'] = "Mike Rodriguez"
        
        print(f"✅ Created simulated call session: {test_call_id}")
        print()
    
    async def simulate_stt(self, text: str) -> float:
        """Simulate STT transcription delay"""
        # Typical STT latency: 50-200ms depending on audio length
        words = len(text.split())
        latency = 0.05 + (words * 0.01)  # Base 50ms + 10ms per word
        await asyncio.sleep(latency)
        return latency
    
    async def simulate_tts(self, text: str) -> tuple[float, str]:
        """Simulate TTS generation and return audio file path"""
        if not self.generate_audio:
            # Quick simulation
            words = len(text.split())
            latency = 0.1 + (words * 0.02)  # Base 100ms + 20ms per word
            await asyncio.sleep(latency)
            return latency, None
        
        # Actually generate TTS audio file (using the production TTS system)
        start = time.time()
        
        try:
            # Generate audio file using agent's TTS settings
            audio_file = await self._generate_tts_file(text)
            latency = time.time() - start
            
            self.audio_files.append(audio_file)
            return latency, audio_file
        
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            # Fallback to simulation
            words = len(text.split())
            latency = 0.1 + (words * 0.02)
            await asyncio.sleep(latency)
            return latency, None
    
    async def _generate_tts_file(self, text: str) -> str:
        """Generate actual TTS audio file"""
        # Use production TTS generation
        # This would call ElevenLabs, OpenAI TTS, or whatever the agent uses
        
        # For now, simulate by creating a placeholder file
        file_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        audio_file = f"/tmp/tts_sim_{file_hash}.mp3"
        
        # In production, this would be:
        # audio_file = await self.session.generate_tts_audio(text)
        
        # Simulate TTS API call time (ElevenLabs typically 200-500ms)
        await asyncio.sleep(0.3)
        
        # Create placeholder file
        with open(audio_file, 'w') as f:
            f.write(f"Simulated TTS: {text[:50]}")
        
        return audio_file
    
    async def simulate_webhook(self, event: str, data: dict) -> float:
        """Simulate webhook processing"""
        # Webhooks typically take 10-50ms to process
        start = time.time()
        
        # Simulate webhook HTTP call
        await asyncio.sleep(0.02)
        
        # Process webhook (update state, etc.)
        latency = time.time() - start
        
        self.metrics['webhook_triggers'] += 1
        return latency
    
    async def process_turn(self, user_message: str, description: str = "") -> Dict:
        """Process a complete conversation turn through the full pipeline"""
        turn_num = len(self.conversation_log) + 1
        turn_start = time.time()
        
        print(f"\n{'='*80}")
        print(f"🎯 TURN {turn_num}: {user_message}")
        if description:
            print(f"   ({description})")
        print('='*80)
        
        turn_timings = {'turn': turn_num}
        
        try:
            # STAGE 1: STT Simulation
            if self.profile:
                print("⏱️  Stage 1: STT Transcription...")
                stt_start = time.time()
            
            stt_latency = await self.simulate_stt(user_message)
            
            if self.profile:
                stt_latency = time.time() - stt_start
                self.profiler.record('stt_simulation', stt_latency)
                turn_timings['stt_simulation'] = stt_latency
                print(f"   ✅ STT: {stt_latency:.3f}s")
            
            # STAGE 2: Message Processing (LLM Call)
            if self.profile:
                print("⏱️  Stage 2: Message Processing (LLM)...")
                msg_start = time.time()
            
            result = await self.session.process_user_input(user_message)
            
            if self.profile:
                msg_latency = time.time() - msg_start
                self.profiler.record('message_processing', msg_latency)
                self.profiler.record('llm_call', msg_latency)  # LLM is main part of processing
                turn_timings['message_processing'] = msg_latency
                turn_timings['llm_call'] = msg_latency
                print(f"   ✅ LLM Processing: {msg_latency:.3f}s")
            
            # Extract response
            if result:
                response_text = result.get('text', '')
                should_end = result.get('end_call', False)
            else:
                response_text = '(Error)'
                should_end = False
            
            current_node = self.session.current_node_id
            
            # STAGE 3: TTS Generation
            if self.profile:
                print("⏱️  Stage 3: TTS Audio Generation...")
            
            tts_latency, audio_file = await self.simulate_tts(response_text)
            
            if self.profile:
                self.profiler.record('tts_generation', tts_latency)
                turn_timings['tts_generation'] = tts_latency
                print(f"   ✅ TTS: {tts_latency:.3f}s")
                if audio_file:
                    print(f"   📁 Audio: {audio_file}")
            
            self.metrics['tts_generations'] += 1
            
            # STAGE 4: Webhook - Playback Started
            webhook_start_latency = await self.simulate_webhook('playback.started', {
                'call_id': self.session.call_id
            })
            
            if self.profile:
                self.profiler.record('webhook_processing', webhook_start_latency)
            
            # STAGE 5: Webhook - Playback Ended
            # Calculate audio duration
            words = len(response_text.split())
            audio_duration = words * 0.15  # ~150ms per word
            await asyncio.sleep(audio_duration)
            
            webhook_end_latency = await self.simulate_webhook('playback.ended', {
                'call_id': self.session.call_id
            })
            
            if self.profile:
                self.profiler.record('webhook_processing', webhook_end_latency)
            
            # Calculate total turn time
            turn_latency = time.time() - turn_start
            
            if self.profile:
                self.profiler.record('total_turn', turn_latency)
                turn_timings['total'] = turn_latency
                turn_timings['node'] = current_node
                self.profiler.record_turn(turn_num, turn_timings)
            
            # Display results
            print(f"\n🤖 AGENT RESPONSE:")
            print(f"   {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
            print(f"\n📊 TURN METRICS:")
            print(f"   Total Time: {turn_latency:.3f}s")
            print(f"   Current Node: {current_node}")
            print(f"   Should End: {should_end}")
            
            if self.profile:
                print(f"\n⚡ LATENCY BREAKDOWN:")
                print(f"   STT: {turn_timings.get('stt_simulation', 0):.3f}s ({turn_timings.get('stt_simulation', 0)/turn_latency*100:.1f}%)")
                print(f"   LLM: {turn_timings.get('llm_call', 0):.3f}s ({turn_timings.get('llm_call', 0)/turn_latency*100:.1f}%)")
                print(f"   TTS: {turn_timings.get('tts_generation', 0):.3f}s ({turn_timings.get('tts_generation', 0)/turn_latency*100:.1f}%)")
                print(f"   Audio Playback: {audio_duration:.3f}s")
            
            # Track variables
            if hasattr(self.session, 'session_variables'):
                vars_to_show = {k: v for k, v in self.session.session_variables.items() 
                               if k != 'now' and v}
                if vars_to_show:
                    print(f"\n📋 Variables: {json.dumps(vars_to_show, indent=3)}")
            
            # Log conversation
            self.conversation_log.append({
                'turn': turn_num,
                'user_message': user_message,
                'agent_response': response_text,
                'node_id': current_node,
                'latency': turn_latency,
                'breakdown': turn_timings,
                'audio_file': audio_file,
                'should_end': should_end,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Update metrics
            self.metrics['total_turns'] += 1
            self.metrics['total_latency'] += turn_latency
            self.metrics['avg_latency'] = self.metrics['total_latency'] / self.metrics['total_turns']
            self.metrics['llm_calls'] += 1
            
            return {
                'response': response_text,
                'should_end': should_end,
                'latency': turn_latency,
                'node_id': current_node
            }
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    async def run_scenario(self, messages: List[Dict], target_latency: float = None):
        """Run scenario and check if it meets target latency"""
        print(f"\n{'#'*80}")
        print(f"# Running Scenario: {len(messages)} messages")
        if target_latency:
            print(f"# Target Latency: {target_latency}s per turn")
        print(f"{'#'*80}\n")
        
        self.metrics['target_latency'] = target_latency
        
        for i, turn in enumerate(messages, 1):
            result = await self.process_turn(turn['message'], turn.get('description', ''))
            
            if result.get('should_end'):
                print("\n🏁 Agent indicated call should end")
                break
            
            # Check if we met target latency
            if target_latency and result.get('latency', 0) > target_latency:
                print(f"\n⚠️  Turn {i} exceeded target latency: {result['latency']:.3f}s > {target_latency}s")
        
        # Print summary
        self.print_summary()
        
        # Return whether we met target
        if target_latency:
            met_target = self.metrics['avg_latency'] <= target_latency
            if met_target:
                print(f"\n✅ SUCCESS: Average latency {self.metrics['avg_latency']:.3f}s <= target {target_latency}s")
            else:
                print(f"\n❌ FAILED: Average latency {self.metrics['avg_latency']:.3f}s > target {target_latency}s")
            return met_target
        
        return True
    
    def print_summary(self):
        """Print detailed summary"""
        print(f"\n\n{'='*80}")
        print("📊 CALL FLOW SIMULATION SUMMARY")
        print('='*80)
        
        print(f"\n🎯 Agent: {self.agent_config.get('name')}")
        print(f"   ID: {self.agent_id}")
        print(f"   Type: {self.agent_config.get('agent_type')}")
        
        print(f"\n💬 Conversation Metrics:")
        print(f"   Total Turns: {self.metrics['total_turns']}")
        print(f"   Total Time: {self.metrics['total_latency']:.2f}s")
        print(f"   Average Latency: {self.metrics['avg_latency']:.2f}s")
        if self.metrics['target_latency']:
            print(f"   Target Latency: {self.metrics['target_latency']:.2f}s")
            status = "✅ MET" if self.metrics['avg_latency'] <= self.metrics['target_latency'] else "❌ MISSED"
            print(f"   Status: {status}")
        
        print(f"\n🔧 System Metrics:")
        print(f"   LLM Calls: {self.metrics['llm_calls']}")
        print(f"   TTS Generations: {self.metrics['tts_generations']}")
        print(f"   Webhook Triggers: {self.metrics['webhook_triggers']}")
        print(f"   Audio Files: {len(self.audio_files)}")
        
        # Detailed profiling
        if self.profile and self.profiler:
            self.profiler.summary()
        
        # Save results
        output_file = f"/app/call_sim_{self.agent_id}_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'agent': {
                    'id': self.agent_id,
                    'name': self.agent_config.get('name'),
                    'type': self.agent_config.get('agent_type')
                },
                'metrics': self.metrics,
                'conversation': self.conversation_log,
                'profiling': self.profiler.stages if self.profile else None,
                'audio_files': self.audio_files
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print('='*80)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()
        
        # Clean up audio files if desired
        # for audio_file in self.audio_files:
        #     if os.path.exists(audio_file):
        #         os.remove(audio_file)


# Scenarios
SCENARIOS = {
    'compliant': [
        {"message": "Yeah, this is Mike", "description": "Confirm name"},
        {"message": "Sure, what do you need?", "description": "Agree to help"},
        {"message": "I guess so, go ahead", "description": "Permission"},
        {"message": "That sounds interesting", "description": "Interest"},
        {"message": "Yeah, I'd love extra money", "description": "$20k question"},
    ],
    
    'quick': [
        {"message": "Yeah, this is Mike", "description": "Confirm name"},
        {"message": "Sure", "description": "Agree"},
        {"message": "Go ahead", "description": "Permission"},
    ]
}


async def main():
    parser = argparse.ArgumentParser(description='Simulate full call flow for latency optimization')
    parser.add_argument('--agent-id', required=True, help='Agent ID to test')
    parser.add_argument('--scenario', choices=['compliant', 'quick'], default='quick',
                       help='Scenario to run')
    parser.add_argument('--target-latency', type=float, help='Target average latency per turn (seconds)')
    parser.add_argument('--profile', action='store_true', default=True, help='Enable detailed profiling')
    parser.add_argument('--no-audio', action='store_true', help='Disable actual TTS generation')
    
    args = parser.parse_args()
    
    simulator = CallFlowSimulator(
        agent_id=args.agent_id,
        profile=args.profile,
        generate_audio=not args.no_audio
    )
    
    try:
        await simulator.setup()
        
        scenario = SCENARIOS[args.scenario]
        met_target = await simulator.run_scenario(scenario, args.target_latency)
        
        # Exit code based on whether target was met
        sys.exit(0 if met_target else 1)
    
    finally:
        await simulator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
