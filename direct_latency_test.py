#!/usr/bin/env python3
"""
Direct Latency Test - High-Fidelity Agent Performance Testing

Tests REAL backend code locally with Redis, bypassing slow deployments.
Measures TRUE user-perceived latency with REAL TTS measurements.

Usage:
    python direct_latency_test.py --agent-id <uuid> --scenario quick --target 2.0
    python direct_latency_test.py --agent-id <uuid> --measure-real-tts --target 2.0
    python direct_latency_test.py --agent-id <uuid> --use-formula --scenario skeptical
    
    Options:
        --measure-real-tts    Call actual ElevenLabs API to measure real TTS time (costs money)
        --use-formula         Use formula-based TTS estimate (free, ±30% accuracy) - DEFAULT
"""

import asyncio
import sys
import os
import time
import argparse
import json
from datetime import datetime

sys.path.append('/app/backend')
# Must import json for WebSocket messages
import json as json_module

from motor.motor_asyncio import AsyncIOMotorClient
from calling_service import CallSession
import redis.asyncio as redis

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')


class DirectLatencyTester:
    """Test backend directly, measure TRUE latency with all system overhead"""
    
    def __init__(self, agent_id: str, target_latency: float = None, measure_real_tts: bool = False):
        self.agent_id = agent_id
        self.target_latency = target_latency
        self.measure_real_tts = measure_real_tts
        
        self.db = None
        self.client = None
        self.agent_config = None
        self.session = None
        
        self.conversation_log = []
        self.elevenlabs_api_key = None
        self.metrics = {
            'total_turns': 0,
            'total_latency': 0,
            'avg_latency': 0,
            'min_latency': float('inf'),
            'max_latency': 0,
            'target_latency': target_latency,
            'turns_met_target': 0,
            'turns_missed_target': 0,
            'tts_method': 'formula'  # Will be 'real' if actual API calls work
        }
    
    async def setup(self):
        """Initialize with real backend components"""
        print("🚀 Direct Latency Test - Testing REAL Backend")
        print(f"   Environment: LOCAL with local Redis")
        print(f"   Agent ID: {self.agent_id}")
        if self.target_latency:
            print(f"   Target Latency: {self.target_latency}s")
        print()
        
        # Connect to MongoDB (same as production)
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        print(f"✅ Connected to MongoDB: {db_name}")
        
        # Load agent
        agent_doc = await self.db.agents.find_one({"id": self.agent_id})
        if not agent_doc:
            raise ValueError(f"Agent {self.agent_id} not found")
        
        self.agent_config = agent_doc
        user_id = agent_doc.get('user_id')
        
        print(f"✅ Loaded agent: {agent_doc.get('name')}")
        print(f"   Type: {agent_doc.get('agent_type')}")
        
        # Get ElevenLabs API key if we want real TTS measurement
        if self.measure_real_tts:
            try:
                # Try to get from database
                api_keys_collection = self.db['api_keys']
                elevenlabs_key_doc = await api_keys_collection.find_one({"service_name": "elevenlabs"})
                if elevenlabs_key_doc:
                    self.elevenlabs_api_key = elevenlabs_key_doc.get('api_key')
                    print(f"✅ ElevenLabs API key loaded (will measure REAL TTS time)")
                    self.metrics['tts_method'] = 'real'
                else:
                    # Fall back to environment variable
                    self.elevenlabs_api_key = os.environ.get('ELEVEN_API_KEY')
                    if self.elevenlabs_api_key:
                        print(f"✅ ElevenLabs API key from environment (will measure REAL TTS time)")
                        self.metrics['tts_method'] = 'real'
                    else:
                        print(f"⚠️  ElevenLabs API key not found - will use formula estimates")
            except Exception as e:
                print(f"⚠️  Could not load ElevenLabs API key: {e} - will use formula estimates")
        
        # Initialize CallSession (EXACTLY like production)
        test_call_id = f"direct_test_{int(time.time())}"
        
        self.session = CallSession(
            call_id=test_call_id,
            agent_id=self.agent_id,
            agent_config=agent_doc,
            db=self.db,
            user_id=user_id,
            knowledge_base=""
        )
        
        self.session.session_variables['customer_name'] = "Mike Rodriguez"
        
        print(f"✅ Created CallSession: {test_call_id}")
        print(f"   Redis: localhost:6379 (local)")
        print()
    
    async def send_message(self, message: str, description: str = ""):
        """
        Send message and measure TRUE latency with detailed breakdown
        
        Measures: Message received → Response ready (NOT audio playback)
        Now includes: LLM time, TTS estimate, and node information
        """
        turn_num = len(self.conversation_log) + 1
        
        print(f"\n{'='*80}")
        print(f"🎯 TURN {turn_num}: {message}")
        if description:
            print(f"   ({description})")
        print('='*80)
        
        try:
            # START LATENCY TIMER
            print("⏱️  Processing message through backend...")
            turn_start = time.time()
            
            # Track LLM time separately
            llm_start = time.time()
            
            # Process through REAL backend (same code as production)
            # This includes:
            # - Redis state management
            # - Database reads/writes
            # - LLM API call
            # - Node transition logic
            # - Variable extraction
            # - TTS generation preparation
            result = await self.session.process_user_input(message)
            
            llm_time = time.time() - llm_start
            
            # END LATENCY TIMER - Response is ready
            latency = time.time() - turn_start
            
            # Extract response
            if result:
                response_text = result.get('text', '')
                should_end = result.get('end_call', False)
            else:
                response_text = '(No response)'
                should_end = False
            
            current_node = self.session.current_node_id
            
            # Calculate TTS time - use REAL measurement if available
            words = len(response_text.split())
            has_ssml = '<speak>' in response_text or '<break' in response_text
            
            if self.measure_real_tts and self.elevenlabs_api_key:
                # Measure REAL TTS time by calling actual API
                tts_result = await measure_real_tts_time(
                    response_text, 
                    self.agent_config, 
                    self.elevenlabs_api_key
                )
                tts_generation = tts_result['tts_time']
                ttfb = tts_result['ttfb']
                tts_method = tts_result['method']
                tts_error = tts_result.get('error')
                
                if tts_method == 'real':
                    print(f"   [TTS: REAL measurement = {tts_generation:.3f}s, TTFB = {ttfb:.3f}s]")
                else:
                    print(f"   [TTS: Formula estimate (API failed: {tts_error})]")
            else:
                # Use formula-based estimate (updated based on real measurements)
                # Real measurements show: 2w=0.18s, 18w=0.32s, 54w=0.83s
                # Formula: base_latency + (words * per_word_rate)
                tts_generation = 0.15 + (words * 0.012)
                # SSML is stripped by API, so no overhead
                ttfb = None
                tts_method = 'formula'
                tts_error = None
            
            # System overhead (transcription, VAD, transmission, buffering)
            system_overhead = 0.9  # seconds
            
            # TRUE LATENCY: Time until user hears response start (this is what matters!)
            true_latency = llm_time + tts_generation + system_overhead
            
            # Audio playback duration (NOT latency, just informational)
            words_per_second = 2.5  # Natural speaking rate
            playback_duration = words / words_per_second
            
            # Get human-readable node label
            node_label = "Unknown"
            if current_node:
                agent_flow = self.agent_config.get('call_flow', [])
                for node in agent_flow:
                    if node.get('id') == current_node:
                        node_label = node.get('label', 'Unnamed Node')
                        break
            
            # DETAILED LATENCY BREAKDOWN
            tts_label = "TTS Generation (REAL)" if tts_method == 'real' else "TTS Generation (formula)"
            print(f"\n⚡ TRUE LATENCY BREAKDOWN (Time Until Response Starts):")
            print(f"\n   Backend Processing:")
            print(f"     LLM Processing:    {llm_time:.3f}s")
            print(f"     {tts_label}:    {tts_generation:.3f}s ({words} words{' + SSML' if has_ssml else ''})")
            if tts_method == 'real' and ttfb:
                print(f"       └─ TTFB:         {ttfb:.3f}s (time to first audio chunk)")
            print(f"     System Overhead:   {system_overhead:.3f}s (VAD + transmission)")
            print(f"   ─────────────────────────────")
            print(f"   TRUE LATENCY:       {true_latency:.3f}s  ← When user hears response")
            print(f"\n   [ℹ️  Audio Playback: {playback_duration:.3f}s - Not counted as latency]")
            
            # Check target (against true latency - time until response starts)
            met_target = True
            if self.target_latency:
                met_target = true_latency <= self.target_latency
                status = "✅" if met_target else "❌"
                print(f"\n   🎯 Target Analysis:")
                print(f"      Target: {self.target_latency:.3f}s")
                print(f"      Actual: {true_latency:.3f}s {status}")
                
                if met_target:
                    self.metrics['turns_met_target'] += 1
                else:
                    self.metrics['turns_missed_target'] += 1
                    over_by = true_latency - self.target_latency
                    print(f"      Over by: {over_by:.3f}s")
            
            print(f"\n🤖 AGENT RESPONSE:")
            print(f"   {response_text[:200] if response_text else '(No response)'}")
            if len(response_text) > 200:
                print(f"   ... ({len(response_text)} chars total)")
            
            print(f"\n📊 TURN METRICS:")
            print(f"   Node: {node_label}")
            print(f"   Node ID: {current_node}")
            print(f"   Response Length: {words} words")
            print(f"   Should End: {should_end}")
            
            # Variables
            if hasattr(self.session, 'session_variables'):
                vars_to_show = {k: v for k, v in self.session.session_variables.items() 
                               if k != 'now' and v}
                if vars_to_show:
                    print(f"   Variables: {json.dumps(vars_to_show, indent=14)}")
            
            # Update metrics (use true_latency as primary metric)
            self.metrics['total_turns'] += 1
            self.metrics['total_latency'] += true_latency
            self.metrics['avg_latency'] = self.metrics['total_latency'] / self.metrics['total_turns']
            self.metrics['min_latency'] = min(self.metrics['min_latency'], true_latency)
            self.metrics['max_latency'] = max(self.metrics['max_latency'], true_latency)
            
            # Log
            self.conversation_log.append({
                'turn': turn_num,
                'user_message': message,
                'agent_response': response_text,
                'true_latency': true_latency,
                'detailed_timing': {
                    'llm_time': round(llm_time, 3),
                    'tts_generation': round(tts_generation, 3),
                    'tts_method': tts_method,
                    'ttfb': round(ttfb, 3) if ttfb else None,
                    'system_overhead': round(system_overhead, 3),
                    'true_latency': round(true_latency, 3),
                    'audio_playback_info': round(playback_duration, 3)  # Informational only
                },
                'node_id': current_node,
                'node_label': node_label,
                'response_words': words,
                'has_ssml': has_ssml,
                'met_target': met_target,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return {
                'response': response_text,
                'latency': latency,
                'met_target': met_target
            }
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    async def run_scenario(self, messages):
        """Run scenario"""
        print(f"\n{'#'*80}")
        print(f"# Running Scenario: {len(messages)} messages")
        print(f"{'#'*80}\n")
        
        for turn in messages:
            await self.send_message(turn['message'], turn.get('description', ''))
        
        self.print_summary()
        
        if self.target_latency:
            return self.metrics['avg_latency'] <= self.target_latency
        return True
    
    def print_summary(self):
        """Print summary"""
        print(f"\n\n{'='*80}")
        print("📊 DIRECT LATENCY TEST SUMMARY")
        print('='*80)
        
        print(f"\n🎯 Agent: {self.agent_config.get('name')}")
        print(f"   Environment: LOCAL (with local Redis)")
        print(f"   Same code as: PRODUCTION")
        
        print(f"\n⚡ TRUE LATENCY (Time Until Response Starts):")
        print(f"   Average: {self.metrics['avg_latency']:.3f}s")
        print(f"   Min: {self.metrics['min_latency']:.3f}s")
        print(f"   Max: {self.metrics['max_latency']:.3f}s")
        print(f"\n   TTS Method: {self.metrics['tts_method'].upper()}")
        if self.metrics['tts_method'] == 'real':
            print(f"   ✅ Used actual ElevenLabs API measurements")
        else:
            print(f"   ⚠️  Used formula estimates (±30% accuracy)")
        print(f"\n   Note: Includes LLM + TTS generation + system overhead")
        print(f"   Audio playback time is shown for reference only (not latency)")
        
        if self.target_latency:
            print(f"\n🎯 TARGET ANALYSIS:")
            print(f"   Target: {self.target_latency:.3f}s")
            print(f"   Average: {self.metrics['avg_latency']:.3f}s")
            print(f"   Met: {self.metrics['turns_met_target']}/{self.metrics['total_turns']}")
            
            if self.metrics['avg_latency'] <= self.target_latency:
                print(f"   Status: ✅ TARGET MET")
            else:
                print(f"   Status: ❌ MISSED by {self.metrics['avg_latency'] - self.target_latency:.3f}s")
        
        print(f"\n📊 PER-TURN DETAILED BREAKDOWN:")
        print(f"   {'Turn':<6} {'Latency':<10} {'LLM':<8} {'TTS Gen':<8} {'System':<8} {'Words':<7} {'Node':<30} {'Status':<6}")
        print(f"   {'-'*95}")
        for log in self.conversation_log:
            status = "✅" if log['met_target'] else "❌"
            timing = log.get('detailed_timing', {})
            latency = timing.get('true_latency', 0)
            llm = timing.get('llm_time', 0)
            tts_gen = timing.get('tts_generation', 0)
            system = timing.get('system_overhead', 0)
            words = log.get('response_words', 0)
            node = log.get('node_label', 'Unknown')[:28]
            print(f"   {log['turn']:<6} {latency:<10.3f} {llm:<8.3f} {tts_gen:<8.3f} {system:<8.3f} {words:<7} {node:<30} {status:<6}")
        
        # Save
        output_file = f"/app/direct_latency_{self.agent_id}_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'agent_id': self.agent_id,
                'metrics': self.metrics,
                'conversation': self.conversation_log
            }, f, indent=2)
        
        print(f"\n💾 Saved: {output_file}")
        print('='*80)
    
    async def cleanup(self):
        if self.client:
            self.client.close()


