# Multi-Worker Call Architecture - Complete Flow

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAILWAY DEPLOYMENT                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Gunicorn (4 Workers) + Uvicorn                │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │  │
│  │  │Worker 1│ │Worker 2│ │Worker 3│ │Worker 4│           │  │
│  │  │Port 800│ │Port 800│ │Port 800│ │Port 800│           │  │
│  │  └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘           │  │
│  │       │          │          │          │                │  │
│  │       └──────────┴──────────┴──────────┘                │  │
│  │                    │                                     │  │
│  │              Load Balancer                               │  │
│  │                    │                                     │  │
│  │         ┌──────────┴──────────┐                         │  │
│  │         │                     │                         │  │
│  │    HTTP Requests        WebSocket                       │  │
│  │         │                  Connections                   │  │
│  └─────────┼──────────────────────┼────────────────────────┘  │
└────────────┼──────────────────────┼───────────────────────────┘
             │                      │
   ┌─────────┴─────────┐   ┌────────┴──────────┐
   │   MongoDB Atlas   │   │   Telnyx API      │
   │  (User Data,      │   │   (Voice Calls)   │
   │   Agents, Keys)   │   │                   │
   └───────────────────┘   └───────────────────┘
             │
   ┌─────────┴─────────┐
   │   Redis           │
   │ (Call State Sync) │
   │  Cross-Worker     │
   └───────────────────┘
```

## Call Flow - Line by Line

### STEP 1: User Clicks "Call" Button in Frontend
**File**: `/app/frontend/src/components/AgentDetail.jsx` (line ~450)
**Code**:
```javascript
const response = await api.post('/telnyx/call/outbound', {
  agent_id: agent.id,
  to_number: phoneNumber,
  custom_variables: { customer_name: "Kendrick" }
});
```
**What happens**: HTTP POST → Load Balancer → Random Worker (e.g., Worker 2)

---

### STEP 2: Worker 2 Receives Outbound Call Request
**File**: `/app/backend/server.py` (line 1520-1660)
**Worker**: Worker 2 (randomly selected by load balancer)

**Line 1568-1575**: Get BACKEND_URL, create WebSocket URL
```python
backend_url = os.environ.get("BACKEND_URL")  # "api.li-ai.org"
ws_url = f"wss://{backend_url}"  # "wss://api.li-ai.org"
stream_url = f"{ws_url}/api/telnyx/audio-stream"  # WebSocket URL for Telnyx
```

**Line 1578-1585**: Get user's API keys from MongoDB
```python
telnyx_api_key = await get_api_key(current_user["id"], "telnyx")  # From MongoDB
telnyx_connection_id = await get_api_key(current_user["id"], "telnyx_connection_id")
```

**Line 1612-1650**: Call Telnyx API to initiate call
```python
call_result = await telnyx_service.dial(
    to_number=request.to_number,
    from_number=from_number,
    webhook_url=webhook_url,  # "https://api.li-ai.org/api/telnyx/webhook"
    stream_url=stream_url,  # "wss://api.li-ai.org/api/telnyx/audio-stream"
    enable_amd=enable_amd
)
```
**Result**: Telnyx returns `call_control_id` (e.g., "v3:pqwvHCdrgy...")

**Line 1645-1660**: Store call data in Redis + Worker 2's memory
```python
call_data = {
    "agent_id": request.agent_id,  # "474917c1-4888-47b8-b76b-f11a18f19d39"
    "agent": agent_sanitized,  # Full agent config
    "custom_variables": request.custom_variables,
    "session": None
}

# CRITICAL: Store in Redis for cross-worker access
redis_service.set_call_data(call_control_id, call_data, ttl=3600)

# Also store in Worker 2's memory (fallback)
active_telnyx_calls[call_control_id] = call_data
```

---

### STEP 3: Telnyx Sends "call.answered" Webhook
**Timing**: ~5 seconds later (when user answers phone)
**Destination**: `POST https://api.li-ai.org/api/telnyx/webhook`
**Worker**: Load balancer routes to Worker 4 (different worker!)

