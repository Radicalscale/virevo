from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from typing import List, Optional
from datetime import datetime
import logging
import csv
import io

from crm_models import (
    Lead, LeadCreate, LeadStatus, LeadSource,
    Appointment, AppointmentCreate, AppointmentStatus,
    QCAgentConfig, QCAgentConfigUpdate, QCAgentType,
    CallAnalytics,
    AppointmentWebhook,
    LeadImportRequest, LeadImportItem
)
from auth_middleware import get_current_user

logger = logging.getLogger(__name__)

crm_router = APIRouter(prefix="/api/crm", tags=["CRM"])

# This will be injected by server.py
db = None

def set_db(database):
    global db
    db = database

# ============ LEAD ENDPOINTS ============

@crm_router.post("/leads", response_model=Lead)
async def create_lead(lead_data: LeadCreate, current_user: dict = Depends(get_current_user)):
    """Create a new lead"""
    lead = Lead(
        user_id=current_user['id'],
        **lead_data.dict()
    )
    await db.leads.insert_one(lead.dict())
    logger.info(f"Created lead: {lead.id} for user: {current_user['email']}")
    return lead

@crm_router.get("/leads", response_model=List[Lead])
async def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """List leads with filters"""
    query = {"user_id": current_user['id']}
    
    if status:
        query["status"] = status
    if source:
        query["source"] = source
    if search:
        # Search in name, email, phone
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    leads = await db.leads.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [Lead(**lead) for lead in leads]

