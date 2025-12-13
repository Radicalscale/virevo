#!/usr/bin/env python3
"""
Comprehensive test of webhook variable extraction and propagation
Simulates the exact flow: Converter webhook -> variable update -> Scheduler uses updated value
"""
import json
import re
import sys

print("=" * 80)
print("TESTING WEBHOOK VARIABLE EXTRACTION & PROPAGATION")
print("=" * 80)

# Simulate session variables at start
session_variables = {
    "customer_name": "Kendrick",
    "customer_email": "kendrickbowman9@gmail.com",
    "to_number": "+17708336397",
    "from_number": "+14048000152",
    "scheduleTime": "November 3rd 11:30 AM",  # Original unconverted value
    "timeZone": "Eastern"
}

print("\n📋 INITIAL SESSION VARIABLES:")
for key, val in session_variables.items():
    print(f"  {key}: {val}")

print("\n" + "=" * 80)
print("STEP 1: CONVERTER WEBHOOK EXECUTES")
print("=" * 80)

# Simulate the exact n8n converter webhook response (as Python dict, like httpx returns)
converter_response_data = {
    "response_type": "tool_call_response",
    "tool_calls_results": [
        {
            "tool_call_id": "",
            "result": "Great! The data conversion is complete. The updated value for scheduleTime is - ```json\n{\n  \"scheduleTime\": \"2025-11-03 11:30\"\n}\n```"
        }
    ]
}

print("\n📥 Converter webhook returns (as dict):")
print(json.dumps(converter_response_data, indent=2)[:200] + "...")

# This is what we'd get after successful httpx response.json()
response_data = converter_response_data
print("✅ Response received as dict (from httpx)")

print(f"Response keys: {list(response_data.keys())}")

# Extract variables (simulating backend extraction logic)
print("\n🔄 Extracting fields from webhook response...")

actual_data = response_data

# Check for n8n tool_calls_results format
if "tool_calls_results" in actual_data:
    print("📦 Detected n8n tool_calls_results format")
    
    # Get result string
    result_str = actual_data.get("tool_calls_results", [{}])[0].get("result", "")
    print(f"Result string: {result_str[:80]}...")
    
    # Extract JSON from markdown block
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_str, re.DOTALL)
    if json_match:
        print("✅ Found ```json block")
        json_str = json_match.group(1)
        print(f"Extracted: {json_str}")
        
        # Parse extracted JSON
        actual_data = json.loads(json_str)
        print(f"✅ Parsed extracted JSON: {actual_data}")
    else:
        print("❌ Could not find ```json block")
        sys.exit(1)
else:
    print("❌ Not n8n format")
    sys.exit(1)

# Update session variables with extracted data
print("\n📝 Updating session variables...")
updated_count = 0
for field_name, field_value in actual_data.items():
    if field_name not in ["success", "message", "error", "status", "response_type"]:
        old_value = session_variables.get(field_name, "NOT SET")
        session_variables[field_name] = field_value
        print(f"  ✓ {field_name}: {old_value} → {field_value}")
        updated_count += 1

if updated_count > 0:
    print(f"✅ Updated {updated_count} session variables")
else:
    print("❌ No variables updated!")
    sys.exit(1)

print("\n" + "=" * 80)
print("STEP 2: SCHEDULER WEBHOOK EXECUTES")
print("=" * 80)

# Simulate scheduler webhook using session variables
print("\n🔍 Scheduler extracts variables from session:")

scheduler_variables = {
    "scheduleTime": session_variables.get("scheduleTime"),
    "timeZone": session_variables.get("timeZone"),
    "customer_email": session_variables.get("customer_email"),
    "to_number": session_variables.get("to_number"),
    "callerName": session_variables.get("customer_name")
}

for key, val in scheduler_variables.items():
    print(f"  ✓ {key}: {val}")

# Build webhook request
print("\n📤 Scheduler webhook request body:")
scheduler_request = json.dumps(scheduler_variables, indent=2)
print(scheduler_request)

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

# Verify the critical update
old_schedule_time = "November 3rd 11:30 AM"
new_schedule_time = scheduler_variables["scheduleTime"]

print(f"\n🔍 Checking if scheduleTime was updated:")
print(f"  Original: {old_schedule_time}")
print(f"  Updated:  {new_schedule_time}")

if new_schedule_time == "2025-11-03 11:30":
    print("\n✅ SUCCESS! Variable was properly updated and propagated!")
    print("\n" + "=" * 80)
    print("FINAL SESSION VARIABLES:")
    print("=" * 80)
    for key, val in session_variables.items():
        print(f"  {key}: {val}")
    print("\n" + "=" * 80)
    print("✅ TEST PASSED - Webhook variable extraction and propagation working!")
    print("=" * 80)
    sys.exit(0)
else:
    print(f"\n❌ FAILED! Variable not updated correctly")
    print(f"Expected: 2025-11-03 11:30")
    print(f"Got: {new_schedule_time}")
    sys.exit(1)
