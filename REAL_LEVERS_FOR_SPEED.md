# Real Levers for Speed - What Actually Controls LLM Latency

## Current Situation
- Skeptical test: 3576ms average
- LLM processing: 1611ms (45% of time)
- TTS generation: 842ms (24% of time)
- KB node: 3798 characters

## What Controls LLM Speed?

### 1. INPUT SIZE (What we send TO the LLM)
- System prompt: 8,518 chars (~2,130 tokens)
- KB node content: 3,798 chars (~950 tokens)
- Conversation history: variable
- **Total input: ~3,000-4,000 tokens per call**

Impact: More tokens = slower processing

### 2. OUTPUT SIZE (What LLM generates)
- max_tokens: Currently 500
- Actual average response: ~150-200 tokens
- **This controls generation time, not thinking time**

Impact: Linear - 500 tokens takes 2x longer than 250 tokens

### 3. MODEL CHOICE
- Current: "grok" (which specific version?)
- Grok has multiple models with different speed/quality tradeoffs
- Need to check what's available

### 4. PROCESSING COMPLEXITY
- Number of instructions in prompt
- Conditional logic complexity
- KB search operations
- Reasoning depth required

## What We CANNOT Change Without Breaking Quality
❌ Context awareness (needs conversation history)
❌ Adaptive responses (needs complex reasoning)
❌ Variation (needs creativity/randomness)
❌ Transition logic (needs exact semantic patterns)

## What We CAN Change
✅ Input token count (if done very carefully)
✅ Output token limit (cap response length)
✅ Model selection (use faster model if available)
✅ Infrastructure (parallel processing, caching non-dynamic parts)

## The Real Question
**Which model is being used and are there faster alternatives?**
