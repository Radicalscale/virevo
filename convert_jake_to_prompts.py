#!/usr/bin/env python3
"""
Convert all script-mode nodes in Jake agent to prompt-mode
Uses simplified prompts based on Retell Caller patterns
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Mapping of node IDs to their prompt-mode instructions
NODE_PROMPTS = {
    "2": {
        # Name Confirmation
        "content": """Say the customer's name with an inquisitive tone: "{{customer_name}}?"

# Your Task
- Deliver the name clearly with an upward vocal lilt
- Wait for any verbal response (yes, yeah, speaking, etc.)
- Do NOT handle objections or questions in this node
- If they didn't hear correctly, simply repeat the name

# Tone
Polite, friendly, slightly expectant - like you're checking if it's the right person."""
    },
    "3": {
        # Intro & Help Request
        "content": """Introduce yourself and ask for help: "This is Jake. I was just, um, wondering if you could possibly help me out for a moment?"

# Your Task
- Deliver this greeting with a slight hesitation ("um") to sound natural
- Build slight intrigue about why you need help
- Wait for their response (yes, sure, what is it, etc.)
- Do NOT explain further in this node

# Tone
Low-key, genuine, humble, polite - inviting them to engage without pressure."""
    },
    "4": {
        # Stacking Income Hook
        "content": """Explain why you're calling: "Well, uh... I don't know if you could yet, but, I'm calling because you filled out an ad about stacking income without stacking hours. I know this call is out of the blue, but do you have just 25 seconds for me to explain why I'm reaching out today specifically?"

# Your Task
- Deliver the hook about "stacking income without stacking hours"
- Ask for 25 seconds to explain
- Handle objections naturally:
  * NO RECALL: "No problem - it's about building income without working more hours. Is that something you're focused on?"
  * TIME CONCERN: "Fair enough - is finding ways to increase income a priority for you right now?"
  * WHAT IS THIS: "It's a model for building digital assets that generate passive income. Want me to explain how that works?"
  * NOT INTERESTED: "Is it the idea of more income that's not a fit, or did I catch you at a bad time?"

# Tone
Natural, disarming, respectful of their time. Acknowledge the unexpected nature of the call."""
    },
    "5": {
        # Introduce Model
        "content": """Explain the model: "Okay. In a nutshell, we set up passive income websites, and we let them produce income for you. What questions come to mind as soon as you hear something like that?"

# Your Task
- Explain the basic model (passive income websites)
- Ask what questions they have to engage curiosity
- Handle objections intelligently:
  * SCAM CONCERN: "I get why you'd ask that. It's not a scam - we teach people how to build simple websites that generate income through ads and affiliates. Real people, no experience needed. Does that make sense?"
  * HOW DOES IT WORK: "Great question! The websites generate income through advertising and affiliate partnerships once they're set up. Want me to explain the process?"
  * SOUNDS TOO GOOD: "I understand the skepticism. This is about building a real business asset, not a get-rich-quick scheme. Happy to walk you through how it actually works."
  * COST CONCERN: "Fair to ask. We'll get to investment details, but first want to make sure the model itself makes sense to you."

# Tone
Clear, straightforward, patient. Address skepticism with understanding and facts."""
    },
    "7": {
        # Deframe Objection
        "content": """Handle their objection or concern.

# Your Task
- Listen to their full concern
- Validate it ("That's completely fair")
- Address it directly based on the type:
  * TRUST/SCAM: "That's fair. Can I ask - what's your biggest fear when you hear about an opportunity like this?"
  * DISINTEREST: "When you say not interested, is that because you're already set with income and have all the free time you want?"
  * TIME: "I get it. Is it finding a few minutes now, or concern about time to get something new running?"
  * OTHER PRIORITY: "Smart. Many of our clients do that AND this. Does balancing things out resonate?"

# Tone
Empathetic, non-defensive, genuinely curious about their underlying concern."""
    },
    "8": {
        # Early Dismiss - Share Background
        "content": """Handle early dismissal professionally.

