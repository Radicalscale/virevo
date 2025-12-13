#!/usr/bin/env python3
"""
QC Testing without authentication to check endpoint availability
"""

import httpx
import asyncio
import json
import sys
import os

BACKEND_URL = "https://tts-guardian.preview.emergentagent.com"

async def test_qc_endpoints_no_auth():
    """Test QC endpoints without authentication to see what's available"""
    print("🔍 Testing QC endpoints without authentication...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test QC preset endpoint
        try:
            response = await client.post(f"{BACKEND_URL}/api/qc/test/preset/high_quality")
            print(f"QC Preset Endpoint: {response.status_code}")
            if response.status_code == 401:
                print("✅ QC endpoint exists but requires authentication (expected)")
            else:
                print(f"Response: {response.text[:200]}...")
        except Exception as e:
            print(f"❌ Error testing QC preset: {e}")
        
        # Test custom QC endpoint
        try:
            test_data = {"transcript": "Agent: Hello User: Hi"}
            response = await client.post(f"{BACKEND_URL}/api/qc/test", json=test_data)
            print(f"Custom QC Endpoint: {response.status_code}")
            if response.status_code == 401:
                print("✅ Custom QC endpoint exists but requires authentication (expected)")
            else:
                print(f"Response: {response.text[:200]}...")
        except Exception as e:
            print(f"❌ Error testing custom QC: {e}")
        
        # Test user creation to get a valid account
        try:
            signup_data = {
                "email": "qc_test_user@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
            response = await client.post(f"{BACKEND_URL}/api/auth/signup", json=signup_data)
            print(f"User Creation: {response.status_code}")
            if response.status_code == 200:
                print("✅ Created test user successfully")
                # Try to login with the new user
                login_data = {
                    "email": "qc_test_user@example.com",
                    "password": "TestPassword123!",
                    "remember_me": False
                }
                login_response = await client.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
                print(f"Login with new user: {login_response.status_code}")
                if login_response.status_code == 200:
                    print("✅ Login successful with new user")
                    cookies = login_response.cookies
                    
                    # Now test QC with authentication
                    test_data = {
                        "transcript": "Agent: Hello! How can I help you today? User: I'm interested in your services. Agent: Great! Let me tell you about our program.",
                        "metadata": {"duration_seconds": 60}
                    }
                    qc_response = await client.post(
                        f"{BACKEND_URL}/api/qc/test",
                        json=test_data,
                        cookies=cookies
                    )
                    print(f"QC Test with Auth: {qc_response.status_code}")
                    if qc_response.status_code == 200:
                        data = qc_response.json()
                        print("✅ QC analysis successful!")
                        print(f"Analysis keys: {list(data.keys())}")
                        analysis = data.get("analysis", {})
                        print(f"Analysis structure: {list(analysis.keys())}")
                    else:
                        print(f"❌ QC failed: {qc_response.text[:300]}...")
                else:
                    print(f"❌ Login failed: {login_response.text[:200]}...")
            elif response.status_code == 400 and "already registered" in response.text:
                print("ℹ️  Test user already exists, trying to login...")
                login_data = {
                    "email": "qc_test_user@example.com",
                    "password": "TestPassword123!",
                    "remember_me": False
                }
                login_response = await client.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
                print(f"Login with existing user: {login_response.status_code}")
                if login_response.status_code == 200:
                    print("✅ Login successful with existing user")
                    cookies = login_response.cookies
                    
                    # Test QC with authentication
                    test_data = {
                        "transcript": "Agent: Hello! How can I help you today? User: I'm interested in your services. Agent: Great! Let me tell you about our program.",
                        "metadata": {"duration_seconds": 60}
                    }
                    qc_response = await client.post(
                        f"{BACKEND_URL}/api/qc/test",
                        json=test_data,
                        cookies=cookies
                    )
                    print(f"QC Test with Auth: {qc_response.status_code}")
                    if qc_response.status_code == 200:
                        data = qc_response.json()
                        print("✅ QC analysis successful!")
                        print(f"Analysis keys: {list(data.keys())}")
                        analysis = data.get("analysis", {})
                        print(f"Analysis structure: {list(analysis.keys())}")
                        
                        # Check for valid scores
                        agents_with_scores = 0
                        for agent_key in ["commitment_analysis", "conversion_analysis", "excellence_analysis"]:
                            if agent_key in analysis:
                                agents_with_scores += 1
                                print(f"✅ {agent_key} present in analysis")
                            else:
                                print(f"❌ {agent_key} missing from analysis")
                        
                        print(f"Agents with results: {agents_with_scores}/3")
                    else:
                        print(f"❌ QC failed: {qc_response.text[:300]}...")
                else:
                    print(f"❌ Login failed: {login_response.text[:200]}...")
            else:
                print(f"❌ User creation failed: {response.text[:200]}...")
        except Exception as e:
            print(f"❌ Error with user creation/login: {e}")

if __name__ == "__main__":
    asyncio.run(test_qc_endpoints_no_auth())