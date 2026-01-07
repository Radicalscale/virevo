import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from maya_tts_service import MayaTTSService

async def test_maya():
    # RunPod Direct TCP (Fastest)
    # pod_id = "kic2rjdm12mk4o"
    # api_url = f"https://{pod_id}-8000.proxy.runpod.net"
    api_url = "http://203.57.40.173:10197"
    
    print(f"🧪 Testing Maya TTS at: {api_url}")
    
    service = MayaTTSService(api_url=api_url)
    
    # Test 1: Standard Generation
    print("\n[1] Testing Standard Generation...")
    text = "Hello! This is a test of the Maya TTS system on RunPod."
    audio = await service.generate_speech(text)
    
    if audio:
        with open("test_maya_standard.wav", "wb") as f:
            f.write(audio)
        print(f"✅ Success! Saved test_maya_standard.wav ({len(audio)} bytes)")
    else:
        print("❌ Standard generation failed.")

    # Test 2: Streaming Generation
    print("\n[2] Testing Streaming Generation...")
    stream_text = "This is a streaming test to verify low latency playback."
    
    with open("test_maya_stream.wav", "wb") as f:
        count = 0
        async for chunk in service.stream_speech(stream_text):
            f.write(chunk)
            count += 1
            sys.stdout.write(f"\rReceived chunk {count}...")
            sys.stdout.flush()
            
    print(f"\n✅ Streaming complete! Saved test_maya_stream.wav")

if __name__ == "__main__":
    asyncio.run(test_maya())
