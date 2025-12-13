#!/usr/bin/env python3
"""
QC Testing using local backend to avoid cookie domain issues
"""

import httpx
import asyncio
import json
import sys
import os

BACKEND_URL = "http://localhost:8001"

async def test_qc_with_local_backend():
    """Test QC endpoints using local backend"""
    print("🔍 Testing QC endpoints with local backend...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create a test user
        try:
            signup_data = {
                "email": "local_test_user@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
            response = await client.post(f"{BACKEND_URL}/api/auth/signup", json=signup_data)
            print(f"User Creation: {response.status_code}")
            
            if response.status_code == 400 and "already registered" in response.text:
                print("ℹ️  Test user already exists")
            elif response.status_code == 200:
                print("✅ Created test user successfully")
            
            # Login
            login_data = {
                "email": "local_test_user@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
            login_response = await client.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
            print(f"Login: {login_response.status_code}")
            
            if login_response.status_code == 200:
                print("✅ Login successful")
                cookies = login_response.cookies
                
                # Test QC with realistic transcript
                test_data = {
                    "transcript": [
                        {"role": "agent", "content": "Hi Sarah! I'm calling about your inquiry from our Facebook ad. How are you today?"},
                        {"role": "user", "content": "Oh yes, I was interested in learning more!"},
                        {"role": "agent", "content": "Great! Tell me, what specifically are you looking to achieve with your business?"},
                        {"role": "user", "content": "I need to grow my revenue. I'm stuck at the same level for months."},
                        {"role": "agent", "content": "I understand that's frustrating. Our program has helped businesses like yours achieve 2x growth in 90 days."},
                        {"role": "user", "content": "That sounds really interesting. How exactly does it work?"},
                        {"role": "agent", "content": "I'm glad you asked! We provide personalized coaching and proven frameworks."},
                        {"role": "user", "content": "Okay, what's the investment?"},
                        {"role": "agent", "content": "Great question! Our program is $5k, and we offer payment plans."},
                        {"role": "user", "content": "That makes sense. I'm interested."},
                        {"role": "agent", "content": "Excellent! Would you like to schedule a free strategy session?"},
                        {"role": "user", "content": "Yes, absolutely! When can we do this?"},
                        {"role": "agent", "content": "Perfect! How's Tuesday at 2pm?"},
                        {"role": "user", "content": "Tuesday at 2pm works great! I'll definitely be there."}
                    ],
                    "metadata": {"duration_seconds": 420}
                }
                
                print("\n🧪 Testing QC Analysis with List Format Transcript...")
                qc_response = await client.post(
                    f"{BACKEND_URL}/api/qc/test",
                    json=test_data,
                    cookies=cookies
                )
                print(f"QC Test Response: {qc_response.status_code}")
                
                if qc_response.status_code == 200:
                    data = qc_response.json()
                    print("✅ QC analysis successful!")
                    print(f"Response keys: {list(data.keys())}")
                    
                    analysis = data.get("analysis", {})
                    print(f"Analysis keys: {list(analysis.keys())}")
                    
                    # Check each agent
                    agents_checked = 0
                    agents_with_valid_scores = 0
                    
                    # Commitment Detector
                    if "commitment_analysis" in analysis:
                        agents_checked += 1
                        commitment = analysis["commitment_analysis"]
                        score = commitment.get("commitment_analysis", {}).get("linguistic_score")
                        if score is not None and isinstance(score, (int, float)):
                            agents_with_valid_scores += 1
                            print(f"✅ Commitment Detector: {score}")
                        else:
                            print(f"❌ Commitment Detector: Invalid score {score}")
                    else:
                        print("❌ Commitment Detector: Not found in analysis")
                    
                    # Conversion Pathfinder
                    if "conversion_analysis" in analysis:
                        agents_checked += 1
                        conversion = analysis["conversion_analysis"]
                        score = conversion.get("funnel_analysis", {}).get("funnel_completion")
                        if score is not None and isinstance(score, (int, float)):
                            agents_with_valid_scores += 1
                            print(f"✅ Conversion Pathfinder: {score}")
                        else:
                            print(f"❌ Conversion Pathfinder: Invalid score {score}")
                    else:
                        print("❌ Conversion Pathfinder: Not found in analysis")
                    
                    # Excellence Replicator
                    if "excellence_analysis" in analysis:
                        agents_checked += 1
                        excellence = analysis["excellence_analysis"]
                        score = excellence.get("excellence_score")
                        if score is not None and isinstance(score, (int, float)):
                            agents_with_valid_scores += 1
                            print(f"✅ Excellence Replicator: {score}")
                        else:
                            print(f"❌ Excellence Replicator: Invalid score {score}")
                    else:
                        print("❌ Excellence Replicator: Not found in analysis")
                    
                    print(f"\nSUMMARY: {agents_with_valid_scores}/{agents_checked} agents returned valid scores")
                    
                    # Check aggregated scores
                    aggregated = analysis.get("aggregated_scores", {})
                    if aggregated:
                        overall = aggregated.get("overall_quality_score")
                        print(f"Overall Quality Score: {overall}")
                    
                    # Test with string format transcript
                    print("\n🧪 Testing QC Analysis with String Format Transcript...")
                    string_transcript = "\n".join([f"{msg['role'].title()}: {msg['content']}" for msg in test_data["transcript"]])
                    
                    string_test_data = {
                        "transcript": string_transcript,
                        "metadata": {"duration_seconds": 420}
                    }
                    
                    string_qc_response = await client.post(
                        f"{BACKEND_URL}/api/qc/test",
                        json=string_test_data,
                        cookies=cookies
                    )
                    print(f"String QC Test Response: {string_qc_response.status_code}")
                    
                    if string_qc_response.status_code == 200:
                        string_data = string_qc_response.json()
                        string_analysis = string_data.get("analysis", {})
                        string_agents_with_scores = 0
                        
                        for agent_key in ["commitment_analysis", "conversion_analysis", "excellence_analysis"]:
                            if agent_key in string_analysis:
                                string_agents_with_scores += 1
                        
                        print(f"String format: {string_agents_with_scores}/3 agents returned results")
                        
                        if agents_with_valid_scores > 0 and string_agents_with_scores > 0:
                            print("\n🎉 SUCCESS: Both list and string formats work - transcript conversion is functional!")
                            return True
                        else:
                            print("\n⚠️  ISSUE: One or both formats failed")
                            return False
                    else:
                        print(f"❌ String format test failed: {string_qc_response.text[:300]}...")
                        return False
                        
                else:
                    print(f"❌ QC failed: {qc_response.text[:500]}...")
                    return False
            else:
                print(f"❌ Login failed: {login_response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    result = asyncio.run(test_qc_with_local_backend())
    sys.exit(0 if result else 1)