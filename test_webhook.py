"""
Test script to simulate a Telnyx webhook for incoming call
This helps debug if the webhook handler is working correctly
"""
import requests
import json

BACKEND_URL = "https://voice-overlap-debug.preview.emergentagent.com"

# Simulate an incoming call webhook from Telnyx
test_webhook_payload = {
    "data": {
        "event_type": "call.initiated",
        "id": "test-event-123",
        "occurred_at": "2025-11-06T12:00:00.000000Z",
        "payload": {
            "call_control_id": "v3:test-call-123",
            "connection_id": "your-connection-id",
            "call_leg_id": "test-leg-123",
            "call_session_id": "test-session-123",
            "direction": "incoming",
            "from": "+15551234567",  # Caller's number
            "to": "+14048000152",    # Your Telnyx number (E.164 format)
            "state": "parked"
        },
        "record_type": "event"
    },
    "meta": {
        "attempt": 1,
        "delivered_to": f"{BACKEND_URL}/api/telnyx/webhook"
    }
}

print("🧪 Testing Telnyx Webhook Handler")
print("=" * 60)
print(f"\n📞 Simulating incoming call to: {test_webhook_payload['data']['payload']['to']}")
print(f"📞 From: {test_webhook_payload['data']['payload']['from']}")
print(f"\n📡 Sending webhook to: {BACKEND_URL}/api/telnyx/webhook")
print("\nPayload:")
print(json.dumps(test_webhook_payload, indent=2))
print("\n" + "=" * 60)

try:
    response = requests.post(
        f"{BACKEND_URL}/api/telnyx/webhook",
        json=test_webhook_payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\n✅ Response Status: {response.status_code}")
    print(f"📝 Response Body: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ Webhook handler is working!")
        print("\nNext steps:")
        print("1. Check backend logs: tail -f /var/log/supervisor/backend.out.log")
        print("2. Look for 'TELNYX WEBHOOK RECEIVED' messages")
        print("3. Verify the phone number lookup is working")
    else:
        print(f"\n❌ Webhook handler returned error: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error sending webhook: {e}")
    print("\nPossible issues:")
    print("1. Backend server not running")
    print("2. Network connectivity issue")
    print("3. Webhook endpoint not accessible")
