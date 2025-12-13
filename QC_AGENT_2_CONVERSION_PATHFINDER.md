# QC Agent 2: The Conversion Pathfinder
## "The Funnel Detective + Sales Coach"

---

## Core Purpose
**Track progression through the sales funnel and identify exactly where and why conversations derail**

## The Insight
Every successful appointment booking follows a path. Failed bookings diverge from that path at specific moments. This agent maps the optimal path and identifies deviation points in real-time.

It's like GPS for sales conversations - it knows the destination, tracks the current route, and alerts when you've taken a wrong turn.

---

## Problem Statements (Multiple Angles)

### The Diagnostic Angle
"At what exact point did this conversation go off track?"

### The Pattern Recognition Angle
"What do all failed bookings have in common in their conversation structure?"

### The Optimization Angle
"Which conversation paths have the highest conversion rates?"

### The Training Angle
"What mistakes do low-performing agents consistently make?"

---

## Architecture Overview

```
POST-CALL ANALYSIS
      |
      ↓
┌──────────────────────────────────────────┐
│   CONVERSION PATHFINDER PIPELINE          │
├──────────────────────────────────────────┤
│                                           │
│  Stage 1: Conversation Segmentation       │
│  → Break transcript into stages          │
│  → Tag each segment                      │
│                                           │
│  Stage 2: Funnel Position Tracker         │
│  → Map to ideal conversion funnel       │
│  → Identify current position            │
│                                           │
│  Stage 3: Deviation Detector              │
│  → Compare to optimal path              │
│  → Identify divergence points           │
│                                           │
│  Stage 4: Sales Framework Evaluator       │
│  → Grade against BANT/SPIN/Challenger   │
│  → Identify missed opportunities        │
│                                           │
│  Stage 5: Root Cause Analyzer             │
│  → Diagnose failure reason              │
│  → Generate improvement suggestions     │
│                                           │
└──────────────────────────────────────────┘
      |
      ↓
[Conversion Diagnostic Report + Optimization Suggestions]
```

---

## The Ideal Conversion Funnel (Baseline)

### The Universal Sales Conversation Structure

Based on analysis of thousands of successful sales calls, here's the optimal path:

```
┌────────────────────────────────────────────────┐
│ STAGE 1: HOOK (First 30 seconds)                  │
│ Goal: Capture attention & establish relevance     │
│ Success Criteria:                                 │
│   - User acknowledges understanding               │
│   - User expresses interest in continuing         │
│   - No immediate objection/hang-up                │
│ Duration: 20-40 seconds                           │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ STAGE 2: QUALIFICATION (1-2 minutes)              │
│ Goal: Determine if this is a qualified lead       │
│ Success Criteria:                                 │
│   - BANT criteria explored (Budget, Authority,    │
│     Need, Timeline)                               │
│   - User's situation understood                   │
│   - Fit confirmed                                 │
│ Duration: 60-120 seconds                          │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ STAGE 3: VALUE PRESENTATION (1-2 minutes)         │
│ Goal: Communicate personalized value              │
│ Success Criteria:                                 │
│   - Benefits tied to their specific situation     │
│   - User acknowledges value                       │
│   - Interest level increases                      │
│ Duration: 60-120 seconds                          │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ STAGE 4: OBJECTION HANDLING (30-90 seconds)       │
│ Goal: Address concerns and build trust            │
│ Success Criteria:                                 │
│   - Objections surfaced and addressed             │
│   - User sentiment improves after handling        │
│   - No unresolved blockers remain                 │
│ Duration: 30-90 seconds                           │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ STAGE 5: CLOSING (30-60 seconds)                  │
│ Goal: Secure commitment to appointment            │
│ Success Criteria:                                 │
│   - Direct ask for appointment made               │
│   - User agrees verbally                          │
│   - Specific date/time discussed                  │
│ Duration: 30-60 seconds                           │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│ STAGE 6: CONFIRMATION (20-30 seconds)             │
│ Goal: Lock in details and reduce no-show risk     │
│ Success Criteria:                                 │
│   - Details repeated back to user                 │
│   - User confirms understanding                   │
│   - Next steps clarified                          │
│   - Urgency/excitement reinforced                 │
│ Duration: 20-40 seconds                           │
└────────────────────────────────────────────────┘
                      ↓
              ✅ APPOINTMENT BOOKED
```

