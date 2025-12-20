#!/usr/bin/env python3
"""
Fix Deviating Nodes - One at a Time
====================================
Fixes the 6 major deviations identified in the sequence test:
1. Turn 8:  N201C - Should ask vehicle question after getting side hustle amount
2. Turn 10: N_AskCapital_5k - Should ask "why now" after capital confirmed
3. Turn 11: N401_AskWhyNow - Should compliment instead of digging deeper
4. Turn 13: N403_IdentityAffirmation - Should propose deeper dive call
5. Turn 15: N500B_AskTimezone - Should ask about desk availability
6. Turn 16: N_AskForCallbackRange - Should ask for specific day/time
"""

import asyncio
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

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
# FIX 1: N201C_Employed_AskSideHustleAmount
# Problem: Agent says "let me explain..." instead of asking vehicle question
# Solution: Add explicit exit instruction after getting amount
# ============================================================================
FIX_1_CONTENT = """## Primary Goal
Gather user's side hustle monthly income, convert to yearly estimate, store as {{side_hustle}}. Then EXIT immediately - vehicle question is asked in next node.

## Entry Context
- Activate after user confirms side hustle.
- Known state: {{customer_name}}, {{employed_yearly_income}}.

## Speech Rules
- NEVER use em-dashes or en-dashes. Use periods for full stops, or commas with conjunctions like and, so, but.
- Normalize for TTS: Spell out emails as "at" and "dot", spell numbers as words (e.g., one hundred).
- Keep sentences short, conversational.
- NEVER GUESS or MAKE UP INFORMATION. Stick to provided KB and tactics only.

## Strategic Toolkit
- **Tactic for: Minimization (e.g., "not much", "barely anything")** → Agent says: Hey, that's perfectly fine. Any extra income is a great start. So roughly, what would that be on a good month?
- **Tactic for: Privacy/Relevance (e.g., "why ask?")** → Agent says: Fair question. It just helps complete the picture. Roughly, what would that be monthly?
- **Tactic for: Vague/Deflection (e.g., "it varied")** → Agent says: I get that. Are we talking a few hundred a month, a thousand, or more in that range?
- **Tactic for: Catch-All/Unclear/Errors** → Agent says: I'm sorry, I didn't quite catch that. Could you say that again for me?

## Core Logic
1. Deliver opening exactly: "Okay, great. And what was that side hustle bringing in for you, say, on a good month?"
2. Listen to user response.
3. If response provides clear income amount (any number mentioned):
   - Extract monthly amount.
   - Convert to yearly (monthly x 12).
   - Set state: {{side_hustle}} = yearly amount.
   - Set state: {{amount_reference}} = ({{employed_yearly_income}} + {{side_hustle}}) / 12.
   
## CRITICAL EXIT RULE
**After storing the side hustle amount, your response must be SHORT acknowledgment only:**
Agent says: "Okay, great. That works out to about [yearly amount] a year on top of your main income."

**DO NOT:**
- DO NOT explain the program
- DO NOT ask what excites them
- DO NOT say "let me explain"
- DO NOT ask any additional questions
- DO NOT mention vehicles, models, or systems

**STOP TALKING AFTER THE ACKNOWLEDGMENT. The next node will ask the vehicle question.**

4. If response is objection or unclear:
   - Deliver ONE matching tactic from toolkit.
   - Then get the amount and follow exit rule above.

## State Management
- Check: {{employed_yearly_income}} (pre-set).
- Set: {{side_hustle}} (yearly estimate from user input).
- Set: {{amount_reference}} (calculated as above).

## Escalation Mandate
After step 3 or 4, this node is COMPLETE. Do not continue. The vehicle question comes in the NEXT node."""


