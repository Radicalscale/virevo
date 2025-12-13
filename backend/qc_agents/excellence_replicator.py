from typing import Dict, Any, List
import logging
from .base_agent import BaseQCAgent

logger = logging.getLogger(__name__)

class ExcellenceReplicatorAgent(BaseQCAgent):
    """
    QC Agent 3: The Excellence Replicator
    Learns from successful calls and provides optimization recommendations
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Excellence patterns (simplified version)
        self.excellence_indicators = {
            'personalization': ['you', 'your situation', 'for you', 'specifically'],
            'enthusiasm': ['great', 'excellent', 'perfect', 'wonderful', '!'],
            'clarity': ['specifically', 'exactly', 'clearly', 'simple'],
            'urgency': ['today', 'now', 'limited', 'deadline', 'spots'],
            'value_focus': ['benefit', 'help', 'achieve', 'result', 'improve']
        }
    
    async def analyze(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze call for excellence patterns using LLM
        
        Returns:
        {
            'excellence_score': int,
            'pattern_analysis': {...},
            'recommendations': [...],
            'comparison_to_ideal': {...}
        }
        """
        try:
            transcript = call_data.get('transcript', '')
            metadata = call_data.get('metadata', {})
            api_key = self.config.get('api_key')
            
            if not api_key:
                logger.warning("No API key provided, using pattern-based fallback")
                return self._fallback_pattern_analysis(transcript, metadata)
            
            # Use LLM to analyze call excellence
            prompt = f"""Analyze this sales call for excellence patterns and identify what makes it successful or unsuccessful.

TRANSCRIPT:
{transcript}

CALL METADATA:
- Duration: {metadata.get('duration_seconds', 'unknown')} seconds

Analyze the call across these dimensions:
1. RAPPORT BUILDING - Connection, trust, personalization
2. VALUE COMMUNICATION - Clear benefits, solution articulation
3. OBJECTION HANDLING - Quality of responses to concerns
4. CALL STRUCTURE - Flow, organization, pacing
5. PROFESSIONALISM - Tone, language, conduct

Return a JSON object with:
{{
    "excellence_score": <0-100>,
    "success_patterns": [<list of 2-3 things that worked well>],
    "failure_patterns": [<list of 2-3 areas that need improvement>],
    "recommendations": [<specific actions to replicate excellence>]
}}"""

            llm_response = await self.call_llm(prompt, api_key, temperature=0.3)
            
            # Parse JSON response
            import json
            result = json.loads(llm_response)
            
            return {
                'excellence_score': result.get('excellence_score', 50),
                'pattern_analysis': {
                    'success_patterns': result.get('success_patterns', []),
                    'failure_patterns': result.get('failure_patterns', [])
                },
                'recommendations': result.get('recommendations', []),
                'comparison_to_ideal': {
                    'score_vs_benchmark': result.get('excellence_score', 50) - 70,
                    'strengths': result.get('success_patterns', []),
                    'improvements': result.get('failure_patterns', [])
                }
            }
            
        except Exception as e:
            logger.error(f"Error in ExcellenceReplicator analysis: {e}")
            return {
                'excellence_score': 50,
                'pattern_analysis': {},
                'recommendations': [f'Analysis error: {str(e)}'],
                'comparison_to_ideal': {}
            }
    
    
    def _fallback_pattern_analysis(self, transcript: str, metadata: Dict) -> Dict[str, Any]:
        """Fallback to pattern-based analysis when no API key is available"""
        # Analyze excellence patterns
        pattern_analysis = self._analyze_excellence_patterns(transcript)
        
        # Calculate excellence score
        excellence_score = self._calculate_excellence_score(
            pattern_analysis,
            metadata
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            pattern_analysis,
            excellence_score
        )
        
        return {
            'excellence_score': excellence_score,
            'pattern_analysis': pattern_analysis,
            'recommendations': recommendations,
            'comparison_to_ideal': {
                'score_vs_benchmark': excellence_score - 70,  # 70 is target
                'strengths': self._identify_strengths(pattern_analysis),
                'improvements': self._identify_improvements(pattern_analysis)
            }
        }
    def _analyze_excellence_patterns(self, transcript: str) -> Dict[str, Any]:
        """Identify excellence patterns in the conversation"""
        transcript_lower = transcript.lower()
        pattern_scores = {}
        
        for pattern_name, keywords in self.excellence_indicators.items():
            count = sum(1 for keyword in keywords if keyword in transcript_lower)
            # Normalize to 0-10 scale
            score = min(10, count)
            pattern_scores[pattern_name] = {
                'count': count,
                'score': score,
                'present': count > 0
            }
        
        return pattern_scores
    
    def _calculate_excellence_score(self,
                                   pattern_analysis: Dict,
                                   metadata: Dict) -> int:
        """Calculate overall excellence score"""
        
        # Weight different patterns
        weights = {
            'personalization': 0.25,
            'enthusiasm': 0.15,
            'clarity': 0.20,
            'urgency': 0.20,
            'value_focus': 0.20
        }
        
        score = 0
        for pattern_name, weight in weights.items():
            pattern_data = pattern_analysis.get(pattern_name, {})
            pattern_score = pattern_data.get('score', 0)
            score += (pattern_score / 10) * weight * 100
        
        # Adjust for call duration (optimal: 3-6 minutes)
        duration = metadata.get('duration_seconds', 0) / 60  # Convert to minutes
        if 3 <= duration <= 6:
            score += 10
        elif duration < 2:
            score -= 10
        elif duration > 10:
            score -= 5
        
        score = max(0, min(100, score))
        return round(score)
    
    def _generate_recommendations(self,
                                 pattern_analysis: Dict,
                                 excellence_score: int) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Check each pattern
        for pattern_name, data in pattern_analysis.items():
            if data['score'] < 3:  # Low score
                if pattern_name == 'personalization':
                    recommendations.append(
                        "Increase personalization: Reference caller's specific situation more often"
                    )
                elif pattern_name == 'enthusiasm':
                    recommendations.append(
                        "Show more enthusiasm: Use positive language and exclamation points"
                    )
                elif pattern_name == 'clarity':
                    recommendations.append(
                        "Improve clarity: Use words like 'specifically', 'exactly', 'clearly'"
                    )
                elif pattern_name == 'urgency':
                    recommendations.append(
                        "Create urgency: Mention limited availability, deadlines, or time-sensitive benefits"
                    )
                elif pattern_name == 'value_focus':
                    recommendations.append(
                        "Emphasize value: Focus on benefits, results, and improvements"
                    )
        
        if excellence_score >= 80:
            recommendations.append(
                "Excellent call! Analyze for replicable patterns in future training"
            )
        elif excellence_score < 50:
            recommendations.append(
                "Multiple improvement areas detected. Consider comprehensive script review"
            )
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _identify_strengths(self, pattern_analysis: Dict) -> List[str]:
        """Identify what was done well"""
        strengths = []
        
        for pattern_name, data in pattern_analysis.items():
            if data['score'] >= 7:
                strengths.append(f"Strong {pattern_name}")
        
        return strengths
    
    def _identify_improvements(self, pattern_analysis: Dict) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        
        for pattern_name, data in pattern_analysis.items():
            if data['score'] < 5:
                improvements.append(f"Improve {pattern_name}")
        
        return improvements
