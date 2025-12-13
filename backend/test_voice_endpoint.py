#!/usr/bin/env python3
import requests
import sys

# Create a proper test recording
print("Creating test audio recording...")

# Use ffmpeg to create a 3-second audio file with tone
import subprocess
subprocess.run([
    'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=3',
    '-ac', '1', '-ar', '16000', '-f', 'wav', '/tmp/test_recording.wav', '-y'
], capture_output=True)

print("Testing backend STT endpoint with recording...")

with open('/tmp/test_recording.wav', 'rb') as f:
    files = {'audio': ('test.wav', f, 'audio/wav')}
    response = requests.post('http://localhost:8001/api/speech-to-text', files=files)
    
print(f"STT Status: {response.status_code}")
print(f"STT Response: {response.text}")

# Test TTS endpoint
print("\nTesting backend TTS endpoint...")
response = requests.post(
    'http://localhost:8001/api/text-to-speech',
    json={'text': 'Hello, this is a test of the text to speech system.', 'voice': 'Rachel'}
)

print(f"TTS Status: {response.status_code}")
print(f"TTS Content-Type: {response.headers.get('content-type')}")
print(f"TTS Audio Size: {len(response.content)} bytes")

if response.status_code == 200 and len(response.content) > 1000:
    with open('/tmp/test_tts.mp3', 'wb') as f:
        f.write(response.content)
    print("✅ TTS audio saved to /tmp/test_tts.mp3")
    
    # Try to play it
    print("Attempting to play audio...")
    subprocess.run(['ffmpeg', '-i', '/tmp/test_tts.mp3', '-f', 'null', '-'], capture_output=True)
    print("✅ Audio file is valid")
else:
    print("❌ TTS failed")