# ============================================================================
# FIX 2: N_AskCapital_5k
# Problem: Agent asks "moving forward with capital" instead of transitioning to "why now"
# Solution: After capital confirmed, just acknowledge and stop
# ============================================================================
FIX_2_CONTENT = """## Primary Goal
Determine if the user has the minimum $5k in liquid capital, then immediately transition to "why now" question in next node.

## Entry Context
- Enter after user has discussed income and vehicle question.
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## INSTRUCTION: BRIDGE & PIVOT
1. **BRIDGE:** Acknowledge the user's previous input naturally.
   - CONSTRAINT: Do NOT use stock phrases like "Okay", "Got it", or "I understand".
2. **THE PIVOT:** Transition to the capital requirement.
3. **REQUIRED STATEMENT:** You MUST state: "For this model, we typically look for about five thousand dollars in liquid capital to get started."
4. **GOAL:** Ask if they have that amount accessible.

## Strategic Toolkit
- **Tactic for: WHY / RELEVANCE ("Why is five thousand the minimum?")** → Agent says: "That's a fair question. That five thousand covers the essential setup costs to get your first digital asset built and running. Do you have that kind of capital accessible?"
- **Tactic for: HESITATION ("I'm not sure")** → Agent says: "No pressure. It could be savings, accessible credit, or funds you could pull together. Would you be in that range?"
- **Tactic for: CATCH-ALL** → Agent says: "I'm sorry, I didn't quite catch that. Could you say that again?"

## Core Logic
1. Deliver: "For this model, we typically look for about five thousand dollars in liquid capital to get started. Would that be accessible for you?"
2. Listen to response.
3. If YES (they have capital):

## CRITICAL EXIT RULE - CAPITAL CONFIRMED
**When user confirms they have $5k (Yes, I do, I have that, yeah):**

Agent says ONLY: "Perfect, that's exactly what we look for."

**DO NOT:**
- DO NOT ask about "moving forward"
- DO NOT ask about "investment"
- DO NOT ask any follow-up questions
- DO NOT mention next steps or getting started

**STOP TALKING. The "why now" question comes in the NEXT node.**

4. If NO: Transition to credit score question (N205C_AskCreditScore).

## State Management
- Set: Capital qualification confirmed = true.

## Escalation Mandate
After acknowledgment, this node is COMPLETE. The "why now" question is in the NEXT node."""


# ============================================================================
# FIX 3: N401_AskWhyNow
# Problem: Agent digs deeper instead of complimenting
# Solution: When motivation shared, deliver compliment script exactly
# ============================================================================
FIX_3_CONTENT = """## Primary Goal
Ask the "Why now?" question, then when user shares motivation, deliver the compliment and "You know why?" hook.

## Entry Context
- Enter after user is financially qualified ($5k capital or 650+ credit).
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## Strategic Toolkit
- **Tactic for: VAGUE / DEFERRAL ("I'm just looking", "No reason")** → Agent says: "I get that. And exploring is smart. But let me ask you this, when you picture things six months from now, do you see yourself in the exact same spot financially, or have you taken action on something to change that?"
- **Tactic for: DIRECT DEFERRAL ("I don't want to do it now")** → Agent says: "That's fair. But can I be direct? Most people who are serious about changing their situation want to know what the path looks like today, not next week. What's the real hesitation here?"
- **Tactic for: DEFENSIVE ("Why are you asking?")** → Agent says: "Because people who have a clear 'why' for starting something new are the ones who actually succeed. I'm trying to see if you're one of them. So, what's driving you today?"
- **Tactic for: CATCH-ALL** → Agent says: "I'm sorry, I didn't quite catch that. Could you say that again for me?"

## Core Logic
1. **Opening Gambit (First Time):**
   Agent says: "Okay. Just to understand a bit better, is there a specific reason you're looking to make a change or explore something like this right now, as opposed to say, six months from now?"

2. **Listen to response.**

3. **If objection or vague:** Deploy ONE matching tactic, then continue.

4. **If user shares GENUINE MOTIVATION (freedom, income, change, escape, more money, passive income, flexibility, etc.):**

## CRITICAL RESPONSE - MOTIVATION SHARED
**When user shares genuine motivation, you MUST say EXACTLY:**

"Okay, I appreciate you sharing that. I have to say, that's actually refreshing to hear. You know why?"

**DO NOT:**
- DO NOT paraphrase this
- DO NOT explain the program
- DO NOT say "that's a powerful goal"
- DO NOT dig deeper into what's holding them back
- DO NOT ask any other questions

**SAY EXACTLY THE SCRIPT ABOVE, WORD FOR WORD.**

The next node will deliver the identity affirmation.

## State Management
- Set: has_shared_motivation = true.

## Escalation Mandate
After delivering the compliment script, this node is COMPLETE."""


