import re
import json
from typing import Dict, Any, List
import logging
from .base_agent import BaseQCAgent

logger = logging.getLogger(__name__)

class ConversionPathfinderAgent(BaseQCAgent):
    """
    QC Agent 2: The Conversion Pathfinder
    Tracks progression through the sales funnel and identifies where calls derail
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Define ideal funnel stages
        self.ideal_funnel = [
            {'stage': 'hook', 'required': True, 'typical_duration': 30},
            {'stage': 'qualification', 'required': True, 'typical_duration': 90},
            {'stage': 'value_presentation', 'required': True, 'typical_duration': 90},
            {'stage': 'objection_handling', 'required': False, 'typical_duration': 60},
            {'stage': 'closing', 'required': True, 'typical_duration': 45},
            {'stage': 'confirmation', 'required': True, 'typical_duration': 30}
        ]
        
        # Stage detection patterns
        self.stage_patterns = {
            'hook': {
                'keywords': ['calling about', 'reaching out', 'wanted to discuss', 'this is'],
                'duration_range': (10, 60)
            },
            'qualification': {
                'keywords': ['currently', 'looking for', 'what kind of', 'tell me about', 'are you', 'do you'],
                'duration_range': (30, 180)
            },
            'value_presentation': {
                'keywords': ['help you', 'benefit', 'solution', 'what we do', 'how it works', 'this will'],
                'duration_range': (40, 180)
            },
            'objection_handling': {
                'keywords': ['but', 'however', 'concern', 'worried', 'not sure', 'I understand'],
                'duration_range': (20, 120)
            },
            'closing': {
                'keywords': ['schedule', 'book', 'set up', 'when', 'available', 'would you like'],
                'duration_range': (20, 90)
            },
            'confirmation': {
                'keywords': ['confirm', 'see you then', 'looking forward', 'reminder', 'calendar'],
                'duration_range': (15, 60)
            }
        }
    
    async def analyze(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze call for funnel progression using LLM
        
        Returns:
        {
            'funnel_analysis': {...},
            'critical_moments': [...],
            'framework_scores': {...},
            'root_cause': {...},
            'recommendations': [...]
        }
        """
        try:
            transcript = call_data.get('transcript', '')
            metadata = call_data.get('metadata', {})
            api_key = self.config.get('api_key')
            
            if not api_key:
                logger.warning("No API key provided, using pattern-based fallback")
                return self._fallback_pattern_analysis(transcript, metadata)
            
            # Use LLM to analyze sales funnel progression
            prompt = f"""Analyze this sales call transcript for funnel progression and identify where the conversation succeeds or fails.

TRANSCRIPT:
{transcript}

CALL METADATA:
- Duration: {metadata.get('duration_seconds', 'unknown')} seconds

Analyze the sales funnel progression through these stages:
1. HOOK - Initial engagement and attention capture
2. QUALIFICATION - Understanding customer needs and fit
3. VALUE PROPOSITION - Presenting solution and benefits
4. OBJECTION HANDLING - Addressing concerns and resistance
5. CLOSING - Securing commitment and next steps

For each stage, determine if it was:
- Reached (fully completed)
- Partially reached (attempted but incomplete)
- Missed (skipped entirely)

Return a JSON object with:
{{
    "conversion_score": <0-100>,
    "stages_reached": [<list of stages fully completed>],
    "stages_missed": [<list of skipped stages>],
    "bottleneck_stage": "<stage where conversation got stuck or null>",
    "critical_moments": [<list of 2-3 pivotal moments in the call>],
    "recommendations": [<specific actionable improvements>]
}}"""

            llm_response = await self.call_llm(prompt, api_key, temperature=0.3)
            
            # Parse JSON response
            import json
            result = json.loads(llm_response)
            
            return {
                'funnel_analysis': {
                    'conversion_score': result.get('conversion_score', 50),
                    'stages_reached': result.get('stages_reached', []),
                    'stages_missed': result.get('stages_missed', []),
                    'bottleneck_stage': result.get('bottleneck_stage')
                },
                'critical_moments': result.get('critical_moments', []),
                'framework_scores': {'overall': result.get('conversion_score', 50)},
                'root_cause': {'bottleneck': result.get('bottleneck_stage')},
                'recommendations': result.get('recommendations', [])
            }
            
        except Exception as e:
            logger.error(f"Error in ConversionPathfinder LLM analysis: {e}, falling back to patterns")
            return self._fallback_pattern_analysis(transcript if 'transcript' in locals() else '', metadata if 'metadata' in locals() else {})
    
    def _fallback_pattern_analysis(self, transcript: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to pattern-based analysis when LLM unavailable"""
        try:
            # Component 1: Conversation Segmentation
            segments = self._segment_conversation(transcript, metadata)
            
            # Component 2: Funnel Position Tracking
            funnel_analysis = self._analyze_funnel_progression(segments)
            
            # Component 3: Deviation Detection
            critical_moments = self._detect_critical_moments(transcript, segments)
            
            # Component 4: Sales Framework Evaluation
            framework_scores = self._evaluate_sales_frameworks(transcript)
            
            # Component 5: Root Cause Analysis
            root_cause = self._analyze_root_cause(
                funnel_analysis,
                critical_moments,
                framework_scores
            )
            
            return {
                'funnel_analysis': funnel_analysis,
                'critical_moments': critical_moments[:5],  # Top 5
                'framework_scores': framework_scores,
                'root_cause': root_cause,
                'recommendations': root_cause.get('recommendations', [])
            }
        except Exception as e:
            logger.error(f"Error in pattern fallback: {e}")
            return {
                'funnel_analysis': None,
                'critical_moments': [],
                'framework_scores': {},
                'root_cause': {'diagnosis': f'Analysis error: {str(e)}'},
                'recommendations': ['Manual review recommended']
            }
    
    def _segment_conversation(self, transcript: str, metadata: Dict) -> List[Dict]:
        """Break transcript into conversation stages"""
        segments = []
        transcript_lower = transcript.lower()
        
        for stage_name, stage_config in self.stage_patterns.items():
            # Check if stage keywords are present
            found = False
            for keyword in stage_config['keywords']:
                if keyword.lower() in transcript_lower:
                    found = True
                    break
            
            if found:
                segments.append({
                    'stage': stage_name,
                    'detected': True,
                    'confidence': 0.8  # Simple heuristic
                })
            else:
                segments.append({
                    'stage': stage_name,
                    'detected': False,
                    'confidence': 0
                })
        
        return segments
    
    def _analyze_funnel_progression(self, segments: List[Dict]) -> Dict[str, Any]:
        """Compare actual conversation to ideal funnel"""
        stage_progression = []
        deviations = []
        
        completed_stages = [s for s in segments if s['detected']]
        
        for ideal_stage in self.ideal_funnel:
            stage_name = ideal_stage['stage']
            
            # Check if stage was completed
            completed = any(s['stage'] == stage_name and s['detected'] for s in segments)
            
            if completed:
                stage_progression.append({
                    'stage': stage_name,
                    'completed': True,
                    'quality': 'good'
                })
            else:
                stage_progression.append({
                    'stage': stage_name,
                    'completed': False,
                    'quality': 'missing'
                })
                
                if ideal_stage['required']:
                    deviations.append({
                        'type': 'skipped_stage',
                        'stage': stage_name,
                        'impact': 'critical'
                    })
        
        # Calculate completion percentage
        required_stages = [s for s in self.ideal_funnel if s['required']]
        completed_required = sum(
            1 for s in stage_progression 
            if s['completed'] and s['stage'] in [rs['stage'] for rs in required_stages]
        )
        funnel_completion = (completed_required / len(required_stages)) * 100
        
        # Diagnose the conversation
        diagnosis = self._diagnose_conversation(stage_progression, deviations)
        
        return {
            'funnel_completion': round(funnel_completion),
            'stage_progression': stage_progression,
            'deviations': deviations,
            'diagnosis': diagnosis
        }
    
    def _diagnose_conversation(self, progression: List[Dict], deviations: List[Dict]) -> str:
        """Generate human-readable diagnosis"""
        critical_issues = [d for d in deviations if d['impact'] == 'critical']
        
        if not critical_issues:
            return "Conversation followed optimal path"
        
        missing_stages = [d['stage'] for d in critical_issues if d['type'] == 'skipped_stage']
        
        if 'value_presentation' in missing_stages:
            return "CRITICAL: Value never presented. User doesn't know what they're getting."
        if 'qualification' in missing_stages:
            return "CRITICAL: Lead not qualified. May be poor fit."
        if 'closing' in missing_stages:
            return "CRITICAL: Never asked for the appointment."
        if 'confirmation' in missing_stages:
            return "WARNING: Details not confirmed. High no-show risk."
        
        return "Multiple deviations detected. Review call for improvement opportunities."
    
    def _detect_critical_moments(self, transcript: str, segments: List[Dict]) -> List[Dict]:
        """Find specific moments where conversation went off track"""
        critical_moments = []
        
        # Pattern 1: Objection ignored
        objection_patterns = [
            r"(too expensive|can't afford|budget)",
            r"(not sure|don't know|need to think)",
            r"(busy|no time|hectic)"
        ]
        
        for pattern in objection_patterns:
            matches = list(re.finditer(pattern, transcript, re.IGNORECASE))
            if matches:
                critical_moments.append({
                    'type': 'objection_detected',
                    'description': f'User raised objection: {matches[0].group()}',
                    'severity': 'high',
                    'should_have_done': 'Acknowledge and address the concern'
                })
        
        # Pattern 2: Missing value presentation
        if not any(s['stage'] == 'value_presentation' and s['detected'] for s in segments):
            critical_moments.append({
                'type': 'missing_stage',
                'description': 'Value presentation stage not detected',
                'severity': 'critical',
                'should_have_done': 'Present clear benefits before asking for commitment'
            })
        
        # Pattern 3: No closing attempt
        if not any(s['stage'] == 'closing' and s['detected'] for s in segments):
            critical_moments.append({
                'type': 'missing_stage',
                'description': 'Closing stage not detected',
                'severity': 'critical',
                'should_have_done': 'Make direct ask for appointment'
            })
        
        return critical_moments
    
    def _evaluate_sales_frameworks(self, transcript: str) -> Dict[str, Any]:
        """Score call against BANT and other frameworks"""
        
        # BANT Framework
        bant_score = self._evaluate_bant(transcript)
        
        # Simple scoring
        return {
            'bant': bant_score,
            'overall_score': bant_score['overall_score']
        }
    
    def _evaluate_bant(self, transcript: str) -> Dict[str, Any]:
        """Evaluate BANT (Budget, Authority, Need, Timeline) qualification"""
        transcript_lower = transcript.lower()
        
        scores = {}
        
        # Budget
        budget_patterns = ['budget', 'afford', 'cost', 'price', 'investment']
        scores['budget'] = {
            'addressed': any(p in transcript_lower for p in budget_patterns),
            'score': 7 if any(p in transcript_lower for p in budget_patterns) else 0
        }
        
        # Authority
        authority_patterns = ['decision', 'in charge', 'your call', 'need approval']
        scores['authority'] = {
            'addressed': any(p in transcript_lower for p in authority_patterns),
            'score': 6 if any(p in transcript_lower for p in authority_patterns) else 0
        }
        
        # Need
        need_patterns = ['need', 'problem', 'challenge', 'goal', 'looking for']
        scores['need'] = {
            'addressed': any(p in transcript_lower for p in need_patterns),
            'score': 9 if any(p in transcript_lower for p in need_patterns) else 0
        }
        
        # Timeline
        timeline_patterns = ['when', 'timeline', 'how soon', 'deadline', 'urgent']
        scores['timeline'] = {
            'addressed': any(p in transcript_lower for p in timeline_patterns),
            'score': 6 if any(p in transcript_lower for p in timeline_patterns) else 0
        }
        
        # Calculate overall
        addressed_count = sum(1 for v in scores.values() if v['addressed'])
        total_score = sum(v['score'] for v in scores.values())
        overall_score = (total_score / 4) * 10  # Scale to 0-100
        
        # Qualification level
        if overall_score >= 70 and addressed_count == 4:
            qualification_level = 'highly_qualified'
        elif overall_score >= 50 and addressed_count >= 3:
            qualification_level = 'qualified'
        elif addressed_count >= 2:
            qualification_level = 'moderately_qualified'
        else:
            qualification_level = 'poorly_qualified'
        
        return {
            **scores,
            'overall_score': round(overall_score),
            'qualification_level': qualification_level,
            'addressed_count': addressed_count
        }
    
    def _analyze_root_cause(self,
                           funnel_analysis: Dict,
                           critical_moments: List[Dict],
                           framework_scores: Dict) -> Dict[str, Any]:
        """Diagnose why the call failed or succeeded"""
        
        if funnel_analysis['funnel_completion'] < 50:
            # Major structural failure
            missing_stages = [
                s['stage'] for s in funnel_analysis['stage_progression'] 
                if not s['completed']
            ]
            
            return {
                'root_cause': 'structural_failure',
                'diagnosis': f"Call missing critical stages: {', '.join(missing_stages)}",
                'impact': 'critical',
                'recommendations': [
                    "Review script to ensure all stages are covered",
                    "Train agent on complete sales process",
                    f"Add missing stages: {', '.join(missing_stages)}"
                ],
                'fix_priority': 'immediate'
            }
        
        elif framework_scores.get('bant', {}).get('qualification_level') in ['poorly_qualified', 'moderately_qualified']:
            # Qualification failure
            bant = framework_scores['bant']
            unaddressed = [key for key, val in bant.items() 
                          if isinstance(val, dict) and not val.get('addressed')]
            
            return {
                'root_cause': 'qualification_failure',
                'diagnosis': f"Lead not properly qualified. Missing: {', '.join(unaddressed)}",
                'impact': 'high',
                'recommendations': [
                    "Implement BANT qualification checklist",
                    "Don't proceed to close without qualification",
                    f"Specifically ask about: {', '.join(unaddressed)}"
                ],
                'fix_priority': 'high'
            }
        
        elif len([m for m in critical_moments if m.get('severity') == 'critical']) > 0:
            # Execution failure
            critical_failures = [m for m in critical_moments if m.get('severity') in ['critical', 'high']]
            
            return {
                'root_cause': 'execution_failure',
                'diagnosis': f"{len(critical_failures)} critical errors during call",
                'impact': 'high',
                'specific_failures': critical_failures[:3],
                'recommendations': [
                    f"Fix: {cf.get('should_have_done', 'Review call')}" 
                    for cf in critical_failures[:3]
                ],
                'fix_priority': 'high'
            }
        
        else:
            # Call was good
            return {
                'root_cause': 'success',
                'diagnosis': "Call executed well across all dimensions",
                'impact': 'positive',
                'recommendations': [
                    "Continue using this approach",
                    "Analyze for replicable patterns"
                ],
                'fix_priority': 'none'
            }
