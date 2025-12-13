"""
Automated Latency Optimizer for JK First Caller Agent
Systematically optimizes prompts and transitions to achieve 1.5s target latency
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import json
import httpx
from typing import Dict, List, Any

# Configuration
AGENT_ID = "f251b2d9-aa56-4872-ac66-9a28accd42bb"
TARGET_LATENCY = 1.5  # seconds
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8001')


class LatencyOptimizer:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.target_latency = TARGET_LATENCY
        self.iteration_count = 0
        self.optimization_log = []
        
    async def load_agent(self):
        """Load agent from MongoDB"""
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client['test_database']
        
        agent = await db.agents.find_one({"id": self.agent_id})
        if not agent:
            raise Exception(f"Agent {self.agent_id} not found")
        
        agent.pop('_id', None)
        return agent
    
    async def analyze_agent(self, agent: Dict) -> Dict[str, Any]:
        """Analyze agent structure for optimization opportunities"""
        system_prompt = agent.get('system_prompt', '')
        call_flow = agent.get('call_flow', [])
        
        # Count optimization opportunities
        nodes_to_optimize = []
        transitions_to_optimize = []
        
        for node in call_flow:
            node_data = node.get('data', {})
            content = node_data.get('content', '')
            
            # Check if node content is long (good optimization candidate)
            if len(content) > 200:  # Longer prompts = more LLM processing time
                nodes_to_optimize.append({
                    'id': node.get('id'),
                    'label': node.get('label', 'Unknown'),
                    'content_length': len(content),
                    'mode': node_data.get('mode', 'unknown')
                })
            
            # Check transitions
            transitions = node_data.get('transitions', [])
            for trans in transitions:
                condition = trans.get('condition', '')
                if len(condition) > 100:  # Long condition = slow transition eval
                    transitions_to_optimize.append({
                        'node_id': node.get('id'),
                        'node_label': node.get('label', 'Unknown'),
                        'transition_id': trans.get('id'),
                        'condition': condition,
                        'condition_length': len(condition)
                    })
        
        analysis = {
            'system_prompt_length': len(system_prompt),
            'total_nodes': len(call_flow),
            'nodes_to_optimize': sorted(nodes_to_optimize, key=lambda x: x['content_length'], reverse=True),
            'transitions_to_optimize': sorted(transitions_to_optimize, key=lambda x: x['condition_length'], reverse=True),
            'total_optimization_targets': len(nodes_to_optimize) + len(transitions_to_optimize)
        }
        
        return analysis
    
    async def optimize_system_prompt(self, agent: Dict) -> str:
        """Optimize the system prompt"""
        system_prompt = agent.get('system_prompt', '')
        
        print(f"\n🎯 Optimizing system prompt ({len(system_prompt)} chars)...")
        
        # Call the optimizer API
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{BACKEND_URL}/api/agents/{self.agent_id}/optimize-system-prompt",
                    json={
                        "original_prompt": system_prompt,
                        "optimization_model": "grok-4-0709"
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized = result.get('optimized_prompt', '')
                    print(f"✅ System prompt optimized: {len(system_prompt)} → {len(optimized)} chars (-{len(system_prompt) - len(optimized)} chars)")
                    return optimized
                else:
                    print(f"❌ Optimization failed: {response.status_code}")
                    return system_prompt
                    
            except Exception as e:
                print(f"❌ Error optimizing system prompt: {e}")
                return system_prompt
    
    async def optimize_node(self, node: Dict) -> Dict:
        """Optimize a single node's content"""
        node_id = node.get('id')
        node_label = node.get('label', 'Unknown')
        node_data = node.get('data', {})
        content = node_data.get('content', '')
        
        if not content or len(content) < 100:
            return node
        
        print(f"\n📝 Optimizing node: {node_label} ({len(content)} chars)...")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{BACKEND_URL}/api/agents/{self.agent_id}/optimize-node",
                    json={
                        "node_id": node_id,
                        "original_content": content,
                        "optimization_model": "grok-4-0709"
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized = result.get('optimized_content', '')
                    
                    if optimized and len(optimized) < len(content):
                        print(f"✅ Node optimized: {len(content)} → {len(optimized)} chars (-{len(content) - len(optimized)} chars)")
                        node_data['content'] = optimized
                        node['data'] = node_data
                    else:
                        print(f"⚠️ No improvement, keeping original")
                        
            except Exception as e:
                print(f"❌ Error optimizing node {node_label}: {e}")
        
        return node
    
    async def optimize_transition(self, node: Dict, transition_index: int) -> Dict:
        """Optimize a single transition condition"""
        node_label = node.get('label', 'Unknown')
        node_data = node.get('data', {})
        transitions = node_data.get('transitions', [])
        
        if transition_index >= len(transitions):
            return node
        
        transition = transitions[transition_index]
        condition = transition.get('condition', '')
        
        if not condition or len(condition) < 50:
            return node
        
        print(f"\n🔀 Optimizing transition in {node_label} ({len(condition)} chars)...")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{BACKEND_URL}/api/agents/{self.agent_id}/optimize-transition",
                    json={
                        "node_id": node.get('id'),
                        "transition_index": transition_index,
                        "original_condition": condition,
                        "optimization_model": "grok-4-0709"
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized = result.get('optimized_condition', '')
                    
                    if optimized and len(optimized) < len(condition):
                        print(f"✅ Transition optimized: {len(condition)} → {len(optimized)} chars (-{len(condition) - len(optimized)} chars)")
                        transition['condition'] = optimized
                        transitions[transition_index] = transition
                        node_data['transitions'] = transitions
                        node['data'] = node_data
                    else:
                        print(f"⚠️ No improvement, keeping original")
                        
            except Exception as e:
                print(f"❌ Error optimizing transition: {e}")
        
        return node
    
    async def save_agent(self, agent: Dict):
        """Save optimized agent back to MongoDB"""
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client['test_database']
        
        # Update agent
        result = await db.agents.update_one(
            {"id": self.agent_id},
            {"$set": agent}
        )
        
        if result.modified_count > 0:
            print(f"✅ Agent saved to database")
        else:
            print(f"⚠️ No changes saved (agent may be unchanged)")
    
    async def log_iteration(self, iteration_num: int, changes: List[str], metrics: Dict):
        """Log iteration results to LATENCY_ITERATIONS.md"""
        timestamp = datetime.now().isoformat()
        
        log_entry = f"""
## Iteration {iteration_num}: Automated Optimization Pass
**Date:** {timestamp}
**Agent:** JK First Caller-copy-copy ({self.agent_id})

### Changes Made:
"""
        for change in changes:
            log_entry += f"- {change}\n"
        
        log_entry += f"""
### Optimization Summary:
- **System Prompt:** {metrics.get('system_prompt_reduction', 0)} chars reduced
- **Nodes Optimized:** {metrics.get('nodes_optimized', 0)}
- **Transitions Optimized:** {metrics.get('transitions_optimized', 0)}
- **Total Character Reduction:** {metrics.get('total_char_reduction', 0)} chars

### Next Steps:
- Test the optimized agent with real calls
- Measure latency improvements
- Validate logic preservation

### Status: Optimization Complete, Ready for Testing

---

"""
        
        # Append to iterations file
        try:
            with open('/app/LATENCY_ITERATIONS.md', 'a') as f:
                f.write(log_entry)
            print(f"✅ Logged iteration {iteration_num} to LATENCY_ITERATIONS.md")
        except Exception as e:
            print(f"❌ Error logging iteration: {e}")
    
    async def run_optimization_pass(self, max_optimizations: int = 10):
        """Run a single optimization pass"""
        self.iteration_count += 1
        
        print(f"\n{'='*80}")
        print(f"🚀 ITERATION {self.iteration_count}: LATENCY OPTIMIZATION PASS")
        print(f"{'='*80}")
        
        # Load agent
        print(f"\n📥 Loading agent {self.agent_id}...")
        agent = await self.load_agent()
        
        # Analyze
        print(f"\n🔍 Analyzing agent structure...")
        analysis = await self.analyze_agent(agent)
        
        print(f"\n📊 Analysis Results:")
        print(f"   System Prompt: {analysis['system_prompt_length']} chars")
        print(f"   Total Nodes: {analysis['total_nodes']}")
        print(f"   Nodes to Optimize: {len(analysis['nodes_to_optimize'])}")
        print(f"   Transitions to Optimize: {len(analysis['transitions_to_optimize'])}")
        print(f"   Total Targets: {analysis['total_optimization_targets']}")
        
        changes = []
        metrics = {
            'system_prompt_reduction': 0,
            'nodes_optimized': 0,
            'transitions_optimized': 0,
            'total_char_reduction': 0
        }
        
        # Optimize system prompt first (biggest impact)
        original_prompt_len = len(agent.get('system_prompt', ''))
        optimized_prompt = await self.optimize_system_prompt(agent)
        if len(optimized_prompt) < original_prompt_len:
            agent['system_prompt'] = optimized_prompt
            reduction = original_prompt_len - len(optimized_prompt)
            metrics['system_prompt_reduction'] = reduction
            metrics['total_char_reduction'] += reduction
            changes.append(f"System prompt optimized: {original_prompt_len} → {len(optimized_prompt)} chars")
        
        # Optimize top priority nodes
        nodes_optimized = 0
        for i, node_info in enumerate(analysis['nodes_to_optimize'][:max_optimizations]):
            # Find the actual node in call_flow
            call_flow = agent.get('call_flow', [])
            for idx, node in enumerate(call_flow):
                if node.get('id') == node_info['id']:
                    original_len = len(node.get('data', {}).get('content', ''))
                    optimized_node = await self.optimize_node(node)
                    new_len = len(optimized_node.get('data', {}).get('content', ''))
                    
                    if new_len < original_len:
                        call_flow[idx] = optimized_node
                        agent['call_flow'] = call_flow
                        reduction = original_len - new_len
                        metrics['total_char_reduction'] += reduction
                        nodes_optimized += 1
                        changes.append(f"Node '{node_info['label']}': {original_len} → {new_len} chars")
                    break
        
        metrics['nodes_optimized'] = nodes_optimized
        
        # Optimize top priority transitions
        transitions_optimized = 0
        for trans_info in analysis['transitions_to_optimize'][:max_optimizations]:
            # Find the node and optimize transition
            call_flow = agent.get('call_flow', [])
            for idx, node in enumerate(call_flow):
                if node.get('id') == trans_info['node_id']:
                    transitions = node.get('data', {}).get('transitions', [])
                    for t_idx, t in enumerate(transitions):
                        if t.get('id') == trans_info['transition_id']:
                            original_len = len(t.get('condition', ''))
                            optimized_node = await self.optimize_transition(node, t_idx)
                            
                            new_transitions = optimized_node.get('data', {}).get('transitions', [])
                            if t_idx < len(new_transitions):
                                new_len = len(new_transitions[t_idx].get('condition', ''))
                                
                                if new_len < original_len:
                                    call_flow[idx] = optimized_node
                                    agent['call_flow'] = call_flow
                                    reduction = original_len - new_len
                                    metrics['total_char_reduction'] += reduction
                                    transitions_optimized += 1
                                    changes.append(f"Transition in '{trans_info['node_label']}': {original_len} → {new_len} chars")
                            break
                    break
        
        metrics['transitions_optimized'] = transitions_optimized
        
        # Save optimized agent
        if changes:
            print(f"\n💾 Saving optimized agent...")
            await self.save_agent(agent)
            
            # Log iteration
            await self.log_iteration(self.iteration_count, changes, metrics)
            
            print(f"\n✅ ITERATION {self.iteration_count} COMPLETE")
            print(f"   Total Reduction: {metrics['total_char_reduction']} chars")
            print(f"   Changes: {len(changes)} optimizations applied")
        else:
            print(f"\n⚠️ No optimizations applied in this iteration")
        
        return metrics


async def main():
    """Main optimization workflow"""
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  LATENCY OPTIMIZATION SYSTEM v1.0                            ║
║                  Target: 1.5s Average Latency                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    optimizer = LatencyOptimizer()
    
    print(f"🎯 Target Agent: JK First Caller-copy-copy")
    print(f"🎯 Agent ID: {AGENT_ID}")
    print(f"🎯 Target Latency: {TARGET_LATENCY}s")
    print(f"🎯 Optimization Strategy: Systematic prompt & transition optimization")
    
    # Run optimization pass
    try:
        metrics = await optimizer.run_optimization_pass(max_optimizations=10)
        
        print(f"\n{'='*80}")
        print(f"🎉 OPTIMIZATION PASS COMPLETE!")
        print(f"{'='*80}")
        print(f"\n📊 Summary:")
        print(f"   System Prompt Reduced: {metrics['system_prompt_reduction']} chars")
        print(f"   Nodes Optimized: {metrics['nodes_optimized']}")
        print(f"   Transitions Optimized: {metrics['transitions_optimized']}")
        print(f"   Total Character Reduction: {metrics['total_char_reduction']} chars")
        print(f"\n✅ Next: Test the optimized agent and measure latency improvements!")
        
    except Exception as e:
        print(f"\n❌ Error during optimization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
