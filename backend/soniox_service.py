import asyncio
import json
import logging
import websockets
import os
import re
from typing import Callable, Optional

logger = logging.getLogger(__name__)

SONIOX_API_KEY = os.getenv("SONIOX_API_KEY")


def clean_transcript(text: str) -> str:
    """
    Clean up Soniox transcript by fixing subword fragmentation.
    
    Soniox's telephony model returns subword tokens which causes patterns like:
    - "th ings" instead of "things"
    - "k ind" instead of "kind"  
    - "Ye ah" instead of "Yeah"
    
    This function intelligently joins fragments while preserving real word boundaries.
    """
    if not text:
        return text
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Common English words that should never be joined with adjacent words
    standalone = {
        'a', 'i', 'an', 'am', 'as', 'at', 'be', 'by', 'do', 'go', 'he', 'if',
        'in', 'is', 'it', 'me', 'my', 'no', 'of', 'on', 'or', 'so', 'to', 'up',
        'us', 'we', 'oh', 'uh', 'um', 'ok', 'hi', 'ah',
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
        'her', 'was', 'one', 'our', 'out', 'has', 'his', 'how', 'its', 'may',
        'new', 'now', 'old', 'see', 'way', 'who', 'did', 'get', 'got', 'let',
        'put', 'say', 'she', 'too', 'use', 'run', 'try', 'from', 'then', 'them',
        'some', 'this', 'that', 'with', 'have', 'will', 'your', 'what', 'when',
        'make', 'like', 'just', 'know', 'take', 'come', 'could', 'would', 'should',
        'after', 'going', 'people', 'money', 'around'
    }
    
    # First pass: Apply specific known fixes
    specific_fixes = [
        # Common fragments - multiple variations to catch different split patterns
        (r'\bO h\b', 'Oh'),
        (r'\bU h\b', 'Uh'),
        (r'\bU m\b', 'Um'),
        (r'\bYe ah\b', 'Yeah'),
        (r'\bYe s\b', 'Yes'),
        (r'\bO kay\b', 'Okay'),
        (r'\bOk ay\b', 'Okay'),  # Added: catches "Ok ay"
        (r'\bO k\b', 'Ok'),      # Added: catches "O k"
        (r'\bS ure\b', 'Sure'),
        (r'\bH ello\b', 'Hello'),
        (r'\bHel lo\b', 'Hello'),  # Added: catches "Hel lo"
        (r'\bH i\b', 'Hi'),        # Added: catches "H i"
        (r'\bN o\b', 'No'),        # Added: catches "N o"
        (r'\blik e\b', 'like'),
        (r'\bLik e\b', 'Like'),
        (r'\bgot ta\b', 'gotta'),
        (r'\bwan na\b', 'wanna'),
        (r'\bgon na\b', 'gonna'),
        (r'\bkin da\b', 'kinda'),
        (r'\bsor ry\b', 'sorry'),  # Added
        (r'\bSor ry\b', 'Sorry'),  # Added
        (r'\bthan ks\b', 'thanks'),  # Added
        (r'\bThan ks\b', 'Thanks'),  # Added
        # -ing patterns
        (r'\bg ett ing\b', 'getting'),
        (r'\bgett ing\b', 'getting'),
        (r'\bget ting\b', 'getting'),
        (r'\brush ing\b', 'rushing'),
        (r'\bhust ling\b', 'hustling'),
        (r'\bh ust le\b', 'hustle'),
        (r'\bmar ket ing\b', 'marketing'),
        (r'\bmarket ing\b', 'marketing'),
        (r'\bche ck ing\b', 'checking'),
        (r'\bcheck ing\b', 'checking'),
        (r'\bwork ing\b', 'working'),
        (r'\blook ing\b', 'looking'),
        (r'\btalk ing\b', 'talking'),
        (r'\bwalk ing\b', 'walking'),
        (r'\bcom ing\b', 'coming'),
        (r'\bgo ing\b', 'going'),
        (r'\btry ing\b', 'trying'),
        (r'\btr y ing\b', 'trying'),
        (r'\bbuy ing\b', 'buying'),
        (r'\bsell ing\b', 'selling'),
        (r'\bspend ing\b', 'spending'),
        (r'\bsp end ing\b', 'spending'),
        (r'\bsp end\b', 'spend'),
        (r'\bfind ing\b', 'finding'),
        (r'\brun ning\b', 'running'),
        (r'\bus ing\b', 'using'),
        (r'\bgener ate\b', 'generate'),
        (r'\bgenerat ing\b', 'generating'),
        # -tion patterns
        (r'\bques tion\b', 'question'),
        # -ly patterns
        (r'\bre all y\b', 'really'),
        (r'\bact ually\b', 'actually'),
        (r'\bdef inite ly\b', 'definitely'),
        (r'\bprob ably\b', 'probably'),
        (r'\bproba bly\b', 'probably'),
        (r'\bab solute ly\b', 'absolutely'),
        # -ey/-ay patterns
        (r'\bm oney\b', 'money'),
        (r'\bmone y\b', 'money'),
        (r'\bmon ey\b', 'money'),
        (r'\bto day\b', 'today'),
        # Common split words
        (r'\bth ose\b', 'those'),
        (r'\bth ese\b', 'these'),
        (r'\bth ings\b', 'things'),
        (r'\bth ing\b', 'thing'),
        (r'\bth at\b', 'that'),
        (r'\bth en\b', 'then'),
        (r'\bth em\b', 'them'),
        (r'\bth ere\b', 'there'),
        (r'\bth eir\b', 'their'),
        (r'\bth ey\b', 'they'),
        (r'\bth is\b', 'this'),
        (r'\bwh at\b', 'what'),
        (r'\bwh en\b', 'when'),
        (r'\bwh ere\b', 'where'),
        (r'\bwh ich\b', 'which'),
        (r'\bwh y\b', 'why'),
        (r'\bwh o\b', 'who'),
        (r'\by ou\b', 'you'),
        (r'\bY ou\b', 'You'),
        (r'\bk ind\b', 'kind'),
        (r'\bf ind\b', 'find'),
        (r'\bm ind\b', 'mind'),
        (r'\bb ehind\b', 'behind'),
        (r'\bso me\b', 'some'),
        (r'\bso mething\b', 'something'),
        (r'\bsome thing\b', 'something'),
        (r'\bany thing\b', 'anything'),
        (r'\bevery thing\b', 'everything'),
        (r'\bno thing\b', 'nothing'),
        (r'\ble ad\b', 'lead'),
        (r'\ble ads\b', 'leads'),
        (r'\blead s\b', 'leads'),
        (r'\ble ase\b', 'lease'),
        (r'\bad s\b', 'ads'),
        (r'\bf ulf ill\b', 'fulfill'),
        (r'\bfulf ill\b', 'fulfill'),
        (r'\bpro cess\b', 'process'),
        (r'\ba he ad\b', 'ahead'),
        (r'\bah ead\b', 'ahead'),
        (r'\btr y\b', 'try'),
        (r'\bgener ate\b', 'generate'),
        # Your/you're patterns
        (r"\by ou ' re\b", "you're"),
        (r"\by ou're\b", "you're"),
    ]
    
    for pattern, replacement in specific_fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Second pass: Generic pattern for single consonant + word fragments
    # Pattern: single consonant (not a/i) followed by space and 2+ letters
    def join_consonant_fragment(match):
        consonant = match.group(1)
        rest = match.group(2)
        # Only join if consonant is lowercase and rest starts with vowel or common pattern
        if consonant.lower() not in 'aeiou' and consonant.lower() != 'i':
            return consonant + rest
        return match.group(0)
    
    # Match single consonant + space + 2+ letters (case insensitive for first letter)
    text = re.sub(r'\b([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]) ([a-zA-Z]{2,})\b', 
                  join_consonant_fragment, text)
    
    # Third pass: Fix spacing around punctuation and apostrophes
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)  # Remove space before punctuation
    text = re.sub(r"(\w) ' (\w)", r"\1'\2", text)  # Fix apostrophe spacing
    text = re.sub(r"(\w)' (\w)", r"\1'\2", text)
    text = re.sub(r"(\w) '(\w)", r"\1'\2", text)
    
    # Fourth pass: Aggressive subword merging for short fragments
    # Pattern: 1-2 letter fragment + space + another fragment (when not standalone words)
    words = text.split()
    merged_words = []
    i = 0
    while i < len(words):
        current = words[i]
        
        # Check if this is a short fragment that should be merged with next word
        # FIX: Do not merge if current token contains digits (prevents "10" + "to" -> "10to")
        if (len(current) <= 2 and 
            not any(c.isdigit() for c in current) and
            current.lower() not in standalone and 
            i + 1 < len(words)):
            next_word = words[i + 1]
            # Merge if current is consonant-only or matches subword pattern
            if (not any(c in current.lower() for c in 'aeiou') or
                len(current) == 1 and current.lower() not in {'a', 'i'}):
                merged_words.append(current + next_word)
                i += 2
                continue
        
        merged_words.append(current)
        i += 1
    
    text = ' '.join(merged_words)
    
    # Final cleanup
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

