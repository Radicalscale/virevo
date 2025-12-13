#!/usr/bin/env python3
"""
Test the Transitioner Strawbanana agent
"""
import requests
import time

BACKEND_URL = "https://tts-guardian.preview.emergentagent.com"
AGENT_ID = "25b0f437-9164-4e55-b925-43b2d81e3ed9"
TO_NUMBER = "+17708336397"
FROM_NUMBER = "+14048000152"

print("📞 Testing Transitioner Strawbanana agent...")
print("   Agent should say 'Say banana or strawberry'")
print("   Then transition based on what you say")
print()

payload = {
    "agent_id": AGENT_ID,
    "to_number": TO_NUMBER,
    "from_number": FROM_NUMBER,
    "custom_variables": {}
}

response = requests.post(f"{BACKEND_URL}/api/telnyx/call/outbound", json=payload)

if response.status_code == 200:
    result = response.json()
    call_id = result.get("call_id")
    print(f"✅ Call initiated: {call_id}")
    print("\n⏳ Please answer and say either 'banana' or 'strawberry'")
    print("   Waiting 45 seconds for transcript...\n")
    
    time.sleep(45)
    
    # Get transcript
    response = requests.get(f"{BACKEND_URL}/api/telnyx/call/{call_id}")
    if response.status_code == 200:
        call_log = response.json()
        transcript = call_log.get("transcript", [])
        
        print(f"\n📋 Transcript ({len(transcript)} messages):")
        print("-"*70)
        for entry in transcript:
            speaker = entry.get("speaker", "unknown")
            text = entry.get("text", "")
            icon = "🤖" if speaker == "agent" else "👤"
            print(f"{icon} [{speaker.upper()}]: {text}")
        print("-"*70)
        
        # Check if transition happened
        agent_messages = [e["text"] for e in transcript if e.get("speaker") == "agent"]
        if len(agent_messages) > 1:
            print("\n✅ TRANSITION WORKED - Multiple agent messages detected!")
            if "yellow" in " ".join(agent_messages).lower():
                print("   → Followed BANANA path")
            elif "gold" in " ".join(agent_messages).lower():
                print("   → Followed STRAWBERRY path")
        else:
            print("\n❌ TRANSITION FAILED - Only greeting detected, no follow-up")
    else:
        print(f"❌ Error getting transcript: {response.status_code}")
else:
    print(f"❌ Error: {response.status_code}")
