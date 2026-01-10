
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio

# Import the app (we need to find where 'app' is defined, likely server.py)
# We might need to mock get_current_user dependent
from backend.agent_test_router import router
from fastapi import FastAPI

# Create a dummy app to mount the router
app = FastAPI()
app.include_router(router)

client = TestClient(app)

# Mock dependencies
@pytest.fixture
def mock_db():
    with patch('backend.agent_test_router.get_db') as mock:
        yield mock

@pytest.fixture
def mock_get_current_user():
    # Override dependency
    app.dependency_overrides[get_current_user] = lambda: {"id": "user123"}
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_session():
    with patch('backend.agent_test_router.get_or_create_session') as mock:
        session = AsyncMock()
        session_data = {"conversation": [], "node_transitions": [], "metrics": {"total_turns": 0, "total_latency": 0}}
        
        # Mock process_user_input to simulate streaming
        async def mock_process(message, stream_callback=None):
            if stream_callback:
                await stream_callback("Valid ")
                await asyncio.sleep(0.01)
                await stream_callback("chunk ")
                await asyncio.sleep(0.01)
                await stream_callback("received.")
            return {"text": "Valid chunk received.", "end_call": False}
            
        session.process_user_input = mock_process
        session.agent_config = {"call_flow": []}
        
        mock.return_value = (session, session_data)
        yield mock

def test_streaming_endpoint(mock_session):
    # Try to import get_current_user to override
    try:
        from backend.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: {"id": "user123"}
    except ImportError:
        pass # Might fail if imports are complex, but we'll try basic path

    with patch('backend.agent_test_router.get_db') as mock_db:
        mock_db.return_value.agents.find_one = AsyncMock(return_value={"id": "agent123", "user_id": "user123"})
        
        response = client.post(
            "/api/agents/agent123/test/message/stream",
            json={
                "session_id": "sess123",
                "message": "Hello",
                "start_node_id": None,
                "measure_real_tts": False
            }
        )
        
        assert response.status_code == 200
        # verify streaming content
        content = response.content.decode('utf-8')
        print("Response Content:", content)
        assert "data: " in content
        assert "Valid " in content
        assert "chunk " in content
