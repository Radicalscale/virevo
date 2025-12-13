import re

log_file = "logs_phase1.log"

# Parse all timing entries
with open(log_file, 'r') as f:
    log_content = f.read()

# Find all E2E summaries with new metrics
print("=" * 80)
print("PHASE 1 ANALYSIS: NEW TIMING METRICS")
print("=" * 80)

# Extract conversations with new metrics
conversations = []
current_conv = {}

for line in log_content.split('\n'):
    if '[TIMING]' in line:
        if 'USER_INPUT:' in line:
            match = re.search(r"USER_INPUT: '([^']*)'", line)
            if match:
                current_conv['user_input'] = match.group(1).strip()
        
        elif 'TTFS (Time To First Sentence):' in line:
            match = re.search(r'TTFS.*?: (\d+)ms', line)
            if match:
                current_conv['ttfs'] = int(match.group(1))
        
        elif 'TTFT_TTS (First TTS Task Started):' in line:
            match = re.search(r'TTFT_TTS.*?: (\d+)ms', line)
            if match:
                current_conv['ttft_tts'] = int(match.group(1))
        
        elif 'TTFA (Time To First Audio' in line:
            match = re.search(r'TTFA.*?: (\d+)ms', line)
            if match:
                current_conv['ttfa'] = int(match.group(1))
        
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
        
        elif 'REAL USER LATENCY:' in line:
            match = re.search(r'REAL USER LATENCY: (\d+)ms', line)
            if match:
                current_conv['real_latency'] = int(match.group(1))
                conversations.append(current_conv.copy())
                current_conv = {}

print(f"\nFound {len(conversations)} conversation turns\n")

for i, conv in enumerate(conversations, 1):
    print(f"{'=' * 80}")
    print(f"TURN #{i}")
    print(f"{'=' * 80}")
    print(f"User Input:     '{conv.get('user_input', 'N/A')}'")
    print()
    print(f"🔹 NEW METRICS:")
    print(f"  TTFS:         {conv.get('ttfs', 'N/A')}ms   (Time to First Sentence from LLM)")
    print(f"  TTFT_TTS:     {conv.get('ttft_tts', 'N/A')}ms   (First TTS Task Started)")
    print(f"  TTFA:         {conv.get('ttfa', 'N/A')}ms   (Time to First Audio) ⭐ KEY METRIC")
    print()
    print(f"🔹 EXISTING METRICS:")
    print(f"  LLM_TOTAL:    {conv.get('llm_total', 'N/A')}ms")
    print(f"  TTS_TOTAL:    {conv.get('tts_total', 'N/A')}ms")
    print(f"  E2E_TOTAL:    {conv.get('e2e_total', 'N/A')}ms")
    print(f"  Real Latency: {conv.get('real_latency', 'N/A')}ms (~{conv.get('real_latency', 0)/1000:.1f}s)")
    print()
    
    # Analysis
    ttfs = conv.get('ttfs')
    ttft_tts = conv.get('ttft_tts')
    ttfa = conv.get('ttfa')
    llm_total = conv.get('llm_total')
    
    print(f"🔍 ANALYSIS:")
    if ttfs:
        if ttfs < 500:
            print(f"  ✅ TTFS is EXCELLENT ({ttfs}ms) - first sentence arrives quickly")
        elif ttfs < 1000:
            print(f"  ✅ TTFS is GOOD ({ttfs}ms) - streaming working")
        elif ttfs < 2000:
            print(f"  ⚠️  TTFS is SLOW ({ttfs}ms) - LLM may be slow")
        else:
            print(f"  ❌ TTFS is TOO SLOW ({ttfs}ms) - LLM not streaming properly")
    
    if ttft_tts and ttfs:
        delay = ttft_tts - ttfs
        if delay < 100:
            print(f"  ✅ TTS starts immediately ({delay}ms after first sentence)")
        else:
            print(f"  ⚠️  TTS start delayed ({delay}ms after first sentence)")
    
    if ttfa:
        if ttfa < 1500:
            print(f"  ✅ TTFA is EXCELLENT ({ttfa}ms) - user hears response quickly")
        elif ttfa < 2500:
            print(f"  ⚠️  TTFA is OK ({ttfa}ms) - could be faster")
        else:
            print(f"  ❌ TTFA is TOO SLOW ({ttfa}ms) - optimization needed")
    else:
        print(f"  ⚠️  TTFA not measured (persistent TTS not used)")
    
    # Check if parallel
    if llm_total and ttfs:
        if ttfs < llm_total * 0.5:
            print(f"  ✅ STREAMING CONFIRMED: First sentence at {ttfs}ms (full LLM: {llm_total}ms)")
        else:
            print(f"  ⚠️  STREAMING QUESTIONABLE: First sentence at {ttfs}ms (full LLM: {llm_total}ms)")
    
    print()

# Overall statistics
if conversations:
    ttfs_values = [c['ttfs'] for c in conversations if 'ttfs' in c]
    
    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total Turns: {len(conversations)}")
    if ttfs_values:
        print(f"\nTTFS (Time To First Sentence):")
        print(f"  Min: {min(ttfs_values)}ms")
        print(f"  Max: {max(ttfs_values)}ms")
        print(f"  Avg: {sum(ttfs_values)//len(ttfs_values)}ms")
        
        if max(ttfs_values) > 3000:
            print(f"\n⚠️  WARNING: Turn with {max(ttfs_values)}ms TTFS detected!")
            print(f"  This is unusually high. Check that turn for issues.")

