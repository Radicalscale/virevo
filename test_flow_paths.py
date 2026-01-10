#!/usr/bin/env python3
"""
Test script to make calls and trigger different flow paths
"""
import requests
import time
import json

BACKEND_URL = "https://missed-variable.preview.emergentagent.com"
TO_NUMBER = "+17708336397"
FROM_NUMBER = "+14048000152"

# Read agent ID
with open("/tmp/test_flow_agent_id.txt", "r") as f:
    AGENT_ID = f.read().strip()

print("="*70)
print("🎯 TELNYX CALL FLOW TEST")
print("="*70)
print(f"Agent ID: {AGENT_ID}")
print(f"Testing 2 different call paths")
print("="*70)

def make_test_call(call_number, path_name):
    """Make an outbound call"""
    print(f"\n📞 TEST CALL #{call_number} - {path_name} Path")
    print("-"*70)
    
    payload = {
        "agent_id": AGENT_ID,
        "to_number": TO_NUMBER,
        "from_number": FROM_NUMBER,
        "custom_variables": {
            "test_number": call_number,
            "path": path_name
        }
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/telnyx/call/outbound",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                call_id = result.get("call_id")
                print(f"✅ Call initiated: {call_id}")
                return call_id
            else:
                print(f"❌ Call failed: {result}")
                return None
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def monitor_call(call_id, duration=60):
    """Monitor call for completion and transcript"""
    print(f"\n👀 Monitoring call: {call_id}")
    print(f"   Waiting up to {duration} seconds...")
    
    start_time = time.time()
    last_status = None
    transcript_count = 0
    
    while time.time() - start_time < duration:
        try:
            response = requests.get(f"{BACKEND_URL}/api/telnyx/call/{call_id}")
            
            if response.status_code == 200:
                call_log = response.json()
                status = call_log.get("status", "unknown")
                transcript = call_log.get("transcript", [])
                
                if status != last_status:
                    print(f"   Status: {status}")
                    last_status = status
                
                if len(transcript) > transcript_count:
                    print(f"   📝 Transcript updated: {len(transcript)} entries")
                    transcript_count = len(transcript)
                
                if status in ["completed", "failed"]:
                    print(f"\n✅ Call ended with status: {status}")
                    return call_log
                    
            time.sleep(3)
            
        except Exception as e:
            print(f"   Error monitoring: {e}")
            time.sleep(3)
    
    print(f"\n⏰ Monitoring timeout after {duration} seconds")
    return None

def display_transcript(call_log, path_name):
    """Display the call transcript"""
    print(f"\n📋 TRANSCRIPT - {path_name} Path")
    print("="*70)
    
    if not call_log:
        print("❌ No call log available")
        return False
    
    transcript = call_log.get("transcript", [])
    
    if not transcript:
        print("❌ No transcript found")
        return False
    
    print(f"Call ID: {call_log.get('call_id')}")
    print(f"Duration: {call_log.get('duration', 0)} seconds")
    print(f"Status: {call_log.get('status')}")
    print(f"\nTranscript ({len(transcript)} messages):")
    print("-"*70)
    
    for entry in transcript:
        speaker = entry.get("speaker", "unknown")
        text = entry.get("text", "")
        icon = "🤖" if speaker == "agent" else "👤"
        print(f"{icon} [{speaker.upper()}]: {text}")
    
    print("="*70)
    return True

# MAIN TEST
print("\n" + "🔔 STARTING AUTOMATED TEST " + "="*42)
print("This test will make 2 calls to test both flow paths.")
print("="*70)

# Test Call 1 - Sales Path
print("\n\n" + "🟢 STARTING TEST CALL #1 (SALES PATH) " + "="*31)
call1_id = make_test_call(1, "Sales")

if call1_id:
    print("\n⏳ Please answer the call and listen...")
    print("   The agent will play the menu and Sales path")
    time.sleep(5)  # Give time to answer
    call1_log = monitor_call(call1_id, duration=45)
    display_transcript(call1_log, "Sales")

print("\n\n⏸️  Waiting 10 seconds before next call...")
time.sleep(10)

# Test Call 2 - Support Path  
print("\n\n" + "🔵 STARTING TEST CALL #2 (SUPPORT PATH) " + "="*29)
call2_id = make_test_call(2, "Support")

if call2_id:
    print("\n⏳ Please answer the call and listen...")
    print("   The agent will play the menu and Support path")
    time.sleep(5)  # Give time to answer
    call2_log = monitor_call(call2_id, duration=45)
    display_transcript(call2_log, "Support")

# Final Summary
print("\n\n" + "📊 TEST SUMMARY " + "="*53)
print("Both test calls completed!")
print("Check the transcripts above to verify:")
print("  ✓ Call #1 followed the Sales path")
print("  ✓ Call #2 followed the Support path")
print("  ✓ Both calls reached their respective ending nodes")
print("="*70)
