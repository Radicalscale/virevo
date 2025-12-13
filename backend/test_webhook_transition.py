"""
Standalone Webhook Transition Tester
Run this to test how a webhook response affects transitions
"""
import asyncio
import aiohttp
import json

async def test_calendar_webhook():
    """Test the Calendar-check webhook with the provided variables"""
    
    # Variables provided by user
    test_variables = {
        "scheduleTime": "2025-12-10 17:00",
        "timeZone": "EST", 
        "customer_email": "kendrickbowman9@gmail.com",
        "to_number": "+17708336397",
        "customer_name": "Kendrick",
        # Also set common variations
        "callerName": "Kendrick",
        "phone_number": "+17708336397",
    }
    
    print("=== Testing Calendar-check Webhook ===")
    print(f"\nVariables being sent:")
    for k, v in test_variables.items():
        print(f"  {k}: {v}")
    
    # You need to provide the webhook URL here
    # This is typically something like: https://your-webhook-url/calendar-check
    webhook_url = input("\nEnter the Calendar-check webhook URL: ").strip()
    
    if not webhook_url:
        print("No webhook URL provided. Exiting.")
        return
    
    # Build payload - adjust field names based on your webhook's expected format
    payload = {
        "scheduleTime": test_variables["scheduleTime"],
        "timeZone": test_variables["timeZone"],
        "customer_email": test_variables["customer_email"],
        "to_number": test_variables["to_number"],
        "customer_name": test_variables["customer_name"],
    }
    
    print(f"\n--- Sending Request ---")
    print(f"URL: {webhook_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                status = response.status
                response_text = await response.text()
                
                print(f"\n--- Response ---")
                print(f"Status: {status}")
                print(f"Body: {response_text}")
                
                try:
                    response_data = json.loads(response_text)
                    print(f"\nParsed JSON: {json.dumps(response_data, indent=2)}")
                    
                    # Check common success indicators
                    print(f"\n--- Analyzing Response for Transitions ---")
                    
                    # Check for various success indicators
                    success_indicators = [
                        ("status", ["success", "booked", "confirmed", "scheduled"]),
                        ("success", [True, "true", "True"]),
                        ("booked", [True, "true", "True"]),
                        ("confirmed", [True, "true", "True"]),
                        ("result", ["success", "booked", "confirmed"]),
                        ("appointment_status", ["booked", "confirmed", "scheduled"]),
                    ]
                    
                    for field, positive_values in success_indicators:
                        if field in response_data:
                            value = response_data[field]
                            is_positive = value in positive_values or str(value).lower() in [str(v).lower() for v in positive_values]
                            print(f"  {field}: {value} -> {'POSITIVE' if is_positive else 'NEGATIVE'}")
                    
                    # Suggest transition conditions
                    print(f"\n--- Suggested Transition Conditions ---")
                    print("For POSITIVE (appointment booked) path:")
                    if "status" in response_data:
                        print(f'  {{{{webhook_response.status}}}} == "success"')
                        print(f'  {{{{webhook_response.status}}}} == "{response_data["status"]}"')
                    if "success" in response_data:
                        print(f'  {{{{webhook_response.success}}}} == true')
                    if "booked" in response_data:
                        print(f'  {{{{webhook_response.booked}}}} == true')
                        
                except json.JSONDecodeError:
                    print("Response is not JSON")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_calendar_webhook())
