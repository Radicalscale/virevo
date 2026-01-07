"""
Voice Library Router - API endpoints for managing voice samples for Maya TTS voice cloning.

Endpoints:
- GET /voice-library - List all voices for user
- POST /voice-library - Upload new voice sample
- GET /voice-library/{id} - Get voice details
- DELETE /voice-library/{id} - Delete voice sample
- GET /voice-library/{id}/audio - Stream audio preview
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import io
import logging

logger = logging.getLogger(__name__)

voice_library_router = APIRouter(prefix="/voice-library", tags=["Voice Library"])


# ============ MODELS ============

class VoiceSample(BaseModel):
    """Voice sample for Maya TTS voice cloning"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str                      # User-friendly name like "Jake Professional"
    description: str = ""          # Optional description of the voice
    file_size: int                 # Size in bytes
    duration_seconds: float = 0.0  # Duration for display
    format: str = "wav"            # wav, mp3, etc.
    sample_rate: int = 24000       # Sample rate
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VoiceSampleResponse(BaseModel):
    """Response model for voice sample (without binary data)"""
    id: str
    name: str
    description: str
    file_size: int
    duration_seconds: float
    format: str
    created_at: datetime


class VoiceSampleCreate(BaseModel):
    """Request model for creating a voice sample"""
    name: str
    description: str = ""


# ============ DEPENDENCIES ============

async def get_current_user():
    """Dependency to get current user - import from server.py"""
    from server import get_current_user as server_get_current_user
    return server_get_current_user


async def get_db():
    """Get database connection"""
    from server import db
    return db


# ============ HELPER FUNCTIONS ============

def get_audio_duration(audio_bytes: bytes, format: str) -> float:
    """Get duration of audio file in seconds"""
    try:
        import wave
        import io
        
        if format.lower() == "wav":
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                duration = frames / float(rate)
                return round(duration, 2)
        else:
            # For MP3 and other formats, estimate from file size
            # Approximate: 128kbps = 16KB/sec
            return round(len(audio_bytes) / 16000, 2)
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {e}")
        return 0.0


def validate_audio_file(filename: str, file_size: int) -> tuple[bool, str]:
    """Validate audio file format and size"""
    # Check extension
    ext = filename.lower().split('.')[-1]
    allowed_formats = ['wav', 'mp3', 'flac', 'ogg', 'm4a']
    
    if ext not in allowed_formats:
        return False, f"Unsupported format: {ext}. Allowed: {', '.join(allowed_formats)}"
    
    # Check size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        return False, f"File too large: {file_size / 1024 / 1024:.1f}MB. Max: 10MB"
    
    # Check minimum size (at least 10KB for any audio)
    if file_size < 10 * 1024:
        return False, f"File too small: {file_size / 1024:.1f}KB. Minimum: 10KB"
    
    return True, ext


# ============ ENDPOINTS ============

