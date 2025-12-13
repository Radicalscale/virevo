#!/usr/bin/env python3
"""
Test script for Kokoro TTS server
Tests latency, voice quality, and API endpoints
"""

import requests
import time
import json
from typing import Optional

# Server configuration
KOKORO_SERVER = "http://203.57.40.151:10213"
OPENAI_ENDPOINT = f"{KOKORO_SERVER}/v1/audio/speech"

# Available voices (from research)
VOICES = {
    "af_bella": "Female - Bella (American)",
    "af_nicole": "Female - Nicole (American)",
    "af_sarah": "Female - Sarah (American)",
    "af_sky": "Female - Sky (American)",
    "bf_emma": "Female - Emma (British)",
    "bf_isabella": "Female - Isabella (British)",
    "am_adam": "Male - Adam (American)",
    "am_michael": "Male - Michael (American)",
    "bm_george": "Male - George (British)",
    "bm_lewis": "Male - Lewis (British)"
}

def test_health_check():
    """Test if server is responding"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{KOKORO_SERVER}/health", timeout=5)
        print(f"✅ Server Status: {response.status_code}")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Server unreachable: {e}")
        return False

def test_tts_generation(voice: str = "af_bella", text: str = "Hello, this is a test of Kokoro TTS.", 
                        response_format: str = "mp3", speed: float = 1.0):
    """Test TTS generation with timing"""
    print("\n" + "="*60)
    print(f"TEST 2: TTS Generation")
    print(f"Voice: {voice} ({VOICES.get(voice, 'Unknown')})")
    print(f"Text: {text}")
    print(f"Format: {response_format}, Speed: {speed}x")
    print("="*60)
    
    request_body = {
        "model": "kokoro",
        "input": text,
        "voice": voice,
        "response_format": response_format,
        "speed": speed
    }
    
    try:
        # Measure latency
        start_time = time.time()
        
        response = requests.post(
            OPENAI_ENDPOINT,
            json=request_body,
            timeout=30
        )
        
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            audio_size = len(response.content)
            print(f"✅ SUCCESS")
            print(f"⏱️  Latency: {latency:.0f}ms")
            print(f"📦 Audio Size: {audio_size:,} bytes ({audio_size/1024:.1f} KB)")
            
            # Save audio file
            filename = f"/tmp/kokoro_test_{voice}.{response_format}"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"💾 Saved to: {filename}")
            
            # Check response headers for additional timing info
            if 'X-Generation-Time' in response.headers:
                print(f"🔍 Server Generation Time: {response.headers['X-Generation-Time']}ms")
            if 'X-Total-Time' in response.headers:
                print(f"🔍 Server Total Time: {response.headers['X-Total-Time']}ms")
            
            return latency, audio_size
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None, None
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None, None

def test_multiple_voices():
    """Test multiple voices for comparison"""
    print("\n" + "="*60)
    print("TEST 3: Voice Comparison")
    print("="*60)
    
    test_text = "This is a quick test of different voices."
    results = {}
    
    for voice_id, voice_name in VOICES.items():
        print(f"\nTesting: {voice_name}")
        latency, size = test_tts_generation(voice_id, test_text, response_format="wav", speed=1.0)
        if latency:
            results[voice_id] = {"latency": latency, "size": size, "name": voice_name}
    
    # Summary
    if results:
        print("\n" + "="*60)
        print("VOICE COMPARISON SUMMARY")
        print("="*60)
        for voice_id, data in sorted(results.items(), key=lambda x: x[1]['latency']):
            print(f"{data['name']:30} | Latency: {data['latency']:6.0f}ms | Size: {data['size']/1024:6.1f} KB")
        
        avg_latency = sum(r['latency'] for r in results.values()) / len(results)
        print(f"\n📊 Average Latency: {avg_latency:.0f}ms")

def test_latency_scaling():
    """Test how latency scales with text length"""
    print("\n" + "="*60)
    print("TEST 4: Latency Scaling")
    print("="*60)
    
    test_texts = [
        ("Short", "Hello world."),
        ("Medium", "This is a medium length sentence to test the latency scaling of Kokoro TTS."),
        ("Long", "This is a much longer piece of text that will help us understand how the latency scales with the input length. We want to see if Kokoro maintains its flat latency characteristic that was mentioned in the documentation.")
    ]
    
    results = []
    for label, text in test_texts:
        print(f"\n{label} text ({len(text)} chars):")
        latency, size = test_tts_generation("af_bella", text, response_format="mp3", speed=1.0)
        if latency:
            results.append((label, len(text), latency, size))
    
    # Summary
    if results:
        print("\n" + "="*60)
        print("LATENCY SCALING SUMMARY")
        print("="*60)
        print(f"{'Length':10} | {'Chars':6} | {'Latency':10} | {'Audio Size':12}")
        print("-" * 60)
        for label, chars, latency, size in results:
            print(f"{label:10} | {chars:6} | {latency:8.0f}ms | {size/1024:8.1f} KB")

def test_speed_variations():
    """Test different speed settings"""
    print("\n" + "="*60)
    print("TEST 5: Speed Variations")
    print("="*60)
    
    text = "Testing different playback speeds for Kokoro TTS."
    speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    
    for speed in speeds:
        print(f"\nSpeed: {speed}x")
        latency, size = test_tts_generation("af_bella", text, response_format="mp3", speed=speed)

def test_formats():
    """Test different audio formats"""
    print("\n" + "="*60)
    print("TEST 6: Audio Formats")
    print("="*60)
    
    text = "Testing audio format options."
    formats = ["mp3", "wav", "opus", "flac"]
    
    results = []
    for fmt in formats:
        print(f"\nFormat: {fmt}")
        latency, size = test_tts_generation("af_bella", text, response_format=fmt, speed=1.0)
        if latency and size:
            results.append((fmt, latency, size))
    
    # Summary
    if results:
        print("\n" + "="*60)
        print("FORMAT COMPARISON")
        print("="*60)
        for fmt, latency, size in results:
            print(f"{fmt:8} | Latency: {latency:6.0f}ms | Size: {size/1024:6.1f} KB")

def run_all_tests():
    """Run all test suites"""
    print("\n" + "#"*60)
    print("# KOKORO TTS SERVER TEST SUITE")
    print("# Server: " + KOKORO_SERVER)
    print("#"*60)
    
    # Test 1: Health Check
    if not test_health_check():
        print("\n❌ Server is not responding. Exiting tests.")
        return
    
    # Test 2: Basic generation
    test_tts_generation()
    
    # Test 3: Multiple voices
    test_multiple_voices()
    
    # Test 4: Latency scaling
    test_latency_scaling()
    
    # Test 5: Speed variations
    test_speed_variations()
    
    # Test 6: Format comparison
    test_formats()
    
    print("\n" + "#"*60)
    print("# ALL TESTS COMPLETE")
    print("#"*60)
    print("\n📝 Audio files saved to /tmp/kokoro_test_*.{format}")
    print("🎧 Listen to the files to verify voice quality")
    print("\n✅ If latency is <500ms, Kokoro is ready for real-time telephony!")

if __name__ == "__main__":
    run_all_tests()
