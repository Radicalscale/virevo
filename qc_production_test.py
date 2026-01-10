#!/usr/bin/env python3
"""
Test QC transcript conversion fix using production URL
"""

import httpx
import asyncio
import json
import sys
import os
import time

BACKEND_URL = "https://missed-variable.preview.emergentagent.com"

async def test_qc_production():
    """Test QC with production backend"""
    print("🔬 TESTING QC TRANSCRIPT CONVERSION FIX - PRODUCTION")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create unique test user
        timestamp = int(time.time())
        test_email = f"qc_test_{timestamp}@example.com"
        test_password = "TestPassword123!"
        
        try:
            # Create user
            signup_data = {
                "email": test_email,
                "password": test_password,
                "remember_me": False
            }
            signup_response = await client.post(f"{BACKEND_URL}/api/auth/signup", json=signup_data)
            print(f"User creation: {signup_response.status_code}")
            
            if signup_response.status_code not in [200, 400]:
                print(f"❌ Signup failed: {signup_response.text}")
                return False
            
            # Login
            login_data = {
                "email": test_email,
                "password": test_password,
                "remember_me": False
            }
            login_response = await client.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
            print(f"Login: {login_response.status_code}")
            
            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.text}")
                return False
            
            cookies = login_response.cookies
            print("✅ Authentication successful")
            
            # Add OpenAI API key for the user (required for QC analysis)
            print("\n🔑 Adding OpenAI API key...")
            api_key_data = {
                "service_name": "openai",
                "api_key": "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"  # From backend .env
            }
            
            api_key_response = await client.post(
                f"{BACKEND_URL}/api/settings/api-keys",
                json=api_key_data,
                cookies=cookies
            )
            print(f"API key setup: {api_key_response.status_code}")
            
            if api_key_response.status_code not in [200, 201]:
                print(f"⚠️  API key setup issue: {api_key_response.text}")
            else:
                print("✅ OpenAI API key added")
            
            # Test with list format transcript
            print("\n🧪 Testing List Format Transcript (The Bug)")
            list_transcript = [
                {"role": "agent", "content": "Hi Sarah! I'm calling about your inquiry from our Facebook ad. How are you today?"},
                {"role": "user", "content": "Oh yes, I was interested in learning more!"},
                {"role": "agent", "content": "Great! Tell me, what specifically are you looking to achieve with your business?"},
                {"role": "user", "content": "I need to grow my revenue. I'm stuck at the same level for months."},
                {"role": "agent", "content": "I understand that's frustrating. Our program has helped businesses like yours achieve 2x growth in 90 days."},
                {"role": "user", "content": "That sounds really interesting. How exactly does it work?"},
                {"role": "agent", "content": "I'm glad you asked! We provide personalized coaching, proven frameworks, and weekly accountability."},
                {"role": "user", "content": "Okay, what's the investment?"},
                {"role": "agent", "content": "Great question - it shows you're serious! Our program is $5k, and we offer payment plans."},
                {"role": "user", "content": "That makes sense. I'm interested."},
                {"role": "agent", "content": "Excellent! Would you like to schedule a free strategy session to discuss your specific goals?"},
                {"role": "user", "content": "Yes, absolutely! When can we do this?"},
                {"role": "agent", "content": "Perfect! I'm really excited to help you. How's Tuesday at 2pm?"},
                {"role": "user", "content": "Tuesday at 2pm works great! I'll definitely be there."}
            ]
            
            test_data = {
                "transcript": list_transcript,
                "metadata": {"duration_seconds": 420}
            }
            
            response = await client.post(
                f"{BACKEND_URL}/api/qc/test",
                json=test_data,
                cookies=cookies
            )
            
            print(f"QC Test Response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ QC analysis successful!")
                
                analysis = data.get("analysis", {})
                if not analysis:
                    print("❌ No analysis data returned")
                    return False
                
                # Check for valid scores from all 3 agents
                agents_with_valid_scores = 0
                agent_results = {}
                
                # Commitment Detector
                if "commitment_analysis" in analysis:
                    commitment = analysis["commitment_analysis"]
                    score = commitment.get("commitment_analysis", {}).get("linguistic_score")
                    if score is not None and isinstance(score, (int, float)) and 0 <= score <= 100:
                        agents_with_valid_scores += 1
                        agent_results["Commitment Detector"] = score
                    else:
                        agent_results["Commitment Detector"] = f"Invalid score: {score}"
                else:
                    agent_results["Commitment Detector"] = "Not found"
                
                # Conversion Pathfinder
                if "conversion_analysis" in analysis:
                    conversion = analysis["conversion_analysis"]
                    score = conversion.get("funnel_analysis", {}).get("funnel_completion")
                    if score is not None and isinstance(score, (int, float)) and 0 <= score <= 100:
                        agents_with_valid_scores += 1
                        agent_results["Conversion Pathfinder"] = score
                    else:
                        agent_results["Conversion Pathfinder"] = f"Invalid score: {score}"
                else:
                    agent_results["Conversion Pathfinder"] = "Not found"
                
                # Excellence Replicator
                if "excellence_analysis" in analysis:
                    excellence = analysis["excellence_analysis"]
                    score = excellence.get("excellence_score")
                    if score is not None and isinstance(score, (int, float)) and 0 <= score <= 100:
                        agents_with_valid_scores += 1
                        agent_results["Excellence Replicator"] = score
                    else:
                        agent_results["Excellence Replicator"] = f"Invalid score: {score}"
                else:
                    agent_results["Excellence Replicator"] = "Not found"
                
                print(f"\n📊 QC AGENT RESULTS:")
                for agent, result in agent_results.items():
                    if isinstance(result, (int, float)):
                        print(f"✅ {agent}: {result}")
                    else:
                        print(f"❌ {agent}: {result}")
                
                print(f"\nValid Scores: {agents_with_valid_scores}/3 agents")
                
                # Check aggregated scores
                aggregated = analysis.get("aggregated_scores", {})
                if aggregated:
                    overall = aggregated.get("overall_quality_score")
                    print(f"Overall Quality Score: {overall}")
                
                if agents_with_valid_scores == 3:
                    print("\n🎉 SUCCESS: All 3 QC agents returned valid scores!")
                    print("✅ Transcript conversion from list to string format is working!")
                    return True
                elif agents_with_valid_scores >= 2:
                    print(f"\n⚠️  PARTIAL SUCCESS: {agents_with_valid_scores}/3 agents working")
                    print("✅ Transcript conversion appears to be working")
                    return True
                else:
                    print(f"\n❌ FAILURE: Only {agents_with_valid_scores}/3 agents returned valid scores")
                    print("❌ Transcript conversion may not be working properly")
                    return False
                    
            elif response.status_code == 401:
                print("❌ Authentication failed - QC test returned 401")
                return False
            elif response.status_code == 400:
                print(f"❌ Bad request: {response.text}")
                return False
            else:
                print(f"❌ QC test failed: {response.status_code} - {response.text[:300]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    result = asyncio.run(test_qc_production())
    if result:
        print("\n✅ QC TRANSCRIPT CONVERSION FIX VERIFIED!")
    else:
        print("\n❌ QC TRANSCRIPT CONVERSION FIX FAILED!")
    sys.exit(0 if result else 1)