### Optimal Call Duration: 3-6 minutes
- Too short (< 2 min): Didn't qualify or build trust
- Too long (> 10 min): Lost focus, user disengaged

---

## Component 1: Conversation Segmentation

### Automatic Stage Detection

Using NLP + LLM, automatically segment the transcript:

```python
from typing import List, Dict, Tuple
import re

class ConversationSegmenter:
    def __init__(self):
        # Stage detection patterns
        self.stage_patterns = {
            'hook': {
                'keywords': ['calling about', 'reaching out', 'wanted to discuss', 'this is'],
                'agent_signals': ['introduction', 'reason for call'],
                'duration_range': (10, 60)
            },
            'qualification': {
                'keywords': ['currently', 'looking for', 'what kind of', 'tell me about'],
                'question_patterns': [r'are you\b', r'do you\b', r'have you\b', r'what.{0,20}\?'],
                'duration_range': (30, 180)
            },
            'value_presentation': {
                'keywords': ['help you', 'benefit', 'solution', 'what we do', 'how it works'],
                'agent_signals': ['explanation', 'value proposition'],
                'duration_range': (40, 180)
            },
            'objection_handling': {
                'keywords': ['but', 'however', 'concern', 'worried', 'not sure'],
                'user_resistance_patterns': [r'I don\'t', r'too expensive', r'not ready'],
                'duration_range': (20, 120)
            },
            'closing': {
                'keywords': ['schedule', 'book', 'set up', 'when', 'available'],
                'direct_ask_patterns': [r'would you like to', r'shall we', r'can we schedule'],
                'duration_range': (20, 90)
            },
            'confirmation': {
                'keywords': ['confirm', 'see you then', 'looking forward', 'reminder'],
                'detail_patterns': [r'\d{1,2}:\d{2}', r'(monday|tuesday|wednesday|thursday|friday)'],
                'duration_range': (15, 60)
            }
        }
    
    def segment(self, transcript: str, timestamps: List[Tuple[float, str]]) -> List[Dict]:
        """
        Breaks transcript into stages
        
        Returns:
        [
            {
                'stage': 'hook',
                'start_time': 0.0,
                'end_time': 32.5,
                'duration': 32.5,
                'transcript_snippet': '...',
                'confidence': 0.85
            },
            ...
        ]
        """
        segments = []
        
        # Use LLM for intelligent segmentation
        segments = self._llm_based_segmentation(transcript, timestamps)
        
        # Validate segments
        segments = self._validate_and_adjust_segments(segments)
        
        return segments
    
    def _llm_based_segmentation(self, transcript: str, timestamps: List) -> List[Dict]:
        """
        Use LLM to intelligently identify conversation stages
        """
        prompt = f"""
        Analyze this sales call transcript and identify the conversation stages.
        
        Stages to identify:
        1. Hook (opening, introduction)
        2. Qualification (understanding customer needs)
        3. Value Presentation (explaining benefits)
        4. Objection Handling (addressing concerns)
        5. Closing (asking for appointment)
        6. Confirmation (confirming details)
        
        For each stage found, provide:
        - Stage name
        - Start timestamp (approximate based on context)
        - End timestamp
        - Key phrases that indicate this stage
        - Confidence (0-1)
        
        Transcript:
        {transcript}
        
        Return as JSON array.
        """
        
        # Call LLM (GPT-4o or similar)
        # In production, this would use the actual LLM client
        # For now, return structured format
        
        return []
```

---

## Component 2: Funnel Position Tracker

### Real-Time Progress Monitoring