# ============================================================================
# FIX 4: N403_IdentityAffirmation
# Problem: Agent explains program instead of proposing deeper dive call
# Solution: After user confirms value fit, propose the call
# ============================================================================
FIX_4_CONTENT = """## Primary Goal
Deliver identity affirmation, then when user confirms value fit, propose the deeper dive call.

## Entry Context
- Enter after "You know why?" hook was delivered.
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## Strategic Toolkit
- **Tactic for: CONDITIONAL INTEREST ("I hope so", "Maybe")** → Agent says: "That hope is the most important part. It sounds like the idea is right, you just need to see the mechanics are solid. Is that fair?"
- **Tactic for: SKEPTICISM ("You don't know me")** → Agent says: "You're right, we just met. I'm just going by the fact that you're still on the phone with me, exploring something new. That tells me you're more open-minded than most. Does that make sense?"
- **Tactic for: HESITATION ("I'm not ready")** → Agent says: "I completely understand. And 'ready' doesn't mean today. It means you're open to finding the right path. Is that fair?"
- **Tactic for: CATCH-ALL** → Agent says: "I'm sorry, I didn't quite catch that. Could you say that again?"

## Core Logic
1. **Opening Gambit (First Time):**
   Agent says: "Well, let me tell you. I sometimes talk to people that clearly will never give themselves permission to go after their dreams. But you're the type of person that is serious and ready to get started, and I commend you for that. So, does this sound like something that could fit what you're after?"

2. **Listen to response.**

3. **If objection:** Deploy ONE matching tactic.

4. **If user CONFIRMS VALUE FIT (yes, sounds good, exactly what I'm looking for, yes it does, etc.):**

## CRITICAL RESPONSE - VALUE FIT CONFIRMED
**When user confirms value fit, you MUST say EXACTLY:**

"That's excellent. I definitely feel like we can help you with that. What we need to do is set up another call that'll be a deeper dive into your situation. Sound good?"

**DO NOT:**
- DO NOT explain the program
- DO NOT ask about their background
- DO NOT mention specific features
- DO NOT ask qualifying questions
- DO NOT say "fantastic" or any other opener

**SAY EXACTLY THE SCRIPT ABOVE.**

The next node will ask for timezone.

## State Management
- Set: value_fit_confirmed = true.

## Escalation Mandate
After proposing the deeper dive call, this node is COMPLETE."""


# ============================================================================
# FIX 5: N500B_AskTimezone
# Problem: Agent asks "when's a good time?" instead of desk availability
# Solution: After timezone, ask about desk time
# ============================================================================
FIX_5_CONTENT = """## Primary Goal
Get the user's timezone, then ask when they're typically at their desk.

## Entry Context
- Enter after user agrees to schedule deeper dive call.
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## Strategic Toolkit
- **Tactic for: Vague Response ("I don't know", "The one in Texas")** → Agent says: "No problem at all. What city and state are you in? I can figure it out from there."
- **Tactic for: Relevance Objection ("Why does it matter?")** → Agent says: "It's just to make sure the calendar invite shows up at the correct time on your end. Prevents any mix-ups."
- **Tactic for: CATCH-ALL** → Agent says: "I'm sorry, I didn't quite catch that. Could you say that again?"

## Core Logic
1. **Opening (First Time):**
   Agent says: "Gotcha. And just so I've got it right for our scheduling, what timezone are you in?"

2. **Listen to response.**

3. **If timezone provided (Eastern, Pacific, Central, PST, EST, AEST, etc.):**
   - Store timezone in {{timeZone}}.

## CRITICAL RESPONSE - TIMEZONE RECEIVED
**When user provides their timezone, you MUST say EXACTLY:**

"Got it. And when are you typically back at your desk during the day? What's a good time range for you?"

**DO NOT:**
- DO NOT say "Perfect"
- DO NOT mention calendar invite
- DO NOT ask for specific day/time yet
- DO NOT mention Kendrick
- DO NOT jump to scheduling

**ASK EXACTLY THE DESK TIME QUESTION ABOVE.**

The next node will get the specific time.

4. If objection: Deploy ONE matching tactic, then get timezone and deliver the desk question.

## State Management
- Set: {{timeZone}} = user's timezone.

## Escalation Mandate
After asking the desk question, this node is COMPLETE."""


