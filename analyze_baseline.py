#!/usr/bin/env python3
"""
Analyze baseline test results to identify optimization targets
"""
import json

# Load baseline results
with open('/app/webhook_latency_test_20251124_134637.json', 'r') as f:
    data = json.load(f)

print("="*80)
print("BASELINE ANALYSIS - Optimization Target Identification")
print("="*80)
print()

# Overall stats
stats = data['overall_stats']
print(f"📊 Overall Performance:")
print(f"   Average Latency: {stats['avg_latency_ms']:.0f}ms")
print(f"   Target: {stats['target_latency_ms']}ms")
print(f"   Gap: {stats['avg_latency_ms'] - stats['target_latency_ms']:.0f}ms ({((stats['avg_latency_ms'] - stats['target_latency_ms'])/stats['target_latency_ms'])*100:.1f}% over)")
print()

# Aggregate by node
node_stats = {}
for conv in data['conversations']:
    for msg in conv['messages']:
        node = msg.get('current_node', 'Unknown')
        llm_time = msg.get('llm_ms', 0)
        tts_time = msg.get('tts_ms', 0)
        total_time = msg.get('latency_ms', 0)
        response_len = msg.get('response_length', 0)
        
        if node not in node_stats:
            node_stats[node] = {
                'calls': 0,
                'llm_times': [],
                'tts_times': [],
                'total_times': [],
                'response_lengths': []
            }
        
        node_stats[node]['calls'] += 1
        node_stats[node]['llm_times'].append(llm_time)
        node_stats[node]['tts_times'].append(tts_time)
        node_stats[node]['total_times'].append(total_time)
        node_stats[node]['response_lengths'].append(response_len)

# Calculate averages and weighted impact
node_analysis = []
for node, stats_data in node_stats.items():
    avg_llm = sum(stats_data['llm_times']) / len(stats_data['llm_times'])
    avg_tts = sum(stats_data['tts_times']) / len(stats_data['tts_times'])
    avg_total = sum(stats_data['total_times']) / len(stats_data['total_times'])
    avg_response_len = sum(stats_data['response_lengths']) / len(stats_data['response_lengths'])
    calls = stats_data['calls']
    
    # Weighted impact: how much this node contributes to total latency
    weighted_impact = avg_total * calls
    
    node_analysis.append({
        'node': node,
        'calls': calls,
        'avg_llm': avg_llm,
        'avg_tts': avg_tts,
        'avg_total': avg_total,
        'avg_response_len': avg_response_len,
        'weighted_impact': weighted_impact
    })

# Sort by weighted impact
node_analysis.sort(key=lambda x: x['weighted_impact'], reverse=True)

print("🔥 TOP 10 HIGHEST IMPACT NODES (by weighted impact):")
print()
for i, node_data in enumerate(node_analysis[:10], 1):
    node = node_data['node']
    calls = node_data['calls']
    avg_llm = node_data['avg_llm']
    avg_tts = node_data['avg_tts']
    avg_total = node_data['avg_total']
    avg_response_len = node_data['avg_response_len']
    weighted_impact = node_data['weighted_impact']
    
    print(f"{i}. Node: {node}")
    print(f"   Calls: {calls}x")
    print(f"   Avg Total: {avg_total:.0f}ms")
    print(f"   Avg LLM: {avg_llm:.0f}ms | Avg TTS: {avg_tts:.0f}ms")
    print(f"   Avg Response Length: {avg_response_len:.0f} chars")
    print(f"   Weighted Impact: {weighted_impact:.0f}")
    
    # Provide optimization suggestion
    if avg_llm > 1500:
        print(f"   🎯 CRITICAL - Very high LLM time")
    elif avg_llm > 1000:
        print(f"   🔴 HIGH PRIORITY - High LLM time")
    elif avg_llm > 700:
        print(f"   🟡 MEDIUM - Above average LLM")
    
    if avg_tts > 1000:
        print(f"   🔴 HIGH PRIORITY - High TTS time (shorten response)")
    elif avg_tts > 600:
        print(f"   🟡 MEDIUM - Above average TTS")
    
    print()

print("="*80)
print("📋 OPTIMIZATION RECOMMENDATIONS:")
print("="*80)
print()

# Calculate potential savings
print("💡 If we optimize the TOP 5 nodes by 30%:")
print()
total_current_latency = sum([msg['latency_ms'] for conv in data['conversations'] for msg in conv['messages']])
total_messages = len([msg for conv in data['conversations'] for msg in conv['messages']])

top_5_nodes = [n['node'] for n in node_analysis[:5]]

# Simulate 30% reduction in LLM time for top 5 nodes
new_latencies = []
for conv in data['conversations']:
    for msg in conv['messages']:
        node = msg.get('current_node')
        llm_time = msg.get('llm_ms', 0)
        tts_time = msg.get('tts_ms', 0)
        
        # Apply 30% LLM reduction if in top 5
        if node in top_5_nodes:
            llm_time = llm_time * 0.70
        
        new_latencies.append(llm_time + tts_time)

current_avg = stats['avg_latency_ms']
projected_avg_llm_only = sum(new_latencies) / len(new_latencies)
improvement_llm_only = current_avg - projected_avg_llm_only

print(f"   LLM Optimization Only (30% reduction on top 5 nodes):")
print(f"   Current: {current_avg:.0f}ms → Projected: {projected_avg_llm_only:.0f}ms")
print(f"   Improvement: {improvement_llm_only:.0f}ms ({(improvement_llm_only/current_avg)*100:.1f}%)")
print()

# Simulate response length reduction (affects TTS)
new_latencies_with_tts = []
for conv in data['conversations']:
    for msg in conv['messages']:
        node = msg.get('current_node')
        llm_time = msg.get('llm_ms', 0)
        tts_time = msg.get('tts_ms', 0)
        response_len = msg.get('response_length', 0)
        
        # Apply 30% LLM reduction if in top 5
        if node in top_5_nodes:
            llm_time = llm_time * 0.70
        
        # Apply 25% TTS reduction (from response shortening)
        tts_time = tts_time * 0.75
        
        new_latencies_with_tts.append(llm_time + tts_time)

projected_avg_both = sum(new_latencies_with_tts) / len(new_latencies_with_tts)
improvement_both = current_avg - projected_avg_both

print(f"   LLM + Response Shortening (30% LLM + 25% response length):")
print(f"   Current: {current_avg:.0f}ms → Projected: {projected_avg_both:.0f}ms")
print(f"   Improvement: {improvement_both:.0f}ms ({(improvement_both/current_avg)*100:.1f}%)")
print()

if projected_avg_both <= stats['target_latency_ms']:
    print(f"   ✅ This would meet the target! ({stats['target_latency_ms'] - projected_avg_both:.0f}ms under)")
else:
    print(f"   ⚠️ Would still be {projected_avg_both - stats['target_latency_ms']:.0f}ms over target")
    print(f"   Need {((projected_avg_both - stats['target_latency_ms'])/projected_avg_both)*100:.1f}% more reduction")

print()
print("="*80)
print("🎯 RECOMMENDED OPTIMIZATION STRATEGY:")
print("="*80)
print()
print("Phase 1: Content Optimization (Highest Impact)")
print("  1. Reduce system prompt by 25-30% (sent with every call)")
print("  2. Optimize top 5 nodes by 30%")
print("  3. Shorten all responses by 25% (reduces TTS time)")
print()
print("Phase 2: Infrastructure Experiments")
print("  - Try caching strategies")
print("  - Optimize API parameters")
print("  - Parallel processing where safe")
print()
print("Expected outcome: Should get to or near 1500ms target")
print()
