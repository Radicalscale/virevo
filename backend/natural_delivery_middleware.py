import re
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class NaturalDeliveryMiddleware:
    """
    Middleware to intercept LLM output and optimize it for natural TTS delivery.
    Supports Dual-Stream architecture:
    1. Logic Stream: Clean text for variable extraction and history.
    2. Audio Stream: Rich text with SSML/Voice Settings for TTS.
    
    Now supports both ElevenLabs and Maya TTS with provider-specific formatting.
    """
    
    # ElevenLabs: Emotional mapping to Voice Settings (Stability, Style)
    # Lower stability = More expressive/variable
    # Higher style = More exaggerated delivery
    ELEVENLABS_EMOTION_MAP = {
        "H": {"stability": 0.30, "style": 0.75},   # Happy: High energy, very expressive
        "S": {"stability": 0.50, "style": 0.30},   # Serious: Grounded but not monotone
        "N": {"stability": 0.40, "style": 0.20}    # Neutral: Engaged, not flat
    }
    
    # Maya TTS: Emotional mapping to Maya emotion tags
    # These are inserted into the text for Maya to interpret
    MAYA_EMOTION_MAP = {
        "H": "<excited>",      # Happy -> Excited tag
        "S": "",               # Serious -> No tag (natural serious tone)
        "N": "",               # Neutral -> No tag
        "L": "<laugh>",        # Laugh
        "C": "<chuckle>",      # Chuckle
        "G": "<sigh>",         # Sigh (like exasperation)
        "A": "<angry>",        # Angry
        "U": "<curious>",      # cUrious
        "D": "<disappointed>", # Disappointed
        "R": "<sarcastic>",    # saRcastic
        "W": "<whisper>",      # Whisper
    }

    def __init__(self):
        self.current_emotion = "N"

    def process(self, text: str, model_id: str = "eleven_flash_v2_5", tts_provider: str = "elevenlabs") -> Tuple[str, Dict]:
        """
        Process text chunk and return separate streams for Logic and Audio.
        
        Args:
            text: Raw text chunk from LLM (may contain [H]/[S]/[L] tags)
            model_id: The ElevenLabs model ID being used (flash vs turbo)
            tts_provider: The TTS provider ("elevenlabs", "maya", "cartesia", etc.)
            
        Returns:
            Tuple[clean_text, audio_payload]
            - clean_text: Pure text for history/logic
            - audio_payload: Dict with "text" and optional "voice_settings" for TTS
        """
        # 1. Detect and Extract Emotion Tag
        # Support extended tags for Maya: [H], [S], [N], [L], [C], [G], [A], [U], [D], [R], [W]
        match = re.match(r'^\[([HSNLCGAUDRW])\]\s*', text)
        if match:
            self.current_emotion = match.group(1)
            # Strip the tag from the text
            clean_text = re.sub(r'^\[([HSNLCGAUDRW])\]\s*', '', text)
        else:
            clean_text = text
        
        # 2. Route to provider-specific processing
        if tts_provider.lower() == "maya":
            return self._process_maya(clean_text, self.current_emotion)
        else:
            # ElevenLabs, Cartesia, or other providers
            return self._process_elevenlabs(clean_text, self.current_emotion, model_id)
    
    def _process_maya(self, text: str, emotion_code: str) -> Tuple[str, Dict]:
        """
        Process text for Maya TTS using emotion tags.
        
        Maya uses inline tags like <laugh>, <sigh>, <excited> etc.
        These are injected at the start of the text.
        """
        # Get the Maya emotion tag for this emotion code
        emotion_tag = self.MAYA_EMOTION_MAP.get(emotion_code, "")
        
        # Insert emotion tag at the beginning if we have one
        if emotion_tag:
            final_audio_text = f"{emotion_tag} {text}"
            logger.debug(f"🎭 Maya emotion applied: {emotion_tag}")
        else:
            final_audio_text = text
        
        # Also handle any inline emotion hints in the text
        # Convert common patterns to Maya tags
        final_audio_text = self._convert_inline_emotions_maya(final_audio_text)
        
        # Maya doesn't use voice_settings like ElevenLabs
        audio_payload = {
            "text": final_audio_text,
            "voice_settings": {}  # Maya ignores this, uses temperature/seed instead
        }
        
        return text, audio_payload  # Return original clean_text without tags
    
    def _convert_inline_emotions_maya(self, text: str) -> str:
        """
        Convert common emotional cues in text to Maya emotion tags.
        
        Examples:
        - "*laughs*" or "(laughs)" -> <laugh>
        - "*sighs*" or "(sighs)" -> <sigh>
        - "*chuckles*" -> <chuckle>
        """
        # Laugh patterns
        text = re.sub(r'\*laughs?\*|\(laughs?\)', '<laugh>', text, flags=re.IGNORECASE)
        text = re.sub(r'\*chuckles?\*|\(chuckles?\)', '<chuckle>', text, flags=re.IGNORECASE)
        text = re.sub(r'\*giggles?\*|\(giggles?\)', '<giggle>', text, flags=re.IGNORECASE)
        
        # Breath patterns
        text = re.sub(r'\*sighs?\*|\(sighs?\)', '<sigh>', text, flags=re.IGNORECASE)
        text = re.sub(r'\*gasps?\*|\(gasps?\)', '<gasp>', text, flags=re.IGNORECASE)
        text = re.sub(r'\*exhales?\*|\(exhales?\)', '<exhale>', text, flags=re.IGNORECASE)
        
        # Emotional patterns (less common in natural dialogue)
        text = re.sub(r'\*angrily\*|\(angry\)', '<angry>', text, flags=re.IGNORECASE)
        text = re.sub(r'\*excitedly\*|\(excited\)', '<excited>', text, flags=re.IGNORECASE)
        text = re.sub(r'\*sarcastically\*|\(sarcastic\)', '<sarcastic>', text, flags=re.IGNORECASE)
        text = re.sub(r'\*whispers?\*|\(whispers?\)', '<whisper>', text, flags=re.IGNORECASE)
        
        return text
    
    def _process_elevenlabs(self, text: str, emotion_code: str, model_id: str) -> Tuple[str, Dict]:
        """
        Process text for ElevenLabs TTS using voice settings and SSML.
        Original ElevenLabs processing logic.
        """
        # Strategy Selection based on Model
        if "flash" in model_id.lower():
            # FLASH STRATEGY: Stability + Pauses (Zero Latency)
            voice_settings = self._get_flash_settings(emotion_code)
            final_audio_text = self._insert_pauses(text)
            
        elif "turbo" in model_id.lower() or "multilingual" in model_id.lower():
            # TURBO STRATEGY: SSML Prosody (High Fidelity)
            voice_settings = {"stability": 0.5} 
            final_audio_text = self._apply_ssml_prosody(text, emotion_code)
            
        else:
            # Fallback (treat as Flash)
            voice_settings = self._get_flash_settings(emotion_code)
            final_audio_text = text

        audio_payload = {
            "text": final_audio_text,
            "voice_settings": voice_settings
        }
        
        return text, audio_payload

    def _get_flash_settings(self, emotion_code: str) -> Dict:
        """Get voice settings optimized for ElevenLabs Flash v2.5"""
        return self.ELEVENLABS_EMOTION_MAP.get(emotion_code, self.ELEVENLABS_EMOTION_MAP["N"])

    def _insert_pauses(self, text: str) -> str:
        """
        Insert micro-pauses for 'Lilt' in ElevenLabs Flash v2.5.
        Flash responds well to <break> tags.
        """
        # Tightened from 0.2s to 0.1s - pauses were too long
        return re.sub(r',(?!\d)', ',<break time="0.1s"/>', text)

    def _apply_ssml_prosody(self, text: str, emotion_code: str) -> str:
        """
        Apply SSML prosody tags for ElevenLabs Turbo v2.5.
        """
        if emotion_code == "H":
            return f'<prosody pitch="+10%" rate="105%">{text}</prosody>'
        elif emotion_code == "S":
            return f'<prosody pitch="-5%" rate="90%">{text}</prosody>'
        
        return text


# Convenience function
def get_middleware() -> NaturalDeliveryMiddleware:
    """Get a configured middleware instance."""
    return NaturalDeliveryMiddleware()
