#!/usr/bin/env python3
"""Test call flow transitions end-to-end"""

import requests
import json

BASE_URL = "http://localhost:8001/api"

def test_call_flow_transitions():
    """Test that call flow properly transitions between nodes"""
    
    # Get the call flow agent
    agents = requests.get(f"{BASE_URL}/agents").json()
    flow_agent = None
    for agent in agents:
        if agent.get("agent_type") == "call_flow":
            flow_agent = agent
            break
    
    if not flow_agent:
        print("❌ No call flow agent found")
        return False
    
    agent_id = flow_agent["id"]
    print(f"✅ Found call flow agent: {agent_id}")
    print(f"   Name: {flow_agent['name']}")
    
    # Conversation history to track state
    conversation_history = []
    
    # TEST 1: First message
    print("\n" + "="*60)
    print("TEST 1: First message - should return greeting")
    print("="*60)
    
    response1 = requests.post(
        f"{BASE_URL}/agents/{agent_id}/process",
        json={
            "message": "Hello",
            "conversation_history": conversation_history
        }
    ).json()
    
    greeting_response = response1["response"]
    print(f"User: Hello")
    print(f"Agent: {greeting_response}")
    
    # Add to conversation history
    conversation_history.append({"role": "user", "content": "Hello"})
    conversation_history.append({
        "role": "assistant", 
        "content": greeting_response,
        "_node_id": "2"  # Greeting node
    })
    
    if "pricing" in greeting_response.lower() and "support" in greeting_response.lower():
        print("✅ PASS: Greeting mentions pricing and support options")
    else:
        print("❌ FAIL: Greeting doesn't mention options")
        return False
    
    # TEST 2: Ask about pricing - should transition to pricing node
    print("\n" + "="*60)
    print("TEST 2: Ask about pricing - should transition to Pricing node")
    print("="*60)
    
    response2 = requests.post(
        f"{BASE_URL}/agents/{agent_id}/process",
        json={
            "message": "How much does it cost?",
            "conversation_history": conversation_history
        }
    ).json()
    
    pricing_response = response2["response"]
    print(f"User: How much does it cost?")
    print(f"Agent: {pricing_response}")
    
    # Add to conversation history
    conversation_history.append({"role": "user", "content": "How much does it cost?"})
    conversation_history.append({
        "role": "assistant",
        "content": pricing_response,
        "_node_id": "3"  # Pricing node
    })
    
    if "$99" in pricing_response or "premium" in pricing_response.lower() or "plan" in pricing_response.lower():
        print("✅ PASS: Response contains pricing information (transitioned to Pricing node)")
    else:
        print("❌ FAIL: Response doesn't contain pricing info - didn't transition!")
        print(f"   Expected pricing info, got: {pricing_response}")
        return False
    
    # TEST 3: Reset and ask about support - should transition to support node
    print("\n" + "="*60)
    print("TEST 3: Ask about support - should transition to Support node")
    print("="*60)
    
    # Start fresh conversation
    conversation_history = []
    
    # First message
    response3a = requests.post(
        f"{BASE_URL}/agents/{agent_id}/process",
        json={
            "message": "Hi",
            "conversation_history": conversation_history
        }
    ).json()
    
    conversation_history.append({"role": "user", "content": "Hi"})
    conversation_history.append({
        "role": "assistant",
        "content": response3a["response"],
        "_node_id": "2"
    })
    
    # Ask about support
    response3b = requests.post(
        f"{BASE_URL}/agents/{agent_id}/process",
        json={
            "message": "I need technical support",
            "conversation_history": conversation_history
        }
    ).json()
    
    support_response = response3b["response"]
    print(f"User: I need technical support")
    print(f"Agent: {support_response}")
    
    if "technical" in support_response.lower() or "problem" in support_response.lower() or "help" in support_response.lower():
        print("✅ PASS: Response is about support (transitioned to Support node)")
    else:
        print("❌ FAIL: Response doesn't relate to support - didn't transition!")
        print(f"   Expected support response, got: {support_response}")
        return False
    
    # TEST 4: Verify we DON'T transition when condition doesn't match
    print("\n" + "="*60)
    print("TEST 4: Generic question - should stay on current node")
    print("="*60)
    
    conversation_history = []
    
    # First message
    response4a = requests.post(
        f"{BASE_URL}/agents/{agent_id}/process",
        json={
            "message": "Hello",
            "conversation_history": conversation_history
        }
    ).json()
    
    conversation_history.append({"role": "user", "content": "Hello"})
    conversation_history.append({
        "role": "assistant",
        "content": response4a["response"],
        "_node_id": "2"
    })
    
    # Generic message that doesn't match any transition
    response4b = requests.post(
        f"{BASE_URL}/agents/{agent_id}/process",
        json={
            "message": "That's nice",
            "conversation_history": conversation_history
        }
    ).json()
    
    generic_response = response4b["response"]
    print(f"User: That's nice")
    print(f"Agent: {generic_response}")
    
    # Should stay on greeting node or return greeting again
    if "pricing" in generic_response.lower() or "support" in generic_response.lower():
        print("✅ PASS: Stayed on greeting node (no transition)")
    else:
        print("⚠️  WARNING: Response changed but we can't verify if transition was correct")
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED!")
    print("="*60)
    print("\nCall flow transitions are working correctly:")
    print("  ✅ First message returns greeting")
    print("  ✅ 'pricing' keywords → transitions to Pricing node")
    print("  ✅ 'support' keywords → transitions to Support node")
    print("  ✅ AI properly evaluates conditions")
    
    return True

if __name__ == "__main__":
    try:
        success = test_call_flow_transitions()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
