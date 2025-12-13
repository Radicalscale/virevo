"""
Deepgram Live Streaming Configuration
Adjust these parameters to tune the voice activity detection and response timing
"""

# Deepgram Live Streaming Settings
DEEPGRAM_CONFIG = {
    # Model Selection
    "model": "nova-3",  # Most accurate model
    "language": "en-US",
    
    # Audio Format
    "encoding": "linear16",
    "sample_rate": 16000,
    "channels": 1,
    
    # Endpointing (silence detection) - CRITICAL FOR RESPONSIVENESS
    # Lower = faster response, but may cut off speech
    # Higher = more patient, but slower response
    "endpointing": 400,  # milliseconds of silence before considering speech complete (balanced setting)
    
    # Interim Results
    "interim_results": True,  # Get real-time partial transcripts
    
    # Utterance End Detection
    # Determines how long to wait after last word before finalizing
    "utterance_end_ms": 1000,  # milliseconds (default, more patient)
    
    # Voice Activity Detection Events
    "vad_events": True,  # Get notified when speech starts/stops
    
    # Smart Formatting
    "smart_format": True,  # Automatic punctuation, capitalization, etc.
    
    # Punctuation
    "punctuate": True,
    
    # Profanity Filter
    "profanity_filter": False,
    
    # Filler Words (um, uh, etc.)
    "filler_words": False,  # Set to True to remove filler words
}

def get_deepgram_url():
    """Generate Deepgram WebSocket URL with all parameters"""
    params = []
    for k, v in DEEPGRAM_CONFIG.items():
        if isinstance(v, bool):
            params.append(f"{k}={str(v).lower()}")
        else:
            params.append(f"{k}={v}")
    return f"wss://api.deepgram.com/v1/listen?{'&'.join(params)}"

def get_config_summary():
    """Return human-readable summary of current settings"""
    return {
        "model": DEEPGRAM_CONFIG["model"],
        "response_speed": "fast" if DEEPGRAM_CONFIG["endpointing"] < 300 else "balanced" if DEEPGRAM_CONFIG["endpointing"] < 500 else "patient",
        "endpointing_ms": DEEPGRAM_CONFIG["endpointing"],
        "utterance_end_ms": DEEPGRAM_CONFIG["utterance_end_ms"],
        "interim_results": DEEPGRAM_CONFIG["interim_results"],
    }
