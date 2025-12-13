#!/usr/bin/env python3
"""
Direct TTS WebSocket Test - Verifying the fix matches master code
"""
import asyncio
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from elevenlabs_ws_service import ElevenLabsWebSocketService

ELEVEN_API_KEY = os.environ.get('ELEVEN_API_KEY', 'sk_fd288b72abe95953baafcfbf561d6fe9d2af4dabf5458e12')
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
MODEL_ID = "eleven_flash_v2_5"

async def test_websocket_tts():
    print("=" * 60)
    print("ElevenLabs WebSocket TTS Test (Master Code Match)")
    print("=" * 60)
    
    test_cases = [
        {"name": "Short greeting", "text": "Hello!"},
        {"name": "With SSML", "text": 'Well, uh<break time="300ms"/> I dont know.'},
        {"name": "Medium", "text": "Hi there, how can I help you today?"},
        {"name": "Single word", "text": "Kendrick?"}
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n--- Test {i+1}: {test['name']} ---")
        print(f"Text: {test['text']}")
        
        service = ElevenLabsWebSocketService(ELEVEN_API_KEY)
        
        try:
            start = time.time()
            connected = await service.connect(VOICE_ID, MODEL_ID)
            connect_time = (time.time() - start) * 1000
            
            if not connected:
                print(f"❌ Failed to connect")
                continue
            
            print(f"✅ Connected in {connect_time:.0f}ms")
            
            # Send text + empty flush (exactly like master code)
            await service.send_text(test['text'], try_trigger_generation=True, flush=False)
            await service.send_text("", try_trigger_generation=False, flush=True)
            
            # Receive audio (using async for like master code)
            recv_start = time.time()
            total_bytes = 0
            chunk_count = 0
            first_chunk_time = None
            
            async for chunk in service.receive_audio_chunks():
                chunk_count += 1
                total_bytes += len(chunk)
                if first_chunk_time is None:
                    first_chunk_time = (time.time() - recv_start) * 1000
            
            total_time = (time.time() - start) * 1000
            recv_time = (time.time() - recv_start) * 1000
            
            print(f"✅ Results:")
            print(f"   TTFB: {first_chunk_time:.0f}ms" if first_chunk_time else "   TTFB: N/A")
            print(f"   Chunks: {chunk_count}, Bytes: {total_bytes}")
            print(f"   Receive time: {recv_time:.0f}ms")
            print(f"   Total E2E: {total_time:.0f}ms")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await service.close()
        
        await asyncio.sleep(0.3)
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_websocket_tts())
