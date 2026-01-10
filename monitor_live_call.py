#!/usr/bin/env python3
"""
Real-time monitoring test - calls user and displays live metrics
"""
import requests
import time
import json
from datetime import datetime

BACKEND_URL = "https://missed-variable.preview.emergentagent.com"
AGENT_ID = "25b0f437-9164-4e55-b925-43b2d81e3ed9"  # Transitioner agent
TO_NUMBER = "+17708336397"
FROM_NUMBER = "+14048000152"

def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

print("="*80)
print("🎙️  REAL-TIME VOICE AGENT MONITORING")
print("="*80)
print(f"Time: {timestamp()}")
print(f"Agent: Transitioner Strawbanana")
print(f"Calling: {TO_NUMBER}")
print("="*80)

# Make the call
print(f"\n[{timestamp()}] 📞 Initiating call...")
payload = {
    "agent_id": AGENT_ID,
    "to_number": TO_NUMBER,
    "from_number": FROM_NUMBER,
    "custom_variables": {}
}

response = requests.post(f"{BACKEND_URL}/api/telnyx/call/outbound", json=payload)

if response.status_code != 200:
    print(f"❌ Error: {response.status_code} - {response.text}")
    exit(1)

result = response.json()
call_id = result.get("call_id")
print(f"[{timestamp()}] ✅ Call initiated: {call_id}")

# Monitor in real-time
print(f"\n{'='*80}")
print("📊 REAL-TIME MONITORING (60 seconds)")
print(f"{'='*80}\n")

last_transcript_count = 0
start_time = time.time()
events = []

for i in range(240):  # 240 seconds = 4 minutes
    try:
        response = requests.get(f"{BACKEND_URL}/api/telnyx/call/{call_id}")
        
        if response.status_code == 200:
            call_log = response.json()
            status = call_log.get("status", "unknown")
            transcript = call_log.get("transcript", [])
            
            # New transcript entries
            if len(transcript) > last_transcript_count:
                for entry in transcript[last_transcript_count:]:
                    speaker = entry.get("speaker", "unknown")
                    text = entry.get("text", "")
                    entry_time = entry.get("timestamp", "")
                    
                    elapsed = time.time() - start_time
                    icon = "🤖" if speaker == "agent" else "👤"
                    
                    print(f"[{timestamp()}] [{elapsed:.1f}s] {icon} {speaker.upper()}: {text}")
                    
                    events.append({
                        "time": elapsed,
                        "speaker": speaker,
                        "text": text
                    })
                
                last_transcript_count = len(transcript)
            
            # Check if call ended
            if status in ["completed", "failed", "no-answer", "busy"]:
                print(f"\n[{timestamp()}] 📞 Call ended: {status}")
                break
        
        time.sleep(0.5)  # Check twice per second
        
    except Exception as e:
        print(f"[{timestamp()}] ⚠️  Error checking: {e}")
        time.sleep(0.5)

# Final analysis
print(f"\n{'='*80}")
print("📈 PERFORMANCE ANALYSIS")
print(f"{'='*80}\n")

# Calculate latencies
if len(events) >= 2:
    for i in range(1, len(events)):
        prev_event = events[i-1]
        curr_event = events[i]
        
        if prev_event["speaker"] != curr_event["speaker"]:
            latency = curr_event["time"] - prev_event["time"]
            print(f"⏱️  Response latency ({prev_event['speaker']} → {curr_event['speaker']}): {latency:.2f}s")

# Get final transcript
try:
    response = requests.get(f"{BACKEND_URL}/api/telnyx/call/{call_id}")
    if response.status_code == 200:
        call_log = response.json()
        transcript = call_log.get("transcript", [])
        
        print(f"\n📋 FINAL TRANSCRIPT ({len(transcript)} messages):")
        print("-"*80)
        for entry in transcript:
            speaker = entry.get("speaker", "unknown")
            text = entry.get("text", "")
            icon = "🤖" if speaker == "agent" else "👤"
            print(f"{icon} [{speaker.upper()}]: {text}")
        print("-"*80)
        
        # Check if transitions worked
        agent_messages = [e["text"] for e in transcript if e.get("speaker") == "agent"]
        user_messages = [e["text"] for e in transcript if e.get("speaker") == "user"]
        
        print(f"\n📊 SUMMARY:")
        print(f"   Agent messages: {len(agent_messages)}")
        print(f"   User messages: {len(user_messages)}")
        print(f"   Total duration: {time.time() - start_time:.1f}s")
        
        if len(agent_messages) > 1:
            print(f"   ✅ Flow transitions: WORKING")
            if "yellow" in " ".join(agent_messages).lower():
                print(f"   📍 Path taken: BANANA")
            elif "gold" in " ".join(agent_messages).lower():
                print(f"   📍 Path taken: STRAWBERRY")
        else:
            print(f"   ❌ Flow transitions: FAILED (only greeting)")
        
        # Endpointing analysis
        if len(user_messages) > 0:
            print(f"\n✅ ENDPOINTING: Working - captured {len(user_messages)} user turn(s)")
        else:
            print(f"\n❌ ENDPOINTING: Not working - no user speech captured")
            
except Exception as e:
    print(f"Error getting final stats: {e}")

print(f"\n{'='*80}")
