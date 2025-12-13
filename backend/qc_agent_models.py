"""
QC Agent Models - Custom QC Agent System

This module defines the data models for the new QC Agent architecture.
QC Agents are separate from Call Agents and handle specific types of analysis:
- Tonality QC Agent: Voice analysis, ElevenLabs recommendations
- Language Pattern QC Agent: Script adherence, pattern detection
- Tech Issues QC Agent: Log analysis, code reading, solution generation
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import uuid


# ============================================================================
# QC AGENT TYPES
# ============================================================================

class QCAgentTypeEnum(str, Enum):
    """Types of QC Agents available"""
    TONALITY = "tonality"  # Voice/audio tonality analysis
    LANGUAGE_PATTERN = "language_pattern"  # Script quality, pattern detection
    TECH_ISSUES = "tech_issues"  # Log analysis, code review, solution generation
    GENERIC = "generic"  # General-purpose QC


class QCAgentMode(str, Enum):
    """Operating modes for QC Agents"""
    GENERIC = "generic"  # Default analysis rules
    CUSTOM = "custom"  # Campaign/agent-specific rules


# ============================================================================
# QC AGENT KNOWLEDGE BASE
# ============================================================================

class QCAgentKBItem(BaseModel):
    """Knowledge Base item for QC Agents"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    qc_agent_id: str
    source_type: str  # "file", "url", "text", "pattern_md"
    source_name: str  # filename, URL, or label
    content: str  # extracted text content
    description: Optional[str] = None
    file_size: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# ELEVENLABS EMOTIONAL DIRECTIONS
# ============================================================================

class ElevenLabsEmotionalDirections(BaseModel):
    """ElevenLabs-specific delivery instructions"""
    emotion_tags: List[str] = []  # ["warm", "confident", "empathetic"]
    pacing_instructions: str = ""  # "slow down on key points"
    emphasis_words: List[str] = []  # Words to emphasize
    tone_description: str = ""  # Overall tone description
    line_by_line_directions: List[Dict[str, str]] = []  # Per-line instructions
    prosody_xml: str = ""  # SSML/prosody markup
    copyable_prompt: str = ""  # Ready-to-paste prompt for node


# ============================================================================
# QC AGENT MODELS
# ============================================================================

class QCAgentCreate(BaseModel):
    """Create a new QC Agent"""
    name: str
    description: Optional[str] = None
    agent_type: QCAgentTypeEnum = QCAgentTypeEnum.GENERIC
    mode: QCAgentMode = QCAgentMode.GENERIC
    
    # LLM Configuration
    llm_provider: str = "grok"  # grok, openai, anthropic, gemini
    llm_model: str = "grok-3"
    
    # Analysis Rules (JSON structure)
    analysis_rules: Dict[str, Any] = {}
    
    # Custom prompt for analysis
    system_prompt: str = ""
    
    # Extended prompt configuration
    analysis_focus: str = ""  # Specific areas to focus on
    custom_criteria: str = ""  # Custom evaluation criteria/rubrics
    output_format_instructions: str = ""  # How to format output
    
    # ElevenLabs settings (for tonality agents)
    elevenlabs_settings: Optional[Dict[str, Any]] = None


