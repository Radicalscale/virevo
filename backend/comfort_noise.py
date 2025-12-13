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
# 1/8th (12.5%):   WHITE_NOISE_DB=-81, HUM_DB=-91 (current)
#
# You can also set via environment variables for easy adjustment:
#   COMFORT_NOISE_WHITE_DB=-81
#   COMFORT_NOISE_HUM_DB=-91
# =============================================================================
COMFORT_NOISE_WHITE_DB = int(os.environ.get("COMFORT_NOISE_WHITE_DB", -81))
COMFORT_NOISE_HUM_DB = int(os.environ.get("COMFORT_NOISE_HUM_DB", -91))

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

