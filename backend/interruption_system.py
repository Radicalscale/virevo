"""
AI Interruption System - Rambler Handler

This module provides an intelligent interruption system that:
1. Monitors user responses for rambling or off-topic behavior
2. Decides when to interrupt to steer conversation back on track
3. Provides contextual or default interruption phrases

Two frameworks:
- Default Framework: Pre-defined interjection phrases
- Contextual Leverage Dynamic Framework: Incorporates what user is saying
"""

import logging
import asyncio
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# MODELS
# ============================================================================

class InterruptionConfig(BaseModel):
    """Configuration for the interruption system"""
    enabled: bool = False
    framework: str = "default"  # "default" or "contextual"
    
    # Thresholds
    word_count_threshold: int = 100  # Interrupt if user speaks > N words
    duration_threshold_seconds: int = 30  # Interrupt if user speaks > N seconds
    off_topic_confidence_threshold: float = 0.7  # 0-1 scale
    
    # Default phrases for default framework
    default_phrases: List[str] = [
        "I hear you. Let me address that specifically...",
        "That's a great point. To make sure I help you best...",
        "I appreciate you sharing that. Let me ask...",
        "Understood. Just to keep us on track...",
        "I want to make sure we cover everything. Let me..."
    ]
    
    # Contextual framework settings
    use_llm_for_context: bool = True
    llm_provider: str = "grok"
    llm_model: str = "grok-3"


class InterruptionDecision(BaseModel):
    """Decision output from the interruption system"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    should_interrupt: bool = False
    reason: str = ""  # Why we're interrupting
    interruption_phrase: str = ""  # What to say
    confidence: float = 0.0  # How confident we are
    detected_issues: List[str] = []  # ["rambling", "off_topic", "emotional"]
    context_leverage: str = ""  # How we're using their words
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RamblerDetectionResult(BaseModel):
    """Result of rambler detection analysis"""
    is_rambling: bool = False
    word_count: int = 0
    duration_seconds: float = 0.0
    is_off_topic: bool = False
    off_topic_confidence: float = 0.0
    topics_detected: List[str] = []
    emotional_state: str = "neutral"  # neutral, frustrated, confused, excited
    key_phrases: List[str] = []  # Phrases to potentially reference


# ============================================================================
# INTERRUPTION SYSTEM
# ============================================================================

class InterruptionSystem:
    """
    AI-powered interruption system for handling ramblers and off-topic speakers.
    """
    
    def __init__(self, config: InterruptionConfig = None):
        self.config = config or InterruptionConfig()
        self._api_key = None
    
    def set_api_key(self, api_key: str):
        """Set API key for LLM calls"""
        self._api_key = api_key
    
    async def analyze_user_response(
        self,
        user_text: str,
        conversation_context: List[Dict[str, str]],
        node_goal: str = "",
        duration_seconds: float = 0.0
    ) -> RamblerDetectionResult:
        """
        Analyze user response for rambling or off-topic behavior.
        
        Args:
            user_text: The user's current response
            conversation_context: Previous turns in conversation
            node_goal: What the current node is trying to achieve
            duration_seconds: How long the user has been speaking
        """
        result = RamblerDetectionResult()
        
        # Basic metrics
        words = user_text.split()
        result.word_count = len(words)
        result.duration_seconds = duration_seconds
        
        # Check word count threshold
        if result.word_count > self.config.word_count_threshold:
            result.is_rambling = True
        
        # Check duration threshold
        if duration_seconds > self.config.duration_threshold_seconds:
            result.is_rambling = True
        
        # Use LLM for deeper analysis if enabled
        if self.config.use_llm_for_context and self._api_key:
            try:
                llm_analysis = await self._analyze_with_llm(
                    user_text, 
                    conversation_context, 
                    node_goal
                )
                
                result.is_off_topic = llm_analysis.get('is_off_topic', False)
                result.off_topic_confidence = llm_analysis.get('off_topic_confidence', 0.0)
                result.topics_detected = llm_analysis.get('topics', [])
                result.emotional_state = llm_analysis.get('emotional_state', 'neutral')
                result.key_phrases = llm_analysis.get('key_phrases', [])
                
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")
        
        return result
    
    async def _analyze_with_llm(
        self,
        user_text: str,
        conversation_context: List[Dict[str, str]],
        node_goal: str
    ) -> Dict[str, Any]:
        """Use LLM to analyze user response"""
        
        context_str = "\n".join([
            f"{turn.get('role', 'unknown')}: {turn.get('content', '')}"
            for turn in conversation_context[-5:]  # Last 5 turns
        ])
        
        prompt = f"""Analyze this user response in a sales/service call context.

**Conversation Goal:** {node_goal or "Move conversation toward desired outcome"}

**Recent Context:**
{context_str}

**Current User Response:**
{user_text}

**Analyze for:**
1. Is the user off-topic from the conversation goal? (0-1 confidence)
2. What topics are they discussing?
3. What is their emotional state? (neutral, frustrated, confused, excited, upset)
4. Extract 2-3 key phrases from their speech that could be referenced