@voice_library_router.get("", response_model=List[VoiceSampleResponse])
async def list_voice_samples(current_user: dict = Depends(get_current_user)):
    """List all voice samples for the current user"""
    try:
        from server import db
        
        samples = await db.voice_library.find(
            {"user_id": current_user['id']}
        ).sort("created_at", -1).to_list(100)
        
        return [
            VoiceSampleResponse(
                id=s['id'],
                name=s['name'],
                description=s.get('description', ''),
                file_size=s['file_size'],
                duration_seconds=s.get('duration_seconds', 0),
                format=s.get('format', 'wav'),
                created_at=s['created_at']
            )
            for s in samples
        ]
    except Exception as e:
        logger.error(f"Error listing voice samples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@voice_library_router.post("", response_model=VoiceSampleResponse)
async def upload_voice_sample(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    current_user: dict = Depends(get_current_user)
):
    """Upload a new voice sample for voice cloning"""
    try:
        from server import db
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file
        is_valid, result = validate_audio_file(file.filename, file_size)
        if not is_valid:
            raise HTTPException(status_code=400, detail=result)
        
        file_format = result
        
        # Get audio duration
        duration = get_audio_duration(file_content, file_format)
        
        # Check duration (5-30 seconds recommended)
        if duration > 0:
            if duration < 3:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Audio too short: {duration}s. Minimum 3 seconds required."
                )
            if duration > 60:
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio too long: {duration}s. Maximum 60 seconds allowed."
                )
        
        # Check user's voice library limit (max 20 voices)
        existing_count = await db.voice_library.count_documents({"user_id": current_user['id']})
        if existing_count >= 20:
            raise HTTPException(
                status_code=400,
                detail="Voice library limit reached (20 voices). Delete some before uploading more."
            )
        
        # Create voice sample record
        sample_id = str(uuid.uuid4())
        sample = {
            "id": sample_id,
            "user_id": current_user['id'],
            "name": name,
            "description": description,
            "file_size": file_size,
            "duration_seconds": duration,
            "format": file_format,
            "audio_data": file_content,  # Store binary data directly (for small files)
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await db.voice_library.insert_one(sample)
        
        logger.info(f"🎤 Voice sample uploaded: {name} ({duration}s, {file_size} bytes) for user {current_user['id']}")
        
        return VoiceSampleResponse(
            id=sample_id,
            name=name,
            description=description,
            file_size=file_size,
            duration_seconds=duration,
            format=file_format,
            created_at=sample['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading voice sample: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@voice_library_router.get("/{sample_id}", response_model=VoiceSampleResponse)
async def get_voice_sample(sample_id: str, current_user: dict = Depends(get_current_user)):
    """Get details of a specific voice sample"""
    try:
        from server import db
        
        sample = await db.voice_library.find_one({
            "id": sample_id,
            "user_id": current_user['id']
        })
        
        if not sample:
            raise HTTPException(status_code=404, detail="Voice sample not found")
        
        return VoiceSampleResponse(
            id=sample['id'],
            name=sample['name'],
            description=sample.get('description', ''),
            file_size=sample['file_size'],
            duration_seconds=sample.get('duration_seconds', 0),
            format=sample.get('format', 'wav'),
            created_at=sample['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice sample: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@voice_library_router.delete("/{sample_id}")
async def delete_voice_sample(sample_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a voice sample"""
    try:
        from server import db
        
        result = await db.voice_library.delete_one({
            "id": sample_id,
            "user_id": current_user['id']
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Voice sample not found")
        
        logger.info(f"🗑️ Voice sample deleted: {sample_id}")
        
        return {"success": True, "message": "Voice sample deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting voice sample: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@voice_library_router.get("/{sample_id}/audio")
async def get_voice_audio(sample_id: str, current_user: dict = Depends(get_current_user)):
    """Stream the audio file for preview"""
    try:
        from server import db
        
        sample = await db.voice_library.find_one({
            "id": sample_id,
            "user_id": current_user['id']
        })
        
        if not sample:
            raise HTTPException(status_code=404, detail="Voice sample not found")
        
        audio_data = sample.get('audio_data')
        if not audio_data:
            raise HTTPException(status_code=404, detail="Audio data not found")
        
        file_format = sample.get('format', 'wav')
        media_type = f"audio/{file_format}"
        if file_format == 'mp3':
            media_type = "audio/mpeg"
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{sample["name"]}.{file_format}"',
                "Content-Length": str(len(audio_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming voice audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ HELPER FUNCTION FOR TTS SERVICE ============

async def load_voice_sample(sample_id: str) -> Optional[bytes]:
    """
    Load voice sample audio data by ID.
    Called by telnyx_service.py when speaker_wav_id is set.
    
    Returns:
        Audio bytes or None if not found
    """
    try:
        from server import db
        
        sample = await db.voice_library.find_one({"id": sample_id})
        
        if sample and 'audio_data' in sample:
            logger.info(f"🎤 Loaded voice sample: {sample.get('name')} ({len(sample['audio_data'])} bytes)")
            return sample['audio_data']
        
        logger.warning(f"⚠️ Voice sample not found: {sample_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading voice sample {sample_id}: {e}")
        return None
