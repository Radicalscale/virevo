"""
QC Learning Models - Memory & Playbook System

This module implements the learning/memory architecture for QC Agents,
inspired by the multi-agent LLM learning system from combat AI.

Key Concepts:
- Playbooks: Active memory injected into QC prompts (like combat_lesson.md)
- Analysis Logs: Raw experience data with predictions
- Learning Sessions: Reflection & training runs
- Patterns: Identified correlations between signals and outcomes
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class LearningMode(str, Enum):
    """How the QC agent triggers learning"""
    AUTO = "auto"  # Learn after each appointment outcome
    EVERY_X = "every_x"  # Learn after X outcomes
    MANUAL = "manual"  # Only learn when user triggers


class OutcomeType(str, Enum):
    """Appointment/call outcomes for learning"""
    SHOWED = "showed"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    PENDING = "pending"
    UNKNOWN = "unknown"


class BookingQuality(str, Enum):
    """Predicted booking quality"""
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class PatternType(str, Enum):
    """Types of learned patterns"""
    VICTORY = "victory"  # Patterns that predict success (showed)
    DEFEAT = "defeat"  # Patterns that predict failure (no-show)
    CAMPAIGN_SPECIFIC = "campaign_specific"
    AGENT_SPECIFIC = "agent_specific"
    TRANSFERABLE = "transferable"  # Works across all contexts


class PlaybookSection(str, Enum):
    """Sections of a playbook"""
    PHILOSOPHY = "philosophy"
    PRE_ANALYSIS_CHECKLIST = "pre_analysis_checklist"
    VICTORY_PATTERNS = "victory_patterns"
    DEFEAT_PATTERNS = "defeat_patterns"
    CAMPAIGN_PATTERNS = "campaign_patterns"
    ANTI_PATTERNS = "anti_patterns"
    SCORING_CALIBRATION = "scoring_calibration"


# ============================================================================
# LEARNING CONFIGURATION
# ============================================================================

class LearningConfig(BaseModel):
    """Learning configuration for a QC Agent"""
    mode: LearningMode = LearningMode.MANUAL
    trigger_count: int = 10  # For EVERY_X mode
    last_learning_at: Optional[datetime] = None
    outcomes_since_last_learning: int = 0
    total_learning_sessions: int = 0
    is_enabled: bool = True


# ============================================================================
# PREDICTIONS
# ============================================================================

class AnalysisPrediction(BaseModel):
    """Predictions made during a QC analysis"""
    show_likelihood: float = Field(default=0.5, ge=0, le=1)
    booking_quality: BookingQuality = BookingQuality.MEDIUM
    risk_factors: List[str] = []
    positive_signals: List[str] = []
    confidence: float = Field(default=0.5, ge=0, le=1)
    
    # For tonality agents
    emotional_alignment_score: Optional[float] = None
    energy_match_score: Optional[float] = None
    
    # For language pattern agents
    commitment_strength_score: Optional[float] = None
    objection_resolution_score: Optional[float] = None


# ============================================================================
# ANALYSIS LOG (Raw Experience)
# ============================================================================

class QCAnalysisLog(BaseModel):
    """
    Individual QC analysis record with predictions.
    This is the "battle_log.md" equivalent - raw experience data.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    qc_agent_id: str
    qc_agent_type: str  # "tonality" or "language_pattern"
    user_id: str
    
    # What was analyzed
    call_id: str
    campaign_id: Optional[str] = None
    lead_id: Optional[str] = None
    call_agent_id: Optional[str] = None  # The call agent that made the call
    
    # The analysis output
    analysis_content: Dict[str, Any] = {}  # Full analysis result
    scores: Dict[str, float] = {}  # Numerical scores
    recommendations: List[str] = []
    
    # PREDICTIONS (critical for learning)
    predictions: Optional[AnalysisPrediction] = None
    
    # POST-OUTCOME (filled in when appointment result known)
    actual_outcome: OutcomeType = OutcomeType.PENDING
    outcome_updated_at: Optional[datetime] = None
    
    # Learning metrics (calculated after outcome known)
    prediction_accuracy: Optional[float] = None  # 0-1, how right were we?
    missed_signals: List[str] = []  # Signals we should have caught
    correct_signals: List[str] = []  # Signals we got right
    
    # Flags
    is_training_data: bool = True  # Include in learning?
    has_been_reviewed: bool = False  # Reviewed in a learning session?
    
    # Timestamps
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# PATTERNS (Learned Knowledge)
# ============================================================================

