import asyncio
import os
import sys

# Add project root to path
sys.path.append("/Users/kendrickbowman/Downloads/Andro-main")

from backend.calling_service import CallingService
from backend.redis_service import RedisService

# Mock MongoDB service
class MockMongoService:
    def get_agent(self, agent_id):
        return {
            "_id": agent_id,
            "systemPrompt": "You are a helpful assistant.",
            "name": "Test Agent"
        }

async def reproduce_bug():
    print("--- Reproducing Auto-Transition Bug ---")
    
    # Mock services
    redis_service = RedisService()
    mongo_service = MockMongoService()
    calling_service = CallingService(redis_service, mongo_service)
    
    # Define the "Greeting" node
    greeting_node = {
        "id": "node_greeting",
        "type": "speak",
        "text": "Kendrick?",
        "transitions": [
            {
                "condition": "Confirms name (Yes|Speaking|This is he/she) OR Greeting",
                "nextNode": "node_intro"
            }
        ]
    }
    
    # Define the "Intro" node (target)
    intro_node = {
        "id": "node_intro",
        "type": "speak",
        "text": "This is Jake from..."
    }
    
    flow_nodes = [greeting_node, intro_node]
    
    # Simulation 1: User says "Hello" (Should NOT transition if strict, but currently DOES)
    print("\nTest Case 1: User says 'Hello'")
    user_message = "Hello"
    calling_service.conversation_history = [
        {"role": "assistant", "content": "Kendrick?"}
    ]
    
    # Manually run _follow_transition logic (mocking the LLM part or running it if keys exist)
    # Since we can't easily mock the OpenAI call inside without patching, 
    # and we want to see the REAL behavior, we'll try to run it.
    # Note: This requires OPENAI_API_KEY env var.
    
    if "OPENAI_API_KEY" not in os.environ:
        print("⚠️ OPENAI_API_KEY not found. Cannot run actual LLM transition.")
        # We will assume the behavior based on logs, but let's try to set a dummy key if needed
        # or just print what we WOUL D do.
        print("Skipping actual LLM call. Please run with API key for live reproduction.")
        return

    try:
        result = await calling_service._follow_transition(
            current_node=greeting_node,
            user_message=user_message,
            flow_nodes=flow_nodes
        )
        
        print(f"Result for 'Hello': {result}")
        if result and result.get("next_node_id") == "node_intro":
            print("❌ BUG REPRODUCED: Transitioned to Intro on 'Hello'")
        else:
            print("✅ Correct behavior: Did not transition on 'Hello'")
            
    except Exception as e:
        print(f"Error running transition: {e}")

    # Simulation 2: User says "Yes" (Should transition)
    print("\nTest Case 2: User says 'Yes'")
    user_message = "Yes"
    
    try:
        result = await calling_service._follow_transition(
            current_node=greeting_node,
            user_message=user_message,
            flow_nodes=flow_nodes
        )
        
        print(f"Result for 'Yes': {result}")
        if result and result.get("next_node_id") == "node_intro":
            print("✅ Correct behavior: Transitioned to Intro on 'Yes'")
        else:
            print("❌ Issue: Did not transition on 'Yes'")
            
    except Exception as e:
        print(f"Error running transition: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce_bug())
