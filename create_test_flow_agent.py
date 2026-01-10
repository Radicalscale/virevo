#!/usr/bin/env python3
"""
Create a test call flow agent with 2 different paths for testing Telnyx integration
"""
import requests
import json
import uuid

BACKEND_URL = "https://missed-variable.preview.emergentagent.com"

def create_call_flow_agent():
    """Create a call flow agent with 2 paths"""
    
    # Create the agent
    agent_data = {
        "name": "Telnyx Test Flow Agent",
        "description": "Test agent for demonstrating call flow with 2 different paths",
        "agent_type": "call_flow",
        "model": "gpt-4-turbo",
        "voice": "Rachel",
        "initial_message": "Testing flow transitions",
        "system_prompt": "You are a helpful assistant for a company."
    }
    
    print("📝 Creating call flow agent...")
    response = requests.post(f"{BACKEND_URL}/api/agents", json=agent_data)
    
    if response.status_code != 200:
        print(f"❌ Error creating agent: {response.status_code} - {response.text}")
        return None
    
    agent = response.json()
    agent_id = agent["id"]
    print(f"✅ Agent created: {agent_id}")
    print(f"   Name: {agent['name']}")
    
    # Generate node IDs
    greeting_id = str(uuid.uuid4())
    sales_id = str(uuid.uuid4())
    support_id = str(uuid.uuid4())
    sales_end_id = str(uuid.uuid4())
    support_end_id = str(uuid.uuid4())
    
    # Create the complete flow
    print("\n📊 Creating complete flow...")
    
    flow = [
        {
            "id": greeting_id,
            "type": "press_digit",
            "label": "Main Menu",
            "data": {
                "prompt": "Thank you for calling. Press 1 for Sales information, or Press 2 for Technical Support.",
                "digit_mappings": {
                    "1": sales_id,
                    "2": support_id
                }
            }
        },
        {
            "id": sales_id,
            "type": "conversation",
            "label": "Sales Information",
            "data": {
                "prompt": "script",
                "script": "You've reached our Sales department. Our premium plan is $99 per month and includes all features. Thank you for your interest!",
                "prompt_type": "script",
                "transitions": [
                    {
                        "to_node_id": sales_end_id,
                        "condition": "After sales message"
                    }
                ]
            }
        },
        {
            "id": support_id,
            "type": "conversation",
            "label": "Technical Support",
            "data": {
                "prompt": "script",
                "script": "You've reached Technical Support. We're here to help with any issues. Our support team is available 24/7.",
                "prompt_type": "script",
                "transitions": [
                    {
                        "to_node_id": support_end_id,
                        "condition": "After support message"
                    }
                ]
            }
        },
        {
            "id": sales_end_id,
            "type": "ending",
            "label": "Sales End",
            "data": {
                "script": "Thank you for your interest in our sales offerings. Have a great day! Goodbye."
            }
        },
        {
            "id": support_end_id,
            "type": "ending",
            "label": "Support End",
            "data": {
                "script": "Thank you for contacting support. We're here if you need us. Goodbye!"
            }
        }
    ]
    
    # Update agent with flow
    response = requests.put(f"{BACKEND_URL}/api/agents/{agent_id}/flow", json=flow)
    
    if response.status_code == 200:
        print("✅ Flow created successfully!")
    else:
        print(f"❌ Error creating flow: {response.status_code} - {response.text}")
        return None
    
    print("\n" + "="*70)
    print("✅ CALL FLOW AGENT CREATED SUCCESSFULLY!")
    print("="*70)
    print(f"Agent ID: {agent_id}")
    print(f"Agent Name: {agent['name']}")
    print("\nFlow Structure:")
    print("  Main Menu (Press Digit)")
    print("    ├─ Press 1 → Sales Information → Sales End")
    print("    └─ Press 2 → Technical Support → Support End")
    print("="*70)
    
    return agent_id

if __name__ == "__main__":
    agent_id = create_call_flow_agent()
    if agent_id:
        print(f"\n💾 Agent ID saved: {agent_id}")
        # Save to file for test script
        with open("/tmp/test_flow_agent_id.txt", "w") as f:
            f.write(agent_id)