```python
class FunnelPositionTracker:
    def __init__(self):
        self.ideal_funnel = [
            {'stage': 'hook', 'required': True, 'typical_duration': 30},
            {'stage': 'qualification', 'required': True, 'typical_duration': 90},
            {'stage': 'value_presentation', 'required': True, 'typical_duration': 90},
            {'stage': 'objection_handling', 'required': False, 'typical_duration': 60},
            {'stage': 'closing', 'required': True, 'typical_duration': 45},
            {'stage': 'confirmation', 'required': True, 'typical_duration': 30}
        ]
    
    def analyze_progression(self, segments: List[Dict]) -> Dict:
        """
        Compare actual conversation to ideal funnel
        
        Returns:
        {
            'funnel_completion': 83,  # % of required stages completed
            'stage_progression': [
                {'stage': 'hook', 'completed': True, 'duration': 28, 'quality': 'good'},
                {'stage': 'qualification', 'completed': True, 'duration': 115, 'quality': 'too_long'},
                {'stage': 'value_presentation', 'completed': False, 'quality': 'missing'},
                ...
            ],
            'deviations': [
                {'type': 'skipped_stage', 'stage': 'value_presentation', 'impact': 'critical'},
                {'type': 'duration_anomaly', 'stage': 'qualification', 'actual': 115, 'expected': 90}
            ],
            'diagnosis': 'Rushed to close without presenting value'
        }
        """
        
        stage_progression = []
        deviations = []
        
        # Check which required stages were completed
        completed_stages = {s['stage'] for s in segments}
        
        for ideal_stage in self.ideal_funnel:
            stage_name = ideal_stage['stage']
            
            if stage_name in completed_stages:
                # Find the actual segment
                actual_segment = next(s for s in segments if s['stage'] == stage_name)
                duration = actual_segment['duration']
                
                # Evaluate quality
                quality = self._evaluate_stage_quality(
                    duration, 
                    ideal_stage['typical_duration'],
                    actual_segment
                )
                
                stage_progression.append({
                    'stage': stage_name,
                    'completed': True,
                    'duration': duration,
                    'quality': quality
                })
                
                # Check for duration anomalies
                if quality in ['too_short', 'too_long']:
                    deviations.append({
                        'type': 'duration_anomaly',
                        'stage': stage_name,
                        'actual': duration,
                        'expected': ideal_stage['typical_duration'],
                        'impact': 'moderate' if not ideal_stage['required'] else 'high'
                    })
            else:
                # Stage was skipped
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
            'funnel_completion': funnel_completion,
            'stage_progression': stage_progression,
            'deviations': deviations,
            'diagnosis': diagnosis
        }
    
    def _evaluate_stage_quality(self, actual_duration: float, 
                                 expected_duration: float,
                                 segment: Dict) -> str:
        """
        Evaluate if stage duration is appropriate
        """
        ratio = actual_duration / expected_duration
        
        if ratio < 0.5:
            return 'too_short'
        elif ratio > 2.0:
            return 'too_long'
        elif 0.7 <= ratio <= 1.3:
            return 'optimal'
        else:
            return 'acceptable'
    
    def _diagnose_conversation(self, progression: List[Dict], deviations: List[Dict]) -> str:
        """
        Generate human-readable diagnosis
        """
        critical_issues = [d for d in deviations if d['impact'] == 'critical']
        
        if not critical_issues:
            return "Conversation followed optimal path"
        
        # Analyze patterns
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
```

---

## Component 3: Deviation Detector

### The "Wrong Turn" Alert System

