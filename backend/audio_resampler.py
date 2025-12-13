import numpy as np
from scipy import signal

def mulaw_to_linear_pcm(mulaw_data: bytes) -> bytes:
    """
    Convert μ-law (mulaw/PCMU) encoded audio to linear PCM (16-bit signed)
    
    Args:
        mulaw_data: Raw μ-law encoded audio bytes
    
    Returns:
        Linear PCM audio as bytes (16-bit signed, little-endian)
    """
    # Pure Python implementation of μ-law to linear PCM conversion
    # This replaces the deprecated audioop module
    
    # μ-law constants
    MULAW_BIAS = 33
    
    # Convert bytes to numpy array
    mulaw_samples = np.frombuffer(mulaw_data, dtype=np.uint8)
    
    # μ-law decompression algorithm
    mulaw_samples = mulaw_samples.astype(np.int16)
    mulaw_samples = ~mulaw_samples  # Invert bits
    
    # Extract sign, exponent, and mantissa
    sign = (mulaw_samples & 0x80) >> 7
    exponent = (mulaw_samples & 0x70) >> 4
    mantissa = mulaw_samples & 0x0F
    
    # Decode to linear
    linear = mantissa * 2 + MULAW_BIAS
    linear = linear << (exponent + 3)
    
    # Apply sign
    linear = np.where(sign == 0, linear, -linear)
    
    # Clip to 16-bit range
    linear = np.clip(linear, -32768, 32767)
    
    # Convert to bytes (16-bit signed, little-endian)
    linear_pcm = linear.astype(np.int16).tobytes()
    return linear_pcm


def resample_audio(pcm_data: bytes, original_rate: int, target_rate: int) -> bytes:
    """
    Resample PCM audio from one sample rate to another
    
    Args:
        pcm_data: Linear PCM audio bytes (16-bit signed)
        original_rate: Original sample rate (e.g., 8000)
        target_rate: Target sample rate (e.g., 16000)
    
    Returns:
        Resampled PCM audio as bytes
    """
    # Convert bytes to numpy array of 16-bit signed integers
    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
    
    # Calculate resampling ratio
    num_samples = int(len(audio_array) * target_rate / original_rate)
    
    # Resample using scipy's high-quality resampler
    resampled = signal.resample(audio_array, num_samples)
    
    # Convert back to 16-bit integers and bytes
    resampled_int16 = np.int16(resampled)
    return resampled_int16.tobytes()


def convert_mulaw_8khz_to_pcm_16khz(mulaw_data: bytes) -> bytes:
    """
    Convert 8kHz μ-law audio to 16kHz linear PCM in one step
    
    This is the main function to use for Telnyx → AssemblyAI conversion.
    
    Args:
        mulaw_data: Raw μ-law encoded audio bytes at 8kHz
    
    Returns:
        Linear PCM audio bytes (16-bit signed) at 16kHz
    """
    # Step 1: Decode μ-law to linear PCM (still 8kHz)
    linear_pcm_8khz = mulaw_to_linear_pcm(mulaw_data)
    
    # Step 2: Resample from 8kHz to 16kHz
    linear_pcm_16khz = resample_audio(linear_pcm_8khz, 8000, 16000)
    
    return linear_pcm_16khz
