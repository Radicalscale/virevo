# Retell AI Clone - API Contracts & Implementation Plan

## Overview
This document outlines the API contracts, mocked data replacement strategy, and backend implementation for the Retell AI clone.

## Frontend Mock Data (to be replaced with real APIs)

### 1. Agent Management
**Mock File**: `/app/frontend/src/mock/data.js` - `mockAgents`
**Real API Endpoints**:
- `GET /api/agents` - List all agents
- `POST /api/agents` - Create new agent
- `GET /api/agents/{id}` - Get agent details
- `PUT /api/agents/{id}` - Update agent
- `DELETE /api/agents/{id}` - Delete agent

### 2. Call Logs
**Mock File**: `/app/frontend/src/mock/data.js` - `mockCalls`
**Real API Endpoints**:
- `GET /api/calls` - List all calls
- `GET /api/calls/{id}` - Get call details
- `POST /api/calls` - Log new call

### 3. Phone Numbers
**Mock File**: `/app/frontend/src/mock/data.js` - `mockPhoneNumbers`
**Real API Endpoints**:
- `GET /api/phone-numbers` - List phone numbers
- `POST /api/phone-numbers` - Add phone number
- `PUT /api/phone-numbers/{id}` - Assign agent to number

### 4. Call Flows
**Mock File**: `/app/frontend/src/mock/data.js` - `mockFlowNodes`
**Real API Endpoints**:
- `GET /api/agents/{id}/flow` - Get agent's call flow
- `PUT /api/agents/{id}/flow` - Update agent's call flow

## Backend Architecture

### Database Models

#### Agent Model
```python
{
  "_id": ObjectId,
  "name": str,
  "description": str,
  "voice": str,  # ElevenLabs voice ID
  "language": str,
  "model": str,  # OpenAI model
  "status": str,  # active/inactive
  "system_prompt": str,
  "call_flow": dict,  # Flow configuration
  "settings": {
    "temperature": float,
    "max_tokens": int,
    "tts_speed": float
  },
  "stats": {
    "calls_handled": int,
    "avg_latency": float,
    "success_rate": float
  },
  "created_at": datetime,
  "updated_at": datetime
}
```

#### Call Model
```python
{
  "_id": ObjectId,
  "agent_id": str,
  "phone_number": str,
  "direction": str,  # inbound/outbound
  "duration": int,
  "status": str,  # completed/failed/in_progress
  "sentiment": str,  # positive/negative/neutral
  "latency": float,
  "transcript": list[dict],  # [{speaker: str, text: str, timestamp: datetime}]
  "recording_url": str,
  "daily_room_url": str,
  "metadata": dict,
  "timestamp": datetime
}
```

#### PhoneNumber Model
```python
{
  "_id": ObjectId,
  "number": str,
  "assigned_agent_id": str,
  "status": str,  # active/inactive/unassigned
  "calls_received": int,
  "created_at": datetime
}
```

## Real-Time Calling Implementation

### WebRTC with Daily.co
1. Frontend initiates call via Daily.co React SDK
2. Backend creates Daily room for the call
3. Audio stream flows:
   - User speech → Deepgram STT → Text
   - Text → OpenAI LLM → Response
   - Response → ElevenLabs TTS → Audio
   - Audio → Daily.co → User

### Latency Optimization
- Use streaming APIs for all services
- WebSocket for real-time communication
- Edge caching for frequently used responses
- Target: <2s end-to-end latency

## API Endpoints Summary

### Agents
- `POST /api/agents` - Create agent
- `GET /api/agents` - List agents
- `GET /api/agents/{id}` - Get agent
- `PUT /api/agents/{id}` - Update agent
- `DELETE /api/agents/{id}` - Delete agent
- `PUT /api/agents/{id}/flow` - Update flow

### Calls
- `POST /api/calls/start` - Initiate call
- `POST /api/calls/end` - End call
- `GET /api/calls` - List calls
- `GET /api/calls/{id}` - Get call details
- `WS /ws/calls/{call_id}` - Real-time call updates

### Phone Numbers
- `POST /api/phone-numbers` - Add number
- `GET /api/phone-numbers` - List numbers
- `PUT /api/phone-numbers/{id}` - Update assignment

### Testing
- `POST /api/test/create-room` - Create Daily.co test room
- `POST /api/test/agent/{id}` - Test agent

## Integration Flow

### 1. Agent Creation
Frontend → `POST /api/agents` → Backend saves to MongoDB → Returns agent object

### 2. Call Flow Configuration
Frontend Flow Builder → `PUT /api/agents/{id}/flow` → Backend validates & saves

### 3. Real-Time Call
Frontend → `POST /api/calls/start` → Backend creates Daily room → Returns room URL
→ WebSocket connection established → Audio processing pipeline active
→ Call ends → `POST /api/calls/end` → Saves call log

## Next Steps
1. ✅ Frontend with mock data (COMPLETED)
2. Backend API implementation
3. Real-time calling with Daily.co
4. Integration & Testing