```python
class DeviationDetector:
    """
    Identifies exact moments where conversation went off track
    """
    
    def detect_critical_moments(self, segments: List[Dict], 
                                 transcript: str) -> List[Dict]:
        """
        Find the specific moments that led to failure
        
        Returns:
        [
            {
                'timestamp': 145.3,
                'type': 'objection_ignored',
                'description': 'User expressed price concern, agent continued script',
                'severity': 'high',
                'should_have_done': 'Acknowledged concern and addressed it immediately',
                'transcript_snippet': '...'
            },
            ...
        ]
        """
        
        critical_moments = []
        
        # Pattern 1: Objection Ignored
        critical_moments.extend(self._detect_ignored_objections(transcript, segments))
        
        # Pattern 2: Premature Close Attempt
        critical_moments.extend(self._detect_premature_close(segments))
        
        # Pattern 3: Value Not Personalized
        critical_moments.extend(self._detect_generic_value_prop(segments))
        
        # Pattern 4: Failed to Create Urgency
        critical_moments.extend(self._detect_missing_urgency(segments))
        
        # Pattern 5: Talking Over User
        critical_moments.extend(self._detect_interruptions(transcript))
        
        return sorted(critical_moments, key=lambda x: x['severity_score'], reverse=True)
    
    def _detect_ignored_objections(self, transcript: str, segments: List[Dict]) -> List[Dict]:
        """
        Find instances where user raised objection but agent ignored it
        """
        moments = []
        
        # Common objection patterns
        objection_patterns = [
            r"(too expensive|can't afford|budget)",
            r"(not sure|don't know|need to think)",
            r"(busy|no time|hectic)",
            r"(tried before|didn't work|skeptical)"
        ]
        
        lines = transcript.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('User:') or line.startswith('Caller:'):
                # Check if this is an objection
                for pattern in objection_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Check if next agent response addresses it
                        if i + 1 < len(lines):
                            next_line = lines[i + 1]
                            if not self._is_acknowledgment(next_line):
                                moments.append({
                                    'timestamp': self._estimate_timestamp(i, lines),
                                    'type': 'objection_ignored',
                                    'description': f'User objection not acknowledged: "{line}"',
                                    'severity': 'high',
                                    'severity_score': 8,
                                    'should_have_done': 'Acknowledge concern: "I understand that..."',
                                    'transcript_snippet': f"{line}\n{next_line if i+1 < len(lines) else ''}"
                                })
        
        return moments
    
    def _is_acknowledgment(self, agent_response: str) -> bool:
        """
        Check if agent acknowledged the objection
        """
        acknowledgment_phrases = [
            'i understand',
            'i hear you',
            'that makes sense',
            'good question',
            'let me address that'
        ]
        
        response_lower = agent_response.lower()
        return any(phrase in response_lower for phrase in acknowledgment_phrases)
```

---

## Component 4: Sales Framework Evaluator

### Multi-Framework Scoring

#### BANT Framework (Budget, Authority, Need, Timeline)

```python
class BANTEvaluator:
    def evaluate(self, transcript: str) -> Dict:
        """
        Score call against BANT qualification framework
        
        Returns:
        {
            'budget': {'addressed': True, 'score': 7},
            'authority': {'addressed': False, 'score': 0},
            'need': {'addressed': True, 'score': 9},
            'timeline': {'addressed': True, 'score': 6},
            'overall_score': 55,
            'qualification_level': 'moderate'
        }
        """
        
        scores = {}
        
        # Budget
        budget_patterns = [r'budget', r'afford', r'cost', r'price', r'investment']
        scores['budget'] = {
            'addressed': self._check_patterns(transcript, budget_patterns),
            'score': self._score_budget_exploration(transcript) if self._check_patterns(transcript, budget_patterns) else 0
        }
        
        # Authority
        authority_patterns = [r'decision', r'in charge', r'your call', r'need approval']
        scores['authority'] = {
            'addressed': self._check_patterns(transcript, authority_patterns),
            'score': self._score_authority_exploration(transcript) if self._check_patterns(transcript, authority_patterns) else 0
        }
        
        # Need
        need_patterns = [r'need', r'problem', r'challenge', r'goal', r'looking for']
        scores['need'] = {
            'addressed': self._check_patterns(transcript, need_patterns),
            'score': self._score_need_exploration(transcript) if self._check_patterns(transcript, need_patterns) else 0
        }
        
        # Timeline
        timeline_patterns = [r'when', r'timeline', r'how soon', r'deadline', r'urgent']
        scores['timeline'] = {
            'addressed': self._check_patterns(transcript, timeline_patterns),
            'score': self._score_timeline_exploration(transcript) if self._check_patterns(transcript, timeline_patterns) else 0
        }
        
        # Calculate overall score
        addressed_count = sum(1 for v in scores.values() if v['addressed'])
        total_score = sum(v['score'] for v in scores.values())
        overall_score = (total_score / 4)  # Average of all 4 components
        
        # Qualification level
        if overall_score >= 7 and addressed_count == 4:
            qualification_level = 'highly_qualified'
        elif overall_score >= 5 and addressed_count >= 3:
            qualification_level = 'qualified'
        elif addressed_count >= 2:
            qualification_level = 'moderately_qualified'
        else:
            qualification_level = 'poorly_qualified'
        
        return {
            **scores,
            'overall_score': overall_score * 10,  # Scale to 0-100
            'qualification_level': qualification_level,
            'addressed_count': addressed_count
        }
```

