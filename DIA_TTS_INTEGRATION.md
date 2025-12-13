# Dia TTS Integration Complete

## 📋 Summary

Dia TTS (1.6B parameter ultra-realistic text-to-speech) has been fully integrated into your voice agent platform, replacing MeloTTS as the default TTS provider.

## 🎯 What You Have

### Backend Files
1. **`/app/backend/dia_tts_service.py`** - Client service to communicate with RunPod
2. **`/app/backend/models.py`** - Updated with DiaSettings model
3. **`/app/backend/server.py`** - Integrated Dia TTS into generate_tts_audio

### Frontend Files
1. **`/app/frontend/src/components/AgentForm.jsx`** - UI controls for Dia TTS settings

### RunPod Deployment Files
1. **`/app/RUNPOD_DIA_SERVER.py`** - FastAPI server for RunPod ⭐ **YOU NEED THIS**
2. **`/app/RUNPOD_DIA_REQUIREMENTS.txt`** - Python dependencies
3. **`/app/DEPLOY_DIA_TO_RUNPOD.md`** - Complete deployment guide

## 🚀 Next Steps

### 1. Deploy to RunPod

Upload these files to your RunPod instance at `/workspace/dia_tts_api/`:
- `RUNPOD_DIA_SERVER.py` (rename to `server.py`)
- `RUNPOD_DIA_REQUIREMENTS.txt` (rename to `requirements.txt`)

Then follow the deployment guide in `DEPLOY_DIA_TO_RUNPOD.md`

Quick start:
```bash
# On RunPod
cd /workspace/dia_tts_api
pip install -r requirements.txt
python3 server.py
```

### 2. Verify Connection

Test from your app server:
```bash
curl http://203.57.40.158:10230/health
```

### 3. Create Test Agent

Go to your app → Create Agent → Select "Dia TTS" → Test it!

## 🎤 Dia TTS Features

### Voice Options
- **S1** - Default Male voice
- **S2** - Default Female voice  
- **S3, S4** - Additional voices

### Special Features
- **Multi-Speaker**: `[S1] Hello there! [S2] Hi, how are you?`
- **Non-Verbals**: `This is funny! (laughs) Really amazing. (sighs)`
- **Speed Control**: 0.25x to 4.0x (1.0 = normal)
- **Formats**: WAV, MP3, Opus, AAC, FLAC

## 🔧 Configuration

### TCP Connection
- **Your App** → `http://203.57.40.158:10230` (external)
- **RunPod Pod** → `0.0.0.0:8000` (internal)
- **RunPod Port Mapping**: `10230:8000`

### Default Settings
- Voice: S1
- Speed: 1.0x
- Format: WAV (converts to MP3 for Telnyx)

### Low Latency Optimizations
✅ Direct TCP connection (no proxies)
✅ Raw audio bytes (no base64)
✅ GPU acceleration
✅ Float16 precision
✅ Model stays loaded in memory
✅ Detailed timing logs

## 📊 Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| Backend Service | ✅ Complete | dia_tts_service.py |
| Models | ✅ Complete | DiaSettings added |
| Server Integration | ✅ Complete | generate_tts_audio updated |
| Frontend UI | ✅ Complete | Dropdown + settings panel |
| RunPod Server Code | ✅ Ready | RUNPOD_DIA_SERVER.py |
| Deployment Guide | ✅ Complete | DEPLOY_DIA_TO_RUNPOD.md |
| Testing | ⏳ Pending | Deploy RunPod server first |

## 🎯 Key Differences from MeloTTS

| Feature | MeloTTS | Dia TTS |
|---------|---------|---------|
| Endpoint | `/tts` | `/v1/audio/speech` (OpenAI format) |
| Voices | EN-US, EN-BR, etc. | S1, S2, S3, S4 (speakers) |
| Special | Voice accents | Multi-speaker + non-verbals |
| Quality | Good | Ultra-realistic (1.6B params) |
| Use Case | Single speaker | Dialogue & emotion |

## 🐛 Troubleshooting

### If Dia TTS fails:
1. Check RunPod server is running: `curl http://203.57.40.158:10230/health`
2. Check backend logs: `tail -f /var/log/supervisor/backend.err.log | grep -i dia`
3. System falls back to ElevenLabs automatically

### Common Issues:
- **503 Error**: RunPod server not running or unreachable
- **Latency**: Check GPU usage on RunPod with `nvidia-smi`
- **Voice inconsistency**: Use speaker tags in prompt text

## 📝 Example Usage

### Simple Single Speaker
```python
# The agent will use default S1 voice
"Hello! This is a test of the Dia TTS system."
```

### Multi-Speaker Dialogue
```python
"[S1] Welcome to our store! How can I help you today? [S2] I'm looking for a new laptop. [S1] Great! Let me show you our latest models."
```

### With Emotion/Non-Verbals
```python
"[S1] That's incredible! (laughs) I can't believe it actually worked. (sighs with relief) What a journey this has been."
```

## 🎉 You're All Set!

Your application now has:
- ✅ Dia TTS integrated in backend
- ✅ UI controls in frontend  
- ✅ RunPod server code ready
- ✅ Comprehensive deployment guide
- ✅ Low-latency configuration

**Just deploy the RunPod server and you're good to go!** 🚀
