#!/usr/bin/env python3
"""
Agent Node Debugging Tool
=========================
Simulates a call flow without actual phone/TTS to debug node transitions and LLM behavior.
Connects to real MongoDB, uses real agent config, captures all prompts and responses.

Usage:
    python3 debug_agent_nodes.py --agent-id "6924d01eefc65d7e63707bb8"
    
    # Or with scripted conversation:
    python3 debug_agent_nodes.py --agent-id "6924d01eefc65d7e63707bb8" --script "script.txt"
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pymongo import MongoClient
from bson import ObjectId

# Configure logging to capture Backend Prompt Logs
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)
# Enable calling service logs
logging.getLogger("backend.calling_service").setLevel(logging.INFO)

# MongoDB connection
MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'


class MockTTSSession:
    """Mock TTS session that captures sentences instead of playing them"""
    def __init__(self):
        self.sentences = []
        self.interrupted = False
        self.generation_complete = True
        self.is_holding_floor = False
        self.is_speaking = False
        
    async def stream_sentence(self, sentence, is_first=False, is_last=False, current_voice_id=None):
        self.sentences.append({
            'text': sentence,
            'is_first': is_first,
            'is_last': is_last,
            'timestamp': datetime.now().isoformat()
        })
        print(f"    🔊 TTS: {sentence[:80]}{'...' if len(sentence) > 80 else ''}")
        return True
    
    def reset_interrupt_flag(self):
        self.interrupted = False
    
    async def clear_audio(self):
        self.interrupted = True
        self.sentences = []


class AgentDebugger:
    def __init__(self, agent_id: str, to_number: str = "+17708336397", custom_vars: dict = None):
        self.agent_id = agent_id
        self.to_number = to_number
        self.custom_vars = custom_vars or {}
        self.client = MongoClient(MONGO_URL)
        self.db = self.client['test_database']
        self.agent_config = None
        self.session = None
        self.mock_tts = MockTTSSession()
        self.conversation_log = []
        self.node_history = []
        
    def load_agent(self) -> bool:
        """Load agent configuration from MongoDB"""
        try:
            # Try as ObjectId first
            try:
                agent = self.db['agents'].find_one({'_id': ObjectId(self.agent_id)})
            except:
                agent = self.db['agents'].find_one({'_id': self.agent_id})
            
            if not agent:
                print(f"❌ Agent not found: {self.agent_id}")
                return False
            
            self.agent_config = agent
            print(f"✅ Loaded agent: {agent.get('name', 'Unknown')}")
            print(f"   Model: {agent.get('model', 'Unknown')}")
            # Support both schema formats
            nodes = []
            if 'call_flow' in agent:
                nodes = agent['call_flow']
            elif 'flow' in agent and 'nodes' in agent['flow']:
                nodes = agent['flow']['nodes']
                
            self.agent_config = agent
            print(f"✅ Loaded agent: {agent.get('name', 'Unknown')}")
            print(f"   Model: {agent.get('model', 'Unknown')}")
            print(f"   Flow nodes: {len(nodes)}")
            return True
        except Exception as e:
            print(f"❌ Error loading agent: {e}")
            return False
    
    def get_node_by_label(self, label: str) -> Optional[Dict]:
        """Find a node by its label"""
        nodes = []
        if 'call_flow' in self.agent_config:
            nodes = self.agent_config['call_flow']
        elif 'flow' in self.agent_config:
            nodes = self.agent_config.get('flow', {}).get('nodes', [])
            
        for node in nodes:
            # Check data.label first, then top-level label
            l = node.get('data', {}).get('label') or node.get('label')
            if l == label:
                return node
        return None
    
    def print_node_details(self, label: str):
        """Print detailed information about a specific node"""
        node = self.get_node_by_label(label)
        if not node:
            print(f"❌ Node not found: {label}")
            print("   Available labels:")
            nodes = []
            if 'call_flow' in self.agent_config:
                nodes = self.agent_config['call_flow']
            elif 'flow' in self.agent_config:
                nodes = self.agent_config.get('flow', {}).get('nodes', [])
                
            for n in nodes:
                l = n.get('data', {}).get('label')
                if l:
                    print(f"   - {l}")
            return
        
        data = node.get('data', {})
        print(f"\n{'='*60}")
        print(f"📋 NODE: {label}")
        print(f"{'='*60}")
        print(f"   Type: {data.get('type', 'Unknown')}")
        print(f"   Mode: {data.get('mode', 'Unknown')}")
        
        # Content/Script
        content = data.get('content', '') or data.get('script', '')
        if content:
            print(f"\n   📝 CONTENT/SCRIPT ({len(content)} chars):")
            print(f"   {'-'*50}")
            # Show first 500 chars
            preview = content[:500]
            for line in preview.split('\n')[:10]:
                print(f"   {line[:100]}")
            if len(content) > 500:
                print(f"   ... ({len(content) - 500} more chars)")
        
        # Transitions
        transitions = data.get('transitions', [])
        if transitions:
            print(f"\n   🔀 TRANSITIONS ({len(transitions)}):")
            for i, t in enumerate(transitions):
                target = t.get('target', 'Unknown')
                condition = t.get('condition', '')[:100] if t.get('condition') else 'No condition'
                print(f"   {i+1}. → {target}")
                print(f"      Condition: {condition}...")
        
        print(f"{'='*60}\n")
    
    async def initialize_session(self):
        """Initialize a mock call session"""
        from calling_service import CallSession
        
        # BRIDGE: Async wrapper for SYNC database lookup
        # This solves the "await dict" error because pymongo is sync but CallSession expects async
        async def mock_get_api_key(key_name: str) -> Optional[str]:
            try:
                from key_encryption import decrypt_api_key
                # Sync DB lookup
                user_id = self.agent_config.get("user_id")
                key_doc = self.db.api_keys.find_one({
                    "user_id": user_id,
                    "service_name": key_name,
                    "is_active": True
                })
                if key_doc and "api_key" in key_doc:
                    return decrypt_api_key(key_doc["api_key"])
            except Exception as e:
                print(f"❌ MockKey Error: {e}")
            return None
        
        # Create session
        # Create session with correct signature
        self.session = CallSession(
            call_id=f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            agent_config=self.agent_config,
            agent_id=self.agent_id,
            db=self.db
        )
        self.session.get_api_key = mock_get_api_key
        
        # Inject phone numbers and custom variables
        self.session.session_variables['from_number'] = "+18885550123"
        self.session.session_variables['to_number'] = self.to_number
        
        if self.custom_vars:
            print(f"💉 Injecting custom variables: {self.custom_vars}")
            self.session.session_variables.update(self.custom_vars)
            
        print("✅ Session initialized")
        return True
    
    async def simulate_turn(self, user_input: str, turn_number: int):
        """Simulate a single conversation turn"""
        print(f"\n{'='*60}")
        print(f"🎤 TURN {turn_number}: User says: \"{user_input}\"")
        print(f"{'='*60}")
        
        self.conversation_log.append({
            'turn': turn_number,
            'role': 'user',
            'text': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # Capture TTS callback
        async def stream_callback(sentence):
            await self.mock_tts.stream_sentence(sentence)
        
        try:
            # Process the input
            response = await self.session.process_user_input(
                user_input,
                stream_callback=stream_callback
            )
            
            response_text = response.get('text', '')
            node_id = response.get('node_id', '')
            node_label = response.get('node_label', 'Unknown')
            
            self.node_history.append({
                'turn': turn_number,
                'node_label': node_label,
                'node_id': node_id
            })
            
            self.conversation_log.append({
                'turn': turn_number,
                'role': 'assistant',
                'text': response_text,
                'node_label': node_label,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"\n   📍 NODE: {node_label}")
            print(f"   🤖 RESPONSE: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
            
            return response
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_interactive(self):
        """Run interactive debugging session"""
        print("\n" + "="*60)
        print("🎮 INTERACTIVE DEBUG MODE")
        print("="*60)
        print("Commands:")
        print("  [text]     - Send user message")
        print("  /node [x]  - Show details of node X")
        print("  /history   - Show conversation history")
        print("  /nodes     - Show node transition history")
        print("  /quit      - Exit")
        print("="*60 + "\n")
        
        turn = 1
        while True:
            try:
                user_input = input(f"\n[Turn {turn}] You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith('/node '):
                    node_label = user_input[6:].strip()
                    self.print_node_details(node_label)
                    continue
                
                if user_input == '/history':
                    print("\n📜 CONVERSATION HISTORY:")
                    for entry in self.conversation_log:
                        role = "🎤 User" if entry['role'] == 'user' else "🤖 Agent"
                        print(f"  {role}: {entry['text'][:100]}...")
                    continue
                
                if user_input == '/nodes':
                    print("\n📍 NODE HISTORY:")
                    for entry in self.node_history:
                        print(f"  Turn {entry['turn']}: {entry['node_label']}")
                    continue
                
                if user_input == '/quit':
                    break
                
                await self.simulate_turn(user_input, turn)
                turn += 1
                
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break
            except EOFError:
                break
    
    async def run_script(self, script_lines: List[str]):
        """Run a scripted conversation"""
        print("\n" + "="*60)
        print("📜 RUNNING SCRIPTED CONVERSATION")
        print("="*60 + "\n")
        
        for turn, line in enumerate(script_lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            await self.simulate_turn(line, turn)
            await asyncio.sleep(0.5)  # Small delay between turns
        
        print("\n" + "="*60)
        print("📊 SCRIPT COMPLETE - NODE HISTORY:")
        print("="*60)
        for entry in self.node_history:
            print(f"  Turn {entry['turn']}: {entry['node_label']}")


async def main():
    parser = argparse.ArgumentParser(description='Debug agent node behavior')
    parser.add_argument('--agent-id', required=True, help='Agent ID from MongoDB')
    parser.add_argument('--script', help='Path to script file with user lines')
    parser.add_argument('--show-node', help='Show details of a specific node and exit')
    
    parser.add_argument('--to-number', default="+17708336397", help='To phone number')
    parser.add_argument('--vars', help='JSON string of custom variables')
    
    args = parser.parse_args()
    
    custom_vars = {}
    if args.vars:
        try:
            custom_vars = json.loads(args.vars)
        except Exception as e:
            print(f"❌ Error parsing --vars: {e}")
            return

    debugger = AgentDebugger(args.agent_id, to_number=args.to_number, custom_vars=custom_vars)
    
    if not debugger.load_agent():
        return
    
    if args.show_node:
        debugger.print_node_details(args.show_node)
        return
    
    if not await debugger.initialize_session():
        return
    
    if args.script:
        with open(args.script, 'r') as f:
            script_lines = f.readlines()
        await debugger.run_script(script_lines)
    else:
        await debugger.run_interactive()


if __name__ == '__main__':
    asyncio.run(main())
