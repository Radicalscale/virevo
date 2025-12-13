from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

# ============ LEAD MODELS ============

class LeadStatus:
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    APPOINTMENT_SET = "appointment_set"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    SHOWED_UP = "showed_up"
    NO_SHOW = "no_show"
    CUSTOMER = "customer"
    DEAD = "dead"

class LeadSource:
    INBOUND_CALL = "inbound_call"
    OUTBOUND_CALL = "outbound_call"
    WEB_FORM = "web_form"
    MANUAL_ENTRY = "manual_entry"
    IMPORT = "import"
    AD_CAMPAIGN = "ad_campaign"


# ============ LEAD CATEGORY SYSTEM ============

class LeadCategoryEnum(str, Enum):
    """Complete lead categorization system for QC tracking"""
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
    """Per-lead tracking metrics for QC analytics"""
    calls_to_answer: int = 0  # How many calls before they answered
    calls_to_book: int = 0  # How many calls before booking appointment
    calls_to_show: int = 0  # How many calls before they showed
    
    no_show_count: int = 0
    no_show_to_followup_booked: int = 0
    no_show_to_followup_showed: int = 0
    
    total_calls_made: int = 0
    total_appointments_set: int = 0
    total_appointments_showed: int = 0
    
    # Ratio calculations (computed)
    no_show_ratio: float = 0.0
    no_show_to_followup_booked_ratio: float = 0.0
    no_show_to_followup_showed_ratio: float = 0.0

class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: str
    source: str = LeadSource.MANUAL_ENTRY
    tags: List[str] = []
    notes: Optional[str] = None
    custom_fields: Dict[str, Any] = {}

class Lead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Owner of this lead
    name: str
    email: Optional[str] = None
    phone: str
    source: str = LeadSource.MANUAL_ENTRY
    status: str = LeadStatus.NEW
    tags: List[str] = []
    notes: Optional[str] = None
    custom_fields: Dict[str, Any] = {}  # Flexible extra fields
    
    # NEW: Category tracking for QC system
    category: Optional[str] = None  # LeadCategoryEnum value
    category_history: List[Dict[str, Any]] = []  # History of category changes
    
    # NEW: Per-lead metrics for QC analytics
    metrics: Optional[LeadMetrics] = None
    
    # Agent tracking
    last_agent_id: Optional[str] = None
    last_agent_name: Optional[str] = None
    
    # NEW: Campaign tracking
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    
    # NEW: Analysis tracking
    last_analysis_id: Optional[str] = None
    last_analysis_at: Optional[datetime] = None
    analysis_history: List[str] = []  # List of analysis IDs
    
    # QC Scores (from last call)
    commitment_score: Optional[int] = None  # 0-100
    conversion_score: Optional[int] = None  # 0-100
    excellence_score: Optional[int] = None  # 0-100
    show_up_probability: Optional[int] = None  # 0-100
    
    # Stats
    total_calls: int = 0
    total_appointments: int = 0
    appointments_showed: int = 0
    
    # Call tracking
    call_history: List[str] = []  # List of call IDs
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_contact: Optional[datetime] = None

# ============ APPOINTMENT MODELS ============

class AppointmentStatus:
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    SHOWED_UP = "showed_up"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"

class AppointmentCreate(BaseModel):
    lead_id: str
    agent_id: str
    scheduled_time: datetime
    duration_minutes: int = 30
    notes: Optional[str] = None
    external_id: Optional[str] = None  # ID from external appointment software

class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Owner
    lead_id: str
    lead_name: str
    agent_id: str
    agent_name: str
    call_id: Optional[str] = None  # Related call that set this appointment
    
    scheduled_time: datetime
    duration_minutes: int = 30
    status: str = AppointmentStatus.SCHEDULED
    
    showed_up: Optional[bool] = None
    showed_up_at: Optional[datetime] = None
    
    notes: Optional[str] = None
    external_id: Optional[str] = None  # ID from external appointment software (Calendly, etc.)
    external_data: Dict[str, Any] = {}  # Extra data from webhook
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ============ QC AGENT CONFIG MODELS ============

class QCAgentType:
    COMMITMENT_DETECTOR = "commitment_detector"
    CONVERSION_PATHFINDER = "conversion_pathfinder"
    EXCELLENCE_REPLICATOR = "excellence_replicator"

class QCAgentConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    agent_type: str  # commitment_detector, conversion_pathfinder, excellence_replicator
    
    # LLM Configuration
    llm_provider: str = "openai"  # openai, grok, anthropic, gemini
    llm_model: str = "gpt-4o"  # gpt-4o, gpt-5, claude-sonnet-4, grok-3, etc.
    
    enabled: bool = True
    
    # Processing settings
    process_on_call_end: bool = True
    process_async: bool = True  # Process in background vs. blocking
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QCAgentConfigUpdate(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    enabled: Optional[bool] = None

# ============ CALL ANALYTICS MODELS ============

class CallAnalytics(BaseModel):
    """Stores QC analysis results for a call"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    call_id: str
    lead_id: Optional[str] = None
    agent_id: str
    
    # Commitment Detector scores
    commitment_analysis: Optional[Dict[str, Any]] = None
    
    # Conversion Pathfinder scores
    conversion_analysis: Optional[Dict[str, Any]] = None
    
    # Excellence Replicator scores
    excellence_analysis: Optional[Dict[str, Any]] = None
    
    # Overall predictions
    show_up_probability: Optional[int] = None
    risk_level: Optional[str] = None  # low, medium, high
    
    # Recommendations
    recommendations: List[str] = []
    action_items: List[str] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============ WEBHOOK MODELS ============

class AppointmentWebhook(BaseModel):
    """Webhook from external appointment software"""
    external_id: str  # Appointment ID from external system
    lead_email: Optional[str] = None
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    event_type: str  # scheduled, confirmed, cancelled, completed, no_show
    event_time: datetime
    data: Dict[str, Any] = {}  # Raw webhook data

# ============ BULK IMPORT MODELS ============

class LeadImportItem(BaseModel):
    name: str
    email: Optional[str] = None
    phone: str
    source: str = LeadSource.IMPORT
    tags: List[str] = []
    notes: Optional[str] = None
    custom_fields: Dict[str, Any] = {}

class LeadImportRequest(BaseModel):
    leads: List[LeadImportItem]
    skip_duplicates: bool = True  # Skip if phone already exists