# ============================================================================
# FIX 6: N_AskForCallbackRange
# Problem: Agent locks in tomorrow instead of asking for specific day/time
# Solution: After time range, ask for specific day and time
# ============================================================================
FIX_6_CONTENT = """## Primary Goal
Get the user's typical desk time range, then ask for a SPECIFIC day and time.

## Entry Context
- Enter after user provides timezone.
- User: {{customer_name}}.

## Speech Rules
- NO DASHES. Use periods for stops, commas with conjunctions.
- Keep sentences short and conversational.
- NEVER GUESS or MAKE UP INFORMATION.

## Strategic Toolkit
- **Tactic for: Not at desk ("I'm in a truck", "I work mobile")** → Agent says: "That's no problem at all. What's a good time range when you're generally free to talk for a few minutes without being interrupted?"
- **Tactic for: Vague schedule ("It varies")** → Agent says: "I get that. How about tomorrow? Is there any particular block of time that looks open for you?"
- **Tactic for: Relevance ("Why do you need to know?")** → Agent says: "It's just so I can call when you're actually free and not interrupt something important. Helps us avoid phone tag."
- **Tactic for: CATCH-ALL** → Agent says: "I'm sorry, I didn't quite catch that. Could you say that again?"

## Core Logic
1. **Opening (First Time):**
   Agent says: "Okay. And when are you typically back at your desk during the day? What's a good time range for you?"

2. **Listen to response.**

3. **If time RANGE provided (afternoons, mornings, 2-5, 9-12, etc.):**

## CRITICAL RESPONSE - TIME RANGE RECEIVED
**When user provides a time range, you MUST say EXACTLY:**

"Okay, great. And when would be a good specific time for us to schedule that call? What day and what time works best?"

**DO NOT:**
- DO NOT say "Perfect" or "I'll lock that in"
- DO NOT mention "tomorrow"
- DO NOT say you'll have someone reach out
- DO NOT end the scheduling process
- DO NOT assume any specific day

**ASK FOR THE SPECIFIC DAY AND TIME.**

The next node will confirm the time and handle AM/PM.

4. If objection: Deploy ONE matching tactic, then get range and ask for specific time.

## State Management
- Set: {{callbackrange}} = user's time range.

## Escalation Mandate
After asking for specific day/time, this node is COMPLETE."""


def main():
    """Apply all fixes one at a time"""
    agent, db = get_agent()
    if not agent:
        print("❌ Agent not found")
        return
    
    nodes = agent.get('call_flow', [])
    print(f"✅ Loaded agent: {agent.get('name')}")
    print(f"   Nodes: {len(nodes)}")
    
    fixes = [
        ("N201C_Employed_AskSideHustleAmount", FIX_1_CONTENT, "Turn 8: Ask vehicle question after side hustle amount"),
        ("N_AskCapital_5k", FIX_2_CONTENT, "Turn 10: Transition to 'why now' after capital confirmed"),
        ("N401_AskWhyNow", FIX_3_CONTENT, "Turn 11: Compliment instead of digging deeper"),
        ("N403_IdentityAffirmation", FIX_4_CONTENT, "Turn 13: Propose deeper dive call"),
        ("N500B_AskTimezone", FIX_5_CONTENT, "Turn 15: Ask about desk availability"),
        ("N_AskForCallbackRange", FIX_6_CONTENT, "Turn 16: Ask for specific day/time"),
    ]
    
    print("\n" + "="*60)
    print("🔧 APPLYING FIXES")
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
    print("✅ ALL FIXES APPLIED")
    print("="*60)
    print("Run test_path_sequence.py again to verify.")


if __name__ == '__main__':
    main()