Return JSON:
{{
  "is_off_topic": true/false,
  "off_topic_confidence": 0.0-1.0,
  "topics": ["topic1", "topic2"],
  "emotional_state": "neutral|frustrated|confused|excited|upset",
  "key_phrases": ["phrase1", "phrase2"]
}}"""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.config.llm_model,
                        "messages": [
                            {"role": "system", "content": "You are an expert conversation analyst. Return only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result['choices'][0]['message']['content']
                    
                    # Parse JSON
                    if '```json' in text:
                        text = text.split('```json')[1].split('```')[0]
                    elif '```' in text:
                        text = text.split('```')[1].split('```')[0]
                    
                    return json.loads(text.strip())
                    
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
        
        return {}
    
    async def decide_interruption(
        self,
        detection_result: RamblerDetectionResult,
        conversation_context: List[Dict[str, str]],
        node_goal: str = ""
    ) -> InterruptionDecision:
        """
        Decide whether to interrupt and generate the interruption phrase.
        """
        decision = InterruptionDecision()
        
        # Determine if we should interrupt
        should_interrupt = False
        reasons = []
        
        if detection_result.is_rambling:
            should_interrupt = True
            reasons.append("User is rambling (exceeded word/time threshold)")
            decision.detected_issues.append("rambling")
        
        if detection_result.is_off_topic and detection_result.off_topic_confidence >= self.config.off_topic_confidence_threshold:
            should_interrupt = True
            reasons.append(f"User is off-topic (confidence: {detection_result.off_topic_confidence:.0%})")
            decision.detected_issues.append("off_topic")
        
        if detection_result.emotional_state in ['frustrated', 'upset']:
            should_interrupt = True
            reasons.append(f"User appears {detection_result.emotional_state}")
            decision.detected_issues.append("emotional")
        
        decision.should_interrupt = should_interrupt
        decision.reason = "; ".join(reasons)
        
        if not should_interrupt:
            return decision
        
        # Generate interruption phrase
        if self.config.framework == "default":
            # Use default phrases
            import random
            decision.interruption_phrase = random.choice(self.config.default_phrases)
            decision.confidence = 0.8
            
        elif self.config.framework == "contextual":
            # Generate contextual phrase using LLM
            phrase = await self._generate_contextual_phrase(
                detection_result,
                conversation_context,
                node_goal
            )
            decision.interruption_phrase = phrase
            decision.confidence = 0.9
            
            # Store how we leveraged their context
            if detection_result.key_phrases:
                decision.context_leverage = f"Referencing: {', '.join(detection_result.key_phrases)}"
        
        return decision
    
    async def _generate_contextual_phrase(
        self,
        detection_result: RamblerDetectionResult,
        conversation_context: List[Dict[str, str]],
        node_goal: str
    ) -> str:
        """Generate a contextual interruption phrase using LLM"""
        
        if not self._api_key:
            # Fallback to default
            return self.config.default_phrases[0]
        
        key_phrases_str = ", ".join(detection_result.key_phrases) if detection_result.key_phrases else "their concerns"
        emotional_state = detection_result.emotional_state
        
        prompt = f"""Generate a polite, professional interruption phrase for a sales/service call.

**Situation:**
- User has been rambling or gone off-topic
- Their emotional state: {emotional_state}
- Key things they mentioned: {key_phrases_str}
- Conversation goal: {node_goal or "Move toward desired outcome"}

**Requirements:**
1. Acknowledge what they said (reference their key phrases)
2. Be warm but redirect the conversation
3. Bridge back to the conversation goal
4. Keep it under 25 words
5. Don't be dismissive

Return ONLY the phrase, no quotes or explanation."""
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.config.llm_model,
                        "messages": [
                            {"role": "system", "content": "You are an expert at redirecting conversations politely. Output only the interruption phrase."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    phrase = result['choices'][0]['message']['content'].strip()
                    # Clean up any quotes
                    phrase = phrase.strip('"\'')
                    return phrase
                    
        except Exception as e:
            logger.error(f"Contextual phrase generation failed: {e}")
        
        # Fallback
        return f"I hear you about {key_phrases_str}. Let me address that..."


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_interruption_system = None

def get_interruption_system(config: InterruptionConfig = None) -> InterruptionSystem:
    """Get or create the interruption system instance"""
    global _interruption_system
    
    if _interruption_system is None or config is not None:
        _interruption_system = InterruptionSystem(config)
    
    return _interruption_system


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def check_for_interruption(
    user_text: str,
    conversation_context: List[Dict[str, str]],
    node_goal: str = "",
    duration_seconds: float = 0.0,
    config: InterruptionConfig = None,
    api_key: str = None
) -> InterruptionDecision:
    """
    Convenience function to check if we should interrupt the user.
    
    Args:
        user_text: The user's current response
        conversation_context: Previous turns in conversation
        node_goal: What the current node is trying to achieve
        duration_seconds: How long the user has been speaking
        config: Optional custom configuration
        api_key: API key for LLM calls
    
    Returns:
        InterruptionDecision with should_interrupt and phrase
    """
    system = get_interruption_system(config)
    
    if api_key:
        system.set_api_key(api_key)
    
    # Analyze the response
    detection = await system.analyze_user_response(
        user_text,
        conversation_context,
        node_goal,
        duration_seconds
    )
    
    # Decide whether to interrupt
    decision = await system.decide_interruption(
        detection,
        conversation_context,
        node_goal
    )
    
    return decision
