#!/usr/bin/env python3
"""
Test script for Telnyx audio streaming
Makes an outbound call and checks for transcripts
"""
import requests
import time
import json
import sys

# Configuration
BACKEND_URL = "https://missed-variable.preview.emergentagent.com"
TO_NUMBER = "+17708336397"  # User's phone number
FROM_NUMBER = "+14048000152"  # Telnyx number
AGENT_ID = None  # Will fetch first available agent

def get_first_agent():
    """Get the first available agent"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/agents")
        if response.status_code == 200:
            agents = response.json()
            if agents:
                return agents[0]["id"]
        print("❌ No agents found")
        return None
    except Exception as e:
        print(f"❌ Error fetching agents: {e}")
        return None

def make_outbound_call(agent_id):
    """Make an outbound call"""
    try:
        payload = {
            "agent_id": agent_id,
            "to_number": TO_NUMBER,
            "from_number": FROM_NUMBER,
            "custom_variables": {
                "customer_name": "Kendric",
                "customer_email": "kendrickbowman9@gmail.com"
            }
        }
        
        print(f"\n📞 Making outbound call to {TO_NUMBER}...")
        print(f"   Agent: {agent_id}")
        print(f"   From: {FROM_NUMBER}")
        
        response = requests.post(
            f"{BACKEND_URL}/api/telnyx/call/outbound",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                call_id = result.get("call_id")
                print(f"✅ Call initiated successfully!")
                print(f"   Call ID: {call_id}")
                print(f"   Status: {result.get('status')}")
                return call_id
            else:
                print(f"❌ Call failed: {result}")
                return None
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error making call: {e}")
        return None

def check_transcript(call_id, max_attempts=30, interval=5):
    """Check for transcripts in the call log"""
    print(f"\n👀 Monitoring call {call_id} for transcripts...")
    print(f"   Will check every {interval} seconds for up to {max_attempts * interval} seconds")
    print(f"   📞 ANSWER THE PHONE AND SPEAK WHEN IT RINGS!")
    print()
    
    has_transcript = False
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Check call log via API
            response = requests.get(f"{BACKEND_URL}/api/telnyx/call/{call_id}")
            
            if response.status_code == 200:
                call_log = response.json()
                transcript = call_log.get("transcript", [])
                status = call_log.get("status", "unknown")
                
                print(f"[{attempt}/{max_attempts}] Status: {status} | Transcript entries: {len(transcript)}")
                
                if transcript:
                    has_transcript = True
                    print(f"\n🎉 SUCCESS! Transcript detected!")
                    print(f"   Found {len(transcript)} transcript entries")
                    print("\n📝 Transcript:")
                    for entry in transcript:
                        speaker = entry.get("speaker", "unknown")
                        text = entry.get("text", "")
                        timestamp = entry.get("timestamp", "")
                        print(f"   [{speaker}] {text}")
                    print()
                    return True
                    
                elif status in ["completed", "failed"]:
                    print(f"\n⚠️  Call ended with status '{status}' but NO transcript found")
                    print(f"   This means audio streaming did NOT work")
                    return False
                    
            elif response.status_code == 404:
                print(f"[{attempt}/{max_attempts}] Call log not found yet (call may not be created)")
                
            time.sleep(interval)
            
        except Exception as e:
            print(f"[{attempt}/{max_attempts}] Error checking: {e}")
            time.sleep(interval)
    
    print("\n⏰ Monitoring period ended.")
    
    if not has_transcript:
        print("\n❌ NO TRANSCRIPT DETECTED")
        print("   Audio streaming did NOT work - need to debug")
    
    return has_transcript

def main():
    print("="*70)
    print("🎙️  TELNYX AUDIO STREAMING TEST")
    print("="*70)
    
    # Get agent
    print("\n1️⃣  Fetching agent...")
    agent_id = get_first_agent()
    if not agent_id:
        print("❌ Cannot proceed without an agent")
        sys.exit(1)
    print(f"   ✅ Using agent: {agent_id}")
    
    # Make call
    print("\n2️⃣  Initiating outbound call...")
    call_id = make_outbound_call(agent_id)
    if not call_id:
        print("❌ Call failed to initiate")
        sys.exit(1)
    
    # Monitor for transcripts
    print("\n3️⃣  Monitoring for audio activity...")
    success = check_transcript(call_id)
    
    # Print final result
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    if success:
        print("✅ AUDIO STREAMING WORKS!")
        print("   Transcripts were successfully captured")
        print("   The bidirectional audio pipeline is functional")
    else:
        print("❌ AUDIO STREAMING FAILED")
        print("   No transcripts were captured")
        print("   Need to debug the audio pipeline")
        print()
        print("🔍 Debug steps:")
        print("   1. Check backend logs: tail -f /var/log/supervisor/backend.out.log")
        print("   2. Look for WebSocket connection messages")
        print("   3. Check for Deepgram/ElevenLabs API errors")
        print("   4. Verify Telnyx streaming_start was called")
    print("="*70)

if __name__ == "__main__":
    main()
