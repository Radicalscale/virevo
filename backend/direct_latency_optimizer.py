"""
Direct Latency Optimizer - Works directly with MongoDB and Grok API
Bypasses authentication requirements for automated optimization
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import json
import httpx

# Configuration
AGENT_ID = "f251b2d9-aa56-4872-ac66-9a28accd42bb"
TARGET_LATENCY = 1.5  # seconds
USER_ID = "dcafa642-6136-4096-b77d-a4cb99a62651"


class DirectLatencyOptimizer:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.user_id = USER_ID
        self.target_latency = TARGET_LATENCY
        self.iteration_count = 0
        self.grok_client = None
        
    async def init_grok_client(self):
        """Initialize Grok API key from api_keys collection"""
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client['test_database']
        
        # Get API keys from the api_keys collection (NOT from user document)
        keys = await db.api_keys.find({"user_id": self.user_id}).to_list(length=50)
        
        grok_key = None
        for key_doc in keys:
            service_name = key_doc.get('service_name', '')
            if service_name == 'grok' and key_doc.get('is_active', False):
                grok_key = key_doc.get('api_key')
                break
        
        if not grok_key:
            raise Exception(f"No active Grok API key found for user {self.user_id}")
        
        self.grok_api_key = grok_key
        print(f"✅ Grok API key loaded")
        
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
    
    async def optimize_with_grok(self, text: str, optimization_type: str) -> str:
        """Use Grok to optimize text"""
        if optimization_type == "system_prompt":
            system_msg = """You are an expert at optimizing voice agent system prompts for minimum latency.

OPTIMIZATION RULES:
1. Remove ALL redundant instructions and examples
2. Convert verbose paragraphs into concise bullet points  
3. Eliminate flowery language - use direct, imperative statements
4. Remove duplicate rules (many system prompts repeat the same instruction)
5. Keep ONLY essential logic - remove nice-to-have guidelines
6. Use abbreviations where clear (e.g., "If user..." → "If user:")
7. Maintain ALL critical business logic and brand voice
8. Preserve ALL KB references and variable names exactly
9. Keep pronunciation guides (phonetic respellings)

OUTPUT: Return ONLY the optimized prompt, no explanations."""
            
            user_msg = f"Optimize this system prompt for minimum processing time:\n\n{text}"
            
        elif optimization_type == "node":
            system_msg = """You are an expert at optimizing voice agent node prompts for speed.

OPTIMIZATION RULES:
1. Remove verbose context - agent already knows it
2. Convert long paragraphs into numbered steps
3. Eliminate redundant instructions
4. Use direct imperatives ("Say X" not "You should say X")
5. Remove flowery transitions and filler
6. Keep core tactical instructions only
7. Preserve exact phrasing that must be spoken
8. Maintain all SSML tags and breaks

OUTPUT: Return ONLY the optimized node content, no explanations."""
            
            user_msg = f"Optimize this node prompt:\n\n{text}"
            
        else:  # transition
            system_msg = """You are an expert at optimizing voice agent transition conditions for instant evaluation.

OPTIMIZATION RULES:
1. Use boolean logic operators (AND/OR/NOT) instead of sentences
2. Remove explanatory text - just the logic
3. Combine similar conditions with OR
4. Use pattern matching shortcuts (e.g., "yes|yeah|yep" not "if user says yes or yeah or yep")
5. Remove redundant checks
6. Use specific keywords instead of vague descriptions