**File**: `/app/backend/server.py` (line 4566-4700)
**Worker**: Worker 4

**Line 4571-4585**: Retrieve call_data from Redis
```python
call_data = redis_service.get_call_data(call_control_id)  # Get from Redis
# Worker 4 doesn't have this in memory, so MUST use Redis
```

**Line 4620-4625**: Get user's Telnyx keys again (for recording)
```python
telnyx_api_key = await get_api_key(user_id, "telnyx")  # From MongoDB
telnyx_connection_id = await get_api_key(user_id, "telnyx_connection_id")
```

**Line 4658-4670**: Create CallSession object
```python
session = await create_call_session(
    call_control_id,
    agent,
    agent_id=agent.get("id"),
    user_id=agent.get("user_id"),
    db=db
)
# Session created in Worker 4's memory (active_sessions dict)
```

**Line 4675-4682**: Store session in call_data
```python
call_data["session"] = session  # ❌ PROBLEM: Session object can't be serialized!
call_data["agent_id"] = agent.get("id")  # Added in fix
call_data["user_id"] = agent.get("user_id")  # Added in fix

# ❌ CRITICAL BUG: This fails silently because session object isn't JSON-serializable!
redis_service.set_call_data(call_control_id, call_data, ttl=3600)
```

**Line 4684**: Mark session ready
```python
redis_service.mark_session_ready(call_control_id, ttl=3600)
# Sets flag in Redis: "session_ready:{call_control_id}" = True
```

---

### STEP 4: Telnyx Connects to WebSocket
**Timing**: Immediately after call answers (~same time as webhook)
**Destination**: `wss://api.li-ai.org/api/telnyx/audio-stream`
**Worker**: Load balancer routes to Worker 6 (yet another different worker!)

**File**: `/app/backend/server.py` (line 2635-2810)
**Worker**: Worker 6

**Line 2708-2721**: Wait for call_data in Redis
```python
call_data = redis_service.get_call_data(call_control_id)  # Get from Redis
# Success! call_data exists (created by Worker 2)
```

**Line 2727-2746**: Try to find session
```python
session = await get_call_session(call_control_id)
# ❌ FAILS! Session is in Worker 4's memory, not Worker 6's
```

**Line 2736-2741**: Wait for session_ready flag
```python
session_ready = redis_service.is_session_ready(call_control_id)
# ✅ Returns True (Worker 4 set this)
```

**Line 2746**: Try to get session again
```python
session = await get_call_session(call_control_id)
# ❌ STILL FAILS! Session is still in Worker 4's memory only
```

**Line 2750-2765**: Fallback - create session in Worker 6
```python
call_data_fresh = redis_service.get_call_data(call_control_id)
agent = call_data_fresh.get("agent")
agent_id = call_data_fresh.get("agent_id")  # ❌ THIS IS MISSING!

# ❌ ERROR: agent_id not in call_data because Redis serialization failed
logger.error(f"❌ No agent data in call_data. Keys: {list(call_data_fresh.keys())}")
```

---

## THE ROOT CAUSE

**Problem 1**: `CallSession` object stored in `call_data["session"]`
- Python objects can't be JSON-serialized
- When `redis_service.set_call_data()` tries to serialize, it fails or strips the session
- Any updates AFTER adding the session (like agent_id, user_id) are lost

**Problem 2**: Session stored in Worker-specific memory (`active_sessions` dict)
- Worker 4 creates session → stores in Worker 4's `active_sessions`
- Worker 6 handles WebSocket → can't find session in its own `active_sessions`
- Workers don't share memory - each has its own `active_sessions` dictionary

---

## THE FIX

### Option 1: Don't Store Session in Redis (RECOMMENDED)
Store only serializable data in Redis, keep sessions in worker memory, recreate if needed.

