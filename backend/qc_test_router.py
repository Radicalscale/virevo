from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from auth_middleware import get_current_user
from qc_agents.orchestrator import QCAgentOrchestrator

logger = logging.getLogger(__name__)

qc_test_router = APIRouter(prefix="/api/qc", tags=["QC Testing"])

# This will be injected by server.py
db = None

def set_db(database):
    global db
    db = database

class QCTestRequest:
    """Request model for testing QC agents"""
    def __init__(self, data: dict):
        self.transcript = data.get('transcript', '')
        self.lead_id = data.get('lead_id')
        self.agent_id = data.get('agent_id')
        self.custom_parameters = data.get('custom_parameters', {})
        self.metadata = data.get('metadata', {})

@qc_test_router.post("/test")
async def test_qc_agents(request_data: dict, current_user: dict = Depends(get_current_user)):
    """
    Test QC agents with custom transcript and parameters
    
    Body:
    {
        "transcript": "Agent: Hello...\nUser: Hi...",
        "lead_id": "optional_lead_id",
        "agent_id": "optional_agent_id",
        "custom_parameters": {
            "track_keywords": ["price", "cost"],
            "expected_commitment_level": "high",
            "expected_funnel_stages": ["hook", "qualification", "closing"]
        },
        "metadata": {
            "duration_seconds": 180,
            "call_hour": 14,
            "day_of_week": 2
        }
    }
    """
    try:
        logger.info(f"🧪 QC Test request from user {current_user['email']}")
        
        request = QCTestRequest(request_data)
        
        # Validate transcript
        if not request.transcript or len(request.transcript) < 10:
            raise HTTPException(
                status_code=400,
                detail="Transcript must be at least 10 characters long"
            )
        
        # Get API key for LLM calls - use user's OpenAI key from database
        from server import get_api_key
        api_key = await get_api_key(current_user['id'], 'openai')
        
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="No OpenAI API key found. Please add your OpenAI API key in Settings (https://platform.openai.com/api-keys)"
            )
        
        logger.info("Using user's OpenAI API key for QC analysis")
        
        # Initialize orchestrator
        orchestrator = QCAgentOrchestrator(db, api_key)
        
        # Prepare metadata with defaults
        metadata = {
            'duration_seconds': request.metadata.get('duration_seconds', 180),
            'call_hour': request.metadata.get('call_hour', datetime.utcnow().hour),
            'day_of_week': request.metadata.get('day_of_week', datetime.utcnow().weekday()),
            **request.custom_parameters  # Add custom parameters to metadata
        }
        
        # Generate test call ID
        test_call_id = f"test_{datetime.utcnow().timestamp()}"
        
        # Convert list of message objects to single concatenated string (same logic as server.py process_qc_analysis)
        transcript_data = request.transcript
        if isinstance(transcript_data, list):
            transcript_parts = []
            for msg in transcript_data:
                role = msg.get("role", "unknown")
                content = msg.get("text", msg.get("content", ""))
                transcript_parts.append(f"{role}: {content}")
            transcript = "\n".join(transcript_parts)
            logger.info(f"📝 Converted transcript from {len(transcript_data)} messages to {len(transcript)} characters")
        else:
            # If it's already a string, use it as-is
            transcript = str(transcript_data)
            logger.info(f"🧪 Using string transcript (length: {len(transcript)} chars)")
        
        # Run QC analysis
        analysis_result = await orchestrator.analyze_call(
            call_id=test_call_id,
            user_id=current_user['id'],
            transcript=transcript,  # Use converted transcript
            metadata=metadata,
            lead_id=request.lead_id,
            agent_id=request.agent_id
        )
        
        logger.info(f"✅ QC test analysis completed")
        
        # Return results with test info
        return {
            'status': 'success',
            'test_call_id': test_call_id,
            'analysis': analysis_result,
            'custom_parameters': request.custom_parameters,
            'metadata': metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in QC test: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"QC test failed: {str(e)}"
        )

