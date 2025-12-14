"""
Comfort noise generator for natural-sounding agent audio
Mixes continuous background noise into TTS audio for seamless comfort noise throughout call
"""
import io
import os
import numpy as np
from pydub import AudioSegment
from pydub.generators import WhiteNoise, Sine
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# COMFORT NOISE VOLUME CONFIGURATION
# =============================================================================
# Adjust these values to change comfort noise volume (persists across restarts)
# Lower dB = quieter. Each -6dB halves the perceived volume.
# 
# Original values: WHITE_NOISE_DB=-63, HUM_DB=-73
# Halved (50%):    WHITE_NOISE_DB=-69, HUM_DB=-79
# Quartered (25%): WHITE_NOISE_DB=-75, HUM_DB=-85
# 1/8th (12.5%):   WHITE_NOISE_DB=-81, HUM_DB=-91
# Current (15% lower than 1/8th): WHITE_NOISE_DB=-83, HUM_DB=-93
#
# You can also set via environment variables for easy adjustment:
#   COMFORT_NOISE_WHITE_DB=-83
#   COMFORT_NOISE_HUM_DB=-93
# =============================================================================
COMFORT_NOISE_WHITE_DB = int(os.environ.get("COMFORT_NOISE_WHITE_DB", -83))
COMFORT_NOISE_HUM_DB = int(os.environ.get("COMFORT_NOISE_HUM_DB", -93))

# Global comfort noise sample loaded once at startup
_comfort_noise_sample = None


def generate_comfort_noise_sample(duration_seconds: int = 30):
    """
    Generate a comfort noise sample that can be mixed into TTS audio
    
    Args:
        duration_seconds: Duration of the noise sample (default 30s)
        
    Returns:
        AudioSegment: The comfort noise sample
    """
    try:
        duration_ms = duration_seconds * 1000
        
        # Base white noise using configurable volume
        noise = WhiteNoise().to_audio_segment(
            duration=duration_ms,
            volume=COMFORT_NOISE_WHITE_DB
        ).set_frame_rate(8000).set_channels(1)
        
        # Add 60Hz phone line hum using configurable volume
        hum = Sine(60).to_audio_segment(
            duration=duration_ms,
            volume=COMFORT_NOISE_HUM_DB
        ).set_frame_rate(8000)
        
        # Mix them
        comfort_noise = noise.overlay(hum)
        
        logger.info(f"✅ Generated comfort noise sample: {duration_seconds}s (white={COMFORT_NOISE_WHITE_DB}dB, hum={COMFORT_NOISE_HUM_DB}dB)")
        return comfort_noise
        
    except Exception as e:
        logger.error(f"❌ Error generating comfort noise sample: {e}")
        return None


def load_comfort_noise_sample():
    """Load comfort noise sample into memory for mixing"""
    global _comfort_noise_sample
    if _comfort_noise_sample is None:
        logger.info("🎵 Loading comfort noise sample into memory...")
        _comfort_noise_sample = generate_comfort_noise_sample(duration_seconds=30)
    return _comfort_noise_sample