**File**: `/app/backend/server.py` (line 4675-4682)
```python
# DON'T add session to call_data before Redis update
call_data["agent_id"] = agent.get("id")
call_data["user_id"] = agent.get("user_id")

# Update Redis FIRST (without session)
redis_service.set_call_data(call_control_id, call_data, ttl=3600)

# THEN add session to local call_data (won't go to Redis)
call_data["session"] = session
```

### Option 2: Make Session Shareable (COMPLEX)
Store session data in Redis as serializable dict, reconstruct CallSession from dict when needed.

---

## Data Flow Chart

```
┌──────────────────────────────────────────────────────────────────┐
│                    CALL INITIATION (Worker 2)                     │
├──────────────────────────────────────────────────────────────────┤
│ 1. Frontend calls POST /telnyx/call/outbound                    │
│ 2. Worker 2 gets user's API keys from MongoDB                   │
│ 3. Worker 2 calls Telnyx API → gets call_control_id             │
│ 4. Worker 2 stores call_data to Redis:                          │
│    {                                                              │
│      "agent_id": "xxx",                                           │
│      "agent": {...},                                              │
│      "custom_variables": {...}                                    │
│    }                                                              │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  CALL ANSWERED (Worker 4)                         │
├──────────────────────────────────────────────────────────────────┤
│ 1. Telnyx sends "call.answered" webhook → Worker 4              │
│ 2. Worker 4 gets call_data from Redis                           │
│ 3. Worker 4 creates CallSession object                           │
│ 4. Worker 4 stores session in Worker 4's active_sessions dict    │
│ 5. Worker 4 tries to update Redis with session → ❌ FAILS       │
│ 6. Worker 4 sets "session_ready" flag in Redis → ✅             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                WEBSOCKET CONNECTION (Worker 6)                    │
├──────────────────────────────────────────────────────────────────┤
│ 1. Telnyx connects WebSocket → Worker 6                         │
│ 2. Worker 6 gets call_data from Redis                           │
│ 3. Worker 6 checks Worker 6's active_sessions → ❌ Not found    │
│ 4. Worker 6 waits for "session_ready" flag → ✅ Found           │
│ 5. Worker 6 checks Worker 6's active_sessions again → ❌ FAIL   │
│ 6. Worker 6 tries to recreate session from Redis call_data       │
│ 7. agent_id missing from Redis → ❌ FAILS                       │
│ 8. WebSocket closes → Call ends silently                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Concurrency Model (20+ Simultaneous Calls)

### How It Should Work:
1. **Load Balancer**: Distributes incoming requests across 4 workers
2. **Redis**: Central store for all call state (accessible by all workers)
3. **MongoDB**: Persistent storage for users, agents, API keys
4. **Worker Memory**: Each worker maintains its own `active_sessions` dict

### For 20 Concurrent Calls:
- Each worker handles ~5 calls
- Call state synced via Redis
- If Worker 1 creates a session, Worker 2 can recreate it from Redis data
- Sessions are lightweight - just conversation history and config

---

## Required Fix

**File**: `/app/backend/server.py` (line 4675-4682)

**Current (Broken)**:
```python
call_data["session"] = session  # Non-serializable!
call_data["agent_id"] = agent.get("id")
redis_service.set_call_data(call_control_id, call_data, ttl=3600)  # Fails
```

**Fixed**:
```python
# Store serializable data FIRST
call_data["agent_id"] = agent.get("id")
call_data["user_id"] = agent.get("user_id")
redis_service.set_call_data(call_control_id, call_data, ttl=3600)  # ✅ Works

# THEN add non-serializable session to local memory only
call_data["session"] = session  # Stays in Worker 4's memory
```

This ensures:
- Redis gets clean, serializable data with agent_id
- Any worker can retrieve agent_id from Redis
- Any worker can recreate the session when needed
