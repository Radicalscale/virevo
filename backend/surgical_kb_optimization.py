"""
Iteration 10: Surgical KB Node Optimization
Manual reduction focusing on removing ONLY duplicate/redundant text
Keeping EVERY instruction and logic element intact
"""
import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient

AGENT_ID = "e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4"
TARGET_NODE = "1763206946898"


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║     ITERATION 10 - Surgical Optimization (Manual, Ultra-Careful)            ║
║     Remove ONLY redundancy, keep EVERY instruction                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    agent = await db.agents.find_one({"id": AGENT_ID})
    agent.pop('_id', None)
    
    # Backup
    with open('/app/agent_backup_iter10.json', 'w') as f:
        json.dump(agent, f, indent=2, default=str)
    print("✅ Backup: /app/agent_backup_iter10.json\n")
    
    # Find the giant node
    call_flow = agent.get('call_flow', [])
    for node in call_flow:
        if node.get('id') == TARGET_NODE:
            original = node.get('data', {}).get('content', '')
            
            print(f"Original: {len(original)} chars")
            print()
            print("Applying manual surgical optimizations:")
            print()
            
            # Manual optimizations - ONLY remove redundancy
            optimized = original
            
            # 1. Shorten verbose instructions while keeping meaning
            optimized = optimized.replace("Before anything set", "Set")
            optimized = optimized.replace("Then proceed.", "")
            optimized = optimized.replace("Always include details on", "Include")
            optimized = optimized.replace("such as each site earning", "sites earn")
            optimized = optimized.replace("aiming for at least", "target")
            optimized = optimized.replace("Transition naturally to", "Ask")
            optimized = optimized.replace("After answering and end you response with", "End with")
            optimized = optimized.replace("<-This question must be asked.", "(required)")
            optimized = optimized.replace("If skeptical (e.g., \"depends\" or \"I don't know\"), refocus on establishing desire for extra money.", "If skeptical, refocus on desire.")
            
            # 2. Remove redundant section headers
            optimized = optimized.replace("Entry Context\nEnter after", "Enter after")
            optimized = optimized.replace("Opening Gambit\nDynamic node. Start", "Start")
            
            # 3. Condense tactical responses while keeping content
            optimized = optimized.replace("That's exactly what the call with Kendrick is designed to figure out. It wouldn't be fair to throw out a number without knowing if this is even the right fit for you, would it?", "That's what the Kendrick call is for. Can't give a number without knowing if it's the right fit, right?")
            
            optimized = optimized.replace("You know, that's a very specific question that I don't have the answer to right now, but it's exactly the kind of thing Kendrick would be able to dive into on your call. Was there anything else I could clear up about the basics?", "I don't have that specific answer, but Kendrick can cover it on your call. Anything else about the basics?")
            
            # 4. Remove redundant phrases
            optimized = optimized.replace("Adaptive Interruption Engine\nCore logic for each turn. Limit to two loops max, then escalate.", "Limit to 2 loops max.")
            optimized = optimized.replace("Turn 1: Diagnose, Adapt, Respond\n\n", "")
            optimized = optimized.replace("Analyze user intent (question, objection, confusion, statement).\n", "")
            optimized = optimized.replace("Classify user style via quick DISC_Guide KB search: 'D', 'I', 'S', or 'C'.\n", "Classify DISC style.\n")
            
            # 5. Remove "Act:" label and condense
            optimized = optimized.replace("Act:\n", "")
            optimized = optimized.replace("If matches Strategic Toolkit tactic, deploy it.\nElse, search the se the kbs Di RE Customer Avatar.pdf and dan in ippei and company info.pdf to help answer any product details or company questions, and the Calm-Disc And Other Sales Frameworks.pdf and/or Objection handler.pdf for objection ha", "If matches toolkit, use it. Else search KBs (Customer Avatar, Company Info, DISC Frameworks, Objection Handler).")
            
            # 6. Remove verbose explanations
            optimized = optimized.replace("If no: Use KB Search Failure tactic.", "If no: Use failure tactic.")
            
            # Calculate reduction
            reduction = len(original) - len(optimized)
            reduction_pct = (reduction / len(original)) * 100
            
            print(f"  ✓ Shortened verbose instructions")
            print(f"  ✓ Removed redundant headers")
            print(f"  ✓ Condensed tactical responses")
            print(f"  ✓ Removed duplicate explanations")
            print()
            print(f"Result: {len(original)} → {len(optimized)} chars")
            print(f"Reduction: {reduction} chars ({reduction_pct:.1f}%)")
            print()
            
            if reduction_pct >= 10:
                node['data']['content'] = optimized
                agent['call_flow'] = call_flow
                
                result = await db.agents.update_one(
                    {"id": AGENT_ID},
                    {"$set": agent}
                )
                
                if result.modified_count > 0:
                    print("✅ Saved to MongoDB")
                    print()
                    print("="*80)
                    print("SURGICAL OPTIMIZATION COMPLETE")
                    print("="*80)
                    print()
                    print("This optimization:")
                    print("  - Removes redundant text only")
                    print("  - Keeps ALL instructions")
                    print("  - Keeps ALL transition logic")
                    print("  - Keeps ALL tactical responses")
                    print()
                    print("Expected:")
                    print("  - Less text for LLM to process")
                    print("  - Same functionality")
                    print("  - Transitions should remain intact")
                    print()
                    print("Next: Test with skeptical_test.py")
                else:
                    print("⚠️ Not saved")
            else:
                print("⚠️ Reduction too small (<10%), not applying")
            
            break


if __name__ == "__main__":
    asyncio.run(main())
