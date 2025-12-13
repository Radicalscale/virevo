#!/usr/bin/env python3
"""
Test script for Sesame TTS RunPod integration
"""
import asyncio
import logging
from sesame_tts_service import get_sesame_tts_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sesame_tts():
    """Test Sesame TTS with custom RunPod endpoint"""
    
    logger.info("🧪 Testing Sesame TTS (RunPod) Integration")
    logger.info("="*60)
    
    # Get service instance
    sesame_service = get_sesame_tts_service()
    
    # Test parameters
    test_text = "Hello! This is a test of the Sesame TTS service running on RunPod."
    test_speaker_id = 0
    
    logger.info(f"📝 Test text: {test_text}")
    logger.info(f"🎤 Speaker ID: {test_speaker_id}")
    logger.info("")
    
    try:
        # Generate speech
        logger.info("🚀 Generating speech...")
        audio_data = await sesame_service.generate_speech(
            text=test_text,
            speaker_id=test_speaker_id,
            output_format="wav"
        )
        
        if audio_data:
            logger.info(f"✅ SUCCESS! Generated {len(audio_data)} bytes of audio")
            logger.info(f"📊 Audio size: {len(audio_data) / 1024:.2f} KB")
            
            # Save test audio file
            output_file = "/tmp/test_sesame_output.wav"
            with open(output_file, 'wb') as f:
                f.write(audio_data)
            logger.info(f"💾 Saved test audio to: {output_file}")
            logger.info("")
            logger.info("🎉 Test PASSED - Sesame TTS integration working!")
            return True
        else:
            logger.error("❌ FAILED - No audio data returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ FAILED - Error: {e}")
        logger.exception(e)
        return False
    finally:
        # Cleanup
        await sesame_service.close()

if __name__ == "__main__":
    result = asyncio.run(test_sesame_tts())
    exit(0 if result else 1)
