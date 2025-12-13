#!/usr/bin/env python3
"""
Test script for the improved prompt optimizer
Tests with the example prompt from the user
"""

import asyncio
import httpx
import os
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')

# Test prompt from user
TEST_PROMPT = """Hey, I have an llm using grok with a voice agent.
 
Please clean this prompt up for me so that the agent can execute properly.
 
I want the agent to answer any question the person might have just asked and then swing that naturally into explaining the value of the product which is setting up sites that can each bring in between $500-$2000 a month passively. They can set up as many as they want but we try to aim for at least 10 to start. Then ask them would they be opposed to an extra $20k a month coming in. The idea is to get them to say they want the money right. "No I wouldn't be opposed" "who'd be against that" etc etc.
 
I need this prompt cleaned up so the agent knows to aim for that result - and to lower the amount of time it would take for the llm to discern through the prompt so it can speed up it's response time and lower any hallucinations.
 
 
**NO DASHES FOR PAUSES/CONJUNCTIONS:** When generating *any* text for speech, NEVER use em-dashes (—) or en-dashes (–) to connect words, thoughts, or indicate pauses. Instead, use periods (`.`) for full stops between distinct ideas, or commas (`,`) with simple conjunctions (e.g., "and," "so," "but") for phrasal breaks.
## 1. Primary Goal for This Node
To dynamically answer the user's questions using the `qualifier setter` KB, - meaning you must talk about the sites what they're worth, and how much money they could potentially make in order to establish the value - and then deliver the "$20k" value-framing question. Wait for their answers to your questions before aiming to discuss the value. the transition is not triggered by skepticism it's compliance to the idea if the user saying anything that's skeptical like "depends" or "i don't know" get them to establish they want extra money.
---
## 2. Entry Context
You are entering this node after the user has acknowledged the "Rank and Bank" concept and is asking questions.
---
## 3. Opening Gambit (The Happy Path)
* This node is dynamic. Its primary action is the `Adaptive Interruption Engine` below, which begins by responding to the user's initial question. There is no single opening gambit.
---
## 4. Strategic Toolkit
This is your pre-defined list of tactics for handling predictable, high-stakes questions within this node.
* **Tactic for: PRICE Question ("How much is the course?")**
    * **AGENT SAYS:**
        > `<speak>That's exactly what the call with Kendrick is designed to figure out. It wouldn't be fair to throw out a number without knowing if this is even the right fit for you, would it?</speak>`
* **Tactic for: KB SEARCH FAILURE ("I don't have that information.")**
    * **Use If:** The `qualifier setter` KB does not contain a relevant answer to the user's question.
    * **AGENT SAYS:**
        > `<speak>You know, that's a very specific question that I don't have the answer to right now, but it's exactly the kind of thing Kendrick would be able to dive into on your call. Was there anything else I could clear up about the basics?</speak>`
---
## 5. Adaptive Two-Turn Interruption Engine
This is the core logic that governs every turn within this node.
> **ADAPTIVE INTERRUPTION ENGINE**
>
> **TURN 1: DIAGNOSE, ADAPT, & RESPOND**
>
> 1. **Analyze the Interruption:** What is the user's core intent (question, objection, confusion, statement)?
> 2. **Analyze the User's Behavioral Style:** Based on their language and tone, perform a quick search on the `DISC_Guide` KB to classify them as 'D', 'I', 'S', or 'C'.
> 3. **Make a Definitive Statement & Choose a Tool (ADAPTED):**
> * **IF** the interruption directly matches a tactic in the `Strategic Toolkit` (e.g., a PRICE question):
> * **THEN** deploy that pre-scripted, tuned tactic.
> * **ELSE (Default Action):**
> * **THEN** search the `qualifier setter` Knowledge Base for an answer to their question.
> * **IF** the KB returns a relevant answer:
> * Deliver the answer concisely, adapting the delivery to the user's DISC style.
> * **SYSTEM ACTION:** If the answer discusses income potential, set `has_discussed_income_potential = true`.
> * Ask a check-in question: `<speak>Does that make sense?</speak>`
> * **ELSE (if the KB fails):**
> * Deploy the `KB SEARCH FAILURE` tactic from the `Strategic Toolkit`.
>
> **TURN 2: RECOVER OR RE-ENGAGE**
>
> 1. **Analyze the User's Response** to your Turn 1 action.
> 2. **Make a Judgment Call:**
> * **IF** the user is still asking questions:
> * **THEN** loop back to the start of this engine (**TURN 1**) to handle their new utterance.
> * **ELSE IF** the user is now compliant or neutral (e.g., "Okay," "No other questions"):
> * **THEN** initiate **Goal-Oriented Recovery (with DISC Adaptation).**
>
> **GOAL-ORIENTED RECOVERY (THE "GET BACK ON TRACK" PROTOCOL)**
>
> 1. **Identify the Elicitation Goal:** The goal is to ask the "$20k" value-framing question.
> 2. **Check State:** The system must check the `has_discussed_income_potential` state variable.
> 3. **Generate a New, Adapted Path:**
> * **IF `has_discussed_income_potential == true`:**
> * **AGENT SAYS:** `<speak>Okay, great. So with all that in mind, would you honestly be upset if you had an extra twenty thousand dollars a month coming in?</speak>`
> * **ELSE (`has_discussed_income_potential == false`):**
> * **AGENT SAYS:** `<speak>Okay, great. So to put some numbers on it for you, each site you build can bring in anywhere from five hundred to two thousand a month. Most of our students aim for about ten sites to start. With that in mind, would you honestly be upset if you had an extra twenty thousand a month coming in?</speak>`
#### **Step 6: Define the "Escalation Mandate"**
This is the final safety net.
* **Action:** I will add a rule: "If you have looped through the `Adaptive Interruption Engine` more than twice without achieving the `Primary Goal`, you MUST escalate to the Global Prompt."
#### **Step 7: "Hallucination-Proof" the Final Node**
This is the final quality check.
* **Action A (Declarative, Not Generative):** The agent's primary function is retrieval and following stateful logic. Its "creativity" is strictly confined to moments of novel interruption, which are governed by clear rules.
* **Action B (State Management):** The system must support the `has_discussed_income_potential` state variable.
* **Action C (System Fallbacks):** I will include an "Anti-Stall Protocol" to handle potential latency or system silence, and every node's `Strategic Toolkit` will contain the following mandatory tactic:
    * **Tactic for: CATCH-ALL / TRANSCRIPTION ERROR (Default Tactic)**
        * **Use If:** The user's response is nonsensical, garbled, or does not make sense based on the current context of the conversation.
        * **AGENT SAYS:**
            > `<speak>I'm sorry, I didn't quite catch that. Could you say that again for me?</speak>`
        * **Performance Tuning:** A clear, polite, and neutral tone."""

