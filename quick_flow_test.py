#!/usr/bin/env python3
"""
Quick test of the flow agent
"""
import requests
import time

BACKEND_URL = "https://tts-guardian.preview.emergentagent.com"
AGENT_ID = "5d2764ba-fb80-4487-bd85-0deeb722ff39"
TO_NUMBER = "+17708336397"
FROM_NUMBER = "+14048000152"

print("📞 Making test call with flow agent...")

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
    print("\n⏳ Waiting 20 seconds for call to complete...")
    
    time.sleep(20)
    
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
    else:
        print(f"❌ Error getting transcript: {response.status_code}")
else:
    print(f"❌ Error: {response.status_code}")