#### SPIN Selling Framework (Situation, Problem, Implication, Need-Payoff)

```python
class SPINEvaluator:
    def evaluate(self, transcript: str) -> Dict:
        """
        Score call against SPIN selling methodology
        """
        
        # Situation Questions: Understanding current state
        situation_score = self._count_situation_questions(transcript)
        
        # Problem Questions: Identifying pain points
        problem_score = self._count_problem_questions(transcript)
        
        # Implication Questions: Exploring consequences
        implication_score = self._count_implication_questions(transcript)
        
        # Need-Payoff Questions: Envisioning solutions
        need_payoff_score = self._count_need_payoff_questions(transcript)
        
        total_score = (situation_score + problem_score + 
                      implication_score + need_payoff_score) / 4
        
        return {
            'situation': situation_score,
            'problem': problem_score,
            'implication': implication_score,
            'need_payoff': need_payoff_score,
            'overall_score': total_score * 10,
            'methodology_adherence': 'strong' if total_score >= 7 else 'weak'
        }
```

---

## Component 5: Root Cause Analyzer

### Diagnostic Decision Tree

```python
class RootCauseAnalyzer:
    def analyze(self, 
                funnel_analysis: Dict,
                deviation_moments: List[Dict],
                bant_score: Dict,
                commitment_score: int) -> Dict:
        """
        Diagnose why the call failed (or succeeded)
        
        Returns comprehensive root cause analysis
        """
        
        # Decision tree for diagnosis
        if funnel_analysis['funnel_completion'] < 50:
            # Major structural failure
            return self._diagnose_structural_failure(funnel_analysis)
        
        elif bant_score['qualification_level'] in ['poorly_qualified', 'moderately_qualified']:
            # Qualification failure
            return self._diagnose_qualification_failure(bant_score)
        
        elif len([d for d in deviation_moments if d['severity'] == 'high']) > 2:
            # Execution failure
            return self._diagnose_execution_failure(deviation_moments)
        
        elif commitment_score < 40:
            # Closing failure
            return self._diagnose_closing_failure(commitment_score, deviation_moments)
        
        else:
            # Call was good
            return self._diagnose_success()
    
    def _diagnose_structural_failure(self, funnel_analysis: Dict) -> Dict:
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
                "Add checklist for required conversation stages"
            ],
            'fix_priority': 'immediate'
        }
    
    def _diagnose_qualification_failure(self, bant_score: Dict) -> Dict:
        unaddressed = [
            key for key, val in bant_score.items() 
            if isinstance(val, dict) and not val.get('addressed')
        ]
        
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
    
    def _diagnose_execution_failure(self, deviation_moments: List[Dict]) -> Dict:
        critical_failures = [d for d in deviation_moments if d['severity'] == 'high']
        
        return {
            'root_cause': 'execution_failure',
            'diagnosis': f"{len(critical_failures)} critical errors during call",
            'impact': 'high',
            'specific_failures': critical_failures[:3],  # Top 3
            'recommendations': [
                f"Address: {cf['should_have_done']}" 
                for cf in critical_failures[:3]
            ],
            'fix_priority': 'high'
        }
    
    def _diagnose_closing_failure(self, commitment_score: int, 
                                   deviation_moments: List[Dict]) -> Dict:
        return {
            'root_cause': 'closing_failure',
            'diagnosis': f"Low commitment (score: {commitment_score}). User not ready to commit.",
            'impact': 'moderate',
            'recommendations': [
                "Strengthen urgency creation",
                "Ensure value is crystal clear before asking",
                "Use trial closes to gauge readiness",
                "Address all objections before final ask"
            ],
            'fix_priority': 'moderate'
        }
```

---

## Output: The Conversion Diagnostic Report

