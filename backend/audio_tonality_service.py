"""
Audio-Based Tonality Analysis Service

Uses OpenAI's audio models to analyze actual audio recordings for emotional
tonality, rather than just transcript text. This provides much more accurate
emotional analysis including:
- Voice pitch and energy
- Speaking pace and rhythm
- Hesitation and confidence markers
- Emotional undertones not captured in text

Integrates with the QC learning system for continuous improvement.
"""

import logging
import os
import httpx
import base64
import tempfile
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

# Supported audio formats for OpenAI
SUPPORTED_AUDIO_FORMATS = ['mp3', 'wav', 'webm', 'mp4', 'm4a', 'mpga', 'mpeg']


class AudioTonalityAnalyzer:
    """
    Analyzes audio recordings for emotional tonality using OpenAI's audio models.
    
    Uses gpt-4o-audio-preview for direct audio understanding, which can detect:
    - Emotional state from voice characteristics
    - Confidence vs hesitation
    - Energy and enthusiasm levels
    - Frustration or satisfaction markers
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o-audio-preview"):
        """
        Initialize the analyzer.
        
        Args:
            api_key: OpenAI API key (or Emergent LLM key for universal access)
            model: Audio model to use (default: gpt-4o-audio-preview)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    async def analyze_audio_segment(
        self, 
        audio_data: bytes, 
        audio_format: str,
        system_prompt: str,
        analysis_prompt: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single audio segment for tonality.
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Format (mp3, wav, etc.)
            system_prompt: System instructions for analysis
            analysis_prompt: Specific analysis request
            context: Additional context (KB, agent config, etc.)
        
        Returns:
            Analysis results with emotion scores, confidence, etc.
        """
        try:
            # Encode audio as base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Build the request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Construct message with audio input
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add context if provided
            if context:
                context_str = json.dumps(context, indent=2)
                messages.append({
                    "role": "user", 
                    "content": f"Context for analysis:\n{context_str}"
                })
            
            # Add audio for analysis
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_b64,
                            "format": audio_format
                        }
                    },
                    {
                        "type": "text",
                        "text": analysis_prompt
                    }
                ]
            })
            
            payload = {
                "model": self.model,
                "messages": messages,
                "modalities": ["text"],  # We only need text output for analysis
                "max_tokens": 2000,
                "temperature": 0.3  # Lower temp for more consistent analysis
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"OpenAI audio API error: {response.status_code} - {error_detail}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                        "detail": error_detail
                    }
                
                result = response.json()
                analysis_text = result['choices'][0]['message']['content']
                
                # Try to parse as JSON if the response is structured
                try:
                    analysis_json = json.loads(analysis_text)
                    return {
                        "success": True,
                        "analysis": analysis_json,
                        "raw_response": analysis_text
                    }
                except json.JSONDecodeError:
                    # Return as structured dict with raw text
                    return {
                        "success": True,
                        "analysis": {"raw_analysis": analysis_text},
                        "raw_response": analysis_text
                    }
        
        except Exception as e:
            logger.error(f"Error analyzing audio segment: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_recording_url(
        self,
        recording_url: str,
        system_prompt: str,
        analysis_prompt: str,
        context: Dict[str, Any] = None,
        max_duration_seconds: int = 300,  # 5 minutes max
        auth_headers: Dict[str, str] = None  # Authentication headers for protected URLs
    ) -> Dict[str, Any]:
        """
        Download and analyze a recording from URL.
        
        Args:
            recording_url: URL to the audio recording
            system_prompt: System instructions for analysis
            analysis_prompt: Specific analysis request
            context: Additional context
            max_duration_seconds: Maximum audio duration to process
            auth_headers: Optional auth headers for protected recording URLs
        
        Returns:
            Analysis results
        """
        try:
            # Download the audio file
            logger.info(f"Downloading audio from: {recording_url}")
            
            # Build headers for download
            download_headers = {}
            if auth_headers:
                download_headers.update(auth_headers)
            
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.get(recording_url, headers=download_headers)
                
                if response.status_code == 403:
                    # Try with common auth patterns
                    logger.warning("403 Forbidden when downloading audio. Trying alternative methods...")
                    
                    # Some services need the URL to be accessed with specific query params
                    # Try adding common access tokens if the URL has them
                    if '?' not in recording_url:
                        # Try without auth as some URLs work after redirect
                        response = await client.get(recording_url, follow_redirects=True)
                    
                    if response.status_code == 403:
                        return {
                            "success": False,
                            "error": "Failed to download audio: 403 Forbidden. The recording URL may have expired or require authentication.",
                            "suggestion": "Please ensure the recording URL is accessible. Some services require regenerating the URL or providing an API key."
                        }
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Failed to download audio: {response.status_code}"
                    }
                
                audio_data = response.content
                
                # Determine format from URL or content-type
                content_type = response.headers.get('content-type', '')
                if 'mp3' in recording_url.lower() or 'mpeg' in content_type:
                    audio_format = 'mp3'
                elif 'wav' in recording_url.lower() or 'wav' in content_type:
                    audio_format = 'wav'
                elif 'webm' in recording_url.lower() or 'webm' in content_type:
                    audio_format = 'webm'
                else:
                    audio_format = 'mp3'  # Default to mp3
                
                logger.info(f"Downloaded {len(audio_data)} bytes, format: {audio_format}")
                
                # Check file size (OpenAI has limits)
                max_size_mb = 25  # OpenAI limit
                if len(audio_data) > max_size_mb * 1024 * 1024:
                    return {
                        "success": False,
                        "error": f"Audio file too large ({len(audio_data) / 1024 / 1024:.1f}MB). Max: {max_size_mb}MB"
                    }
                
                # Analyze the audio
                return await self.analyze_audio_segment(
                    audio_data=audio_data,
                    audio_format=audio_format,
                    system_prompt=system_prompt,
                    analysis_prompt=analysis_prompt,
                    context=context
                )
        
        except Exception as e:
            logger.error(f"Error analyzing recording URL: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


def build_tonality_system_prompt(
    agent_config: Dict[str, Any] = None,
    knowledge_base: str = None,
    custom_guidelines: str = None
) -> str:
    """
    Build a comprehensive system prompt for tonality analysis.
    
    Incorporates agent configuration, KB, and custom guidelines to make
    the analysis context-aware and aligned with the agent's purpose.
    """
    
    base_prompt = """You are an expert audio tonality and emotional intelligence analyst for AI voice agents.

Your task is to analyze voice recordings and provide detailed emotional and tonal insights that would NOT be apparent from text transcripts alone.

## What to Analyze:

### Voice Characteristics:
- **Pitch patterns**: Rising (questioning/uncertain), falling (confident/conclusive), flat (disengaged)
- **Speaking pace**: Fast (excited/nervous), slow (calm/thoughtful), variable (engaged)
- **Volume dynamics**: Loud (assertive/frustrated), soft (hesitant/intimate)
- **Voice quality**: Clear (confident), breathy (nervous), strained (stressed)

### Emotional Markers:
- **Primary emotions**: Joy, frustration, anger, sadness, fear, surprise, neutral
- **Secondary emotions**: Anxiety, confidence, enthusiasm, boredom, satisfaction
- **Emotional intensity**: Scale 1-10
- **Emotional consistency**: Stable vs fluctuating

### Engagement Indicators:
- **Interest level**: Active listening cues, engagement sounds
- **Hesitation markers**: Pauses, filler words, restarts
- **Confidence indicators**: Assertive statements vs hedging language
- **Rapport signals**: Matching energy, collaborative tone

### Interaction Quality:
- **Turn-taking flow**: Smooth vs interrupted
- **Response appropriateness**: Does tone match context?
- **Emotional mirroring**: Agent matching user's energy appropriately

## Output Format:
Always respond with valid JSON containing your analysis."""

    # Add agent context if available
    if agent_config:
        agent_name = agent_config.get('name', 'AI Agent')
        agent_purpose = agent_config.get('system_prompt', '')[:500] if agent_config.get('system_prompt') else ''
        
        base_prompt += f"""

## Agent Context:
- **Agent Name**: {agent_name}
- **Agent Purpose**: {agent_purpose[:300]}...

Consider the agent's purpose when evaluating if emotional responses are appropriate."""

    # Add knowledge base context if available
    if knowledge_base:
        base_prompt += f"""

## Knowledge Base Context:
The agent has access to this knowledge base, which should inform expected conversation topics:
{knowledge_base[:1000]}..."""

    # Add custom guidelines
    if custom_guidelines:
        base_prompt += f"""

## Custom Analysis Guidelines:
{custom_guidelines}"""

    return base_prompt


def build_analysis_prompt(
    transcript: List[Dict] = None,
    focus_areas: List[str] = None
) -> str:
    """
    Build the analysis request prompt.
    
    Args:
        transcript: Optional transcript for reference
        focus_areas: Specific areas to focus analysis on
    """
    
    prompt = """Analyze the audio recording and provide a detailed tonality assessment.

Return your analysis as JSON with this structure:

```json
{
    "overall_assessment": {
        "primary_emotion": "emotion_name",
        "emotion_intensity": 1-10,
        "confidence_level": 1-10,
        "engagement_level": 1-10,
        "overall_tone": "positive|negative|neutral|mixed"
    },
    "speaker_analysis": {
        "user": {
            "emotions_detected": ["emotion1", "emotion2"],
            "dominant_emotion": "emotion_name",
            "confidence": "high|medium|low",
            "engagement": "high|medium|low",
            "notable_moments": ["description of key emotional moments"]
        },
        "agent": {
            "tone_appropriateness": 1-10,
            "emotional_matching": 1-10,
            "energy_level": "high|medium|low",
            "areas_for_improvement": ["specific suggestions"]
        }
    },
    "emotional_journey": [
        {
            "timestamp_description": "beginning|middle|end or time estimate",
            "emotion_shift": "description of emotional change",
            "trigger": "what caused the shift"
        }
    ],
    "recommendations": {
        "ssml_suggestions": ["specific SSML tags to improve delivery"],
        "tone_adjustments": ["how agent should adjust tone"],
        "pacing_suggestions": ["speed/rhythm recommendations"]
    },
    "flags": {
        "frustration_detected": true|false,
        "confusion_detected": true|false,
        "satisfaction_signals": true|false,
        "rapport_established": true|false
    },
    "quality_scores": {
        "emotional_intelligence": 1-10,
        "appropriate_responses": 1-10,
        "conversation_flow": 1-10,
        "overall_quality": 1-10
    }
}
```"""

    # Add transcript context if available
    if transcript and len(transcript) > 0:
        transcript_text = "\n".join([
            f"{t.get('role', 'unknown')}: {t.get('text', '')[:100]}"
            for t in transcript[:10]  # First 10 turns for context
        ])
        prompt += f"""

For reference, here is the transcript of the conversation (use this to correlate emotional moments):
{transcript_text}"""

    # Add focus areas if specified
    if focus_areas:
        prompt += f"""

Please pay special attention to these areas:
{chr(10).join(f'- {area}' for area in focus_areas)}"""

    return prompt


async def analyze_call_audio_tonality(
    recording_url: str = None,
    api_key: str = None,
    agent_config: Dict[str, Any] = None,
    knowledge_base: str = None,
    transcript: List[Dict] = None,
    custom_guidelines: str = None,
    focus_areas: List[str] = None,
    auth_headers: Dict[str, str] = None,  # Auth headers for protected recording URLs
    audio_data: bytes = None,  # Pre-downloaded audio data (from Telnyx)
    audio_format: str = 'mp3'  # Format of pre-downloaded audio
) -> Dict[str, Any]:
    """
    Main function to analyze call audio for tonality.
    
    This is the primary entry point for audio-based tonality analysis.
    
    Args:
        recording_url: URL to the call recording (optional if audio_data provided)
        api_key: OpenAI API key
        agent_config: Agent configuration for context
        knowledge_base: KB content for context
        transcript: Conversation transcript for reference
        custom_guidelines: User-provided analysis guidelines
        focus_areas: Specific areas to analyze
        auth_headers: Optional auth headers for protected recording URLs
        audio_data: Pre-downloaded audio bytes (e.g., from Telnyx API)
        audio_format: Format of audio_data ('mp3', 'wav', etc.)
    
    Returns:
        Comprehensive tonality analysis results
    """
    
    # Build prompts with context
    system_prompt = build_tonality_system_prompt(
        agent_config=agent_config,
        knowledge_base=knowledge_base,
        custom_guidelines=custom_guidelines
    )
    
    analysis_prompt = build_analysis_prompt(
        transcript=transcript,
        focus_areas=focus_areas
    )
    
    # Create analyzer and run analysis
    analyzer = AudioTonalityAnalyzer(api_key=api_key)
    
    # Build context dict
    context = {}
    if agent_config:
        context['agent_name'] = agent_config.get('name', '')
        context['agent_type'] = agent_config.get('agent_type', '')
    
    # If we have pre-downloaded audio data, use it directly
    if audio_data:
        logger.info(f"Analyzing pre-downloaded audio ({len(audio_data)} bytes, format: {audio_format})")
        result = await analyzer.analyze_audio_segment(
            audio_data=audio_data,
            audio_format=audio_format,
            system_prompt=system_prompt,
            analysis_prompt=analysis_prompt,
            context=context if context else None
        )
    elif recording_url:
        # Download from URL
        result = await analyzer.analyze_recording_url(
            recording_url=recording_url,
            system_prompt=system_prompt,
            analysis_prompt=analysis_prompt,
            context=context if context else None,
            auth_headers=auth_headers
        )
    else:
        return {
            "success": False,
            "error": "No audio source provided. Either recording_url or audio_data is required."
        }
    
    return result


# Learning system integration
async def create_audio_tonality_learning_entry(
    qc_agent_id: str,
    analysis_result: Dict[str, Any],
    call_id: str,
    actual_outcome: str = None,
    db_instance = None
) -> Dict[str, Any]:
    """
    Create a learning entry from audio tonality analysis.
    
    This allows the learning system to track patterns between
    audio emotional markers and call outcomes.
    
    Args:
        qc_agent_id: The QC agent performing analysis
        analysis_result: Results from analyze_call_audio_tonality
        call_id: The call being analyzed
        actual_outcome: Known outcome (showed/no_show) if available
        db_instance: Database connection
    
    Returns:
        Learning log entry
    """
    
    if not analysis_result.get('success'):
        return {"success": False, "error": "Analysis failed, cannot create learning entry"}
    
    analysis = analysis_result.get('analysis', {})
    
    # Extract key metrics for learning
    overall = analysis.get('overall_assessment', {})
    quality = analysis.get('quality_scores', {})
    flags = analysis.get('flags', {})
    
    # Build prediction based on audio analysis
    prediction = {
        "booking_likelihood": "medium",  # Default
        "confidence": 0.5,
        "positive_signals": [],
        "risk_factors": []
    }
    
    # Analyze quality scores to determine prediction
    ei_score = quality.get('emotional_intelligence', 5)
    engagement = overall.get('engagement_level', 5)
    
    if ei_score >= 7 and engagement >= 7:
        prediction['booking_likelihood'] = "high"
        prediction['confidence'] = 0.7
        prediction['positive_signals'].append(f"High emotional intelligence ({ei_score}/10)")
        prediction['positive_signals'].append(f"Strong engagement ({engagement}/10)")
    elif ei_score <= 4 or engagement <= 4:
        prediction['booking_likelihood'] = "low"
        prediction['confidence'] = 0.6
        prediction['risk_factors'].append(f"Low emotional intelligence ({ei_score}/10)")
    
    # Check flags
    if flags.get('satisfaction_signals'):
        prediction['positive_signals'].append("Satisfaction signals detected in voice")
    if flags.get('rapport_established'):
        prediction['positive_signals'].append("Rapport established")
    if flags.get('frustration_detected'):
        prediction['risk_factors'].append("Frustration detected in voice")
    if flags.get('confusion_detected'):
        prediction['risk_factors'].append("Confusion detected")
    
    # Create learning log entry
    learning_entry = {
        "id": str(__import__('uuid').uuid4()),
        "qc_agent_id": qc_agent_id,
        "call_id": call_id,
        "analysis_type": "audio_tonality",
        "created_at": datetime.now(timezone.utc),
        "predictions": prediction,
        "scores": {
            "emotional_intelligence": ei_score,
            "engagement_level": engagement,
            "overall_quality": quality.get('overall_quality', 5),
            "appropriate_responses": quality.get('appropriate_responses', 5)
        },
        "audio_analysis": {
            "primary_emotion": overall.get('primary_emotion', 'neutral'),
            "emotion_intensity": overall.get('emotion_intensity', 5),
            "flags": flags
        },
        "actual_outcome": actual_outcome,  # Will be updated later if not known
        "prediction_accuracy": None  # Calculated when outcome is known
    }
    
    # Save to database if provided
    if db_instance:
        try:
            await db_instance.qc_analysis_logs.insert_one(learning_entry)
            logger.info(f"Created audio tonality learning entry: {learning_entry['id']}")
        except Exception as e:
            logger.error(f"Error saving learning entry: {str(e)}")
    
    return {
        "success": True,
        "learning_entry_id": learning_entry['id'],
        "predictions": prediction
    }
