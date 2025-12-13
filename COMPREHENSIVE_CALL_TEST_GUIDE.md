# Comprehensive AI Call Testing Guide

## 🎯 Purpose
This guide helps you verify that your AI calling agent is properly loading and using:
- ✅ Correct STT provider (Soniox, Deepgram, AssemblyAI, etc.)
- ✅ Correct TTS provider (ElevenLabs, Cartesia, etc.)
- ✅ Correct LLM provider and model
- ✅ Agent tools and knowledge base
- ✅ Interruption handling
- ✅ Low latency performance

---

## 📋 Pre-Test Checklist

### Environment Variables (Railway):
- [ ] `BACKEND_URL` = Your Railway domain
- [ ] `ENCRYPTION_KEY` = Valid Fernet key (44 chars)
- [ ] `MONGO_URL` = MongoDB connection string
- [ ] `REDIS_URL` = Redis internal URL
- [ ] `JWT_SECRET_KEY` = Random 32-char string
- [ ] `CORS_ORIGINS` = Your frontend URL
- [ ] `TELNYX_API_KEY` = Your Telnyx key
- [ ] Provider keys (Soniox, ElevenLabs, etc.)

### Telnyx Configuration:
- [ ] Webhook URL set to: `https://your-backend/api/webhook/telnyx`
- [ ] Phone number purchased and connected
- [ ] Connection active

### Agent Configuration (Frontend):
- [ ] Agent created with name
- [ ] STT provider selected (e.g., Soniox)
- [ ] TTS provider selected (e.g., ElevenLabs)
- [ ] LLM configured
- [ ] Phone number assigned
- [ ] Agent prompt configured
- [ ] API keys saved in Settings

---

## 🧪 Test 1: Basic Call Connection

### Objective:
Verify call connects and webhook is received.

### Steps:
1. Make outbound call from frontend
2. Answer the phone when it rings
3. Monitor Railway logs

### Expected Logs:
```
✅ 📞 Outbound call initiated: v3:xxxxx
✅ 📦 Call data stored in Redis
✅ 🎯 Webhook received: call.answered for v3:xxxxx
```

### Success Criteria:
- [ ] Call connects and rings
- [ ] Phone answers
- [ ] Backend receives `call.answered` webhook
- [ ] No errors in logs

### If Failed:
- Check BACKEND_URL is set correctly
- Verify Telnyx webhook URL in portal
- Check TELNYX_API_KEY is valid
- Look for errors in logs

---

## 🧪 Test 2: Agent Configuration Loading

### Objective:
Verify agent settings are loaded from database.

### Steps:
1. Before calling, note your agent's configuration in UI
2. Make a call
3. Check Railway logs for agent initialization

### Expected Logs:
```
✅ 🔧 Loading agent configuration: [agent_id]
✅ 📋 Agent: [agent_name]
✅ 🎤 STT Provider: Soniox
✅ 🔊 TTS Provider: ElevenLabs
✅ 🧠 LLM: openai/gpt-4
✅ 📚 Knowledge Base: enabled
✅ 🛠️ Tools: [tool1, tool2]
✅ ⚡ Interruption: enabled
```

### Success Criteria:
- [ ] Agent settings match UI configuration
- [ ] Correct STT provider loaded
- [ ] Correct TTS provider loaded
- [ ] Correct LLM loaded
- [ ] Tools and KB settings correct

### If Failed:
- Check agent ID is correct
- Verify agent exists in database
- Check MONGO_URL connection
- Look for MongoDB connection errors

---

## 🧪 Test 3: API Key Decryption

### Objective:
Verify API keys are properly encrypted and decrypted.

### Steps:
1. Make a call
2. Check logs for decryption

### Expected Logs:
```
✅ 🔑 Decrypting API keys for agent
✅ 🔑 Soniox API key loaded
✅ 🔑 ElevenLabs API key loaded
✅ 🔑 OpenAI API key loaded
```

### Should NOT See:
```
❌ Failed to decrypt key, assuming unencrypted
❌ Fernet key must be 32 url-safe base64-encoded bytes
```

### Success Criteria:
- [ ] No decryption errors
- [ ] All provider keys loaded
- [ ] Keys work with services

### If Failed:
- Regenerate ENCRYPTION_KEY (use `/app/generate_encryption_key.py`)
- Re-enter all API keys in frontend
- Restart backend

---

## 🧪 Test 4: STT (Soniox) Initialization

### Objective:
Verify Soniox STT service initializes and receives audio.

### Steps:
1. Make a call
2. Say "Hello, can you hear me?"
3. Check logs

### Expected Logs:
```
✅ 🎤 Initializing Soniox STT service
✅ 🔑 Soniox API key: KEY_xxxx (first 8 chars)
✅ 🌐 Connecting to Soniox WebSocket
✅ ✅ Soniox STT ready
✅ 🎙️ Audio streaming started
✅ 📝 Audio chunk sent to Soniox
✅ 📝 Transcription: "Hello, can you hear me?"
```