class LearnedPattern(BaseModel):
    """
    A pattern identified through learning.
    Like entries in master_win.md or master_loss.md.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    qc_agent_id: str
    user_id: str
    
    # Pattern classification
    pattern_type: PatternType
    agent_type: str  # "tonality" or "language_pattern"
    
    # Scope
    scope: str = "global"  # "global", "campaign:{id}", "call_agent:{id}"
    campaign_id: Optional[str] = None
    call_agent_id: Optional[str] = None
    
    # The pattern itself
    signal: str  # e.g., "No time confirmation in close"
    description: str  # Detailed explanation
    
    # Statistical backing
    correlation: float = 0.0  # How strongly correlated with outcome (-1 to 1)
    confidence: float = 0.0  # Statistical confidence (0-1)
    sample_size: int = 0  # How many analyses support this
    
    # Impact on predictions
    outcome_impact: str  # "showed" or "no_show"
    impact_percentage: float = 0.0  # e.g., +15% show rate
    
    # Status
    is_active: bool = True
    is_verified: bool = False  # Manually verified by user
    
    # Timestamps
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# PLAYBOOK (Active Memory)
# ============================================================================

class PlaybookContent(BaseModel):
    """Structured playbook content"""
    # Core sections
    philosophy: str = ""
    pre_analysis_checklist: List[str] = []
    
    # Victory/Defeat patterns (transferable)
    victory_patterns: List[Dict[str, Any]] = []  # [{signal, impact, description}]
    defeat_patterns: List[Dict[str, Any]] = []
    
    # Campaign-specific patterns
    campaign_patterns: Dict[str, List[Dict[str, Any]]] = {}  # {campaign_id: [patterns]}
    
    # Anti-patterns (common mistakes)
    anti_patterns: List[str] = []
    
    # Scoring calibration
    scoring_calibration: Dict[str, Any] = {}
    
    # Raw markdown (for full playbook)
    raw_markdown: str = ""


class QCPlaybook(BaseModel):
    """
    The active memory for a QC agent.
    This is the "combat_lesson.md" equivalent - injected into prompts.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    qc_agent_id: str
    user_id: str
    agent_type: str  # "tonality" or "language_pattern"
    
    # Version control
    version: int = 1
    is_current: bool = True
    
    # The playbook content
    content: PlaybookContent = Field(default_factory=PlaybookContent)
    
    # Stats
    training_data_count: int = 0  # How many analyses used
    verified_outcomes_count: int = 0  # How many had known outcomes
    prediction_accuracy: float = 0.0  # Historical accuracy
    
    # Patterns included
    patterns_count: int = 0
    campaign_patterns_count: int = 0
    
    # Edit tracking
    is_auto_generated: bool = True
    user_edited: bool = False
    last_edited_by: str = "system"  # "system" or "user"
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_injection_prompt(self) -> str:
        """Convert playbook to prompt injection format"""
        return self.content.raw_markdown or self._generate_markdown()
    
    def _generate_markdown(self) -> str:
        """Generate markdown from structured content"""
        lines = [
            f"# QC Playbook v{self.version}",
            f"Agent Type: {self.agent_type.replace('_', ' ').title()}",
            f"Training Data: {self.training_data_count} analyses, {self.verified_outcomes_count} verified outcomes",
            f"Historical Accuracy: {self.prediction_accuracy:.1%}",
            "",
        ]
        
        if self.content.philosophy:
            lines.extend([
                "## 1. CORE PHILOSOPHY",
                self.content.philosophy,
                "",
            ])
        
        if self.content.pre_analysis_checklist:
            lines.extend([
                "## 2. PRE-ANALYSIS CHECKLIST",
                "Before scoring ANY call, verify:",
            ])
            for item in self.content.pre_analysis_checklist:
                lines.append(f"□ {item}")
            lines.append("")
        
        if self.content.victory_patterns:
            lines.extend([
                "## 3. VICTORY PATTERNS (Predict 'Showed')",
            ])
            for p in self.content.victory_patterns:
                impact = p.get('impact', 0)
                sign = "+" if impact > 0 else ""
                lines.append(f"- {p.get('signal', '')}: {sign}{impact:.0%} show rate")
            lines.append("")
        
        if self.content.defeat_patterns:
            lines.extend([
                "## 4. DEFEAT PATTERNS (Predict 'No-Show')",
            ])
            for p in self.content.defeat_patterns:
                impact = p.get('impact', 0)
                sign = "+" if impact > 0 else ""
                lines.append(f"- {p.get('signal', '')}: {sign}{impact:.0%} no-show rate")
            lines.append("")
        
        if self.content.campaign_patterns:
            lines.append("## 5. CAMPAIGN-SPECIFIC PATTERNS")
            for campaign_id, patterns in self.content.campaign_patterns.items():
                lines.append(f"### Campaign: {campaign_id}")
                for p in patterns:
                    lines.append(f"- {p.get('signal', '')}: {p.get('description', '')}")
            lines.append("")
        
        if self.content.anti_patterns:
            lines.extend([
                "## 6. COMMON MISTAKES (Anti-Patterns)",
            ])
            for ap in self.content.anti_patterns:
                lines.append(f"- DON'T: {ap}")
            lines.append("")
        
        return "\n".join(lines)


