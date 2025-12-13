#!/bin/bash
# Latency Optimization Loop
# Run tests back-to-back until target latency is achieved

set -e

AGENT_ID="$1"
TARGET_LATENCY="$2"
SCENARIO="${3:-quick}"

if [ -z "$AGENT_ID" ] || [ -z "$TARGET_LATENCY" ]; then
    echo "Usage: $0 <agent-id> <target-latency> [scenario]"
    echo "Example: $0 b6b1d141-75a2-43d8-80b8-3decae5c0a92 2.0 quick"
    exit 1
fi

echo "=========================================="
echo "LATENCY OPTIMIZATION LOOP"
echo "=========================================="
echo "Agent ID: $AGENT_ID"
echo "Target Latency: ${TARGET_LATENCY}s"
echo "Scenario: $SCENARIO"
echo "=========================================="
echo ""

ITERATION=1
MAX_ITERATIONS=50

while [ $ITERATION -le $MAX_ITERATIONS ]; do
    echo ""
    echo "==================== ITERATION $ITERATION ===================="
    echo ""
    
    # Run simulation
    if python3 /app/call_flow_simulator.py \
        --agent-id "$AGENT_ID" \
        --scenario "$SCENARIO" \
        --target-latency "$TARGET_LATENCY" \
        --profile; then
        
        echo ""
        echo "✅ SUCCESS! Target latency achieved in $ITERATION iterations"
        echo ""
        exit 0
    else
        echo ""
        echo "❌ Iteration $ITERATION: Target not met"
        echo ""
        
        if [ $ITERATION -eq $MAX_ITERATIONS ]; then
            echo "⚠️  Reached maximum iterations ($MAX_ITERATIONS)"
            echo "   Review the profiling data to identify bottlenecks"
            exit 1
        fi
        
        echo "Press Enter to run next iteration (or Ctrl+C to stop and make changes)..."
        read
        
        ITERATION=$((ITERATION + 1))
    fi
done