### Success Criteria:
- [ ] Soniox initializes without errors
- [ ] WebSocket connection established
- [ ] Audio is transcribed
- [ ] Transcription is accurate
- [ ] Latency < 1 second

### If Failed:
- Check SONIOX_API_KEY is valid
- Verify Soniox account has credits
- Check WebSocket connection logs
- Test Soniox API key directly

---

## 🧪 Test 5: LLM Response Generation

### Objective:
Verify LLM processes transcription and generates response.

### Steps:
1. During call, say something
2. Check logs for LLM activity

### Expected Logs:
```
✅ 📝 Transcription: "What's the weather like?"
✅ 🧠 Sending to LLM: openai/gpt-4
✅ 🤖 LLM Response: "I don't have access to weather..."
```

### Success Criteria:
- [ ] LLM receives transcription
- [ ] LLM generates response
- [ ] Response is contextually relevant
- [ ] Response follows agent prompt

### If Failed:
- Check LLM API key is valid
- Verify LLM model is available
- Check prompt configuration
- Look for LLM API errors

---

## 🧪 Test 6: TTS (ElevenLabs) Synthesis

### Objective:
Verify TTS synthesizes and streams audio.

### Steps:
1. Wait for agent to respond
2. Listen for audio
3. Check logs

### Expected Logs:
```
✅ 🔊 Sending to TTS: ElevenLabs
✅ 🎵 TTS generated: 3.2 seconds of audio
✅ 📡 Streaming audio to caller
✅ ✅ Audio sent successfully
```

### Success Criteria:
- [ ] TTS generates audio
- [ ] Audio is streamed to caller
- [ ] Voice quality is good
- [ ] Latency is acceptable
- [ ] No audio glitches

### If Failed:
- Check ElevenLabs API key
- Verify voice ID exists
- Check audio format compatibility
- Look for TTS errors

---

## 🧪 Test 7: Knowledge Base Integration

### Objective:
Verify KB is loaded and used in responses.

### Steps:
1. Add knowledge to agent's KB
2. Make a call
3. Ask a question about the KB content
4. Check logs

### Expected Logs:
```
✅ 📚 Loading knowledge base for agent
✅ 📊 KB loaded: 15 documents
✅ 🔍 Searching KB for: "product pricing"
✅ 📄 KB results found: 3 relevant chunks
✅ 🤖 Using KB context in LLM prompt
```

### Success Criteria:
- [ ] KB loads successfully
- [ ] KB search works
- [ ] Relevant content retrieved
- [ ] Agent uses KB in response
- [ ] Response includes KB information

### If Failed:
- Check KB documents are uploaded
- Verify RAG service is enabled
- Check vector embeddings exist
- Look for ChromaDB errors

---

## 🧪 Test 8: Tool Execution

### Objective:
Verify agent tools execute correctly.

### Steps:
1. Configure agent with tools (e.g., "book_appointment")
2. Make a call
3. Trigger tool usage
4. Check logs

### Expected Logs:
```
✅ 🛠️ Agent tools loaded: [book_appointment, send_email]
✅ 🤖 LLM decides to use tool: book_appointment
✅ 🔧 Executing tool: book_appointment
✅ 📊 Tool parameters: {"date": "2025-11-15", "time": "10:00"}
✅ ✅ Tool executed successfully
✅ 🤖 LLM response includes tool result
```

### Success Criteria:
- [ ] Tools are loaded
- [ ] LLM decides to use tool appropriately
- [ ] Tool executes successfully
- [ ] Tool result is used in response
- [ ] User is informed of action

### If Failed:
- Check tool configuration in agent
- Verify tool function definitions
- Check tool execution permissions
- Look for tool execution errors

---

## 🧪 Test 9: Interruption Handling

### Objective:
Verify agent stops when user interrupts.

### Steps:
1. Make a call
2. Let agent start speaking (long response)
3. Interrupt mid-sentence by speaking
4. Check logs

### Expected Logs:
```
✅ 🔊 TTS streaming to caller
✅ 🎙️ User speech detected during TTS
✅ ⚡ Interruption detected
✅ 🛑 Stopping TTS playback
✅ 🎤 Listening to user...
✅ 📝 Transcription: "Wait, let me ask..."
```

### Success Criteria:
- [ ] Agent stops speaking immediately
- [ ] User speech is captured
- [ ] No audio overlap
- [ ] Conversation continues naturally
- [ ] No dropped audio

### If Failed:
- Check interruption settings in agent config
- Verify VAD (Voice Activity Detection) is working
- Check audio streaming configuration
- Look for WebSocket errors

---

## 🧪 Test 10: Multi-Agent Configuration

### Objective:
Verify different agents use their own configurations.

