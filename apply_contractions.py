#!/usr/bin/env python3
"""
Contraction Fixer - Natural Speech Cleanup
===========================================
1. Scans all node prompts for non-contracted speech
2. Replaces with natural contractions
3. Adds global rule for dynamic generation
"""

from pymongo import MongoClient
from bson import ObjectId
import re

MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'
AGENT_ID = "69468a6d6a4bcc7eb92595cd"

# Contractions to apply (case-insensitive replacements)
CONTRACTIONS = [
    # Common ones
    ("I am", "I'm"),
    ("I will", "I'll"),
    ("I would", "I'd"),
    ("I have", "I've"),
    ("I had", "I'd"),
    ("you are", "you're"),
    ("you will", "you'll"),
    ("you would", "you'd"),
    ("you have", "you've"),
    ("you had", "you'd"),
    ("we are", "we're"),
    ("we will", "we'll"),
    ("we would", "we'd"),
    ("we have", "we've"),
    ("they are", "they're"),
    ("they will", "they'll"),
    ("they would", "they'd"),
    ("they have", "they've"),
    ("it is", "it's"),
    ("it will", "it'll"),
    ("it would", "it'd"),
    ("it has", "it's"),
    ("that is", "that's"),
    ("that will", "that'll"),
    ("that would", "that'd"),
    ("that has", "that's"),
    ("there is", "there's"),
    ("there will", "there'll"),
    ("there would", "there'd"),
    ("here is", "here's"),
    ("what is", "what's"),
    ("what will", "what'll"),
    ("who is", "who's"),
    ("who will", "who'll"),
    ("how is", "how's"),
    ("where is", "where's"),
    ("when is", "when's"),
    ("why is", "why's"),
    ("is not", "isn't"),
    ("are not", "aren't"),
    ("was not", "wasn't"),
    ("were not", "weren't"),
    ("have not", "haven't"),
    ("has not", "hasn't"),
    ("had not", "hadn't"),
    ("will not", "won't"),
    ("would not", "wouldn't"),
    ("could not", "couldn't"),
    ("should not", "shouldn't"),
    ("do not", "don't"),
    ("does not", "doesn't"),
    ("did not", "didn't"),
    ("can not", "can't"),
    ("cannot", "can't"),
    ("let us", "let's"),
]

# Global rule to add
CONTRACTION_RULE = """
## NATURAL SPEECH - CONTRACTION RULES (MANDATORY)
Always use contractions in spoken responses to sound natural and conversational:
- Use "I'm" not "I am"
- Use "you're" not "you are"
- Use "we're" not "we are"
- Use "it's" not "it is"
- Use "that's" not "that is"
- Use "there's" not "there is"
- Use "don't" not "do not"
- Use "won't" not "will not"
- Use "can't" not "cannot"
- Use "I'll" not "I will"
- Use "you'll" not "you will"
- Use "we'll" not "we will"
- Use "I've" not "I have"
- Use "you've" not "you have"
- Use "I'd" not "I would"
- Use "you'd" not "you would"
- Use "let's" not "let us"
- Use "what's" not "what is"
- Use "who's" not "who is"
- Use "how's" not "how is"

**SPEAK NATURALLY.** Avoid formal, stiff language. Sound like a friendly human, not a robot.
"""


def apply_contractions(text: str) -> tuple[str, int]:
    """Apply all contractions to text, return (new_text, count_of_changes)"""
    changes = 0
    result = text
    
    for formal, contraction in CONTRACTIONS:
        # Case-insensitive replacement
        pattern = re.compile(re.escape(formal), re.IGNORECASE)
        
        def replace_match(match):
            nonlocal changes
            original = match.group(0)
            # Preserve case of first letter
            if original[0].isupper():
                changes += 1
                return contraction[0].upper() + contraction[1:]
            else:
                changes += 1
                return contraction.lower()
        
        result = pattern.sub(replace_match, result)
    
    return result, changes


def main():
    client = MongoClient(MONGO_URL)
    db = client['test_database']
    
    agent = db['agents'].find_one({'_id': ObjectId(AGENT_ID)})
    if not agent:
        print("❌ Agent not found")
        return
    
    print(f"✅ Loaded: {agent.get('name')}")
    
    nodes = agent.get('call_flow', [])
    global_prompt = agent.get('global_prompt', '') or agent.get('system_prompt', '')
    
    total_node_changes = 0
    nodes_modified = 0
    
    print("\n" + "="*60)
    print("🔧 APPLYING CONTRACTIONS TO NODE PROMPTS")
    print("="*60)
    
    # Process each node
    for i, node in enumerate(nodes):
        data = node.get('data', {})
        content = data.get('content', '') or data.get('script', '')
        label = data.get('label', f'Node {i}')
        
        if not content:
            continue
        
        new_content, changes = apply_contractions(content)
        
        if changes > 0:
            nodes_modified += 1
            total_node_changes += changes
            print(f"\n📝 {label[:40]}: {changes} contractions applied")
            
            # Update in database
            if data.get('content'):
                db['agents'].update_one(
                    {'_id': ObjectId(AGENT_ID)},
                    {'$set': {f'call_flow.{i}.data.content': new_content}}
                )
            elif data.get('script'):
                db['agents'].update_one(
                    {'_id': ObjectId(AGENT_ID)},
                    {'$set': {f'call_flow.{i}.data.script': new_content}}
                )
    
    print(f"\n✅ Nodes modified: {nodes_modified}")
    print(f"✅ Total contractions applied: {total_node_changes}")
    
    # Update global prompt
    print("\n" + "="*60)
    print("🔧 UPDATING GLOBAL PROMPT WITH CONTRACTION RULE")
    print("="*60)
    
    # Apply contractions to existing global prompt
    new_global, global_changes = apply_contractions(global_prompt)
    print(f"   Contractions in existing global prompt: {global_changes}")
    
    # Check if rule already exists
    if "CONTRACTION RULES" not in new_global:
        # Find a good place to insert - after the first major section
        if "## " in new_global:
            # Insert after first paragraph or header
            lines = new_global.split('\n')
            insert_point = 0
            for j, line in enumerate(lines):
                if j > 5 and line.startswith('## '):
                    insert_point = j
                    break
            
            if insert_point > 0:
                lines.insert(insert_point, CONTRACTION_RULE)
                new_global = '\n'.join(lines)
            else:
                # Add at end
                new_global += "\n\n" + CONTRACTION_RULE
        else:
            new_global += "\n\n" + CONTRACTION_RULE
        
        print("   ✅ Contraction rule added to global prompt")
    else:
        print("   ⚠️ Contraction rule already exists")
    
    # Save updated global prompt
    db['agents'].update_one(
        {'_id': ObjectId(AGENT_ID)},
        {'$set': {'global_prompt': new_global}}
    )
    
    print("\n" + "="*60)
    print("✅ CONTRACTION CLEANUP COMPLETE")
    print("="*60)
    print(f"   Nodes updated: {nodes_modified}")
    print(f"   Contractions applied: {total_node_changes + global_changes}")
    print(f"   Global rule added: Yes")


if __name__ == '__main__':
    main()