```json
{
  "call_id": "c_12345",
  "analysis_timestamp": "2025-01-20T14:35:00Z",
  
  "funnel_analysis": {
    "completion_percentage": 67,
    "stages_completed": ["hook", "qualification", "closing"],
    "stages_skipped": ["value_presentation", "objection_handling", "confirmation"],
    "diagnosis": "CRITICAL: Value never presented. User doesn't know what they're getting."
  },
  
  "critical_moments": [
    {
      "timestamp": 87.3,
      "type": "skipped_value_presentation",
      "description": "Agent jumped from qualification directly to close",
      "severity": "critical",
      "should_have_done": "Present personalized value before asking for commitment"
    },
    {
      "timestamp": 112.8,
      "type": "objection_ignored",
      "description": "User said 'I'm not sure' but agent continued script",
      "severity": "high"
    }
  ],
  
  "framework_scores": {
    "bant": {
      "overall_score": 45,
      "qualification_level": "moderately_qualified",
      "budget": {"addressed": false},
      "authority": {"addressed": true, "score": 6},
      "need": {"addressed": true, "score": 7},
      "timeline": {"addressed": false}
    },
    "spin": {
      "overall_score": 32,
      "methodology_adherence": "weak"
    }
  },
  
  "root_cause": {
    "primary": "structural_failure",
    "diagnosis": "Call missing critical stages: value_presentation, confirmation",
    "impact": "critical",
    "fix_priority": "immediate"
  },
  
  "improvement_recommendations": [
    "CRITICAL: Always present value before asking for commitment",
    "Add value presentation stage to script (60-90 seconds)",
    "Include confirmation stage at end to reduce no-shows",
    "Train agent to recognize and address objections in real-time"
  ],
  
  "benchmark_comparison": {
    "vs_top_10_percent": {
      "funnel_completion": "33% below average",
      "call_duration": "45% shorter than optimal",
      "commitment_score": "28 points lower"
    }
  }
}
```

---

## Integration with System

```python
# In backend/server.py

from conversion_pathfinder import ConversionPathfinder

pathfinder = ConversionPathfinder()

@app.post("/api/webhooks/call_ended")
async def handle_call_ended(payload: dict):
    call_id = payload['call_id']
    transcript = payload['transcript']
    
    # Run funnel analysis
    diagnostic_report = pathfinder.analyze_full_call(
        transcript=transcript,
        metadata=payload.get('call_analysis', {})
    )
    
    # Store results
    await db.conversion_analytics.insert_one({
        'call_id': call_id,
        'timestamp': datetime.now(timezone.utc),
        'diagnostic_report': diagnostic_report
    })
    
    # Alert on critical failures
    if diagnostic_report['root_cause']['fix_priority'] == 'immediate':
        await send_alert_to_manager(call_id, diagnostic_report)
    
    return {"status": "analyzed"}
```

---

## Novel Insights from Creativity Framework

### 1. GPS Analogy
"Sales conversations are like driving - you have a destination, and there are optimal routes. This agent is the GPS that warns 'Recalculating' when you take a wrong turn."

### 2. Medical Differential Diagnosis
Borrowed from medicine:
- **Symptom**: No appointment booked
- **Possible Diagnoses**: 7 different root causes
- **Tests**: Analyze conversation structure, language patterns, timing
- **Treatment**: Specific fix for each diagnosis

### 3. Sports "Game Film" Analysis
Like coaches reviewing game footage:
- Identify the "play" that lost the game
- What should have been done differently?
- Create practice drills for weak areas

### 4. The "3-Second Rule" from Basketball
Applied to objections:
- Must acknowledge objection within 3 seconds (next response)
- Failing to do so = technical foul = lost trust

---

## Success Metrics

### Diagnostic Accuracy
- **Root Cause Accuracy**: % of diagnosed issues that managers agree with
- **Recommendation Quality**: % of suggestions that improve outcomes when implemented

### Business Impact
- **Conversion Rate Improvement**: Target +20% through systematic optimization
- **Agent Training Efficiency**: Reduce training time with specific feedback
- **Script Optimization ROI**: Measure improvement from script changes

---

**Next**: See `QC_AGENT_3_EXCELLENCE_REPLICATOR.md` for continuous learning.