class SonioxStreamingService:
    """
    Soniox Real-Time Speech-to-Text
    Handles real-time speech-to-text with advanced endpoint detection
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or SONIOX_API_KEY
        self.ws = None
        self.session_id = None
        
    async def connect(self, 
                     model: str = "stt-rt-v3",
                     audio_format: str = "mulaw",
                     sample_rate: int = 8000,
                     num_channels: int = 1,
                     enable_endpoint_detection: bool = True,
                     enable_speaker_diarization: bool = False,
                     language_hints: list = None,
                     context: str = ""):
        """
        Connect to Soniox Real-Time WebSocket API
        
        Args:
            model: Soniox model to use (default: stt-rt-v3 for best accuracy)
            audio_format: Audio format (mulaw, alaw, pcm_s16le, etc.)
            sample_rate: Audio sample rate (8000 or 16000)
            num_channels: Number of audio channels (1=mono, 2=stereo)
            enable_endpoint_detection: Enable automatic endpoint detection
            enable_speaker_diarization: Enable speaker diarization
            language_hints: List of language codes (e.g. ["en", "es"])
            context: Custom context for improved accuracy
        """
        url = "wss://stt-rt.soniox.com/transcribe-websocket"
        
        # Build configuration message
        config = {
            "api_key": self.api_key,
            "model": model,
            "audio_format": audio_format,
            "sample_rate": sample_rate,
            "num_channels": num_channels,
            "enable_endpoint_detection": enable_endpoint_detection,
        }
        
        # Add optional parameters
        if enable_speaker_diarization:
            config["enable_speaker_diarization"] = True
        
        if language_hints:
            config["language_hints"] = language_hints
        
        if context:
            config["context"] = context
        
        try:
            # Connect to Soniox WebSocket
            # Increased ping_timeout from 10s to 30s to handle network latency and prevent 408 timeout errors
            self.ws = await websockets.connect(url, ping_interval=30, ping_timeout=30)
            logger.info(f"✅ Connected to Soniox Real-Time STT")
            
            # Send configuration message
            await self.ws.send(json.dumps(config))
            logger.info(f"⚙️  Config: model={model}, format={audio_format}, rate={sample_rate}Hz, channels={num_channels}")
            logger.info(f"⚙️  Endpoint detection: {enable_endpoint_detection}, Speaker diarization: {enable_speaker_diarization}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Soniox: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to Soniox (binary WebSocket frame)"""
        if self.ws and not self.ws.closed:
            try:
                # Soniox expects raw binary audio data
                await self.ws.send(audio_data)
            except Exception as e:
                logger.error(f"❌ Error sending audio to Soniox: {e}")
    
    async def receive_messages(self, 
                               on_partial_transcript: Optional[Callable] = None,
                               on_final_transcript: Optional[Callable] = None,
                               on_endpoint_detected: Optional[Callable] = None):
        """
        Receive and process messages from Soniox
        
        Args:
            on_partial_transcript: Callback for non-final tokens
            on_final_transcript: Callback for final tokens  
            on_endpoint_detected: Callback for <end> token (endpoint detected)
        """
        # Accumulate final tokens until endpoint detection for cleaner transcripts
        accumulated_final_tokens = []
        
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                # Check for errors
                if "error_code" in data:
                    error_code = data.get("error_code")
                    error_message = data.get("error_message", "Unknown error")
                    logger.error(f"❌ Soniox error {error_code}: {error_message}")
                    break
                
                # Check for finished signal
                if data.get("finished"):
                    logger.info("🛑 Soniox session finished")
                    break
                
                # Process tokens
                tokens = data.get("tokens", [])
                if tokens:
                    # 🔍 DEBUG: Log raw token evolution (as per Soniox docs)
                    token_summary = []
                    for t in tokens:
                        token_text = t.get("text", "")
                        is_final = t.get("is_final", False)
                        status = "✓" if is_final else "?"
                        token_summary.append(f'"{token_text}"{status}')
                    logger.info(f"🔤 RAW TOKENS: [{', '.join(token_summary)}]")
                    
                    # Separate final and non-final tokens
                    final_tokens = []
                    non_final_tokens = []
                    endpoint_detected = False
                    
                    for token in tokens:
                        text = token.get("text", "")
                        is_final = token.get("is_final", False)
                        
                        # Check for endpoint token
                        if text == "<end>" and is_final:
                            endpoint_detected = True
                            logger.info(f"🎯 Endpoint detected: <end> token received")
                            continue  # Don't include <end> in transcript
                        
                        if is_final:
                            final_tokens.append(token)
                        else:
                            non_final_tokens.append(token)
                    
                    # Callbacks for non-final tokens (partial transcripts)
                    if non_final_tokens and on_partial_transcript:
                        text = "".join([t.get("text", "") for t in non_final_tokens])
                        # Clean up the transcript to fix split words
                        text = clean_transcript(text)
                        if text.strip():
                            logger.info(f"🔍 Soniox (partial): {text[:50]}...")
                            await on_partial_transcript(text, data)
                    
                    # Accumulate final tokens
                    if final_tokens:
                        prev_count = len(accumulated_final_tokens)
                        accumulated_final_tokens.extend(final_tokens)
                        
                        # Log the token accumulation
                        new_final = "".join([t.get("text", "") for t in final_tokens])
                        logger.info(f"📥 FINAL TOKENS ADDED: +'{new_final}' (total: {len(accumulated_final_tokens)} tokens)")
                        
                        # Send accumulated transcript on each final token batch
                        # This gives the LLM context while waiting for endpoint
                        text = "".join([t.get("text", "") for t in accumulated_final_tokens])
                        raw_text = text
                        text = clean_transcript(text)
                        if raw_text != text:
                            logger.info(f"🧹 Cleaned transcript: '{raw_text}' -> '{text}'")
                        
                        if text.strip() and on_final_transcript:
                            logger.info(f"✅ Soniox ACCUMULATED (final): '{text}'")
                            await on_final_transcript(text, data)
                    
                    # When endpoint detected, clear accumulator and trigger callback
                    if endpoint_detected:
                        # Final cleanup and send complete transcript
                        if accumulated_final_tokens:
                            complete_text = "".join([t.get("text", "") for t in accumulated_final_tokens])
                            complete_text = clean_transcript(complete_text)
                            logger.info(f"🏁 ENDPOINT: Complete utterance ready: '{complete_text}'")
                        else:
                            logger.info(f"🏁 ENDPOINT: No final tokens accumulated")
                        
                        # Clear accumulator for next utterance
                        accumulated_final_tokens = []
                        
                        if on_endpoint_detected:
                            logger.info(f"🚀 TRIGGERING LLM PROCESSING (on_endpoint_detected callback)")
                            await on_endpoint_detected()
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 Soniox connection closed")
        except Exception as e:
            logger.error(f"❌ Error receiving Soniox messages: {e}")
    
    async def finalize_manually(self):
        """Send manual finalization message to force all tokens to become final"""
        if self.ws and not self.ws.closed:
            try:
                finalize_message = {"type": "finalize"}
                await self.ws.send(json.dumps(finalize_message))
                logger.info("📌 Sent manual finalization request to Soniox")
            except Exception as e:
                logger.error(f"❌ Error sending finalization: {e}")
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.ws and not self.ws.closed:
            try:
                # Send empty frame to gracefully end stream
                await self.ws.send(b"")
                logger.info("✅ Sent end-of-stream signal to Soniox")
                
                # Wait briefly for final responses
                await asyncio.sleep(0.5)
                
                await self.ws.close()
                logger.info("✅ Soniox session closed gracefully")
            except Exception as e:
                logger.error(f"❌ Error closing Soniox session: {e}")