@qc_test_router.post("/test/preset/{preset_name}")
async def test_qc_with_preset(preset_name: str, current_user: dict = Depends(get_current_user)):
    """
    Test QC agents with preset scenarios
    
    Presets: high_quality, poor_quality, medium_quality, objection_heavy
    """
    presets = {
        'high_quality': {
            'transcript': '''Agent: Hi Sarah! I'm calling about your inquiry from our Facebook ad. How are you today?
User: Oh yes, I was interested in learning more!
Agent: Great! Tell me, what specifically are you looking to achieve with your business?
User: I need to grow my revenue. I'm stuck at the same level for months.
Agent: I understand that's frustrating. Our program has helped businesses like yours achieve 2x growth in 90 days. For your specific situation, this means you could see an additional $50k in revenue.
User: That sounds really interesting. How exactly does it work?
Agent: I'm glad you asked! We provide personalized coaching, proven frameworks, and weekly accountability. The benefit you'll see is not just revenue growth, but sustainable systems.
User: Okay, what's the investment?
Agent: Great question - it shows you're serious! Our program is $5k, and we offer payment plans. Given the potential $50k increase, it pays for itself quickly.
User: That makes sense. I'm interested.
Agent: Excellent! Would you like to schedule a free strategy session to discuss your specific goals and see if this is the right fit?
User: Yes, absolutely! When can we do this?
Agent: Perfect! I'm really excited to help you. How's Tuesday at 2pm?
User: Tuesday at 2pm works great! I'll definitely be there.
Agent: Wonderful! I'm sending you a calendar invite right now with all the details. You'll also receive a reminder 24 hours before. I'm really looking forward to helping you achieve that revenue growth!
User: Thank you so much! I'm looking forward to it too!
Agent: See you Tuesday, Sarah! Have a great day!''',
            'metadata': {'duration_seconds': 420},
            'expected': {'commitment': 85, 'conversion': 95, 'excellence': 88}
        },
        'poor_quality': {
            'transcript': '''Agent: Hey.
User: Hi?
Agent: Want to schedule something?
User: I guess... what is it?
Agent: A call.
User: I don't know if I'll be free.
Agent: Okay, I'll just put you down for Tuesday.
User: Uh, okay.''',
            'metadata': {'duration_seconds': 45},
            'expected': {'commitment': 25, 'conversion': 30, 'excellence': 20}
        },
        'medium_quality': {
            'transcript': '''Agent: Hi, I'd like to discuss our services with you.
User: Okay, but I'm really busy right now.
Agent: I understand. This will only take 2 minutes of your time.
User: Alright, go ahead.
Agent: We help businesses like yours grow revenue. Are you interested in growth?
User: Yes, but I've tried programs before and they didn't work.
Agent: I hear you. What didn't work about those programs?
User: They were too generic and didn't fit my business.
Agent: That's exactly why ours is different. We customize everything to your specific needs and industry.
User: Hmm, okay. How much does it cost?
Agent: The investment is $3k, but given your revenue potential, you'll see ROI in 60 days.
User: Alright, let me schedule a call to discuss this further.
Agent: Perfect! I'll send you some times.''',
            'metadata': {'duration_seconds': 180},
            'expected': {'commitment': 58, 'conversion': 68, 'excellence': 62}
        },
        'objection_heavy': {
            'transcript': '''Agent: Hi! I'd love to tell you about our program.
User: I don't have time for this.
Agent: I completely understand. What if I could show you how to save 10 hours a week?
User: I've heard that before. It never works.
Agent: I hear your skepticism. Can you tell me what you tried before?
User: Some productivity course. It was useless.
Agent: I appreciate you sharing that. Our approach is different because we focus on your specific workflow. What's your biggest time drain right now?
User: Emails. I spend 3 hours a day on emails.
Agent: That's huge! Our system helped clients cut email time by 70%. That's 2 hours back in your day.
User: Okay, but how much is this going to cost me?
Agent: The program is $2k. But think about it - if you save 2 hours daily at your billing rate, that's $10k+ in value per month.
User: I need to talk to my business partner first.
Agent: Absolutely, I respect that. How about we schedule a call with both of you? That way we can address any questions together.
User: Alright, that makes sense. Next Wednesday?
Agent: Perfect! Wednesday at 3pm work?
User: Yes, that works.
Agent: Great! I'll send a calendar invite to both of you with all the details.''',
            'metadata': {'duration_seconds': 300},
            'expected': {'commitment': 65, 'conversion': 75, 'excellence': 70}
        }
    }
    
    if preset_name not in presets:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown preset: {preset_name}. Available: {', '.join(presets.keys())}"
        )
    
    preset = presets[preset_name]
    
    # Run test with preset
    return await test_qc_agents(
        request_data={
            'transcript': preset['transcript'],
            'metadata': preset['metadata'],
            'custom_parameters': {
                'preset_name': preset_name,
                'expected_scores': preset['expected']
            }
        },
        current_user=current_user
    )
