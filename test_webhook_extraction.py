#!/usr/bin/env python3
"""Test webhook response extraction logic"""
import json
import re

# Simulate the exact response from n8n converter webhook (with proper escaping)
test_response = {
    "response_type": "tool_call_response",
    "tool_calls_results": [
        {
            "tool_call_id": "",
            "result": "Great! The data conversion is complete. The updated value for scheduleTime is - ```json\n{\n  \"scheduleTime\": \"2025-11-03 02:09\"\n}\n```"
        }
    ]
}

print("=" * 60)
print("Testing Webhook Response Extraction")
print("=" * 60)

response_data = test_response

# Check for n8n format
print("\n1. Checking for n8n tool_calls_results format...")
if "tool_calls_results" in response_data:
    print("✅ Detected n8n format")
    
    # Extract result from array
    result_str = response_data.get("tool_calls_results", [{}])[0].get("result", "")
    print(f"Result string: {result_str[:100]}...")
    
    # Try to extract JSON
    print("\n2. Extracting JSON from result string...")
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_str, re.DOTALL)
    if json_match:
        print("✅ Found ```json block")
        json_str = json_match.group(1)
        print(f"Extracted JSON string: {repr(json_str[:50])}")
        
        # Parse the JSON
        print("\n3. Parsing extracted JSON...")
        try:
            actual_data = json.loads(json_str)
            print("✅ Successfully parsed extracted JSON")
            print(f"Data: {actual_data}")
            
            # Extract scheduleTime
            print("\n4. Extracting scheduleTime variable...")
            if "scheduleTime" in actual_data:
                schedule_time = actual_data["scheduleTime"]
                print(f"✅ scheduleTime = {schedule_time}")
                print("\n" + "=" * 60)
                print("SUCCESS! Variable extraction working correctly")
                print("=" * 60)
            else:
                print("❌ scheduleTime not found in data")
        except Exception as e:
            print(f"❌ Failed to parse extracted JSON: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Could not find ```json block in result")
        print(f"Result was: {result_str}")
else:
    print("❌ Not n8n format")
    print(f"Keys: {list(response_data.keys())}")

