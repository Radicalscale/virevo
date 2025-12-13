"""
QC Learning Service - The Learning Brains

This module implements the multi-agent learning architecture:
1. Reflection Brain - Analyzes outcomes, identifies patterns
2. Training Brain - Synthesizes lessons into playbooks

Inspired by the combat AI learning loop:
Experience → Reflection → Instruction → Application
"""

import logging
import json
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
import uuid

from qc_learning_models import (
    QCAnalysisLog, QCPlaybook, PlaybookContent, LearnedPattern,
    LearningSession, LearningSessionType, LearningConfig, LearningMode,
    AnalysisPrediction, OutcomeType, PatternType, BookingQuality,
    get_default_playbook_content, get_default_brain_prompts, BrainPrompts,
    DEFAULT_TONALITY_PLAYBOOK, DEFAULT_LANGUAGE_PATTERN_PLAYBOOK
)

logger = logging.getLogger(__name__)

# Database reference (set by router)
db = None

def set_db(database):
    global db
    db = database


# ============================================================================
# REFLECTION BRAIN
# ============================================================================

class ReflectionBrain:
    """
    Analyzes QC analysis logs against actual outcomes.
    Identifies patterns, calculates accuracy, discovers what works/doesn't.
    """
    
    def __init__(self, api_key: str, llm_provider: str = "grok", llm_model: str = "grok-3", 
                 custom_prompts: Dict[str, Any] = None, agent_type: str = "language_pattern"):
        self.api_key = api_key
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.agent_type = agent_type
        
        # Load default prompts and merge with custom
        defaults = get_default_brain_prompts(agent_type)
        self.system_prompt = (custom_prompts or {}).get('reflection_system_prompt', defaults.reflection_system_prompt)
        self.prefix = (custom_prompts or {}).get('reflection_prefix', defaults.reflection_prefix)
        self.suffix = (custom_prompts or {}).get('reflection_suffix', defaults.reflection_suffix)
        self.custom_instructions = (custom_prompts or {}).get('custom_instructions', defaults.custom_instructions)
    
    async def reflect(
        self,
        qc_agent_id: str,
        agent_type: str,
        analysis_logs: List[dict],
        existing_patterns: List[dict] = None
    ) -> Dict[str, Any]:
        """
        Reflect on a batch of analysis logs with known outcomes.
        Returns identified patterns and accuracy metrics.
        """
        if not analysis_logs:
            return {"patterns": [], "accuracy": 0, "insights": []}
        
        # Separate by outcome
        showed_logs = [l for l in analysis_logs if l.get('actual_outcome') == 'showed']
        no_show_logs = [l for l in analysis_logs if l.get('actual_outcome') == 'no_show']
        
        # Calculate prediction accuracy
        accuracy_data = self._calculate_accuracy(analysis_logs)
        
        # Build reflection prompt
        prompt = self._build_reflection_prompt(
            agent_type=agent_type,
            showed_logs=showed_logs,
            no_show_logs=no_show_logs,
            existing_patterns=existing_patterns or [],
            accuracy_data=accuracy_data
        )
        
        # Call LLM for pattern analysis
        try:
            reflection_result = await self._call_llm(prompt)
            
            # Parse patterns from LLM response
            patterns = self._parse_patterns(reflection_result, qc_agent_id, agent_type)
            
            return {
                "patterns": patterns,
                "accuracy": accuracy_data,
                "insights": reflection_result.get("insights", []),
                "raw_response": reflection_result
            }
        except Exception as e:
            logger.error(f"Reflection brain error: {str(e)}")
            return {
                "patterns": [],
                "accuracy": accuracy_data,
                "insights": [],
                "error": str(e)
            }
    
    def _calculate_accuracy(self, logs: List[dict]) -> Dict[str, Any]:
        """Calculate prediction accuracy metrics"""
        total = len(logs)
        if total == 0:
            return {"overall": 0, "showed": 0, "no_show": 0, "total": 0}
        
        correct_predictions = 0
        showed_correct = 0
        showed_total = 0
        no_show_correct = 0
        no_show_total = 0
        
        for log in logs:
            outcome = log.get('actual_outcome')
            predictions = log.get('predictions', {})
            show_likelihood = predictions.get('show_likelihood', 0.5)
            
            if outcome == 'showed':
                showed_total += 1
                if show_likelihood >= 0.5:
                    correct_predictions += 1
                    showed_correct += 1
            elif outcome == 'no_show':
                no_show_total += 1
                if show_likelihood < 0.5:
                    correct_predictions += 1
                    no_show_correct += 1
        
        return {
            "overall": correct_predictions / total if total > 0 else 0,
            "showed": showed_correct / showed_total if showed_total > 0 else 0,
            "no_show": no_show_correct / no_show_total if no_show_total > 0 else 0,
            "total": total,
            "showed_count": showed_total,
            "no_show_count": no_show_total
        }
    
    def _build_reflection_prompt(
        self,
        agent_type: str,
        showed_logs: List[dict],
        no_show_logs: List[dict],
        existing_patterns: List[dict],
        accuracy_data: Dict
    ) -> str:
        """Build the reflection prompt for the LLM"""
        
        agent_focus = "voice tonality and emotional delivery" if agent_type == "tonality" else "conversation tactics and language patterns"
        
        # Format showed examples
        showed_examples = []
        for log in showed_logs[:10]:  # Limit to 10 examples
            predictions = log.get('predictions', {})
            showed_examples.append({
                "risk_factors": predictions.get('risk_factors', []),
                "positive_signals": predictions.get('positive_signals', []),
                "show_likelihood_predicted": predictions.get('show_likelihood', 0.5),
                "scores": log.get('scores', {}),
                "campaign_id": log.get('campaign_id'),
            })
        
        # Format no-show examples
        no_show_examples = []
        for log in no_show_logs[:10]:
            predictions = log.get('predictions', {})
            no_show_examples.append({
                "risk_factors": predictions.get('risk_factors', []),
                "positive_signals": predictions.get('positive_signals', []),
                "show_likelihood_predicted": predictions.get('show_likelihood', 0.5),
                "scores": log.get('scores', {}),
                "campaign_id": log.get('campaign_id'),
            })
        
        # Build the dynamic content
        dynamic_content = f"""You are a QC Analysis Reflection Brain specializing in {agent_focus}.

Your task: Analyze these QC analysis results against their actual outcomes to identify patterns.

## CURRENT ACCURACY
- Overall: {accuracy_data['overall']:.1%}
- Showed predictions: {accuracy_data['showed']:.1%} ({accuracy_data['showed_count']} samples)
- No-show predictions: {accuracy_data['no_show']:.1%} ({accuracy_data['no_show_count']} samples)

## APPOINTMENTS THAT SHOWED (Success Cases)
{json.dumps(showed_examples, indent=2)}

## APPOINTMENTS THAT NO-SHOWED (Failure Cases)
{json.dumps(no_show_examples, indent=2)}

## EXISTING PATTERNS (for reference)
{json.dumps([{{'signal': p.get('signal'), 'impact': p.get('impact_percentage')}} for p in existing_patterns[:20]], indent=2)}

## YOUR ANALYSIS TASK

1. **VICTORY PATTERNS**: What signals appear consistently in SHOWED appointments?
   - Look for: common positive_signals, high scores, risk factors that were present but didn't matter

2. **DEFEAT PATTERNS**: What signals appear consistently in NO-SHOW appointments?
   - Look for: common risk_factors, low scores, positive signals that were misleading

3. **PREDICTION ERRORS**: Where did our predictions go wrong?
   - High confidence showed → no-show (false positives)
   - Low confidence showed → showed (false negatives)

4. **CAMPAIGN PATTERNS**: Any patterns specific to certain campaigns?

5. **TRANSFERABLE INSIGHTS**: What works across ALL contexts?

Return JSON:
{{
  "victory_patterns": [
    {{"signal": "description of pattern", "impact": 0.15, "confidence": 0.8, "sample_size": 5}}
  ],
  "defeat_patterns": [
    {{"signal": "description of pattern", "impact": 0.20, "confidence": 0.7, "sample_size": 4}}
  ],
  "campaign_patterns": {{
    "campaign_id": [{{"signal": "pattern", "impact": 0.10}}]
  }},
  "missed_signals": ["signals we should look for but didn't"],
  "misleading_signals": ["signals that don't actually predict outcomes"],
  "insights": ["key learnings from this analysis"],
  "calibration_adjustments": {{
    "adjust_up_when": ["conditions"],
    "adjust_down_when": ["conditions"]
  }}
}}"""
        
        # Add custom prefix and suffix
        prompt = f"{self.prefix}{dynamic_content}{self.suffix}"
        
        # Add custom instructions if present
        if self.custom_instructions:
            prompt += f"\n\n## ADDITIONAL INSTRUCTIONS\n{self.custom_instructions}"
        
        return prompt
    
    def _parse_patterns(
        self,
        llm_response: Dict,
        qc_agent_id: str,
        agent_type: str
    ) -> List[LearnedPattern]:
        """Parse LLM response into LearnedPattern objects"""
        patterns = []
        
        # Victory patterns
        for p in llm_response.get('victory_patterns', []):
            patterns.append(LearnedPattern(
                qc_agent_id=qc_agent_id,
                user_id="",  # Set by caller
                pattern_type=PatternType.VICTORY,
                agent_type=agent_type,
                signal=p.get('signal', ''),
                description=p.get('signal', ''),
                correlation=p.get('confidence', 0.5),
                confidence=p.get('confidence', 0.5),
                sample_size=p.get('sample_size', 0),
                outcome_impact="showed",
                impact_percentage=p.get('impact', 0)
            ))
        
        # Defeat patterns
        for p in llm_response.get('defeat_patterns', []):
            patterns.append(LearnedPattern(
                qc_agent_id=qc_agent_id,
                user_id="",
                pattern_type=PatternType.DEFEAT,
                agent_type=agent_type,
                signal=p.get('signal', ''),
                description=p.get('signal', ''),
                correlation=-p.get('confidence', 0.5),
                confidence=p.get('confidence', 0.5),
                sample_size=p.get('sample_size', 0),
                outcome_impact="no_show",
                impact_percentage=p.get('impact', 0)
            ))
        
        # Campaign patterns
        for campaign_id, camp_patterns in llm_response.get('campaign_patterns', {}).items():
            for p in camp_patterns:
                patterns.append(LearnedPattern(
                    qc_agent_id=qc_agent_id,
                    user_id="",
                    pattern_type=PatternType.CAMPAIGN_SPECIFIC,
                    agent_type=agent_type,
                    scope=f"campaign:{campaign_id}",
                    campaign_id=campaign_id,
                    signal=p.get('signal', ''),
                    description=p.get('signal', ''),
                    confidence=0.6,
                    impact_percentage=p.get('impact', 0),
                    outcome_impact="showed" if p.get('impact', 0) > 0 else "no_show"
                ))
        
        return patterns
    
    async def _call_llm(self, prompt: str) -> Dict:
        """Call the LLM and parse JSON response"""
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                if self.llm_provider == "grok":
                    response = await client.post(
                        "https://api.x.ai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.llm_model,
                            "messages": [
                                {"role": "system", "content": self.system_prompt},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.3
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Parse JSON from response
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0]
                        elif '```' in content:
                            content = content.split('```')[1].split('```')[0]
                        
                        return json.loads(content.strip())
                    else:
                        logger.error(f"LLM API error: {response.status_code}")
                        return {}
        except Exception as e:
            logger.error(f"LLM call error: {str(e)}")
            return {}


# ============================================================================
# TRAINING BRAIN
# ============================================================================

class TrainingBrain:
    """
    Synthesizes learned patterns into an actionable playbook.
    Like a coach turning raw analysis into a game plan.
    """
    
    def __init__(self, api_key: str, llm_provider: str = "grok", llm_model: str = "grok-3",
                 custom_prompts: Dict[str, Any] = None, agent_type: str = "language_pattern"):
        self.api_key = api_key
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.agent_type = agent_type
        
        # Load default prompts and merge with custom
        defaults = get_default_brain_prompts(agent_type)
        self.system_prompt = (custom_prompts or {}).get('training_system_prompt', defaults.training_system_prompt)
        self.prefix = (custom_prompts or {}).get('training_prefix', defaults.training_prefix)
        self.suffix = (custom_prompts or {}).get('training_suffix', defaults.training_suffix)
        self.custom_instructions = (custom_prompts or {}).get('custom_instructions', defaults.custom_instructions)
        self.api_key = api_key
        self.llm_provider = llm_provider
        self.llm_model = llm_model
    
    async def generate_playbook(
        self,
        qc_agent_id: str,
        agent_type: str,
        patterns: List[dict],
        current_playbook: Optional[QCPlaybook] = None,
        accuracy_data: Dict = None,
        recent_analyses: List[dict] = None
    ) -> QCPlaybook:
        """
        Generate a new playbook version from learned patterns.
        """
        # Start with default template
        default_content = get_default_playbook_content(agent_type)
        
        # Build training prompt
        prompt = self._build_training_prompt(
            agent_type=agent_type,
            patterns=patterns,
            current_playbook=current_playbook,
            accuracy_data=accuracy_data or {},
            recent_analyses=recent_analyses or []
        )
        
        try:
            # Get LLM to synthesize playbook
            playbook_content = await self._call_llm(prompt)
            
            # Create new playbook
            new_version = (current_playbook.version + 1) if current_playbook else 1
            
            # Merge LLM output with defaults
            content = PlaybookContent(
                philosophy=playbook_content.get('philosophy', default_content.philosophy),
                pre_analysis_checklist=playbook_content.get('pre_analysis_checklist', default_content.pre_analysis_checklist),
                victory_patterns=playbook_content.get('victory_patterns', default_content.victory_patterns),
                defeat_patterns=playbook_content.get('defeat_patterns', default_content.defeat_patterns),
                campaign_patterns=playbook_content.get('campaign_patterns', {}),
                anti_patterns=playbook_content.get('anti_patterns', default_content.anti_patterns),
                scoring_calibration=playbook_content.get('scoring_calibration', default_content.scoring_calibration),
                raw_markdown=playbook_content.get('raw_markdown', '')
            )
            
            # Count patterns
            patterns_count = len(content.victory_patterns) + len(content.defeat_patterns)
            campaign_patterns_count = sum(len(v) for v in content.campaign_patterns.values())
            
            playbook = QCPlaybook(
                qc_agent_id=qc_agent_id,
                user_id="",  # Set by caller
                agent_type=agent_type,
                version=new_version,
                is_current=True,
                content=content,
                training_data_count=len(recent_analyses) if recent_analyses else 0,
                verified_outcomes_count=accuracy_data.get('total', 0) if accuracy_data else 0,
                prediction_accuracy=accuracy_data.get('overall', 0) if accuracy_data else 0,
                patterns_count=patterns_count,
                campaign_patterns_count=campaign_patterns_count,
                is_auto_generated=True,
                user_edited=False,
                last_edited_by="system"
            )
            
            # Generate the raw markdown
            playbook.content.raw_markdown = playbook._generate_markdown()
            
            return playbook
            
        except Exception as e:
            logger.error(f"Training brain error: {str(e)}")
            # Return a playbook with defaults on error
            return QCPlaybook(
                qc_agent_id=qc_agent_id,
                user_id="",
                agent_type=agent_type,
                version=(current_playbook.version + 1) if current_playbook else 1,
                content=default_content
            )
    
    def _build_training_prompt(
        self,
        agent_type: str,
        patterns: List[dict],
        current_playbook: Optional[QCPlaybook],
        accuracy_data: Dict,
        recent_analyses: List[dict]
    ) -> str:
        """Build the training prompt for playbook generation"""
        
        agent_focus = "voice tonality and emotional delivery" if agent_type == "tonality" else "conversation tactics and language patterns"
        
        # Separate patterns by type
        victory_patterns = [p for p in patterns if p.get('pattern_type') == 'victory' or p.get('outcome_impact') == 'showed']
        defeat_patterns = [p for p in patterns if p.get('pattern_type') == 'defeat' or p.get('outcome_impact') == 'no_show']
        campaign_patterns = [p for p in patterns if p.get('pattern_type') == 'campaign_specific']
        
        current_playbook_md = ""
        if current_playbook:
            current_playbook_md = current_playbook.content.raw_markdown or current_playbook._generate_markdown()
        
        dynamic_content = f"""You are a QC Training Brain specializing in {agent_focus}.

Your task: Synthesize learned patterns into an actionable playbook for QC analysis.

## LEARNED PATTERNS

### Victory Patterns (predict "showed"):
{json.dumps([{{'signal': p.get('signal'), 'impact': p.get('impact_percentage')}} for p in victory_patterns], indent=2)}

### Defeat Patterns (predict "no-show"):
{json.dumps([{{'signal': p.get('signal'), 'impact': p.get('impact_percentage')}} for p in defeat_patterns], indent=2)}

### Campaign-Specific Patterns:
{json.dumps([{{'campaign': p.get('campaign_id'), 'signal': p.get('signal')}} for p in campaign_patterns], indent=2)}

## CURRENT ACCURACY
{json.dumps(accuracy_data, indent=2)}

## CURRENT PLAYBOOK (for reference)
{current_playbook_md[:2000] if current_playbook_md else "No existing playbook"}

## YOUR TASK

Create an updated playbook that:
1. Prioritizes the most impactful patterns
2. Provides clear, actionable guidance
3. Includes a pre-analysis checklist
4. Adds anti-patterns (common mistakes to avoid)
5. Includes scoring calibration guidance

Return JSON:
{{
  "philosophy": "Core analysis philosophy (2-3 sentences)",
  "pre_analysis_checklist": ["item1", "item2", ...],
  "victory_patterns": [
    {{"signal": "pattern description", "impact": 0.15, "description": "why it matters"}}
  ],
  "defeat_patterns": [
    {{"signal": "pattern description", "impact": 0.20, "description": "why it matters"}}
  ],
  "campaign_patterns": {{
    "campaign_id": [{{"signal": "pattern", "description": "context"}}]
  }},
  "anti_patterns": ["DON'T do this", "DON'T do that"],
  "scoring_calibration": {{
    "base_show_likelihood": 0.5,
    "adjust_up_when": ["condition1", "condition2"],
    "adjust_down_when": ["condition1", "condition2"]
  }},
  "raw_markdown": "# Full playbook in markdown format\\n..."
}}

IMPORTANT: The raw_markdown should be a complete, well-formatted playbook document that can be injected into the QC agent's prompt."""
        
        # Add custom prefix and suffix
        prompt = f"{self.prefix}{dynamic_content}{self.suffix}"
        
        # Add custom instructions if present
        if self.custom_instructions:
            prompt += f"\n\n## ADDITIONAL INSTRUCTIONS\n{self.custom_instructions}"
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> Dict:
        """Call the LLM and parse JSON response"""
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                if self.llm_provider == "grok":
                    response = await client.post(
                        "https://api.x.ai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.llm_model,
                            "messages": [
                                {"role": "system", "content": self.system_prompt},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.4
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Parse JSON from response
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0]
                        elif '```' in content:
                            content = content.split('```')[1].split('```')[0]
                        
                        return json.loads(content.strip())
                    else:
                        logger.error(f"LLM API error: {response.status_code}")
                        return {}
        except Exception as e:
            logger.error(f"LLM call error: {str(e)}")
            return {}


# ============================================================================
# LEARNING ORCHESTRATOR
# ============================================================================

class LearningOrchestrator:
    """
    Orchestrates the full learning loop:
    1. Check if learning should trigger
    2. Gather analysis logs with outcomes
    3. Run Reflection Brain
    4. Run Training Brain
    5. Update playbook
    """
    
    def __init__(self, db_instance):
        global db
        db = db_instance
    
    async def check_and_trigger_learning(
        self,
        qc_agent_id: str,
        user_id: str,
        trigger_reason: str = "outcome_update"
    ) -> Optional[LearningSession]:
        """
        Check if learning should trigger based on agent config.
        Returns LearningSession if learning was triggered, None otherwise.
        """
        # Get agent and config
        agent = await db.qc_agents.find_one({"id": qc_agent_id, "user_id": user_id})
        if not agent:
            return None
        
        learning_config = agent.get('learning_config', {})
        mode = learning_config.get('mode', 'manual')
        
        if mode == 'manual':
            return None  # Only manual trigger
        
        if mode == 'auto':
            # Trigger on every outcome update
            return await self.run_learning_session(qc_agent_id, user_id, trigger="auto")
        
        if mode == 'every_x':
            # Check if we've hit the threshold
            outcomes_since = learning_config.get('outcomes_since_last_learning', 0)
            trigger_count = learning_config.get('trigger_count', 10)
            
            if outcomes_since >= trigger_count:
                return await self.run_learning_session(qc_agent_id, user_id, trigger="every_x")
        
        return None
    
    async def run_learning_session(
        self,
        qc_agent_id: str,
        user_id: str,
        trigger: str = "manual"
    ) -> LearningSession:
        """
        Run a full learning session (reflection + training).
        """
        session = LearningSession(
            qc_agent_id=qc_agent_id,
            user_id=user_id,
            session_type=LearningSessionType.FULL,
            trigger=trigger
        )
        
        try:
            # Get agent
            agent = await db.qc_agents.find_one({"id": qc_agent_id, "user_id": user_id})
            if not agent:
                session.success = False
                session.error_message = "Agent not found"
                return session
            
            agent_type = agent.get('agent_type', 'language_pattern')
            session.agent_type = agent_type
            
            # Get API key
            api_key = await self._get_api_key(user_id, agent.get('llm_provider', 'grok'))
            if not api_key:
                session.success = False
                session.error_message = "No API key configured"
                return session
            
            # Get analysis logs with known outcomes
            logs = await db.qc_analysis_logs.find({
                "qc_agent_id": qc_agent_id,
                "actual_outcome": {"$in": ["showed", "no_show"]},
                "is_training_data": True
            }).to_list(length=500)
            
            session.analyses_reviewed_count = len(logs)
            session.analyses_reviewed_ids = [l.get('id') for l in logs[:100]]
            
            # Count outcomes
            showed_count = len([l for l in logs if l.get('actual_outcome') == 'showed'])
            no_show_count = len([l for l in logs if l.get('actual_outcome') == 'no_show'])
            session.outcomes_included = {"showed": showed_count, "no_show": no_show_count}
            
            if len(logs) < 5:
                session.success = False
                session.error_message = f"Not enough training data. Need at least 5 outcomes, have {len(logs)}."
                return session
            
            # Get existing patterns
            existing_patterns = await db.qc_patterns.find({
                "qc_agent_id": qc_agent_id,
                "is_active": True
            }).to_list(length=100)
            
            # Get current playbook
            current_playbook = await db.qc_playbooks.find_one({
                "qc_agent_id": qc_agent_id,
                "is_current": True
            })
            if current_playbook:
                session.playbook_version_before = current_playbook.get('version')
            
            # Get custom brain prompts (if any)
            custom_prompts = agent.get('brain_prompts')
            
            # === REFLECTION BRAIN ===
            reflection_brain = ReflectionBrain(
                api_key=api_key,
                llm_provider=agent.get('llm_provider', 'grok'),
                llm_model=agent.get('llm_model', 'grok-3'),
                custom_prompts=custom_prompts,
                agent_type=agent_type
            )
            
            reflection_result = await reflection_brain.reflect(
                qc_agent_id=qc_agent_id,
                agent_type=agent_type,
                analysis_logs=logs,
                existing_patterns=[p for p in existing_patterns]
            )
            
            # Save new patterns
            new_patterns = reflection_result.get('patterns', [])
            for pattern in new_patterns:
                pattern.user_id = user_id
                await db.qc_patterns.insert_one(pattern.dict())
                session.new_patterns.append(pattern.id)
            
            session.patterns_identified = len(new_patterns)
            
            # === TRAINING BRAIN ===
            training_brain = TrainingBrain(
                api_key=api_key,
                llm_provider=agent.get('llm_provider', 'grok'),
                llm_model=agent.get('llm_model', 'grok-3'),
                custom_prompts=custom_prompts,
                agent_type=agent_type
            )
            
            # Combine existing + new patterns
            all_patterns = existing_patterns + [p.dict() for p in new_patterns]
            
            current_playbook_obj = None
            if current_playbook:
                current_playbook_obj = QCPlaybook(**current_playbook)
            
            new_playbook = await training_brain.generate_playbook(
                qc_agent_id=qc_agent_id,
                agent_type=agent_type,
                patterns=all_patterns,
                current_playbook=current_playbook_obj,
                accuracy_data=reflection_result.get('accuracy', {}),
                recent_analyses=logs[:50]
            )
            
            new_playbook.user_id = user_id
            
            # Archive old playbook
            if current_playbook:
                await db.qc_playbooks.update_one(
                    {"id": current_playbook['id']},
                    {"$set": {"is_current": False}}
                )
            
            # Save new playbook
            await db.qc_playbooks.insert_one(new_playbook.dict())
            session.playbook_version_after = new_playbook.version
            
            # Update agent's learning config
            await db.qc_agents.update_one(
                {"id": qc_agent_id},
                {
                    "$set": {
                        "learning_config.last_learning_at": datetime.now(timezone.utc),
                        "learning_config.outcomes_since_last_learning": 0,
                        "learning_config.total_learning_sessions": agent.get('learning_config', {}).get('total_learning_sessions', 0) + 1
                    }
                }
            )
            
            # Mark logs as reviewed
            await db.qc_analysis_logs.update_many(
                {"id": {"$in": session.analyses_reviewed_ids}},
                {"$set": {"has_been_reviewed": True}}
            )
            
            session.success = True
            session.completed_at = datetime.now(timezone.utc)
            session.duration_seconds = (session.completed_at - session.started_at).total_seconds()
            session.accuracy_before = current_playbook.get('prediction_accuracy') if current_playbook else None
            session.accuracy_after = new_playbook.prediction_accuracy
            
            # Calculate diff summary
            if current_playbook:
                old_patterns = current_playbook.get('patterns_count', 0)
                new_patterns_count = new_playbook.patterns_count
                session.playbook_diff_summary = f"Patterns: {old_patterns} → {new_patterns_count}"
            else:
                session.playbook_diff_summary = f"Initial playbook created with {new_playbook.patterns_count} patterns"
            
            # Save session
            await db.qc_learning_sessions.insert_one(session.dict())
            
            return session
            
        except Exception as e:
            logger.error(f"Learning session error: {str(e)}")
            session.success = False
            session.error_message = str(e)
            session.completed_at = datetime.now(timezone.utc)
            await db.qc_learning_sessions.insert_one(session.dict())
            return session
    
    async def _get_api_key(self, user_id: str, provider: str) -> Optional[str]:
        """Get API key for the user"""
        from key_encryption import decrypt_api_key
        
        try:
            key_patterns = {
                'grok': 'xai-',
                'openai': 'sk-',
                'anthropic': 'sk-ant-'
            }
            
            key_doc = await db.api_keys.find_one({
                "user_id": user_id,
                "$or": [
                    {"service_name": provider, "is_active": True},
                    {"provider": provider, "is_active": True}
                ]
            })
            
            if not key_doc and provider in key_patterns:
                pattern = key_patterns[provider]
                all_keys = await db.api_keys.find({"user_id": user_id}).to_list(length=None)
                for k in all_keys:
                    api_key = k.get('api_key', '')
                    if api_key.startswith(pattern):
                        key_doc = k
                        break
            
            if not key_doc:
                return None
            
            if key_doc.get('encrypted_key'):
                return decrypt_api_key(key_doc['encrypted_key'])
            return key_doc.get('api_key')
        except Exception as e:
            logger.error(f"Error getting API key: {str(e)}")
            return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def create_initial_playbook(
    qc_agent_id: str,
    user_id: str,
    agent_type: str
) -> QCPlaybook:
    """Create an initial playbook for a new QC agent"""
    content = get_default_playbook_content(agent_type)
    
    playbook = QCPlaybook(
        qc_agent_id=qc_agent_id,
        user_id=user_id,
        agent_type=agent_type,
        version=1,
        is_current=True,
        content=content,
        is_auto_generated=True
    )
    
    # Generate markdown
    playbook.content.raw_markdown = playbook._generate_markdown()
    
    return playbook


async def log_qc_analysis(
    qc_agent_id: str,
    user_id: str,
    agent_type: str,
    call_id: str,
    analysis_content: dict,
    predictions: AnalysisPrediction,
    campaign_id: str = None,
    lead_id: str = None,
    call_agent_id: str = None
) -> QCAnalysisLog:
    """Log a QC analysis with predictions for learning"""
    
    log = QCAnalysisLog(
        qc_agent_id=qc_agent_id,
        qc_agent_type=agent_type,
        user_id=user_id,
        call_id=call_id,
        campaign_id=campaign_id,
        lead_id=lead_id,
        call_agent_id=call_agent_id,
        analysis_content=analysis_content,
        scores=analysis_content.get('scores', {}),
        recommendations=analysis_content.get('recommendations', []),
        predictions=predictions
    )
    
    return log


async def update_analysis_outcome(
    log_id: str,
    outcome: OutcomeType,
    db_instance
) -> Tuple[bool, Optional[float]]:
    """
    Update an analysis log with the actual outcome.
    Returns (success, prediction_accuracy)
    """
    log = await db_instance.qc_analysis_logs.find_one({"id": log_id})
    if not log:
        return False, None
    
    predictions = log.get('predictions', {})
    show_likelihood = predictions.get('show_likelihood', 0.5)
    
    # Calculate prediction accuracy
    accuracy = None
    if outcome == OutcomeType.SHOWED:
        accuracy = show_likelihood  # Higher is better
    elif outcome == OutcomeType.NO_SHOW:
        accuracy = 1 - show_likelihood  # Lower likelihood = better prediction
    
    # Determine missed/correct signals
    risk_factors = predictions.get('risk_factors', [])
    positive_signals = predictions.get('positive_signals', [])
    
    missed_signals = []
    correct_signals = []
    
    if outcome == OutcomeType.SHOWED:
        correct_signals = positive_signals
        # Risk factors that didn't matter
    elif outcome == OutcomeType.NO_SHOW:
        correct_signals = risk_factors
        # Positive signals that were misleading
        missed_signals = positive_signals
    
    await db_instance.qc_analysis_logs.update_one(
        {"id": log_id},
        {
            "$set": {
                "actual_outcome": outcome.value,
                "outcome_updated_at": datetime.now(timezone.utc),
                "prediction_accuracy": accuracy,
                "missed_signals": missed_signals,
                "correct_signals": correct_signals
            }
        }
    )
    
    # Increment outcomes counter on agent
    await db_instance.qc_agents.update_one(
        {"id": log['qc_agent_id']},
        {"$inc": {"learning_config.outcomes_since_last_learning": 1}}
    )
    
    return True, accuracy
