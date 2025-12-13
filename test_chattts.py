"""
Test script for ChatTTS RunPod Server
Tests health, latency, voices, and all features
"""

import requests
import time
import json
from typing import Dict, Any

# Configure your RunPod server URL here
CHATTTS_API_URL = "http://localhost:8000"  # Change to your RunPod URL

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    try:
        response = requests.get(f"{CHATTTS_API_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

def test_voices():
    """Test voices endpoint"""
    print("\n=== Testing Voices Endpoint ===")
    try:
        response = requests.get(f"{CHATTTS_API_URL}/voices")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Available voices: {data['voices']}")
        print(f"Voice seeds: {json.dumps(data['voice_seeds'], indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Voices check failed: {str(e)}")
        return False

def test_generation(text: str, voice: str = "female_1", speed: float = 1.0, 
                   temperature: float = 0.3, response_format: str = "wav"):
    """Test speech generation"""
    print(f"\n=== Testing Generation: voice={voice}, speed={speed}, temp={temperature} ===")
    
    payload = {
        "text": text,
        "voice": voice,
        "speed": speed,
        "temperature": temperature,
        "response_format": response_format
    }
    
    try:
        start = time.time()
        response = requests.post(
            f"{CHATTTS_API_URL}/v1/audio/speech",
            json=payload
        )
        latency = time.time() - start
        
        print(f"Status: {response.status_code}")
        print(f"Total Latency: {latency:.3f}s")
        
        if response.status_code == 200:
            # Check headers for metrics
            processing_time = response.headers.get('X-Processing-Time', 'N/A')
            audio_duration = response.headers.get('X-Audio-Duration', 'N/A')
            rtf = response.headers.get('X-RTF', 'N/A')
            inference_time = response.headers.get('X-Inference-Time', 'N/A')
            
            print(f"Processing Time: {processing_time}s")
            print(f"Audio Duration: {audio_duration}s")
            print(f"Real-Time Factor (RTF): {rtf}")
            print(f"Inference Time: {inference_time}s")
            
            # Save audio file
            filename = f"test_chattts_{voice}_{speed}_{temperature}.{response_format}"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Audio saved to: {filename}")
            print(f"Audio size: {len(response.content)} bytes")
            
            return True
        else:
            print(f"❌ Generation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Generation test failed: {str(e)}")
        return False

def test_multiple_voices():
    """Test all available voices"""
    print("\n=== Testing All Voices ===")
    
    test_text = "Hello, I am testing different voices with ChatTTS."
    voices = ["male_1", "male_2", "female_1", "female_2", "neutral_1"]
    
    results = []
    for voice in voices:
        success = test_generation(test_text, voice=voice, response_format="wav")
        results.append((voice, success))
        time.sleep(0.5)  # Small delay between requests
    
    print("\n=== Voice Test Summary ===")
    for voice, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {voice}")

def test_speed_variations():
    """Test different speed settings"""
    print("\n=== Testing Speed Variations ===")
    
    test_text = "Testing speed control with ChatTTS."
    speeds = [0.5, 1.0, 1.5, 2.0]
    
    results = []
    for speed in speeds:
        success = test_generation(test_text, voice="female_1", speed=speed)
        results.append((speed, success))
        time.sleep(0.5)
    
    print("\n=== Speed Test Summary ===")
    for speed, success in results:
        status = "✅" if success else "❌"
        print(f"{status} Speed {speed}x")

def test_temperature_variations():
    """Test different temperature settings"""
    print("\n=== Testing Temperature Variations ===")
    
    test_text = "Testing temperature control for voice variation."
    temperatures = [0.1, 0.3, 0.5, 0.8]
    
    results = []
    for temp in temperatures:
        success = test_generation(test_text, voice="female_1", temperature=temp)
        results.append((temp, success))
        time.sleep(0.5)
    
    print("\n=== Temperature Test Summary ===")
    for temp, success in results:
        status = "✅" if success else "❌"
        print(f"{status} Temperature {temp}")

def test_formats():
    """Test different audio formats"""
    print("\n=== Testing Audio Formats ===")
    
    test_text = "Testing different audio output formats."
    formats = ["wav", "mp3"]
    
    results = []
    for fmt in formats:
        success = test_generation(test_text, voice="female_1", response_format=fmt)
        results.append((fmt, success))
        time.sleep(0.5)
    
    print("\n=== Format Test Summary ===")
    for fmt, success in results:
        status = "✅" if success else "❌"
        print(f"{status} Format: {fmt}")

def test_long_text():
    """Test with longer text"""
    print("\n=== Testing Long Text ===")
    
    long_text = """
    This is a longer text to test the performance of ChatTTS with more complex sentences.
    We want to see how well it handles longer inputs and maintains good voice quality.
    The system should still maintain low latency even with longer text inputs.
    """
    
    return test_generation(long_text.strip(), voice="female_1", temperature=0.3)

def benchmark_latency(iterations: int = 5):
    """Benchmark latency over multiple requests"""
    print(f"\n=== Latency Benchmark ({iterations} iterations) ===")
    
    test_text = "This is a latency benchmark test."
    latencies = []
    
    for i in range(iterations):
        print(f"\nIteration {i+1}/{iterations}")
        start = time.time()
        response = requests.post(
            f"{CHATTTS_API_URL}/v1/audio/speech",
            json={
                "text": test_text,
                "voice": "female_1",
                "speed": 1.0,
                "temperature": 0.3,
                "response_format": "wav"
            }
        )
        latency = time.time() - start
        
        if response.status_code == 200:
            latencies.append(latency)
            rtf = response.headers.get('X-RTF', 'N/A')
            print(f"Latency: {latency:.3f}s, RTF: {rtf}")
        else:
            print(f"❌ Request failed")
        
        time.sleep(0.5)
    
    if latencies:
        print("\n=== Latency Statistics ===")
        print(f"Min: {min(latencies):.3f}s")
        print(f"Max: {max(latencies):.3f}s")
        print(f"Avg: {sum(latencies)/len(latencies):.3f}s")
        print(f"First request (warmup): {latencies[0]:.3f}s")
        if len(latencies) > 1:
            print(f"Avg (excluding first): {sum(latencies[1:])/len(latencies[1:]):.3f}s")

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("ChatTTS Server Test Suite")
    print("=" * 60)
    print(f"Testing server: {CHATTTS_API_URL}")
    
    # Basic tests
    if not test_health():
        print("\n❌ Server health check failed. Exiting.")
        return
    
    test_voices()
    
    # Generation tests
    test_generation("Hello, this is a basic test of ChatTTS.", voice="female_1")
    
    # Feature tests
    test_multiple_voices()
    test_speed_variations()
    test_temperature_variations()
    test_formats()
    test_long_text()
    
    # Performance benchmark
    benchmark_latency(5)
    
    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)

if __name__ == "__main__":
    # Update the API URL before running
    print("⚠️  Update CHATTTS_API_URL in this script before running!")
    print(f"Current URL: {CHATTTS_API_URL}")
    print("\nStarting tests in 3 seconds...")
    time.sleep(3)
    
    run_all_tests()
