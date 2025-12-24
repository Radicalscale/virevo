import json
import re

CALL_FILE = "call_v3_KBe6.json"
AGENT_FILE = "agent_bbeda2.json"

def load_dirty_json(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
        # Find the first '{'
        start = content.find('{')
        end = content.rfind('}')
        if start == -1 or end == -1:
            raise ValueError(f"No JSON found in {filepath}")
        return json.loads(content[start:end+1])

def analyze():
    print("📉 Loading data...")
    call_data = load_dirty_json(CALL_FILE)
    agent_data = load_dirty_json(AGENT_FILE)
    
    # Map Agent Nodes for easy lookup
    nodes = {n['id']: n for n in agent_data.get('call_flow', [])}
    
    print("\n🧐 Analyzing Turns...")
    logs = call_data.get('logs', [])
    turn_events = [l for l in logs if l.get('type') == 'turn_complete']
    
    if not turn_events:
        print("⚠️ No turn_complete logs found! Falling back to raw transcript...")
        transcript = call_data.get('db_record', {}).get('transcript', []) or call_data.get('transcript', [])
        for t in transcript:
            print(f"[{t.get('role')}] {t.get('text')}")
        return

    deviations = []
    
    for i, turn in enumerate(turn_events):
        node_id = turn.get('node_id')
        agent_text = turn.get('agent_text', "").strip()
        user_text = turn.get('user_text', "").strip()
        node_label = turn.get('node_label', "Unknown")
        
        # Get Node Config
        node_config = nodes.get(node_id)
        if not node_config:
            print(f"⚠️  Turn {i}: Node ID {node_id} not found in agent config.")
            continue
            
        node_data = node_config.get('data', {})
        mode = node_data.get('mode') or node_data.get('promptType')
        expected_content = node_data.get('content', "").strip()
        
        print(f"Turn {i} | Node: {node_label} ({mode})")
        print(f"  User: {user_text}")
        print(f"  Agent: {agent_text[:50]}...")
        
        if True: # Print everything
            print(f"  User: {user_text}")
            print(f"  Agent: {agent_text}")
            print("-" * 40)

    print(f"\nFound {len(deviations)} deviations.")

if __name__ == "__main__":
    analyze()