def mix_comfort_noise_into_audio(audio_bytes: bytes, audio_format: str = "mp3") -> bytes:
    """
    Mix comfort noise into TTS audio for seamless background noise
    
    Args:
        audio_bytes: The TTS audio bytes
        audio_format: Audio format (default "mp3")
        
    Returns:
        bytes: Mixed audio with comfort noise
    """
    try:
        # Load comfort noise if not already loaded
        comfort_noise = load_comfort_noise_sample()
        if comfort_noise is None:
            logger.warning("⚠️ No comfort noise available, returning original audio")
            return audio_bytes
        
        # Load TTS audio
        tts_audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=audio_format)
        
        # Ensure same format (8kHz, mono)
        tts_audio = tts_audio.set_frame_rate(8000).set_channels(1)
        
        # Get a segment of comfort noise matching TTS duration
        tts_duration_ms = len(tts_audio)
        
        # Loop comfort noise to match TTS duration if needed
        if tts_duration_ms > len(comfort_noise):
            # Repeat comfort noise to cover entire TTS
            repeats = (tts_duration_ms // len(comfort_noise)) + 1
            comfort_segment = comfort_noise * repeats
        else:
            comfort_segment = comfort_noise
        
        # Trim to exact TTS duration
        comfort_segment = comfort_segment[:tts_duration_ms]
        
        # Mix comfort noise under TTS audio
        mixed_audio = tts_audio.overlay(comfort_segment)
        
        # Export to bytes
        output_buffer = io.BytesIO()
        mixed_audio.export(output_buffer, format=audio_format, bitrate="32k")
        output_buffer.seek(0)
        
        return output_buffer.read()
        
    except Exception as e:
        logger.error(f"❌ Error mixing comfort noise: {e}")
        return audio_bytes  # Return original on error


def generate_continuous_comfort_noise(duration_seconds: int = 300, output_path: str = "/tmp/comfort_noise_continuous.mp3"):
    """
    Generate a long continuous comfort noise file (for backward compatibility)
    NOTE: This is no longer used for actual playback - comfort noise is now mixed into TTS
    
    Args:
        duration_seconds: How long the noise should be (default 5 minutes for long calls)
        output_path: Where to save the file
    """
    try:
        # Generate very subtle pink-ish noise (closer to real phone line noise)
        # Mix white noise with very low frequency components for naturalness
        duration_ms = duration_seconds * 1000
        
        # Use configurable volume settings
        noise = WhiteNoise().to_audio_segment(
            duration=duration_ms,
            volume=COMFORT_NOISE_WHITE_DB
        ).set_frame_rate(8000).set_channels(1)
        
        # Add very low frequency hum (like phone line hum)
        # 60Hz hum is common in phone systems
        hum = Sine(60).to_audio_segment(
            duration=duration_ms,
            volume=COMFORT_NOISE_HUM_DB
        ).set_frame_rate(8000)
        
        # Mix them
        comfort_noise = noise.overlay(hum)
        
        # Export as low-bitrate MP3 (saves bandwidth)
        comfort_noise.export(output_path, format="mp3", bitrate="32k")
        logger.info(f"Generated continuous comfort noise: {output_path} ({duration_seconds}s, white={COMFORT_NOISE_WHITE_DB}dB, hum={COMFORT_NOISE_HUM_DB}dB)")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating comfort noise: {e}")
        return None


# =============================================================================
# MULAW COMFORT NOISE FOR WEBSOCKET MIXING
# =============================================================================
# These functions generate comfort noise in raw mulaw format for mixing
# directly into WebSocket audio chunks (since REST API playback doesn't
# overlay properly with WebSocket streaming)

# Global mulaw comfort noise sample for WebSocket mixing
_comfort_noise_mulaw = None


def generate_comfort_noise_mulaw() -> bytes:
    """
    Generate comfort noise as raw mulaw bytes for WebSocket mixing.
    Returns 30 seconds of mulaw comfort noise at 8kHz.
    """
    try:
        import subprocess
        import tempfile
        import os as os_module
        
        # Generate comfort noise as AudioSegment
        sample = generate_comfort_noise_sample(duration_seconds=30)
        if not sample:
            return None
        
        # Export to temporary WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
            wav_path = wav_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.mulaw', delete=False) as mulaw_file:
            mulaw_path = mulaw_file.name
        
        try:
            # Export AudioSegment to WAV
            sample.export(wav_path, format='wav')
            
            # Convert WAV to mulaw using ffmpeg
            result = subprocess.run([
                'ffmpeg', '-y',
                '-i', wav_path,
                '-ar', '8000',        # 8kHz sample rate
                '-ac', '1',           # Mono
                '-f', 'mulaw',        # mulaw codec
                mulaw_path
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0:
                with open(mulaw_path, 'rb') as f:
                    mulaw_data = f.read()
                logger.info(f"✅ Generated mulaw comfort noise: {len(mulaw_data)} bytes")
                return mulaw_data
            else:
                logger.error(f"❌ ffmpeg error: {result.stderr.decode()}")
                return None
                
        finally:
            # Clean up temp files
            try:
                os_module.remove(wav_path)
                os_module.remove(mulaw_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ Error generating mulaw comfort noise: {e}")
        return None


def get_comfort_noise_mulaw() -> bytes:
    """Get cached mulaw comfort noise sample (loads on first call)"""
    global _comfort_noise_mulaw
    if _comfort_noise_mulaw is None:
        logger.info("🎵 Loading mulaw comfort noise for WebSocket mixing...")
        _comfort_noise_mulaw = generate_comfort_noise_mulaw()
    return _comfort_noise_mulaw


def get_comfort_noise_chunk(chunk_size: int, position: int) -> bytes:
    """
    Get a chunk of comfort noise mulaw bytes for sending during silence.
    
    Args:
        chunk_size: Number of bytes to return (typically 160 for 20ms)
        position: Current position in the noise loop
        
    Returns:
        Raw mulaw bytes of comfort noise
    """
    noise = get_comfort_noise_mulaw()
    if not noise or len(noise) == 0:
        # Return silence (0xFF in mulaw is silence)
        return bytes([0xFF] * chunk_size)
    
    noise_len = len(noise)
    chunk = bytearray(chunk_size)
    
    for i in range(chunk_size):
        noise_pos = (position + i) % noise_len
        chunk[i] = noise[noise_pos]
    
    return bytes(chunk)
