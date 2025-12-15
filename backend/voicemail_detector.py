"""
Voicemail and IVR Detection Module
Real-time pattern matching for voicemail greetings and IVR systems.
Zero-latency detection runs in parallel with call processing.
"""
import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Voicemail detection patterns (high confidence)
VOICEMAIL_PATTERNS = [
    # Common voicemail phrases
    r"leave.*mess\s*age.*after.*beep",
    r"leave.*mess\s*age.*after.*ton\s*e",
    r"ple\s*ase.*leave.*mess\s*age",
    r"ple\s*ase.*rec\s*ord.*mess\s*age",  # Added: "please record your message"
    r"not.*avail\s*able.*right.*now",
    r"not.*avail\s*able.*at.*the.*ton\s*e",  # Added: "not available. At the tone"
    r"person.*you.*try\s*ing.*reach.*not.*avail\s*able",  # Added: "The person you're trying to reach is not available"
    r"can\s*not.*take.*call",
    r"can\s*\'?t.*tak\s*e.*call", # "Can'ttak eyour call"
    r"reach.*mail\s*box",
    r"voice.*mail.*system",
    r"rec\s*ord.*mess\s*age.*after.*ton\s*e",
    r"rec\s*ord.*mess\s*age.*after.*beep",
    r"at.*the.*ton\s*e.*rec\s*ord",  # Added: "At the tone, please record"
    r"at.*the.*ton\s*e.*ple\s*ase",  # Added: "At the tone, please..."
    r"at.*the.*ton\s*e",
    r"after.*the.*beep",
    r"mail\s*box.*is.*full",
    r"you.*have.*reached.*voice\s*mail",
    r"when.*you.*have.*fin\s*ished.*rec\s*ord\s*ing",  # Added: "When you have finished recording"
    r"you.*may.*hang.*up",  # Added: "you may hang up"
    r"hang.*up.*or.*press",
]

# IVR detection patterns (automated system)
IVR_PATTERNS = [
    # Press digit instructions
    r"press\s+\d+\s+for",
    r"press\s+\d+\s+to",
    r"dial\s+\d+\s+for",
    r"say\s+\d+\s+for",
    r"push\s+\d+\s+for",
    # Garbled press instructions (text numbers)
    r"press\s*on\s*e",
    r"press\s*two",
    r"press\s*thre\s*e",
    r"press\s*fo\s*ur",
    r"press\s*fi\s*ve",
    r"press\s*po\s*und",
    r"press\s*star",
    # Menu navigation
    r"for.*press\s+\d+",
    r"to.*press\s+\d+",
    r"main.*menu",
    r"return.*to.*menu",
    r"speak.*to.*representative.*press",
    r"operator.*press.*0",
    r"stay.*on.*the.*line",
    r"your.*call.*is.*imp\s*or\s*tant",
    # Business hours / closed messages
    r"office.*hours",
    r"currently.*closed",
    r"normal.*business.*hours",
]

# Gatekeeper patterns - "Press X to connect/accept" type systems
# These require sending DTMF to get through to a human
GATEKEEPER_PATTERNS = [
    r"press\s+(\d+)\s+to\s+(?:connect|accept|answer|speak|talk)",
    r"press\s+(\d+)\s+to\s+be\s+connected",
    r"press\s+(\d+)\s+if\s+you\s+(?:are|want)",
    r"to\s+(?:connect|accept|answer)\s+(?:this\s+call\s+)?press\s+(\d+)",
    r"dial\s+(\d+)\s+to\s+(?:connect|accept|answer)",
    r"(?:connect|accept|answer)\s+press\s+(\d+)",
]

def detect_gatekeeper(transcript: str) -> Tuple[bool, str]:
    """
    Detect "press X to connect" type gatekeeper systems and extract the digit.
    
    Returns:
        Tuple of (is_gatekeeper, digit_to_press)
        - is_gatekeeper: True if gatekeeper detected
        - digit_to_press: The digit to send (e.g., "1") or None
    """
    if not transcript or len(transcript.strip()) < 10:
        return False, None
    
    transcript_lower = transcript.lower()
    
    for pattern in GATEKEEPER_PATTERNS:
        match = re.search(pattern, transcript_lower)
        if match:
            digit = match.group(1) if match.groups() else "1"
            logger.info(f"🚪 Gatekeeper detected! Pattern: {pattern}, Digit to press: {digit}")
            return True, digit
    
    return False, None