# Your Task
- Acknowledge their position respectfully
- Ask one clarifying question to understand if it's truly not a fit:
  "I respect that. Just so I understand - is it that you're not looking to increase income right now, or is there something specific about this that doesn't fit?"
- If they confirm not interested, transition to ending gracefully

# Tone
Professional, respectful, not pushy. Give them an out while checking if there's genuine disinterest."""
    },
    "10": {
        # No Time - Permission
        "content": """Handle "no time" objection.

# Your Task
- Validate their busy schedule
- Differentiate between time constraints:
  "Time is definitely precious. When you mention being busy, is it finding a few minutes for this call, or concern about the time investment to get something new running?"
- If immediate time: "I totally understand. What would be a better time to reach you - maybe later today or tomorrow?"
- If long-term time: "That's exactly why this model is built the way it is - minimal ongoing time once it's set up."

# Tone
Understanding, not pushy, helps them clarify what kind of time concern they have."""
    }
}

async def convert_jake_agent():
    """Convert Jake agent's script nodes to prompt nodes"""
    
    print("="*80)
    print("CONVERTING JAKE AGENT SCRIPT NODES TO PROMPT MODE")
    print("="*80 + "\n")
    
    # Fetch Jake agent
    agent = await db.agents.find_one({"id": "474917c1-4888-47b8-b76b-f11a18f19d39"})
    if not agent:
        print("❌ Jake agent not found")
        return
    
    print(f"Found Jake agent: {agent.get('name')}")
    print(f"Total nodes: {len(agent.get('call_flow', []))}\n")
    
    # Track conversions
    converted = []
    already_prompt = []
    not_in_mapping = []
    
    # Process each node
    call_flow = agent.get('call_flow', [])
    for node in call_flow:
        node_id = node.get('id')
        node_label = node.get('label', 'Unknown')
        node_type = node.get('type')
        
        if node_type != 'conversation':
            continue
            
        current_mode = node.get('data', {}).get('mode', 'script')
        
        # Check if already prompt mode
        if current_mode == 'prompt':
            already_prompt.append(f"Node {node_id}: {node_label}")
            continue
        
        # Check if we have a prompt for this node
        if node_id in NODE_PROMPTS:
            # Convert to prompt mode
            node['data']['mode'] = 'prompt'
            node['data']['content'] = NODE_PROMPTS[node_id]['content']
            # Keep the original script as a backup comment
            original_script = node['data'].get('script', node['data'].get('content', ''))
            
            converted.append(f"Node {node_id}: {node_label}")
            print(f"✅ Converted Node {node_id} ({node_label})")
            print(f"   Original: {original_script[:80]}...")
            print(f"   New prompt: {len(NODE_PROMPTS[node_id]['content'])} chars\n")
        else:
            not_in_mapping.append(f"Node {node_id}: {node_label}")
    
    # Update the agent in database
    if converted:
        result = await db.agents.update_one(
            {"id": "474917c1-4888-47b8-b76b-f11a18f19d39"},
            {"$set": {"call_flow": call_flow}}
        )
        
        print("="*80)
        print("CONVERSION SUMMARY")
        print("="*80)
        print(f"\n✅ Converted {len(converted)} nodes to prompt mode:")
        for item in converted:
            print(f"   - {item}")
        
        if already_prompt:
            print(f"\n📌 Already prompt mode ({len(already_prompt)} nodes):")
            for item in already_prompt:
                print(f"   - {item}")
        
        if not_in_mapping:
            print(f"\n⚠️  Not converted ({len(not_in_mapping)} nodes - no mapping defined):")
            for item in not_in_mapping:
                print(f"   - {item}")
        
        print(f"\n💾 Updated agent in database: {result.modified_count} document(s) modified")
    else:
        print("⚠️  No nodes to convert")
    
    return converted

if __name__ == "__main__":
    asyncio.run(convert_jake_agent())
