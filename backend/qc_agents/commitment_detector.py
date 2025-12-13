import re
import json
from typing import Dict, Any, List
import logging
from .base_agent import BaseQCAgent

logger = logging.getLogger(__name__)

class CommitmentDetectorAgent(BaseQCAgent):
    """
    QC Agent 1: The Commitment Detector
    Analyzes linguistic patterns to predict genuine commitment and show-up likelihood
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Strong commitment patterns with weights
        self.strong_commitment_patterns = {
            r"\b(absolutely|definitely|certainly|for sure)\b": 10,
            r"\b(I will|I'll be there|I'm marking|I'm scheduling)\b": 9,
            r"\b(excited|looking forward|can't wait|perfect)\b": 8,
            r"\b(yes!)\b|\b(great!)\b|\b(excellent!)\b": 7,
        }
        
        # Weak commitment patterns with negative weights
        self.weak_commitment_patterns = {
            r"\b(I guess|I suppose|maybe|might|could|should)\b": -5,
            r"\b(try to|attempt to|see if)\b": -4,
            r"\b(if I'm free|if I can|if possible)\b": -6,
            r"\b(I think|probably|hopefully)\b": -3,
        }
        
        # Red flag patterns
        self.red_flag_patterns = {
            r"\b(have to think|call you back|not sure|pretty busy)\b": -10,
            r"\b(unpredictable|can't commit|don't know)\b": -8,
            r"\b(let me check)\b.*(?!.*\byes\b)": -7,
        }
    
    async def analyze(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze call for commitment signals using LLM
        
        Returns:
        {
            'commitment_analysis': {...},
            'show_up_probability': int,
            'risk_level': str,
            'action_items': [str]
        }
        """
        try:
            transcript = call_data.get('transcript', '')
            metadata = call_data.get('metadata', {})
            api_key = self.config.get('api_key')
            
            if not api_key:
                logger.warning("No API key provided, using pattern-based fallback")
                return self._fallback_pattern_analysis(transcript, metadata)
            
            # Use LLM to analyze commitment
            prompt = f"""Analyze this sales call transcript for customer commitment signals.

TRANSCRIPT:
{transcript}

CALL METADATA:
- Duration: {metadata.get('duration_seconds', 'unknown')} seconds

Analyze the customer's commitment level and predict show-up probability. Consider:
1. Linguistic commitment signals (definitive language vs hedging)
2. Behavioral progression through commitment stages
3. Resistance patterns and objection handling
4. Urgency and value recognition

Return a JSON object with:
{{
    "commitment_score": <0-100>,
    "show_up_probability": <0-100>,
    "risk_level": "<high|medium|low>",
    "key_phrases": [<list of commitment phrases found>],
    "red_flags": [<list of concerning phrases>],
    "recommendations": [<actionable recommendations>]
}}"""

            llm_response = await self.call_llm(prompt, api_key, temperature=0.3)
            
            # Parse JSON response
            import json
            result = json.loads(llm_response)
            
            return {
                'commitment_analysis': {
                    'commitment_score': result.get('commitment_score', 50),
                    'key_phrases': result.get('key_phrases', []),
                    'red_flags': result.get('red_flags', [])
                },
                'show_up_probability': result.get('show_up_probability', 50),
                'risk_level': result.get('risk_level', 'medium'),
                'key_factors': result.get('key_phrases', []),
                'action_items': result.get('recommendations', [])
            }
            
        except Exception as e:
            logger.error(f"Error in CommitmentDetector LLM analysis: {e}, falling back to patterns")
            return self._fallback_pattern_analysis(transcript if 'transcript' in locals() else '', metadata if 'metadata' in locals() else {})
    
    def _fallback_pattern_analysis(self, transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to pattern-based analysis when LLM unavailable"""
        try:
            # Component 1: Linguistic Commitment Analysis
            linguistic_score = self._analyze_linguistic_commitment(transcript)
            
            # Component 2: Behavioral Signal Extraction
            behavioral_analysis = self._extract_behavioral_signals(transcript)
            
            # Component 3: Resistance Pattern Detection
            resistance_analysis = self._detect_resistance_patterns(transcript)
            
            # Component 4: Urgency & Value Validation
            motivation_analysis = self._validate_urgency_and_value(transcript)
            
            # Component 5: Prediction Model
            prediction = self._predict_show_up(
                linguistic_score,
                behavioral_analysis,
                resistance_analysis,
                motivation_analysis,
                metadata
            )
            
            return {
                'commitment_analysis': {
                    'linguistic_score': linguistic_score,
                    'behavioral_progression': behavioral_analysis,
                    'objection_handling': resistance_analysis,
                    'motivation': motivation_analysis
                },
                'show_up_probability': prediction['show_up_probability'],
                'risk_level': prediction['risk_level'],
                'key_factors': prediction['key_factors'],
                'action_items': prediction['action_items']
            }
        except Exception as e:
            logger.error(f"Error in pattern fallback: {e}")
            return {
                'commitment_analysis': None,
                'show_up_probability': 50,
                'risk_level': 'medium',
                'key_factors': [f"Analysis error: {str(e)}"],
                'action_items': ["Manual review recommended"]
            }
    
    def _analyze_linguistic_commitment(self, transcript: str) -> int:
        """Analyze user responses for commitment signals"""
        user_responses = self.extract_user_responses(transcript)
        
        score = 50  # Start at neutral
        
        # Check strong patterns
        for pattern, weight in self.strong_commitment_patterns.items():
            matches = re.findall(pattern, user_responses, re.IGNORECASE)
            if matches:
                score += weight * len(matches)
        
        # Check weak patterns
        for pattern, weight in self.weak_commitment_patterns.items():
            matches = re.findall(pattern, user_responses, re.IGNORECASE)
            if matches:
                score += weight * len(matches)
        
        # Check red flags
        for pattern, weight in self.red_flag_patterns.items():
            matches = re.findall(pattern, user_responses, re.IGNORECASE)
            if matches:
                score += weight * len(matches)
        
        # Normalize to 0-100
        score = max(0, min(100, score))
        
        return score
    
    def _extract_behavioral_signals(self, transcript: str) -> Dict[str, Any]:
        """Track progression through commitment stages"""
        commitment_ladder = [
            {'stage': 'awareness', 'signals': ['tell me more', 'how does', 'what is'], 'value': 1},
            {'stage': 'interest', 'signals': ['that sounds', 'interesting', 'I like'], 'value': 2},
            {'stage': 'consideration', 'signals': ['how much', 'what are the', 'do you offer'], 'value': 3},
            {'stage': 'intent', 'signals': ['next step', 'how do I', 'when can'], 'value': 4},
            {'stage': 'commitment', 'signals': ['yes', 'book it', 'sign me up', 'I\'ll take'], 'value': 5}
        ]
        
        transcript_lower = transcript.lower()
        stages_reached = []
        
        for stage_data in commitment_ladder:
            for signal in stage_data['signals']:
                if signal.lower() in transcript_lower:
                    stages_reached.append(stage_data)
                    break
        
        if not stages_reached:
            return {
                'highest_stage_reached': 'none',
                'progression_score': 0,
                'stuck_at': 'awareness'
            }
        
        highest = max(stages_reached, key=lambda x: x['value'])
        progression_score = (highest['value'] / 5) * 100
        
        return {
            'highest_stage_reached': highest['stage'],
            'progression_score': progression_score,
            'stuck_at': None if highest['value'] >= 4 else highest['stage']
        }
    
    def _detect_resistance_patterns(self, transcript: str) -> Dict[str, Any]:
        """Detect objections and evaluate if they were handled"""
        resistance_patterns = {
            'timing': [r"not right now", r"maybe later", r"bad timing", r"too busy"],
            'skepticism': [r"sounds too good", r"not sure if", r"really work"],
            'price': [r"how much", r"cost", r"expensive", r"afford"],
            'authority': [r"need to ask", r"talk to my", r"check with"],
            'avoidance': [r"I'll think", r"call me back", r"send me info"]
        }
        
        objections_found = []
        
        for obj_type, patterns in resistance_patterns.items():
            for pattern in patterns:
                if re.search(pattern, transcript, re.IGNORECASE):
                    objections_found.append(obj_type)
                    break
        
        # Simple heuristic: if objection raised but conversation continued positively, consider it handled
        resolved = []
        unresolved = []
        
        for obj_type in objections_found:
            # Check if positive language appears after objection
            if re.search(r"\b(great|perfect|sounds good|I understand|makes sense)\b", transcript, re.IGNORECASE):
                resolved.append(obj_type)
            else:
                unresolved.append(obj_type)
        
        total_objections = len(objections_found)
        handling_score = (len(resolved) / total_objections * 100) if total_objections > 0 else 100
        
        return {
            'objections_raised': objections_found,
            'objections_resolved': resolved,
            'unresolved_objections': unresolved,
            'handling_score': handling_score,
            'critical_failure': 'avoidance' in unresolved
        }
    
    def _validate_urgency_and_value(self, transcript: str) -> Dict[str, Any]:
        """Check if value and urgency were communicated"""
        value_keywords = ['benefit', 'help you', 'result', 'achieve', 'improve', 'solution']
        urgency_keywords = ['limited', 'deadline', 'soon', 'now', 'today', 'urgent', 'spots left']
        
        value_score = sum(1 for keyword in value_keywords if keyword in transcript.lower())
        urgency_score = sum(1 for keyword in urgency_keywords if keyword in transcript.lower())
        
        # Normalize to 0-10 scale
        value_score = min(10, value_score)
        urgency_score = min(10, urgency_score)
        
        # Calculate motivation score
        effort_score = 3  # Assume moderate effort (can be enhanced)
        if effort_score == 0:
            motivation_score = 0
        else:
            motivation_score = ((value_score * urgency_score) / effort_score) * 10
            motivation_score = min(100, motivation_score)
        
        return {
            'value_score': value_score,
            'urgency_score': urgency_score,
            'effort_score': effort_score,
            'overall_score': motivation_score
        }
    
    def _predict_show_up(self, 
                        commitment_score: int,
                        behavioral_analysis: Dict,
                        resistance_analysis: Dict,
                        motivation_analysis: Dict,
                        metadata: Dict) -> Dict[str, Any]:
        """Combine all signals to predict show-up probability"""
        
        # Weighted combination
        weights = {
            'commitment': 0.35,
            'progression': 0.20,
            'objection_handling': 0.25,
            'motivation': 0.20
        }
        
        probability = (
            commitment_score * weights['commitment'] +
            behavioral_analysis['progression_score'] * weights['progression'] +
            resistance_analysis['handling_score'] * weights['objection_handling'] +
            motivation_analysis['overall_score'] * weights['motivation']
        )
        
        # Adjust based on metadata
        duration = metadata.get('duration_seconds', 0)
        if 120 <= duration <= 600:  # 2-10 minutes optimal
            probability += 5
        elif duration < 60:
            probability -= 10
        
        probability = max(0, min(100, probability))
        
        # Determine risk level
        if probability >= 75:
            risk_level = 'low'
        elif probability >= 50:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        # Identify key factors
        key_factors = []
        if commitment_score >= 70:
            key_factors.append("Strong commitment language detected")
        if behavioral_analysis['highest_stage_reached'] == 'commitment':
            key_factors.append("Reached commitment stage")
        if resistance_analysis['handling_score'] >= 80:
            key_factors.append("Objections handled well")
        if motivation_analysis['overall_score'] >= 60:
            key_factors.append("Strong motivation created")
        
        # Generate action items
        action_items = []
        if risk_level == 'high':
            action_items.append("URGENT: Call within 1 hour to re-confirm")
            action_items.append("Send personalized SMS with clear value reminder")
        elif risk_level == 'medium':
            action_items.append("Send confirmation email within 15 minutes")
            action_items.append("Schedule reminder SMS 24 hours before")
        else:
            action_items.append("Send standard confirmation")
        
        return {
            'show_up_probability': round(probability),
            'risk_level': risk_level,
            'key_factors': key_factors,
            'action_items': action_items
        }
