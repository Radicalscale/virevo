#!/usr/bin/env python3
"""
Simple Backend Test - Test basic connectivity and health
"""

import asyncio
import aiohttp
import json

BACKEND_URL = "https://missed-variable.preview.emergentagent.com/api"

async def test_basic_connectivity():
    """Test basic backend connectivity"""
    print("🔍 Testing Basic Backend Connectivity")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Health check
        try:
            async with session.get(f"{BACKEND_URL}/health", timeout=10) as response:
                print(f"Health Check: Status {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health Response: {data}")
                else:
                    text = await response.text()
                    print(f"❌ Health Error: {text}")
        except Exception as e:
            print(f"❌ Health Check Failed: {e}")
        
        # Test 2: Root endpoint
        try:
            async with session.get(f"{BACKEND_URL}/", timeout=10) as response:
                print(f"Root Endpoint: Status {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Root Response: {data}")
                else:
                    text = await response.text()
                    print(f"❌ Root Error: {text}")
        except Exception as e:
            print(f"❌ Root Endpoint Failed: {e}")
        
        # Test 3: Try agents endpoint (should get 401)
        try:
            async with session.get(f"{BACKEND_URL}/agents", timeout=10) as response:
                print(f"Agents Endpoint: Status {response.status}")
                text = await response.text()
                print(f"Response: {text[:200]}")
        except Exception as e:
            print(f"❌ Agents Endpoint Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_basic_connectivity())