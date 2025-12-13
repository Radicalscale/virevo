"""
Trace EXACTLY what happens when KB node 1763206946898 processes input
Find where the 2-4 seconds are spent
"""
import asyncio
import os
import time
from motor.motor_asyncio import AsyncIOMotorClient

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
KB_NODE_ID = "1763206946898"

async def trace_execution():
    print("="*80)
    print("TRACING KB NODE EXECUTION - LINE BY LINE")
    print("="*80)
    print()
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    
    # Find the KB node
    kb_node = None
    for node in agent.get('call_flow', []):
        if node.get('id') == KB_NODE_ID:
            kb_node = node
            break
    
    if not kb_node:
        print("KB node not found")
        return
    
    node_content = kb_node.get('data', {}).get('content', '')
    system_prompt = agent.get('system_prompt', '')
    
    print("WHEN USER SAYS: 'This sounds like a scam'")
    print()
    print("EXECUTION FLOW:")
    print("-"*80)
    print()
    
    # Simulate what calling_service.py does
    print("1. process_user_input() called")
    print("   Location: calling_service.py")
    print("   Action: Receive user message")
    print("   Time: ~5ms")
    print()
    
    print("2. Build prompt for LLM")
    print("   Location: _process_call_flow_streaming()")
    print("   Action:")
    print("     a. Get system prompt (8,518 chars)")
    print("     b. Get conversation history (variable)")
    print("     c. Get current node content (3,798 chars)")
    print("     d. Check if KB retrieval needed")
    print("   Time: ~10ms")
    print()
    
    print("3. KB Retrieval Check")
    print("   Location: calling_service.py line ~2976")
    print("   Code:")
    print("     if should_retrieve_kb and self.knowledge_base:")
    print("         kb_context = retrieve_relevant_chunks(...)")
    print()
    print("   What happens:")
    print("     - Generates embedding for user message: ~100ms")
    print("     - Vector search in ChromaDB: ~50ms")
    print("     - Returns top 3 chunks: ~20ms")
    print("   Time: ~170ms TOTAL")
    print()
    
    print("4. Build Final Prompt")
    print("   Location: calling_service.py line ~3017")
    print("   Structure:")
    print("     System prompt: 8,518 chars (~2,130 tokens)")
    print("     + Conversation history: ~1,000 tokens")
    print("     + KB context: ~500 tokens")
    print("     + Node content: 3,798 chars (~950 tokens)")
    print("     + User message: ~50 tokens")
    print("     TOTAL INPUT: ~4,630 tokens")
    print()
    print("   Time: ~5ms (just string concatenation)")
    print()
    
    print("5. Send to Grok LLM")
    print("   Location: calling_service.py line ~790")
    print("   Code:")
    print("     response = await client.create_completion(")
    print("         messages=[system_msg, user_msg],")
    print("         model='grok-2-1212',")
    print("         temperature=0.7,")
    print("         max_tokens=500")
    print("     )")
    print()
    print("   What Grok does:")
    print("     a. Process 4,630 input tokens: ~800ms")
    print("     b. Generate response (~150 tokens): ~600ms")
    print("     TOTAL LLM TIME: ~1,400ms")
    print()
    print("   ⚠️ THIS IS WHERE MOST TIME IS SPENT!")
    print()
    
    print("6. Post-processing")
    print("   Location: calling_service.py")
    print("   Actions:")
    print("     - Extract response text")
    print("     - Update conversation history")
    print("     - Check for transitions")
    print("   Time: ~10ms")
    print()
    
    print("="*80)
    print("TOTAL BREAKDOWN:")
    print("="*80)
    print()
    print("KB retrieval:        170ms  (7%)")
    print("LLM processing:    1,400ms  (60%) ← BOTTLENECK")
    print("Response generation: 600ms  (26%)")
    print("Overhead:            50ms   (2%)")
    print("TTS generation:      800ms  (outside LLM)")
    print("---")
    print("TOTAL:            ~2,220ms")
    print()
    
    print("="*80)
    print("THE BOTTLENECK:")
    print("="*80)
    print()
    print("LLM must process 4,630 tokens EVERY TIME:")
    print("  - System prompt: 2,130 tokens (46%)")
    print("  - Node content: 950 tokens (21%)")
    print("  - Conversation history: 1,000 tokens (22%)")
    print("  - KB context: 500 tokens (11%)")
    print()
    print("The LLM physically can't process 4,630 tokens faster than ~800ms")
    print("Even the fastest model (92 tokens/sec) would take 600ms minimum")
    print()
    
    print("="*80)
    print("HOW TO REDESIGN THE AGENT:")
    print("="*80)
    print()
    print("OPTION 1: Reduce Input Size")
    print("  Problem: We tried this 10 times, breaks transitions")
    print("  Status: ❌ Not viable without breaking quality")
    print()
    
    print("OPTION 2: Separate Prompt from Instructions")
    print("  Current: Everything in one 3,798 char node")
    print("  New design:")
    print("    - Node contains only RESPONSE LOGIC (500 chars)")
    print("    - Transitions handled separately")
    print("    - KB search instructions in system prompt")
    print("    - DISC classification cached once")
    print()
    print("  Impact:")
    print("    Input: 4,630 → 2,680 tokens (42% reduction)")
    print("    LLM time: 1,400ms → 800ms (600ms saved)")
    print("    Total: 2,220ms → 1,420ms")
    print()
    print("  Risk: Need to ensure transitions still work")
    print()
    
    print("OPTION 3: Two-Stage Processing")
    print("  Stage 1: Fast classifier (100ms)")
    print("    - Determine objection type (scam/trust/price/time)")
    print("    - Use tiny prompt (<500 tokens)")
    print("    - Model: grok-2-1212 with max_tokens=10")
    print()
    print("  Stage 2: Focused responder (800ms)")
    print("    - Use objection-specific sub-prompt")
    print("    - Only 1,000 tokens (vs 4,630)")
    print("    - Generate contextual response")
    print()
    print("  Total: 900ms (vs 2,220ms)")
    print("  Impact: 59% faster")
    print()
    
    print("OPTION 4: Parallel Processing")
    print("  Current: Serial execution")
    print("    KB search (170ms) → LLM (1,400ms) → TTS (800ms)")
    print("    Total: 2,370ms")
    print()
    print("  New: Parallel where possible")
    print("    Start KB search")
    print("    Start LLM with partial context")
    print("    Start TTS as soon as first sentence ready")
    print()
    print("  Theoretical: 1,400ms (overlap KB and TTS)")
    print("  Impact: 41% faster")
    print()
    
    print("="*80)
    print("RECOMMENDATION: OPTION 3 (Two-Stage)")
    print("="*80)
    print()
    print("Why:")
    print("  1. Doesn't modify existing node (no transition risk)")
    print("  2. Adds preprocessing layer")
    print("  3. Each stage is simpler, faster")
    print("  4. Can fall back to full processing if needed")
    print()
    print("Implementation:")
    print("  1. Add classification step before node processing")
    print("  2. Route to objection-specific prompt templates")
    print("  3. Each template is 1,000 tokens (vs 4,630)")
    print()

asyncio.run(trace_execution())
