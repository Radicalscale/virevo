#!/usr/bin/env python3
"""
Test QC endpoints via HTTP to verify the transcript conversion fix
"""

import httpx
import asyncio
import json
import sys
import os

BACKEND_URL = "http://localhost:8001"

async def test_qc_fix_via_http():
    """Test the QC transcript conversion fix via HTTP endpoints"""
    print("🔬 TESTING QC TRANSCRIPT CONVERSION FIX VIA HTTP")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create and login with test user
        try:
            # Try to create user
            signup_data = {
                "email": "qc_fix_test@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
            await client.post(f"{BACKEND_URL}/api/auth/signup", json=signup_data)
            
            # Login
            login_data = {
                "email": "qc_fix_test@example.com", 
                "password": "TestPassword123!",
                "remember_me": False
            }
            login_response = await client.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
            
            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.status_code}")
                return False
            
            # Extract token from response and use it in Authorization header instead of cookies
            # This bypasses the domain issue
            data = login_response.json()
            # We need to get the token from the cookie since it's httpOnly
            cookies = login_response.cookies
            auth_token = cookies.get("access_token")
            
            if not auth_token:
                print("❌ No auth token received")
                return False
            
            print("✅ Authentication successful")
            
            # Test 1: List format transcript (the bug scenario)
            print("\n🧪 Test 1: List Format Transcript")
            list_transcript = [
                {"role": "agent", "content": "Hi! I'm calling about your inquiry. How are you today?"},
                {"role": "user", "content": "Oh yes, I was interested in learning more!"},
                {"role": "agent", "content": "Great! What are you looking to achieve?"},
                {"role": "user", "content": "I need to grow my revenue."},
                {"role": "agent", "content": "Our program helps businesses achieve 2x growth."},
                {"role": "user", "content": "That sounds interesting. How does it work?"},
                {"role": "agent", "content": "We provide coaching and frameworks."},
                {"role": "user", "content": "What's the investment?"},
                {"role": "agent", "content": "The program is $5k with payment plans."},
                {"role": "user", "content": "That makes sense. I'm interested."},
                {"role": "agent", "content": "Would you like to schedule a strategy session?"},
                {"role": "user", "content": "Yes, absolutely!"},
                {"role": "agent", "content": "How's Tuesday at 2pm?"},
                {"role": "user", "content": "Tuesday works great!"}
            ]
            
            test_data = {
                "transcript": list_transcript,
                "metadata": {"duration_seconds": 300}
            }
            
            # Use cookies for authentication
            response = await client.post(
                f"{BACKEND_URL}/api/qc/test",
                json=test_data,
                cookies=cookies
            )
            
            print(f"List format response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                analysis = data.get("analysis", {})
                
                # Count agents with results
                agents_with_results = 0
                agent_scores = {}
                
                if "commitment_analysis" in analysis:
                    agents_with_results += 1
                    commitment = analysis["commitment_analysis"]
                    score = commitment.get("commitment_analysis", {}).get("linguistic_score")
                    agent_scores["Commitment"] = score
                
                if "conversion_analysis" in analysis:
                    agents_with_results += 1
                    conversion = analysis["conversion_analysis"]
                    score = conversion.get("funnel_analysis", {}).get("funnel_completion")
                    agent_scores["Conversion"] = score
                
                if "excellence_analysis" in analysis:
                    agents_with_results += 1
                    excellence = analysis["excellence_analysis"]
                    score = excellence.get("excellence_score")
                    agent_scores["Excellence"] = score
                
                print(f"✅ List format: {agents_with_results}/3 agents returned results")
                for agent, score in agent_scores.items():
                    if score is not None:
                        print(f"  {agent}: {score}")
                
                list_success = agents_with_results >= 2
                
            else:
                print(f"❌ List format failed: {response.text[:300]}...")
                list_success = False
            
            # Test 2: String format transcript
            print("\n🧪 Test 2: String Format Transcript")
            string_transcript = "\n".join([f"{msg['role'].title()}: {msg['content']}" for msg in list_transcript])
            
            string_test_data = {
                "transcript": string_transcript,
                "metadata": {"duration_seconds": 300}
            }
            
            string_response = await client.post(
                f"{BACKEND_URL}/api/qc/test",
                json=string_test_data,
                cookies=cookies
            )
            
            print(f"String format response: {string_response.status_code}")
            
            if string_response.status_code == 200:
                string_data = string_response.json()
                string_analysis = string_data.get("analysis", {})
                
                string_agents_with_results = 0
                if "commitment_analysis" in string_analysis:
                    string_agents_with_results += 1
                if "conversion_analysis" in string_analysis:
                    string_agents_with_results += 1
                if "excellence_analysis" in string_analysis:
                    string_agents_with_results += 1
                
                print(f"✅ String format: {string_agents_with_results}/3 agents returned results")
                string_success = string_agents_with_results >= 2
                
            else:
                print(f"❌ String format failed: {string_response.text[:300]}...")
                string_success = False
            
            # Summary
            print(f"\n📊 TRANSCRIPT CONVERSION FIX TEST RESULTS:")
            print(f"List Format: {'✅ PASS' if list_success else '❌ FAIL'}")
            print(f"String Format: {'✅ PASS' if string_success else '❌ FAIL'}")
            
            if list_success and string_success:
                print("\n🎉 SUCCESS: Transcript conversion fix is working!")
                print("✅ Both list and string formats work correctly")
                return True
            elif string_success and not list_success:
                print("\n⚠️  PARTIAL: String works, list format still has issues")
                print("❌ Transcript conversion fix may not be complete")
                return False
            else:
                print("\n❌ FAILURE: QC analysis not working properly")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    result = asyncio.run(test_qc_fix_via_http())
    sys.exit(0 if result else 1)