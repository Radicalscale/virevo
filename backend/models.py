from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

# API Key Management Models
class APIKeyCreate(BaseModel):
    service_name: str  # "openai", "deepgram", "elevenlabs", "grok", "hume"
    api_key: str
    
class APIKey(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Owner of this API key
    service_name: str
    api_key: str  # Should be encrypted in real production
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Dead Air Prevention Settings
class DeadAirSettings(BaseModel):
    silence_timeout_normal: int = 7  # seconds - timeout when user goes silent
    silence_timeout_hold_on: int = 25  # seconds - timeout when user says "hold on"
    max_checkins_before_disconnect: int = 2  # max check-ins per silence period before disconnect
    max_call_duration: int = 1500  # seconds (25 minutes) - max call length
    checkin_message: str = "Are you still there?"  # message to send during check-ins

# Voicemail & IVR Detection Settings
class VoicemailDetectionSettings(BaseModel):
    enabled: bool = True  # Enable voicemail/IVR detection
    use_telnyx_amd: bool = True  # Use Telnyx's AMD (Answering Machine Detection)
    telnyx_amd_mode: str = "premium"  # "standard" or "premium"
    use_llm_detection: bool = True  # Use AI-based detection during call
    disconnect_on_detection: bool = True  # Auto-disconnect when voicemail/IVR detected
    
# Advanced Agent Settings Models
class DeepgramSettings(BaseModel):
    endpointing: int = 500  # ms - time of silence before considering speech ended
    vad_turnoff: int = 250  # ms - VAD silence detection threshold  
    utterance_end_ms: int = 1000  # ms - time to wait before finalizing utterance
    interim_results: bool = True  # whether to return interim transcription results
    smart_format: bool = True  # auto-format transcripts
    
class ElevenLabsSettings(BaseModel):
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel
    model: str = "eleven_turbo_v2_5"  # turbo_v2_5, flash_v2_5, eleven_multilingual_v2
    stability: float = 0.5  # 0.0 to 1.0
    similarity_boost: float = 0.75  # 0.0 to 1.0
    style: float = 0.0  # 0.0 to 1.0 (only for v2 models)
    speed: float = 1.0  # 0.5 to 2.0
    use_speaker_boost: bool = True
    enable_normalization: bool = True  # Auto-converts numbers, dates to spoken form
    enable_ssml_parsing: bool = False  # Support for SSML tags (slight latency increase)

class HumeSettings(BaseModel):
    voice_name: str = "e7af7ed6-3381-48aa-ab97-49485007470b"  # Hume voice ID (UUID)
    description: str = "warm and friendly"  # Emotional description (not used in API)
    speed: float = 1.0  # 0.5 to 2.0

class SesameSettings(BaseModel):
    speaker_id: int = 0  # Voice ID (0-9 for different voices)
    output_format: str = "wav"  # Output format (wav recommended for Telnyx)

class MeloTTSSettings(BaseModel):
    voice: str = "EN-US"  # Voice ID (EN-US, EN-BR, EN-INDIA, EN-AU, EN-Default)
    speed: float = 1.2  # Speech rate (0.5 to 2.0)
    clone_wav: Optional[str] = None  # Optional path to WAV file for voice cloning


class DiaSettings(BaseModel):
    voice: str = "S1"  # Speaker/Voice ID (S1, S2, S3, etc.)
    speed: float = 1.0  # Speech rate (0.25 to 4.0)
    response_format: str = "wav"  # Audio format (wav, mp3, opus, aac, flac)


class KokoroSettings(BaseModel):
    voice: str = "af_bella"  # Voice ID (af_bella, af_nicole, af_sarah, af_sky, bf_emma, bf_isabella, am_adam, am_michael, bm_george, bm_lewis)
    speed: float = 1.0  # Speech rate (0.5 to 2.0)
    response_format: str = "mp3"  # Audio format (mp3, wav)

class ChatTTSSettings(BaseModel):
    voice: str = "female_1"  # Voice preset (male_1, male_2, male_3, female_1, female_2, female_3, neutral_1, neutral_2)
    speed: float = 1.0  # Speech rate (0.5 to 2.0)
    temperature: float = 0.3  # Sampling temperature (0.1 to 1.0, lower = faster/more stable)
    response_format: str = "wav"  # Audio format (wav, mp3)

class AssemblyAISettings(BaseModel):
    sample_rate: int = 8000  # Audio sample rate (8000 or 16000)
    word_boost: List[str] = []  # Words to boost recognition
    enable_extra_session_information: bool = True  # Include session metadata
    disable_partial_transcripts: bool = False  # Disable real-time partial results
    threshold: float = 0.0  # Turn detection threshold (0.0-1.0, 0=most responsive)
    # Smart Endpointing Parameters (Advanced Turn Detection)
    end_of_turn_confidence_threshold: float = 0.8  # Confidence threshold for turn detection (0.0-1.0)
    min_end_of_turn_silence_when_confident: int = 500  # Minimum silence (ms) when confident about turn end
    max_turn_silence: int = 2000  # Maximum silence (ms) before forcing turn end

class SonioxSettings(BaseModel):
    model: str = "stt-rt-telephony-v3"  # Soniox telephony model for 8kHz mulaw audio
    sample_rate: int = 8000  # Audio sample rate (8000 or 16000)
    audio_format: str = "mulaw"  # Audio format: mulaw, alaw, pcm_s16le, etc.
    num_channels: int = 1  # Number of audio channels (1=mono, 2=stereo)
    enable_endpoint_detection: bool = True  # Enable automatic endpoint detection
    enable_speaker_diarization: bool = False  # Enable speaker diarization
    language_hints: List[str] = ["en"]  # Language hints for recognition
    context: str = ""  # Custom context for improved accuracy

# Agent Models
class AgentSettings(BaseModel):
    temperature: float = 0.7
    max_tokens: int = 500
    tts_speed: float = 1.0
    
    # Advanced Provider Settings
    llm_provider: str = "openai"  # "openai" or "grok"
    tts_provider: str = "cartesia"  # "elevenlabs", "hume", "cartesia", "kokoro", "chattts", etc.
    stt_provider: str = "deepgram"  # "deepgram", "assemblyai", or "soniox"
    
    # Comfort Noise Setting (optional per-agent feature)
    enable_comfort_noise: bool = False  # Enable subtle background noise mixed into TTS audio
    
    # Dead Air Prevention Settings
    dead_air_settings: Optional[DeadAirSettings] = Field(default_factory=DeadAirSettings)
    
    # Voicemail & IVR Detection Settings
    voicemail_detection: Optional[VoicemailDetectionSettings] = Field(default_factory=VoicemailDetectionSettings)
    
    # Provider-specific settings
    deepgram_settings: Optional[DeepgramSettings] = Field(default_factory=DeepgramSettings)
    elevenlabs_settings: Optional[ElevenLabsSettings] = Field(default_factory=ElevenLabsSettings)
    hume_settings: Optional[HumeSettings] = Field(default_factory=HumeSettings)
    sesame_settings: Optional[SesameSettings] = Field(default_factory=SesameSettings)
    melo_settings: Optional[MeloTTSSettings] = Field(default_factory=MeloTTSSettings)
    dia_settings: Optional[DiaSettings] = Field(default_factory=DiaSettings)
    kokoro_settings: Optional[KokoroSettings] = Field(default_factory=KokoroSettings)
    chattts_settings: Optional[ChatTTSSettings] = Field(default_factory=ChatTTSSettings)
    assemblyai_settings: Optional[AssemblyAISettings] = Field(default_factory=AssemblyAISettings)
    soniox_settings: Optional[SonioxSettings] = Field(default_factory=SonioxSettings)

class AgentStats(BaseModel):
    calls_handled: int = 0
    avg_latency: float = 0.0
    success_rate: float = 0.0

# Auto QC Settings for Agents
class AutoQCSettings(BaseModel):
    enabled: bool = False  # Master toggle for auto QC
    campaign_id: Optional[str] = None  # Campaign to auto-add calls to
    run_tech_analysis: bool = True  # Run Tech/Latency analysis
    run_script_analysis: bool = True  # Run Script Quality analysis
    run_tonality_analysis: bool = True  # Run Tonality analysis

class FlowNode(BaseModel):
    id: str
    type: str
    label: str
    data: Dict[str, Any]

class AgentCreate(BaseModel):
    name: str
    description: str
    voice: str = "Rachel"
    language: str = "English"
    model: str = "gpt-4-turbo"
    agent_type: str = "single_prompt"  # "single_prompt" or "call_flow"
    system_prompt: str = ""  # Used by single_prompt agents
    call_flow: List[FlowNode] = []  # Used by call_flow agents
    settings: Optional[AgentSettings] = AgentSettings()

class Agent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Owner of this agent
    name: str
    description: str
    voice: str
    language: str
    model: str
    status: str = "active"
    agent_type: str = "single_prompt"  # "single_prompt" or "call_flow"
    system_prompt: str = ""  # GLOBAL PROMPT: Used by both single_prompt and call_flow agents
                              # For single_prompt: This IS the agent's prompt
                              # For call_flow: This is the universal personality/behavior layer that applies across all nodes
    call_flow: List[FlowNode] = []  # Used by call_flow agents only
    settings: AgentSettings = AgentSettings()
    stats: AgentStats = AgentStats()
    auto_qc_settings: Optional[AutoQCSettings] = Field(default_factory=AutoQCSettings)  # Auto QC configuration
    # QC Agent assignments - which QC agents analyze calls from this voice agent
    tonality_qc_agent_id: Optional[str] = None  # Assigned Tonality QC agent
    language_pattern_qc_agent_id: Optional[str] = None  # Assigned Language Pattern QC agent  
    tech_issues_qc_agent_id: Optional[str] = None  # Assigned Tech Issues QC agent
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Call Models
class TranscriptEntry(BaseModel):
    speaker: str
    text: str
    timestamp: datetime

class CallCreate(BaseModel):
    agent_id: str
    phone_number: Optional[str] = None
    direction: str = "outbound"

class Call(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Owner of this call
    agent_id: str
    agent_name: str
    phone_number: Optional[str] = None
    direction: str
    duration: int = 0
    status: str = "in_progress"
    sentiment: str = "neutral"
    latency: float = 0.0
    transcript: List[TranscriptEntry] = []
    recording_url: Optional[str] = None
    daily_room_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Phone Number Models
class PhoneNumberCreate(BaseModel):
    number: str
    inbound_agent_id: Optional[str] = None
    outbound_agent_id: Optional[str] = None

class PhoneNumber(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Owner of this phone number
    number: str
    inbound_agent_id: Optional[str] = None
    inbound_agent_name: Optional[str] = None
    outbound_agent_id: Optional[str] = None
    outbound_agent_name: Optional[str] = None
    status: str = "active"
    calls_received: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Daily.co Room Models
class DailyRoomCreate(BaseModel):
    name: Optional[str] = None
    privacy: str = "public"
    properties: Dict[str, Any] = {}

class DailyRoomResponse(BaseModel):
    room_url: str
    room_name: str
    config: Dict[str, Any]

# Knowledge Base Models
class KnowledgeBaseItemCreate(BaseModel):
    agent_id: str
    source_type: str  # "file" or "url"
    source_name: str  # filename or URL
    content: str  # extracted text content
    description: Optional[str] = None  # What this KB contains (e.g., "company info", "sales scripts")

class KnowledgeBaseItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Owner of this knowledge base item
    agent_id: str
    source_type: str  # "file" or "url"
    source_name: str  # filename or URL
    content: str  # extracted text content
    description: Optional[str] = None  # What this KB contains - helps agent know when to use it
    file_size: int = 0  # size in bytes
    created_at: datetime = Field(default_factory=datetime.utcnow)


# QC Campaign Models

# Campaign Agent Role Types
class CampaignAgentRole:
    FIRST_TOUCH = "first_touch"
    FOLLOW_UP_PRE_APPOINTMENT = "follow_up_pre_appointment"
    NO_SHOW = "no_show"
    SECOND_NO_SHOW = "second_no_show"

class CampaignAgentConfig(BaseModel):
    """Configuration for agents in a multi-agent campaign"""
    role: str  # CampaignAgentRole value
    agent_id: str
    agent_name: str = ""
    is_required: bool = True

class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: Optional[str] = None
    rules: Dict[str, Any] = {}  # User-defined rules for QC analysis
    learning_parameters: Dict[str, Any] = {}  # What to look for, thresholds, etc.
    linked_agents: List[str] = []  # Agent IDs associated with this campaign
    auto_pattern_detection: bool = False  # Auto-run pattern detection when new calls are added
    
    # NEW: Multi-agent campaign support
    campaign_agents: List[Dict[str, Any]] = []  # List of CampaignAgentConfig
    
    # NEW: QC Agent assignments
    tonality_qc_agent_id: Optional[str] = None
    language_pattern_qc_agent_id: Optional[str] = None
    tech_issues_qc_agent_id: Optional[str] = None
    
    # NEW: Knowledge Base
    kb_items: List[str] = []  # KB item IDs
    custom_prompt_instructions: str = ""
    
    # NEW: Auto-analysis settings
    auto_analysis_after_n_calls: Optional[int] = None  # Auto after X calls
    auto_analysis_every_n_calls: Optional[int] = None  # Auto every X calls
    auto_analysis_on_category: List[str] = []  # Auto for specific categories
    
    # NEW: CRM Integration
    crm_integration_enabled: bool = False
    auto_create_leads: bool = False
    auto_reanalyze_on_appointment_update: bool = False
    
    # NEW: Training calls count
    total_training_calls: int = 0
    total_real_calls: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rules: Dict[str, Any] = {}
    learning_parameters: Dict[str, Any] = {}
    linked_agents: List[str] = []
    auto_pattern_detection: bool = False
    # NEW fields
    campaign_agents: List[Dict[str, Any]] = []
    tonality_qc_agent_id: Optional[str] = None
    language_pattern_qc_agent_id: Optional[str] = None
    tech_issues_qc_agent_id: Optional[str] = None
    custom_prompt_instructions: str = ""
    auto_analysis_after_n_calls: Optional[int] = None
    auto_analysis_every_n_calls: Optional[int] = None
    crm_integration_enabled: bool = False
    auto_create_leads: bool = False

class CampaignCall(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    call_id: str
    call_type: str = "real"  # "training" or "real"
    designation: str = ""  # User-provided label
    category: Optional[str] = None  # Lead category
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    tech_qc_results: Optional[Dict[str, Any]] = None  # Latency analysis
    script_qc_results: Optional[Dict[str, Any]] = None  # Script quality analysis
    tonality_qc_results: Optional[Dict[str, Any]] = None  # Tonality analysis

# Training Call Model
class TrainingCall(BaseModel):
    """Training call uploaded to campaign for pattern learning"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    user_id: str
    filename: str
    file_url: Optional[str] = None
    file_size: int = 0
    transcript: List[Dict[str, Any]] = []
    duration: int = 0  # seconds
    designation: str = ""  # User-provided label
    tags: List[str] = []
    qc_results: Optional[Dict[str, Any]] = None
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CampaignSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    suggestion_type: str  # "prompt", "transition", "kb", "tonality"
    node_id: Optional[str] = None
    suggestion_text: str
    frequency_count: int = 1  # How many times this suggestion appeared
    impact_score: float = 0.0  # Estimated impact
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CampaignPattern(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    pattern_type: str  # "bottleneck", "success", "failure", "improvement"
    description: str
    affected_nodes: List[str] = []
    evidence_calls: List[str] = []  # Call IDs where this pattern was observed
    confidence_score: float = 0.0  # 0-1 confidence in this pattern
    created_at: datetime = Field(default_factory=datetime.utcnow)

# QC Analysis Request/Response Models
class TechQCRequest(BaseModel):
    call_id: str
    call_log_url: Optional[str] = None  # URL to log file or embedded log data
    call_log_data: Optional[str] = None  # Raw log content

class TechQCResponse(BaseModel):
    call_id: str
    overall_performance: str  # "excellent", "good", "needs improvement", "poor"
    total_nodes: int
    flagged_nodes: int
    node_analyses: List[Dict[str, Any]]  # Detailed breakdown per node
    recommendations: List[str]
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

class ScriptQCRequest(BaseModel):
    call_id: str
    campaign_id: Optional[str] = None
    custom_rules: Optional[Dict[str, Any]] = None

class ScriptQCResponse(BaseModel):
    call_id: str
    overall_quality: str
    node_analyses: List[Dict[str, Any]]
    bulk_suggestions: Dict[str, Any]  # Suggestions for all nodes
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