def detect_voicemail_or_ivr(transcript: str, context: Dict = None) -> Tuple[bool, str, float]:
    """
    Detect if transcript contains voicemail or IVR patterns.
    
    Args:
        transcript: User transcript text to analyze
        context: Optional context (call duration, word count, etc.)
    
    Returns:
        Tuple of (is_detected, detection_type, confidence)
        - is_detected: True if voicemail/IVR detected
        - detection_type: "voicemail" or "ivr" or "none"
        - confidence: 0.0 to 1.0
    """
    if not transcript or len(transcript.strip()) < 10:
        return False, "none", 0.0
    
    transcript_lower = transcript.lower()
    
    # Check voicemail patterns
    voicemail_matches = 0
    for pattern in VOICEMAIL_PATTERNS:
        if re.search(pattern, transcript_lower):
            voicemail_matches += 1
            logger.debug(f"Voicemail pattern matched: {pattern}")
    
    # Check IVR patterns
    ivr_matches = 0
    for pattern in IVR_PATTERNS:
        if re.search(pattern, transcript_lower):
            ivr_matches += 1
            logger.debug(f"IVR pattern matched: {pattern}")
    
    # Additional heuristics
    word_count = len(transcript.split())
    
    # Long monologue (>50 words) without interaction is suspicious
    is_long_monologue = word_count > 50
    
    # Calculate confidence
    if voicemail_matches > 0:
        confidence = min(0.5 + (voicemail_matches * 0.2), 1.0)
        if voicemail_matches >= 2:  # High confidence with multiple matches
            confidence = 0.9
        return True, "voicemail", confidence
    
    if ivr_matches > 0:
        confidence = min(0.5 + (ivr_matches * 0.15), 1.0)
        if ivr_matches >= 2:  # High confidence with multiple matches
            confidence = 0.85
        return True, "ivr", confidence
    
    # Edge case: Very long monologue might be IVR
    if is_long_monologue and context:
        call_duration = context.get("call_duration_seconds", 0)
        if call_duration < 20:  # Long speech at start = likely IVR
            return True, "ivr", 0.6
    
    return False, "none", 0.0


def should_disconnect(detection_type: str, confidence: float, settings: Dict) -> bool:
    """
    Determine if call should be disconnected based on detection.
    
    Args:
        detection_type: "voicemail" or "ivr"
        confidence: Detection confidence (0.0 to 1.0)
        settings: Agent's voicemail detection settings
    
    Returns:
        True if should disconnect
    """
    if not settings.get("enabled", True):
        return False
    
    if not settings.get("disconnect_on_detection", True):
        return False
    
    # High confidence threshold (0.7+) for auto-disconnect
    # This prevents false positives
    if confidence >= 0.7:
        logger.info(f"🤖 High confidence {detection_type} detected ({confidence:.2f}) - recommending disconnect")
        return True
    
    # Medium confidence (0.5-0.7) - log but don't disconnect
    if confidence >= 0.5:
        logger.warning(f"⚠️ Medium confidence {detection_type} detected ({confidence:.2f}) - monitoring")
        return False
    
    return False


class VoicemailDetector:
    """Stateful voicemail/IVR detector for call sessions"""
    
    def __init__(self, agent_settings: Dict):
        self.settings = agent_settings.get("voicemail_detection", {})
        self.enabled = self.settings.get("enabled", True)
        self.use_llm_detection = self.settings.get("use_llm_detection", True)
        self.accumulated_transcript = ""
        self.detection_made = False
        self.detection_type = None
        self.call_start_time = None
        
    def analyze_transcript(self, new_transcript: str, call_start_time: float = None) -> Tuple[bool, str, float]:
        """
        Analyze new transcript chunk for voicemail/IVR patterns.
        
        Args:
            new_transcript: New transcript text
            call_start_time: Unix timestamp of call start
        
        Returns:
            Tuple of (should_disconnect, detection_type, confidence)
        """
        if not self.enabled or not self.use_llm_detection:
            return False, "none", 0.0
        
        if self.detection_made:
            return False, self.detection_type, 0.0
        
        # Accumulate transcript
        self.accumulated_transcript += " " + new_transcript
        self.accumulated_transcript = self.accumulated_transcript.strip()
        
        # Build context
        import time
        context = {}
        if call_start_time:
            context["call_duration_seconds"] = time.time() - call_start_time
        
        # Run detection
        is_detected, detection_type, confidence = detect_voicemail_or_ivr(
            self.accumulated_transcript, 
            context
        )
        
        if is_detected:
            logger.info(f"🔍 Detection: {detection_type} (confidence: {confidence:.2f})")
            logger.info(f"   Transcript: {self.accumulated_transcript[:100]}...")
            
            # Check if should disconnect
            if should_disconnect(detection_type, confidence, self.settings):
                self.detection_made = True
                self.detection_type = detection_type
                return True, detection_type, confidence
        
        return False, detection_type, confidence
    
    def check_for_gatekeeper(self, transcript: str) -> Tuple[bool, str]:
        """
        Check if transcript contains a gatekeeper "press X to connect" message.
        
        Returns:
            Tuple of (is_gatekeeper, digit_to_press)
        """
        if not self.enabled:
            return False, None
        
        # Check for gatekeeper patterns
        return detect_gatekeeper(transcript)
