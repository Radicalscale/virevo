import re
from datetime import datetime

log_file = "logs_new.log"

# Parse all timing entries
timing_entries = []
with open(log_file, 'r') as f:
    for line in f:
        if '[TIMING]' in line:
            timing_entries.append(line)

# Extract E2E summaries
print("=" * 80)
print("E2E LATENCY ANALYSIS")
print("=" * 80)

conversations = []
current_conv = {}

for line in timing_entries:
    if 'USER_INPUT:' in line:
        match = re.search(r"USER_INPUT: '([^']*)'", line)
        if match:
            current_conv['user_input'] = match.group(1).strip()
    
    elif 'E2E_TOTAL:' in line:
        match = re.search(r'E2E_TOTAL: (\d+)ms', line)
        if match:
            current_conv['e2e_total'] = int(match.group(1))
    
    elif 'LLM_TOTAL:' in line and 'E2E' not in line:
        match = re.search(r'LLM_TOTAL: (\d+)ms', line)
        if match:
            current_conv['llm_total'] = int(match.group(1))
    
    elif 'TTS_TOTAL:' in line:
        match = re.search(r'TTS_TOTAL: (\d+)ms', line)
        if match:
            current_conv['tts_total'] = int(match.group(1))
    
    elif 'STT:' in line and 'E2E' not in line:
        match = re.search(r'STT: (\d+)ms', line)
        if match:
            current_conv['stt'] = int(match.group(1))
    
    elif 'REAL USER LATENCY:' in line:
        match = re.search(r'REAL USER LATENCY: (\d+)ms', line)
        if match:
            current_conv['real_latency'] = int(match.group(1))
            conversations.append(current_conv.copy())
            current_conv = {}

# Analyze transition timings
print("\nTRANSITION EVALUATION TIMINGS:")
print("-" * 80)
for line in timing_entries:
    if 'TRANSITION_EVAL:' in line:
        match = re.search(r'TRANSITION_EVAL: (\d+)ms', line)
        if match:
            ms = int(match.group(1))
            status = "✅ CACHED" if ms == 0 else f"⏱️  {ms}ms"
            # Find the user input from previous lines
            print(f"  {status}")

print("\n" + "=" * 80)
print("CONVERSATION TURN ANALYSIS")
print("=" * 80)

for i, conv in enumerate(conversations, 1):
    print(f"\nTurn #{i}:")
    print(f"  User Input: '{conv.get('user_input', 'N/A')}'")
    print(f"  STT:        {conv.get('stt', 'N/A')}ms")
    print(f"  LLM:        {conv.get('llm_total', 'N/A')}ms")
    print(f"  TTS:        {conv.get('tts_total', 'N/A')}ms")
    print(f"  E2E Total:  {conv.get('e2e_total', 'N/A')}ms")
    print(f"  Real User:  {conv.get('real_latency', 'N/A')}ms (~{conv.get('real_latency', 0)/1000:.1f}s)")

# Calculate statistics
if conversations:
    e2e_values = [c['e2e_total'] for c in conversations if 'e2e_total' in c]
    real_values = [c['real_latency'] for c in conversations if 'real_latency' in c]
    
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total Turns: {len(conversations)}")
    if e2e_values:
        print(f"E2E Latency:  Min={min(e2e_values)}ms, Max={max(e2e_values)}ms, Avg={sum(e2e_values)//len(e2e_values)}ms")
    if real_values:
        print(f"Real Latency: Min={min(real_values)}ms, Max={max(real_values)}ms, Avg={sum(real_values)//len(real_values)}ms")
        print(f"Real Latency (seconds): Min={min(real_values)/1000:.2f}s, Max={max(real_values)/1000:.2f}s, Avg={sum(real_values)/len(real_values)/1000:.2f}s")

