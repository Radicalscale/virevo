# Time-Based Interruption Window Approach (ARCHIVED)

## Overview
This approach estimates audio playback duration based on word count to determine when the interruption window should close.

## Implementation

### Core Logic
```python
# After agent finishes generating response text:
word_count = len(response_text.split())
estimated_audio_duration = word_count / 3.0  # 3 words/sec = 180 WPM

# Keep agent_generating_response=True for estimated duration
async def clear_after_audio():
    await asyncio.sleep(estimated_audio_duration)
    agent_generating_response = False
    is_agent_speaking = False
    current_playback_ids.clear()
    logger.info(f"🔊 Audio playback complete - interruption window closed")

asyncio.create_task(clear_after_audio())
```

### Calculation
- **Speaking Rate**: 180 words per minute (3 words/second)
- **Formula**: `duration_seconds = word_count / 3.0`
- **Example**: 30 words = 10 seconds

### Why This Was Abandoned
1. **Inaccurate**: Speaking rate varies by TTS voice, speed settings, punctuation
2. **Emotional TTS**: Future emotional variance (faster/slower) would break timing
3. **Inflexible**: Can't adapt to actual playback without manual tuning
4. **User Experience Issues**:
   - Overestimate → ignores legitimate user responses
   - Underestimate → processes single-word acknowledgments as turns

## Replacement Approach
Use Telnyx `call.playback.ended` webhooks to detect actual audio completion in real-time.

## If You Need This Again
Replace the webhook-based approach in `server.py` with the code above in the section where `agent_generating_response` is managed.
