import requests
import json
import time
import sseclient

# Configuration
BASE_URL = "http://localhost:8000"
AGENT_ID = "bbeda238-e8d9-4d8c-b93b-1b7694581adb" # Taken from logs
SESSION_ID = f"test_streaming_{int(time.time())}"

def test_streaming():
    print(f"🚀 Testing Streaming Endpoint for Agent: {AGENT_ID}")
    
    url = f"{BASE_URL}/api/agents/{AGENT_ID}/test/message/stream"
    payload = {
        "session_id": SESSION_ID,
        "message": "I don't like scams.",  # Trigger the scam objection
        "start_node_id": None,
        "measure_real_tts": False
    }
    
    headers = {
        "Content-Type": "application/json",
        # Assuming no auth for local test or handling it via mock if needed
        # In real scenario, we might need a token. 
        # For now, let's see if we can hit it locally if the server is running without strict auth on loopback or if we can mock it.
        # Actually, the router depends on get_current_user. 
        # We might need to mock this or generate a valid token.
        # Let's try to hit it and see.
    }

    try:
        # Note: server must be running. We assume the user has the server running.
        # If not, we can't really verify via HTTP request without starting it.
        # But we are in an agentic environment, maybe we can't assume localhost:8000 is accessible to us?
        # We can run a python script that imports the app and runs a test client.
        pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_streaming()
