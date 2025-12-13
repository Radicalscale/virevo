"""
QC Agent Router - Custom QC Agent System API

This module provides REST API endpoints for managing QC Agents:
- CRUD operations for QC Agents
- Knowledge Base management
- QC Agent assignments to Call Agents/Campaigns
- Tech Issues analysis and solution generation
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json
import uuid
import httpx

from auth_middleware import get_current_user
from qc_agent_models import (
    QCAgent, QCAgentCreate, QCAgentUpdate, QCAgentTypeEnum, QCAgentMode,
    QCAgentKBItem, QCAgentAssignment,
    TechIssueSolution, ElevenLabsEmotionalDirections,
    TrainingCall, LeadCategoryEnum, LeadMetrics
)

logger = logging.getLogger(__name__)

qc_agent_router = APIRouter(prefix="/qc/agents", tags=["QC Agents"])

# Database injection
db = None

def set_db(database):
    global db
    db = database


# ============================================================================
# QC AGENT CRUD ENDPOINTS
# ============================================================================

@qc_agent_router.post("", response_model=dict)
async def create_qc_agent(
    agent_data: QCAgentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new QC Agent"""
    try:
        # Create the QC Agent
        qc_agent = QCAgent(
            user_id=current_user['id'],
            name=agent_data.name,
            description=agent_data.description,
            agent_type=agent_data.agent_type,
            mode=agent_data.mode,
            llm_provider=agent_data.llm_provider,
            llm_model=agent_data.llm_model,
            analysis_rules=agent_data.analysis_rules,
            system_prompt=agent_data.system_prompt,
            analysis_focus=agent_data.analysis_focus,
            custom_criteria=agent_data.custom_criteria,
            output_format_instructions=agent_data.output_format_instructions,
            elevenlabs_settings=agent_data.elevenlabs_settings
        )
        
        await db.qc_agents.insert_one(qc_agent.dict())
        
        logger.info(f"Created QC Agent: {qc_agent.id} ({qc_agent.agent_type}) for user {current_user['id']}")
        
        # Return without _id
        result = qc_agent.dict()
        return result
    
    except Exception as e:
        logger.error(f"Error creating QC Agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.get("", response_model=List[dict])
async def list_qc_agents(
    agent_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List all QC Agents for current user"""
    try:
        query = {"user_id": current_user['id']}
        
        if agent_type:
            query["agent_type"] = agent_type
        
        agents = await db.qc_agents.find(query).to_list(length=100)
        
        # Convert ObjectId to string and add patterns count
        for agent in agents:
            if '_id' in agent:
                agent['_id'] = str(agent['_id'])
            
            # Get patterns count from synced campaign
            synced_campaign_id = agent.get('synced_campaign_id')
            if synced_campaign_id:
                patterns_count = await db.campaign_patterns.count_documents({
                    "campaign_id": synced_campaign_id
                })
                agent['patterns_count'] = patterns_count
            else:
                agent['patterns_count'] = agent.get('campaign_patterns_count', 0)
        
        logger.info(f"Listed {len(agents)} QC Agents for user {current_user['id']}")
        return agents
    
    except Exception as e:
        logger.error(f"Error listing QC Agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.get("/by-type/{agent_type}", response_model=List[dict])
async def list_qc_agents_by_type(
    agent_type: str,
    current_user: dict = Depends(get_current_user)
):
    """List QC Agents filtered by type (tonality, language_pattern, tech_issues, generic)"""
    try:
        agents = await db.qc_agents.find({
            "user_id": current_user['id'],
            "agent_type": agent_type
        }).to_list(length=100)
        
        for agent in agents:
            if '_id' in agent:
                agent['_id'] = str(agent['_id'])
        
        return agents
    
    except Exception as e:
        logger.error(f"Error listing QC Agents by type: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.get("/{agent_id}", response_model=dict)
async def get_qc_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific QC Agent"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        if '_id' in agent:
            agent['_id'] = str(agent['_id'])
        
        # Get patterns count from synced campaign
        synced_campaign_id = agent.get('synced_campaign_id')
        if synced_campaign_id:
            patterns_count = await db.campaign_patterns.count_documents({
                "campaign_id": synced_campaign_id
            })
            agent['patterns_count'] = patterns_count
        else:
            agent['patterns_count'] = agent.get('campaign_patterns_count', 0)
        
        return agent
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting QC Agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.put("/{agent_id}", response_model=dict)
async def update_qc_agent(
    agent_id: str,
    updates: QCAgentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a QC Agent"""
    try:
        # Verify ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Build update dict
        update_data = {k: v for k, v in updates.dict(exclude_unset=True).items() if v is not None}
        update_data['updated_at'] = datetime.utcnow()
        
        await db.qc_agents.update_one(
            {"id": agent_id, "user_id": current_user['id']},
            {"$set": update_data}
        )
        
        # Get updated agent
        updated_agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if '_id' in updated_agent:
            updated_agent['_id'] = str(updated_agent['_id'])
        
        logger.info(f"Updated QC Agent: {agent_id}")
        return updated_agent
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating QC Agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.delete("/{agent_id}")
async def delete_qc_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a QC Agent"""
    try:
        # Verify ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Delete agent and related data
        await db.qc_agents.delete_one({"id": agent_id, "user_id": current_user['id']})
        await db.qc_agent_kb.delete_many({"qc_agent_id": agent_id})
        await db.qc_agent_assignments.delete_many({"qc_agent_id": agent_id})
        
        logger.info(f"Deleted QC Agent: {agent_id}")
        return {"success": True, "message": "QC Agent deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting QC Agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# QC AGENT KNOWLEDGE BASE ENDPOINTS
# ============================================================================

@qc_agent_router.post("/{agent_id}/kb")
async def upload_qc_agent_kb(
    agent_id: str,
    file: UploadFile = File(...),
    description: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload knowledge base file to QC Agent"""
    try:
        # Verify ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Read file content
        content = await file.read()
        content_text = content.decode('utf-8', errors='ignore')
        
        # Create KB item
        kb_item = QCAgentKBItem(
            qc_agent_id=agent_id,
            source_type="file",
            source_name=file.filename,
            content=content_text,
            description=description,
            file_size=len(content)
        )
        
        await db.qc_agent_kb.insert_one(kb_item.dict())
        
        # Update agent's KB item list
        await db.qc_agents.update_one(
            {"id": agent_id},
            {"$push": {"kb_items": kb_item.id}}
        )
        
        logger.info(f"Uploaded KB to QC Agent {agent_id}: {file.filename}")
        
        return {
            "success": True,
            "kb_item_id": kb_item.id,
            "filename": file.filename,
            "size": len(content)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.get("/{agent_id}/kb")
async def list_qc_agent_kb(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List knowledge base items for QC Agent"""
    try:
        # Verify ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        kb_items = await db.qc_agent_kb.find({
            "qc_agent_id": agent_id
        }).to_list(length=100)
        
        for item in kb_items:
            if '_id' in item:
                item['_id'] = str(item['_id'])
            # Don't return full content in list view
            if 'content' in item:
                item['content_preview'] = item['content'][:200] + "..." if len(item['content']) > 200 else item['content']
                del item['content']
        
        return kb_items
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.delete("/{agent_id}/kb/{kb_item_id}")
async def delete_qc_agent_kb(
    agent_id: str,
    kb_item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete knowledge base item from QC Agent"""
    try:
        # Verify ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Delete KB item
        result = await db.qc_agent_kb.delete_one({
            "id": kb_item_id,
            "qc_agent_id": agent_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="KB item not found")
        
        # Remove from agent's KB list
        await db.qc_agents.update_one(
            {"id": agent_id},
            {"$pull": {"kb_items": kb_item_id}}
        )
        
        return {"success": True, "message": "KB item deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PATTERN MD UPLOAD
# ============================================================================

@qc_agent_router.get("/{agent_id}/patterns")
async def get_qc_agent_patterns(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get patterns synced to this QC Agent from campaigns"""
    try:
        # Verify ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Get patterns from synced campaign
        synced_campaign_id = agent.get('synced_campaign_id')
        patterns = []
        
        if synced_campaign_id:
            patterns_raw = await db.campaign_patterns.find({
                "campaign_id": synced_campaign_id
            }).to_list(length=100)
            
            for p in patterns_raw:
                if '_id' in p:
                    p['_id'] = str(p['_id'])
                patterns.append(p)
        
        return {
            "agent_id": agent_id,
            "agent_name": agent.get('name'),
            "synced_campaign_id": synced_campaign_id,
            "patterns_count": len(patterns),
            "patterns": patterns,
            "pattern_md_content": agent.get('pattern_md_content'),
            "pattern_md_updated_at": agent.get('pattern_md_updated_at')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting QC Agent patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.post("/{agent_id}/pattern-md")
async def upload_pattern_md(
    agent_id: str,
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Upload pattern MD from campaign analysis to QC Agent"""
    try:
        # Verify ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        pattern_md = request_data.get('pattern_md', '')
        
        await db.qc_agents.update_one(
            {"id": agent_id},
            {
                "$set": {
                    "pattern_md_content": pattern_md,
                    "pattern_md_updated_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Uploaded pattern MD to QC Agent {agent_id}")
        return {"success": True, "message": "Pattern MD uploaded"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading pattern MD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# QC AGENT ASSIGNMENTS
# ============================================================================

@qc_agent_router.post("/assign")
async def assign_qc_agent(
    assignment_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Assign QC Agent to a Call Agent or Campaign"""
    try:
        qc_agent_id = assignment_data.get('qc_agent_id')
        call_agent_id = assignment_data.get('call_agent_id')
        campaign_id = assignment_data.get('campaign_id')
        auto_analyze = assignment_data.get('auto_analyze', False)
        analysis_types = assignment_data.get('analysis_types', ['all'])
        
        # Verify QC Agent ownership
        qc_agent = await db.qc_agents.find_one({
            "id": qc_agent_id,
            "user_id": current_user['id']
        })
        
        if not qc_agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Verify target ownership
        if call_agent_id:
            call_agent = await db.agents.find_one({
                "id": call_agent_id,
                "user_id": current_user['id']
            })
            if not call_agent:
                raise HTTPException(status_code=404, detail="Call Agent not found")
        
        if campaign_id:
            campaign = await db.campaigns.find_one({
                "id": campaign_id,
                "user_id": current_user['id']
            })
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Create assignment
        assignment = QCAgentAssignment(
            qc_agent_id=qc_agent_id,
            call_agent_id=call_agent_id,
            campaign_id=campaign_id,
            auto_analyze=auto_analyze,
            analysis_types=analysis_types
        )
        
        # Upsert (replace existing assignment for same target)
        filter_query = {"qc_agent_id": qc_agent_id}
        if call_agent_id:
            filter_query["call_agent_id"] = call_agent_id
        if campaign_id:
            filter_query["campaign_id"] = campaign_id
        
        await db.qc_agent_assignments.update_one(
            filter_query,
            {"$set": assignment.dict()},
            upsert=True
        )
        
        logger.info(f"Assigned QC Agent {qc_agent_id} to {'call_agent ' + call_agent_id if call_agent_id else 'campaign ' + campaign_id}")
        return {"success": True, "assignment_id": assignment.id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning QC Agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.get("/assignments")
async def list_qc_agent_assignments(
    qc_agent_id: Optional[str] = None,
    call_agent_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List QC Agent assignments"""
    try:
        # Build query - filter by user's QC agents
        user_qc_agents = await db.qc_agents.find(
            {"user_id": current_user['id']},
            {"id": 1}
        ).to_list(length=100)
        
        user_qc_agent_ids = [a['id'] for a in user_qc_agents]
        
        query = {"qc_agent_id": {"$in": user_qc_agent_ids}}
        
        if qc_agent_id:
            query["qc_agent_id"] = qc_agent_id
        if call_agent_id:
            query["call_agent_id"] = call_agent_id
        if campaign_id:
            query["campaign_id"] = campaign_id
        
        assignments = await db.qc_agent_assignments.find(query).to_list(length=100)
        
        for assignment in assignments:
            if '_id' in assignment:
                assignment['_id'] = str(assignment['_id'])
        
        return assignments
    
    except Exception as e:
        logger.error(f"Error listing assignments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.delete("/assignments/{assignment_id}")
async def delete_qc_agent_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a QC Agent assignment"""
    try:
        # Get assignment
        assignment = await db.qc_agent_assignments.find_one({"id": assignment_id})
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        # Verify user owns the QC agent
        qc_agent = await db.qc_agents.find_one({
            "id": assignment['qc_agent_id'],
            "user_id": current_user['id']
        })
        
        if not qc_agent:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        await db.qc_agent_assignments.delete_one({"id": assignment_id})
        
        return {"success": True, "message": "Assignment deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting assignment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ELEVENLABS EMOTIONAL DIRECTIONS
# ============================================================================

@qc_agent_router.post("/{agent_id}/emotional-directions")
async def generate_emotional_directions(
    agent_id: str,
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Generate ElevenLabs emotional directions for a transcript"""
    try:
        # Verify ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id'],
            "agent_type": "tonality"
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Tonality QC Agent not found")
        
        transcript = request_data.get('transcript', [])
        custom_guidelines = request_data.get('custom_guidelines', '')
        
        if not transcript:
            raise HTTPException(status_code=400, detail="Transcript required")
        
        # Get API key
        api_key = await get_user_api_key(current_user['id'], agent.get('llm_provider', 'grok'))
        
        if not api_key:
            raise HTTPException(status_code=400, detail="No API key configured for LLM provider")
        
        # Generate emotional directions using LLM
        directions = await generate_elevenlabs_directions(
            transcript,
            custom_guidelines,
            api_key,
            agent.get('llm_provider', 'grok'),
            agent.get('llm_model', 'grok-3')
        )
        
        return directions
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating emotional directions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_elevenlabs_directions(
    transcript: List[dict],
    custom_guidelines: str,
    api_key: str,
    llm_provider: str,
    llm_model: str
) -> dict:
    """Generate ElevenLabs emotional directions from transcript analysis"""
    
    # Build conversation text
    conversation_text = "\n".join([
        f"{msg.get('role', 'unknown')}: {msg.get('content', '') or msg.get('text', '')}"
        for msg in transcript
    ])
    
    analysis_prompt = f"""You are an expert in voice AI delivery and ElevenLabs TTS optimization.
Analyze this conversation and generate detailed emotional delivery directions.

**Conversation:**
{conversation_text}

{f"**Custom Guidelines:** {custom_guidelines}" if custom_guidelines else ""}

**Generate the following for EACH agent response:**

1. **Emotion Tags** - What emotions should be conveyed (warm, confident, empathetic, urgent, etc.)
2. **Pacing Instructions** - Speed variations (slow down for emphasis, speed up for energy)
3. **Emphasis Words** - Specific words to emphasize
4. **Tone Description** - Overall vocal quality
5. **Line-by-Line Directions** - Detailed per-sentence delivery instructions
6. **Prosody XML** - SSML/prosody markup for ElevenLabs

**ElevenLabs Best Practices:**
- Use [pause] or ... for natural pauses
- Use *emphasis* for words to stress
- Describe emotions in delivery instructions
- Consider pitch, rate, volume for each phrase

Return JSON:
{{
  "emotion_tags": ["warm", "professional"],
  "pacing_instructions": "Moderate pace with slowing on key benefits",
  "emphasis_words": ["important", "guarantee", "today"],
  "tone_description": "Warm and confident sales professional",
  "line_by_line_directions": [
    {{
      "line": "First agent line here",
      "delivery": "Start warm and welcoming, slight smile in voice",
      "pace": "moderate",
      "emotion": "friendly"
    }}
  ],
  "prosody_xml": "<prosody rate='medium' pitch='medium'>...</prosody>",
  "copyable_prompt": "Full delivery instruction text that can be pasted into node prompt"
}}"""
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if llm_provider == "grok":
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-3",
                        "messages": [
                            {"role": "system", "content": "You are an expert voice delivery coach for AI TTS systems. Generate detailed, actionable delivery instructions in JSON format."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        "temperature": 0.3
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    analysis_text = result['choices'][0]['message']['content']
                    
                    # Parse JSON
                    if '```json' in analysis_text:
                        analysis_text = analysis_text.split('```json')[1].split('```')[0]
                    elif '```' in analysis_text:
                        analysis_text = analysis_text.split('```')[1].split('```')[0]
                    
                    return json.loads(analysis_text.strip())
                else:
                    logger.error(f"LLM API error: {response.status_code}")
                    return {"error": "LLM API error", "status": response.status_code}
                    
    except Exception as e:
        logger.error(f"Error in generate_elevenlabs_directions: {str(e)}")
        return {"error": str(e)}


# ============================================================================
# TECH ISSUES ANALYSIS
# ============================================================================

@qc_agent_router.post("/{agent_id}/analyze-tech-issues")
async def analyze_tech_issues(
    agent_id: str,
    request_data: dict,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Analyze call logs for tech issues and generate solution MD"""
    try:
        # Verify ownership and type
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id'],
            "agent_type": "tech_issues"
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Tech Issues QC Agent not found")
        
        call_id = request_data.get('call_id')
        call_logs = request_data.get('call_logs', [])
        include_code_analysis = request_data.get('include_code_analysis', False)
        
        if not call_id:
            raise HTTPException(status_code=400, detail="call_id required")
        
        # Get call data
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": current_user['id']},
                {"id": call_id, "user_id": current_user['id']}
            ]
        })
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Use call logs from request or from call record
        logs_to_analyze = call_logs or call.get('logs', [])
        
        # Get API key
        api_key = await get_user_api_key(current_user['id'], agent.get('llm_provider', 'grok'))
        
        if not api_key:
            raise HTTPException(status_code=400, detail="No API key configured for LLM provider")
        
        # Run tech analysis
        solution = await analyze_tech_issues_with_llm(
            call_id=call_id,
            logs=logs_to_analyze,
            agent=agent,
            api_key=api_key,
            include_code_analysis=include_code_analysis
        )
        
        # Store solution
        solution['user_id'] = current_user['id']
        solution['qc_agent_id'] = agent_id
        await db.tech_issue_solutions.insert_one(solution)
        
        # Update agent stats
        await db.qc_agents.update_one(
            {"id": agent_id},
            {
                "$inc": {"analyses_run": 1},
                "$set": {"last_analysis_at": datetime.utcnow()}
            }
        )
        
        logger.info(f"Tech issues analysis complete for call {call_id}")
        return solution
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in tech issues analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_tech_issues_with_llm(
    call_id: str,
    logs: List[dict],
    agent: dict,
    api_key: str,
    include_code_analysis: bool = False
) -> dict:
    """Analyze call logs and generate tech issue solutions"""
    
    # Format logs for analysis
    log_text = "\n".join([
        f"[{log.get('timestamp', '')}] {log.get('level', 'INFO')}: {log.get('message', '')}"
        for log in logs
    ])
    
    analysis_prompt = f"""You are an expert technical analyst for voice AI systems.
Analyze these call logs and identify any technical issues.

**Call ID:** {call_id}

**Logs:**
{log_text[:10000]}  # Limit log length

**Classify the issue as one of:**
- system: Infrastructure or code bug
- prompt: Agent prompt needs modification
- multi_agent: Needs multi-agent architecture
- optimize_prompt: Use optimize prompt feature
- optimize_transition: Use optimize transition feature
- node_split: Break prompt into multiple nodes
- combination: Multiple fixes needed

**For each issue provide:**
1. Clear problem description
2. Severity (critical/high/medium/low)
3. Specific solution steps
4. If code change needed: provide step-by-step fix instructions
5. If prompt change needed: provide the improved prompt

Return JSON:
{{
  "issue_type": "system|prompt|multi_agent|optimize_prompt|optimize_transition|node_split|combination",
  "issue_description": "Clear description of what's wrong",
  "severity": "critical|high|medium|low",
  "affected_components": ["component1", "component2"],
  "root_cause_analysis": "Why this is happening",
  "script_reconfiguration_md": "# Agent/Prompt Changes\\n\\n## Issue\\n...\\n## Solution\\n...",
  "code_enhancement_md": "# Code Fix Guide\\n\\n## Problem\\n...\\n## Files to Modify\\n...\\n## Step-by-Step Fix\\n...",
  "ai_coder_prompt": "Complete prompt that can be given to an AI coder to fix the issue with all necessary context",
  "recommendations": ["recommendation1", "recommendation2"],
  "quick_fixes": ["quick fix 1", "quick fix 2"]
}}"""
    
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": agent.get('llm_model', 'grok-3'),
                    "messages": [
                        {"role": "system", "content": "You are an expert technical analyst. Provide detailed, actionable solutions in JSON format."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    "temperature": 0.2
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result['choices'][0]['message']['content']
                
                # Parse JSON
                if '```json' in analysis_text:
                    analysis_text = analysis_text.split('```json')[1].split('```')[0]
                elif '```' in analysis_text:
                    analysis_text = analysis_text.split('```')[1].split('```')[0]
                
                solution_data = json.loads(analysis_text.strip())
                
                # Build solution object
                solution = {
                    "id": str(uuid.uuid4()),
                    "call_id": call_id,
                    "issue_type": solution_data.get('issue_type', 'unknown'),
                    "issue_description": solution_data.get('issue_description', ''),
                    "severity": solution_data.get('severity', 'medium'),
                    "affected_files": solution_data.get('affected_components', []),
                    "affected_nodes": [],
                    "log_analysis": {
                        "total_logs": len(logs),
                        "root_cause": solution_data.get('root_cause_analysis', '')
                    },
                    "script_reconfiguration_md": solution_data.get('script_reconfiguration_md'),
                    "code_enhancement_md": solution_data.get('code_enhancement_md'),
                    "ai_coder_prompt": solution_data.get('ai_coder_prompt'),
                    "recommendations": solution_data.get('recommendations', []),
                    "quick_fixes": solution_data.get('quick_fixes', []),
                    "created_at": datetime.utcnow().isoformat()
                }
                
                return solution
            else:
                logger.error(f"LLM API error: {response.status_code}")
                return {"error": "LLM API error", "call_id": call_id}
                
    except Exception as e:
        logger.error(f"Error in analyze_tech_issues_with_llm: {str(e)}")
        return {"error": str(e), "call_id": call_id}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_user_api_key(user_id: str, service_name: str) -> Optional[str]:
    """Get user-specific API key for a service"""
    from key_encryption import decrypt_api_key
    
    try:
        # Map service names to key patterns
        key_patterns = {
            'grok': 'xai-',
            'openai': 'sk-',
            'anthropic': 'sk-ant-'
        }
        
        # Try direct service name match first
        key_doc = await db.api_keys.find_one({
            "user_id": user_id,
            "$or": [
                {"service_name": service_name, "is_active": True},
                {"provider": service_name, "is_active": True}
            ]
        })
        
        if not key_doc and service_name in key_patterns:
            # Try to find by key pattern
            pattern = key_patterns[service_name]
            all_keys = await db.api_keys.find({"user_id": user_id}).to_list(length=None)
            for k in all_keys:
                api_key = k.get('api_key', '')
                if api_key.startswith(pattern):
                    key_doc = k
                    break
        
        if not key_doc:
            return None
        
        # Decrypt if encrypted
        if key_doc.get('encrypted_key'):
            return decrypt_api_key(key_doc['encrypted_key'])
        return key_doc.get('api_key')
    
    except Exception as e:
        logger.error(f"Error getting API key: {str(e)}")
        return None


# ============================================================================
# AI INTERRUPTION SYSTEM ENDPOINTS
# ============================================================================

@qc_agent_router.post("/interruption/check")
async def check_interruption(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if the AI should interrupt the user (rambler detection).
    
    Request body:
    {
        "user_text": "The user's current speech",
        "conversation_context": [{"role": "user/agent", "content": "..."}],
        "node_goal": "What this conversation node is trying to achieve",
        "duration_seconds": 15.0,
        "framework": "default" or "contextual"
    }
    """
    try:
        from interruption_system import (
            check_for_interruption,
            InterruptionConfig
        )
        
        user_text = request_data.get('user_text', '')
        conversation_context = request_data.get('conversation_context', [])
        node_goal = request_data.get('node_goal', '')
        duration_seconds = request_data.get('duration_seconds', 0.0)
        framework = request_data.get('framework', 'default')
        
        if not user_text:
            raise HTTPException(status_code=400, detail="user_text required")
        
        # Get API key for contextual framework
        api_key = None
        if framework == "contextual":
            api_key = await get_user_api_key(current_user['id'], 'grok')
        
        # Create config
        config = InterruptionConfig(
            enabled=True,
            framework=framework,
            word_count_threshold=request_data.get('word_count_threshold', 100),
            duration_threshold_seconds=request_data.get('duration_threshold', 30),
            use_llm_for_context=(framework == "contextual" and api_key is not None)
        )
        
        # Check for interruption
        decision = await check_for_interruption(
            user_text=user_text,
            conversation_context=conversation_context,
            node_goal=node_goal,
            duration_seconds=duration_seconds,
            config=config,
            api_key=api_key
        )
        
        logger.info(f"Interruption check: should_interrupt={decision.should_interrupt}, reason={decision.reason}")
        
        return {
            "should_interrupt": decision.should_interrupt,
            "reason": decision.reason,
            "interruption_phrase": decision.interruption_phrase,
            "confidence": decision.confidence,
            "detected_issues": decision.detected_issues,
            "context_leverage": decision.context_leverage
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in interruption check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_agent_router.get("/interruption/phrases")
async def get_default_interruption_phrases(
    current_user: dict = Depends(get_current_user)
):
    """Get the default interruption phrases"""
    from interruption_system import InterruptionConfig
    
    config = InterruptionConfig()
    return {
        "phrases": config.default_phrases,
        "thresholds": {
            "word_count": config.word_count_threshold,
            "duration_seconds": config.duration_threshold_seconds,
            "off_topic_confidence": config.off_topic_confidence_threshold
        }
    }


@qc_agent_router.put("/interruption/phrases")
async def update_interruption_phrases(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update user's custom interruption phrases"""
    try:
        phrases = request_data.get('phrases', [])
        thresholds = request_data.get('thresholds', {})
        
        # Store in user settings
        await db.user_settings.update_one(
            {"user_id": current_user['id']},
            {
                "$set": {
                    "interruption_phrases": phrases,
                    "interruption_thresholds": thresholds,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return {"success": True, "message": "Interruption settings updated"}
    
    except Exception as e:
        logger.error(f"Error updating interruption phrases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
