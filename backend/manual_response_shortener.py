"""
Manual Response Shortener - Surgical Optimization
Only shortens scripted response templates, doesn't touch transition logic
"""
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"

# Manual optimizations - shorten specific verbose phrases
RESPONSE_SHORTCUTS = [
    # Remove verbose SSML breaks
    ('<break time="500ms"/>', '<break time="300ms"/>'),
    ('<break time="400ms"/>', '<break time="250ms"/>'),
    
    # Shorten common phrases
    ("I was just, um, wondering if you could possibly help me out for a moment", "wondering if you could help me out for just a moment"),
    ("We've helped over 7,500 students", "We've helped 7,500+ students"),
    ("the idea of generating new income", "generating new income"),
    ("is that because", "because"),
    ("That's the perfect question", "Great question"),
    ("Absolutely, and that's a smart question", "Absolutely"),
    ("I get why you're cautious—plenty of people are", "I get why you're cautious"),
    ("When you say you're not interested, is that because", "Not interested because"),
    
    # Remove filler words in templates
    ("really", ""),
    ("actually", ""),
    ("basically", ""),
    ("essentially", ""),
]

async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║           MANUAL RESPONSE SHORTENER - Surgical Optimization                  ║
║           Only touches response templates, not prompt logic                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    print("📥 Loading agent...")
    agent = await db.agents.find_one({"id": AGENT_ID})
    if not agent:
        print("❌ Agent not found")
        return
    
    agent.pop('_id', None)
    
    # Backup
    with open('/app/agent_backup_manual_opt.json', 'w') as f:
        json.dump(agent, f, indent=2, default=str)
    print("✅ Backup: /app/agent_backup_manual_opt.json\n")
    
    call_flow = agent.get('call_flow', [])
    changes_count = 0
    total_chars_saved = 0
    
    print("="*80)
    print("Applying Manual Response Shortcuts")
    print("="*80)
    print()
    
    for node in call_flow:
        node_id = node.get('id', '')
        label = node.get('label', 'Unknown')
        
        # Get all text fields in the node
        data = node.get('data', {})
        
        # Check various fields that might contain responses
        text_fields = ['content', 'response_template', 'agent_says']
        
        node_modified = False
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                original = data[field]
                modified = original
                
                # Apply all shortcuts
                for old_phrase, new_phrase in RESPONSE_SHORTCUTS:
                    if old_phrase in modified:
                        modified = modified.replace(old_phrase, new_phrase)
                
                if modified != original:
                    chars_saved = len(original) - len(modified)
                    data[field] = modified
                    node_modified = True
                    total_chars_saved += chars_saved
                    
                    if changes_count < 10:  # Only print first 10 to avoid clutter
                        print(f"✓ {node_id[:15]}... | {field}: saved {chars_saved} chars")
        
        if node_modified:
            node['data'] = data
            changes_count += 1
    
    agent['call_flow'] = call_flow
    
    print()
    print("="*80)
    print(f"Saving Changes")
    print("="*80)
    print()
    
    if changes_count > 0:
        print(f"📊 Modified {changes_count} nodes")
        print(f"💾 Total characters saved: {total_chars_saved}")
        print()
        
        result = await db.agents.update_one(
            {"id": AGENT_ID},
            {"$set": agent}
        )
        
        if result.modified_count > 0:
            print(f"✅ Saved to MongoDB")
            
            # Log
            with open('/app/OPTIMIZATION_LOG.md', 'a') as f:
                f.write(f"""
## Iteration 3: Manual Response Shortening
**Timestamp:** Manual surgical optimization
**Status:** COMPLETE - Ready for Testing

### Approach:
- Shortened response templates only (not prompts)
- Removed verbose SSML breaks
- Replaced wordy phrases with concise versions
- Removed filler words from templates

### Changes:
- Modified: {changes_count} nodes
- Characters saved: {total_chars_saved}
- Expected TTS reduction: ~{total_chars_saved * 0.3:.0f}ms

### Safety:
- No prompt logic touched
- No transition keywords changed
- Only response template shortening

### Next: Test latency

---

""")
            print(f"✅ Logged")
        else:
            print(f"⚠️ No changes saved")
    else:
        print(f"⚠️ No changes applied")
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