async def test_optimizer():
    """Test the prompt optimizer with the example prompt"""
    
    print("=" * 80)
    print("TESTING IMPROVED PROMPT OPTIMIZER WITH GROK 4")
    print("=" * 80)
    print()
    
    # Connect to MongoDB to get Grok API key
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get Grok API key from database
    api_keys_collection = db['api_keys']
    grok_key_doc = await api_keys_collection.find_one({"service_name": "grok"})
    
    if not grok_key_doc:
        print("❌ Grok API key not found in database")
        print("   Please add Grok API key in Settings > API Keys")
        return
    
    grok_api_key = grok_key_doc.get('api_key')
    print(f"✅ Found Grok API key: {grok_api_key[:10]}...")
    print()
    
    print("📝 Original Prompt Length:", len(TEST_PROMPT), "characters")
    print()
    
    # Call the optimizer directly (simulating what the API does)
    print("🚀 Calling Grok 4 (grok-4-0709) to optimize...")
    print()
    
    optimization_prompt = f"""You are an expert at optimizing voice agent conversation node prompts for real-time non-reasoning LLM agents. Your task is to clean up and restructure the provided prompt to optimize for speed, clarity, and hallucination prevention.

**CORE OPTIMIZATION PRINCIPLES:**

**1. Modular Node Structure**
- Design as a focused, self-contained node with clear entry/exit points
- Break complex logic into numbered steps, not nested paragraphs
- Use headings (##) for major sections: Primary Goal, Entry Context, Strategic Toolkit, Core Logic, etc.

**2. Hallucination Prevention**
- Confine agent to retrieval from KB and predefined tactics only
- Include explicit "NEVER GUESS" or "NEVER MAKE UP INFORMATION" rules
- Use declarative, not generative instructions
- Add catch-all tactics for transcription errors or unclear input
- Set low temperature (0.1-0.3) mentally for deterministic outputs

**3. Speed Optimization**
- Reduce verbosity by 40-50% while preserving all logic
- Use bullet points, not prose
- Eliminate redundant explanations
- Make instructions scannable with clear action verbs
- Condense nested IF-THEN statements into flat numbered steps

**4. State Management**
- Explicitly define any state variables needed (e.g., `has_discussed_income_potential`)
- Show clear "set" and "check" points for states
- Use states to guide transitions without re-explaining context

**5. Voice-Specific Rules**
- **CRITICAL:** NO DASHES FOR PAUSES/CONJUNCTIONS. When generating ANY text for speech, NEVER use em-dashes (—) or en-dashes (–). Instead, use periods (`.`) for full stops between distinct ideas, or commas (`,`) with simple conjunctions (e.g., "and," "so," "but") for phrasal breaks.
- All speech text goes in `<speak>` tags
- Normalize for TTS: "john@example.com" → "john at example dot com"
- Keep sentences short and conversational

**6. Adaptive Logic (If Applicable)**
- If the node handles dynamic interruptions, structure as a clear loop with max iterations (e.g., 2 loops, then escalate)
- For DISC or persona adaptation: Quick KB search, not elaborate analysis
- Show recovery paths explicitly

**7. Strategic Toolkit**
- List predefined tactics for common scenarios (price questions, KB failures, catch-all errors)
- Format as: "**Tactic for: [SCENARIO]** → Agent says: `<speak>exact text</speak>`"
- Keep responses concise and on-brand

**8. Escalation Mandate**
- Always include a rule for when to escalate (e.g., after 2 failed loops, or if goal unmet)
- Make it explicit: "If X, then escalate to [Global Prompt / Human / Supervisor Node]"

**ORIGINAL PROMPT TO CLEAN UP:**
```
{TEST_PROMPT}
```

**YOUR TASK:**
1. Analyze the original prompt's intent, goals, and logic flow
2. Restructure it into the optimized format described above
3. Reduce verbosity while preserving ALL essential logic, rules, and goals
4. Ensure NO DASHES are used in any speech text (use periods/commas with conjunctions only)
5. Output ONLY the cleaned prompt, ready to paste directly into a voice agent node
6. Do NOT include explanations, context, or comparison tables—just the optimized prompt itself

**OUTPUT FORMAT:**
Return the cleaned prompt using clear markdown headings (##) and bullet points. Make it modular, scannable, and production-ready for a Grok-based voice agent."""

    try:
        async with httpx.AsyncClient(timeout=90.0) as http_client:
            response = await http_client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {grok_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-4-0709",
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an elite voice agent prompt engineer. You optimize prompts for real-time non-reasoning LLMs by reducing verbosity, preventing hallucinations, and structuring for speed. You output clean, production-ready prompts with zero fluff."
                        },
                        {"role": "user", "content": optimization_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 4000
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Grok API error: {response.status_code}")
                print(response.text)
                return
            
            result = response.json()
            optimized_content = result['choices'][0]['message']['content']
            usage = result.get('usage', {})
            
            print("✅ Optimization complete!")
            print()
            print("📊 Stats:")
            print(f"   Original length: {len(TEST_PROMPT)} chars")
            print(f"   Optimized length: {len(optimized_content)} chars")
            reduction = ((len(TEST_PROMPT) - len(optimized_content)) / len(TEST_PROMPT)) * 100
            print(f"   Reduction: {reduction:.1f}%")
            print(f"   Tokens used: {usage.get('total_tokens', 'unknown')}")
            print()
            print("=" * 80)
            print("OPTIMIZED PROMPT OUTPUT:")
            print("=" * 80)
            print()
            print(optimized_content)
            print()
            print("=" * 80)
            print()
            
            # Check for dashes in speech tags
            import re
            speak_tags = re.findall(r'<speak>(.*?)</speak>', optimized_content, re.DOTALL)
            has_dashes = False
            for tag in speak_tags:
                if '—' in tag or '–' in tag:
                    has_dashes = True
                    print(f"⚠️  WARNING: Found dashes in speech text: {tag[:100]}")
            
            if not has_dashes:
                print("✅ VALIDATION PASSED: No dashes found in speech text")
            else:
                print("❌ VALIDATION FAILED: Dashes found in speech text")
            
            print()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_optimizer())