### Steps:
1. Create Agent A: Deepgram STT + Cartesia TTS
2. Create Agent B: Soniox STT + ElevenLabs TTS
3. Call Agent A, note behavior
4. Call Agent B, note behavior
5. Compare logs

### Expected Behavior:
- Agent A uses Deepgram and Cartesia
- Agent B uses Soniox and ElevenLabs
- No configuration bleeding
- Each agent maintains own settings

### Success Criteria:
- [ ] Each agent uses correct STT
- [ ] Each agent uses correct TTS
- [ ] No configuration conflicts
- [ ] Consistent behavior per agent

### If Failed:
- Check agent IDs are unique
- Verify config is stored per agent
- Check Redis state isolation
- Look for configuration caching issues

---

## 🧪 Test 11: Low Latency Performance

### Objective:
Measure end-to-end latency.

### Steps:
1. Make a call
2. Say "Hello"
3. Measure time until agent responds
4. Check logs for timing

### Expected Logs:
```
✅ 📝 Transcription received: 450ms
✅ 🧠 LLM response: 800ms
✅ 🔊 TTS synthesis: 300ms
✅ ⏱️ Total latency: 1.55s
```

### Success Criteria:
- [ ] STT latency < 500ms
- [ ] LLM latency < 1s
- [ ] TTS latency < 500ms
- [ ] Total latency < 2s
- [ ] Conversation feels natural

### If Failed:
- Check network connectivity
- Verify provider APIs are responsive
- Optimize agent prompt (shorter = faster)
- Consider faster models/providers
- Check for rate limiting

---

## 🧪 Test 12: Error Recovery

### Objective:
Verify graceful error handling.

### Steps:
1. Temporarily invalidate an API key
2. Make a call
3. Check error handling
4. Fix key and retry

### Expected Logs:
```
❌ 🔑 Error: Invalid Soniox API key
✅ ⚠️ Falling back to error message
✅ 🔊 Playing error TTS to user
✅ 📞 Call continues with error state
```

### Success Criteria:
- [ ] Errors are caught and logged
- [ ] User is informed of issue
- [ ] Call doesn't crash
- [ ] Graceful degradation
- [ ] Recovery after fix

### If Failed:
- Add more error handling
- Improve error messages
- Add fallback mechanisms
- Better logging

---

## 📊 Complete Success Checklist

After all tests, you should have:

### ✅ Call Flow:
- [ ] Calls connect reliably
- [ ] Webhooks received
- [ ] WebSockets established
- [ ] Audio streaming works

### ✅ Agent Configuration:
- [ ] Correct STT provider loaded
- [ ] Correct TTS provider loaded
- [ ] Correct LLM loaded
- [ ] Tools and KB working
- [ ] Interruption handling works

### ✅ Performance:
- [ ] Low latency (< 2s)
- [ ] High quality audio
- [ ] Accurate transcription
- [ ] Natural conversation flow

### ✅ Reliability:
- [ ] No crashes or errors
- [ ] Consistent behavior
- [ ] Proper error handling
- [ ] Multi-agent support

---

## 🆘 Common Issues & Solutions

### Issue: "Agent doesn't respond"
**Solutions:**
1. Check ENCRYPTION_KEY is valid Fernet format
2. Verify Telnyx webhook is configured
3. Check all API keys are valid
4. Monitor logs for errors

### Issue: "Wrong STT provider used"
**Solutions:**
1. Verify agent config in UI
2. Check database has correct settings
3. Clear Redis cache
4. Restart backend

### Issue: "High latency"
**Solutions:**
1. Use faster LLM models
2. Shorten agent prompt
3. Enable streaming responses
4. Check network connectivity

### Issue: "Transcription errors"
**Solutions:**
1. Test STT API key directly
2. Check audio format compatibility
3. Verify WebSocket connection
4. Try different STT provider

### Issue: "Tools not executing"
**Solutions:**
1. Check tool definitions in agent
2. Verify LLM has access to tools
3. Check tool execution logs
4. Test tools independently

---

## 📈 Performance Benchmarks

### Target Latencies:
- STT (Speech-to-Text): < 500ms
- LLM (Response Generation): < 1000ms
- TTS (Text-to-Speech): < 500ms
- **Total End-to-End: < 2000ms**

### Quality Metrics:
- Transcription Accuracy: > 95%
- Response Relevance: > 90%
- Audio Quality: Clear, no distortion
- Interruption Response: < 200ms

### Reliability Targets:
- Call Connection Rate: > 99%
- Webhook Reception Rate: 100%
- Agent Response Rate: > 95%
- Error Recovery Rate: 100%

---

## 🎯 Final Verification

Before considering deployment complete:

1. **Run all 12 tests** ✅
2. **Document any issues** 📝
3. **Verify fixes work** 🔧
4. **Test with real users** 👥
5. **Monitor production logs** 📊

**Your AI calling system is production-ready when all tests pass!** 🚀