# ============================================================================
# LEARNING SESSION (Training Run)
# ============================================================================

class LearningSessionType(str, Enum):
    REFLECTION = "reflection"  # Analyze outcomes, identify patterns
    LESSON_GENERATION = "lesson_generation"  # Generate playbook from patterns
    FULL = "full"  # Both reflection + lesson generation


class LearningSession(BaseModel):
    """
    Record of a learning/training run.
    Captures what was analyzed and what was learned.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    qc_agent_id: str
    user_id: str
    agent_type: str
    
    # Session type
    session_type: LearningSessionType
    trigger: str  # "auto", "every_x", "manual"
    
    # Inputs
    analyses_reviewed_count: int = 0
    analyses_reviewed_ids: List[str] = []
    outcomes_included: Dict[str, int] = {}  # {"showed": X, "no_show": Y}
    
    # Outputs
    patterns_identified: int = 0
    new_patterns: List[str] = []  # Pattern IDs
    updated_patterns: List[str] = []  # Pattern IDs
    
    playbook_version_before: Optional[int] = None
    playbook_version_after: Optional[int] = None
    playbook_diff_summary: str = ""
    
    # LLM details
    llm_provider: str = "grok"
    llm_model: str = "grok-3"
    reflection_prompt_used: str = ""
    training_prompt_used: str = ""
    
    # Results
    success: bool = True
    error_message: Optional[str] = None
    
    # Stats
    accuracy_before: Optional[float] = None
    accuracy_after: Optional[float] = None
    
    # Timestamps
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


# ============================================================================
# DEFAULT PLAYBOOK TEMPLATES
# ============================================================================

DEFAULT_TONALITY_PLAYBOOK = PlaybookContent(
    philosophy="""You are analyzing voice tonality and emotional delivery in sales calls.
