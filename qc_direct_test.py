#!/usr/bin/env python3
"""
Direct QC Agent Testing - Bypass HTTP authentication to test core functionality
This tests the QC agents directly to verify the transcript conversion fix
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add backend to path
sys.path.append('/app/backend')

from qc_agents.orchestrator import QCAgentOrchestrator

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db_name = os.environ.get('DB_NAME', 'test_database')

async def test_qc_agents_directly():
    """Test QC agents directly without HTTP layer"""
    print("🔬 DIRECT QC AGENT TESTING - TRANSCRIPT CONVERSION VERIFICATION")
    print("=" * 70)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Use OpenAI API key from environment
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found in environment")
        return False
    
    print(f"✅ Using OpenAI API key: {api_key[:10]}...")
    
    # Initialize orchestrator
    orchestrator = QCAgentOrchestrator(db, api_key)
    
    # Test user ID
    test_user_id = "test_user_direct_qc"
    
    print("\n🧪 Test 1: List Format Transcript (The Bug Scenario)")
    
    # Test with list format transcript (the original bug)
    list_transcript = [
        {"role": "agent", "content": "Hi Sarah! I'm calling about your inquiry from our Facebook ad. How are you today?"},
        {"role": "user", "content": "Oh yes, I was interested in learning more!"},
        {"role": "agent", "content": "Great! Tell me, what specifically are you looking to achieve with your business?"},
        {"role": "user", "content": "I need to grow my revenue. I'm stuck at the same level for months."},
        {"role": "agent", "content": "I understand that's frustrating. Our program has helped businesses like yours achieve 2x growth in 90 days. For your specific situation, this means you could see an additional $50k in revenue."},
        {"role": "user", "content": "That sounds really interesting. How exactly does it work?"},
        {"role": "agent", "content": "I'm glad you asked! We provide personalized coaching, proven frameworks, and weekly accountability. The benefit you'll see is not just revenue growth, but sustainable systems."},
        {"role": "user", "content": "Okay, what's the investment?"},
        {"role": "agent", "content": "Great question - it shows you're serious! Our program is $5k, and we offer payment plans. Given the potential $50k increase, it pays for itself quickly."},
        {"role": "user", "content": "That makes sense. I'm interested."},
        {"role": "agent", "content": "Excellent! Would you like to schedule a free strategy session to discuss your specific goals and see if this is the right fit?"},
        {"role": "user", "content": "Yes, absolutely! When can we do this?"},
        {"role": "agent", "content": "Perfect! I'm really excited to help you. How's Tuesday at 2pm?"},
        {"role": "user", "content": "Tuesday at 2pm works great! I'll definitely be there."}
    ]
    
    metadata = {
        'duration_seconds': 420,
        'call_hour': 14,
        'day_of_week': 2
    }
    
    try:
        # This should trigger the transcript conversion from list to string
        print("📝 Testing with list format transcript...")
        result1 = await orchestrator.analyze_call(
            call_id="test_list_format",
            user_id=test_user_id,
            transcript=list_transcript,  # List format - should be converted
            metadata=metadata
        )
        
        print(f"✅ List format analysis completed")
        print(f"Result keys: {list(result1.keys())}")
        
        # Check if we have analysis results
        agents_with_results = 0
        agent_scores = {}
        
        if "commitment_analysis" in result1:
            agents_with_results += 1
            commitment = result1["commitment_analysis"]
            score = commitment.get("commitment_analysis", {}).get("linguistic_score")
            agent_scores["Commitment Detector"] = score
            print(f"✅ Commitment Detector: {score}")
        
        if "conversion_analysis" in result1:
            agents_with_results += 1
            conversion = result1["conversion_analysis"]
            score = conversion.get("funnel_analysis", {}).get("funnel_completion")
            agent_scores["Conversion Pathfinder"] = score
            print(f"✅ Conversion Pathfinder: {score}")
        
        if "excellence_analysis" in result1:
            agents_with_results += 1
            excellence = result1["excellence_analysis"]
            score = excellence.get("excellence_score")
            agent_scores["Excellence Replicator"] = score
            print(f"✅ Excellence Replicator: {score}")
        
        print(f"Agents with results: {agents_with_results}/3")
        
        # Check aggregated scores
        aggregated = result1.get("aggregated_scores", {})
        if aggregated:
            overall = aggregated.get("overall_quality_score")
            print(f"Overall Quality Score: {overall}")
        
        list_success = agents_with_results >= 2  # At least 2 agents should work
        
    except Exception as e:
        print(f"❌ List format test failed: {e}")
        import traceback
        traceback.print_exc()
        list_success = False
    
    print("\n🧪 Test 2: String Format Transcript (Expected Format)")
    
    # Convert list to string format
    string_transcript = "\n".join([f"{msg['role'].title()}: {msg['content']}" for msg in list_transcript])
    
    try:
        print("📝 Testing with string format transcript...")
        result2 = await orchestrator.analyze_call(
            call_id="test_string_format",
            user_id=test_user_id,
            transcript=string_transcript,  # String format
            metadata=metadata
        )
        
        print(f"✅ String format analysis completed")
        
        # Check if we have analysis results
        string_agents_with_results = 0
        
        if "commitment_analysis" in result2:
            string_agents_with_results += 1
        if "conversion_analysis" in result2:
            string_agents_with_results += 1
        if "excellence_analysis" in result2:
            string_agents_with_results += 1
        
        print(f"String format agents with results: {string_agents_with_results}/3")
        
        string_success = string_agents_with_results >= 2
        
    except Exception as e:
        print(f"❌ String format test failed: {e}")
        import traceback
        traceback.print_exc()
        string_success = False
    
    print("\n📊 DIRECT QC TESTING SUMMARY:")
    print(f"List Format Test: {'✅ PASS' if list_success else '❌ FAIL'}")
    print(f"String Format Test: {'✅ PASS' if string_success else '❌ FAIL'}")
    
    if list_success and string_success:
        print("\n🎉 SUCCESS: QC agents working with both list and string formats!")
        print("✅ Transcript conversion fix is working correctly")
        return True
    elif string_success and not list_success:
        print("\n⚠️  PARTIAL SUCCESS: String format works, list format has issues")
        print("❌ Transcript conversion may not be working properly")
        return False
    elif list_success and not string_success:
        print("\n⚠️  UNEXPECTED: List format works but string format doesn't")
        return False
    else:
        print("\n❌ FAILURE: Both formats failed - QC agents not working")
        return False
    
    await client.close()

if __name__ == "__main__":
    result = asyncio.run(test_qc_agents_directly())
    sys.exit(0 if result else 1)