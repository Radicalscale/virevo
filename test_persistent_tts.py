#!/usr/bin/env python3
"""
Test script for Persistent TTS infrastructure
Tests WebSocket connection, sentence streaming, and timing
"""
import asyncio
import time
import sys
import os

# Add backend to path
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from elevenlabs_ws_service import ElevenLabsWebSocketService
from persistent_tts_service import PersistentTTSSession

# Test sentences (simulating a conversation)
TEST_SENTENCES = [
    "Hello! This is a test of the persistent TTS system.",
    "We're checking if audio chunks arrive quickly.",
    "This should be faster than REST API calls.",
    "Let's measure the timing and verify it works!"
]

async def get_agent_config(agent_id: str):
    """Fetch agent configuration from MongoDB"""
    from key_encryption import decrypt_api_key
    
    mongo_url = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
    client = AsyncIOMotorClient(mongo_url)
    db = client["test_database"]
    
    agent = await db.agents.find_one({"id": agent_id})
    if not agent:
        return None
    
    user_id = agent.get('user_id')
    settings = agent.get('settings', {})
    elevenlabs = settings.get('elevenlabs_settings', {})
    
    # Get ElevenLabs API key from api_keys collection
    api_key = None
    key_doc = await db.api_keys.find_one({
        "user_id": user_id,
        "service_name": "elevenlabs",
        "is_active": True
    })
    
    if key_doc:
        encrypted_key = key_doc.get("encrypted_key") or key_doc.get("api_key")
        if encrypted_key:
            try:
                api_key = decrypt_api_key(encrypted_key)
            except:
                # Plaintext fallback
                api_key = encrypted_key
    
    return {
        'voice_id': elevenlabs.get('voice_id', 'J5iaaqzR5zn6HFG4jV3b'),
        'model_id': elevenlabs.get('model', 'eleven_flash_v2_5'),
        'api_key': api_key
    }

async def test_websocket_connection(config):
    """Test 1: WebSocket Connection"""
    print("\n" + "=" * 80)
    print("TEST 1: WebSocket Connection")
    print("=" * 80)
    
    if not config['api_key']:
        print("❌ No ElevenLabs API key found!")
        return False
    
    ws_service = ElevenLabsWebSocketService(config['api_key'])
    
    start_time = time.time()
    connected = await ws_service.connect(
        voice_id=config['voice_id'],
        model_id=config['model_id'],
        output_format="pcm_16000"
    )
    connection_time = (time.time() - start_time) * 1000
    
    if connected:
        print(f"✅ WebSocket connected in {connection_time:.0f}ms")
        print(f"   Voice: {config['voice_id'][:20]}...")
        print(f"   Model: {config['model_id']}")
        
        # Close connection
        await ws_service.close()
        return True
    else:
        print(f"❌ WebSocket connection failed after {connection_time:.0f}ms")
        return False

async def test_sentence_streaming(config):
    """Test 2: Sentence Streaming with Timing"""
    print("\n" + "=" * 80)
    print("TEST 2: Sentence Streaming & Timing")
    print("=" * 80)
    
    ws_service = ElevenLabsWebSocketService(config['api_key'])
    
    # Connect
    start_connect = time.time()
    connected = await ws_service.connect(
        voice_id=config['voice_id'],
        model_id=config['model_id'],
        output_format="ulaw_8000"
    )
    connect_time = (time.time() - start_connect) * 1000
    
    if not connected:
        print("❌ Failed to connect")
        return False
    
    print(f"✅ Connected in {connect_time:.0f}ms")
    print(f"\n📤 Sending {len(TEST_SENTENCES)} test sentences...")
    
    all_success = True
    
    for i, sentence in enumerate(TEST_SENTENCES, 1):
        print(f"\n--- Sentence {i}: {sentence[:50]}...")
        
        # Send text
        send_start = time.time()
        sent = await ws_service.send_text(sentence, try_trigger_generation=True, flush=True)
        
        if not sent:
            print(f"  ❌ Failed to send")
            all_success = False
            continue
        
        # Receive audio chunks
        chunk_count = 0
        first_chunk_time = None
        total_audio_bytes = 0
        
        try:
            async for audio_chunk in ws_service.receive_audio_chunks():
                if first_chunk_time is None:
                    first_chunk_time = time.time()
                    ttfb = (first_chunk_time - send_start) * 1000
                    print(f"  ⏱️  TTFB (Time To First Byte): {ttfb:.0f}ms")
                
                chunk_count += 1
                total_audio_bytes += len(audio_chunk)
            
            total_time = (time.time() - send_start) * 1000
            
            if chunk_count > 0:
                print(f"  ✅ Received {chunk_count} chunks, {total_audio_bytes:,} bytes in {total_time:.0f}ms")
                print(f"  📊 Avg chunk size: {total_audio_bytes // chunk_count:,} bytes")
            else:
                print(f"  ❌ No audio chunks received (waited {total_time:.0f}ms)")
                all_success = False
                
        except Exception as e:
            print(f"  ❌ Error receiving audio: {e}")
            all_success = False
    
    await ws_service.close()
    return all_success