@crm_router.get("/leads/stats")
async def get_leads_stats(current_user: dict = Depends(get_current_user)):
    """Get lead statistics"""
    pipeline = [
        {"$match": {"user_id": current_user['id']}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    result = await db.leads.aggregate(pipeline).to_list(100)
    
    stats = {
        "total": 0,
        "by_status": {}
    }
    
    for item in result:
        stats["by_status"][item["_id"]] = item["count"]
        stats["total"] += item["count"]
    
    return stats

@crm_router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Get lead by ID"""
    lead = await db.leads.find_one({"id": lead_id, "user_id": current_user['id']})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Lead(**lead)

@crm_router.put("/leads/{lead_id}", response_model=Lead)
async def update_lead(lead_id: str, lead_data: dict, current_user: dict = Depends(get_current_user)):
    """Update lead"""
    lead = await db.leads.find_one({"id": lead_id, "user_id": current_user['id']})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead_data["updated_at"] = datetime.utcnow()
    lead_data.pop('user_id', None)  # Prevent user_id modification
    lead_data.pop('id', None)  # Prevent id modification
    
    await db.leads.update_one(
        {"id": lead_id, "user_id": current_user['id']},
        {"$set": lead_data}
    )
    
    updated_lead = await db.leads.find_one({"id": lead_id, "user_id": current_user['id']})
    return Lead(**updated_lead)

@crm_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Delete lead"""
    result = await db.leads.delete_one({"id": lead_id, "user_id": current_user['id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}

@crm_router.post("/leads/import")
async def import_leads(import_data: LeadImportRequest, current_user: dict = Depends(get_current_user)):
    """Bulk import leads"""
    imported = 0
    skipped = 0
    errors = []
    
    for lead_item in import_data.leads:
        try:
            # Check for duplicates by phone
            if import_data.skip_duplicates:
                existing = await db.leads.find_one({
                    "user_id": current_user['id'],
                    "phone": lead_item.phone
                })
                if existing:
                    skipped += 1
                    continue
            
            # Create lead
            lead = Lead(
                user_id=current_user['id'],
                **lead_item.dict()
            )
            await db.leads.insert_one(lead.dict())
            imported += 1
        except Exception as e:
            errors.append({"phone": lead_item.phone, "error": str(e)})
    
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors
    }

@crm_router.post("/leads/import-csv")
async def import_leads_from_csv(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Import leads from CSV file"""
    try:
        content = await file.read()
        csv_data = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        leads = []
        for row in csv_reader:
            lead_item = LeadImportItem(
                name=row.get('name', ''),
                email=row.get('email'),
                phone=row.get('phone', ''),
                source=row.get('source', LeadSource.IMPORT),
                tags=row.get('tags', '').split(',') if row.get('tags') else [],
                notes=row.get('notes')
            )
            leads.append(lead_item)
        
        # Use the import endpoint
        import_request = LeadImportRequest(leads=leads, skip_duplicates=True)
        return await import_leads(import_request, current_user)
        
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to import CSV: {str(e)}")

# ============ APPOINTMENT ENDPOINTS ============

@crm_router.post("/appointments", response_model=Appointment)
async def create_appointment(appt_data: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    """Create a new appointment"""
    # Get lead
    lead = await db.leads.find_one({"id": appt_data.lead_id, "user_id": current_user['id']})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get agent
    agent = await db.agents.find_one({"id": appt_data.agent_id, "user_id": current_user['id']})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    appointment = Appointment(
        user_id=current_user['id'],
        lead_id=appt_data.lead_id,
        lead_name=lead['name'],
        agent_id=appt_data.agent_id,
        agent_name=agent['name'],
        scheduled_time=appt_data.scheduled_time,
        duration_minutes=appt_data.duration_minutes,
        notes=appt_data.notes,
        external_id=appt_data.external_id
    )
    
    await db.appointments.insert_one(appointment.dict())
    
    # Update lead
    await db.leads.update_one(
        {"id": appt_data.lead_id},
        {
            "$set": {"status": LeadStatus.APPOINTMENT_SET, "updated_at": datetime.utcnow()},
            "$inc": {"total_appointments": 1}
        }
    )
    
    logger.info(f"Created appointment: {appointment.id} for lead: {appt_data.lead_id}")
    return appointment

@crm_router.get("/appointments", response_model=List[Appointment])
async def list_appointments(
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """List appointments"""
    query = {"user_id": current_user['id']}
    
    if lead_id:
        query["lead_id"] = lead_id
    if status:
        query["status"] = status
    
    appointments = await db.appointments.find(query).sort("scheduled_time", -1).limit(limit).to_list(limit)
    return [Appointment(**appt) for appt in appointments]

@crm_router.get("/appointments/{appt_id}", response_model=Appointment)
async def get_appointment(appt_id: str, current_user: dict = Depends(get_current_user)):
    """Get appointment by ID"""
    appt = await db.appointments.find_one({"id": appt_id, "user_id": current_user['id']})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return Appointment(**appt)

@crm_router.put("/appointments/{appt_id}", response_model=Appointment)
async def update_appointment(appt_id: str, appt_data: dict, current_user: dict = Depends(get_current_user)):
    """Update appointment"""
    appt = await db.appointments.find_one({"id": appt_id, "user_id": current_user['id']})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appt_data["updated_at"] = datetime.utcnow()
    
    await db.appointments.update_one(
        {"id": appt_id, "user_id": current_user['id']},
        {"$set": appt_data}
    )
    
    updated_appt = await db.appointments.find_one({"id": appt_id, "user_id": current_user['id']})
    return Appointment(**updated_appt)

# ============ WEBHOOK ENDPOINTS ============

@crm_router.post("/webhooks/appointment")
async def appointment_webhook(webhook_data: AppointmentWebhook):
    """
    Webhook endpoint for external appointment software (Calendly, Cal.com, etc.)
    Updates lead and appointment based on external ID
    """
    try:
        logger.info(f"📞 Received appointment webhook: {webhook_data.event_type} for {webhook_data.external_id}")
        
        # Find appointment by external_id
        appointment = await db.appointments.find_one({"external_id": webhook_data.external_id})
        
        if not appointment:
            logger.warning(f"⚠️  No appointment found for external_id: {webhook_data.external_id}")
            # Try to match by lead email or phone
            lead_query = {}
            if webhook_data.lead_email:
                lead_query["email"] = webhook_data.lead_email
            elif webhook_data.lead_phone:
                lead_query["phone"] = webhook_data.lead_phone
            
            if lead_query:
                lead = await db.leads.find_one(lead_query)
                if lead:
                    # Find most recent appointment for this lead
                    appointment = await db.appointments.find_one(
                        {"lead_id": lead['id']},
                        sort=[("scheduled_time", -1)]
                    )
        
        if not appointment:
            return {"status": "not_found", "message": "Appointment not found"}
        
        # Update appointment based on event type
        update_data = {
            "updated_at": datetime.utcnow(),
            "external_data": webhook_data.data
        }
        
        lead_update = {"updated_at": datetime.utcnow()}
        
        if webhook_data.event_type in ["confirmed", "rescheduled"]:
            update_data["status"] = AppointmentStatus.CONFIRMED
            lead_update["status"] = LeadStatus.APPOINTMENT_CONFIRMED
        
        elif webhook_data.event_type == "completed":
            update_data["status"] = AppointmentStatus.SHOWED_UP
            update_data["showed_up"] = True
            update_data["showed_up_at"] = webhook_data.event_time
            lead_update["status"] = LeadStatus.SHOWED_UP
            lead_update["$inc"] = {"appointments_showed": 1}
        
        elif webhook_data.event_type == "no_show":
            update_data["status"] = AppointmentStatus.NO_SHOW
            update_data["showed_up"] = False
            lead_update["status"] = LeadStatus.NO_SHOW
        
        elif webhook_data.event_type == "cancelled":
            update_data["status"] = AppointmentStatus.CANCELLED
        
        # Update appointment
        await db.appointments.update_one(
            {"id": appointment['id']},
            {"$set": update_data}
        )
        
        # Update lead
        if "$inc" in lead_update:
            inc_data = lead_update.pop("$inc")
            await db.leads.update_one(
                {"id": appointment['lead_id']},
                {"$set": lead_update, "$inc": inc_data}
            )
        else:
            await db.leads.update_one(
                {"id": appointment['lead_id']},
                {"$set": lead_update}
            )
        
        logger.info(f"✅ Updated appointment {appointment['id']} and lead {appointment['lead_id']}")
        
        return {"status": "success", "appointment_id": appointment['id']}
        
    except Exception as e:
        logger.error(f"❌ Error processing appointment webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ MANUAL APPOINTMENT OUTCOME ENDPOINTS ============

@crm_router.post("/appointments/{appt_id}/outcome")
async def update_appointment_outcome(
    appt_id: str,
    outcome_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Manually update appointment outcome (showed/no_show/cancelled).
    Use this for manual updates when external webhooks aren't available.
    
    Request body:
    {
        "outcome": "showed" | "no_show" | "cancelled" | "rescheduled",
        "notes": "Optional notes about the outcome",
        "outcome_time": "2025-12-02T14:00:00Z"  // Optional, defaults to now
    }
    """
    try:
        # Find appointment
        appointment = await db.appointments.find_one({
            "id": appt_id,
            "user_id": current_user['id']
        })
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        outcome = outcome_data.get('outcome', 'unknown')
        notes = outcome_data.get('notes', '')
        outcome_time = outcome_data.get('outcome_time')
        
        if outcome_time:
            from dateutil import parser
            outcome_time = parser.parse(outcome_time)
        else:
            outcome_time = datetime.utcnow()
        
        # Update appointment
        update_data = {
            "updated_at": datetime.utcnow(),
            "outcome_notes": notes
        }
        
        lead_update = {"updated_at": datetime.utcnow()}
        
        if outcome == "showed":
            update_data["status"] = AppointmentStatus.SHOWED_UP
            update_data["showed_up"] = True
            update_data["showed_up_at"] = outcome_time
            lead_update["status"] = LeadStatus.SHOWED_UP
            lead_update["$inc"] = {"appointments_showed": 1}
            
        elif outcome == "no_show":
            update_data["status"] = AppointmentStatus.NO_SHOW
            update_data["showed_up"] = False
            lead_update["status"] = LeadStatus.NO_SHOW
            
        elif outcome == "cancelled":
            update_data["status"] = AppointmentStatus.CANCELLED
            lead_update["status"] = LeadStatus.APPOINTMENT_CANCELLED if hasattr(LeadStatus, 'APPOINTMENT_CANCELLED') else "cancelled"
            
        elif outcome == "rescheduled":
            update_data["status"] = AppointmentStatus.RESCHEDULED
            # Keep lead status as appointment_set
        
        await db.appointments.update_one(
            {"id": appt_id},
            {"$set": update_data}
        )
        
        # Update lead
        if "$inc" in lead_update:
            inc_data = lead_update.pop("$inc")
            await db.leads.update_one(
                {"id": appointment['lead_id']},
                {"$set": lead_update, "$inc": inc_data}
            )
        else:
            await db.leads.update_one(
                {"id": appointment['lead_id']},
                {"$set": lead_update}
            )
        
        logger.info(f"✅ Updated appointment {appt_id} outcome to '{outcome}'")
        
        return {
            "status": "success",
            "appointment_id": appt_id,
            "outcome": outcome,
            "message": f"Appointment marked as {outcome}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating appointment outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@crm_router.post("/calls/{call_id}/detect-appointment")
async def detect_appointment_from_call(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze a call transcript to detect if an appointment was set.
    Creates an appointment record if detected.
    
    Returns:
    {
        "appointment_detected": true/false,
        "appointment_id": "uuid" (if created),
        "detected_info": {
            "date": "2025-12-05",
            "time": "14:00",
            "confidence": 0.95
        }
    }
    """
    try:
        # Get call data
        call = await db.call_logs.find_one({
            "call_id": call_id,
            "user_id": current_user['id']
        })
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        transcript = call.get('transcript', [])
        if not transcript:
            return {
                "appointment_detected": False,
                "message": "No transcript available for analysis"
            }
        
        # Format transcript for analysis
        conversation_text = ""
        for entry in transcript:
            role = entry.get('role', entry.get('speaker', 'unknown'))
            text = entry.get('text', entry.get('content', ''))
            conversation_text += f"{role}: {text}\n"
        
        # Use LLM to detect appointment
        result = await analyze_transcript_for_appointment(
            conversation_text,
            current_user['id']
        )
        
        if result.get('appointment_detected'):
            # Find or create lead
            to_number = call.get('to_number')
            lead = await db.leads.find_one({
                "phone": to_number,
                "user_id": current_user['id']
            })
            
            if not lead:
                # Create lead from call
                from uuid import uuid4
                lead = {
                    "id": str(uuid4()),
                    "user_id": current_user['id'],
                    "name": result.get('customer_name', 'Unknown'),
                    "phone": to_number,
                    "email": None,
                    "source": "call",
                    "status": LeadStatus.APPOINTMENT_SET,
                    "total_calls": 1,
                    "total_appointments": 0,
                    "appointments_showed": 0,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                await db.leads.insert_one(lead)
            
            # Create appointment
            from uuid import uuid4
            appointment_datetime = result.get('appointment_datetime')
            if not appointment_datetime:
                # Default to tomorrow at detected time or noon
                from datetime import timedelta
                appointment_datetime = datetime.utcnow() + timedelta(days=1)
                appointment_datetime = appointment_datetime.replace(hour=12, minute=0, second=0, microsecond=0)
            
            appointment = {
                "id": str(uuid4()),
                "user_id": current_user['id'],
                "lead_id": lead['id'],
                "agent_id": call.get('agent_id'),
                "call_id": call_id,
                "scheduled_time": appointment_datetime,
                "status": AppointmentStatus.SCHEDULED,
                "notes": f"Auto-detected from call. {result.get('notes', '')}",
                "detected_info": result,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await db.appointments.insert_one(appointment)
            
            # Update lead
            await db.leads.update_one(
                {"id": lead['id']},
                {
                    "$set": {
                        "status": LeadStatus.APPOINTMENT_SET,
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {"total_appointments": 1}
                }
            )
            
            logger.info(f"✅ Auto-detected appointment from call {call_id}, created appointment {appointment['id']}")
            
            return {
                "appointment_detected": True,
                "appointment_id": appointment['id'],
                "lead_id": lead['id'],
                "detected_info": result
            }
        else:
            return {
                "appointment_detected": False,
                "message": result.get('message', 'No appointment detected in conversation')
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error detecting appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_transcript_for_appointment(conversation_text: str, user_id: str) -> dict:
    """
    Use LLM to analyze transcript and detect if an appointment was set.
    """
    try:
        import httpx
        import json
        
        # Get user's API key (prefer OpenAI for this task)
        api_key_doc = await db.api_keys.find_one({
            "user_id": user_id,
            "service_name": "openai"
        })
        
        if not api_key_doc:
            # Fallback to grok
            api_key_doc = await db.api_keys.find_one({
                "user_id": user_id,
                "service_name": "grok"
            })
        
        if not api_key_doc:
            return {
                "appointment_detected": False,
                "message": "No API key configured for appointment detection"
            }
        
        api_key = api_key_doc.get('api_key')
        service = api_key_doc.get('service_name', 'openai')
        
        prompt = f"""Analyze this call transcript and determine if an appointment was set/scheduled.

Transcript:
{conversation_text}

Respond in JSON format:
{{
    "appointment_detected": true/false,
    "confidence": 0.0-1.0,
    "appointment_date": "YYYY-MM-DD" or null,
    "appointment_time": "HH:MM" or null,
    "customer_name": "extracted name" or null,
    "notes": "brief description of what was scheduled",
    "indicators": ["list of phrases that indicate appointment"]
}}

Look for indicators like:
- "let's schedule", "book an appointment", "set up a time"
- Specific dates/times mentioned
- Confirmations like "see you then", "looking forward to meeting"
- Calendar/scheduling references
"""
        
        if service == 'openai':
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "max_tokens": 500
            }
        else:  # grok
            url = "https://api.x.ai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "grok-3-fast",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            
            if response.status_code != 200:
                logger.error(f"LLM API error: {response.text}")
                return {"appointment_detected": False, "message": "LLM API error"}
            
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '{}')
            
            try:
                parsed = json.loads(content)
                
                # Parse date/time if detected
                if parsed.get('appointment_date') and parsed.get('appointment_time'):
                    from dateutil import parser
                    datetime_str = f"{parsed['appointment_date']} {parsed['appointment_time']}"
                    try:
                        parsed['appointment_datetime'] = parser.parse(datetime_str)
                    except:
                        parsed['appointment_datetime'] = None
                
                return parsed
            except json.JSONDecodeError:
                return {"appointment_detected": False, "message": "Failed to parse LLM response"}
        
    except Exception as e:
        logger.error(f"Error in appointment detection: {e}")
        return {"appointment_detected": False, "message": str(e)}


# ============ QC AGENT CONFIG ENDPOINTS ============

@crm_router.get("/qc-config", response_model=List[QCAgentConfig])
async def list_qc_configs(current_user: dict = Depends(get_current_user)):
    """List all QC agent configurations"""
    configs = await db.qc_agent_config.find({"user_id": current_user['id']}).to_list(10)
    
    # If no configs exist, create defaults
    if not configs:
        default_configs = [
            QCAgentConfig(
                user_id=current_user['id'],
                agent_type=QCAgentType.COMMITMENT_DETECTOR,
                llm_provider="openai",
                llm_model="gpt-4o"
            ),
            QCAgentConfig(
                user_id=current_user['id'],
                agent_type=QCAgentType.CONVERSION_PATHFINDER,
                llm_provider="openai",
                llm_model="gpt-4o"
            ),
            QCAgentConfig(
                user_id=current_user['id'],
                agent_type=QCAgentType.EXCELLENCE_REPLICATOR,
                llm_provider="openai",
                llm_model="gpt-4o"
            )
        ]
        
        for config in default_configs:
            await db.qc_agent_config.insert_one(config.dict())
        
        configs = [config.dict() for config in default_configs]
    
    return [QCAgentConfig(**config) for config in configs]

@crm_router.put("/qc-config/{agent_type}", response_model=QCAgentConfig)
async def update_qc_config(
    agent_type: str,
    config_data: QCAgentConfigUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update QC agent configuration"""
    config = await db.qc_agent_config.find_one({
        "user_id": current_user['id'],
        "agent_type": agent_type
    })
    
    if not config:
        raise HTTPException(status_code=404, detail="QC agent config not found")
    
    update_data = config_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db.qc_agent_config.update_one(
        {"user_id": current_user['id'], "agent_type": agent_type},
        {"$set": update_data}
    )
    
    updated_config = await db.qc_agent_config.find_one({
        "user_id": current_user['id'],
        "agent_type": agent_type
    })
    
    return QCAgentConfig(**updated_config)

# ============ CALL ANALYTICS ENDPOINTS ============

@crm_router.get("/analytics/call/{call_id}")
async def get_call_analytics(call_id: str, current_user: dict = Depends(get_current_user)):
    """Get QC analysis for a specific call"""
    analytics = await db.call_analytics.find_one({"call_id": call_id, "user_id": current_user['id']})
    if not analytics:
        raise HTTPException(status_code=404, detail="Call analytics not found")
    
    # Remove MongoDB ObjectId to make it JSON serializable
    if '_id' in analytics:
        del analytics['_id']
    
    # Convert datetime to ISO string if present
    if 'created_at' in analytics and hasattr(analytics['created_at'], 'isoformat'):
        analytics['created_at'] = analytics['created_at'].isoformat()
    
    return analytics

@crm_router.get("/analytics/lead/{lead_id}")
async def get_lead_analytics(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Get all QC analyses for a lead's calls"""
    analytics_list = await db.call_analytics.find({"lead_id": lead_id, "user_id": current_user['id']}).to_list(100)
    
    # Remove MongoDB ObjectId from each document
    for analytics in analytics_list:
        if '_id' in analytics:
            del analytics['_id']
        if 'created_at' in analytics and hasattr(analytics['created_at'], 'isoformat'):
            analytics['created_at'] = analytics['created_at'].isoformat()
    
    return analytics_list


# ============ LEAD CATEGORY MANAGEMENT ============

@crm_router.put("/leads/{lead_id}/category")
async def update_lead_category(
    lead_id: str,
    category_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update lead category for QC tracking"""
    lead = await db.leads.find_one({"id": lead_id, "user_id": current_user['id']})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    new_category = category_data.get('category')
    
    # Record category history
    category_history_entry = {
        "previous_category": lead.get('category'),
        "new_category": new_category,
        "changed_at": datetime.utcnow().isoformat(),
        "reason": category_data.get('reason', '')
    }
    
    await db.leads.update_one(
        {"id": lead_id, "user_id": current_user['id']},
        {
            "$set": {
                "category": new_category,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "category_history": category_history_entry
            }
        }
    )
    
    logger.info(f"Updated lead {lead_id} category to: {new_category}")
    return {"success": True, "category": new_category}


@crm_router.get("/leads/by-category/{category}")
async def get_leads_by_category(
    category: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all leads in a specific category"""
    leads = await db.leads.find({
        "user_id": current_user['id'],
        "category": category
    }).to_list(length=1000)
    
    for lead in leads:
        if '_id' in lead:
            lead['_id'] = str(lead['_id'])
    
    return leads


@crm_router.put("/leads/{lead_id}/metrics")
async def update_lead_metrics(
    lead_id: str,
    metrics_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update lead QC metrics"""
    lead = await db.leads.find_one({"id": lead_id, "user_id": current_user['id']})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    existing_metrics = lead.get('metrics', {}) or {}
    updated_metrics = {**existing_metrics, **metrics_data}
    
    # Calculate ratios
    if updated_metrics.get('no_show_count', 0) > 0 and updated_metrics.get('total_appointments_set', 0) > 0:
        updated_metrics['no_show_ratio'] = updated_metrics['no_show_count'] / updated_metrics['total_appointments_set']
    if updated_metrics.get('no_show_to_followup_booked', 0) > 0 and updated_metrics.get('no_show_count', 0) > 0:
        updated_metrics['no_show_to_followup_booked_ratio'] = updated_metrics['no_show_to_followup_booked'] / updated_metrics['no_show_count']
    
    await db.leads.update_one(
        {"id": lead_id, "user_id": current_user['id']},
        {
            "$set": {
                "metrics": updated_metrics,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"success": True, "metrics": updated_metrics}


# ============ APPOINTMENT RE-ANALYSIS ============

@crm_router.post("/appointments/{appt_id}/reanalyze")
async def trigger_appointment_reanalysis(
    appt_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger re-analysis of a call after appointment outcome is known.
    This creates a post-appointment analysis that factors in whether the lead showed up.
    """
    try:
        # Get appointment
        appointment = await db.appointments.find_one({
            "id": appt_id,
            "user_id": current_user['id']
        })
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        lead_id = appointment.get('lead_id')
        
        # Get the lead
        lead = await db.leads.find_one({"id": lead_id, "user_id": current_user['id']})
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Get the last call for this lead
        last_call_id = lead.get('call_history', [])[-1] if lead.get('call_history') else None
        
        if not last_call_id:
            raise HTTPException(status_code=400, detail="No call history found for lead")
        
        # Get the original analysis
        original_analysis = await db.call_analytics.find_one({
            "call_id": last_call_id,
            "user_id": current_user['id']
        })
        
        # Determine appointment outcome
        outcome = "showed" if appointment.get('showed_up') else "no_show"
        
        # Create re-analysis record
        reanalysis = {
            "id": str(__import__('uuid').uuid4()),
            "appointment_id": appt_id,
            "call_id": last_call_id,
            "lead_id": lead_id,
            "campaign_id": lead.get('campaign_id'),
            "user_id": current_user['id'],
            "original_analysis_id": original_analysis.get('id') if original_analysis else None,
            "original_prediction": {
                "show_up_probability": original_analysis.get('show_up_probability') if original_analysis else None,
                "commitment_score": original_analysis.get('commitment_score') if original_analysis else None
            },
            "appointment_outcome": outcome,
            "post_analysis": {},
            "prediction_accuracy": 0.0,
            "insights": [],
            "created_at": datetime.utcnow()
        }
        
        # Calculate prediction accuracy if we had a prediction
        if original_analysis and original_analysis.get('show_up_probability') is not None:
            predicted_prob = original_analysis['show_up_probability'] / 100.0
            actual_outcome = 1.0 if outcome == "showed" else 0.0
            reanalysis['prediction_accuracy'] = 1.0 - abs(predicted_prob - actual_outcome)
        
        await db.appointment_reanalyses.insert_one(reanalysis)
        
        # Update lead with this analysis
        await db.leads.update_one(
            {"id": lead_id},
            {
                "$push": {"analysis_history": reanalysis['id']},
                "$set": {
                    "last_analysis_id": reanalysis['id'],
                    "last_analysis_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Check if campaign has auto_reanalyze enabled and trigger campaign update
        if lead.get('campaign_id'):
            campaign = await db.campaigns.find_one({"id": lead['campaign_id']})
            if campaign and campaign.get('auto_reanalyze_on_appointment_update'):
                logger.info(f"Triggering campaign re-analysis for {lead['campaign_id']} due to appointment update")
                # The actual campaign re-analysis would be triggered here
                # For now, just log it
        
        logger.info(f"Created re-analysis {reanalysis['id']} for appointment {appt_id}")
        
        return {
            "success": True,
            "reanalysis_id": reanalysis['id'],
            "outcome": outcome,
            "prediction_accuracy": reanalysis['prediction_accuracy']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering re-analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@crm_router.get("/leads/{lead_id}/call-history")
async def get_lead_call_history(
    lead_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get complete call history for a lead with all analyses"""
    lead = await db.leads.find_one({"id": lead_id, "user_id": current_user['id']})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    call_ids = lead.get('call_history', [])
    
    # Fetch all calls
    calls = []
    for call_id in call_ids:
        call = await db.call_logs.find_one({"call_id": call_id, "user_id": current_user['id']})
        if call:
            if '_id' in call:
                call['_id'] = str(call['_id'])
            
            # Get analysis for this call
            analysis = await db.call_analytics.find_one({
                "call_id": call_id,
                "user_id": current_user['id']
            })
            if analysis:
                if '_id' in analysis:
                    del analysis['_id']
                call['qc_analysis'] = analysis
            
            calls.append(call)
    
    return {
        "lead_id": lead_id,
        "total_calls": len(calls),
        "calls": calls
    }


# ============ AUTO LEAD CREATION FROM CALLS ============

@crm_router.post("/leads/from-call")
async def create_lead_from_call(
    call_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Auto-create a lead from a call if CRM integration is enabled.
    Called after a call completes if campaign.auto_create_leads is True.
    """
    try:
        call_id = call_data.get('call_id')
        phone = call_data.get('phone')
        campaign_id = call_data.get('campaign_id')
        agent_id = call_data.get('agent_id')
        
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number required")
        
        # Check if lead already exists with this phone
        existing_lead = await db.leads.find_one({
            "phone": phone,
            "user_id": current_user['id']
        })
        
        if existing_lead:
            # Update existing lead
            await db.leads.update_one(
                {"id": existing_lead['id']},
                {
                    "$push": {"call_history": call_id},
                    "$inc": {"total_calls": 1},
                    "$set": {
                        "last_agent_id": agent_id,
                        "last_contact": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            logger.info(f"Updated existing lead {existing_lead['id']} with new call {call_id}")
            return {
                "success": True,
                "lead_id": existing_lead['id'],
                "is_new": False
            }
        
        # Create new lead
        lead = Lead(
            user_id=current_user['id'],
            name=call_data.get('caller_name', f"Lead {phone[-4:]}"),
            phone=phone,
            source=LeadSource.OUTBOUND_CALL if call_data.get('direction') == 'outbound' else LeadSource.INBOUND_CALL,
            status=LeadStatus.CONTACTED,
            category="new_first_call",
            campaign_id=campaign_id,
            last_agent_id=agent_id,
            total_calls=1,
            call_history=[call_id],
            last_contact=datetime.utcnow()
        )
        
        await db.leads.insert_one(lead.dict())
        logger.info(f"Auto-created lead {lead.id} from call {call_id}")
        
        return {
            "success": True,
            "lead_id": lead.id,
            "is_new": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating lead from call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