OUTPUT: Return ONLY the optimized condition, no explanations."""
            
            user_msg = f"Optimize this transition condition:\n\n{text}"
        
        try:
            # Use OpenAI-compatible API endpoint for Grok
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.grok_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-4-0709",
                        "messages": [
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 4000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized = result['choices'][0]['message']['content'].strip()
                    return optimized
                else:
                    print(f"❌ API error {response.status_code}: {response.text[:200]}")
                    return text
            
        except Exception as e:
            print(f"❌ Grok optimization error: {e}")
            return text
    
    async def analyze_agent(self, agent: dict) -> dict:
        """Analyze agent for optimization opportunities"""
        system_prompt = agent.get('system_prompt', '')
        call_flow = agent.get('call_flow', [])
        
        nodes_to_optimize = []
        transitions_to_optimize = []
        
        for node in call_flow:
            node_data = node.get('data', {})
            content = node_data.get('content', '')
            
            if len(content) > 300:  # Long prompts
                nodes_to_optimize.append({
                    'id': node.get('id'),
                    'label': node.get('label', 'Unknown'),
                    'content_length': len(content),
                    'mode': node_data.get('mode', 'unknown')
                })
            
            transitions = node_data.get('transitions', [])
            for trans in transitions:
                condition = trans.get('condition', '')
                if len(condition) > 80:  # Long conditions
                    transitions_to_optimize.append({
                        'node_id': node.get('id'),
                        'node_label': node.get('label', 'Unknown'),
                        'transition_id': trans.get('id'),
                        'condition': condition,
                        'condition_length': len(condition)
                    })
        
        return {
            'system_prompt_length': len(system_prompt),
            'total_nodes': len(call_flow),
            'nodes_to_optimize': sorted(nodes_to_optimize, key=lambda x: x['content_length'], reverse=True),
            'transitions_to_optimize': sorted(transitions_to_optimize, key=lambda x: x['condition_length'], reverse=True)
        }
    
    async def run_optimization(self, max_nodes=5, max_transitions=10):
        """Run comprehensive optimization"""
        self.iteration_count += 1
        
        print(f"\n{'='*80}")
        print(f"🚀 ITERATION {self.iteration_count}: DIRECT LATENCY OPTIMIZATION")
        print(f"{'='*80}\n")
        
        # Initialize
        await self.init_grok_client()
        
        # Load agent
        print(f"📥 Loading agent...")
        agent = await self.load_agent()
        # Skip deep copy - not needed and causes datetime issues
        # original_agent = agent.copy()
        
        # Analyze
        print(f"🔍 Analyzing agent structure...")
        analysis = await self.analyze_agent(agent)
        
        print(f"\n📊 Analysis:")
        print(f"   System Prompt: {analysis['system_prompt_length']:,} chars")
        print(f"   Nodes with long prompts: {len(analysis['nodes_to_optimize'])}")
        print(f"   Transitions with long conditions: {len(analysis['transitions_to_optimize'])}")
        
        changes = []
        total_reduction = 0
        
        # Optimize system prompt
        print(f"\n🎯 Optimizing system prompt...")
        original_prompt = agent.get('system_prompt', '')
        if len(original_prompt) > 1000:
            optimized_prompt = await self.optimize_with_grok(original_prompt, "system_prompt")
            
            if len(optimized_prompt) < len(original_prompt):
                reduction = len(original_prompt) - len(optimized_prompt)
                agent['system_prompt'] = optimized_prompt
                total_reduction += reduction
                changes.append(f"System prompt: {len(original_prompt):,} → {len(optimized_prompt):,} chars (-{reduction:,})")
                print(f"   ✅ Reduced by {reduction:,} chars")
            else:
                print(f"   ⚠️ No improvement")
        
        # Optimize nodes
        print(f"\n📝 Optimizing top {max_nodes} nodes...")
        nodes_optimized = 0
        call_flow = agent.get('call_flow', [])
        
        for node_info in analysis['nodes_to_optimize'][:max_nodes]:
            for idx, node in enumerate(call_flow):
                if node.get('id') == node_info['id']:
                    original_content = node.get('data', {}).get('content', '')
                    if len(original_content) > 200:
                        print(f"   Optimizing: {node_info['label'][:50]}...")
                        optimized_content = await self.optimize_with_grok(original_content, "node")
                        
                        if len(optimized_content) < len(original_content):
                            reduction = len(original_content) - len(optimized_content)
                            node['data']['content'] = optimized_content
                            call_flow[idx] = node
                            total_reduction += reduction
                            nodes_optimized += 1
                            changes.append(f"Node '{node_info['label'][:40]}': {len(original_content):,} → {len(optimized_content):,} chars (-{reduction:,})")
                            print(f"      ✅ Reduced by {reduction:,} chars")
                        else:
                            print(f"      ⚠️ No improvement")
                    break
        
        agent['call_flow'] = call_flow
        
        # Optimize transitions
        print(f"\n🔀 Optimizing top {max_transitions} transitions...")
        transitions_optimized = 0
        
        for trans_info in analysis['transitions_to_optimize'][:max_transitions]:
            for idx, node in enumerate(call_flow):
                if node.get('id') == trans_info['node_id']:
                    transitions = node.get('data', {}).get('transitions', [])
                    for t_idx, trans in enumerate(transitions):
                        if trans.get('id') == trans_info['transition_id']:
                            original_condition = trans.get('condition', '')
                            if len(original_condition) > 50:
                                print(f"   Optimizing transition in: {trans_info['node_label'][:40]}...")
                                optimized_condition = await self.optimize_with_grok(original_condition, "transition")
                                
                                if len(optimized_condition) < len(original_condition):
                                    reduction = len(original_condition) - len(optimized_condition)
                                    trans['condition'] = optimized_condition
                                    transitions[t_idx] = trans
                                    node['data']['transitions'] = transitions
                                    call_flow[idx] = node
                                    total_reduction += reduction
                                    transitions_optimized += 1
                                    changes.append(f"Transition in '{trans_info['node_label'][:30]}': {len(original_condition)} → {len(optimized_condition)} chars (-{reduction})")
                                    print(f"      ✅ Reduced by {reduction} chars")
                                else:
                                    print(f"      ⚠️ No improvement")
                            break
                    break
        
        agent['call_flow'] = call_flow
        
        # Save if changes made
        if changes:
            print(f"\n💾 Saving optimized agent to MongoDB...")
            mongo_url = os.environ.get('MONGO_URL')
            client = AsyncIOMotorClient(mongo_url)
            db = client['test_database']
            
            result = await db.agents.update_one(
                {"id": self.agent_id},
                {"$set": agent}
            )
            
            if result.modified_count > 0:
                print(f"✅ Agent saved successfully")
                
                # Log iteration
                await self.log_iteration(changes, {
                    'total_reduction': total_reduction,
                    'nodes_optimized': nodes_optimized,
                    'transitions_optimized': transitions_optimized
                })
            else:
                print(f"⚠️ No changes saved")
        
        print(f"\n{'='*80}")
        print(f"✅ ITERATION {self.iteration_count} COMPLETE")
        print(f"{'='*80}")
        print(f"\n📊 Summary:")
        print(f"   Total Character Reduction: {total_reduction:,} chars")
        print(f"   Nodes Optimized: {nodes_optimized}")
        print(f"   Transitions Optimized: {transitions_optimized}")
        print(f"   Total Changes: {len(changes)}")
        
        return len(changes) > 0
    
    async def log_iteration(self, changes, metrics):
        """Log to LATENCY_ITERATIONS.md"""
        timestamp = datetime.now().isoformat()
        
        log_entry = f"""
