#!/usr/bin/env python3
"""
Node Fixes - Round 3 (Early Flow)
==================================
Fixes for remaining issues in early qualification flow:
- N201A_Employed_AskYearlyIncome: After income, ask about side hustle
- N201B_Employed_AskSideHustle: After "yes", ask HOW MUCH
"""

from pymongo import MongoClient
from bson import ObjectId

MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'
AGENT_ID = "69468a6d6a4bcc7eb92595cd"


def get_agent():
    client = MongoClient(MONGO_URL)
    db = client['test_database']
    return db['agents'].find_one({'_id': ObjectId(AGENT_ID)}), db


def find_node_by_partial_label(nodes, partial):
    for i, node in enumerate(nodes):
        data = node.get('data', {})
        label = data.get('label', '') or node.get('label', '')
        if partial.lower() in label.lower():
            return i, node
    return None, None


def apply_fix(db, agent_id, node_index, new_content):
    result = db['agents'].update_one(
        {'_id': ObjectId(agent_id)},
        {'$set': {f'call_flow.{node_index}.data.content': new_content}}
    )
    return result.modified_count > 0


# ============================================================================
# FIX: N201A_Employed_AskYearlyIncome
# Problem: After user gives income, agent doesn't ask about side hustle
# Solution: After income received, acknowledge and ask about side hustle
# ============================================================================
FIX_N201A_CONTENT = """## Primary Goal
Get the user's yearly income, then ask about side hustle.

## Entry Context
- Enter after user confirms they are employed.
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## Strategic Toolkit
- **Tactic for: Privacy ("That's personal")** → Agent says: "I get it. A rough estimate is fine. I just want to make sure this is a good fit for your current setup."
- **Tactic for: Refusal ("I'd rather not say")** → Agent says: "No worries at all. Let me ask a different way. Would you say you're making under fifty thousand, or over?"
- **Tactic for: CATCH-ALL** → Agent says: "I'm sorry, I didn't quite catch that. Could you say that again?"

## Core Logic

### PART 1: Opening (If user just confirmed employment)
Agent says: "Got it. And what's that job producing for you yearly, approximately?"

**Wait for user response.**

### PART 2: After user provides income

**If user provides income amount (any number - 30k, 36 thousand, about 40k, etc.):**

- Store in {{employed_yearly_income}}

## CRITICAL RESPONSE - INCOME RECEIVED
Agent MUST say EXACTLY:

"Got it. And in the last two years, did you happen to have any kind of side hustle or anything else bringing in income?"

**DO NOT:**
- DO NOT say "that gives me a clear picture"
- DO NOT say "Thanks for sharing"
- DO NOT ask about goals or timelines
- DO NOT explain the program

**ASK THE SIDE HUSTLE QUESTION IMMEDIATELY.**

The next node handles their answer.

**If objection:** Deploy ONE matching tactic, then get income and ask side hustle question.

## State Management
- Set: {{employed_yearly_income}} = yearly amount

## Escalation Mandate
After asking the side hustle question, this node is COMPLETE."""


# ============================================================================
# FIX: N201B_Employed_AskSideHustle
# Problem: When user says "yes" to side hustle, agent doesn't ask HOW MUCH
# Solution: When yes, immediately ask for the monthly amount
# ============================================================================
FIX_N201B_CONTENT = """## Primary Goal
Ask if user has a side hustle. If YES, immediately ask how much it makes monthly.

## Entry Context
- Enter after user provides yearly income.
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## Strategic Toolkit
- **Tactic for: Confusion ("What do you mean by side hustle?")** → Agent says: "Good question. Just anything extra you might have done on the side to bring in a bit more money. So, anything like that for you in the last couple of years?"
- **Tactic for: Privacy ("Why do you need to know?")** → Agent says: "It just helps me understand your overall picture. It's not a deal-breaker either way."
- **Tactic for: CATCH-ALL** → Agent says: "I'm sorry, I didn't quite catch that. Could you say that again?"

## Core Logic

### PART 1: Opening (If asking fresh)
Agent says: "And in the last two years, did you happen to have any kind of side hustle or anything else bringing in income?"

**Wait for user response.**

### PART 2: After user responds

**If user says YES (Yes, I do, Yeah, I freelance, I have a side gig, etc.):**

## CRITICAL RESPONSE - SIDE HUSTLE CONFIRMED
Agent MUST say EXACTLY:

"Okay, great. And what was that side hustle bringing in for you, say, on a good month?"

**DO NOT:**
- DO NOT say "Thanks for sharing"
- DO NOT say "freelance work counts as a great side hustle"
- DO NOT ask about anything else
- DO NOT explain the program

**ASK FOR THE MONTHLY AMOUNT IMMEDIATELY.**

The next node handles the amount and vehicle question.

**If user says NO:** Transition to vehicle question node.

**If objection:** Deploy ONE matching tactic.

## State Management
- Set: has_side_hustle = true/false

## Escalation Mandate
After asking for the monthly amount (or transitioning on "no"), this node is COMPLETE."""


def main():
    agent, db = get_agent()
    if not agent:
        print("❌ Agent not found")
        return
    
    nodes = agent.get('call_flow', [])
    print(f"✅ Loaded agent: {agent.get('name')}")
    
    fixes = [
        ("N201A_Employed_AskYearlyIncome", FIX_N201A_CONTENT, "Turn 6: Ask side hustle after income"),
        ("N201B_Employed_AskSideHustle", FIX_N201B_CONTENT, "Turn 7: Ask HOW MUCH after yes"),
    ]
    
    print("\n" + "="*60)
    print("🔧 APPLYING ROUND 3 FIXES (Early Flow)")
    print("="*60)
    
    for partial_label, new_content, description in fixes:
        idx, node = find_node_by_partial_label(nodes, partial_label)
        if idx is None:
            print(f"\n❌ Node not found: {partial_label}")
            continue
        
        data = node.get('data', {})
        label = data.get('label', partial_label)
        
        print(f"\n📝 Fixing: {label}")
        print(f"   Issue: {description}")
        
        if apply_fix(db, AGENT_ID, idx, new_content):
            print(f"   ✅ APPLIED")
        else:
            print(f"   ❌ FAILED")
    
    print("\n" + "="*60)
    print("✅ ROUND 3 FIXES APPLIED")
    print("="*60)


if __name__ == '__main__':
    main()