Your goal: Identify patterns in vocal delivery that correlate with appointment outcomes.
Focus on: warmth, energy matching, confidence, emotional resonance, pacing.""",
    
    pre_analysis_checklist=[
        "Assess opening warmth and energy level",
        "Check for energy matching with customer throughout",
        "Evaluate emotional tone during objection handling",
        "Rate confidence level during close",
        "Note any tone mismatches or abrupt shifts",
    ],
    
    victory_patterns=[
        {"signal": "Warm, genuine opening tone", "impact": 0.15, "description": "Calls that start warm have higher show rates"},
        {"signal": "Energy matching with customer", "impact": 0.12, "description": "Mirroring customer energy builds rapport"},
        {"signal": "Confident, calm close", "impact": 0.18, "description": "Confident closes without desperation predict shows"},
    ],
    
    defeat_patterns=[
        {"signal": "Rushed pacing during close", "impact": 0.20, "description": "Rushing signals desperation, predicts no-shows"},
        {"signal": "Monotone during objections", "impact": 0.15, "description": "Flat delivery on objections fails to reassure"},
        {"signal": "Energy mismatch", "impact": 0.12, "description": "Not matching customer energy breaks rapport"},
    ],
    
    anti_patterns=[
        "Score high just because they agreed - check HOW they agreed",
        "Ignore subtle tone shifts that signal hesitation",
        "Overlook background noise or distraction in customer voice",
    ],
    
    scoring_calibration={
        "base_show_likelihood": 0.5,
        "adjust_down_when": ["rushed close", "tone mismatch", "forced enthusiasm"],
        "adjust_up_when": ["natural warmth", "energy sync", "confident pace"],
    }
)


DEFAULT_LANGUAGE_PATTERN_PLAYBOOK = PlaybookContent(
    philosophy="""You are analyzing conversation tactics and script quality in sales calls.
Your goal: Identify language patterns that correlate with appointment outcomes.
Focus on: commitment language, objection handling, confirmation steps, closing techniques.""",
    
    pre_analysis_checklist=[
        "Did agent confirm appointment DATE and TIME explicitly?",
        "Were all objections addressed (not deflected or ignored)?",
        "Was there a clear, specific next-step commitment?",
        "Did agent recap the value proposition before close?",
        "Check for vague language ('maybe', 'I'll try', 'we'll see')",
    ],
    
    victory_patterns=[
        {"signal": "Explicit time confirmation", "impact": 0.25, "description": "Confirming specific date/time dramatically increases shows"},
        {"signal": "Objection fully resolved", "impact": 0.20, "description": "Addressing concerns completely builds confidence"},
        {"signal": "Value recap before close", "impact": 0.15, "description": "Reminding of benefits reinforces commitment"},
        {"signal": "Assumptive close language", "impact": 0.12, "description": "Treating appointment as given increases follow-through"},
    ],
    
    defeat_patterns=[
        {"signal": "Vague commitment ('I'll try')", "impact": 0.30, "description": "Weak language predicts no-shows"},
        {"signal": "Skipped confirmation step", "impact": 0.25, "description": "Not confirming details = not committed"},
        {"signal": "Unresolved objections", "impact": 0.20, "description": "Lingering doubts lead to cancellations"},
        {"signal": "Rushed or pressured close", "impact": 0.18, "description": "Pressure creates buyer's remorse"},
    ],
    
    anti_patterns=[
        "Score high just because booking happened - evaluate HOW it happened",
        "Ignore soft objections (sighs, hesitation, long pauses)",
        "Miss the difference between agreement and commitment",
        "Overlook when customer asks 'clarifying' questions that signal doubt",
    ],
    
    scoring_calibration={
        "base_show_likelihood": 0.5,
        "adjust_down_when": ["vague commitment", "no time confirm", "open objections"],
        "adjust_up_when": ["explicit confirm", "resolved objections", "strong close"],
    }
)


def get_default_playbook_content(agent_type: str) -> PlaybookContent:
    """Get default playbook content for an agent type"""
    if agent_type == "tonality":
        return DEFAULT_TONALITY_PLAYBOOK
    elif agent_type == "language_pattern":
        return DEFAULT_LANGUAGE_PATTERN_PLAYBOOK
    else:
        return PlaybookContent()


# ============================================================================
# BRAIN PROMPT TEMPLATES
# ============================================================================

class BrainPrompts(BaseModel):
    """
    Customizable prompts for the learning brains.
    Users can view and tweak these to customize how the agent learns.
    """
    # Reflection Brain - analyzes outcomes
    reflection_system_prompt: str = "You are an expert QC analyst. Return valid JSON only."
    reflection_task_prompt: str = ""  # Built dynamically, but prefix/suffix can be customized
    reflection_prefix: str = ""  # Added before the dynamic prompt
    reflection_suffix: str = ""  # Added after the dynamic prompt
    
    # Training Brain - generates playbooks
    training_system_prompt: str = "You are an expert QC coach. Return valid JSON only."
    training_task_prompt: str = ""  # Built dynamically
    training_prefix: str = ""  # Added before the dynamic prompt
    training_suffix: str = ""  # Added after the dynamic prompt
    
    # Custom instructions that apply to both brains
    custom_instructions: str = ""


# Default brain prompts for Tonality agents
DEFAULT_TONALITY_BRAIN_PROMPTS = BrainPrompts(
    reflection_system_prompt="""You are an expert voice tonality and emotional intelligence analyst. 