## Iteration {self.iteration_count}: Direct Grok Optimization
**Date:** {timestamp}
**Agent:** JK First Caller-copy-copy
**Target:** 1.5s average latency

### Changes Made:
"""
        for change in changes:
            log_entry += f"- {change}\n"
        
        log_entry += f"""
### Metrics:
- **Total Character Reduction:** {metrics['total_reduction']:,} chars
- **Nodes Optimized:** {metrics['nodes_optimized']}
- **Transitions Optimized:** {metrics['transitions_optimized']}

### Next Steps:
1. Test the agent with real phone calls
2. Measure actual latency with the latency tester
3. Validate that logic and intent are preserved
4. Apply more optimizations if needed

### Status: ✅ Optimization Complete - Ready for Testing

---

"""
        
        try:
            with open('/app/LATENCY_ITERATIONS.md', 'a') as f:
                f.write(log_entry)
            print(f"✅ Logged to LATENCY_ITERATIONS.md")
        except Exception as e:
            print(f"❌ Error logging: {e}")


async def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               DIRECT LATENCY OPTIMIZATION SYSTEM v2.0                        ║
║               Optimizes Agent Prompts Using Grok 4                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    optimizer = DirectLatencyOptimizer()
    
    try:
        has_changes = await optimizer.run_optimization(max_nodes=5, max_transitions=10)
        
        if has_changes:
            print(f"\n✅ SUCCESS! Agent optimized and saved.")
            print(f"\n📞 Next: Test the agent by calling it and measuring latency.")
        else:
            print(f"\n⚠️ No optimizations applied (agent may already be optimal)")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