class QCAgent(BaseModel):
    """QC Agent model - separate from Call Agents"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Owner
    name: str
    description: Optional[str] = None
    agent_type: QCAgentTypeEnum = QCAgentTypeEnum.GENERIC
    mode: QCAgentMode = QCAgentMode.GENERIC
    
    # LLM Configuration
    llm_provider: str = "grok"
    llm_model: str = "grok-3"
    api_key_id: Optional[str] = None  # Reference to user's API key
    
    # Analysis Configuration
    analysis_rules: Dict[str, Any] = {}
    system_prompt: str = ""
    
    # Extended prompt configuration
    analysis_focus: str = ""  # Specific areas to focus on
    custom_criteria: str = ""  # Custom evaluation criteria/rubrics
    output_format_instructions: str = ""  # How to format output
    
    # ElevenLabs Settings (for tonality agents)
    elevenlabs_settings: Optional[Dict[str, Any]] = None
    
    # Emotional Directions Template (for tonality agents)
    emotional_directions_template: Optional[ElevenLabsEmotionalDirections] = None
    
    # Knowledge Base references
    kb_items: List[str] = []  # List of KB item IDs
    
    # Pattern MD (uploaded from campaign analysis)
    pattern_md_content: Optional[str] = None
    pattern_md_updated_at: Optional[datetime] = None
    
    # Learning Configuration (for tonality and language_pattern agents)
    learning_config: Dict[str, Any] = Field(default_factory=lambda: {
        "mode": "manual",  # "auto", "every_x", "manual"
        "trigger_count": 10,  # For every_x mode
        "is_enabled": True,
        "outcomes_since_last_learning": 0,
        "total_learning_sessions": 0,
        "last_learning_at": None
    })
    
    # Brain Prompts (customizable learning brain prompts)
    brain_prompts: Optional[Dict[str, Any]] = None  # If None, uses defaults
    
    # Stats
    analyses_run: int = 0
    last_analysis_at: Optional[datetime] = None
    
    # Status
    is_active: bool = True
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QCAgentUpdate(BaseModel):
    """Update QC Agent"""
    name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[QCAgentMode] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    analysis_rules: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    analysis_focus: Optional[str] = None
    custom_criteria: Optional[str] = None
    output_format_instructions: Optional[str] = None
    elevenlabs_settings: Optional[Dict[str, Any]] = None
    emotional_directions_template: Optional[Dict[str, Any]] = None
    brain_prompts: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


# ============================================================================
# TECH ISSUES QC AGENT SPECIFIC MODELS
# ============================================================================

class TechIssueSolution(BaseModel):
    """Solution generated by Tech Issues QC Agent"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    qc_agent_id: str
    
    # Problem Classification
    issue_type: str  # "system", "prompt", "code", "multi_agent", "combination"
    issue_description: str
    severity: str  # "critical", "high", "medium", "low"
    
    # Solution Documents
    script_reconfiguration_md: Optional[str] = None  # Agent/prompt changes
    code_enhancement_md: Optional[str] = None  # Code fix instructions
    ai_coder_prompt: Optional[str] = None  # Ready-to-use prompt for AI coder
    
    # Affected Components
    affected_files: List[str] = []
    affected_nodes: List[str] = []
    
    # Analysis Details
    log_analysis: Dict[str, Any] = {}
    code_trace: Optional[str] = None
    
    # Recommendations
    recommendations: List[str] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# QC AGENT ASSIGNMENT
# ============================================================================

class QCAgentAssignment(BaseModel):
    """Links a QC Agent to a Call Agent or Campaign"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    qc_agent_id: str
    
    # Target (one of these should be set)
    call_agent_id: Optional[str] = None  # Assigned to specific call agent
    campaign_id: Optional[str] = None  # Assigned to campaign
    
    # Analysis triggers
    auto_analyze: bool = False  # Auto-run after call
    analysis_types: List[str] = ["all"]  # ["tech", "script", "tonality"] or ["all"]
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# LEAD CATEGORY SYSTEM
# ============================================================================

class LeadCategoryEnum(str, Enum):
    """Complete lead categorization system"""
    # Training
    TRAINING_CALL = "training_call"
    
    # Initial Contact
    NEW_FIRST_CALL = "new_first_call"
    NEW_NON_ANSWERED = "new_non_answered"
    
    # First Call Outcomes
    CALLED_DELAYED = "called_delayed"
    CALLED_REFUSED = "called_refused"
    APPOINTMENT_1_PRE_DATE = "1_appointment_pre_date"
    
    # First Appointment Outcomes
    APPOINTMENT_1_SHOWED = "1_appointment_showed"
    APPOINTMENT_1_NO_SHOW_CALL_2_NON_ANSWERED = "1_appointment_no_show_call_2_non_answered"
    APPOINTMENT_1_NO_SHOW_CALL_2_DELAYED = "1_appointment_no_show_call_2_delayed"
    APPOINTMENT_1_NO_SHOW_CALL_2_REFUSED = "1_appointment_no_show_call_2_refused"
    APPOINTMENT_1_NO_SHOW_CALL_2_NEW_APPOINTMENT = "1_appointment_no_show_call_2_new_appointment"
    
    # Second Appointment Outcomes
    APPOINTMENT_2_SHOWED = "2_appointment_showed"
    APPOINTMENT_2_NO_SHOW_CALL_3_NON_ANSWERED = "2_appointment_no_show_call_3_non_answered"
    APPOINTMENT_2_NO_SHOW_CALL_3_DELAYED = "2_appointment_no_show_call_3_delayed"
    APPOINTMENT_2_NO_SHOW_CALL_3_REFUSED = "2_appointment_no_show_call_3_refused"
    APPOINTMENT_2_NO_SHOW_CALL_3_NEW_APPOINTMENT = "2_appointment_no_show_call_3_new_appointment"
    
    # 3+ Appointments
    APPOINTMENT_3_PLUS_SHOWED = "3_plus_appointment_showed"
    APPOINTMENT_3_PLUS_NO_SHOW_CALL_4_PLUS_NON_ANSWERED = "3_plus_appointment_no_show_call_4_plus_non_answered"
    APPOINTMENT_3_PLUS_NO_SHOW_CALL_4_PLUS_DELAYED = "3_plus_appointment_no_show_call_4_plus_delayed"
    APPOINTMENT_3_PLUS_NO_SHOW_CALL_4_PLUS_REFUSED = "3_plus_appointment_no_show_call_4_plus_refused"
    APPOINTMENT_3_PLUS_NO_SHOW_CALL_4_PLUS_NEW_APPOINTMENT = "3_plus_appointment_no_show_call_4_plus_new_appointment"


class LeadMetrics(BaseModel):
    """Per-lead tracking metrics"""
    calls_to_answer: int = 0  # How many calls before they answered
    calls_to_book: int = 0  # How many calls before booking appointment
    calls_to_show: int = 0  # How many calls before they showed
    
    no_show_count: int = 0
    no_show_to_followup_booked: int = 0
    no_show_to_followup_showed: int = 0
    
    total_calls_made: int = 0
    total_appointments_set: int = 0
    total_appointments_showed: int = 0


# ============================================================================
# CAMPAIGN CALL TYPES
# ============================================================================

class CampaignCallType(str, Enum):
    """Types of calls in a campaign"""
    TRAINING = "training"  # Uploaded for training/pattern detection only
    REAL = "real"  # Actual campaign calls from agents


class CampaignAgentRole(str, Enum):
    """Agent roles in a multi-agent campaign"""
    FIRST_TOUCH = "first_touch"
    FOLLOW_UP_PRE_APPOINTMENT = "follow_up_pre_appointment"
    NO_SHOW = "no_show"
    SECOND_NO_SHOW = "second_no_show"


# ============================================================================
# TRAINING CALL MODEL
# ============================================================================

class TrainingCall(BaseModel):
    """Training call uploaded to campaign for pattern learning"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    user_id: str
    
    # File info
    filename: str
    file_url: Optional[str] = None
    file_size: int = 0
    
    # Extracted data
    transcript: List[Dict[str, Any]] = []
    duration: int = 0  # seconds
    
    # Designation/tags
    designation: str = ""  # User-provided label
    tags: List[str] = []
    
    # Analysis results (from QC agent)
    qc_results: Optional[Dict[str, Any]] = None
    
    # Status
    processed: bool = False
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# CAMPAIGN ENHANCEMENTS
# ============================================================================