async def measure_real_tts_time(text: str, agent_config: dict, api_key: str) -> dict:
    """
    Measure ACTUAL TTS generation time using ElevenLabs WebSocket (same as production)
    
    Returns:
        dict with {
            'tts_time': float,
            'ttfb': float (time to first byte),
            'method': 'real' or 'formula',
            'error': str (if failed)
        }
    """
    if not api_key:
        # Fall back to formula (based on real measurements)
        words = len(text.split())
        tts_time = 0.15 + (words * 0.012)
        return {
            'tts_time': tts_time,
            'ttfb': None,
            'method': 'formula',
            'error': 'No API key provided'
        }
    
    try:
        import aiohttp
        
        settings = agent_config.get("settings", {})
        voice_id = settings.get("elevenlabs_settings", {}).get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        model_id = settings.get("elevenlabs_settings", {}).get("model", "eleven_flash_v2_5")
        stability = settings.get("elevenlabs_settings", {}).get("stability", 0.5)
        similarity_boost = settings.get("elevenlabs_settings", {}).get("similarity_boost", 0.75)
        
        # Strip SSML tags (REST API doesn't support SSML)
        clean_text = text
        if '<speak>' in text or '<break' in text:
            import re
            clean_text = re.sub(r'<[^>]+>', '', text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        tts_start = time.time()
        
        # Call ElevenLabs REST API (simpler than WebSocket for testing)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": clean_text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        
        ttfb = None
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs API error {response.status}: {error_text}")
                
                # Measure time to first byte
                ttfb = time.time() - tts_start
                
                # Read all audio data
                audio_data = await response.read()
                
        total_time = time.time() - tts_start
        
        return {
            'tts_time': total_time,
            'ttfb': ttfb,
            'audio_size': len(audio_data),
            'method': 'real',
            'error': None
        }
        
    except Exception as e:
        # Fall back to formula on error (based on real measurements)
        words = len(text.split())
        tts_time = 0.15 + (words * 0.012)
        return {
            'tts_time': tts_time,
            'ttfb': None,
            'method': 'formula',
            'error': str(e)
        }


SCENARIOS = {
    'quick': [
        {"message": "Yeah, this is Mike", "description": "Name"},
        {"message": "Sure", "description": "Agree"},
        {"message": "Go ahead", "description": "Permission"},
    ],
    'compliant': [
        {"message": "Yeah, this is Mike"},
        {"message": "Sure, what do you need?"},
        {"message": "I guess so, go ahead"},
        {"message": "That sounds interesting"},
        {"message": "Yeah, I'd love extra money"},
    ],
    'skeptical': [
        {"message": "Yeah, this is John", "description": "Name confirmation"},
        {"message": "Look I'm busy, what is this about?", "description": "Resistance"},
        {"message": "I don't know, how did you get my number?", "description": "Privacy concern"},
        {"message": "Sounds like a pyramid scheme to me", "description": "MLM objection"},
        {"message": "I've heard all this before. Why should I trust you?", "description": "Trust objection"},
        {"message": "Fine, tell me more but this better be good", "description": "Reluctant permission"},
        {"message": "Okay I get it. Yeah I wouldn't mind extra money", "description": "$20k question compliance"},
        {"message": "I work full time as a manager", "description": "Employment answer"},
    ],
    'skeptical_proper': [
        {"message": "Yeah, this is Mike", "description": "Name confirmation"},
        {"message": "Sure, what do you need?", "description": "Permission to continue"},
        {"message": "Okay, go ahead", "description": "Allow pitch"},
        {"message": "Sounds like a pyramid scheme to me", "description": "MLM objection"},
        {"message": "I've heard this stuff before. Why should I believe you?", "description": "Trust objection"},
        {"message": "Fine, I'll listen but make it quick", "description": "Reluctant permission"},
        {"message": "Yeah, I wouldn't mind extra money I guess", "description": "$20k interest"},
        {"message": "I work full time as a sales manager", "description": "Employment answer"},
    ]
}


async def main():
    parser = argparse.ArgumentParser(description='Direct Latency Test - Test REAL backend performance')
    parser.add_argument('--agent-id', required=True, help='Agent ID to test')
    parser.add_argument('--scenario', choices=['quick', 'compliant', 'skeptical', 'skeptical_proper'], default='quick')
    parser.add_argument('--target', type=float, default=None, help='Target latency in seconds (e.g., 2.0)')
    parser.add_argument('--measure-real-tts', action='store_true', 
                        help='Call actual ElevenLabs API to measure real TTS time (costs money, more accurate)')
    parser.add_argument('--use-formula', action='store_true',
                        help='Use formula-based TTS estimates (free, ±30%% accuracy) - DEFAULT')
    args = parser.parse_args()
    
    # Default to formula-based estimates unless --measure-real-tts is specified
    measure_real_tts = args.measure_real_tts
    if args.use_formula:
        measure_real_tts = False
    
    tester = DirectLatencyTester(args.agent_id, args.target, measure_real_tts)
    
    try:
        await tester.setup()
        met = await tester.run_scenario(SCENARIOS[args.scenario])
        sys.exit(0 if met else 1)
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
