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
    """
    
    # Emotional mapping to Voice Settings (Stability, Style)
    # Lower stability = More expressive/variable
    # Higher stability = More consistent/serious
    EMOTION_MAP = {
        "H": {"stability": 0.35, "style": 0.5},   # Happy/Excited
        "S": {"stability": 0.75, "style": 0.0},   # Serious/Empathetic
        "N": {"stability": 0.5, "style": 0.0}     # Neutral (Default)
    }

    def __init__(self):
        self.current_emotion = "N"

    def process(self, text: str, model_id: str = "eleven_flash_v2_5") -> Tuple[str, Dict]:
        """
        Process text chunk and return separate streams for Logic and Audio.
        
        Args:
            text: Raw text chunk from LLM (may contain [H]/[S] tags)
            model_id: The ElevenLabs model ID being used (flash vs turbo)
            
        Returns:
            Tuple[clean_text, audio_payload]
            - clean_text: Pure text for history/logic
            - audio_payload: Dict with "text" and "voice_settings" for TTS
        """
        # 1. Detect and Extract Emotion
        # Check for tags like [H], [S], [N] at start of text
        match = re.match(r'^\[([HSN])\]\s*', text)
        if match:
            self.current_emotion = match.group(1)
            # Strip the tag from the text
            clean_text = re.sub(r'^\[([HSN])\]\s*', '', text)
        else:
            clean_text = text
            
        # 2. Strategy Selection based on Model
        if "flash" in model_id.lower():
            # FLASH STRATEGY: Stability + Pauses (Zero Latency)
            # Flash ignores prosody tags, so we use stability and breaks
            voice_settings = self._get_flash_settings(self.current_emotion)
            final_audio_text = self._insert_pauses(clean_text)
            
        elif "turbo" in model_id.lower() or "multilingual" in model_id.lower():
            # TURBO STRATEGY: SSML Prosody (High Fidelity)
            # Turbo respects pitch/rate tags
            # We keep default stability to let prosody do the work (or slight adjustment)
            voice_settings = {"stability": 0.5} 
            final_audio_text = self._apply_ssml_prosody(clean_text, self.current_emotion)
            
        else:
            # Fallback (treat as Flash)
            voice_settings = self._get_flash_settings(self.current_emotion)
            final_audio_text = clean_text

        # 3. Construct Payload
        audio_payload = {
            "text": final_audio_text,
            "voice_settings": voice_settings
        }
        
        return clean_text, audio_payload

    def _get_flash_settings(self, emotion_code: str) -> Dict:
        """Get voice settings optimized for Flash v2.5"""
        return self.EMOTION_MAP.get(emotion_code, self.EMOTION_MAP["N"])

    def _insert_pauses(self, text: str) -> str:
        """
        Insert micro-pauses for 'Lilt' in Flash v2.5.
        Flash responds well to <break> tags.
        """
        # Add slight break after commas for pacing
        # But ensure we don't break simple lists too aggressively
        # Regex: Replace comma not followed by digit (to avoid breaking numbers like 1,000)
        return re.sub(r',(?!\d)', ',<break time="0.1s"/>', text)

    def _apply_ssml_prosody(self, text: str, emotion_code: str) -> str:
        """
        Apply SSML prosody tags for Turbo v2.5.
        """
        if emotion_code == "H":
            # Happy: Higher pitch, slightly faster
            return f'<prosody pitch="+10%" rate="105%">{text}</prosody>'
        elif emotion_code == "S":
            # Serious: Lower pitch, slower
            return f'<prosody pitch="-5%" rate="90%">{text}</prosody>'
        
        return text