class CampaignAgentConfig(BaseModel):
    """Configuration for agents in a multi-agent campaign"""
    role: CampaignAgentRole
    agent_id: str
    agent_name: str
    is_required: bool = True


class CampaignEnhanced(BaseModel):
    """Enhanced Campaign model with new features"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: Optional[str] = None
    
    # QC Agent assignments
    tonality_qc_agent_id: Optional[str] = None
    language_pattern_qc_agent_id: Optional[str] = None
    tech_issues_qc_agent_id: Optional[str] = None
    
    # Multi-agent configuration
    agents: List[CampaignAgentConfig] = []
    
    # Knowledge Base
    kb_items: List[str] = []  # KB item IDs
    custom_prompt_instructions: str = ""
    
    # Analysis rules
    rules: Dict[str, Any] = {}
    learning_parameters: Dict[str, Any] = {}
    
    # Auto-analysis settings
    auto_pattern_detection: bool = False
    auto_analysis_after_n_calls: Optional[int] = None  # Auto after X calls
    auto_analysis_every_n_calls: Optional[int] = None  # Auto every X calls
    auto_analysis_on_category: List[str] = []  # Auto for specific categories
    
    # CRM Integration
    crm_integration_enabled: bool = False
    auto_create_leads: bool = False
    auto_reanalyze_on_appointment_update: bool = False
    
    # Stats
    total_training_calls: int = 0
    total_real_calls: int = 0
    last_analysis_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# APPOINTMENT RE-ANALYSIS
# ============================================================================

class AppointmentReAnalysis(BaseModel):
    """Re-analysis triggered after appointment outcome"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    appointment_id: str
    call_id: str
    lead_id: str
    campaign_id: str
    
    # Original analysis
    original_analysis_id: str
    original_prediction: Dict[str, Any] = {}
    
    # Post-appointment analysis
    appointment_outcome: str  # "showed", "no_show"
    post_analysis: Dict[str, Any] = {}
    
    # What changed
    prediction_accuracy: float = 0.0
    insights: List[str] = []
    
    # Generated document
    analysis_document_md: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
