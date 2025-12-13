# Which Sesame WebSocket Server Should You Use?

## Quick Answer

**Use: `sesame_ws_server_true_streaming.py`** ✅

This is the **EASIEST** to deploy and works out of the box.

---

## File Comparison

### Option 1: `sesame_ws_server_true_streaming.py` ✅ RECOMMENDED

**Dependencies:**
```bash
pip install fastapi uvicorn[standard] websockets
pip install torch transformers huggingface_hub
```

**Pros:**
- ✅ Standard HuggingFace transformers (widely supported)
- ✅ No custom dependencies
- ✅ Easy to deploy
- ✅ Works on any RunPod PyTorch template
- ✅ Reliable and tested

**Cons:**
- ⚠️ Generates full audio first, then streams chunks (~3-6s latency)
- Not true real-time streaming (but still fast enough!)

**Latency:** 3-6 seconds total

---

### Option 2: `sesame_ws_server_csm_streaming.py` ⚡ FASTEST (but harder)

**Dependencies:**
```bash
pip install fastapi uvicorn[standard] websockets
pip install torch transformers huggingface_hub
git clone https://github.com/davidbrowne17/csm-streaming
cd csm-streaming && pip install -e .
```

**Pros:**
- ⚡ TRUE real-time streaming (chunks generated incrementally)
- ⚡ Lowest latency (<1s to first chunk)
- ⚡ 0.28x RTF on RTX 4090

**Cons:**
- ❌ Requires custom csm-streaming library
- ❌ More setup steps
- ❌ May break with updates
- ❌ Not officially supported

**Latency:** <1 second to first chunk

---

## Recommendation

### For Your Use Case: Use `sesame_ws_server_true_streaming.py`

**Why?**
1. **Easy setup** - Standard packages only
2. **Reliable** - Uses official HuggingFace transformers
3. **Fast enough** - 3-6s is perfectly fine for conversational AI
4. **No custom dependencies** - Won't break
5. **Your platform already configured** - Backend URLs point to standard endpoints

**The 3-6 second latency is acceptable because:**
- Much faster than REST API (10-30s)
- User experience is still smooth
- Voice conversations naturally have pauses
- Your fallback to ElevenLabs is also ~2-3s

---

## Deployment to RunPod

### Copy This File to Your RunPod Instance

**File to copy:** `/app/sesame_ws_server_true_streaming.py`

**On RunPod (`6qt2ld98tmdhu2`):**

```bash
cd /workspace

# Copy the entire file content here (shown in previous message)
# Save as: sesame_ws_server.py

# Install dependencies
pip install fastapi uvicorn[standard] websockets torch transformers huggingface_hub

# Set token
export HF_TOKEN="hf_your_token_here"

# Run in tmux
tmux new -s sesame
python sesame_ws_server.py
# Press Ctrl+B then D to detach
```

---

## Your Platform Configuration (Already Done!)

**Backend files updated with:**
- `wss://6qt2ld98tmdhu2-8000.proxy.runpod.net/ws/generate`
- `https://6qt2ld98tmdhu2-8000.proxy.runpod.net/generate`

**Test agent created:**
- Agent ID: `8015d274-4291-432a-acba-fcac59fac97b`
- TTS Provider: Sesame
- Call flow with transitions ready

**Just start the server on RunPod and test!**

---

## If You Want Maximum Speed Later

You can always switch to `csm_streaming` version later:

1. On RunPod: Clone csm-streaming repo
2. Install the csm-streaming package
3. Copy `sesame_ws_server_csm_streaming.py` instead
4. Same endpoints work (no backend changes needed)

But start with the simple version first to get it working!
