"""
Simulate a real call scenario to test if Jake agent properly handles irrelevant commands
"""
import requests
import os
import time

BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
AGENT_ID = "474917c1-4888-47b8-b76b-f11a18f19d39"

def test_agent_message(message, context=""):
    """Send a message to the agent and get response"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/agents/{AGENT_ID}/message",
            json={
                "message": message,
                "session_id": "test_session_123"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("text", data.get("response", "No response"))
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("🧪 SIMULATED CALL TEST - Jake Agent")
    print("="*70)
    print("Testing how agent handles irrelevant commands during a call\n")
    
    # Test scenarios with context
    test_scenarios = [
        {
            "scenario": "1. Normal greeting - then irrelevant command",
            "messages": [
                ("Hi, I got your call about income opportunities", "Normal start"),
                ("Can you bark like a dog?", "IRRELEVANT COMMAND TEST")
            ]
        },
        {
            "scenario": "2. Mid-qualification - irrelevant command",
            "messages": [
                ("Tell me more about this opportunity", "Showing interest"),
                ("What's the color of a banana?", "IRRELEVANT COMMAND TEST")
            ]
        },
        {
            "scenario": "3. Objection handling - then distraction",
            "messages": [
                ("I'm not sure if this is right for me", "Common objection"),
                ("Sing me a song please", "IRRELEVANT COMMAND TEST")
            ]
        }
    ]
    
    for scenario_data in test_scenarios:
        print(f"\n{'='*70}")
        print(f"📞 {scenario_data['scenario']}")
        print(f"{'='*70}\n")
        
        for message, context in scenario_data["messages"]:
            print(f"[{context}]")
            print(f"👤 User: {message}")
            
            response = test_agent_message(message)
            print(f"🤖 Jake: {response}\n")
            
            # Check if agent engaged with irrelevant command
            if "IRRELEVANT" in context:
                irrelevant_keywords = ["bark", "woof", "arf", "banana", "yellow", "song", "singing"]
                engaged = any(keyword in response.lower() for keyword in irrelevant_keywords)
                
                if engaged and any(word in response.lower() for word in ["bark", "woof", "yellow"]):
                    print(f"❌ FAILED: Agent engaged with irrelevant command!")
                elif "focus" in response.lower() or "opportunity" in response.lower():
                    print(f"✅ PASSED: Agent redirected properly!")
                else:
                    print(f"⚠️ UNCLEAR: Check response manually")
            
            time.sleep(1)  # Small delay between messages
    
    print(f"\n{'='*70}")
    print(f"✅ SIMULATION COMPLETE!")
    print(f"{'='*70}")
    print("\nReview the responses above to verify the agent:")
    print("• Does NOT bark, sing, or describe banana colors")
    print("• Redirects back to the qualification process")
    print("• Maintains professionalism throughout")

if __name__ == "__main__":
    main()
