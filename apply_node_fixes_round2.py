#!/usr/bin/env python3
"""
Additional Node Fixes - Round 2
================================
Fixes for remaining issues found in verification test:
- N402_Compliment: Should deliver identity affirmation after "No, why?"
- N500A_ProposeDeeperDive: Should ask for timezone after user agrees
"""

from pymongo import MongoClient
from bson import ObjectId

MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'
AGENT_ID = "69468a6d6a4bcc7eb92595cd"


def get_agent():
    """Get agent from MongoDB"""
    client = MongoClient(MONGO_URL)
    db = client['test_database']
    return db['agents'].find_one({'_id': ObjectId(AGENT_ID)}), db


def find_node_by_partial_label(nodes, partial):
    """Find node by partial label match"""
    for i, node in enumerate(nodes):
        data = node.get('data', {})
        label = data.get('label', '') or node.get('label', '')
        if partial.lower() in label.lower():
            return i, node
    return None, None


def apply_fix(db, agent_id, node_index, new_content):
    """Apply fix to specific node"""
    result = db['agents'].update_one(
        {'_id': ObjectId(agent_id)},
        {'$set': {f'call_flow.{node_index}.data.content': new_content}}
    )
    return result.modified_count > 0


# ============================================================================
# FIX: N402_Compliment_And_AskYouKnowWhy
# Problem: After "You know why?", when user says "No, why?" - agent should 
# deliver the identity affirmation, NOT stay in N402
# Solution: Make N402 handle BOTH the "You know why?" AND the follow-up response
# ============================================================================
FIX_N402_CONTENT = """## Primary Goal
This is a TWO-PART node:
1. First, deliver "I appreciate you... You know why?"
2. Then, when user responds, deliver the identity affirmation

## Entry Context
- Enter after user shares their motivation for wanting change.
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## Core Logic

### PART 1: Opening (If user just shared motivation)
Agent says EXACTLY: "Okay, I appreciate you sharing that. I have to say, that's actually refreshing to hear. You know why?"

**Wait for user response.**

### PART 2: After user responds to "You know why?"

When user responds with ANYTHING (No why?, Why?, What?, Tell me, etc.):

## CRITICAL RESPONSE - DELIVER IDENTITY AFFIRMATION
Agent MUST say EXACTLY:

"Well, let me tell you. I sometimes talk to people that clearly will never give themselves permission to go after their dreams. But you're the type of person that is serious and ready to get started, and I commend you for that. So, does this sound like something that could fit what you're after?"

**DO NOT:**
- DO NOT explain the program details
- DO NOT mention specific features
- DO NOT say anything else before or after this script
- DO NOT improvise or paraphrase

**SAY EXACTLY THE SCRIPT ABOVE.**

The next node will handle their response about value fit.

## Strategic Toolkit
- **Tactic for: CATCH-ALL** → Agent says: "I'm sorry, I didn't quite catch that. Could you say that again?"

## State Management
- Part 1 delivered = waiting for response
- Part 2 delivered = node complete

## Escalation Mandate
After delivering Part 2 (identity affirmation), this node is COMPLETE."""


# ============================================================================
# FIX: N500A_ProposeDeeperDive
# Problem: After user agrees to call, agent says "I'll have our team reach out"
# instead of asking for timezone
# Solution: When user agrees, ask for timezone immediately
# ============================================================================
FIX_N500A_CONTENT = """## Primary Goal
Get user agreement to schedule a deeper dive call. When they agree, immediately ask for their timezone.

## Entry Context
- Enter after user confirms value fit.
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## Strategic Toolkit
- **Tactic for: Hesitation ("What's the call about?")** → Agent says: "Good question. The next call is for our senior consultant to review your situation and outline a custom plan. It's a strategy session, not a sales pitch. Does that sound helpful?"
- **Tactic for: Time ("I'm busy")** → Agent says: "I understand. We keep it to forty five minutes, and we flex to your schedule. Can we find a slot that works?"
- **Tactic for: Cost ("Is this a sales call?")** → Agent says: "The best part is the call is free with no obligation. Are you open to that?"
- **Tactic for: CATCH-ALL** → Agent says: "Sorry, I didn't catch that. Could you repeat it?"

## Core Logic

### PART 1: Opening (If Fresh Start)
Agent says: "Okay, that's excellent. I definitely feel like we can help you with that. What we need to do is set up another call that'll be a deeper dive into your situation. Sound good?"

**Wait for user response.**

### PART 2: After user responds

**If user AGREES (Yes, Sure, Sounds good, Okay, Yeah, Yep, etc.):**

## CRITICAL RESPONSE - AGREEMENT RECEIVED
Agent MUST say EXACTLY:

"Great. And just so I've got it right for our scheduling, what timezone are you in?"

**DO NOT:**
- DO NOT say "I'll have our team reach out"
- DO NOT mention sending details
- DO NOT ask for email
- DO NOT mention Kendrick
- DO NOT say anything about "locking in"
- DO NOT end the scheduling process

**ASK FOR TIMEZONE IMMEDIATELY.**

The next node will continue with desk availability.

**If user OBJECTS:** Deploy ONE matching tactic, then wait for response.

## State Management
- Agreement received = ask for timezone immediately

## Escalation Mandate
After asking for timezone, this node is COMPLETE."""


def main():
    """Apply fixes"""
    agent, db = get_agent()
    if not agent:
        print("❌ Agent not found")
        return
    
    nodes = agent.get('call_flow', [])
    print(f"✅ Loaded agent: {agent.get('name')}")
    print(f"   Nodes: {len(nodes)}")
    
    fixes = [
        ("N402_Compliment_And_AskYouKnowWhy", FIX_N402_CONTENT, "Turn 12: Deliver identity affirmation after 'No, why?'"),
        ("N500A_ProposeDeeperDive", FIX_N500A_CONTENT, "Turn 14: Ask for timezone after user agrees"),
    ]
    
    print("\n" + "="*60)
    print("🔧 APPLYING ROUND 2 FIXES")
    print("="*60)
    
    for partial_label, new_content, description in fixes:
        idx, node = find_node_by_partial_label(nodes, partial_label)
        if idx is None:
            print(f"\n❌ Node not found: {partial_label}")
            continue
        
        data = node.get('data', {})
        label = data.get('label', partial_label)
        old_content = data.get('content', '')
        
        print(f"\n📝 Fixing: {label}")
        print(f"   Issue: {description}")
        print(f"   Old content: {len(old_content)} chars")
        print(f"   New content: {len(new_content)} chars")
        
        if apply_fix(db, AGENT_ID, idx, new_content):
            print(f"   ✅ APPLIED")
        else:
            print(f"   ❌ FAILED")
    
    print("\n" + "="*60)
    print("✅ ROUND 2 FIXES APPLIED")
    print("="*60)


if __name__ == '__main__':
    main()
