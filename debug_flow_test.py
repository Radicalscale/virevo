#!/usr/bin/env python3
"""
Debug Call Flow Agent Transitions
"""

import asyncio
import aiohttp
import json

BACKEND_URL = "https://tts-guardian.preview.emergentagent.com/api"

async def debug_flow():
    async with aiohttp.ClientSession() as session:
        # Get the agent
        agent_id = "a034c9ad-94a2-4abe-9cec-23296e9c09fb"
        
        # Check current flow
        print("=== Current Flow ===")
        async with session.get(f"{BACKEND_URL}/agents/{agent_id}/flow") as response:
            if response.status == 200:
                flow_data = await response.json()
                print(json.dumps(flow_data, indent=2))
            else:
                print(f"Failed to get flow: {response.status}")
        
        # Test message processing with detailed logging
        print("\n=== Testing Pricing Query ===")
        request_data = {
            "message": "How much does it cost?",
            "conversation_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hello! I can help with pricing or technical support. What do you need?"}
            ]
        }
        
        async with session.post(f"{BACKEND_URL}/agents/{agent_id}/process", json=request_data) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Response: {data}")
            else:
                print(f"Failed: {response.status} - {await response.text()}")

if __name__ == "__main__":
    asyncio.run(debug_flow())