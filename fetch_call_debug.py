
import os
import sys
import telnyx
import json
from datetime import datetime

# Load environment variables (ensure TELNYX_API_KEY is set in your env)
TELNYX_API_KEY = os.environ.get('TELNYX_API_KEY')

if not TELNYX_API_KEY:
    print("❌ Error: TELNYX_API_KEY environment variable is not set.")
    sys.exit(1)

telnyx.api_key = TELNYX_API_KEY

def json_converter(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

def fetch_call_debug_info(call_control_id):
    """
    Retrieves status and debug info for a specific Telnyx call.
    """
    print(f"🔍 Fetching debug info for Call ID: {call_control_id}...")
    
    debug_data = {
        "call_id": call_control_id,
        "timestamp": datetime.now().isoformat(),
        "call_details": None,
        "recordings": [],
        "errors": []
    }

    # 1. Try to retrieve Call Information
    # Note: Telnyx Call Control API generally requires an active call for 'retrieve',
    # OR we might be able to find it in CDRs/Reports if it's historic.
    # We'll try the standard retrieve first.
    try:
        # Check standard call retrieve (often only works for active calls)
        try:
            call = telnyx.Call.retrieve(call_control_id)
            debug_data["call_details"] = call
            print("✅ Found active/cached call details.")
        except telnyx.error.ResourceNotFoundError:
            print("⚠️  Call not found in active sessions (expected for finished calls).")
            # If not active, we might try to look up CDRs if we had the UUID, 
            # but usually Call Control ID is ephemeral. 
            # Let's try to verify if it exists as a minimal check.
            debug_data["call_details"] = {"status": "not_active_or_not_found"}
            
    except Exception as e:
        debug_data["errors"].append(f"Call Retrieve Error: {str(e)}")

    # 2. List Recordings associated with this call (if mapped)
    # This is often the best artifact for "did this happen?"
    try:
        # Note: Filtering recordings by specific call control ID filter might vary 
        # depending on API capabilities. We'll list recent and filter client-side if needed,
        # or use specific filters if available.
        # For this script, we'll try a precise filter if the SDK supports it.
        # Telnyx 'list' often accepts filters.
        print("🔍 Searching for recordings...")
        recordings = telnyx.Recording.list(filter={"call_control_id": call_control_id})
        
        for rec in recordings.data:
            debug_data["recordings"].append({
                "id": rec.id,
                "created_at": rec.created_at,
                "status": rec.status,
                "download_urls": rec.download_urls,
                "duration": getattr(rec, "duration", None)
            })
        print(f"✅ Found {len(debug_data['recordings'])} recordings.")
        
    except Exception as e:
        # debug_data["errors"].append(f"Recording Fetch Error: {str(e)}")
        # Silence this for now as it can be noisy if filter is invalid
        print(f"⚠️  Recording fetch warning: {e}")

    # Output detailed JSON
    print("\n" + "="*40)
    print("DEBUG REPORT")
    print("="*40)
    print(json.dumps(debug_data, indent=2, default=json_converter))
    print("="*40)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_call_debug.py <call_control_id>")
        sys.exit(1)
        
    target_call_id = sys.argv[1]
    fetch_call_debug_info(target_call_id)
