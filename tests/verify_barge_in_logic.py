import asyncio
import sys
import os
import logging
from unittest.mock import MagicMock, AsyncMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

# Mock dependencies before importing core_calling_service
sys.modules['rag_service'] = MagicMock()
sys.modules['voicemail_detector'] = MagicMock()
sys.modules['natural_delivery_middleware'] = MagicMock()
sys.modules['redis_service'] = MagicMock()

# Import CallSession
from core_calling_service import CallSession

# CallSession needs some basic mocks
async def test_barge_in_handler():
    print("🧪 Starting Barge-In Verification...")
    
    # Mock Logger
    logging.basicConfig(level=logging.INFO)
    
    # Mock Agent Config
    agent_config = {
        "id": "test_agent",
        "user_id": "test_user",
        "settings": {
            "llm_provider": "openai",
            "barge_in_settings": {
                "enable_verbose_barge_in": True,
                "word_count_threshold": 10,
                "interruption_prompt": "Interrupt politely."
            }
        }
    }
    
    # Mock DB
    mock_db = MagicMock()
    
    # Instantiate CallSession
    session = CallSession("test_call_id", agent_config, db=mock_db)
    
    # Mock LLM Client
    mock_llm_response = MagicMock()
    mock_llm_response.choices = [MagicMock(message=MagicMock(content="Hold on, let me stop you there."))]
    
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_llm_response
    
    # Mock get_llm_client helper
    session.get_llm_client_for_session = AsyncMock(return_value=mock_client)
    
    # Mock Speak Callback
    callback_called = False
    callback_text = ""
    
    async def mock_speak_callback(text):
        nonlocal callback_called, callback_text
        callback_called = True
        callback_text = text
        print(f"🗣️ Callback received text: '{text}'")
    
    # Test Data: Long partial transcript
    long_transcript = "This is a very long sentence that keeps going and going and really should be interrupted because I am just rambling on and on without stopping."
    
    print(f"📝 Testing with transcript: '{long_transcript}'")
    
    # Call the handler
    await session.handle_verbose_interruption(long_transcript, mock_speak_callback)
    
    # Verify results
    if callback_called:
        print("✅ SUCCESS: Callback was called.")
        print(f"✅ Interruption generated: '{callback_text}'")
    else:
        print("❌ FAILURE: Callback was NOT called.")
        exit(1)
        
    if "Hold on" in callback_text:
        print("✅ Response matches mock.")
    else:
        print("❌ Unexpected response content.")

if __name__ == "__main__":
    asyncio.run(test_barge_in_handler())
