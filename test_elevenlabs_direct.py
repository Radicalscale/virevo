#!/usr/bin/env python3
"""
Test ElevenLabs API directly to see if it's reachable
"""

import asyncio
import httpx
import os
import time

ELEVEN_API_KEY = os.environ.get('ELEVEN_API_KEY')

async def test_elevenlabs():
    """Test ElevenLabs API with simple request"""
    
    text = "Alright, love that! So, are you working for someone right now or do you run your own business?"
    voice_id = "J5iaaqzR5zn6HFG4jV3b"  # Same voice from logs
    model = "eleven_flash_v2_5"
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "use_speaker_boost": True,
            "speed": 1.0,
            "style": 0.0
        },
        "apply_text_normalization": "on",
        "enable_ssml_parsing": False,
        "optimize_streaming_latency": 4
    }
    
    print("="*80)
    print("TESTING ELEVENLABS API DIRECTLY")
    print("="*80)
    print(f"\nText: {text}")
    print(f"Voice ID: {voice_id}")
    print(f"Model: {model}")
    print(f"URL: {url}")
    print(f"\nData payload:")
    print(f"  text length: {len(text)}")
    print(f"  model_id: {data['model_id']}")
    print(f"  voice_settings: {data['voice_settings']}")
    print(f"  apply_text_normalization: {data['apply_text_normalization']}")
    
    print(f"\n{'='*80}")
    print("ATTEMPTING CONNECTION")
    print(f"{'='*80}\n")
    
    try:
        start_time = time.time()
        
        # Try with 10 second timeout like in our code
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"[{time.time() - start_time:.3f}s] HTTP client created")
            
            print(f"[{time.time() - start_time:.3f}s] Sending POST request...")
            async with client.stream('POST', url, headers=headers, json=data) as response:
                print(f"[{time.time() - start_time:.3f}s] ✓ Connection established!")
                print(f"[{time.time() - start_time:.3f}s] Response status: {response.status_code}")
                
                if response.status_code == 200:
                    chunks = []
                    chunk_count = 0
                    
                    print(f"[{time.time() - start_time:.3f}s] Streaming chunks...")
                    async for chunk in response.aiter_bytes():
                        chunk_count += 1
                        chunks.append(chunk)
                        if chunk_count == 1:
                            print(f"[{time.time() - start_time:.3f}s] ✓ First chunk received ({len(chunk)} bytes)")
                    
                    audio_data = b''.join(chunks)
                    print(f"[{time.time() - start_time:.3f}s] ✓ Complete! {chunk_count} chunks, {len(audio_data)} bytes total")
                    print(f"\n✅ SUCCESS - ElevenLabs API is working correctly")
                    return True
                else:
                    error_text = await response.aread()
                    print(f"❌ ERROR {response.status_code}: {error_text}")
                    return False
                    
    except httpx.ConnectTimeout as e:
        elapsed = time.time() - start_time
        print(f"[{elapsed:.3f}s] ❌ CONNECTION TIMEOUT")
        print(f"Error: {e}")
        print(f"\nThis means ElevenLabs API is unreachable or not responding")
        return False
    except httpx.ReadTimeout as e:
        elapsed = time.time() - start_time
        print(f"[{elapsed:.3f}s] ❌ READ TIMEOUT")
        print(f"Error: {e}")
        print(f"\nThis means connection was established but data transfer timed out")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{elapsed:.3f}s] ❌ ERROR: {type(e).__name__}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_elevenlabs())
    exit(0 if result else 1)
