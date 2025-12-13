"""
QC Learning Router - API Endpoints for Learning System

Endpoints for:
- Playbook management (CRUD, versioning)
- Learning control (trigger, configure)
- Analysis logging with predictions
- Brain prompts (view/edit)
- Stats and insights
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from auth_middleware import get_current_user
from qc_learning_models import (
    QCPlaybook, PlaybookContent, QCAnalysisLog, LearnedPattern,
    LearningSession, LearningConfig, LearningMode, OutcomeType,
    AnalysisPrediction, get_default_playbook_content,
    BrainPrompts, get_default_brain_prompts
)
from qc_learning_service import (
    LearningOrchestrator, create_initial_playbook,
    log_qc_analysis, update_analysis_outcome, set_db
)

logger = logging.getLogger(__name__)

qc_learning_router = APIRouter(prefix="/qc/learning", tags=["QC Learning"])

# Database injection
db = None

def set_learning_db(database):
    global db
    db = database
    set_db(database)


# ============================================================================
# PLAYBOOK ENDPOINTS
# ============================================================================

@qc_learning_router.get("/agents/{agent_id}/playbook")
async def get_current_playbook(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the current active playbook for a QC agent"""
    try:
        # Verify agent ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Get current playbook
        playbook = await db.qc_playbooks.find_one({
            "qc_agent_id": agent_id,
            "is_current": True
        })
        
        if not playbook:
            # Create initial playbook
            agent_type = agent.get('agent_type', 'language_pattern')
            initial = await create_initial_playbook(
                qc_agent_id=agent_id,
                user_id=current_user['id'],
                agent_type=agent_type
            )
            await db.qc_playbooks.insert_one(initial.dict())
            playbook = initial.dict()
        
        if '_id' in playbook:
            playbook['_id'] = str(playbook['_id'])
        
        return playbook
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.put("/agents/{agent_id}/playbook")
async def update_playbook(
    agent_id: str,
    playbook_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update/edit the current playbook (user tweaks)"""
    try:
        # Verify agent ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Get current playbook
        current = await db.qc_playbooks.find_one({
            "qc_agent_id": agent_id,
            "is_current": True
        })
        
        if not current:
            raise HTTPException(status_code=404, detail="No playbook found")
        
        # Update the playbook content
        update_fields = {
            "updated_at": datetime.now(timezone.utc),
            "user_edited": True,
            "last_edited_by": "user"
        }
        
        # Update content if provided
        if 'content' in playbook_data:
            content = playbook_data['content']
            if isinstance(content, dict):
                # Update specific fields
                for key in ['philosophy', 'pre_analysis_checklist', 'victory_patterns', 
                           'defeat_patterns', 'campaign_patterns', 'anti_patterns',
                           'scoring_calibration', 'raw_markdown']:
                    if key in content:
                        update_fields[f'content.{key}'] = content[key]
        
        # Allow direct raw_markdown update
        if 'raw_markdown' in playbook_data:
            update_fields['content.raw_markdown'] = playbook_data['raw_markdown']
        
        await db.qc_playbooks.update_one(
            {"id": current['id']},
            {"$set": update_fields}
        )
        
        # Get updated playbook
        updated = await db.qc_playbooks.find_one({"id": current['id']})
        if '_id' in updated:
            updated['_id'] = str(updated['_id'])
        
        return updated
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating playbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.get("/agents/{agent_id}/playbook/history")
async def get_playbook_history(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all playbook versions for a QC agent"""
    try:
        # Verify agent ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Get all playbooks sorted by version
        playbooks = await db.qc_playbooks.find({
            "qc_agent_id": agent_id
        }).sort("version", -1).to_list(length=50)
        
        # Clean up for response
        for p in playbooks:
            if '_id' in p:
                p['_id'] = str(p['_id'])
            # Don't include full content in list view
            if 'content' in p and 'raw_markdown' in p['content']:
                p['content']['raw_markdown'] = p['content']['raw_markdown'][:500] + "..." if len(p['content'].get('raw_markdown', '')) > 500 else p['content'].get('raw_markdown', '')
        
        return playbooks
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playbook history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.get("/agents/{agent_id}/playbook/version/{version}")
async def get_playbook_version(
    agent_id: str,
    version: int,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific playbook version"""
    try:
        # Verify agent ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        playbook = await db.qc_playbooks.find_one({
            "qc_agent_id": agent_id,
            "version": version
        })
        
        if not playbook:
            raise HTTPException(status_code=404, detail=f"Playbook version {version} not found")
        
        if '_id' in playbook:
            playbook['_id'] = str(playbook['_id'])
        
        return playbook
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playbook version: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.post("/agents/{agent_id}/playbook/restore/{version}")
async def restore_playbook_version(
    agent_id: str,
    version: int,
    current_user: dict = Depends(get_current_user)
):
    """Restore a previous playbook version as current"""
    try:
        # Verify agent ownership
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Get the version to restore
        to_restore = await db.qc_playbooks.find_one({
            "qc_agent_id": agent_id,
            "version": version
        })
        
        if not to_restore:
            raise HTTPException(status_code=404, detail=f"Playbook version {version} not found")
        
        # Get current playbook
        current = await db.qc_playbooks.find_one({
            "qc_agent_id": agent_id,
            "is_current": True
        })
        
        # Set current to not current
        if current:
            await db.qc_playbooks.update_one(
                {"id": current['id']},
                {"$set": {"is_current": False}}
            )
        
        # Create new version from restored content
        new_version = (current['version'] + 1) if current else version + 1
        
        new_playbook = {
            **to_restore,
            "id": str(__import__('uuid').uuid4()),
            "version": new_version,
            "is_current": True,
            "is_auto_generated": False,
            "user_edited": True,
            "last_edited_by": "user",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        del new_playbook['_id']
        
        await db.qc_playbooks.insert_one(new_playbook)
        
        return {
            "success": True,
            "message": f"Restored version {version} as new version {new_version}",
            "new_version": new_version
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring playbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LEARNING CONTROL ENDPOINTS
# ============================================================================

@qc_learning_router.get("/agents/{agent_id}/config")
async def get_learning_config(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get learning configuration for a QC agent"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        config = agent.get('learning_config', {
            "mode": "manual",
            "trigger_count": 10,
            "is_enabled": True,
            "outcomes_since_last_learning": 0,
            "total_learning_sessions": 0
        })
        
        return config
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting learning config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.put("/agents/{agent_id}/config")
async def update_learning_config(
    agent_id: str,
    config_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update learning configuration for a QC agent"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Validate mode
        if 'mode' in config_data:
            if config_data['mode'] not in ['auto', 'every_x', 'manual']:
                raise HTTPException(status_code=400, detail="Invalid learning mode")
        
        # Build update
        update_fields = {}
        for key in ['mode', 'trigger_count', 'is_enabled']:
            if key in config_data:
                update_fields[f'learning_config.{key}'] = config_data[key]
        
        if update_fields:
            await db.qc_agents.update_one(
                {"id": agent_id},
                {"$set": update_fields}
            )
        
        # Get updated config
        updated_agent = await db.qc_agents.find_one({"id": agent_id})
        return updated_agent.get('learning_config', {})
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating learning config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.post("/agents/{agent_id}/learn")
async def trigger_learning(
    agent_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger a learning session"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Check agent type supports learning
        if agent.get('agent_type') == 'tech_issues':
            raise HTTPException(
                status_code=400, 
                detail="Tech Issues agents don't support learning"
            )
        
        # Run learning session
        orchestrator = LearningOrchestrator(db)
        session = await orchestrator.run_learning_session(
            qc_agent_id=agent_id,
            user_id=current_user['id'],
            trigger="manual"
        )
        
        if session.success:
            return {
                "success": True,
                "session_id": session.id,
                "message": f"Learning completed. Playbook updated to v{session.playbook_version_after}",
                "analyses_reviewed": session.analyses_reviewed_count,
                "patterns_identified": session.patterns_identified,
                "playbook_diff": session.playbook_diff_summary
            }
        else:
            return {
                "success": False,
                "session_id": session.id,
                "message": session.error_message
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering learning: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.get("/agents/{agent_id}/stats")
async def get_learning_stats(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get learning statistics for a QC agent"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        # Get analysis counts
        total_analyses = await db.qc_analysis_logs.count_documents({
            "qc_agent_id": agent_id
        })
        
        verified_outcomes = await db.qc_analysis_logs.count_documents({
            "qc_agent_id": agent_id,
            "actual_outcome": {"$in": ["showed", "no_show"]}
        })
        
        showed_count = await db.qc_analysis_logs.count_documents({
            "qc_agent_id": agent_id,
            "actual_outcome": "showed"
        })
        
        no_show_count = await db.qc_analysis_logs.count_documents({
            "qc_agent_id": agent_id,
            "actual_outcome": "no_show"
        })
        
        # Get pattern counts
        patterns_count = await db.qc_patterns.count_documents({
            "qc_agent_id": agent_id,
            "is_active": True
        })
        
        # Get current playbook accuracy
        current_playbook = await db.qc_playbooks.find_one({
            "qc_agent_id": agent_id,
            "is_current": True
        })
        
        playbook_accuracy = current_playbook.get('prediction_accuracy', 0) if current_playbook else 0
        playbook_version = current_playbook.get('version', 0) if current_playbook else 0
        
        # Get learning session count
        sessions_count = await db.qc_learning_sessions.count_documents({
            "qc_agent_id": agent_id
        })
        
        # Calculate average prediction accuracy
        accuracy_pipeline = [
            {"$match": {
                "qc_agent_id": agent_id,
                "prediction_accuracy": {"$exists": True, "$ne": None}
            }},
            {"$group": {
                "_id": None,
                "avg_accuracy": {"$avg": "$prediction_accuracy"}
            }}
        ]
        
        accuracy_result = await db.qc_analysis_logs.aggregate(accuracy_pipeline).to_list(1)
        avg_accuracy = accuracy_result[0]['avg_accuracy'] if accuracy_result else 0
        
        learning_config = agent.get('learning_config', {})
        
        return {
            "total_analyses": total_analyses,
            "verified_outcomes": verified_outcomes,
            "showed_count": showed_count,
            "no_show_count": no_show_count,
            "patterns_learned": patterns_count,
            "playbook_version": playbook_version,
            "playbook_accuracy": playbook_accuracy,
            "average_prediction_accuracy": avg_accuracy,
            "learning_sessions": sessions_count,
            "outcomes_since_last_learning": learning_config.get('outcomes_since_last_learning', 0),
            "learning_mode": learning_config.get('mode', 'manual'),
            "learning_enabled": learning_config.get('is_enabled', True)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting learning stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALYSIS LOG ENDPOINTS
# ============================================================================

@qc_learning_router.get("/agents/{agent_id}/analysis-logs")
async def get_analysis_logs(
    agent_id: str,
    limit: int = 50,
    outcome: Optional[str] = None,
    campaign_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get analysis logs for a QC agent"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        query = {"qc_agent_id": agent_id}
        
        if outcome:
            query["actual_outcome"] = outcome
        
        if campaign_id:
            query["campaign_id"] = campaign_id
        
        logs = await db.qc_analysis_logs.find(query).sort(
            "analyzed_at", -1
        ).to_list(length=limit)
        
        for log in logs:
            if '_id' in log:
                log['_id'] = str(log['_id'])
        
        return logs
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.put("/agents/{agent_id}/analysis-logs/{log_id}/outcome")
async def update_log_outcome(
    agent_id: str,
    log_id: str,
    outcome_data: dict,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Update the actual outcome for an analysis log"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        outcome = outcome_data.get('outcome')
        if outcome not in ['showed', 'no_show', 'rescheduled', 'cancelled']:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        
        success, accuracy = await update_analysis_outcome(
            log_id=log_id,
            outcome=OutcomeType(outcome),
            db_instance=db
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Analysis log not found")
        
        # Check if learning should trigger
        if agent.get('learning_config', {}).get('is_enabled', True):
            orchestrator = LearningOrchestrator(db)
            session = await orchestrator.check_and_trigger_learning(
                qc_agent_id=agent_id,
                user_id=current_user['id'],
                trigger_reason="outcome_update"
            )
            
            if session:
                return {
                    "success": True,
                    "prediction_accuracy": accuracy,
                    "learning_triggered": True,
                    "learning_session_id": session.id
                }
        
        return {
            "success": True,
            "prediction_accuracy": accuracy,
            "learning_triggered": False
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating log outcome: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PATTERNS ENDPOINTS
# ============================================================================

@qc_learning_router.get("/agents/{agent_id}/patterns")
async def get_patterns(
    agent_id: str,
    pattern_type: Optional[str] = None,
    campaign_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get learned patterns for a QC agent"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        query = {"qc_agent_id": agent_id, "is_active": True}
        
        if pattern_type:
            query["pattern_type"] = pattern_type
        
        if campaign_id:
            query["campaign_id"] = campaign_id
        
        patterns = await db.qc_patterns.find(query).sort(
            "impact_percentage", -1
        ).to_list(length=100)
        
        for p in patterns:
            if '_id' in p:
                p['_id'] = str(p['_id'])
        
        return patterns
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.delete("/agents/{agent_id}/patterns/{pattern_id}")
async def delete_pattern(
    agent_id: str,
    pattern_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Deactivate a learned pattern"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        result = await db.qc_patterns.update_one(
            {"id": pattern_id, "qc_agent_id": agent_id},
            {"$set": {"is_active": False}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        return {"success": True, "message": "Pattern deactivated"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pattern: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LEARNING SESSIONS ENDPOINTS
# ============================================================================

@qc_learning_router.get("/agents/{agent_id}/sessions")
async def get_learning_sessions(
    agent_id: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get learning session history for a QC agent"""
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        sessions = await db.qc_learning_sessions.find({
            "qc_agent_id": agent_id
        }).sort("started_at", -1).to_list(length=limit)
        
        for s in sessions:
            if '_id' in s:
                s['_id'] = str(s['_id'])
        
        return sessions
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting learning sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BRAIN PROMPTS ENDPOINTS
# ============================================================================

@qc_learning_router.get("/agents/{agent_id}/brain-prompts")
async def get_brain_prompts(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get brain prompts for a QC agent.
    Returns custom prompts if set, otherwise returns defaults for the agent type.
    """
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        agent_type = agent.get('agent_type', 'language_pattern')
        
        # Check if agent supports learning
        if agent_type == 'tech_issues':
            raise HTTPException(
                status_code=400, 
                detail="Tech Issues agents don't support learning/brain prompts"
            )
        
        # Get custom prompts or defaults
        custom_prompts = agent.get('brain_prompts')
        default_prompts = get_default_brain_prompts(agent_type)
        
        # If custom prompts exist, merge with defaults (custom overrides)
        if custom_prompts:
            result = {
                "is_customized": True,
                "prompts": {
                    "reflection_system_prompt": custom_prompts.get('reflection_system_prompt', default_prompts.reflection_system_prompt),
                    "reflection_prefix": custom_prompts.get('reflection_prefix', default_prompts.reflection_prefix),
                    "reflection_suffix": custom_prompts.get('reflection_suffix', default_prompts.reflection_suffix),
                    "training_system_prompt": custom_prompts.get('training_system_prompt', default_prompts.training_system_prompt),
                    "training_prefix": custom_prompts.get('training_prefix', default_prompts.training_prefix),
                    "training_suffix": custom_prompts.get('training_suffix', default_prompts.training_suffix),
                    "custom_instructions": custom_prompts.get('custom_instructions', default_prompts.custom_instructions),
                },
                "defaults": default_prompts.dict()
            }
        else:
            result = {
                "is_customized": False,
                "prompts": default_prompts.dict(),
                "defaults": default_prompts.dict()
            }
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting brain prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.put("/agents/{agent_id}/brain-prompts")
async def update_brain_prompts(
    agent_id: str,
    prompts_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update brain prompts for a QC agent.
    Pass null/empty to reset to defaults.
    """
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        agent_type = agent.get('agent_type', 'language_pattern')
        
        # Check if agent supports learning
        if agent_type == 'tech_issues':
            raise HTTPException(
                status_code=400, 
                detail="Tech Issues agents don't support learning/brain prompts"
            )
        
        # If reset_to_defaults is true, clear custom prompts
        if prompts_data.get('reset_to_defaults'):
            await db.qc_agents.update_one(
                {"id": agent_id},
                {"$set": {"brain_prompts": None}}
            )
            return {
                "success": True,
                "message": "Brain prompts reset to defaults",
                "prompts": get_default_brain_prompts(agent_type).dict()
            }
        
        # Otherwise update with custom prompts
        allowed_fields = [
            'reflection_system_prompt',
            'reflection_prefix',
            'reflection_suffix',
            'training_system_prompt',
            'training_prefix',
            'training_suffix',
            'custom_instructions'
        ]
        
        update_data = {}
        for field in allowed_fields:
            if field in prompts_data:
                update_data[field] = prompts_data[field]
        
        if update_data:
            # Merge with existing custom prompts
            existing = agent.get('brain_prompts') or {}
            merged = {**existing, **update_data}
            
            await db.qc_agents.update_one(
                {"id": agent_id},
                {"$set": {"brain_prompts": merged}}
            )
            
            return {
                "success": True,
                "message": "Brain prompts updated",
                "prompts": merged
            }
        else:
            return {
                "success": False,
                "message": "No valid fields to update"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating brain prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_learning_router.post("/agents/{agent_id}/brain-prompts/preview")
async def preview_brain_prompts(
    agent_id: str,
    preview_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Preview what the full prompt will look like with sample data.
    Useful for seeing how custom prompts combine with dynamic content.
    """
    try:
        agent = await db.qc_agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        if not agent:
            raise HTTPException(status_code=404, detail="QC Agent not found")
        
        agent_type = agent.get('agent_type', 'language_pattern')
        brain_type = preview_data.get('brain_type', 'reflection')  # 'reflection' or 'training'
        
        # Get prompts (custom or default)
        custom_prompts = agent.get('brain_prompts') or {}
        default_prompts = get_default_brain_prompts(agent_type)
        
        if brain_type == 'reflection':
            system_prompt = custom_prompts.get('reflection_system_prompt', default_prompts.reflection_system_prompt)
            prefix = custom_prompts.get('reflection_prefix', default_prompts.reflection_prefix)
            suffix = custom_prompts.get('reflection_suffix', default_prompts.reflection_suffix)
            
            # Sample dynamic content
            sample_dynamic = """## CURRENT ACCURACY
- Overall: 65.0%
- Showed predictions: 70.0% (10 samples)
- No-show predictions: 60.0% (8 samples)

## APPOINTMENTS THAT SHOWED (Success Cases)
[Sample data would appear here with risk factors, positive signals, scores]

## APPOINTMENTS THAT NO-SHOWED (Failure Cases)
[Sample data would appear here with risk factors, positive signals, scores]

## EXISTING PATTERNS (for reference)
[List of existing patterns]

## YOUR ANALYSIS TASK
1. VICTORY PATTERNS: What signals appear consistently in SHOWED appointments?
2. DEFEAT PATTERNS: What signals appear consistently in NO-SHOW appointments?
3. PREDICTION ERRORS: Where did our predictions go wrong?
4. CAMPAIGN PATTERNS: Any patterns specific to certain campaigns?
5. TRANSFERABLE INSIGHTS: What works across ALL contexts?

Return JSON with victory_patterns, defeat_patterns, campaign_patterns, etc."""
            
            full_prompt = f"{prefix}{sample_dynamic}{suffix}"
            
            return {
                "brain_type": "reflection",
                "system_prompt": system_prompt,
                "full_task_prompt": full_prompt,
                "sections": {
                    "prefix": prefix,
                    "dynamic_content": "[Generated based on analysis data]",
                    "suffix": suffix
                }
            }
        
        elif brain_type == 'training':
            system_prompt = custom_prompts.get('training_system_prompt', default_prompts.training_system_prompt)
            prefix = custom_prompts.get('training_prefix', default_prompts.training_prefix)
            suffix = custom_prompts.get('training_suffix', default_prompts.training_suffix)
            
            # Sample dynamic content
            sample_dynamic = """## LEARNED PATTERNS

### Victory Patterns (predict "showed"):
[List of patterns with signals and impacts]

### Defeat Patterns (predict "no-show"):
[List of patterns with signals and impacts]

### Campaign-Specific Patterns:
[Campaign-specific patterns]

## CURRENT ACCURACY
[Accuracy metrics]

## YOUR TASK
Create an updated playbook that prioritizes impactful patterns, provides clear guidance, includes checklists and anti-patterns.

Return JSON with philosophy, pre_analysis_checklist, victory_patterns, defeat_patterns, etc."""
            
            full_prompt = f"{prefix}{sample_dynamic}{suffix}"
            
            return {
                "brain_type": "training",
                "system_prompt": system_prompt,
                "full_task_prompt": full_prompt,
                "sections": {
                    "prefix": prefix,
                    "dynamic_content": "[Generated based on patterns and accuracy data]",
                    "suffix": suffix
                }
            }
        
        else:
            raise HTTPException(status_code=400, detail="brain_type must be 'reflection' or 'training'")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing brain prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
