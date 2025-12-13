from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class CallDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class CallStatus(str, Enum):
    QUEUED = "queued"
    RINGING = "ringing"
    ANSWERED = "answered"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    CANCELED = "canceled"

class CallEndReason(str, Enum):
    HANGUP = "hangup"
    COMPLETED = "completed"
    DECLINED = "declined"
    TIMEOUT = "timeout"
    ERROR = "error"
    USER_HANGUP = "user_hangup"
    AGENT_HANGUP = "agent_hangup"

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"

class PhoneNumberModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: str  # E.164 format: +14048000152
    agent_id: Optional[str] = None
    direction: CallDirection  # inbound or outbound
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CallLogModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str  # Telnyx call_control_id
    agent_id: str
    phone_number_id: Optional[str] = None
    direction: CallDirection
    from_number: str
    to_number: str
    
    # Call details
    status: CallStatus = CallStatus.QUEUED
    end_reason: Optional[CallEndReason] = None
    duration: int = 0  # seconds
    cost: float = 0.0
    
    # Timestamps
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    
    # AI Analysis
    sentiment: Sentiment = Sentiment.UNKNOWN
    transcript: List[Dict[str, Any]] = []  # Full conversation transcript
    summary: str = ""  # AI-generated summary
    
    # Metrics
    latency_avg: float = 0.0  # Average response latency
    latency_p50: float = 0.0
    latency_p90: float = 0.0
    latency_p99: float = 0.0
    user_sentiment_score: float = 0.0  # -1 to 1
    
    # Media
    recording_url: Optional[str] = None
    recording_duration: int = 0
    
    # Variables
    custom_variables: Dict[str, Any] = {}  # customer_name, email, etc.
    
    # Metadata
    metadata: Dict[str, Any] = {}
    error_message: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class OutboundCallRequest(BaseModel):
    agent_id: str
    to_number: str  # E.164 format
    from_number: Optional[str] = None  # If not provided, use agent's default
    email: Optional[str] = None  # Contact's email address
    custom_variables: Dict[str, Any] = {}  # Inject variables into agent

class CallHistoryFilter(BaseModel):
    agent_id: Optional[str] = None
    direction: Optional[CallDirection] = None
    status: Optional[CallStatus] = None
    sentiment: Optional[Sentiment] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    search: Optional[str] = None  # Search by phone number or call_id
    limit: int = 50
    offset: int = 0

class CallAnalytics(BaseModel):
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    avg_duration: float = 0.0
    total_cost: float = 0.0
    avg_sentiment: float = 0.0
    sentiment_breakdown: Dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    avg_latency: float = 0.0
    total_duration: int = 0
    period_start: datetime
    period_end: datetime

import uuid
