#!/bin/bash
# Test the Schedule Tester2 agent flow end-to-end

AGENT_ID="68bbb816-50d0-4d36-ae82-f04473e67483"
SESSION_ID="continuous-test-$(date +%s)"
URL="http://localhost:8001/api/agents/$AGENT_ID/message"

echo "========================================="
echo "Testing Schedule Tester2 Agent Flow"
echo "Session ID: $SESSION_ID"
echo "========================================="

echo ""
echo "Message 1: Initial greeting"
echo "-----------------------------------------"
RESPONSE=$(curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Hi\",\"session_id\":\"$SESSION_ID\"}")
echo "$RESPONSE" | python3 -m json.tool | grep '"text"'

sleep 2

echo ""
echo "Message 2: Provide appointment info"
echo "-----------------------------------------"
RESPONSE=$(curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"I want to book for November 5th at 3pm Eastern\",\"session_id\":\"$SESSION_ID\"}")
echo "$RESPONSE" | python3 -m json.tool | grep '"text"'

echo ""
echo "========================================="
echo "Checking backend logs for flow execution"
echo "========================================="
tail -n 200 /var/log/supervisor/backend.err.log | grep -E "Using flow node|converter|Scheduler|Extracting fields|Updated session variable" | tail -30