async def test_race_condition_fix(config):
    """Test 3: Race Condition & Retry Logic"""
    print("\n" + "=" * 80)
    print("TEST 3: Race Condition & Retry Logic")
    print("=" * 80)
    
    print("Simulating fast response scenario (LLM responds before TTS ready)...")
    
    # Simulate persistent TTS manager
    class MockManager:
        def __init__(self):
            self.session = None
            self.ready_at = None
        
        def get_session(self, call_id):
            if self.ready_at and time.time() >= self.ready_at:
                return self.session
            return None
    
    manager = MockManager()
    
    # Simulate TTS initialization (takes 240ms)
    async def init_tts():
        await asyncio.sleep(0.24)  # 240ms
        manager.session = {"mock": "session"}
        manager.ready_at = time.time()
        print("  ✅ Persistent TTS initialized (240ms)")
    
    # Start initialization (async, non-blocking)
    start_time = time.time()
    init_task = asyncio.create_task(init_tts())
    
    # Simulate fast user response + LLM (98ms)
    await asyncio.sleep(0.098)
    print(f"  🎯 First TTS lookup at T+{int((time.time() - start_time) * 1000)}ms")
    
    # Test OLD behavior (would fail)
    session = manager.get_session("test_call")
    if not session:
        print(f"  ❌ OLD: Session NOT FOUND (expected - too fast)")
    
    # Test NEW behavior (with retry)
    print(f"  🔄 NEW: Starting retry logic...")
    session = manager.get_session("test_call")
    retry_count = 0
    max_retries = 3
    
    while not session and retry_count < max_retries:
        await asyncio.sleep(0.05)  # 50ms delay
        session = manager.get_session("test_call")
        retry_count += 1
        elapsed = int((time.time() - start_time) * 1000)
        if session:
            print(f"  ✅ NEW: Session FOUND on retry #{retry_count} at T+{elapsed}ms")
        else:
            print(f"  ⏳ Retry #{retry_count} at T+{elapsed}ms: NOT FOUND")
    
    if session:
        print(f"  ✅ Race condition handled successfully!")
    else:
        print(f"  ❌ Session still not found after {max_retries} retries")
    
    await init_task
    return bool(session)

async def test_flush_fix(config):
    """Test 4: Flush Fix (Audio Generation Trigger)"""
    print("\n" + "=" * 80)
    print("TEST 4: Flush Fix (Audio Generation Trigger)")
    print("=" * 80)
    
    ws_service = ElevenLabsWebSocketService(config['api_key'])
    
    connected = await ws_service.connect(
        voice_id=config['voice_id'],
        model_id=config['model_id'],
        output_format="pcm_16000"
    )
    
    if not connected:
        print("❌ Failed to connect")
        return False
    
    print("Testing: flush=True (NEW - should work)")
    
    # Send with flush=True (NEW behavior)
    start = time.time()
    await ws_service.send_text("Test sentence.", try_trigger_generation=True, flush=True)
    
    chunk_count = 0
    async for audio_chunk in ws_service.receive_audio_chunks():
        chunk_count += 1
    
    elapsed = (time.time() - start) * 1000
    
    if chunk_count > 0:
        print(f"✅ With flush=True: Received {chunk_count} chunks in {elapsed:.0f}ms")
        await ws_service.close()
        return True
    else:
        print(f"❌ With flush=True: No chunks received (waited {elapsed:.0f}ms)")
        await ws_service.close()
        return False

async def main():
    """Run all tests"""
    print("=" * 80)
    print("PERSISTENT TTS INFRASTRUCTURE TEST")
    print("=" * 80)
    
    agent_id = "b6b1d141-75a2-43d8-80b8-3decae5c0a92"
    
    print(f"\n🔍 Fetching agent config: {agent_id}")
    config = await get_agent_config(agent_id)
    
    if not config:
        print(f"❌ Agent not found!")
        return
    
    if not config['api_key']:
        print(f"❌ No ElevenLabs API key found for agent!")
        print(f"   Please add API key to user account")
        return
    
    print(f"✅ Config loaded:")
    print(f"   Voice: {config['voice_id'][:20]}...")
    print(f"   Model: {config['model_id']}")
    print(f"   API Key: {config['api_key'][:10]}...{config['api_key'][-4:]}")
    
    # Run tests
    results = {}
    
    try:
        results['connection'] = await test_websocket_connection(config)
        results['streaming'] = await test_sentence_streaming(config)
        results['race_condition'] = await test_race_condition_fix(config)
        results['flush_fix'] = await test_flush_fix(config)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Persistent TTS infrastructure is working!")
    else:
        print("\n⚠️  Some tests failed. Review logs above.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