Your specialty is identifying patterns in HOW things are said, not just WHAT is said.
Focus on: vocal warmth, energy levels, pacing, emotional resonance, confidence signals.
Return valid JSON only.""",

    reflection_prefix="""## TONALITY-SPECIFIC GUIDANCE
When analyzing these QC results, focus on VOICE patterns:
- Emotional tone at key moments (open, objection, close)
- Energy matching between agent and customer
- Pacing changes that signal confidence or anxiety
- Warmth indicators in voice quality

""",

    reflection_suffix="""

## TONALITY PATTERN PRIORITIES
Prioritize patterns related to:
1. Opening warmth and its correlation with outcomes
2. How agents handle emotional objections
3. Close confidence vs desperation signals
4. Energy synchronization throughout the call""",

    training_system_prompt="""You are a voice coaching expert who trains sales teams on emotional intelligence and vocal delivery.
Your playbooks should focus on HOW to speak, not just what to say.
Return valid JSON only.""",

    training_prefix="""## TONALITY PLAYBOOK FOCUS
This playbook should help QC analysts evaluate voice quality and emotional delivery.
Include specific guidance on:
- What warm vs cold openings sound like
- How to rate energy matching
- Signs of confident vs desperate closes
- Red flags in vocal delivery

""",

    training_suffix="""

## TONALITY COACHING PRINCIPLES
Remember: The same words delivered differently produce different outcomes.
Focus on patterns that are AUDIBLE, not just transcript-based.""",

    custom_instructions=""
)


# Default brain prompts for Language Pattern agents
DEFAULT_LANGUAGE_PATTERN_BRAIN_PROMPTS = BrainPrompts(
    reflection_system_prompt="""You are an expert sales conversation analyst.
Your specialty is identifying tactical patterns in sales conversations - what words, phrases, and structures lead to successful outcomes.
Focus on: commitment language, objection handling techniques, confirmation steps, closing tactics.
Return valid JSON only.""",

    reflection_prefix="""## LANGUAGE PATTERN GUIDANCE
When analyzing these QC results, focus on TACTICAL patterns:
- Specific phrases that correlate with shows vs no-shows
- Objection handling techniques and their effectiveness
- Confirmation and commitment language strength
- Closing technique variations and outcomes

""",

    reflection_suffix="""

## LANGUAGE PATTERN PRIORITIES
Prioritize patterns related to:
1. Confirmation language (explicit time/date vs vague)
2. Commitment strength indicators ("I will" vs "I'll try")
3. Objection resolution completeness
4. Close technique effectiveness""",

    training_system_prompt="""You are a sales tactics expert who trains teams on conversation structure and persuasion techniques.
Your playbooks should focus on WHAT to say and HOW to structure conversations.
Return valid JSON only.""",

    training_prefix="""## LANGUAGE TACTICS PLAYBOOK FOCUS
This playbook should help QC analysts evaluate conversation quality and tactical execution.
Include specific guidance on:
- What strong vs weak commitment language looks like
- How to rate objection resolution completeness
- Signs of effective vs ineffective closes
- Red flags in conversation structure

""",

    training_suffix="""

## TACTICAL COACHING PRINCIPLES
Remember: Small changes in wording produce big changes in outcomes.
Focus on patterns that are ACTIONABLE and TEACHABLE.""",

    custom_instructions=""
)


def get_default_brain_prompts(agent_type: str) -> BrainPrompts:
    """Get default brain prompts for an agent type"""
    if agent_type == "tonality":
        return DEFAULT_TONALITY_BRAIN_PROMPTS
    elif agent_type == "language_pattern":
        return DEFAULT_LANGUAGE_PATTERN_BRAIN_PROMPTS
    else:
        return BrainPrompts()

