#!/usr/bin/env python3
"""
Transition Validation Script
Compares baseline vs optimized to ensure conversation paths haven't changed
"""
import json
import sys

def validate_transitions(baseline_file, optimized_file):
    # Load both files
    with open(baseline_file, 'r') as f:
        baseline = json.load(f)
    
    with open(optimized_file, 'r') as f:
        optimized = json.load(f)
    
    print("="*80)
    print("TRANSITION VALIDATION - CRITICAL CHECK")
    print("="*80)
    print()
    
    # Track results
    total_messages = 0
    total_failures = 0
    failures_by_conversation = {}
    
    # Compare each conversation
    for b_conv, o_conv in zip(baseline['conversations'], optimized['conversations']):
        conv_name = b_conv['name']
        conv_failures = []
        
        # Compare each message
        for b_msg, o_msg in zip(b_conv['messages'], o_conv['messages']):
            total_messages += 1
            
            user_msg = b_msg['message']
            b_node = b_msg.get('current_node', 'Unknown')
            o_node = o_msg.get('current_node', 'Unknown')
            
            if b_node != o_node:
                total_failures += 1
                conv_failures.append({
                    'message': user_msg,
                    'expected': b_node,
                    'got': o_node
                })
        
        if conv_failures:
            failures_by_conversation[conv_name] = conv_failures
    
    # Print results
    if total_failures == 0:
        print("✅" * 20)
        print()
        print(" " * 20 + "ALL TRANSITIONS MATCH!")
        print()
        print("✅" * 20)
        print()
        print(f"  {total_messages}/{total_messages} transitions correct (100%)")
        print()
        print("  🎉 OPTIMIZATION IS SAFE TO KEEP")
        print()
        print("  Next steps:")
        print("  1. Analyze latency improvement")
        print("  2. Investigate why LLM time increased")
        print("  3. Decide on next optimization iteration")
        return True
    
    else:
        print("❌" * 20)
        print()
        print(" " * 15 + "TRANSITION FAILURES DETECTED")
        print()
        print("❌" * 20)
        print()
        print(f"  Failures: {total_failures}/{total_messages} ({(total_failures/total_messages)*100:.1f}%)")
        print()
        
        # Show failures by conversation
        for conv_name, failures in failures_by_conversation.items():
            print(f"\n  Conversation: {conv_name}")
            print(f"  Failures: {len(failures)}")
            print()
            
            for failure in failures[:5]:
                print(f"    Message: \"{failure['message']}\"")
                print(f"    Expected: {failure['expected']}")
                print(f"    Got:      {failure['got']}")
                print()
            
            if len(failures) > 5:
                print(f"    ... and {len(failures) - 5} more failures")
                print()
        
        print()
        print("  🚨 CRITICAL - MUST REVERT OPTIMIZATION")
        print()
        print("  Rollback command:")
        print("  cd /app/backend && python3 << 'EOF'")
        print("import asyncio, json, os")
        print("from motor.motor_asyncio import AsyncIOMotorClient")
        print()
        print("async def rollback():")
        print("    with open('/app/agent_backup_pre_optimization.json', 'r') as f:")
        print("        agent = json.load(f)")
        print("    mongo_url = os.environ.get('MONGO_URL')")
        print("    client = AsyncIOMotorClient(mongo_url)")
        print("    db = client['test_database']")
        print("    result = await db.agents.update_one(")
        print("        {'id': 'e1f8ec18-fa7a-4da3-aa2b-3deb7723abb4'},")
        print("        {'$set': agent}")
        print("    )")
        print("    print(f'Rollback complete: {result.modified_count} updated')")
        print()
        print("asyncio.run(rollback())")
        print("EOF")
        return False
    
    print("="*80)


if __name__ == "__main__":
    baseline_file = '/app/webhook_latency_test_20251124_134637.json'
    optimized_file = '/app/webhook_latency_test_20251124_135800.json'
    
    print(f"Baseline:  {baseline_file}")
    print(f"Optimized: {optimized_file}")
    print()
    
    success = validate_transitions(baseline_file, optimized_file)
    sys.exit(0 if success else 1)
