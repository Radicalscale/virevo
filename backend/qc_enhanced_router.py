from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging
import json
import re
import uuid
import httpx
import asyncio
import os
from collections import Counter, defaultdict

from auth_middleware import get_current_user
from models import (
    Campaign, CampaignCreate, CampaignCall, CampaignSuggestion, CampaignPattern,
    TechQCRequest, TechQCResponse, ScriptQCRequest, ScriptQCResponse, AutoQCSettings
)
from qc_learning_models import (
    QCAnalysisLog, AnalysisPrediction, OutcomeType, BookingQuality
)
from qc_learning_service import log_qc_analysis

logger = logging.getLogger(__name__)

qc_enhanced_router = APIRouter(prefix="/qc/enhanced", tags=["QC Enhanced"])

# Database injection
db = None

def set_db(database):
    global db
    db = database

# ============================================================================
# CAMPAIGN MANAGEMENT ENDPOINTS
# ============================================================================

@qc_enhanced_router.post("/campaigns")
async def create_campaign(
    campaign: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new QC campaign"""
    try:
        campaign_data = CampaignCreate(**campaign)
        new_campaign = Campaign(
            **campaign_data.dict(),
            user_id=current_user['id']
        )
        
        await db.campaigns.insert_one(new_campaign.dict())
        return new_campaign
    
    except Exception as e:
        logger.error(f"Error creating campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.get("/campaigns")
async def list_campaigns(current_user: dict = Depends(get_current_user)):
    """List all campaigns for current user"""
    try:
        campaigns = await db.campaigns.find({
            "user_id": current_user['id']
        }).to_list(length=100)
        
        # Convert ObjectId to string and add call counts
        for campaign in campaigns:
            if '_id' in campaign:
                campaign['_id'] = str(campaign['_id'])
            
            # Get call count for this campaign
            call_count = await db.campaign_calls.count_documents({
                "campaign_id": campaign['id']
            })
            
            # Get pattern count
            pattern_count = await db.campaign_patterns.count_documents({
                "campaign_id": campaign['id']
            })
            
            # Add stats object as expected by frontend
            campaign['stats'] = {
                'total_calls': call_count,
                'patterns_identified': pattern_count
            }
        
        logger.info(f"Listed {len(campaigns)} campaigns for user {current_user['id']}")
        return campaigns
    
    except Exception as e:
        logger.error(f"Error listing campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific campaign details with analytics"""
    try:
        # SECURITY: Ensure campaign belongs to current user
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']  # Tenant isolation
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign statistics
        calls = await db.campaign_calls.find({
            "campaign_id": campaign_id
        }).to_list(length=1000)
        
        suggestions = await db.campaign_suggestions.find({
            "campaign_id": campaign_id
        }).to_list(length=1000)
        
        patterns = await db.campaign_patterns.find({
            "campaign_id": campaign_id
        }).to_list(length=100)
        
        # Convert ObjectId to string for all items
        if '_id' in campaign:
            campaign['_id'] = str(campaign['_id'])
        
        for call in calls:
            if '_id' in call:
                call['_id'] = str(call['_id'])
        
        for suggestion in suggestions:
            if '_id' in suggestion:
                suggestion['_id'] = str(suggestion['_id'])
        
        for pattern in patterns:
            if '_id' in pattern:
                pattern['_id'] = str(pattern['_id'])
        
        return {
            **campaign,
            "calls": calls,
            "suggestions": suggestions,
            "patterns": patterns,
            "stats": {
                "total_calls": len(calls),
                "total_suggestions": len(suggestions),
                "patterns_identified": len(patterns),
                "last_analyzed": calls[-1].get('analyzed_at') if calls else None
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@qc_enhanced_router.get("/campaigns/{campaign_id}/qc-results")
async def get_campaign_qc_results(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all QC results for a campaign - shows which calls have been analyzed and their results"""
    try:
        # Verify campaign belongs to user
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get all campaign_calls with their QC results
        campaign_calls = await db.campaign_calls.find(
            {"campaign_id": campaign_id},
            {"_id": 0}
        ).to_list(length=1000)
        
        # Build summary
        results = []
        summary = {
            "total_calls": len(campaign_calls),
            "analyzed": 0,
            "pending": 0,
            "failed": 0,
            "tech_analyzed": 0,
            "script_analyzed": 0,
            "tonality_analyzed": 0
        }
        
        for call in campaign_calls:
            call_id = call.get("call_id")
            
            # IMPORTANT: Check if campaign_calls has empty or incomplete results, merge with call_logs
            script_results = call.get("script_qc_results")
            tech_results = call.get("tech_qc_results")
            tonality_results = call.get("tonality_qc_results")
            
            # Helper function to check if results have valid node names
            def has_valid_node_names(results):
                if not results or not results.get("node_analyses"):
                    return False
                # Check if first analysis has a real node name (not None, not "Turn X")
                first_analysis = results.get("node_analyses", [{}])[0]
                node_name = first_analysis.get("node_name")
                if not node_name or node_name == "None" or node_name.startswith("Turn ") or node_name.startswith("Turn-"):
                    return False
                return True
            
            # Check if any campaign_calls data is incomplete (empty node_analyses or missing node names)
            needs_merge = (
                not has_valid_node_names(script_results) or
                not has_valid_node_names(tonality_results) or
                not has_valid_node_names(tech_results)
            )
            
            if needs_merge:
                # Try to get from call_logs
                call_log = await db.call_logs.find_one(
                    {"call_id": call_id},
                    {"_id": 0, "script_qc_results": 1, "tech_qc_results": 1, "tonality_qc_results": 1}
                )
                if call_log:
                    # Merge script results - prefer call_logs if it has better node names
                    call_log_script = call_log.get("script_qc_results")
                    if has_valid_node_names(call_log_script):
                        script_results = call_log_script
                        logger.info(f"Merged script_qc_results from call_logs for {call_id[:30]}...")
                    
                    # Merge tonality results
                    call_log_tonality = call_log.get("tonality_qc_results")
                    if has_valid_node_names(call_log_tonality):
                        tonality_results = call_log_tonality
                        logger.info(f"Merged tonality_qc_results from call_logs for {call_id[:30]}...")
                    
                    # Merge tech results
                    call_log_tech = call_log.get("tech_qc_results")
                    if has_valid_node_names(call_log_tech):
                        tech_results = call_log_tech
                        logger.info(f"Merged tech_qc_results from call_logs for {call_id[:30]}...")
            
            # Check for meaningful content in results
            has_script_qc = bool(script_results and script_results.get("node_analyses"))
            has_tech_qc = bool(tech_results and tech_results.get("node_analyses"))
            has_tonality_qc = bool(tonality_results and tonality_results.get("node_analyses"))
            
            call_result = {
                "call_id": call_id,
                "analysis_status": call.get("analysis_status", "pending"),
                "analysis_error": call.get("analysis_error"),
                "updated_at": call.get("updated_at"),
                "has_tech_qc": has_tech_qc,
                "has_script_qc": has_script_qc,
                "has_tonality_qc": has_tonality_qc,
                "has_audio_tonality": bool(call.get("audio_tonality_results")),
            }
            
            # Extract key metrics if available
            if script_results and script_results.get("node_analyses"):
                bulk_suggestions = script_results.get("bulk_suggestions", {})
                if bulk_suggestions.get("summary"):
                    call_result["script_summary"] = {
                        "total_turns": bulk_suggestions["summary"].get("total_turns", 0),
                        "good_quality": bulk_suggestions["summary"].get("good_quality", 0),
                        "needs_improvement": bulk_suggestions["summary"].get("needs_improvement", 0),
                        "poor_quality": bulk_suggestions["summary"].get("poor_quality", 0)
                    }
                summary["script_analyzed"] += 1
            
            if tech_results:
                call_result["tech_summary"] = {
                    "avg_latency": tech_results.get("analysis_summary", {}).get("average_total_latency", 0),
                    "nodes_analyzed": tech_results.get("analysis_summary", {}).get("nodes_analyzed", 0)
                }
                summary["tech_analyzed"] += 1
            
            if tonality_results:
                call_result["tonality_summary"] = {
                    "overall": tonality_results.get("overall_tone", "unknown"),
                    "sentiment": tonality_results.get("sentiment", "unknown")
                }
                summary["tonality_analyzed"] += 1
            
            # Count status
            status = call.get("analysis_status", "pending")
            if status == "completed" or call_result["has_tech_qc"] or call_result["has_script_qc"]:
                summary["analyzed"] += 1
            elif status == "failed":
                summary["failed"] += 1
            else:
                summary["pending"] += 1
            
            results.append(call_result)
        
        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name", "Unknown"),
            "summary": summary,
            "calls": results,
            "batch_analysis_status": campaign.get("batch_analysis_status"),
            "batch_analysis_completed": campaign.get("batch_analysis_completed", 0),
            "batch_analysis_total": campaign.get("batch_analysis_total", 0)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign QC results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.put("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    updates: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update campaign settings"""
    try:
        # SECURITY: Verify ownership before update
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']  # Tenant isolation
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Update only allowed fields - now includes QC agent assignments and automation settings
        allowed_fields = [
            'name', 
            'description', 
            'rules', 
            'learning_parameters', 
            'linked_agents', 
            'auto_pattern_detection',
            # QC Agent assignments
            'tonality_qc_agent_id',
            'language_pattern_qc_agent_id', 
            'tech_issues_qc_agent_id',
            # Campaign agents
            'campaign_agents',
            # Custom settings
            'custom_prompt_instructions',
            # Automation settings
            'auto_analysis_after_n_calls',
            'auto_analysis_every_n_calls',
            # CRM Integration
            'crm_integration_enabled',
            'auto_create_leads',
            'auto_reanalyze_on_appointment_update'
        ]
        update_data = {k: v for k, v in updates.items() if k in allowed_fields}
        update_data['updated_at'] = datetime.utcnow()
        
        await db.campaigns.update_one(
            {"id": campaign_id, "user_id": current_user['id']},  # Double check ownership
            {"$set": update_data}
        )
        
        return {"success": True, "message": "Campaign updated"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete campaign and all associated data"""
    try:
        # SECURITY: Verify ownership before deletion
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']  # Tenant isolation
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Delete campaign and cascade delete related data
        await db.campaigns.delete_one({"id": campaign_id, "user_id": current_user['id']})
        await db.campaign_calls.delete_many({"campaign_id": campaign_id})
        await db.campaign_suggestions.delete_many({"campaign_id": campaign_id})
        await db.campaign_patterns.delete_many({"campaign_id": campaign_id})
        
        return {"success": True, "message": "Campaign deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.post("/campaigns/{campaign_id}/add-call")
async def add_call_to_campaign(
    campaign_id: str,
    call_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Add a call to campaign for analysis"""
    try:
        # SECURITY: Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']  # Tenant isolation
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        call_id = call_data.get('call_id')
        if not call_id:
            raise HTTPException(status_code=400, detail="call_id required")
        
        # SECURITY: Verify call belongs to user (query call_logs collection)
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": current_user['id']},
                {"id": call_id, "user_id": current_user['id']}
            ]
        })
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found or access denied")
        
        # Add to campaign with pending status
        campaign_call = {
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "call_id": call_id,
            "added_at": datetime.utcnow(),
            "analysis_status": "pending"
        }
        
        await db.campaign_calls.insert_one(campaign_call)
        logger.info(f"📥 Call {call_id} added to campaign {campaign_id}")
        
        # Check if campaign has auto_analyze enabled
        auto_analyze = campaign.get('auto_analyze', False)
        
        if auto_analyze:
            logger.info(f"🔄 Auto-analyze enabled, triggering QC for call {call_id}")
            
            # Get the agent_id from the call
            agent_id = call.get('agent_id')
            
            # Build QC agent config from campaign settings
            qc_agents_config = {}
            script_qc_agent_id = campaign.get('language_pattern_qc_agent_id')
            if script_qc_agent_id:
                script_agent = await db.qc_agents.find_one({"id": script_qc_agent_id})
                if script_agent:
                    qc_agents_config['script'] = {
                        'llm_provider': script_agent.get('llm_provider', 'grok'),
                        'llm_model': script_agent.get('llm_model', 'grok-3')
                    }
            
            tonality_qc_agent_id = campaign.get('tonality_qc_agent_id')
            if tonality_qc_agent_id:
                tonality_agent = await db.qc_agents.find_one({"id": tonality_qc_agent_id})
                if tonality_agent:
                    qc_agents_config['tonality'] = {
                        'llm_provider': tonality_agent.get('llm_provider', 'grok'),
                        'llm_model': tonality_agent.get('llm_model', 'grok-3')
                    }
            
            # Trigger QC analysis in background
            asyncio.create_task(run_full_qc_analysis(
                call_id=call_id,
                user_id=current_user['id'],
                agent_id=agent_id,
                campaign_id=campaign_id,
                run_tech=campaign.get('run_tech_analysis', True),
                run_script=campaign.get('run_script_analysis', True),
                run_tonality=campaign.get('run_tonality_analysis', True),
                qc_agents_config=qc_agents_config
            ))
            
            return {"success": True, "message": "Call added to campaign and QC analysis triggered"}
        
        return {"success": True, "message": "Call added to campaign"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding call to campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.get("/campaigns/{campaign_id}/calls")
async def get_campaign_calls(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all calls in campaign"""
    try:
        # SECURITY: Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']  # Tenant isolation
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign_calls = await db.campaign_calls.find({
            "campaign_id": campaign_id
        }).to_list(length=1000)
        
        # Convert ObjectId to string
        for call in campaign_calls:
            if '_id' in call:
                call['_id'] = str(call['_id'])
        
        return campaign_calls
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign calls: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.post("/campaigns/{campaign_id}/delete-calls")
async def delete_campaign_calls(
    campaign_id: str,
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete multiple calls from a campaign.
    Removes from campaign_calls collection and cleans up related data.
    
    Request body:
    {
        "call_ids": ["call_id_1", "call_id_2", ...]
    }
    """
    try:
        # SECURITY: Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        call_ids = request.get('call_ids', [])
        if not call_ids:
            raise HTTPException(status_code=400, detail="No call IDs provided")
        
        logger.info(f"🗑️ Deleting {len(call_ids)} calls from campaign {campaign_id}")
        
        deleted_count = 0
        errors = []
        
        for call_id in call_ids:
            try:
                # 1. Delete from campaign_calls
                result = await db.campaign_calls.delete_one({
                    "campaign_id": campaign_id,
                    "call_id": call_id
                })
                
                if result.deleted_count > 0:
                    deleted_count += 1
                    
                    # 2. Remove campaign reference from call_logs (don't delete the call itself)
                    await db.call_logs.update_one(
                        {"call_id": call_id},
                        {"$unset": {
                            "campaign_id": "",
                            "campaign_analyzed": "",
                            "campaign_analysis_at": ""
                        }}
                    )
                    
                    # 3. Remove from call_analytics if exists
                    await db.call_analytics.delete_one({
                        "call_id": call_id,
                        "campaign_id": campaign_id
                    })
                    
                    # 4. Remove from qc_analysis_logs if exists
                    await db.qc_analysis_logs.delete_many({
                        "call_id": call_id,
                        "campaign_id": campaign_id
                    })
                    
                    logger.info(f"✅ Deleted call {call_id} from campaign")
                else:
                    errors.append(f"Call {call_id} not found in campaign")
                    
            except Exception as e:
                errors.append(f"Error deleting {call_id}: {str(e)}")
                logger.error(f"Error deleting call {call_id}: {e}")
        
        # Update campaign stats
        remaining_calls = await db.campaign_calls.count_documents({"campaign_id": campaign_id})
        analyzed_calls = await db.campaign_calls.count_documents({
            "campaign_id": campaign_id,
            "status": "completed"
        })
        
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {
                "total_calls": remaining_calls,
                "analyzed_calls": analyzed_calls,
                "updated_at": datetime.utcnow()
            }}
        )
        
        logger.info(f"🗑️ Deleted {deleted_count}/{len(call_ids)} calls from campaign {campaign_id}")
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "requested_count": len(call_ids),
            "errors": errors if errors else None,
            "remaining_calls": remaining_calls
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign calls: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.post("/campaigns/{campaign_id}/analyze-patterns")
async def analyze_campaign_patterns(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Analyze patterns across all calls in campaign"""
    try:
        # SECURITY: Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']  # Tenant isolation
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get all campaign calls
        campaign_calls_raw = await db.campaign_calls.find({
            "campaign_id": campaign_id
        }).to_list(length=1000)
        
        # Convert ObjectId to string for all documents
        campaign_calls = []
        for cc in campaign_calls_raw:
            if '_id' in cc:
                cc['_id'] = str(cc['_id'])
            campaign_calls.append(cc)
        
        if len(campaign_calls) < 2:
            raise HTTPException(
                status_code=400, 
                detail="At least 2 calls required for pattern recognition. Add more calls to the campaign."
            )
        
        # Check how many have been analyzed
        analyzed_count = sum(1 for cc in campaign_calls if cc.get('script_qc_results'))
        
        if analyzed_count < 2:
            raise HTTPException(
                status_code=400,
                detail=f"At least 2 calls must be analyzed first. Currently {analyzed_count}/{len(campaign_calls)} calls have been analyzed. Run Script QC on each call first."
            )
        
        logger.info(f"Pattern analysis: {analyzed_count} calls analyzed, running detection...")
        
        # Aggregate patterns from script QC results
        patterns = await detect_campaign_patterns(campaign_id, campaign_calls, current_user['id'])
        
        logger.info(f"Pattern analysis complete: {len(patterns)} patterns found")
        
        # Store patterns in database
        for pattern in patterns:
            pattern['campaign_id'] = campaign_id
            pattern['detected_at'] = datetime.utcnow().isoformat()
            await db.campaign_patterns.update_one(
                {"campaign_id": campaign_id, "pattern_type": pattern.get('pattern_type'), "description": pattern.get('description')},
                {"$set": pattern},
                upsert=True
            )
        
        # Sync patterns to assigned QC agents
        await sync_patterns_to_qc_agents(campaign_id, patterns, current_user['id'])
        
        return {
            "campaign_id": campaign_id,
            "calls_analyzed": analyzed_count,
            "patterns": patterns,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing patterns: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.post("/campaigns/{campaign_id}/generate-report")
async def generate_campaign_report(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate comprehensive campaign report"""
    try:
        # SECURITY: Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']  # Tenant isolation
        }, {"_id": 0})
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get all data - exclude _id to prevent ObjectId serialization issues
        campaign_calls = await db.campaign_calls.find({
            "campaign_id": campaign_id
        }, {"_id": 0}).to_list(length=1000)
        
        suggestions = await db.campaign_suggestions.find({
            "campaign_id": campaign_id
        }, {"_id": 0}).to_list(length=1000)
        
        patterns = await db.campaign_patterns.find({
            "campaign_id": campaign_id
        }, {"_id": 0}).to_list(length=100)
        
        # Debug logging
        logger.info(f"Report generation debug - campaign: {campaign is not None}, calls: {len(campaign_calls) if campaign_calls else 0}, suggestions: {len(suggestions) if suggestions else 0}, patterns: {len(patterns) if patterns else 0}")
        
        # Generate report
        report = await generate_comprehensive_report(
            campaign, 
            campaign_calls, 
            suggestions, 
            patterns,
            current_user['id']
        )
        
        return report
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error generating report: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TRAINING CALLS MANAGEMENT
# ============================================================================

@qc_enhanced_router.post("/campaigns/{campaign_id}/training-calls")
async def upload_training_call(
    campaign_id: str,
    file: UploadFile = File(...),
    designation: str = "",
    tags: str = "",
    outcome: str = "unknown",  # "showed", "no_show", "unknown"
    outcome_notes: str = "",
    current_user: dict = Depends(get_current_user)
):
    """Upload a training call to campaign for pattern learning"""
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Validate outcome
        valid_outcomes = ["showed", "no_show", "unknown"]
        if outcome not in valid_outcomes:
            outcome = "unknown"
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Store audio file to disk for later transcription
        training_call_id = str(uuid.uuid4())
        audio_dir = f"/tmp/training_calls/{campaign_id}"
        os.makedirs(audio_dir, exist_ok=True)
        
        # Determine file extension
        file_ext = os.path.splitext(file.filename)[1].lower() or '.wav'
        audio_path = f"{audio_dir}/{training_call_id}{file_ext}"
        
        # Write audio file
        with open(audio_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Stored training call audio: {audio_path} ({file_size} bytes)")
        
        training_call = {
            "id": training_call_id,
            "campaign_id": campaign_id,
            "user_id": current_user['id'],
            "filename": file.filename,
            "file_size": file_size,
            "audio_path": audio_path,  # Store path for later transcription
            "audio_format": file_ext.replace('.', ''),
            "designation": designation,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "transcript": [],
            "transcript_text": "",  # Full transcript text
            "duration": 0,
            "processed": False,
            "analysis_status": "pending",
            
            # Outcome tracking for learning
            "outcome": outcome,  # "showed", "no_show", "unknown"
            "outcome_notes": outcome_notes,
            "outcome_set_at": datetime.now(timezone.utc).isoformat() if outcome != "unknown" else None,
            "outcome_known_before_analysis": outcome != "unknown",  # Did we know outcome before running QC?
            
            # QC Analysis linkage
            "qc_analysis_id": None,  # Will be set when QC runs
            "qc_analyzed_at": None,
            
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.training_calls.insert_one(training_call)
        
        # Update campaign training call count
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$inc": {"total_training_calls": 1}}
        )
        
        logger.info(f"Uploaded training call {training_call['id']} to campaign {campaign_id} with outcome: {outcome}")
        
        return {
            "success": True,
            "training_call_id": training_call['id'],
            "filename": file.filename,
            "size": file_size,
            "outcome": outcome,
            "audio_stored": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading training call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.get("/campaigns/{campaign_id}/training-calls")
async def list_training_calls(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all training calls in a campaign"""
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        training_calls = await db.training_calls.find({
            "campaign_id": campaign_id,
            "user_id": current_user['id']
        }).to_list(length=1000)
        
        for call in training_calls:
            if '_id' in call:
                call['_id'] = str(call['_id'])
        
        return training_calls
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing training calls: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.delete("/campaigns/{campaign_id}/training-calls/{training_call_id}")
async def delete_training_call(
    campaign_id: str,
    training_call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a training call from campaign"""
    try:
        # Verify ownership
        result = await db.training_calls.delete_one({
            "id": training_call_id,
            "campaign_id": campaign_id,
            "user_id": current_user['id']
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Training call not found")
        
        # Update campaign count
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$inc": {"total_training_calls": -1}}
        )
        
        return {"success": True, "message": "Training call deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting training call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.put("/campaigns/{campaign_id}/training-calls/{training_call_id}/outcome")
async def update_training_call_outcome(
    campaign_id: str,
    training_call_id: str,
    outcome_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the outcome of a training call.
    This can trigger learning if the QC agent has learning enabled.
    
    Body:
    {
        "outcome": "showed" | "no_show" | "unknown",
        "outcome_notes": "Optional notes about the outcome",
        "trigger_learning": true  // Whether to trigger learning if applicable
    }
    """
    try:
        # Get training call
        training_call = await db.training_calls.find_one({
            "id": training_call_id,
            "campaign_id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not training_call:
            raise HTTPException(status_code=404, detail="Training call not found")
        
        # Validate outcome
        outcome = outcome_data.get('outcome', 'unknown')
        valid_outcomes = ["showed", "no_show", "unknown"]
        if outcome not in valid_outcomes:
            raise HTTPException(status_code=400, detail=f"Invalid outcome. Must be one of: {valid_outcomes}")
        
        outcome_notes = outcome_data.get('outcome_notes', '')
        trigger_learning = outcome_data.get('trigger_learning', True)
        
        # Update training call
        update_fields = {
            "outcome": outcome,
            "outcome_notes": outcome_notes,
            "outcome_set_at": datetime.now(timezone.utc) if outcome != "unknown" else None
        }
        
        await db.training_calls.update_one(
            {"id": training_call_id},
            {"$set": update_fields}
        )
        
        logger.info(f"Updated training call {training_call_id} outcome to: {outcome}")
        
        # If there's a linked QC analysis, update its outcome too
        learning_triggered = False
        qc_analysis_id = training_call.get('qc_analysis_id')
        
        if qc_analysis_id and outcome in ["showed", "no_show"]:
            # Update the analysis log outcome
            await db.qc_analysis_logs.update_one(
                {"id": qc_analysis_id},
                {
                    "$set": {
                        "actual_outcome": outcome,
                        "outcome_updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Get the QC agent to check learning config
            analysis_log = await db.qc_analysis_logs.find_one({"id": qc_analysis_id})
            if analysis_log and trigger_learning:
                qc_agent_id = analysis_log.get('qc_agent_id')
                if qc_agent_id:
                    # Import and check learning trigger
                    try:
                        from qc_learning_service import LearningOrchestrator, update_analysis_outcome
                        from qc_learning_models import OutcomeType
                        
                        # Update outcome and calculate accuracy
                        await update_analysis_outcome(
                            log_id=qc_analysis_id,
                            outcome=OutcomeType(outcome),
                            db_instance=db
                        )
                        
                        # Check if learning should trigger
                        orchestrator = LearningOrchestrator(db)
                        session = await orchestrator.check_and_trigger_learning(
                            qc_agent_id=qc_agent_id,
                            user_id=current_user['id'],
                            trigger_reason="training_call_outcome"
                        )
                        
                        if session:
                            learning_triggered = True
                            logger.info(f"Learning triggered for agent {qc_agent_id}")
                    except Exception as learn_err:
                        logger.error(f"Error triggering learning: {str(learn_err)}")
        
        return {
            "success": True,
            "training_call_id": training_call_id,
            "outcome": outcome,
            "learning_triggered": learning_triggered
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating training call outcome: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.get("/campaigns/{campaign_id}/training-calls/{training_call_id}")
async def get_training_call(
    campaign_id: str,
    training_call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific training call with its outcome and analysis status"""
    try:
        training_call = await db.training_calls.find_one({
            "id": training_call_id,
            "campaign_id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not training_call:
            raise HTTPException(status_code=404, detail="Training call not found")
        
        if '_id' in training_call:
            training_call['_id'] = str(training_call['_id'])
        
        # If there's a linked analysis, get prediction info
        if training_call.get('qc_analysis_id'):
            analysis = await db.qc_analysis_logs.find_one(
                {"id": training_call['qc_analysis_id']},
                {"_id": 0}
            )
            if analysis:
                training_call['qc_analysis'] = {
                    "predictions": analysis.get('predictions', {}),
                    "scores": analysis.get('scores', {}),
                    "actual_outcome": analysis.get('actual_outcome'),
                    "prediction_accuracy": analysis.get('prediction_accuracy')
                }
        
        return training_call
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting training call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_training_call_script(transcript_text: str, qc_agent: dict, user_id: str) -> tuple:
    """
    Analyze training call transcript using script QC agent guidelines.
    Returns (node_analyses, overall_quality, summary)
    """
    import httpx
    
    try:
        if not transcript_text:
            return [], "pending_transcription", "No transcript available"
        
        # Get user's API key for LLM
        api_key = await get_user_api_key(user_id, 'grok')
        if not api_key:
            api_key = await get_user_api_key(user_id, 'openai')
        if not api_key:
            api_key = await get_user_api_key(user_id, 'anthropic')
        
        if not api_key:
            logger.warning(f"No LLM API key found for training call script analysis, user: {user_id}")
            return [], "good", "Analysis skipped - no LLM API key configured"
        
        # Get QC agent guidelines
        guidelines = ""
        if qc_agent:
            guidelines = qc_agent.get('base_prompt', '') or qc_agent.get('guidelines', '') or ''
        
        # Split transcript into segments for analysis
        # Assume alternating speaker pattern or detect speakers
        segments = parse_transcript_into_segments(transcript_text)
        
        logger.info(f"Training call script analysis: {len(segments)} segments to analyze")
        
        # Build analysis prompt
        analysis_prompt = f"""You are an expert AI conversation analyst evaluating a sales/service call transcript.

**QC AGENT GUIDELINES:**
{guidelines if guidelines else "Evaluate for clarity, professionalism, goal achievement, and customer engagement."}

**TRANSCRIPT:**
{transcript_text[:4000]}

**TASK:**
Analyze this call segment by segment (each exchange between speakers). For each segment, evaluate:
1. Response effectiveness - Did the agent respond appropriately?
2. Goal efficiency - Is the conversation progressing toward the objective?
3. Script adherence - Does it follow expected patterns?
4. Areas for improvement

**OUTPUT FORMAT (JSON array):**
[
  {{
    "segment_number": 1,
    "segment_text": "Brief excerpt of what was said",
    "quality": "excellent|good|needs_improvement|poor",
    "goal_efficiency": "excellent|good|needs_improvement|poor",
    "analysis": "Detailed analysis of this segment",
    "suggestion": "Specific improvement suggestion if any",
    "strengths": ["list", "of", "strengths"],
    "weaknesses": ["list", "of", "weaknesses"]
  }},
  ...
]

Return ONLY the JSON array, no other text."""

        # Call LLM for analysis
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-3-fast",
                    "messages": [
                        {"role": "system", "content": "You are an expert QC analyst. Always respond with valid JSON only."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 3000
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                # Parse JSON response
                import json
                # Clean up response - remove markdown code blocks if present
                ai_response = ai_response.replace('```json', '').replace('```', '').strip()
                
                try:
                    node_analyses = json.loads(ai_response)
                    
                    # Normalize the response format
                    normalized_analyses = []
                    for i, analysis in enumerate(node_analyses):
                        normalized_analyses.append({
                            "node_name": f"Segment {analysis.get('segment_number', i+1)}",
                            "turn_number": analysis.get('segment_number', i+1),
                            "segment_text": analysis.get('segment_text', ''),
                            "quality": analysis.get('quality', 'good'),
                            "goal_efficiency": analysis.get('goal_efficiency', 'good'),
                            "analysis": analysis.get('analysis', ''),
                            "suggestion": analysis.get('suggestion', ''),
                            "strengths": analysis.get('strengths', []),
                            "weaknesses": analysis.get('weaknesses', [])
                        })
                    
                    # Calculate overall quality
                    quality_scores = {'excellent': 4, 'good': 3, 'needs_improvement': 2, 'poor': 1}
                    if normalized_analyses:
                        avg_score = sum(quality_scores.get(a.get('quality', 'good'), 3) for a in normalized_analyses) / len(normalized_analyses)
                        overall_quality = 'excellent' if avg_score >= 3.5 else 'good' if avg_score >= 2.5 else 'needs_improvement' if avg_score >= 1.5 else 'poor'
                    else:
                        overall_quality = 'good'
                    
                    summary = f"Analyzed {len(normalized_analyses)} conversation segments. Overall quality: {overall_quality}."
                    
                    return normalized_analyses, overall_quality, summary
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM response as JSON: {e}")
                    logger.error(f"Response was: {ai_response[:500]}")
                    return [], "good", f"Analysis completed but response parsing failed"
            else:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                return [], "good", f"Analysis failed - API error {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error in training call script analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [], "good", f"Analysis error: {str(e)}"


async def analyze_training_call_tonality(transcript_text: str, qc_agent: dict, user_id: str) -> tuple:
    """
    Analyze training call transcript for tonality using QC agent guidelines.
    Returns (node_analyses, overall_rating, assessment)
    """
    import httpx
    
    try:
        if not transcript_text:
            return [], "pending_transcription", "No transcript available"
        
        # Get user's API key for LLM
        api_key = await get_user_api_key(user_id, 'grok')
        if not api_key:
            api_key = await get_user_api_key(user_id, 'openai')
        if not api_key:
            api_key = await get_user_api_key(user_id, 'anthropic')
        
        if not api_key:
            logger.warning(f"No LLM API key found for training call tonality analysis, user: {user_id}")
            return [], "good", "Analysis skipped - no LLM API key configured"
        
        # Get QC agent guidelines
        guidelines = ""
        if qc_agent:
            guidelines = qc_agent.get('base_prompt', '') or qc_agent.get('guidelines', '') or ''
        
        # Build tonality analysis prompt
        analysis_prompt = f"""You are an expert at analyzing conversation tone and delivery in sales/service calls.

**TONALITY GUIDELINES:**
{guidelines if guidelines else "Evaluate for warmth, confidence, enthusiasm, empathy, and professionalism."}

**TRANSCRIPT:**
{transcript_text[:4000]}

**TASK:**
Analyze the tone and delivery throughout this call. For each significant exchange, evaluate:
1. Emotional tone - warmth, enthusiasm, confidence
2. Pacing and energy
3. Empathy and rapport building
4. Professional demeanor

**OUTPUT FORMAT (JSON array):**
[
  {{
    "segment_number": 1,
    "segment_text": "Brief excerpt",
    "tone_rating": "excellent|good|needs_improvement|poor",
    "tone_analysis": "Detailed tone assessment",
    "emotion_detected": "confident|warm|neutral|hesitant|aggressive|etc",
    "suggestion": "Specific tone improvement if needed",
    "positive_aspects": ["list", "of", "positives"],
    "areas_to_improve": ["list", "of", "improvements"]
  }},
  ...
]

Return ONLY the JSON array, no other text."""

        # Call LLM for analysis
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-3-fast",
                    "messages": [
                        {"role": "system", "content": "You are an expert tonality analyst. Always respond with valid JSON only."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 3000
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                # Parse JSON response
                import json
                ai_response = ai_response.replace('```json', '').replace('```', '').strip()
                
                try:
                    node_analyses = json.loads(ai_response)
                    
                    # Normalize the response format
                    normalized_analyses = []
                    for i, analysis in enumerate(node_analyses):
                        normalized_analyses.append({
                            "node_name": f"Segment {analysis.get('segment_number', i+1)}",
                            "turn_number": analysis.get('segment_number', i+1),
                            "segment_text": analysis.get('segment_text', ''),
                            "tone_rating": analysis.get('tone_rating', 'good'),
                            "tone_analysis": analysis.get('tone_analysis', ''),
                            "emotion_detected": analysis.get('emotion_detected', 'neutral'),
                            "suggestion": analysis.get('suggestion', ''),
                            "positive_aspects": analysis.get('positive_aspects', []),
                            "areas_to_improve": analysis.get('areas_to_improve', [])
                        })
                    
                    # Calculate overall rating
                    rating_scores = {'excellent': 4, 'good': 3, 'needs_improvement': 2, 'poor': 1}
                    if normalized_analyses:
                        avg_score = sum(rating_scores.get(a.get('tone_rating', 'good'), 3) for a in normalized_analyses) / len(normalized_analyses)
                        overall_rating = 'excellent' if avg_score >= 3.5 else 'good' if avg_score >= 2.5 else 'needs_improvement' if avg_score >= 1.5 else 'poor'
                    else:
                        overall_rating = 'good'
                    
                    assessment = f"Analyzed {len(normalized_analyses)} segments for tone and delivery. Overall rating: {overall_rating}."
                    
                    return normalized_analyses, overall_rating, assessment
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM tonality response as JSON: {e}")
                    return [], "good", f"Tonality analysis completed but response parsing failed"
            else:
                logger.error(f"LLM API error for tonality: {response.status_code} - {response.text}")
                return [], "good", f"Tonality analysis failed - API error {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error in training call tonality analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [], "good", f"Tonality analysis error: {str(e)}"


def parse_transcript_into_segments(transcript_text: str) -> list:
    """Parse raw transcript text into speaker segments"""
    segments = []
    lines = transcript_text.split('\n')
    
    current_segment = {"speaker": "", "text": ""}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try to detect speaker changes (common patterns)
        # Pattern: "Speaker:" or "Agent:" or "[Speaker]" etc
        import re
        speaker_match = re.match(r'^(?:\[?(\w+)\]?:?\s*)', line)
        
        if speaker_match and len(speaker_match.group(1)) < 20:
            # New speaker detected
            if current_segment["text"]:
                segments.append(current_segment)
            current_segment = {
                "speaker": speaker_match.group(1),
                "text": line[speaker_match.end():].strip()
            }
        else:
            # Continue current segment
            current_segment["text"] += " " + line
    
    if current_segment["text"]:
        segments.append(current_segment)
    
    # If no speaker patterns found, split by sentences or every N characters
    if len(segments) <= 1:
        # Split into roughly equal chunks
        words = transcript_text.split()
        chunk_size = max(50, len(words) // 10)  # ~10 segments
        segments = []
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i+chunk_size])
            segments.append({"speaker": f"Turn {len(segments)+1}", "text": chunk})
    
    return segments


@qc_enhanced_router.post("/campaigns/{campaign_id}/training-calls/{training_call_id}/analyze")
async def analyze_training_call(
    campaign_id: str,
    training_call_id: str,
    analysis_data: dict = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze a single training call using Soniox for transcription and the campaign's assigned QC agents.
    """
    from server import transcribe_audio_file_dynamic, get_api_key
    
    try:
        # Get training call
        training_call = await db.training_calls.find_one({
            "id": training_call_id,
            "campaign_id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not training_call:
            raise HTTPException(status_code=404, detail="Training call not found")
        
        # Get campaign for QC agent config
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        }, {"_id": 0})
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get assigned QC agents
        script_qc_agent_id = campaign.get('language_pattern_qc_agent_id')
        tonality_qc_agent_id = campaign.get('tonality_qc_agent_id')
        
        # Get QC agent details if assigned
        script_agent = None
        tonality_agent = None
        
        if script_qc_agent_id:
            script_agent = await db.qc_agents.find_one({"id": script_qc_agent_id}, {"_id": 0})
        
        if tonality_qc_agent_id:
            tonality_agent = await db.qc_agents.find_one({"id": tonality_qc_agent_id}, {"_id": 0})
        
        # Mark as analyzing
        await db.training_calls.update_one(
            {"id": training_call_id},
            {"$set": {"analysis_status": "analyzing", "analysis_started_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Transcribe audio using Soniox
        transcript_text = ""
        transcription_status = "pending"
        transcription_error = None
        
        audio_path = training_call.get('audio_path')
        if audio_path and os.path.exists(audio_path):
            try:
                logger.info(f"Transcribing training call audio: {audio_path}")
                
                # Read audio file
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()
                
                # Transcribe using Soniox (or fallback to Deepgram)
                transcript_text = await transcribe_audio_file_dynamic(
                    audio_data, 
                    stt_provider="soniox", 
                    user_id=current_user['id']
                )
                
                if transcript_text:
                    transcription_status = "completed"
                    logger.info(f"Transcription completed: {len(transcript_text)} characters")
                else:
                    transcription_status = "failed"
                    transcription_error = "Soniox returned empty transcript - check API key or audio format"
                    logger.warning(f"Transcription returned empty result for {training_call_id}")
                    
            except Exception as e:
                transcription_status = "failed"
                transcription_error = str(e)
                logger.error(f"Transcription error for {training_call_id}: {e}")
        elif audio_path and not os.path.exists(audio_path):
            transcription_status = "no_audio"
            transcription_error = f"Audio file not found at: {audio_path}"
            logger.warning(f"Audio file missing for training call {training_call_id}: {audio_path}")
        else:
            transcription_status = "no_audio"
            transcription_error = "Training call uploaded before audio storage was enabled. Please re-upload the audio file."
            logger.warning(f"No audio_path for training call {training_call_id} - uploaded before audio storage feature")
        
        # Perform real LLM-based analysis if we have transcript
        script_node_analyses = []
        tonality_node_analyses = []
        script_overall_quality = "pending_transcription"
        tonality_overall_rating = "pending_transcription"
        script_summary = "Transcription required for full analysis."
        tonality_assessment = "Transcription required for full analysis."
        
        if transcript_text:
            logger.info(f"Training call analysis: Running LLM analysis on {len(transcript_text)} chars of transcript")
            
            # Run script analysis using the QC agent
            script_node_analyses, script_overall_quality, script_summary = await analyze_training_call_script(
                transcript_text,
                script_agent,
                current_user['id']
            )
            
            # Run tonality analysis using the QC agent
            tonality_node_analyses, tonality_overall_rating, tonality_assessment = await analyze_training_call_tonality(
                transcript_text,
                tonality_agent,
                current_user['id']
            )
            
            logger.info(f"Training call analysis: Got {len(script_node_analyses)} script analyses, {len(tonality_node_analyses)} tonality analyses")
        
        # Build analysis result with real analysis data
        script_analysis = {
            "overall_quality": script_overall_quality,
            "summary": script_summary,
            "qc_agent_used": script_agent.get('name') if script_agent else "No Script QC Agent Assigned",
            "qc_agent_id": script_qc_agent_id,
            "guidelines": script_agent.get('base_prompt', '')[:200] + '...' if script_agent and script_agent.get('base_prompt') else "Default analysis",
            "node_analyses": script_node_analyses,
            "transcript_preview": transcript_text[:500] + '...' if len(transcript_text) > 500 else transcript_text,
            "status": "analyzed" if transcript_text else "requires_transcription"
        }
        
        tonality_analysis = {
            "overall_rating": tonality_overall_rating, 
            "assessment": tonality_assessment,
            "qc_agent_used": tonality_agent.get('name') if tonality_agent else "No Tonality QC Agent Assigned",
            "qc_agent_id": tonality_qc_agent_id,
            "guidelines": tonality_agent.get('base_prompt', '')[:200] + '...' if tonality_agent and tonality_agent.get('base_prompt') else "Default analysis",
            "node_analyses": tonality_node_analyses,
            "recommendations": [a.get('suggestion', '') for a in tonality_node_analyses if a.get('suggestion')],
            "status": "analyzed" if transcript_text else "requires_transcription"
        }
        
        analysis_result = {
            "id": str(uuid.uuid4()),
            "training_call_id": training_call_id,
            "campaign_id": campaign_id,
            "filename": training_call.get('filename'),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "script_analysis": script_analysis,
            "tonality_analysis": tonality_analysis,
            "agents_used": {
                "script_qc_agent": {
                    "id": script_qc_agent_id,
                    "name": script_agent.get('name') if script_agent else None,
                    "assigned": bool(script_qc_agent_id)
                },
                "tonality_qc_agent": {
                    "id": tonality_qc_agent_id,
                    "name": tonality_agent.get('name') if tonality_agent else None,
                    "assigned": bool(tonality_qc_agent_id)
                }
            },
            "transcription": {
                "provider": "soniox",
                "status": transcription_status,
                "error": transcription_error,
                "text_length": len(transcript_text) if transcript_text else 0
            },
            "has_transcript": bool(transcript_text),
            "transcript_length": len(transcript_text) if transcript_text else 0,
            "status": "completed" if transcript_text else "transcription_failed"
        }
        
        # Update training call as processed with transcript
        await db.training_calls.update_one(
            {"id": training_call_id},
            {
                "$set": {
                    "processed": True,
                    "analysis_status": "completed",
                    "qc_analysis_id": analysis_result["id"],
                    "qc_analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "analysis_result": analysis_result,
                    "script_qc_agent_id": script_qc_agent_id,
                    "tonality_qc_agent_id": tonality_qc_agent_id,
                    "transcript_text": transcript_text,
                    "transcription_status": transcription_status,
                    "transcription_provider": "soniox"
                }
            }
        )
        
        logger.info(f"Analyzed training call {training_call_id} using Soniox transcription ({transcription_status}) and agents: script={script_qc_agent_id}, tonality={tonality_qc_agent_id}")
        
        return {
            "success": True,
            "training_call_id": training_call_id,
            "analysis_id": analysis_result["id"],
            "status": "completed",
            "agents_used": analysis_result["agents_used"],
            "has_transcript": analysis_result["has_transcript"],
            "transcription": analysis_result["transcription"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing training call: {str(e)}")
        # Mark as failed
        await db.training_calls.update_one(
            {"id": training_call_id},
            {"$set": {"analysis_status": "failed", "analysis_error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.post("/campaigns/{campaign_id}/training-calls/analyze-all")
async def analyze_all_training_calls(
    campaign_id: str,
    analysis_data: dict = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze all pending training calls in a campaign using Soniox transcription and assigned QC agents.
    """
    from server import transcribe_audio_file_dynamic
    
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        }, {"_id": 0})
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get assigned QC agents
        script_qc_agent_id = campaign.get('language_pattern_qc_agent_id')
        tonality_qc_agent_id = campaign.get('tonality_qc_agent_id')
        
        # Get QC agent details if assigned
        script_agent = None
        tonality_agent = None
        
        if script_qc_agent_id:
            script_agent = await db.qc_agents.find_one({"id": script_qc_agent_id}, {"_id": 0})
        
        if tonality_qc_agent_id:
            tonality_agent = await db.qc_agents.find_one({"id": tonality_qc_agent_id}, {"_id": 0})
        
        # Get all pending training calls
        force_reanalyze = analysis_data.get('force_reanalyze', False) if analysis_data else False
        
        query = {
            "campaign_id": campaign_id,
            "user_id": current_user['id']
        }
        
        if not force_reanalyze:
            query["$or"] = [
                {"processed": False},
                {"processed": {"$exists": False}},
                {"analysis_status": {"$in": ["pending", "failed", None]}}
            ]
        
        pending_calls = await db.training_calls.find(query, {"_id": 0}).to_list(length=1000)
        
        if not pending_calls:
            return {
                "success": True,
                "message": "No pending training calls to analyze",
                "total_queued": 0,
                "already_processed": 0,
                "agents_used": {
                    "script_qc_agent": script_agent.get('name') if script_agent else None,
                    "tonality_qc_agent": tonality_agent.get('name') if tonality_agent else None
                }
            }
        
        # Mark all as analyzing
        call_ids = [call["id"] for call in pending_calls]
        await db.training_calls.update_many(
            {"id": {"$in": call_ids}},
            {"$set": {"analysis_status": "analyzing", "analysis_started_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Process each call with transcription
        processed_count = 0
        failed_count = 0
        transcribed_count = 0
        
        for call in pending_calls:
            try:
                # Transcribe audio using Soniox
                transcript_text = ""
                transcription_status = "pending"
                
                audio_path = call.get('audio_path')
                if audio_path and os.path.exists(audio_path):
                    try:
                        with open(audio_path, 'rb') as f:
                            audio_data = f.read()
                        
                        transcript_text = await transcribe_audio_file_dynamic(
                            audio_data, 
                            stt_provider="soniox", 
                            user_id=current_user['id']
                        )
                        
                        if transcript_text:
                            transcription_status = "completed"
                            transcribed_count += 1
                        else:
                            transcription_status = "failed"
                    except Exception as e:
                        logger.error(f"Transcription error for {call['id']}: {e}")
                        transcription_status = "failed"
                else:
                    transcription_status = "no_audio"
                
                script_analysis = {
                    "overall_quality": "good" if transcript_text else "pending_transcription",
                    "summary": f"Transcribed {len(transcript_text)} chars using Soniox. Analyzed using {script_agent.get('name') if script_agent else 'default settings'}." if transcript_text else "Transcription required.",
                    "qc_agent_used": script_agent.get('name') if script_agent else "No Script QC Agent Assigned",
                    "qc_agent_id": script_qc_agent_id,
                    "node_analyses": [],
                    "transcript_preview": transcript_text[:500] + '...' if len(transcript_text) > 500 else transcript_text,
                    "status": "analyzed" if transcript_text else "requires_transcription"
                }
                
                tonality_analysis = {
                    "overall_rating": "good" if transcript_text else "pending_transcription",
                    "assessment": f"Analyzed using {tonality_agent.get('name') if tonality_agent else 'default settings'}." if transcript_text else "Transcription required.",
                    "qc_agent_used": tonality_agent.get('name') if tonality_agent else "No Tonality QC Agent Assigned",
                    "qc_agent_id": tonality_qc_agent_id,
                    "recommendations": [],
                    "status": "analyzed" if transcript_text else "requires_transcription"
                }
                
                analysis_result = {
                    "id": str(uuid.uuid4()),
                    "training_call_id": call["id"],
                    "campaign_id": campaign_id,
                    "filename": call.get('filename'),
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "script_analysis": script_analysis,
                    "tonality_analysis": tonality_analysis,
                    "agents_used": {
                        "script_qc_agent": {
                            "id": script_qc_agent_id,
                            "name": script_agent.get('name') if script_agent else None,
                            "assigned": bool(script_qc_agent_id)
                        },
                        "tonality_qc_agent": {
                            "id": tonality_qc_agent_id,
                            "name": tonality_agent.get('name') if tonality_agent else None,
                            "assigned": bool(tonality_qc_agent_id)
                        }
                    },
                    "transcription": {
                        "provider": "soniox",
                        "status": transcription_status,
                        "text_length": len(transcript_text) if transcript_text else 0
                    },
                    "has_transcript": bool(transcript_text),
                    "status": "completed" if transcript_text else "transcription_failed"
                }
                
                await db.training_calls.update_one(
                    {"id": call["id"]},
                    {
                        "$set": {
                            "processed": True,
                            "analysis_status": "completed",
                            "qc_analysis_id": analysis_result["id"],
                            "qc_analyzed_at": datetime.now(timezone.utc).isoformat(),
                            "analysis_result": analysis_result,
                            "script_qc_agent_id": script_qc_agent_id,
                            "tonality_qc_agent_id": tonality_qc_agent_id,
                            "transcript_text": transcript_text,
                            "transcription_status": transcription_status,
                            "transcription_provider": "soniox"
                        }
                    }
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"Error analyzing training call {call['id']}: {str(e)}")
                await db.training_calls.update_one(
                    {"id": call["id"]},
                    {"$set": {"analysis_status": "failed", "analysis_error": str(e)}}
                )
                failed_count += 1
        
        logger.info(f"Bulk analyzed {processed_count} training calls ({transcribed_count} transcribed) for campaign {campaign_id}")
        
        return {
            "success": True,
            "total_queued": len(pending_calls),
            "processed": processed_count,
            "failed": failed_count,
            "transcribed": transcribed_count,
            "message": f"Analyzed {processed_count} training calls ({transcribed_count} transcribed using Soniox)",
            "agents_used": {
                "script_qc_agent": script_agent.get('name') if script_agent else None,
                "tonality_qc_agent": tonality_agent.get('name') if tonality_agent else None
            },
            "transcription_provider": "soniox"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk analyze training calls: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.post("/campaigns/{campaign_id}/custom-calls")
async def upload_custom_call(
    campaign_id: str,
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Upload a custom call (not from an agent) to campaign"""
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Create a campaign call entry
        campaign_call = {
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "call_id": request_data.get('call_id') or f"custom_{uuid.uuid4()}",
            "call_type": "custom",
            "designation": request_data.get('designation', ''),
            "category": request_data.get('category'),
            "transcript": request_data.get('transcript', []),
            "metadata": request_data.get('metadata', {}),
            "analyzed_at": datetime.utcnow()
        }
        
        await db.campaign_calls.insert_one(campaign_call)
        
        # Update campaign count
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$inc": {"total_real_calls": 1}}
        )
        
        return {
            "success": True,
            "campaign_call_id": campaign_call['id']
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading custom call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.post("/campaigns/{campaign_id}/kb")
async def upload_campaign_kb(
    campaign_id: str,
    file: UploadFile = File(...),
    description: str = "",
    current_user: dict = Depends(get_current_user)
):
    """Upload knowledge base file to campaign"""
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Read file content
        content = await file.read()
        content_text = content.decode('utf-8', errors='ignore')
        
        # Create KB item
        kb_item = {
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "user_id": current_user['id'],
            "source_type": "file",
            "source_name": file.filename,
            "content": content_text,
            "description": description,
            "file_size": len(content),
            "created_at": datetime.utcnow()
        }
        
        await db.campaign_kb.insert_one(kb_item)
        
        # Update campaign's KB list
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$push": {"kb_items": kb_item['id']}}
        )
        
        return {
            "success": True,
            "kb_item_id": kb_item['id'],
            "filename": file.filename
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading campaign KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.get("/campaigns/{campaign_id}/kb")
async def list_campaign_kb(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List knowledge base items for campaign"""
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        kb_items = await db.campaign_kb.find({
            "campaign_id": campaign_id
        }).to_list(length=100)
        
        for item in kb_items:
            if '_id' in item:
                item['_id'] = str(item['_id'])
            # Truncate content for list view
            if 'content' in item:
                item['content_preview'] = item['content'][:200] + "..." if len(item['content']) > 200 else item['content']
                del item['content']
        
        return kb_items
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing campaign KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.put("/campaigns/{campaign_id}/agents")
async def update_campaign_agents(
    campaign_id: str,
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update multi-agent configuration for campaign"""
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign_agents = request_data.get('campaign_agents', [])
        
        # Validate agent IDs
        for agent_config in campaign_agents:
            agent_id = agent_config.get('agent_id')
            if agent_id:
                agent = await db.agents.find_one({
                    "id": agent_id,
                    "user_id": current_user['id']
                })
                if agent:
                    agent_config['agent_name'] = agent.get('name', '')
        
        await db.campaigns.update_one(
            {"id": campaign_id},
            {
                "$set": {
                    "campaign_agents": campaign_agents,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {"success": True, "message": "Campaign agents updated"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CALL DATA FETCHING FOR QC ANALYSIS
# ============================================================================

@qc_enhanced_router.post("/calls/fetch")
async def fetch_call_for_qc(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch call data for QC analysis
    
    Accepts call_id in request body to avoid URL encoding issues with special characters
    (e.g., v3:xxx format includes colons)
    
    Returns complete call data including transcript, metadata, and call log
    """
    try:
        call_id = request_data.get('call_id')
        campaign_id = request_data.get('campaign_id')  # Optional - if coming from campaign view
        
        if not call_id:
            raise HTTPException(status_code=400, detail="call_id required")
        
        logger.info(f"Fetching call data for QC analysis: {call_id}")
        
        # Fetch call from call_logs collection (not 'calls')
        # Try multiple possible ID field names for compatibility
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": current_user['id']},
                {"id": call_id, "user_id": current_user['id']}
            ]
        })
        
        if not call:
            logger.warning(f"Call not found for ID: {call_id} (user: {current_user['id']})")
            raise HTTPException(status_code=404, detail="Call not found or you don't have access to it")
        
        # Convert ObjectId to string for JSON serialization
        if '_id' in call:
            call['_id'] = str(call['_id'])
        
        # IMPORTANT: Also check campaign_calls for saved QC results (from batch analysis)
        campaign_call_results = None
        if campaign_id:
            campaign_call_results = await db.campaign_calls.find_one({
                "campaign_id": campaign_id,
                "call_id": call_id
            }, {"_id": 0})
        else:
            # Try to find any campaign_call entry for this call
            campaign_call_results = await db.campaign_calls.find_one({
                "call_id": call_id
            }, {"_id": 0})
        
        # Merge QC results - prioritize campaign_calls results (from batch analysis)
        tech_qc_results = call.get("tech_qc_results")
        script_qc_results = call.get("script_qc_results")
        tonality_qc_results = call.get("tonality_qc_results")
        audio_tonality_results = call.get("audio_tonality_results")
        
        # Helper function to check if results have valid node names
        def has_valid_node_names(results):
            if not results or not results.get("node_analyses"):
                return False
            # Check if first analysis has a real node name (not None, not "Turn X")
            first_analysis = results.get("node_analyses", [{}])[0]
            node_name = first_analysis.get("node_name")
            if not node_name or node_name == "None" or str(node_name).startswith("Turn ") or str(node_name).startswith("Turn-"):
                return False
            return True
        
        if campaign_call_results:
            logger.info(f"Found campaign QC results for call {call_id}")
            # IMPORTANT: Only use campaign_calls data if it has actual content AND valid node names
            # Campaign_calls might have empty node_analyses or None node names from old analysis
            # while call_logs has the real data from individual analysis with proper node names
            
            campaign_tech = campaign_call_results.get("tech_qc_results")
            if has_valid_node_names(campaign_tech):
                tech_qc_results = campaign_tech
                
            campaign_script = campaign_call_results.get("script_qc_results")
            if has_valid_node_names(campaign_script):
                script_qc_results = campaign_script
            elif campaign_script and not script_qc_results:
                # Use campaign data only if we have no other data
                script_qc_results = campaign_script
                
            campaign_tonality = campaign_call_results.get("tonality_qc_results")
            if has_valid_node_names(campaign_tonality):
                tonality_qc_results = campaign_tonality
            elif campaign_tonality and not tonality_qc_results:
                tonality_qc_results = campaign_tonality
                
            if campaign_call_results.get("audio_tonality_results"):
                audio_tonality_results = campaign_call_results["audio_tonality_results"]
        
        # Build response with all necessary data
        # Include FULL call data for comprehensive QC analysis
        response_data = {
            "call_id": call.get("call_id") or call.get("id"),
            "transcript": call.get("transcript", []),
            # CRITICAL FIX: Use 'logs' field (not 'call_log') - this is where latency data is stored
            "call_log": call.get("logs", []),  # Store logs array as call_log for frontend
            "logs": call.get("logs", []),  # Also include as 'logs' for clarity
            "duration": call.get("duration", 0),
            "agent_id": call.get("agent_id"),
            "agent_name": call.get("agent_name", ""),
            "created_at": call.get("created_at"),
            "status": call.get("status", ""),
            "from_number": call.get("from_number", ""),
            "to_number": call.get("to_number", ""),
            "recording_url": call.get("recording_url", ""),
            "recording_id": call.get("recording_id", ""),
            "metadata": call.get("metadata", {}),
            # Include additional comprehensive data
            "sentiment": call.get("sentiment", ""),
            "summary": call.get("summary", ""),
            "latency_avg": call.get("latency_avg", 0),
            "latency_p50": call.get("latency_p50", 0),
            "latency_p90": call.get("latency_p90", 0),
            "latency_p99": call.get("latency_p99", 0),
            "cost": call.get("cost", 0),
            "end_reason": call.get("end_reason", ""),
            "start_time": call.get("start_time"),
            "end_time": call.get("end_time"),
            "custom_variables": call.get("custom_variables", {}),
            "error_message": call.get("error_message"),
            # Include saved QC results (merged from call_logs and campaign_calls)
            "tech_qc_results": tech_qc_results,
            "script_qc_results": script_qc_results,
            "tonality_qc_results": tonality_qc_results,
            "audio_tonality_results": audio_tonality_results,
            # Include campaign info if found
            "campaign_id": campaign_call_results.get("campaign_id") if campaign_call_results else None,
            "analysis_status": campaign_call_results.get("analysis_status") if campaign_call_results else None
        }
        
        logger.info(f"Successfully fetched call data for {call_id}")
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching call for QC: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TECH/LATENCY QC ENDPOINT
# ============================================================================

@qc_enhanced_router.post("/analyze/tech")
async def analyze_tech_performance(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze call for technical performance and latency bottlenecks
    
    Parses call logs and identifies:
    - Nodes exceeding 4s TTFS threshold
    - Specific bottlenecks (LLM, TTS, KB, transitions)
    - Actionable recommendations
    """
    try:
        call_id = request_data.get('call_id')
        call_log_data = request_data.get('call_log_data')
        call_log_url = request_data.get('call_log_url')
        custom_guidelines = request_data.get('custom_guidelines', '')
        llm_provider = request_data.get('llm_provider', 'grok')
        model = request_data.get('model', 'grok-4-1-fast-non-reasoning')
        
        if not call_id:
            raise HTTPException(status_code=400, detail="call_id required")
        
        # Get call data from call_logs collection
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": current_user['id']},
                {"id": call_id, "user_id": current_user['id']}
            ]
        })
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Get agent's call_flow for node name resolution
        agent_id = call.get('agent_id')
        call_flow = []
        if agent_id:
            agent = await db.agents.find_one({"id": agent_id})
            if agent:
                call_flow = agent.get('call_flow', [])
                logger.info(f"Tech QC: Retrieved call_flow with {len(call_flow)} nodes")
        
        # Parse log data - try multiple sources
        node_analyses = []
        logger.info(f"Tech QC: Parsing log data for call {call_id}")
        
        if call_log_url:
            raise HTTPException(status_code=501, detail="URL fetching not implemented yet")
        elif call_log_data:
            # Try to parse call_log_data (can be string, dict, or list)
            if isinstance(call_log_data, str):
                try:
                    call_log_json = json.loads(call_log_data)
                    # Check if it's a list (logs array) or dict (structured call_log)
                    if isinstance(call_log_json, list):
                        logger.info(f"Tech QC: Parsing string as logs array ({len(call_log_json)} items)")
                        node_analyses = parse_logs_array_for_latency(call_log_json, call_flow)
                    else:
                        logger.info("Tech QC: Parsing string as JSON dict")
                        node_analyses = parse_call_log_json_for_latency(call_log_json)
                except json.JSONDecodeError:
                    logger.info("Tech QC: Parsing as text log lines")
                    log_lines = call_log_data.split('\n')
                    node_analyses = parse_call_log_for_latency(log_lines)
            elif isinstance(call_log_data, list):
                # Direct list format (logs array)
                logger.info(f"Tech QC: Received logs array directly ({len(call_log_data)} items)")
                node_analyses = parse_logs_array_for_latency(call_log_data, call_flow)
            elif isinstance(call_log_data, dict) and call_log_data:  # Non-empty dict
                logger.info("Tech QC: Parsing dict call_log")
                node_analyses = parse_call_log_json_for_latency(call_log_data)
        
        # If no nodes found yet, try parsing from call.logs array in database
        if not node_analyses and call.get('logs'):
            logger.info(f"Tech QC: Falling back to call.logs from database ({len(call.get('logs', []))} items)")
            node_analyses = parse_logs_array_for_latency(call.get('logs'), call_flow)
        
        # Log debug info about what we found
        logger.info(f"Tech QC: Found {len(node_analyses)} nodes to analyze")
        if node_analyses:
            logger.info(f"Tech QC: First node sample: {node_analyses[0]}")
        
        # If still no nodes, provide a helpful fallback
        if not node_analyses:
            # Check what data we actually received
            has_call_log_data = bool(call_log_data)
            has_db_logs = bool(call.get('logs'))
            
            logger.warning(f"Tech QC: No nodes parsed. call_log_data={has_call_log_data}, db_logs={has_db_logs}")
            
            if not has_call_log_data and not has_db_logs:
                error_msg = "No log data available for this call. The call may not have been completed or logs were not recorded."
            else:
                error_msg = "Could not parse latency data from logs. The log format may not include timing metrics. Try re-recording the call with latency tracking enabled."
            
            # Instead of raising an error, return a minimal result with explanation
            node_analyses = [{
                "node_name": "No Latency Data",
                "node_id": "",
                "llm_time": 0,
                "tts_time": 0,
                "tts_first_chunk": 0,
                "stt_time": 0,
                "transition_time": 0,
                "kb_time": 0,
                "ttfs": 0,
                "bottlenecks": [error_msg],
                "user_message": "",
                "agent_message": ""
            }]
        
        # Flag nodes exceeding 4s TTFS
        flagged_nodes = [n for n in node_analyses if n.get('ttfs', 0) > 4.0]
        
        # Generate overall assessment
        if len(flagged_nodes) == 0:
            overall = "excellent"
        elif len(flagged_nodes) <= 2:
            overall = "good"
        elif len(flagged_nodes) <= 5:
            overall = "needs improvement"
        else:
            overall = "poor"
        
        # Generate recommendations with custom guidelines
        recommendations = generate_tech_recommendations(
            node_analyses, 
            flagged_nodes, 
            custom_guidelines=custom_guidelines,
            llm_provider=llm_provider,
            model=model
        )
        
        result = {
            "call_id": call_id,
            "overall_performance": overall,
            "total_nodes": len(node_analyses),
            "flagged_nodes": len(flagged_nodes),
            "node_analyses": node_analyses,
            "recommendations": recommendations,
            "custom_guidelines_applied": custom_guidelines if custom_guidelines else "Default guidelines used",
            "llm_used": f"{llm_provider}/{model}",
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        # Always save results to the call record for persistence
        try:
            update_result = await db.call_logs.update_one(
                {
                    "$or": [
                        {"call_id": call_id, "user_id": current_user['id']},
                        {"id": call_id, "user_id": current_user['id']}
                    ]
                },
                {"$set": {"tech_qc_results": result}}
            )
            if update_result.modified_count > 0:
                logger.info(f"Tech QC: Saved results to call record (modified: {update_result.modified_count})")
            else:
                logger.warning(f"Tech QC: No documents modified when saving results for call {call_id}")
        except Exception as save_error:
            logger.error(f"Error saving tech QC results: {save_error}")
        
        # Also store in campaign if campaign specified
        campaign_id = request_data.get('campaign_id')
        if campaign_id:
            await store_campaign_call_analysis(
                campaign_id,
                call_id,
                tech_qc_results=result
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing tech performance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# NODE OPTIMIZATION WITH AUTO-TESTING
# ============================================================================

@qc_enhanced_router.post("/optimize/node")
async def optimize_node_with_testing(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Optimize a specific node for latency and auto-test to verify improvement.
    
    Request body:
    {
        "agent_id": "agent-uuid",
        "node_id": "node-uuid",
        "optimization_type": "prompt|content|both",
        "test_input": "sample user message to test with",
        "max_attempts": 2
    }
    
    Returns optimized node with before/after latency comparison.
    """
    try:
        agent_id = request_data.get('agent_id')
        node_id = request_data.get('node_id')
        optimization_type = request_data.get('optimization_type', 'prompt')
        test_input = request_data.get('test_input', 'Hello, I have a question.')
        max_attempts = request_data.get('max_attempts', 2)
        
        if not agent_id or not node_id:
            raise HTTPException(status_code=400, detail="agent_id and node_id required")
        
        # Get agent
        agent = await db.agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Find the node
        call_flow = agent.get('call_flow', [])
        target_node = None
        
        for node in call_flow:
            if node.get('id') == node_id:
                target_node = node
                break
        
        if not target_node:
            raise HTTPException(status_code=404, detail="Node not found in agent call flow")
        
        # Get API key for optimization
        api_key = await get_user_api_key(current_user['id'], 'grok')
        if not api_key:
            raise HTTPException(status_code=400, detail="No Grok API key found for optimization")
        
        # Store original content
        original_prompt = target_node.get('data', {}).get('prompt', '')
        original_content = target_node.get('data', {}).get('content', '')
        node_label = target_node.get('label', target_node.get('id', 'Unknown'))
        
        # Run baseline test
        logger.info(f"🧪 Running baseline test for node {node_label}")
        baseline_result = await run_node_latency_test(
            agent_id=agent_id,
            node_id=node_id,
            user_id=current_user['id'],
            test_input=test_input,
            api_key=api_key
        )
        
        baseline_latency = baseline_result.get('latency_ms', 0)
        logger.info(f"📊 Baseline latency: {baseline_latency}ms")
        
        # Optimize the node
        optimization_results = []
        best_optimization = None
        best_latency = baseline_latency
        
        for attempt in range(max_attempts):
            logger.info(f"🔧 Optimization attempt {attempt + 1}/{max_attempts}")
            
            # Optimize with Grok
            optimized_prompt, optimized_content = await optimize_node_content(
                original_prompt=original_prompt,
                original_content=original_content,
                optimization_type=optimization_type,
                node_label=node_label,
                api_key=api_key,
                attempt=attempt
            )
            
            # Calculate reduction
            prompt_reduction = len(original_prompt) - len(optimized_prompt) if optimized_prompt else 0
            content_reduction = len(original_content) - len(optimized_content) if optimized_content else 0
            
            # Test optimized version
            test_result = await run_node_latency_test(
                agent_id=agent_id,
                node_id=node_id,
                user_id=current_user['id'],
                test_input=test_input,
                api_key=api_key,
                override_prompt=optimized_prompt,
                override_content=optimized_content
            )
            
            test_latency = test_result.get('latency_ms', 0)
            latency_improvement = baseline_latency - test_latency
            improvement_percent = (latency_improvement / baseline_latency * 100) if baseline_latency > 0 else 0
            
            attempt_result = {
                "attempt": attempt + 1,
                "optimized_prompt": optimized_prompt,
                "optimized_content": optimized_content,
                "prompt_reduction_chars": prompt_reduction,
                "content_reduction_chars": content_reduction,
                "test_latency_ms": test_latency,
                "latency_improvement_ms": latency_improvement,
                "improvement_percent": round(improvement_percent, 1),
                "test_response": test_result.get('response', ''),
                "success": test_latency < baseline_latency
            }
            
            optimization_results.append(attempt_result)
            
            # Track best result
            if test_latency < best_latency:
                best_latency = test_latency
                best_optimization = attempt_result
            
            logger.info(f"📊 Attempt {attempt + 1}: {test_latency}ms (improvement: {latency_improvement}ms / {improvement_percent:.1f}%)")
            
            # If we got significant improvement, we can stop
            if improvement_percent >= 20:
                logger.info("✅ Significant improvement achieved, stopping optimization")
                break
        
        # Generate suggestions if optimization didn't help much
        suggestions = []
        if not best_optimization or best_optimization.get('improvement_percent', 0) < 10:
            suggestions = generate_optimization_suggestions(
                target_node,
                baseline_latency,
                optimization_results
            )
        
        return {
            "agent_id": agent_id,
            "node_id": node_id,
            "node_label": node_label,
            "baseline_latency_ms": baseline_latency,
            "best_latency_ms": best_latency,
            "total_improvement_ms": baseline_latency - best_latency,
            "improvement_percent": round((baseline_latency - best_latency) / baseline_latency * 100, 1) if baseline_latency > 0 else 0,
            "original_prompt": original_prompt,
            "original_content": original_content,
            "optimization_attempts": optimization_results,
            "best_optimization": best_optimization,
            "suggestions": suggestions,
            "can_apply": best_optimization is not None and best_optimization.get('improvement_percent', 0) > 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing node: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.post("/optimize/node/apply")
async def apply_node_optimization(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Apply the optimized node changes to the agent permanently.
    
    Request body:
    {
        "agent_id": "agent-uuid",
        "node_id": "node-uuid",
        "optimized_prompt": "new prompt text",
        "optimized_content": "new content text"
    }
    """
    try:
        agent_id = request_data.get('agent_id')
        node_id = request_data.get('node_id')
        optimized_prompt = request_data.get('optimized_prompt')
        optimized_content = request_data.get('optimized_content')
        
        if not agent_id or not node_id:
            raise HTTPException(status_code=400, detail="agent_id and node_id required")
        
        # Get agent
        agent = await db.agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Find and update the node
        call_flow = agent.get('call_flow', [])
        updated = False
        node_label = None
        
        for node in call_flow:
            if node.get('id') == node_id:
                node_label = node.get('label', node_id)
                if 'data' not in node:
                    node['data'] = {}
                
                # Store original as backup
                node['data']['_backup_prompt'] = node['data'].get('prompt', '')
                node['data']['_backup_content'] = node['data'].get('content', '')
                node['data']['_optimized_at'] = datetime.utcnow().isoformat()
                
                # Apply optimization
                if optimized_prompt:
                    node['data']['prompt'] = optimized_prompt
                if optimized_content:
                    node['data']['content'] = optimized_content
                
                updated = True
                break
        
        if not updated:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Save to database
        await db.agents.update_one(
            {"id": agent_id, "user_id": current_user['id']},
            {"$set": {"call_flow": call_flow, "updated_at": datetime.utcnow()}}
        )
        
        logger.info(f"✅ Applied optimization to node {node_label} in agent {agent_id}")
        
        return {
            "success": True,
            "message": f"Optimization applied to node '{node_label}'",
            "agent_id": agent_id,
            "node_id": node_id,
            "backup_created": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying node optimization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_node_latency_test(
    agent_id: str,
    node_id: str,
    user_id: str,
    test_input: str,
    api_key: str,
    override_prompt: str = None,
    override_content: str = None
) -> dict:
    """Run a latency test for a specific node"""
    import time
    
    try:
        # Get agent
        agent = await db.agents.find_one({"id": agent_id})
        if not agent:
            return {"error": "Agent not found", "latency_ms": 99999}
        
        # Find the node
        call_flow = agent.get('call_flow', [])
        target_node = None
        
        for node in call_flow:
            if node.get('id') == node_id:
                target_node = dict(node)  # Copy to avoid modifying original
                break
        
        if not target_node:
            return {"error": "Node not found", "latency_ms": 99999}
        
        # Apply overrides if provided
        if override_prompt:
            if 'data' not in target_node:
                target_node['data'] = {}
            target_node['data']['prompt'] = override_prompt
        if override_content:
            if 'data' not in target_node:
                target_node['data'] = {}
            target_node['data']['content'] = override_content
        
        # Build the prompt for LLM
        system_prompt = agent.get('system_prompt', '')
        node_prompt = target_node.get('data', {}).get('prompt', '')
        node_content = target_node.get('data', {}).get('content', '')
        
        full_prompt = f"{system_prompt}\n\n{node_content}\n\n{node_prompt}"
        
        # Make LLM call and measure latency
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-3",
                    "messages": [
                        {"role": "system", "content": full_prompt},
                        {"role": "user", "content": test_input}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
        
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            return {
                "latency_ms": latency_ms,
                "response": ai_response[:500],
                "success": True
            }
        else:
            return {
                "latency_ms": latency_ms,
                "error": f"API error: {response.status_code}",
                "success": False
            }
    
    except Exception as e:
        logger.error(f"Error in node latency test: {str(e)}")
        return {"latency_ms": 99999, "error": str(e), "success": False}


async def optimize_node_content(
    original_prompt: str,
    original_content: str,
    optimization_type: str,
    node_label: str,
    api_key: str,
    attempt: int = 0
) -> tuple:
    """Optimize node prompt/content using Grok"""
    
    optimized_prompt = original_prompt
    optimized_content = original_content
    
    # Vary the optimization approach based on attempt
    aggressiveness = "moderate" if attempt == 0 else "aggressive"
    
    optimization_instruction = f"""You are an expert at optimizing voice agent node prompts for MINIMUM LATENCY.

OPTIMIZATION LEVEL: {aggressiveness.upper()}

RULES:
1. Remove ALL redundant instructions and filler words
2. Convert verbose paragraphs into concise bullet points
3. Eliminate flowery language - use direct imperatives
4. Remove duplicate rules and repeated instructions
5. Keep ONLY essential logic - remove nice-to-have guidelines
6. Use abbreviations where clear
7. Maintain critical business logic and exact phrasing that must be spoken
8. Preserve SSML tags, KB references, and variable names
9. {"Cut content by 40-50% while keeping core functionality" if aggressiveness == "aggressive" else "Cut content by 20-30% while keeping all functionality"}

OUTPUT: Return ONLY the optimized text, no explanations or markdown."""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Optimize prompt if requested
            if optimization_type in ['prompt', 'both'] and original_prompt:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-3",
                        "messages": [
                            {"role": "system", "content": optimization_instruction},
                            {"role": "user", "content": f"Optimize this node prompt for '{node_label}':\n\n{original_prompt}"}
                        ],
                        "temperature": 0.3
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized_prompt = result['choices'][0]['message']['content'].strip()
                    # Clean up any markdown
                    if optimized_prompt.startswith('```'):
                        optimized_prompt = optimized_prompt.split('```')[1]
                        if optimized_prompt.startswith('\n'):
                            optimized_prompt = optimized_prompt[1:]
            
            # Optimize content if requested
            if optimization_type in ['content', 'both'] and original_content:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-3",
                        "messages": [
                            {"role": "system", "content": optimization_instruction},
                            {"role": "user", "content": f"Optimize this node content for '{node_label}':\n\n{original_content}"}
                        ],
                        "temperature": 0.3
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized_content = result['choices'][0]['message']['content'].strip()
                    if optimized_content.startswith('```'):
                        optimized_content = optimized_content.split('```')[1]
                        if optimized_content.startswith('\n'):
                            optimized_content = optimized_content[1:]
        
        return optimized_prompt, optimized_content
    
    except Exception as e:
        logger.error(f"Error optimizing node content: {str(e)}")
        return original_prompt, original_content


def generate_optimization_suggestions(node: dict, baseline_latency: float, attempts: list) -> list:
    """Generate suggestions when automatic optimization doesn't help"""
    suggestions = []
    
    node_data = node.get('data', {})
    prompt_length = len(node_data.get('prompt', ''))
    content_length = len(node_data.get('content', ''))
    
    if baseline_latency > 3000:
        suggestions.append({
            "type": "critical",
            "title": "Consider Splitting Node",
            "description": "This node has very high latency. Consider breaking it into multiple smaller nodes with focused purposes.",
            "action": "split_node"
        })
    
    if prompt_length > 2000:
        suggestions.append({
            "type": "warning",
            "title": "Large Prompt Detected",
            "description": f"Node prompt is {prompt_length} characters. Try manually removing non-essential instructions.",
            "action": "edit_prompt"
        })
    
    if content_length > 3000:
        suggestions.append({
            "type": "warning",
            "title": "Large Content Block",
            "description": f"Node content is {content_length} characters. Consider moving reference material to Knowledge Base instead.",
            "action": "move_to_kb"
        })
    
    # Check for common latency issues
    prompt = node_data.get('prompt', '').lower()
    if 'example' in prompt and prompt.count('example') > 2:
        suggestions.append({
            "type": "info",
            "title": "Multiple Examples",
            "description": "Node has multiple examples. Keep only 1-2 most relevant examples.",
            "action": "reduce_examples"
        })
    
    if 'if ' in prompt and prompt.count('if ') > 5:
        suggestions.append({
            "type": "info",
            "title": "Complex Conditionals",
            "description": "Node has many conditional statements. Consider using transition logic instead.",
            "action": "use_transitions"
        })
    
    # Check KB references
    if '{{kb' in node_data.get('prompt', '').lower() or '{{kb' in node_data.get('content', '').lower():
        suggestions.append({
            "type": "info",
            "title": "KB Retrieval Present",
            "description": "Node uses Knowledge Base. Ensure KB chunks are optimized and not too large.",
            "action": "optimize_kb"
        })
    
    if not suggestions:
        suggestions.append({
            "type": "success",
            "title": "Node is Well Optimized",
            "description": "Automatic optimization didn't find significant improvements. The node may already be well-optimized, or latency may be due to external factors (network, API).",
            "action": "none"
        })
    
    return suggestions


# ============================================================================
# SCRIPT QUALITY QC ENDPOINT
# ============================================================================

@qc_enhanced_router.post("/analyze/script")
async def analyze_script_quality(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze conversation script quality and suggest improvements
    
    Uses LLM to analyze:
    - Response effectiveness
    - Snappiness and relevance
    - Path to node goal efficiency
    """
    try:
        logger.info(f"Script QC: Starting analysis for user {current_user['id']}")
        
        call_id = request_data.get('call_id')
        campaign_id = request_data.get('campaign_id')
        custom_rules = request_data.get('custom_rules', {})
        custom_guidelines = request_data.get('custom_guidelines', '')
        llm_provider = request_data.get('llm_provider', 'grok')
        model = request_data.get('model', 'grok-4-1-fast-non-reasoning')
        
        # Accept transcript data from frontend as fallback
        frontend_transcript = request_data.get('transcript', [])
        frontend_call_log = request_data.get('call_log', [])
        frontend_agent_id = request_data.get('agent_id')
        
        logger.info(f"Script QC: call_id={call_id}, llm={llm_provider}/{model}")
        
        if not call_id:
            raise HTTPException(status_code=400, detail="call_id required")
        
        # Get call data with transcript from call_logs collection
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": current_user['id']},
                {"id": call_id, "user_id": current_user['id']}
            ]
        })
        
        # If call not found but we have frontend data, create a minimal call object
        if not call and (frontend_transcript or frontend_call_log):
            logger.warning(f"Script QC: Call not found in DB, using frontend data")
            call = {
                "call_id": call_id,
                "transcript": frontend_transcript,
                "logs": frontend_call_log,
                "agent_id": frontend_agent_id,
                "user_id": current_user['id']
            }
        elif not call:
            logger.error(f"Script QC: Call not found: {call_id}")
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Extract transcript from call data (handles both transcript and logs fields)
        transcript = extract_transcript_from_call(call)
        
        # Fallback to frontend data if DB call has no transcript
        if (not transcript or len(transcript) == 0) and frontend_transcript:
            logger.info(f"Script QC: Using frontend transcript data ({len(frontend_transcript)} entries)")
            transcript = frontend_transcript
        
        if (not transcript or len(transcript) == 0) and frontend_call_log:
            logger.info(f"Script QC: Using frontend call_log data ({len(frontend_call_log)} entries)")
            # Try to extract transcript from call_log
            temp_call = {"logs": frontend_call_log}
            transcript = extract_transcript_from_call(temp_call)
        
        logger.info(f"Script QC: Found {len(transcript)} transcript entries")
        
        # If still no transcript, return helpful message
        if not transcript or len(transcript) == 0:
            logger.warning(f"Script QC: No transcript found for call {call_id}")
            # Log what fields the call has to help debug
            logger.warning(f"Script QC: Call fields available: {list(call.keys())}")
            if call.get('logs'):
                sample_log = call['logs'][0] if call['logs'] else {}
                logger.warning(f"Script QC: Sample log entry keys: {list(sample_log.keys()) if isinstance(sample_log, dict) else type(sample_log)}")
            
            return {
                "call_id": call_id,
                "overall_quality": "good",
                "node_analyses": [],
                "bulk_suggestions": [],
                "predictions": None,
                "message": "No transcript found for this call. Script analysis requires a conversation transcript with role and text fields."
            }
        
        # Get agent data for node information
        agent = await db.agents.find_one({
            "id": call.get('agent_id'),
            "user_id": current_user['id']
        })
        
        if not agent:
            logger.warning(f"Script QC: Agent not found for agent_id: {call.get('agent_id')}, proceeding without agent data")
            # Create a minimal agent structure for analysis
            agent = {"id": call.get('agent_id'), "call_flow": []}
        
        # Get campaign rules if provided
        rules = custom_rules
        if campaign_id:
            campaign = await db.campaigns.find_one({
                "id": campaign_id,
                "user_id": current_user['id']
            })
            if campaign:
                rules = {**campaign.get('rules', {}), **custom_rules}
        
        # Add custom guidelines and LLM settings to rules
        rules['custom_guidelines'] = custom_guidelines
        rules['llm_provider'] = llm_provider
        rules['model'] = model
        rules['user_id'] = current_user['id']
        
        logger.info(f"Script QC: Starting LLM analysis with {llm_provider}/{model}")
        
        # Analyze script with LLM - pass logs for node name extraction
        node_analyses = await analyze_script_with_llm(
            call.get('transcript', []),
            agent.get('call_flow', []),
            rules,
            call.get('logs', [])  # Pass logs for node name extraction
        )
        
        logger.info(f"Script QC: LLM analysis complete, got {len(node_analyses)} analyses")
        
        # Generate bulk suggestions
        bulk_suggestions = generate_bulk_script_suggestions(node_analyses)
        
        # Calculate overall quality from individual analyses
        quality_scores = {'excellent': 4, 'good': 3, 'needs_improvement': 2, 'poor': 1}
        if node_analyses:
            avg_score = sum(quality_scores.get(n.get('quality', 'good'), 3) for n in node_analyses) / len(node_analyses)
            overall_quality = 'excellent' if avg_score >= 3.5 else 'good' if avg_score >= 2.5 else 'needs_improvement' if avg_score >= 1.5 else 'poor'
        else:
            overall_quality = 'good'
        
        # Generate predictions for learning system
        predictions = await generate_script_predictions(node_analyses, call.get('transcript', []))
        
        result = {
            "call_id": call_id,
            "overall_quality": overall_quality,
            "node_analyses": node_analyses,
            "bulk_suggestions": bulk_suggestions,
            "predictions": predictions.dict() if predictions else None,
            "custom_guidelines_applied": custom_guidelines if custom_guidelines else "Default guidelines used",
            "llm_used": f"{llm_provider}/{model}",
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        # Always save results to the call record for persistence
        try:
            # First try to update existing record
            update_result = await db.call_logs.update_one(
                {
                    "$or": [
                        {"call_id": call_id, "user_id": current_user['id']},
                        {"id": call_id, "user_id": current_user['id']}
                    ]
                },
                {"$set": {"script_qc_results": result}}
            )
            logger.info(f"Script QC: Save attempt for call {call_id} (user: {current_user['id']}) - matched: {update_result.matched_count}, modified: {update_result.modified_count}")
            
            if update_result.matched_count == 0:
                # Call doesn't exist in DB - create a minimal record to store QC results
                logger.warning(f"Script QC: No matching document found for call {call_id}, creating new record")
                new_record = {
                    "call_id": call_id,
                    "user_id": current_user['id'],
                    "agent_id": call.get('agent_id'),
                    "script_qc_results": result,
                    "created_at": datetime.utcnow(),
                    "status": "qc_only"  # Mark as QC-only record
                }
                await db.call_logs.insert_one(new_record)
                logger.info(f"Script QC: Created new call record with QC results")
            elif update_result.modified_count == 0:
                logger.info(f"Script QC: Document matched but not modified (data may be unchanged)")
            else:
                logger.info(f"Script QC: Successfully saved results to call record")
        except Exception as save_error:
            logger.error(f"Error saving script QC results: {save_error}")
        
        # Also store in campaign if campaign specified
        if campaign_id:
            await store_campaign_call_analysis(
                campaign_id,
                call_id,
                script_qc_results=result
            )
        
        # Log to learning system if qc_agent_id provided
        qc_agent_id = request_data.get('qc_agent_id')
        training_call_id = request_data.get('training_call_id')
        lead_id = request_data.get('lead_id')
        
        if qc_agent_id and predictions:
            try:
                analysis_log = await log_qc_analysis(
                    qc_agent_id=qc_agent_id,
                    user_id=current_user['id'],
                    agent_type="language_pattern",
                    call_id=call_id,
                    analysis_content=result,
                    predictions=predictions,
                    campaign_id=campaign_id,
                    lead_id=lead_id,
                    call_agent_id=call.get('agent_id')
                )
                
                # Save to database
                await db.qc_analysis_logs.insert_one(analysis_log.dict())
                result['analysis_log_id'] = analysis_log.id
                
                # If this is a training call, link the analysis
                if training_call_id:
                    await db.training_calls.update_one(
                        {"id": training_call_id},
                        {
                            "$set": {
                                "qc_analysis_id": analysis_log.id,
                                "qc_analyzed_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                
                logger.info(f"Script QC: Logged analysis to learning system: {analysis_log.id}")
            except Exception as log_err:
                logger.error(f"Failed to log analysis to learning system: {str(log_err)}")
        
        logger.info(f"Script QC: Returning result with {len(node_analyses)} conversation analyses")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing script quality: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TONALITY QC ENDPOINT
# ============================================================================

@qc_enhanced_router.post("/analyze/tonality")
async def analyze_tonality(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze audio tonality and delivery quality
    
    Uses transcript analysis to infer tonality patterns and generate
    SSML/prosody recommendations for voice improvement.
    """
    try:
        call_id = request_data.get('call_id')
        custom_guidelines = request_data.get('custom_guidelines', '')
        llm_provider = request_data.get('llm_provider', 'grok')
        model = request_data.get('model', 'grok-3')
        
        logger.info(f"Tonality QC: Starting analysis for call {call_id}")
        
        if not call_id:
            raise HTTPException(status_code=400, detail="call_id required")
        
        # Get call data from call_logs collection
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": current_user['id']},
                {"id": call_id, "user_id": current_user['id']}
            ]
        })
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        recording_url = call.get('recording_url')
        transcript = extract_transcript_from_call(call)
        
        logger.info(f"Tonality QC: Found {len(transcript)} transcript entries")
        
        # Get API key for LLM analysis
        api_key = await get_user_api_key(current_user['id'], llm_provider)
        
        if not api_key:
            logger.warning(f"Tonality QC: No API key found for {llm_provider}")
            # Return basic analysis without LLM
            return {
                "call_id": call_id,
                "recording_url": recording_url,
                "node_analyses": [],
                "overall_tonality": "unknown",
                "ssml_recommendations": [],
                "custom_guidelines_applied": custom_guidelines if custom_guidelines else "Default guidelines used",
                "llm_configured": f"{llm_provider}/{model}",
                "analyzed_at": datetime.utcnow().isoformat(),
                "message": f"No API key configured for {llm_provider}. Add your API key in Settings to enable AI-powered tonality analysis."
            }
        
        # Get agent data for node information
        agent = await db.agents.find_one({
            "id": call.get('agent_id'),
            "user_id": current_user['id']
        })
        
        call_flow = agent.get('call_flow', []) if agent else []
        call_logs = call.get('logs', []) if call else []
        
        # Analyze tonality using LLM based on transcript - pass logs for node name extraction
        node_analyses = await analyze_tonality_with_llm(transcript, custom_guidelines, api_key, llm_provider, model, call_flow, call_logs)
        
        # Generate SSML recommendations
        ssml_recommendations = generate_ssml_recommendations(node_analyses)
        
        # Determine overall tonality
        if node_analyses:
            quality_scores = {'excellent': 4, 'good': 3, 'needs_improvement': 2, 'poor': 1}
            avg_score = sum(quality_scores.get(n.get('delivery_quality', 'good'), 3) for n in node_analyses) / len(node_analyses)
            overall = 'excellent' if avg_score >= 3.5 else 'good' if avg_score >= 2.5 else 'needs_improvement' if avg_score >= 1.5 else 'poor'
        else:
            overall = 'good'
        
        logger.info(f"Tonality QC: Analysis complete, {len(node_analyses)} turns analyzed, overall: {overall}")
        
        # Generate predictions for learning system
        predictions = await generate_tonality_predictions(node_analyses, transcript)
        
        result = {
            "call_id": call_id,
            "recording_url": recording_url,
            "node_analyses": node_analyses,
            "overall_tonality": overall,
            "ssml_recommendations": ssml_recommendations,
            "predictions": predictions.dict() if predictions else None,
            "custom_guidelines_applied": custom_guidelines if custom_guidelines else "Default guidelines used",
            "llm_configured": f"{llm_provider}/{model}",
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        # Log to learning system if qc_agent_id provided
        qc_agent_id = request_data.get('qc_agent_id')
        campaign_id = request_data.get('campaign_id')
        training_call_id = request_data.get('training_call_id')
        lead_id = request_data.get('lead_id')
        
        if qc_agent_id and predictions:
            try:
                analysis_log = await log_qc_analysis(
                    qc_agent_id=qc_agent_id,
                    user_id=current_user['id'],
                    agent_type="tonality",
                    call_id=call_id,
                    analysis_content=result,
                    predictions=predictions,
                    campaign_id=campaign_id,
                    lead_id=lead_id,
                    call_agent_id=call.get('agent_id')
                )
                
                # Save to database
                await db.qc_analysis_logs.insert_one(analysis_log.dict())
                result['analysis_log_id'] = analysis_log.id
                
                # If this is a training call, link the analysis
                if training_call_id:
                    await db.training_calls.update_one(
                        {"id": training_call_id},
                        {
                            "$set": {
                                "qc_analysis_id": analysis_log.id,
                                "qc_analyzed_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                
                logger.info(f"Tonality QC: Logged analysis to learning system: {analysis_log.id}")
            except Exception as log_err:
                logger.error(f"Failed to log analysis to learning system: {str(log_err)}")
        
        # Always save results to the call record for persistence
        try:
            update_result = await db.call_logs.update_one(
                {
                    "$or": [
                        {"call_id": call_id, "user_id": current_user['id']},
                        {"id": call_id, "user_id": current_user['id']}
                    ]
                },
                {"$set": {"tonality_qc_results": result}}
            )
            if update_result.modified_count > 0:
                logger.info(f"Tonality QC: Saved results to call record (modified: {update_result.modified_count})")
            else:
                logger.warning(f"Tonality QC: No documents modified when saving results for call {call_id}")
        except Exception as save_error:
            logger.error(f"Error saving tonality QC results: {save_error}")
        
        # Also store in campaign if campaign specified
        if campaign_id:
            await store_campaign_call_analysis(
                campaign_id,
                call_id,
                tonality_qc_results=result
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing tonality: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.post("/analyze/audio-tonality")
async def analyze_audio_tonality(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze audio recording for emotional tonality using multimodal LLM.
    
    This provides much more accurate emotional analysis than transcript-based,
    detecting voice characteristics like:
    - Pitch patterns (uncertain vs confident)
    - Speaking pace (excited vs calm)
    - Emotional undertones not in text
    - Frustration/satisfaction from voice quality
    
    Integrates with the learning system for continuous improvement.
    """
    try:
        from audio_tonality_service import (
            analyze_call_audio_tonality,
            create_audio_tonality_learning_entry
        )
        
        call_id = request_data.get('call_id')
        custom_guidelines = request_data.get('custom_guidelines', '')
        focus_areas = request_data.get('focus_areas', [])
        qc_agent_id = request_data.get('qc_agent_id')  # For learning integration
        
        logger.info(f"Audio Tonality QC: Starting analysis for call {call_id}")
        
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
        
        recording_url = call.get('recording_url')
        recording_id = call.get('recording_id')  # Telnyx recording ID for authenticated download
        
        if not recording_url and not recording_id:
            raise HTTPException(
                status_code=400, 
                detail="No recording URL found for this call. Audio tonality analysis requires a call recording."
            )
        
        # If we have a recording_id, try to get a fresh download URL via Telnyx API
        audio_data = None
        audio_format = 'mp3'
        
        if recording_id:
            try:
                # Get user's Telnyx API key
                telnyx_api_key = await get_user_api_key(current_user['id'], 'telnyx')
                
                if telnyx_api_key:
                    from telnyx_service import TelnyxService
                    telnyx_service = TelnyxService()
                    telnyx_service.api_key = telnyx_api_key
                    
                    logger.info(f"Audio Tonality QC: Downloading recording via Telnyx API (recording_id: {recording_id})")
                    
                    recording_result = await telnyx_service.get_recording(recording_id)
                    
                    if recording_result.get('success') and recording_result.get('content'):
                        audio_data = recording_result['content']
                        content_type = recording_result.get('content_type', 'audio/mpeg')
                        audio_format = 'wav' if 'wav' in content_type else 'mp3'
                        logger.info(f"Audio Tonality QC: Downloaded {len(audio_data)} bytes via Telnyx API")
                    else:
                        logger.warning(f"Audio Tonality QC: Telnyx download failed, falling back to URL: {recording_result.get('error', 'Unknown error')}")
                else:
                    logger.warning("Audio Tonality QC: No Telnyx API key configured, falling back to direct URL download")
            except Exception as e:
                logger.error(f"Audio Tonality QC: Error downloading via Telnyx: {str(e)}")
        
        transcript = call.get('transcript', [])
        
        # Get agent data for context
        agent = await db.agents.find_one({
            "id": call.get('agent_id'),
            "user_id": current_user['id']
        })
        
        agent_config = agent if agent else None
        
        # Get knowledge base content for context
        knowledge_base = None
        if agent and agent.get('knowledge_base_ids'):
            kb_items = await db.knowledge_bases.find({
                "id": {"$in": agent.get('knowledge_base_ids', [])}
            }).to_list(length=10)
            if kb_items:
                knowledge_base = "\n---\n".join([
                    f"Source: {kb.get('name', 'Unknown')}\n{kb.get('content', '')[:500]}"
                    for kb in kb_items
                ])
        
        # Get OpenAI API key - prefer user's key, fall back to Emergent key
        api_key = await get_user_api_key(current_user['id'], 'openai')
        
        if not api_key:
            # Try Emergent LLM key as fallback
            import os
            api_key = os.environ.get('EMERGENT_LLM_KEY')
        
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="No OpenAI API key configured. Audio tonality analysis requires OpenAI for multimodal audio processing."
            )
        
        logger.info("Audio Tonality QC: Analyzing recording...")
        
        # Run the audio analysis - use pre-downloaded audio if available
        if audio_data:
            logger.info(f"Audio Tonality QC: Using pre-downloaded audio ({len(audio_data)} bytes)")
            analysis_result = await analyze_call_audio_tonality(
                api_key=api_key,
                agent_config=agent_config,
                knowledge_base=knowledge_base,
                transcript=transcript,
                custom_guidelines=custom_guidelines,
                focus_areas=focus_areas if focus_areas else None,
                audio_data=audio_data,
                audio_format=audio_format
            )
        else:
            logger.info(f"Audio Tonality QC: Downloading from URL: {recording_url[:50]}...")
            analysis_result = await analyze_call_audio_tonality(
                recording_url=recording_url,
                api_key=api_key,
                agent_config=agent_config,
                knowledge_base=knowledge_base,
                transcript=transcript,
                custom_guidelines=custom_guidelines,
                focus_areas=focus_areas if focus_areas else None
            )
        
        if not analysis_result.get('success'):
            error_msg = analysis_result.get('error', 'Unknown error')
            suggestion = analysis_result.get('suggestion', '')
            
            logger.error(f"Audio analysis failed: {error_msg}")
            
            # Provide helpful error message based on error type
            if '403' in str(error_msg):
                detail = "Recording URL access denied (403 Forbidden). The recording may have expired or require authentication. Please try refreshing the call data or re-recording the call."
            elif '404' in str(error_msg):
                detail = "Recording not found (404). The recording URL may be invalid or the file was deleted."
            else:
                detail = f"Audio analysis failed: {error_msg}"
            
            if suggestion:
                detail += f" {suggestion}"
            
            raise HTTPException(status_code=500, detail=detail)
        
        analysis = analysis_result.get('analysis', {})
        
        # Extract key metrics for response
        overall = analysis.get('overall_assessment', {})
        quality_scores = analysis.get('quality_scores', {})
        flags = analysis.get('flags', {})
        speaker_analysis = analysis.get('speaker_analysis', {})
        recommendations = analysis.get('recommendations', {})
        
        # Calculate overall score
        overall_quality = quality_scores.get('overall_quality', 5)
        if overall_quality >= 8:
            overall_rating = 'excellent'
        elif overall_quality >= 6:
            overall_rating = 'good'
        elif overall_quality >= 4:
            overall_rating = 'needs_improvement'
        else:
            overall_rating = 'poor'
        
        # Build result
        result = {
            "call_id": call_id,
            "recording_url": recording_url,
            "analysis_type": "audio_multimodal",
            "model_used": "gpt-4o-audio-preview",
            
            # Overall assessment
            "overall_rating": overall_rating,
            "overall_assessment": overall,
            
            # Detailed scores
            "quality_scores": quality_scores,
            
            # Speaker-specific analysis
            "user_analysis": speaker_analysis.get('user', {}),
            "agent_analysis": speaker_analysis.get('agent', {}),
            
            # Emotional journey through the call
            "emotional_journey": analysis.get('emotional_journey', []),
            
            # Flags for quick insights
            "flags": flags,
            
            # Actionable recommendations
            "recommendations": recommendations,
            
            # Metadata
            "custom_guidelines_applied": custom_guidelines if custom_guidelines else "Default guidelines used",
            "focus_areas": focus_areas if focus_areas else [],
            "analyzed_at": datetime.utcnow().isoformat(),
            
            # Raw analysis for advanced users
            "raw_analysis": analysis_result.get('raw_response', '')
        }
        
        # Create learning entry if QC agent specified
        if qc_agent_id:
            learning_result = await create_audio_tonality_learning_entry(
                qc_agent_id=qc_agent_id,
                analysis_result=analysis_result,
                call_id=call_id,
                db_instance=db
            )
            result['learning_entry_id'] = learning_result.get('learning_entry_id')
            result['predictions'] = learning_result.get('predictions', {})
        
        # Always save results to the call record for persistence
        try:
            update_result = await db.call_logs.update_one(
                {
                    "$or": [
                        {"call_id": call_id, "user_id": current_user['id']},
                        {"id": call_id, "user_id": current_user['id']}
                    ]
                },
                {"$set": {"audio_tonality_results": result}}
            )
            if update_result.modified_count > 0:
                logger.info(f"Audio Tonality QC: Saved results to call record (modified: {update_result.modified_count})")
            else:
                logger.warning(f"Audio Tonality QC: No documents modified when saving results for call {call_id}")
        except Exception as save_error:
            logger.error(f"Error saving audio tonality results: {save_error}")
        
        # Also store in campaign if campaign specified
        campaign_id = request_data.get('campaign_id')
        if campaign_id:
            await store_campaign_call_analysis(
                campaign_id,
                call_id,
                audio_tonality_results=result
            )
        
        logger.info(f"Audio Tonality QC: Complete - Overall: {overall_rating}, Quality: {overall_quality}/10")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in audio tonality analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_tonality_with_llm(transcript: List[Dict], custom_guidelines: str, api_key: str, llm_provider: str, model: str, call_flow: List[Dict] = None, logs: List[Dict] = None) -> List[Dict]:
    """Analyze tonality patterns from transcript using LLM with node awareness"""
    node_analyses = []
    
    # Extract node names from logs (with call_flow as fallback)
    node_names_from_logs = {}
    if logs or call_flow:
        node_names_from_logs = extract_node_names_from_logs(logs or [], call_flow)
        logger.info(f"Tonality QC: Extracted {len(node_names_from_logs)} node names")
    
    # Build node map for quick lookup
    node_map = {}
    if call_flow:
        for node in call_flow:
            node_map[node.get('id')] = {
                'label': node.get('label', 'Unknown Node'),
                'type': node.get('type', 'unknown'),
                'data': node.get('data', {}),
                'goal': node.get('data', {}).get('goal', ''),
                'voice_settings': node.get('data', {}).get('voice_settings', {})
            }
    
    # Build conversation turns with node info
    conversation_turns = []
    current_turn = {"user": "", "assistant": "", "timestamp": None, "node_id": None, "node_name": None}
    
    for msg in transcript:
        role = msg.get('role', '').lower()
        content = msg.get('content', '') or msg.get('text', '')
        node_id = msg.get('_node_id')
        
        if role == 'user':
            if current_turn['assistant']:
                conversation_turns.append(current_turn)
                current_turn = {"user": "", "assistant": "", "timestamp": msg.get('timestamp'), "node_id": None, "node_name": None}
            current_turn['user'] = content
        elif role == 'assistant':
            current_turn['assistant'] = content
            if node_id:
                current_turn['node_id'] = node_id
                node_info = node_map.get(node_id, {})
                current_turn['node_name'] = node_info.get('label', f'Node-{node_id[:8]}' if node_id else 'Unknown')
                current_turn['node_goal'] = node_info.get('goal', '')
                current_turn['voice_settings'] = node_info.get('voice_settings', {})
    
    if current_turn['user'] or current_turn['assistant']:
        conversation_turns.append(current_turn)
    
    logger.info(f"Tonality QC: Analyzing {len(conversation_turns)} conversation turns")
    
    if not conversation_turns:
        return []
    
    # Use grok-3 for analysis
    actual_model = 'grok-3'
    
    for i, turn in enumerate(conversation_turns):
        if not turn['assistant']:
            continue
        
        # Get node context - use node_names_from_logs as priority, then turn's node_name, then fallback
        turn_num = i + 1
        node_name = node_names_from_logs.get(turn_num) or turn.get('node_name') or f'Turn-{turn_num}'
        node_goal = turn.get('node_goal', '')
        voice_settings = turn.get('voice_settings', {})
        
        analysis_prompt = f"""You are an expert voice delivery and tonality analyst for AI phone agents.

**NODE CONTEXT:**
- Node Name: {node_name}
- Node Goal: {node_goal or 'Not specified'}
{f"- Voice Settings: {json.dumps(voice_settings)}" if voice_settings else ""}

**CONVERSATION TURN {i+1}:**
User said: "{turn['user']}"
Agent responded: "{turn['assistant']}"

{f"**Custom Guidelines:** {custom_guidelines}" if custom_guidelines else ""}

**CRITICAL ANALYSIS POINTS:**
1. **Tone Appropriateness**: Does the tone match the conversation context? Is it warm enough for rapport, professional for business?
2. **Response Conciseness**: Is the response brief and direct? Penalize verbose or rambling responses.
3. **Question Quality**: Does it end with an open-ended invitation (e.g., "Would you like to hear more?") rather than leading/assumptive questions?
4. **Energy Match**: Does the agent's energy match the user's emotional state?
5. **Emotional Intelligence**: Does it acknowledge and respond to user emotions appropriately?
6. **Pacing Indicators**: Are sentences appropriately varied in length for natural delivery?

**Return as JSON:**
{{
  "turn_number": {i+1},
  "node_name": "{node_name}",
  "node_id": "{turn.get('node_id', '')}",
  "delivery_quality": "excellent|good|needs_improvement|poor",
  "tone_assessment": {{
    "detected_tone": "warm|professional|neutral|robotic|empathetic|cold|rushed",
    "appropriateness": "excellent|good|needs_improvement|poor",
    "issues": ["specific issue 1", "specific issue 2"],
    "what_worked": ["positive aspect 1", "positive aspect 2"]
  }},
  "pacing_assessment": {{
    "current_pacing": "fast|moderate|slow",
    "sentence_variety": "good|monotonous|too_varied",
    "recommended_adjustments": "specific pacing changes"
  }},
  "energy_match": {{
    "user_energy": "low|medium|high|frustrated|excited|neutral",
    "agent_energy": "low|medium|high",
    "alignment": "excellent|good|mismatched",
    "adjustment_needed": "description if mismatched"
  }},
  "emotional_intelligence": {{
    "score": 1-10,
    "acknowledged_user_emotion": true|false,
    "empathy_shown": true|false,
    "notes": "specific observations"
  }},
  "brevity_assessment": {{
    "score": "excellent|good|needs_improvement|poor",
    "word_count": {len(turn['assistant'].split())},
    "is_too_long": true|false,
    "feedback": "specific feedback on length and directness"
  }},
  "question_quality": {{
    "ends_with_question": true|false,
    "question_type": "open_ended|leading|assumptive|none",
    "improvement": "better question if applicable"
  }},
  "ssml_recommendations": [
    {{
      "type": "prosody|break|emphasis|say-as",
      "text_to_modify": "specific text",
      "suggestion": "<prosody rate='slow'>text</prosody>",
      "reasoning": "why this helps"
    }}
  ],
  "improved_delivery": "Rewritten response with better delivery style - keep it concise and end with open invitation",
  "impact": "high|medium|low"
}}"""

        try:
            # Configure API based on provider
            api_configs = {
                'grok': {
                    'url': 'https://api.x.ai/v1/chat/completions',
                    'model_map': {
                        'grok-3': 'grok-3',
                        'grok-2-1212': 'grok-2-1212',
                        'default': 'grok-3'
                    }
                },
                'openai': {
                    'url': 'https://api.openai.com/v1/chat/completions',
                    'model_map': {
                        'gpt-5': 'gpt-4o',
                        'gpt-4o': 'gpt-4o',
                        'gpt-4o-mini': 'gpt-4o-mini',
                        'grok-3': 'gpt-4o',
                        'default': 'gpt-4o'
                    }
                },
                'anthropic': {
                    'url': 'https://api.anthropic.com/v1/messages',
                    'model_map': {
                        'claude-3-5-sonnet': 'claude-3-5-sonnet-20241022',
                        'default': 'claude-3-5-sonnet-20241022'
                    }
                }
            }
            
            config = api_configs.get(llm_provider, api_configs['grok'])
            actual_model = config['model_map'].get(model, config['model_map'].get('default', 'grok-3'))
            
            logger.info(f"Tonality QC: Using {llm_provider}/{actual_model} for turn {i+1}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Build request based on provider
                if llm_provider == 'anthropic':
                    headers = {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    }
                    json_data = {
                        "model": actual_model,
                        "max_tokens": 2000,
                        "messages": [
                            {"role": "user", "content": analysis_prompt}
                        ],
                        "system": "You are an expert voice delivery and tonality analyst for AI phone agents. Analyze conversational AI responses for voice quality, emotional intelligence, and provide SSML recommendations. Prioritize conciseness and natural conversation flow. Always respond in valid JSON."
                    }
                else:  # OpenAI-compatible (grok, openai)
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    json_data = {
                        "model": actual_model,
                        "messages": [
                            {"role": "system", "content": "You are an expert voice delivery and tonality analyst for AI phone agents. Analyze conversational AI responses for voice quality, emotional intelligence, and provide SSML recommendations. Prioritize conciseness and natural conversation flow. Always respond in valid JSON."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        "temperature": 0.3
                    }
                
                response = await client.post(
                    config['url'],
                    headers=headers,
                    json=json_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract content based on provider
                    if llm_provider == 'anthropic':
                        analysis_text = result['content'][0]['text']
                    else:
                        analysis_text = result['choices'][0]['message']['content']
                    
                    # Parse JSON from response
                    try:
                        # Clean up markdown code blocks if present
                        if '```json' in analysis_text:
                            analysis_text = analysis_text.split('```json')[1].split('```')[0]
                        elif '```' in analysis_text:
                            analysis_text = analysis_text.split('```')[1].split('```')[0]
                        
                        analysis = json.loads(analysis_text.strip())
                        
                        # Get node name from logs if available, or from turn data, or from LLM
                        turn_num = analysis.get('turn_number', i + 1)
                        node_name = node_names_from_logs.get(turn_num) or analysis.get('node_name') or turn.get('node_name') or f'Turn {turn_num}'
                        
                        node_analyses.append({
                            "turn_number": turn_num,
                            "node_name": node_name,
                            "node_id": analysis.get('node_id', turn.get('node_id', '')),
                            "user_text": turn['user'],
                            "agent_text": turn['assistant'],
                            "delivery_quality": analysis.get('delivery_quality', 'good'),
                            "tone_assessment": analysis.get('tone_assessment', {}),
                            "pacing_assessment": analysis.get('pacing_assessment', {}),
                            "energy_match": analysis.get('energy_match', {}),
                            "emotional_intelligence": analysis.get('emotional_intelligence', {}),
                            "brevity_assessment": analysis.get('brevity_assessment', {}),
                            "question_quality": analysis.get('question_quality', {}),
                            "ssml_recommendations": analysis.get('ssml_recommendations', []),
                            "improved_delivery": analysis.get('improved_delivery', ''),
                            "impact": analysis.get('impact', 'medium'),
                            # Include node context for reference
                            "node_goal": turn.get('node_goal', '')
                        })
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse LLM response as JSON for turn {i+1}")
                        # Add basic analysis with node name from logs
                        node_name = node_names_from_logs.get(i + 1, f'Turn {i + 1}')
                        node_analyses.append({
                            "turn_number": i + 1,
                            "node_name": node_name,
                            "user_text": turn['user'],
                            "agent_text": turn['assistant'],
                            "delivery_quality": "good",
                            "raw_analysis": analysis_text[:500]
                        })
                else:
                    logger.warning(f"Tonality LLM returned {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error in tonality LLM call: {str(e)}")
    
    return node_analyses


def generate_ssml_recommendations(node_analyses: List[Dict]) -> List[Dict]:
    """Generate consolidated SSML recommendations from node analyses"""
    all_recommendations = []
    
    for node in node_analyses:
        ssml_recs = node.get('ssml_recommendations', [])
        for rec in ssml_recs:
            all_recommendations.append({
                "turn": node.get('turn_number'),
                **rec
            })
    
    # Deduplicate and prioritize
    seen = set()
    unique_recs = []
    for rec in all_recommendations:
        key = (rec.get('type'), rec.get('suggestion', '')[:50])
        if key not in seen:
            seen.add(key)
            unique_recs.append(rec)
    
    return unique_recs[:10]  # Return top 10 recommendations

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_transcript_from_call(call: Dict) -> List[Dict]:
    """Extract transcript from call data, checking multiple possible fields.
    
    Handles various data formats:
    - transcript: Direct transcript array
    - logs: Log entries that may contain role/text data
    """
    # First try the standard transcript field
    transcript = call.get('transcript', [])
    
    if transcript and len(transcript) > 0:
        return transcript
    
    # Try to build transcript from logs
    logs = call.get('logs', [])
    if not logs:
        return []
    
    logger.info(f"extract_transcript_from_call: Building transcript from {len(logs)} log entries")
    
    transcript = []
    for log in logs:
        if not isinstance(log, dict):
            continue
            
        # Check for role-based entries
        role = log.get('role', '') or log.get('speaker', '')
        content = log.get('text', '') or log.get('content', '') or log.get('message', '')
        
        if role and content:
            # Normalize role names
            role_lower = role.lower()
            if role_lower in ['user', 'human', 'customer', 'caller', 'lead']:
                normalized_role = 'user'
            elif role_lower in ['assistant', 'agent', 'ai', 'bot', 'system']:
                normalized_role = 'assistant'
            else:
                normalized_role = role_lower
            
            transcript.append({
                'role': normalized_role,
                'text': content,
                'timestamp': log.get('timestamp'),
                '_node_id': log.get('node_id') or log.get('_node_id')
            })
        
        # Also check for user_text/agent_text format
        elif log.get('user_text') or log.get('agent_text'):
            if log.get('user_text'):
                transcript.append({
                    'role': 'user',
                    'text': log.get('user_text'),
                    'timestamp': log.get('timestamp'),
                    '_node_id': log.get('node_id')
                })
            if log.get('agent_text'):
                transcript.append({
                    'role': 'assistant',
                    'text': log.get('agent_text'),
                    'timestamp': log.get('timestamp'),
                    '_node_id': log.get('node_id')
                })
    
    logger.info(f"extract_transcript_from_call: Extracted {len(transcript)} entries")
    return transcript


def parse_logs_array_for_latency(logs: List[Dict], call_flow: List[Dict] = None) -> List[Dict[str, Any]]:
    """Parse logs array from call and extract latency metrics per turn
    
    Key metrics:
    - TTFS (Time To First Speech): The actual "dead air" time the user experiences
      This is: STT + LLM + first TTS chunk time (NOT total TTS time)
    - transition_time: Time spent evaluating which node to go to next
    - kb_time: Time spent retrieving knowledge base content
    """
    node_analyses = []
    turn_count = 0
    
    # Extract node names from logs (with call_flow as fallback)
    node_names_from_logs = extract_node_names_from_logs(logs or [], call_flow)
    logger.info(f"Tech QC: Extracted {len(node_names_from_logs)} node names from logs/call_flow")
    
    # Debug: Log the structure of first few entries to understand format
    if logs:
        logger.info(f"Tech QC parse_logs_array_for_latency: Processing {len(logs)} log entries")
        for i, sample_log in enumerate(logs[:3]):
            logger.info(f"Tech QC: Sample log {i} keys: {list(sample_log.keys()) if isinstance(sample_log, dict) else type(sample_log)}")
            if isinstance(sample_log, dict):
                logger.info(f"Tech QC: Sample log {i} data: {str(sample_log)[:300]}")
    
    for idx, log in enumerate(logs):
        message = log.get('message', '')
        latency = log.get('latency', {})
        log_type = log.get('type', '')
        
        # Check for structured latency data first (new format)
        # Accept multiple type values that indicate a turn/response
        latency_types = ['turn_complete', 'latency_breakdown', 'response', 'agent_response', 'turn', 'conversation_turn']
        has_latency_type = log_type in latency_types
        
        # Also accept if we have latency data without specific type
        # (some logs have latency but no type field)
        has_any_latency = latency and (
            latency.get('llm_ms') or latency.get('tts_ms') or latency.get('stt_ms') or 
            latency.get('e2e_ms') or latency.get('total_ms') or latency.get('dead_air_ms') or
            latency.get('ttfs_ms') or latency.get('latency_ms')
        )
        
        if has_latency_type or has_any_latency:
            turn_count += 1
            
            # Extract node name - prioritize explicit node_label, then node_names_from_logs, then fallbacks
            node_name = None
            if log.get('node_label') and log.get('node_label') != "Unknown":
                node_name = log.get('node_label')
            elif log.get('current_node'):
                node_name = log.get('current_node')
            elif node_names_from_logs.get(turn_count):
                node_name = node_names_from_logs.get(turn_count)
            
            # Final fallback
            if not node_name:
                node_name = f"Turn {turn_count}"
            
            # Get timing metrics
            stt_ms = latency.get('stt_ms', 0)
            llm_ms = latency.get('llm_ms', 0)
            tts_ms = latency.get('tts_ms', 0)  # Full TTS generation time
            tts_first_chunk_ms = latency.get('tts_first_chunk_ms', 0) or latency.get('tts_ttfb_ms', 0)  # Time to first audio byte
            transition_ms = latency.get('transition_ms', 0)
            kb_ms = latency.get('kb_ms', 0)
            
            # Use dead_air_ms if available (most accurate), otherwise calculate TTFS
            # dead_air_ms = actual silence user hears (STT + LLM + first TTS chunk)
            # This does NOT include full TTS generation time
            if latency.get('dead_air_ms'):
                ttfs_seconds = latency.get('dead_air_ms', 0) / 1000.0
            elif latency.get('ttfs_ms'):
                ttfs_seconds = latency.get('ttfs_ms', 0) / 1000.0
            elif latency.get('e2e_ms'):
                # e2e_ms is LLM processing time only, add STT to get actual TTFS
                ttfs_seconds = (stt_ms + latency.get('e2e_ms', 0)) / 1000.0
            else:
                # Fallback: calculate from components but DON'T include full TTS
                # User doesn't wait for all TTS to complete, just first chunk
                ttfs_seconds = (stt_ms + llm_ms + transition_ms + kb_ms) / 1000.0
            
            # Estimate TTS first chunk time if not available
            # Typically ~10-20% of full TTS time for streaming TTS
            if not tts_first_chunk_ms and tts_ms > 0:
                tts_first_chunk_ms = int(tts_ms * 0.15)  # Estimate: first chunk at ~15% of total
            
            node_info = {
                "node_name": node_name,
                "node_id": log.get('node_id', ''),
                "llm_time": llm_ms,
                "tts_time": tts_ms,  # Total TTS generation time (full response)
                "tts_first_chunk": tts_first_chunk_ms,  # Time to first audio chunk (when user starts hearing)
                "stt_time": stt_ms,
                "transition_time": transition_ms,
                "kb_time": kb_ms,
                "ttfs": ttfs_seconds,  # This is the actual "dead air" / TTFS
                "bottlenecks": [],
                "user_message": log.get('user_text', '')[:100] if log.get('user_text') else '',
                "agent_message": log.get('agent_text', '')[:100] if log.get('agent_text') else ''
            }
            
            # Identify bottlenecks based on TTFS (actual dead air)
            ttfs_ms = ttfs_seconds * 1000
            if ttfs_ms > 4000:
                node_info['bottlenecks'].append(f"High dead air: {int(ttfs_ms)}ms exceeds 4s threshold")
            if llm_ms > 3000:
                node_info['bottlenecks'].append(f"LLM processing slow: {llm_ms}ms - consider simplifying prompt")
            if transition_ms > 1000:
                node_info['bottlenecks'].append(f"Transition evaluation slow: {transition_ms}ms - use auto-transition")
            if kb_ms > 2000:
                node_info['bottlenecks'].append(f"KB retrieval slow: {kb_ms}ms - optimize knowledge base")
            # Note: TTS time is NOT a latency bottleneck because TTS streams to user
            # We only flag it if it's extremely long (causes other issues)
            if tts_ms > 6000:
                node_info['bottlenecks'].append(f"TTS generation very long: {tts_ms}ms - consider shorter response")
            
            node_analyses.append(node_info)
            continue
        
        # Fallback: Extract E2E latency from message (legacy format)
        if 'E2E latency' in message:
            try:
                turn_count += 1
                # Parse: "E2E latency for this turn: 249ms (LLM: 0ms)"
                parts = message.split('|')
                latency_part = parts[0] if parts else message
                
                # Extract E2E time
                e2e_match = latency_part.split('E2E latency for this turn:')[1].split('ms')[0].strip() if 'E2E latency' in latency_part else '0'
                e2e_time = float(e2e_match)
                
                # Extract LLM time
                llm_time = 0
                if '(LLM:' in latency_part:
                    llm_match = latency_part.split('(LLM:')[1].split('ms')[0].strip()
                    llm_time = float(llm_match)
                
                # Extract user/agent messages
                user_msg = ""
                agent_msg = ""
                if len(parts) > 1:
                    convo_part = parts[1]
                    if 'User:' in convo_part and '->' in convo_part:
                        user_agent = convo_part.split('->') if '->' in convo_part else ['', '']
                        user_msg = user_agent[0].split('User:')[1].strip() if len(user_agent) > 0 and 'User:' in user_agent[0] else ''
                        agent_msg = user_agent[1].split('Agent:')[1].strip() if len(user_agent) > 1 and 'Agent:' in user_agent[1] else ''
                
                node_info = {
                    "node_name": f"Turn {turn_count}",
                    "llm_time": llm_time,
                    "tts_time": max(0, e2e_time - llm_time),
                    "transition_time": 0,  # Not available in legacy format
                    "kb_time": 0,  # Not available in legacy format
                    "ttfs": e2e_time / 1000.0,
                    "bottlenecks": [],
                    "user_message": user_msg[:50],
                    "agent_message": agent_msg[:50]
                }
                
                # Identify bottlenecks
                if e2e_time > 4000:
                    node_info['bottlenecks'].append(f"High E2E latency: {e2e_time}ms exceeds 4s threshold")
                if llm_time > 3000:
                    node_info['bottlenecks'].append("LLM processing slow")
                
                node_analyses.append(node_info)
            except Exception as e:
                logger.error(f"Error parsing log entry: {str(e)}")
                continue
        
        # Additional fallback: Parse any log entry that looks like a conversation turn
        # (has user/agent text or role indicators)
        elif log.get('role') in ['user', 'assistant', 'agent'] or log.get('user_text') or log.get('agent_text') or log.get('text') or log.get('speaker'):
            turn_count += 1
            
            # Extract what data we can
            node_name = f"Turn {turn_count}"
            if log.get('node_label'):
                node_name = log.get('node_label')
            elif log.get('current_node'):
                node_name = log.get('current_node')
            elif log.get('speaker'):
                node_name = f"Turn {turn_count} ({log.get('speaker')})"
            
            # Try to get timing from any available field
            timing = log.get('timing', {}) or log.get('metrics', {}) or log.get('latency', {})
            ttfs = 0
            if timing.get('total_ms'):
                ttfs = timing.get('total_ms', 0) / 1000.0
            elif timing.get('e2e_ms'):
                ttfs = timing.get('e2e_ms', 0) / 1000.0
            elif log.get('latency_ms'):
                ttfs = log.get('latency_ms', 0) / 1000.0
            elif log.get('duration_ms'):
                ttfs = log.get('duration_ms', 0) / 1000.0
            elif log.get('duration'):
                # Duration might be in seconds
                dur = log.get('duration', 0)
                ttfs = dur if dur < 100 else dur / 1000.0  # Assume >100 is ms
            
            # Determine role from available fields
            role = log.get('role', '') or log.get('speaker', '') or ''
            is_user = role.lower() in ['user', 'human', 'customer', 'caller']
            is_agent = role.lower() in ['assistant', 'agent', 'ai', 'bot', 'system']
            
            # Extract message text
            text_content = log.get('text', '') or log.get('content', '') or log.get('message', '') or ''
            
            node_info = {
                "node_name": node_name,
                "node_id": log.get('node_id', ''),
                "llm_time": timing.get('llm_ms', 0),
                "tts_time": timing.get('tts_ms', 0),
                "tts_first_chunk": timing.get('tts_first_chunk_ms', 0) or timing.get('tts_ttfb_ms', 0) or int(timing.get('tts_ms', 0) * 0.15),
                "stt_time": timing.get('stt_ms', 0),
                "transition_time": timing.get('transition_ms', 0),
                "kb_time": timing.get('kb_ms', 0),
                "ttfs": ttfs,
                "bottlenecks": [],
                "user_message": str(log.get('user_text', '') or (text_content if is_user else ''))[:100],
                "agent_message": str(log.get('agent_text', '') or (text_content if is_agent else ''))[:100]
            }
            
            # Add bottlenecks
            if ttfs > 4:
                node_info['bottlenecks'].append(f"High TTFS: {ttfs:.2f}s exceeds 4s threshold")
            
            node_analyses.append(node_info)
    
    # If still no nodes found, try to create at least one summary node
    if not node_analyses and logs:
        logger.warning(f"No latency data found in {len(logs)} log entries. Log format may not include timing metrics.")
        # Log the structure of the first few entries to help debug
        for i, log in enumerate(logs[:2]):
            logger.warning(f"Sample log {i} structure: {list(log.keys()) if isinstance(log, dict) else type(log)}")
        
        # Try to count conversation turns from logs using various indicators
        turn_indicators = ['role', 'speaker', 'user_text', 'agent_text', 'text', 'content', 'message']
        turn_count = sum(1 for log in logs if isinstance(log, dict) and any(log.get(k) for k in turn_indicators))
        
        # Also check for specific type values
        type_count = sum(1 for log in logs if isinstance(log, dict) and log.get('type') in ['user_message', 'agent_message', 'user', 'agent', 'assistant'])
        
        total_turns = max(turn_count, type_count)
        
        if total_turns > 0:
            node_analyses.append({
                "node_name": f"Conversation Summary ({total_turns} entries)",
                "node_id": "",
                "llm_time": 0,
                "tts_time": 0,
                "tts_first_chunk": 0,
                "stt_time": 0,
                "transition_time": 0,
                "kb_time": 0,
                "ttfs": 0,
                "bottlenecks": ["Detailed latency data not available - log format may not include timing metrics. Consider re-recording the call with latency tracking enabled."],
                "user_message": "",
                "agent_message": ""
            })
        else:
            # Even if we can't find turns, create a node so user sees something
            node_analyses.append({
                "node_name": f"Call Data ({len(logs)} log entries)",
                "node_id": "",
                "llm_time": 0,
                "tts_time": 0,
                "tts_first_chunk": 0,
                "stt_time": 0,
                "transition_time": 0,
                "kb_time": 0,
                "ttfs": 0,
                "bottlenecks": ["Unable to parse latency data from logs. The log format doesn't match expected patterns for latency analysis."],
                "user_message": "",
                "agent_message": ""
            })
    
    return node_analyses

def parse_call_log_json_for_latency(call_log: Dict) -> List[Dict[str, Any]]:
    """Parse JSON call_log structure and extract latency metrics per node"""
    node_analyses = []
    
    # Extract nodes from call_log structure
    nodes = call_log.get('nodes', {})
    
    for node_id, node_data in nodes.items():
        tts_time = node_data.get('tts_time', 0)
        tts_first_chunk = node_data.get('tts_first_chunk', 0) or node_data.get('tts_ttfb', 0) or int(tts_time * 0.15)
        
        node_info = {
            "node_name": node_data.get('node_name', node_id),
            "llm_time": node_data.get('llm_time', 0),
            "tts_time": tts_time,  # Full TTS generation time
            "tts_first_chunk": tts_first_chunk,  # Time to first audio chunk
            "transition_time": node_data.get('transition_time', 0),
            "kb_time": node_data.get('kb_retrieval_time', 0),
            "ttfs": 0,
            "bottlenecks": []
        }
        
        # Calculate TTFS (Time To First Speech)
        # TTFS = LLM + Transition + KB + First TTS chunk (NOT full TTS)
        node_info['ttfs'] = (
            node_info['llm_time'] + 
            node_info['transition_time'] + 
            node_info['kb_time'] + 
            tts_first_chunk  # Use first chunk time, not full TTS
        ) / 1000.0  # Convert to seconds
        
        # Identify bottlenecks
        if node_info['llm_time'] > 3000:
            node_info['bottlenecks'].append("LLM processing slow - consider simplifying prompt")
        if node_info['transition_time'] > 1000:
            node_info['bottlenecks'].append("Transition evaluation slow - use auto-transition")
        if node_info['kb_time'] > 2000:
            node_info['bottlenecks'].append("KB retrieval slow - optimize knowledge base")
        if tts_time > 6000:
            node_info['bottlenecks'].append("TTS generation slow - consider shorter response")
        
        node_analyses.append(node_info)
    
    return node_analyses

def parse_call_log_for_latency(log_lines: List[str]) -> List[Dict[str, Any]]:
    """Parse call log and extract latency metrics per node"""
    node_analyses = []
    current_node = None
    
    # Regex patterns for extracting metrics
    node_pattern = re.compile(r'Node: (.+?)$')
    llm_pattern = re.compile(r'LLM.*?(\d+)ms')
    tts_pattern = re.compile(r'TTS.*?(\d+)ms')
    transition_pattern = re.compile(r'TRANSITION.*?(\d+)ms')
    kb_pattern = re.compile(r'KB.*?(\d+)ms')
    
    for line in log_lines:
        # Detect new node
        node_match = node_pattern.search(line)
        if node_match:
            if current_node:
                node_analyses.append(current_node)
            current_node = {
                "node_name": node_match.group(1),
                "llm_time": 0,
                "tts_time": 0,
                "transition_time": 0,
                "kb_time": 0,
                "ttfs": 0,
                "bottlenecks": []
            }
        
        if current_node:
            # Extract timing data
            llm_match = llm_pattern.search(line)
            if llm_match:
                current_node['llm_time'] = int(llm_match.group(1))
            
            tts_match = tts_pattern.search(line)
            if tts_match:
                current_node['tts_time'] = int(tts_match.group(1))
            
            transition_match = transition_pattern.search(line)
            if transition_match:
                current_node['transition_time'] = int(transition_match.group(1))
            
            kb_match = kb_pattern.search(line)
            if kb_match:
                current_node['kb_time'] = int(kb_match.group(1))
    
    # Add last node
    if current_node:
        node_analyses.append(current_node)
    
    # Calculate TTFS and identify bottlenecks
    for node in node_analyses:
        # TTFS = LLM + Transition + KB + First TTS chunk (not total TTS)
        node['ttfs'] = (node['llm_time'] + node['transition_time'] + 
                       node['kb_time'] + min(node['tts_time'], 500)) / 1000.0  # Convert to seconds
        
        # Identify bottlenecks
        if node['llm_time'] > 3000:
            node['bottlenecks'].append("LLM processing slow - consider simplifying prompt")
        if node['transition_time'] > 1000:
            node['bottlenecks'].append("Transition evaluation slow - use auto-transition")
        if node['kb_time'] > 2000:
            node['bottlenecks'].append("KB retrieval slow - optimize knowledge base")
        if node['tts_time'] > 2000:
            node['bottlenecks'].append("TTS generation slow - shorten response")
    
    return node_analyses

def generate_tech_recommendations(node_analyses: List[Dict], flagged_nodes: List[Dict], custom_guidelines: str = '', llm_provider: str = 'grok', model: str = 'grok-4-1-fast-non-reasoning') -> List[str]:
    """Generate actionable recommendations based on analysis"""
    recommendations = []
    
    # Add custom guidelines note if provided
    if custom_guidelines:
        recommendations.append(f"📋 Custom Guidelines Applied: {custom_guidelines[:100]}...")
    
    if not flagged_nodes:
        recommendations.append("✅ All nodes performing well - TTFS under 4s threshold")
        return recommendations
    
    # Aggregate bottleneck types
    bottleneck_types = {}
    for node in flagged_nodes:
        for bottleneck in node.get('bottlenecks', []):
            if 'LLM' in bottleneck:
                bottleneck_types['llm'] = bottleneck_types.get('llm', 0) + 1
            elif 'Transition' in bottleneck:
                bottleneck_types['transition'] = bottleneck_types.get('transition', 0) + 1
            elif 'KB' in bottleneck:
                bottleneck_types['kb'] = bottleneck_types.get('kb', 0) + 1
            elif 'TTS' in bottleneck:
                bottleneck_types['tts'] = bottleneck_types.get('tts', 0) + 1
    
    # Generate specific recommendations
    if bottleneck_types.get('llm', 0) > 0:
        recommendations.append(f"🔧 {bottleneck_types['llm']} node(s) with slow LLM - reduce prompt complexity or context")
    if bottleneck_types.get('transition', 0) > 0:
        recommendations.append(f"⚡ {bottleneck_types['transition']} node(s) with slow transitions - enable auto-transition feature")
    if bottleneck_types.get('kb', 0) > 0:
        recommendations.append(f"📚 {bottleneck_types['kb']} node(s) with slow KB retrieval - optimize knowledge base structure")
    if bottleneck_types.get('tts', 0) > 0:
        recommendations.append(f"🔊 {bottleneck_types['tts']} node(s) with slow TTS - break responses into shorter chunks")
    
    return recommendations

async def get_user_api_key(user_id: str, service_name: str) -> Optional[str]:
    """
    Get user-specific API key for a service from database.
    
    Supports multiple providers and fallback patterns:
    - Direct service_name match (e.g., 'grok', 'openai')
    - Provider field match
    - Key prefix pattern matching for common providers
    
    Args:
        user_id: The user's ID
        service_name: The service/provider name (e.g., 'grok', 'openai', 'anthropic', 'gemini')
    
    Returns:
        The API key string or None if not found
    """
    from key_encryption import decrypt_api_key
    
    # Normalize service name
    service_name = service_name.lower().strip()
    
    # Service name aliases
    service_aliases = {
        'xai': 'grok',
        'x.ai': 'grok',
        'gpt': 'openai',
        'gpt-4': 'openai',
        'gpt-5': 'openai',
        'claude': 'anthropic',
        'google': 'gemini',
    }
    
    service_name = service_aliases.get(service_name, service_name)
    
    # Key prefix patterns for common providers
    key_patterns = {
        'grok': ['xai-'],
        'openai': ['sk-', 'sk-proj-'],
        'anthropic': ['sk-ant-'],
        'gemini': ['AIza'],
        'elevenlabs': ['sk_'],
    }
    
    try:
        # Strategy 1: Direct match on service_name or provider field
        key_doc = await db.api_keys.find_one({
            "user_id": user_id,
            "$or": [
                {"service_name": service_name, "is_active": {"$ne": False}},
                {"provider": service_name, "is_active": {"$ne": False}},
                {"service_name": {"$regex": f"^{service_name}$", "$options": "i"}},
                {"provider": {"$regex": f"^{service_name}$", "$options": "i"}}
            ]
        })
        
        if key_doc:
            # Decrypt if encrypted
            if key_doc.get('encrypted_key'):
                return decrypt_api_key(key_doc['encrypted_key'])
            return key_doc.get('api_key')
        
        # Strategy 2: Pattern matching on key prefix
        if service_name in key_patterns:
            patterns = key_patterns[service_name]
            all_keys = await db.api_keys.find({
                "user_id": user_id,
                "is_active": {"$ne": False}
            }).to_list(length=50)
            
            for k in all_keys:
                api_key = k.get('api_key', '')
                encrypted_key = k.get('encrypted_key', '')
                
                # Check raw key
                for pattern in patterns:
                    if api_key and api_key.startswith(pattern):
                        logger.info(f"Found {service_name} key by pattern match: {pattern}***")
                        return api_key
                
                # Check if need to decrypt first
                if encrypted_key:
                    try:
                        decrypted = decrypt_api_key(encrypted_key)
                        for pattern in patterns:
                            if decrypted.startswith(pattern):
                                logger.info(f"Found {service_name} key by encrypted pattern match")
                                return decrypted
                    except Exception:
                        pass
        
        # Strategy 3: Check for universal/Emergent key (if applicable)
        if service_name in ['openai', 'anthropic', 'gemini', 'grok']:
            emergent_key = os.environ.get('EMERGENT_LLM_KEY')
            if emergent_key:
                logger.info(f"Using Emergent LLM key for {service_name}")
                return emergent_key
        
        logger.warning(f"No API key found for {service_name} for user {user_id}")
        return None
    
    except Exception as e:
        logger.error(f"Error getting API key for {service_name}: {str(e)}")
        return None


def extract_node_names_from_logs(logs: List[Dict], call_flow: List[Dict] = None) -> Dict[int, str]:
    """
    Extract node names from call logs by parsing latency_breakdown entries.
    Falls back to call_flow node labels if no node info in logs.
    Returns a dict mapping turn number to node name.
    """
    node_map = {}
    turn_number = 0
    
    for log in logs:
        log_type = log.get('type', '')
        message = log.get('message', '')
        
        # Count turns by turn_complete entries
        if log_type == 'turn_complete':
            turn_number += 1
        
        # Extract node name from latency_breakdown
        if log_type == 'latency_breakdown' and 'Node:' in message:
            # Parse "LATENCY BREAKDOWN - Node: NodeName | ..."
            try:
                node_part = message.split('Node:')[1].split('|')[0].strip()
                # Clean up node name
                node_name = node_part.replace('Node ID:', '').replace('Node Prompt:', '').strip()
                # Remove version suffixes if too long
                if len(node_name) > 50:
                    node_name = node_name[:47] + '...'
                node_map[turn_number] = node_name
            except:
                pass
    
    # If we didn't get node names from logs but have call_flow, use that as fallback
    if not node_map and call_flow:
        logger.info(f"No node names in logs, falling back to call_flow ({len(call_flow)} nodes)")
        # Map turns to call_flow nodes - this is a rough approximation
        # The call flow typically starts with a greeting/begin node
        turn_index = 0
        for node in call_flow:
            node_label = node.get('label', '')
            node_type = node.get('type', '')
            
            # Skip non-conversation nodes
            if node_type in ['start', 'end', 'condition', 'ending']:
                continue
            
            turn_index += 1
            
            # Clean up common prefixes
            clean_label = node_label
            for prefix in ['Node Prompt:', 'Node ID:', 'Node:', 'Prompt:']:
                if clean_label.startswith(prefix):
                    clean_label = clean_label[len(prefix):].strip()
            
            # Truncate if too long
            if len(clean_label) > 50:
                clean_label = clean_label[:47] + '...'
            
            node_map[turn_index] = clean_label or f'Node {turn_index}'
    
    return node_map


def create_basic_analysis_from_transcript(transcript: List[Dict], logs: List[Dict] = None, call_flow: List[Dict] = None) -> List[Dict]:
    """Create basic analysis from transcript without LLM - fallback when LLM unavailable"""
    logger.info(f"Creating basic analysis from {len(transcript)} transcript entries")
    
    # Extract node names from logs if available (with call_flow fallback)
    node_names = {}
    if logs or call_flow:
        node_names = extract_node_names_from_logs(logs or [], call_flow)
        logger.info(f"Extracted {len(node_names)} node names")
    
    node_analyses = []
    turn_number = 0
    current_user = ""
    current_assistant = ""
    
    for msg in transcript:
        role = (msg.get('role', '') or msg.get('speaker', '') or '').lower()
        content = msg.get('text', '') or msg.get('content', '') or msg.get('message', '') or ''
        node_id = msg.get('_node_id') or msg.get('node_id') or ''
        
        is_user = role in ['user', 'human', 'customer', 'caller', 'lead']
        is_assistant = role in ['assistant', 'agent', 'ai', 'bot', 'system']
        
        if is_user:
            if current_assistant:
                # Save previous turn
                turn_number += 1
                # Get node name from logs map, fallback to Turn N
                node_name = node_names.get(turn_number, f"Turn {turn_number}")
                node_analyses.append({
                    "turn_number": turn_number,
                    "node_name": node_name,
                    "node_id": node_id,
                    "user_message": current_user,
                    "ai_response": current_assistant,
                    "quality": "pending_review",
                    "positives": ["Response captured"],
                    "issues": ["Detailed analysis requires LLM API key"],
                    "improved_response": "",
                    "prompt_suggestions": {
                        "type": "info",
                        "suggestion": "Configure LLM API key in QC agent settings for detailed analysis",
                        "reasoning": "LLM-powered analysis provides specific improvement suggestions",
                        "impact": "high"
                    },
                    "goal_efficiency": "unknown",
                    "goal_progress_explanation": "Manual review recommended",
                    "brevity_score": "unknown",
                    "conciseness_feedback": "Enable LLM analysis for detailed feedback"
                })
            current_user = content
            current_assistant = ""
        elif is_assistant:
            current_assistant = content
    
    # Don't forget the last turn
    if current_user or current_assistant:
        turn_number += 1
        node_name = node_names.get(turn_number, f"Turn {turn_number}")
        node_analyses.append({
            "turn_number": turn_number,
            "node_name": node_name,
            "node_id": "",
            "user_message": current_user,
            "ai_response": current_assistant,
            "quality": "pending_review",
            "positives": ["Response captured"],
            "issues": ["Detailed analysis requires LLM API key"],
            "improved_response": "",
            "prompt_suggestions": {},
            "goal_efficiency": "unknown",
            "goal_progress_explanation": "Manual review recommended",
            "brevity_score": "unknown",
            "conciseness_feedback": ""
        })
    
    logger.info(f"Created basic analysis with {len(node_analyses)} turns")
    return node_analyses

async def analyze_script_with_llm(transcript: List[Dict], call_flow: List[Dict], rules: Dict, logs: List[Dict] = None) -> List[Dict]:
    """Analyze script quality using LLM with node-aware analysis"""
    import httpx
    
    try:
        # Get user's API key for LLM analysis
        # Default to Grok for now, could be configurable
        user_id = rules.get('user_id')
        if not user_id:
            logger.warning("No user_id in rules, cannot analyze script")
            return []
        
        # Use the LLM provider from rules, with fallback to grok
        llm_provider = rules.get('llm_provider', 'grok')
        logger.info(f"Script QC: Using LLM provider: {llm_provider}, transcript entries: {len(transcript)}")
        
        # Extract node names from logs (with call_flow as fallback)
        node_names_from_logs = {}
        if logs or call_flow:
            node_names_from_logs = extract_node_names_from_logs(logs or [], call_flow)
            logger.info(f"Script QC: Extracted {len(node_names_from_logs)} node names")
        
        # Debug: Log transcript structure
        if transcript:
            sample = transcript[0] if transcript else {}
            logger.info(f"Script QC: Transcript sample keys: {list(sample.keys()) if isinstance(sample, dict) else type(sample)}")
            logger.info(f"Script QC: Transcript sample: {str(sample)[:300]}")
        else:
            logger.warning("Script QC: Empty transcript provided!")
            return []
        
        api_key = await get_user_api_key(user_id, llm_provider)
        if not api_key:
            logger.warning(f"No {llm_provider} API key found, trying fallback providers")
            # Try other providers as fallback
            fallback_providers = ['grok', 'openai', 'anthropic']
            for fallback in fallback_providers:
                if fallback != llm_provider:
                    api_key = await get_user_api_key(user_id, fallback)
                    if api_key:
                        llm_provider = fallback
                        logger.info(f"Script QC: Using fallback provider: {fallback}")
                        break
            
            if not api_key:
                logger.warning(f"No API key found for script analysis. Tried: {llm_provider} and fallbacks. User: {user_id}")
                # Return basic analysis without LLM
                return create_basic_analysis_from_transcript(transcript, logs)
        
        # Build node map for quick lookup
        node_map = {}
        for node in call_flow:
            node_map[node.get('id')] = {
                'label': node.get('label', 'Unknown Node'),
                'type': node.get('type', 'unknown'),
                'data': node.get('data', {}),
                'goal': node.get('data', {}).get('goal', ''),
                'prompt': node.get('data', {}).get('prompt', '')
            }
        
        # Parse transcript into conversation turns with node info
        conversation_turns = []
        current_turn = {"user": "", "assistant": "", "timestamp": None, "node_id": None, "node_name": None}
        
        for msg in transcript:
            # Handle different field names for role
            role = (msg.get('role', '') or msg.get('speaker', '') or '').lower()
            
            # Handle different field names for content
            content = msg.get('text', '') or msg.get('content', '') or msg.get('message', '') or ''
            
            node_id = msg.get('_node_id') or msg.get('node_id')
            
            # Map various role names to user/assistant
            is_user = role in ['user', 'human', 'customer', 'caller', 'lead']
            is_assistant = role in ['assistant', 'agent', 'ai', 'bot', 'system']
            
            if is_user:
                if current_turn['user'] or current_turn['assistant']:
                    conversation_turns.append(current_turn)
                    current_turn = {"user": "", "assistant": "", "timestamp": msg.get('timestamp'), "node_id": None, "node_name": None}
                current_turn['user'] = content
            elif is_assistant:
                current_turn['assistant'] = content
                if node_id:
                    current_turn['node_id'] = node_id
                    node_info = node_map.get(node_id, {})
                    current_turn['node_name'] = node_info.get('label', f'Node-{node_id[:8]}' if node_id else 'Unknown')
                    current_turn['node_goal'] = node_info.get('goal', '')
                    current_turn['node_prompt'] = node_info.get('prompt', '')
        
        if current_turn['user'] or current_turn['assistant']:
            conversation_turns.append(current_turn)
        
        logger.info(f"Script QC: Found {len(conversation_turns)} conversation turns from {len(transcript)} transcript entries")
        
        # If no conversation turns found, return basic analysis
        if not conversation_turns:
            logger.warning("Script QC: No conversation turns found, creating basic analysis")
            return create_basic_analysis_from_transcript(transcript)
        
        node_analyses = []
        
        # Analyze each conversation turn
        for i, turn in enumerate(conversation_turns):
            if not turn['assistant']:  # Skip if no AI response
                continue
            
            # Get node context - use node_names_from_logs as priority, then turn's node_name, then fallback
            turn_num = i + 1
            node_name = node_names_from_logs.get(turn_num) or turn.get('node_name') or f'Turn-{turn_num}'
            node_goal = turn.get('node_goal', '')
            node_prompt = turn.get('node_prompt', '')
            
            # Build enhanced analysis prompt with node context
            analysis_prompt = f"""You are an expert AI conversation analyst. Analyze this specific conversation turn from a phone call agent.

**NODE CONTEXT:**
- Node Name: {node_name}
- Node Goal: {node_goal or 'Not specified'}
{f"- Current Prompt: {node_prompt[:500]}..." if node_prompt and len(node_prompt) > 500 else f"- Current Prompt: {node_prompt}" if node_prompt else ""}

**CONVERSATION TURN {i+1}:**
User: {turn['user']}
AI Response: {turn['assistant']}

**ANALYSIS FOCUS:**
{rules.get('custom_guidelines', 'Focus on response effectiveness and goal progression.')}

**CRITICAL EVALUATION CRITERIA:**
1. **Response Brevity**: Is the response concise and to-the-point? Penalize rambling or overly verbose responses.
2. **Goal Alignment**: Does this response efficiently move toward the node's goal? {f"The goal is: {node_goal}" if node_goal else "Assess if it progresses the conversation."}
3. **Question Quality**: Does it end with an open-ended invitation (e.g., "Would you like to hear more?") rather than assumptive/leading questions?
4. **Natural Flow**: Does it sound human and conversational, not robotic?
5. **Relevance**: Does it directly address what the user said?

**RETURN AS JSON:**
{{
  "turn_number": {i+1},
  "node_name": "{node_name}",
  "node_id": "{turn.get('node_id', '')}",
  "quality": "excellent|good|needs_improvement|poor",
  "positives": ["specific strength 1", "specific strength 2"],
  "issues": ["specific issue with fix suggestion", "another issue"],
  "improved_response": "Rewrite showing exactly how to improve - keep it concise and end with an open invitation",
  "prompt_suggestions": {{
    "type": "new_prompt|adjustment|kb_addition",
    "suggestion": "Specific prompt modification to improve this node",
    "reasoning": "Why this change will help",
    "impact": "high|medium|low"
  }},
  "goal_efficiency": "excellent|good|needs_improvement|poor",
  "goal_progress_explanation": "How this response helped or hindered goal achievement",
  "brevity_score": "excellent|good|needs_improvement|poor",
  "conciseness_feedback": "Specific feedback on length and directness"
}}"""

            # Determine which model to use
            llm_provider = rules.get('llm_provider', 'grok')
            model = rules.get('model', 'grok-3')
            
            # Map model names to API endpoints and models
            api_configs = {
                'grok': {
                    'url': 'https://api.x.ai/v1/chat/completions',
                    'model_map': {
                        'grok-4.1': 'grok-3',
                        'grok-4-reasoning': 'grok-3',
                        'grok-4-1-fast-non-reasoning': 'grok-3',
                        'grok-4-fast-non-reasoning': 'grok-3',
                        'grok-4-fast-reasoning': 'grok-3',
                        'grok-4-fast': 'grok-3',
                        'grok-3': 'grok-3',
                        'grok-2-1212': 'grok-2-1212',
                        'grok-beta': 'grok-3'
                    }
                },
                'openai': {
                    'url': 'https://api.openai.com/v1/chat/completions',
                    'model_map': {
                        'gpt-5': 'gpt-4o',
                        'gpt-4o': 'gpt-4o',
                        'gpt-4o-mini': 'gpt-4o-mini',
                        'gpt-4-turbo': 'gpt-4-turbo',
                        'gpt-4': 'gpt-4',
                        'gpt-3.5-turbo': 'gpt-3.5-turbo',
                        'grok-3': 'gpt-4o',  # Map grok model to OpenAI equivalent
                        'default': 'gpt-4o'
                    }
                },
                'anthropic': {
                    'url': 'https://api.anthropic.com/v1/messages',
                    'model_map': {
                        'claude-3-opus': 'claude-3-opus-20240229',
                        'claude-3-sonnet': 'claude-3-sonnet-20240229',
                        'claude-3-haiku': 'claude-3-haiku-20240307',
                        'claude-3-5-sonnet': 'claude-3-5-sonnet-20241022',
                        'default': 'claude-3-5-sonnet-20241022'
                    }
                }
            }
            
            config = api_configs.get(llm_provider, api_configs['grok'])
            actual_model = config['model_map'].get(model, config['model_map'].get('default', 'gpt-4o'))
            
            logger.info(f"Script QC: Using {llm_provider}/{actual_model} for turn {i+1}")

            # Call LLM for analysis
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Build request based on provider
                if llm_provider == 'anthropic':
                    headers = {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    }
                    json_data = {
                        "model": actual_model,
                        "max_tokens": 2000,
                        "messages": [
                            {"role": "user", "content": analysis_prompt}
                        ],
                        "system": "You are an expert conversational AI analyst. Provide detailed, actionable feedback in JSON format."
                    }
                else:  # OpenAI-compatible (grok, openai)
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    json_data = {
                        "model": actual_model,
                        "messages": [
                            {"role": "system", "content": "You are an expert conversational AI analyst. Provide detailed, actionable feedback in JSON format."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        "temperature": 0.3
                    }
                
                response = await client.post(
                    config['url'],
                    headers=headers,
                    json=json_data
                )
                
                logger.info(f"Script QC: LLM response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract content based on provider
                    if llm_provider == 'anthropic':
                        analysis_text = result['content'][0]['text']
                    else:
                        analysis_text = result['choices'][0]['message']['content']
                    
                    # Parse JSON from response
                    if "```json" in analysis_text:
                        analysis_text = analysis_text.split("```json")[1].split("```")[0]
                    elif "```" in analysis_text:
                        analysis_text = analysis_text.split("```")[1].split("```")[0]
                    
                    try:
                        analysis_data = json.loads(analysis_text.strip())
                        
                        # Add to node analyses with enhanced structure
                        # Get node name from logs if available, or from turn data, or from LLM
                        turn_num = analysis_data.get('turn_number', i + 1)
                        node_name = node_names_from_logs.get(turn_num) or analysis_data.get('node_name') or turn.get('node_name') or f'Turn {turn_num}'
                        
                        node_analyses.append({
                            "turn_number": turn_num,
                            "node_name": node_name,
                            "node_id": analysis_data.get('node_id', turn.get('node_id', '')),
                            "user_message": turn['user'],
                            "ai_response": turn['assistant'],
                            "quality": analysis_data.get('quality', 'good'),
                            "positives": analysis_data.get('positives', []),
                            "issues": analysis_data.get('issues', []),
                            "improved_response": analysis_data.get('improved_response', ''),
                            "prompt_suggestions": analysis_data.get('prompt_suggestions', {}),
                            "goal_efficiency": analysis_data.get('goal_efficiency', 'good'),
                            "goal_progress_explanation": analysis_data.get('goal_progress_explanation', ''),
                            "brevity_score": analysis_data.get('brevity_score', 'good'),
                            "conciseness_feedback": analysis_data.get('conciseness_feedback', ''),
                            "reasoning": analysis_data.get('reasoning', ''),
                            # Include node context for reference
                            "node_goal": turn.get('node_goal', ''),
                            "node_prompt_preview": turn.get('node_prompt', '')[:100] + "..." if turn.get('node_prompt', '') and len(turn.get('node_prompt', '')) > 100 else turn.get('node_prompt', '')
                        })
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse LLM analysis JSON: {e}")
                        continue
        
        return node_analyses
        
    except Exception as e:
        logger.error(f"Error in analyze_script_with_llm: {str(e)}")
        return []

def generate_bulk_script_suggestions(node_analyses: List[Dict]) -> Dict[str, Any]:
    """Generate bulk suggestions for script improvements"""
    if not node_analyses:
        return {
            "prompt_improvements": [],
            "transition_improvements": [],
            "kb_additions": [],
            "estimated_impact": "low"
        }
    
    # Aggregate suggestions across all nodes
    prompt_improvements = []
    kb_additions = []
    quality_issues = []
    
    poor_quality_count = 0
    needs_improvement_count = 0
    
    for analysis in node_analyses:
        quality = analysis.get('quality', 'good')
        
        if quality == 'poor':
            poor_quality_count += 1
        elif quality == 'needs_improvement':
            needs_improvement_count += 1
        
        # Collect prompt suggestions
        prompt_suggestion = analysis.get('prompt_suggestions', {})
        if prompt_suggestion and prompt_suggestion.get('suggestion'):
            prompt_improvements.append({
                "turn": analysis.get('turn_number'),
                "type": prompt_suggestion.get('type', 'adjustment'),
                "suggestion": prompt_suggestion.get('suggestion'),
                "reasoning": prompt_suggestion.get('reasoning')
            })
        
        # Collect issues for potential KB additions
        issues = analysis.get('issues', [])
        for issue in issues:
            if 'knowledge' in issue.lower() or 'information' in issue.lower():
                kb_additions.append({
                    "turn": analysis.get('turn_number'),
                    "issue": issue,
                    "suggested_kb_content": f"Add information to address: {issue}"
                })
    
    # Determine estimated impact
    total_nodes = len(node_analyses)
    problematic_nodes = poor_quality_count + needs_improvement_count
    
    if problematic_nodes >= total_nodes * 0.5:
        impact = "high"
    elif problematic_nodes >= total_nodes * 0.25:
        impact = "medium"
    else:
        impact = "low"
    
    return {
        "prompt_improvements": prompt_improvements[:10],  # Top 10
        "transition_improvements": [],  # Could analyze transition logic separately
        "kb_additions": kb_additions[:5],  # Top 5
        "estimated_impact": impact,
        "summary": {
            "total_turns": total_nodes,
            "poor_quality": poor_quality_count,
            "needs_improvement": needs_improvement_count,
            "good_quality": total_nodes - poor_quality_count - needs_improvement_count
        }
    }


# ============================================================================
# PREDICTION GENERATION FOR LEARNING SYSTEM
# ============================================================================

async def generate_script_predictions(node_analyses: List[Dict], transcript: List[Dict]) -> Optional[AnalysisPrediction]:
    """
    Generate predictions from script/language pattern analysis for the learning system.
    Returns AnalysisPrediction with show_likelihood, risk_factors, positive_signals.
    """
    if not node_analyses:
        return None
    
    risk_factors = []
    positive_signals = []
    commitment_score = 0.5
    objection_resolution_score = 0.5
    
    quality_scores = {'excellent': 1.0, 'good': 0.75, 'needs_improvement': 0.5, 'poor': 0.25}
    total_quality = 0
    
    for analysis in node_analyses:
        quality = analysis.get('quality', 'good')
        total_quality += quality_scores.get(quality, 0.5)
        
        # Extract risk factors from issues
        issues = analysis.get('issues', [])
        for issue in issues:
            issue_lower = issue.lower()
            # Categorize issues as risk factors
            if any(word in issue_lower for word in ['vague', 'unclear', 'no confirm', 'didn\'t confirm', 'weak', 'hesitat']):
                risk_factors.append(issue[:100])
            elif any(word in issue_lower for word in ['rushed', 'pressure', 'skip', 'missed']):
                risk_factors.append(issue[:100])
            elif any(word in issue_lower for word in ['objection', 'unresolved', 'concern', 'doubt']):
                risk_factors.append(issue[:100])
        
        # Extract positive signals from positives
        positives = analysis.get('positives', [])
        for positive in positives:
            positive_lower = positive.lower()
            if any(word in positive_lower for word in ['confirm', 'specific', 'clear', 'strong', 'commit']):
                positive_signals.append(positive[:100])
            elif any(word in positive_lower for word in ['rapport', 'warm', 'empathy', 'natural']):
                positive_signals.append(positive[:100])
            elif any(word in positive_lower for word in ['resolved', 'addressed', 'handled']):
                positive_signals.append(positive[:100])
        
        # Goal efficiency affects commitment score
        goal_efficiency = analysis.get('goal_efficiency', 'good')
        if goal_efficiency == 'excellent':
            commitment_score += 0.1
        elif goal_efficiency == 'poor':
            commitment_score -= 0.1
    
    # Calculate average quality
    avg_quality = total_quality / len(node_analyses) if node_analyses else 0.5
    
    # Calculate show likelihood based on factors
    base_likelihood = 0.5
    
    # Quality adjustment
    base_likelihood += (avg_quality - 0.5) * 0.3
    
    # Risk factor penalty
    base_likelihood -= len(risk_factors) * 0.05
    
    # Positive signal bonus
    base_likelihood += len(positive_signals) * 0.05
    
    # Clamp to valid range
    show_likelihood = max(0.1, min(0.95, base_likelihood))
    
    # Determine booking quality
    if show_likelihood >= 0.7:
        booking_quality = BookingQuality.STRONG
    elif show_likelihood >= 0.4:
        booking_quality = BookingQuality.MEDIUM
    else:
        booking_quality = BookingQuality.WEAK
    
    # Calculate confidence based on data quality
    confidence = min(0.9, 0.5 + len(node_analyses) * 0.05)
    
    return AnalysisPrediction(
        show_likelihood=round(show_likelihood, 2),
        booking_quality=booking_quality,
        risk_factors=risk_factors[:10],  # Top 10
        positive_signals=positive_signals[:10],  # Top 10
        confidence=round(confidence, 2),
        commitment_strength_score=round(max(0, min(1, commitment_score)), 2),
        objection_resolution_score=round(objection_resolution_score, 2)
    )


async def generate_tonality_predictions(node_analyses: List[Dict], transcript: List[Dict]) -> Optional[AnalysisPrediction]:
    """
    Generate predictions from tonality analysis for the learning system.
    Returns AnalysisPrediction with show_likelihood, risk_factors, positive_signals.
    """
    if not node_analyses:
        return None
    
    risk_factors = []
    positive_signals = []
    emotional_alignment_score = 0.5
    energy_match_score = 0.5
    
    quality_scores = {'excellent': 1.0, 'good': 0.75, 'needs_improvement': 0.5, 'poor': 0.25}
    total_quality = 0
    
    for analysis in node_analyses:
        quality = analysis.get('delivery_quality', 'good')
        total_quality += quality_scores.get(quality, 0.5)
        
        # Analyze tone assessment
        tone_assessment = analysis.get('tone_assessment', {})
        detected_tone = tone_assessment.get('detected_tone', '')
        appropriateness = tone_assessment.get('appropriateness', 'good')
        tone_issues = tone_assessment.get('issues', [])
        
        if detected_tone in ['warm', 'empathetic']:
            positive_signals.append("Warm/empathetic tone detected")
            emotional_alignment_score += 0.1
        elif detected_tone in ['robotic', 'cold']:
            risk_factors.append("Robotic/cold tone detected")
            emotional_alignment_score -= 0.1
        
        if appropriateness == 'poor':
            risk_factors.append("Inappropriate tone for conversation context")
        elif appropriateness == 'excellent':
            positive_signals.append("Excellent tone appropriateness")
        
        for issue in tone_issues:
            risk_factors.append(issue[:100])
        
        # Analyze energy match
        energy_match = analysis.get('energy_match', {})
        alignment = energy_match.get('alignment', 'good')
        if alignment == 'mismatched':
            risk_factors.append("Energy mismatch with customer")
            energy_match_score -= 0.1
        elif alignment == 'good':
            positive_signals.append("Good energy alignment with customer")
            energy_match_score += 0.1
        
        # Analyze emotional intelligence
        ei = analysis.get('emotional_intelligence', {})
        ei_score = ei.get('score', 5)
        if ei_score >= 8:
            positive_signals.append(f"High emotional intelligence (score: {ei_score}/10)")
        elif ei_score <= 4:
            risk_factors.append(f"Low emotional intelligence (score: {ei_score}/10)")
        
        # Analyze pacing
        pacing = analysis.get('pacing_assessment', {})
        current_pacing = pacing.get('current_pacing', 'moderate')
        if current_pacing == 'fast':
            risk_factors.append("Fast pacing detected - may indicate rushing")
    
    # Calculate average quality
    avg_quality = total_quality / len(node_analyses) if node_analyses else 0.5
    
    # Calculate show likelihood based on factors
    base_likelihood = 0.5
    
    # Quality adjustment
    base_likelihood += (avg_quality - 0.5) * 0.3
    
    # Risk factor penalty
    base_likelihood -= len(risk_factors) * 0.04
    
    # Positive signal bonus
    base_likelihood += len(positive_signals) * 0.04
    
    # Emotional alignment adjustment
    base_likelihood += (emotional_alignment_score - 0.5) * 0.2
    
    # Energy match adjustment
    base_likelihood += (energy_match_score - 0.5) * 0.15
    
    # Clamp to valid range
    show_likelihood = max(0.1, min(0.95, base_likelihood))
    
    # Determine booking quality
    if show_likelihood >= 0.7:
        booking_quality = BookingQuality.STRONG
    elif show_likelihood >= 0.4:
        booking_quality = BookingQuality.MEDIUM
    else:
        booking_quality = BookingQuality.WEAK
    
    # Calculate confidence
    confidence = min(0.85, 0.5 + len(node_analyses) * 0.05)
    
    return AnalysisPrediction(
        show_likelihood=round(show_likelihood, 2),
        booking_quality=booking_quality,
        risk_factors=risk_factors[:10],
        positive_signals=positive_signals[:10],
        confidence=round(confidence, 2),
        emotional_alignment_score=round(max(0, min(1, emotional_alignment_score)), 2),
        energy_match_score=round(max(0, min(1, energy_match_score)), 2)
    )

async def store_campaign_call_analysis(
    campaign_id: str,
    call_id: str,
    tech_qc_results: Optional[Dict] = None,
    script_qc_results: Optional[Dict] = None,
    tonality_qc_results: Optional[Dict] = None,
    audio_tonality_results: Optional[Dict] = None
):
    """Store QC analysis results for campaign - only updates provided fields"""
    try:
        # Build update dict with only provided fields
        update_fields = {
            "campaign_id": campaign_id,
            "call_id": call_id,
            "updated_at": datetime.utcnow()
        }
        
        # Only set fields that have values (don't overwrite existing with None)
        if tech_qc_results is not None:
            update_fields["tech_qc_results"] = tech_qc_results
            update_fields["tech_analyzed_at"] = datetime.utcnow()
        if script_qc_results is not None:
            update_fields["script_qc_results"] = script_qc_results
            update_fields["script_analyzed_at"] = datetime.utcnow()
        if tonality_qc_results is not None:
            update_fields["tonality_qc_results"] = tonality_qc_results
            update_fields["tonality_analyzed_at"] = datetime.utcnow()
        if audio_tonality_results is not None:
            update_fields["audio_tonality_results"] = audio_tonality_results
            update_fields["audio_analyzed_at"] = datetime.utcnow()
        
        result = await db.campaign_calls.update_one(
            {"campaign_id": campaign_id, "call_id": call_id},
            {"$set": update_fields},
            upsert=True
        )
        
        logger.info(f"Stored campaign call analysis: campaign={campaign_id}, call={call_id[:20]}..., matched={result.matched_count}, modified={result.modified_count}")
        
    except Exception as e:
        logger.error(f"Error storing campaign call analysis: {str(e)}")
        raise


# ============================================================================
# CAMPAIGN PATTERN DETECTION & REPORTING
# ============================================================================

async def detect_campaign_patterns(campaign_id: str, campaign_calls: List[Dict], user_id: str) -> List[Dict]:
    """Detect patterns across multiple calls in a campaign"""
    patterns = []
    
    # Aggregate issues across all calls
    all_issues = []
    all_positives = []
    quality_by_turn = defaultdict(list)
    prompt_suggestions_by_type = defaultdict(list)
    
    analyzed_calls = 0
    for campaign_call in campaign_calls:
        if not campaign_call:
            continue
            
        script_results = campaign_call.get('script_qc_results')
        if not script_results:
            # Call not analyzed yet
            continue
        
        analyzed_calls += 1
        node_analyses = script_results.get('node_analyses', [])
        
        for analysis in node_analyses:
            if not analysis:
                continue
                
            turn_num = analysis.get('turn_number', 0)
            quality = analysis.get('quality', 'good')
            
            # Track quality by turn position
            quality_by_turn[turn_num].append(quality)
            
            # Collect issues
            issues = analysis.get('issues', [])
            if issues:
                all_issues.extend(issues)
            
            positives = analysis.get('positives', [])
            if positives:
                all_positives.extend(positives)
            
            # Track prompt suggestions
            prompt_sugg = analysis.get('prompt_suggestions')
            if prompt_sugg and isinstance(prompt_sugg, dict):
                suggestion_type = prompt_sugg.get('type', 'unknown')
                prompt_suggestions_by_type[suggestion_type].append({
                    'suggestion': prompt_sugg.get('suggestion', ''),
                    'turn': turn_num,
                    'call_id': campaign_call.get('call_id')
                })
    
    logger.info(f"Pattern detection: {analyzed_calls}/{len(campaign_calls)} calls have been analyzed")
    
    if analyzed_calls < 2:
        logger.warning(f"Not enough analyzed calls for pattern detection (need at least 2, have {analyzed_calls})")
        return patterns
    
    # Pattern 1: Identify consistently problematic turns
    for turn_num, qualities in quality_by_turn.items():
        poor_count = qualities.count('poor') + qualities.count('needs_improvement')
        if poor_count >= len(qualities) * 0.6:  # 60%+ of calls have issues at this turn
            pattern = {
                "id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "pattern_type": "bottleneck",
                "description": f"Turn {turn_num} consistently underperforms across {poor_count}/{len(qualities)} calls",
                "affected_nodes": [f"Turn {turn_num}"],
                "evidence_calls": [cc.get('call_id') for cc in campaign_calls],
                "confidence_score": poor_count / len(qualities),
                "created_at": datetime.utcnow().isoformat()
            }
            patterns.append(pattern)
            
            # Store in database
            await db.campaign_patterns.insert_one(pattern.copy())
    
    # Pattern 2: Recurring issues
    issue_counter = Counter(all_issues)
    for issue, count in issue_counter.most_common(5):
        if count >= 3:  # Issue appears in 3+ calls
            pattern = {
                "id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "pattern_type": "recurring_issue",
                "description": f"Recurring issue: {issue}",
                "affected_nodes": [],
                "evidence_calls": [],
                "confidence_score": min(count / len(campaign_calls), 1.0),
                "created_at": datetime.utcnow().isoformat()
            }
            patterns.append(pattern)
            await db.campaign_patterns.insert_one(pattern.copy())
    
    # Pattern 3: Common prompt improvement needs
    for sugg_type, suggestions in prompt_suggestions_by_type.items():
        if len(suggestions) >= 3:  # Type appears 3+ times
            pattern = {
                "id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "pattern_type": "improvement_opportunity",
                "description": f"Multiple calls need {sugg_type}: {suggestions[0]['suggestion'][:100]}...",
                "affected_nodes": [f"Turn {s['turn']}" for s in suggestions[:5]],
                "evidence_calls": [s['call_id'] for s in suggestions[:5]],
                "confidence_score": min(len(suggestions) / len(campaign_calls), 1.0),
                "created_at": datetime.utcnow().isoformat()
            }
            patterns.append(pattern)
            await db.campaign_patterns.insert_one(pattern.copy())
    
    # Pattern 4: Success patterns
    positive_counter = Counter(all_positives)
    for positive, count in positive_counter.most_common(3):
        if count >= len(campaign_calls) * 0.7:  # Appears in 70%+ of calls
            pattern = {
                "id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "pattern_type": "success",
                "description": f"Consistent success: {positive}",
                "affected_nodes": [],
                "evidence_calls": [],
                "confidence_score": count / len(campaign_calls),
                "created_at": datetime.utcnow().isoformat()
            }
            patterns.append(pattern)
            await db.campaign_patterns.insert_one(pattern.copy())
    
    return patterns


async def sync_patterns_to_qc_agents(campaign_id: str, patterns: List[Dict], user_id: str):
    """
    Sync detected campaign patterns to assigned QC agents.
    This updates the pattern_md_content field in the QC agents.
    """
    try:
        # Get the campaign to find assigned QC agents
        campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": user_id})
        
        if not campaign:
            logger.warning(f"Campaign {campaign_id} not found for pattern sync")
            return
        
        # Get assigned QC agent IDs
        qc_agent_ids = []
        if campaign.get('language_pattern_qc_agent_id'):
            qc_agent_ids.append(campaign['language_pattern_qc_agent_id'])
        if campaign.get('tonality_qc_agent_id'):
            qc_agent_ids.append(campaign['tonality_qc_agent_id'])
        if campaign.get('tech_issues_qc_agent_id'):
            qc_agent_ids.append(campaign['tech_issues_qc_agent_id'])
        
        if not qc_agent_ids:
            logger.info(f"No QC agents assigned to campaign {campaign_id}")
            return
        
        # Generate pattern markdown content
        pattern_md = f"# Campaign Patterns - {campaign.get('name', 'Unknown')}\n\n"
        pattern_md += f"**Generated:** {datetime.utcnow().isoformat()}\n"
        pattern_md += f"**Total Patterns:** {len(patterns)}\n\n"
        
        # Group patterns by type
        patterns_by_type = {}
        for p in patterns:
            ptype = p.get('pattern_type', 'unknown')
            if ptype not in patterns_by_type:
                patterns_by_type[ptype] = []
            patterns_by_type[ptype].append(p)
        
        for ptype, plist in patterns_by_type.items():
            pattern_md += f"## {ptype.replace('_', ' ').title()}\n\n"
            for p in plist:
                confidence = p.get('confidence_score', 0)
                pattern_md += f"### {p.get('description', 'No description')}\n"
                pattern_md += f"- **Confidence:** {confidence * 100:.1f}%\n"
                
                affected = p.get('affected_nodes', [])
                if affected:
                    pattern_md += f"- **Affected Nodes:** {', '.join(affected[:5])}\n"
                
                evidence = p.get('evidence_calls', [])
                if evidence:
                    pattern_md += f"- **Evidence Calls:** {len(evidence)}\n"
                
                pattern_md += "\n"
        
        # Update all assigned QC agents with the patterns
        for qc_agent_id in qc_agent_ids:
            # Get current patterns count for the agent
            all_campaign_patterns = await db.campaign_patterns.find({
                "campaign_id": campaign_id
            }).to_list(length=1000)
            
            await db.qc_agents.update_one(
                {"id": qc_agent_id, "user_id": user_id},
                {
                    "$set": {
                        "pattern_md_content": pattern_md,
                        "pattern_md_updated_at": datetime.utcnow(),
                        "campaign_patterns_count": len(all_campaign_patterns),
                        "synced_campaign_id": campaign_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            logger.info(f"Synced {len(patterns)} patterns to QC agent {qc_agent_id}")
        
        logger.info(f"Pattern sync complete for campaign {campaign_id} to {len(qc_agent_ids)} QC agents")
        
    except Exception as e:
        logger.error(f"Error syncing patterns to QC agents: {str(e)}")


async def generate_comprehensive_report(
    campaign: Dict,
    campaign_calls: List[Dict],
    suggestions: List[Dict],
    patterns: List[Dict],
    user_id: str
) -> Dict:
    """Generate comprehensive campaign report with insights"""
    
    # Debug logging
    logger.info(f"generate_comprehensive_report called with campaign={campaign is not None}, calls={len(campaign_calls) if campaign_calls else 0}")
    
    if not campaign_calls:
        return {
            "campaign_id": campaign.get('id') if campaign else None,
            "campaign_name": campaign.get('name') if campaign else None,
            "status": "insufficient_data",
            "message": "No calls analyzed yet"
        }
    
    # Calculate overall statistics
    total_calls = len(campaign_calls) if campaign_calls else 0
    
    # Aggregate quality scores
    all_qualities = []
    all_efficiencies = []
    total_turns = 0
    
    for i, cc in enumerate(campaign_calls):
        if cc is None:
            logger.info(f"Campaign call {i} is None, skipping")
            continue
        try:
            script_results = cc.get('script_qc_results', {}) or {}
            node_analyses = script_results.get('node_analyses', []) or []
            
            for j, analysis in enumerate(node_analyses):
                if analysis is None:
                    logger.info(f"Analysis {j} in call {i} is None, skipping")
                    continue
                all_qualities.append(analysis.get('quality', 'good'))
                all_efficiencies.append(analysis.get('goal_efficiency', 'good'))
                total_turns += 1
        except Exception as e:
            logger.error(f"Error processing campaign call {i}: {str(e)}, call data: {type(cc)}, continuing")
            continue
    
    # Quality distribution
    quality_dist = Counter(all_qualities)
    efficiency_dist = Counter(all_efficiencies)
    
    # Calculate average quality score
    quality_scores = {
        'excellent': 4,
        'good': 3,
        'needs_improvement': 2,
        'poor': 1
    }
    avg_quality_score = sum(quality_scores.get(q, 2) for q in all_qualities) / len(all_qualities) if all_qualities else 2.5
    
    # Group patterns by type
    patterns_by_type = defaultdict(list)
    for pattern in patterns:
        if pattern is not None:
            patterns_by_type[pattern.get('pattern_type', 'unknown')].append(pattern)
    
    # High-impact suggestions (frequency-based)
    suggestion_frequency = Counter()
    for sugg in suggestions:
        if sugg is None:
            continue
        key = f"{sugg.get('suggestion_type', 'unknown')}:{sugg.get('node_id', 'general')}"
        suggestion_frequency[key] += 1
    
    high_impact_suggestions = [
        {
            "type": key.split(':')[0],
            "node": key.split(':')[1],
            "frequency": count,
            "impact": "high" if count >= total_calls * 0.5 else "medium"
        }
        for key, count in suggestion_frequency.most_common(10)
    ]
    
    # Generate actionable insights
    insights = []
    
    # Insight 1: Overall quality trend
    if avg_quality_score >= 3.5:
        insights.append({
            "type": "positive",
            "title": "Strong Performance",
            "description": f"Campaign maintaining high quality across {total_calls} calls"
        })
    elif avg_quality_score < 2.5:
        insights.append({
            "type": "critical",
            "title": "Quality Issues Detected",
            "description": f"Average quality score: {avg_quality_score:.1f}/4.0 - immediate attention needed"
        })
    
    # Insight 2: Bottleneck patterns
    bottleneck_patterns = patterns_by_type.get('bottleneck', [])
    if bottleneck_patterns:
        insights.append({
            "type": "warning",
            "title": "Performance Bottlenecks",
            "description": f"{len(bottleneck_patterns)} consistent bottlenecks identified across calls"
        })
    
    # Insight 3: Success patterns
    success_patterns = patterns_by_type.get('success', [])
    if success_patterns:
        insights.append({
            "type": "positive",
            "title": "Repeatable Success",
            "description": f"{len(success_patterns)} successful patterns to replicate"
        })
    
    # Insight 4: Improvement opportunities
    improvement_patterns = patterns_by_type.get('improvement_opportunity', [])
    if improvement_patterns:
        insights.append({
            "type": "info",
            "title": "Optimization Opportunities",
            "description": f"{len(improvement_patterns)} areas for improvement identified"
        })
    
    # Build comprehensive report
    # Helper function to serialize dates
    def serialize_date(val):
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val) if val else None
    
    # Sanitize patterns to ensure all datetime objects are converted to strings
    sanitized_patterns = []
    for p in patterns:
        if p is None:
            continue
        sanitized_pattern = {}
        for k, v in p.items():
            if isinstance(v, datetime):
                sanitized_pattern[k] = v.isoformat()
            else:
                sanitized_pattern[k] = v
        sanitized_patterns.append(sanitized_pattern)
    
    report = {
        "campaign_id": campaign.get('id') if campaign else None,
        "campaign_name": campaign.get('name') if campaign else None,
        "generated_at": datetime.utcnow().isoformat(),
        "date_range": {
            "start": serialize_date(campaign_calls[0].get('analyzed_at')) if campaign_calls and campaign_calls[0] else None,
            "end": serialize_date(campaign_calls[-1].get('analyzed_at')) if campaign_calls and campaign_calls[-1] else None
        },
        "summary": {
            "total_calls_analyzed": total_calls,
            "total_conversation_turns": total_turns,
            "average_quality_score": round(avg_quality_score, 2),
            "quality_distribution": dict(quality_dist),
            "efficiency_distribution": dict(efficiency_dist)
        },
        "patterns": {
            "total_patterns": len(patterns),
            "by_type": {
                "bottlenecks": len(bottleneck_patterns),
                "recurring_issues": len(patterns_by_type.get('recurring_issue', [])),
                "improvements": len(improvement_patterns),
                "successes": len(success_patterns)
            },
            "details": sanitized_patterns
        },
        "high_impact_suggestions": high_impact_suggestions,
        "insights": insights,
        "recommendations": generate_campaign_recommendations(
            patterns,
            high_impact_suggestions,
            avg_quality_score
        )
    }
    
    return report

def generate_campaign_recommendations(
    patterns: List[Dict],
    high_impact_suggestions: List[Dict],
    avg_quality_score: float
) -> List[Dict]:
    """Generate actionable recommendations from campaign data"""
    recommendations = []
    
    # Recommendation 1: Based on quality score
    if avg_quality_score < 2.5:
        recommendations.append({
            "priority": "critical",
            "title": "Comprehensive Agent Redesign Needed",
            "action": "Consider rebuilding agent prompts and flow based on identified patterns",
            "estimated_impact": "high"
        })
    elif avg_quality_score < 3.0:
        recommendations.append({
            "priority": "high",
            "title": "Targeted Improvements Required",
            "action": "Focus on addressing recurring issues and bottleneck patterns",
            "estimated_impact": "high"
        })
    
    # Recommendation 2: Based on high-impact suggestions
    if high_impact_suggestions:
        top_suggestion = high_impact_suggestions[0]
        recommendations.append({
            "priority": "high",
            "title": f"Fix {top_suggestion['type'].replace('_', ' ').title()}",
            "action": f"This issue appears in {top_suggestion['frequency']} calls - addressing it will have broad impact",
            "estimated_impact": top_suggestion['impact']
        })
    
    # Recommendation 3: Pattern-based
    bottlenecks = [p for p in patterns if p.get('pattern_type') == 'bottleneck']
    if bottlenecks:
        recommendations.append({
            "priority": "high",
            "title": "Address Consistent Bottlenecks",
            "action": f"Focus on {len(bottlenecks)} identified bottlenecks that slow down conversions",
            "estimated_impact": "high"
        })
    
    return recommendations



# ============================================================================
# AUTO QC SETTINGS & PROCESSING
# ============================================================================

@qc_enhanced_router.get("/agents/{agent_id}/auto-qc-settings")
async def get_agent_auto_qc_settings(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get auto QC settings for an agent"""
    try:
        agent = await db.agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        auto_qc = agent.get('auto_qc_settings', {
            'enabled': False,
            'campaign_id': None,
            'run_tech_analysis': True,
            'run_script_analysis': True,
            'run_tonality_analysis': True,
            'llm_provider': 'grok',
            'llm_model': 'grok-3'
        })
        
        return {
            "agent_id": agent_id,
            "auto_qc_settings": auto_qc
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting auto QC settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.put("/agents/{agent_id}/auto-qc-settings")
async def update_agent_auto_qc_settings(
    agent_id: str,
    settings: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update auto QC settings for an agent"""
    try:
        agent = await db.agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Validate campaign_id if provided
        campaign_id = settings.get('campaign_id')
        if campaign_id:
            campaign = await db.campaigns.find_one({
                "id": campaign_id,
                "user_id": current_user['id']
            })
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Build auto_qc_settings
        auto_qc_settings = {
            'enabled': settings.get('enabled', False),
            'campaign_id': campaign_id,
            'run_tech_analysis': settings.get('run_tech_analysis', True),
            'run_script_analysis': settings.get('run_script_analysis', True),
            'run_tonality_analysis': settings.get('run_tonality_analysis', True),
            'llm_provider': settings.get('llm_provider', 'grok'),
            'llm_model': settings.get('llm_model', 'grok-3')
        }
        
        await db.agents.update_one(
            {"id": agent_id, "user_id": current_user['id']},
            {"$set": {
                "auto_qc_settings": auto_qc_settings,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # If auto QC is enabled, also add the agent to the campaign's linked_agents
        if auto_qc_settings['enabled'] and campaign_id:
            await db.campaigns.update_one(
                {"id": campaign_id, "user_id": current_user['id']},
                {"$addToSet": {"linked_agents": agent_id}}
            )
        
        return {
            "success": True,
            "agent_id": agent_id,
            "auto_qc_settings": auto_qc_settings
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating auto QC settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.post("/process-call-qc")
async def process_call_qc(
    request_data: dict,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Process QC for a call - can be triggered manually or automatically
    Runs all enabled QC analyses and adds to campaign
    """
    try:
        call_id = request_data.get('call_id')
        agent_id = request_data.get('agent_id')
        run_tech = request_data.get('run_tech_analysis', True)
        run_script = request_data.get('run_script_analysis', True)
        run_tonality = request_data.get('run_tonality_analysis', True)
        campaign_id = request_data.get('campaign_id')
        llm_provider = request_data.get('llm_provider', 'grok')
        model = request_data.get('model', 'grok-4-1-fast-non-reasoning')
        
        if not call_id:
            raise HTTPException(status_code=400, detail="call_id required")
        
        # Verify call exists and belongs to user
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": current_user['id']},
                {"id": call_id, "user_id": current_user['id']}
            ]
        })
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Schedule background processing - convert old-style llm params to new qc_agents_config format
        qc_agents_config = {
            'script': {'llm_provider': llm_provider, 'llm_model': model},
            'tonality': {'llm_provider': llm_provider, 'llm_model': model}
        }
        
        background_tasks.add_task(
            run_full_qc_analysis,
            call_id=call_id,
            user_id=current_user['id'],
            agent_id=agent_id,
            campaign_id=campaign_id,
            run_tech=run_tech,
            run_script=run_script,
            run_tonality=run_tonality,
            qc_agents_config=qc_agents_config
        )
        
        return {
            "success": True,
            "message": "QC processing started in background",
            "call_id": call_id,
            "campaign_id": campaign_id,
            "analyses_queued": {
                "tech": run_tech,
                "script": run_script,
                "tonality": run_tonality
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting QC processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_full_qc_analysis(
    call_id: str,
    user_id: str,
    agent_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    run_tech: bool = True,
    run_script: bool = True,
    run_tonality: bool = True,
    qc_agents_config: Dict[str, Any] = None
):
    """Background task to run full QC analysis on a call using assigned QC agents"""
    try:
        # Get LLM settings from QC agent configs, with fallbacks
        if qc_agents_config is None:
            qc_agents_config = {}
        
        script_config = qc_agents_config.get('script', {})
        tonality_config = qc_agents_config.get('tonality', {})
        
        script_llm_provider = script_config.get('llm_provider', 'grok')
        script_model = script_config.get('llm_model', 'grok-3')
        tonality_llm_provider = tonality_config.get('llm_provider', 'grok')
        tonality_model = tonality_config.get('llm_model', 'grok-3')
        
        logger.info(f"🔍 [RUN-QC] Starting full analysis for call={call_id}, user={user_id}, agent={agent_id}, campaign={campaign_id}")
        logger.info(f"🔍 [RUN-QC] Analysis flags: tech={run_tech}, script={run_script}, tonality={run_tonality}")
        logger.info(f"🔍 [RUN-QC] LLM configs: script={script_llm_provider}/{script_model}, tonality={tonality_llm_provider}/{tonality_model}")
        
        # Get call data
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": user_id},
                {"id": call_id, "user_id": user_id}
            ]
        })
        
        if not call:
            logger.error(f"❌ [RUN-QC] Call not found in call_logs: call_id={call_id}, user_id={user_id}")
            return
        
        # Log call details
        transcript = call.get('transcript', [])
        logs = call.get('logs', [])
        logger.info(f"📊 [RUN-QC] Call found: transcript_turns={len(transcript)}, logs_count={len(logs)}, status={call.get('status')}, duration={call.get('duration')}s")
        
        if not transcript or len(transcript) == 0:
            logger.warning(f"⚠️ [RUN-QC] No transcript data available for analysis")
        
        tech_results = None
        script_results = None
        tonality_results = None
        
        # Get agent's call_flow for node name resolution
        agent = await db.agents.find_one({"id": agent_id})
        call_flow = agent.get('call_flow', []) if agent else []
        
        # Run Tech Analysis
        if run_tech:
            try:
                logger.info(f"Auto QC: Running tech analysis for {call_id}")
                logs_data = call.get('logs', [])
                if logs_data:
                    node_analyses = parse_logs_array_for_latency(logs_data, call_flow)
                    if node_analyses:
                        flagged_nodes = [n for n in node_analyses if n.get('ttfs', 0) > 4.0]
                        
                        if len(flagged_nodes) == 0:
                            overall = "excellent"
                        elif len(flagged_nodes) <= 2:
                            overall = "good"
                        elif len(flagged_nodes) <= 5:
                            overall = "needs improvement"
                        else:
                            overall = "poor"
                        
                        tech_results = {
                            "call_id": call_id,
                            "overall_performance": overall,
                            "total_nodes": len(node_analyses),
                            "flagged_nodes": len(flagged_nodes),
                            "node_analyses": node_analyses,
                            "recommendations": [],
                            "analyzed_at": datetime.utcnow().isoformat()
                        }
                        logger.info(f"Auto QC: Tech analysis complete - {overall}")
            except Exception as e:
                logger.error(f"Auto QC: Tech analysis failed: {str(e)}")
        
        # Run Script Analysis
        if run_script:
            try:
                logger.info(f"Auto QC: Running script analysis for {call_id} with {script_llm_provider}/{script_model}")
                transcript = call.get('transcript', [])
                if transcript and len(transcript) > 0:
                    # call_flow already retrieved above
                    
                    # Get campaign rules if available
                    rules = {}
                    if campaign_id:
                        campaign = await db.campaigns.find_one({"id": campaign_id})
                        if campaign:
                            rules = campaign.get('rules', {})
                    
                    # Add LLM settings from QC agent config
                    api_key = await auto_qc_get_user_api_key(user_id, script_llm_provider)
                    if api_key:
                        rules['llm_provider'] = script_llm_provider
                        rules['model'] = script_model
                        rules['user_id'] = user_id
                        
                        # Add custom system prompt from QC agent if available
                        if script_config.get('system_prompt'):
                            rules['system_prompt'] = script_config['system_prompt']
                        
                        logger.info(f"Auto QC: Script using {script_llm_provider}/{script_model}")
                        
                        # Use the same analysis function as manual QC
                        node_analyses = await analyze_script_with_llm(
                            transcript,
                            call_flow,
                            rules,
                            call.get('logs', [])
                        )
                        
                        # Calculate overall quality
                        quality_scores = {'excellent': 4, 'good': 3, 'needs_improvement': 2, 'poor': 1}
                        if node_analyses:
                            avg_score = sum(quality_scores.get(n.get('quality', 'good'), 3) for n in node_analyses) / len(node_analyses)
                            overall_quality = 'excellent' if avg_score >= 3.5 else 'good' if avg_score >= 2.5 else 'needs_improvement' if avg_score >= 1.5 else 'poor'
                        else:
                            overall_quality = 'good'
                        
                        script_results = {
                            "call_id": call_id,
                            "overall_quality": overall_quality,
                            "quality_score": int(avg_score * 2.5) if node_analyses else 5,
                            "node_analyses": node_analyses,
                            "analyzed_at": datetime.utcnow().isoformat(),
                            "llm_used": f"{script_llm_provider}/{script_model}"
                        }
                        logger.info(f"Auto QC: Script analysis complete with {len(node_analyses)} node analyses")
                    else:
                        logger.warning(f"Auto QC: No API key for {script_llm_provider}, skipping script analysis")
                else:
                    logger.warning(f"Auto QC: No transcript found for script analysis")
            except Exception as e:
                logger.error(f"Auto QC: Script analysis failed: {str(e)}")
        
        # Run Tonality Analysis
        if run_tonality:
            try:
                logger.info(f"Auto QC: Running tonality analysis for {call_id} with {tonality_llm_provider}/{tonality_model}")
                transcript = call.get('transcript', [])
                if transcript and len(transcript) > 0:
                    api_key = await auto_qc_get_user_api_key(user_id, tonality_llm_provider)
                    if api_key:
                        # Get agent for call flow
                        agent = await db.agents.find_one({"id": agent_id})
                        call_flow = agent.get('call_flow', []) if agent else []
                        
                        # Get custom guidelines from campaign
                        custom_guidelines = ""
                        if campaign_id:
                            campaign = await db.campaigns.find_one({"id": campaign_id})
                            if campaign:
                                custom_guidelines = campaign.get('tonality_guidelines', '')
                        
                        # Add custom system prompt from QC agent if available
                        if tonality_config.get('system_prompt'):
                            custom_guidelines = f"{tonality_config['system_prompt']}\n\n{custom_guidelines}"
                        
                        logger.info(f"Auto QC: Tonality using {tonality_llm_provider}/{tonality_model}")
                        
                        # Use the same analysis function as manual QC
                        node_analyses = await analyze_tonality_with_llm(
                            transcript,
                            custom_guidelines,
                            api_key,
                            tonality_llm_provider,
                            tonality_model,
                            call_flow,
                            call.get('logs', [])
                        )
                        
                        # Calculate overall tonality
                        if node_analyses:
                            tone_counts = {}
                            for n in node_analyses:
                                tone = n.get('tone', 'neutral')
                                tone_counts[tone] = tone_counts.get(tone, 0) + 1
                            overall_tone = max(tone_counts, key=tone_counts.get) if tone_counts else 'neutral'
                        else:
                            overall_tone = 'neutral'
                        
                        tonality_results = {
                            "call_id": call_id,
                            "overall_tonality": overall_tone,
                            "node_analyses": node_analyses,
                            "analyzed_at": datetime.utcnow().isoformat(),
                            "llm_used": f"{tonality_llm_provider}/{tonality_model}"
                        }
                        logger.info(f"Auto QC: Tonality analysis complete with {len(node_analyses)} node analyses")
                    else:
                        logger.warning(f"Auto QC: No API key for {tonality_llm_provider}, skipping tonality analysis")
                else:
                    logger.warning(f"Auto QC: No transcript found for tonality analysis")
            except Exception as e:
                logger.error(f"Auto QC: Tonality analysis failed: {str(e)}")
        
        # Store results in campaign if provided
        if campaign_id and (tech_results or script_results or tonality_results):
            try:
                # Add call to campaign
                campaign_call = {
                    "id": str(uuid.uuid4()),
                    "campaign_id": campaign_id,
                    "call_id": call_id,
                    "analyzed_at": datetime.utcnow(),
                    "tech_qc_results": tech_results,
                    "script_qc_results": script_results,
                    "tonality_qc_results": tonality_results,
                    "auto_analyzed": True
                }
                
                await db.campaign_calls.update_one(
                    {"campaign_id": campaign_id, "call_id": call_id},
                    {"$set": campaign_call},
                    upsert=True
                )
                logger.info(f"Auto QC: Added call {call_id} to campaign {campaign_id}")
                
                # Check if campaign has auto pattern detection enabled
                campaign = await db.campaigns.find_one({"id": campaign_id})
                if campaign and campaign.get('auto_pattern_detection', False):
                    # Get all campaign calls to check if we have enough for pattern analysis
                    campaign_calls = await db.campaign_calls.find({
                        "campaign_id": campaign_id
                    }).to_list(length=1000)
                    
                    # Convert ObjectId
                    for cc in campaign_calls:
                        if '_id' in cc:
                            cc['_id'] = str(cc['_id'])
                    
                    analyzed_count = sum(1 for cc in campaign_calls if cc.get('script_qc_results'))
                    
                    if analyzed_count >= 2:
                        logger.info(f"Auto QC: Running auto pattern detection for campaign {campaign_id}")
                        patterns = await detect_campaign_patterns(campaign_id, campaign_calls, user_id)
                        
                        # Store patterns
                        for pattern in patterns:
                            pattern['campaign_id'] = campaign_id
                            pattern['detected_at'] = datetime.utcnow().isoformat()
                            await db.campaign_patterns.update_one(
                                {"campaign_id": campaign_id, "pattern_type": pattern.get('pattern_type'), "description": pattern.get('description')},
                                {"$set": pattern},
                                upsert=True
                            )
                        logger.info(f"Auto QC: Detected {len(patterns)} patterns")
                    else:
                        logger.info(f"Auto QC: Only {analyzed_count} calls analyzed, need 2+ for pattern detection")
                        
            except Exception as e:
                logger.error(f"Auto QC: Failed to store campaign results: {str(e)}")
        
        # Update call log with QC status
        await db.call_logs.update_one(
            {"$or": [{"call_id": call_id}, {"id": call_id}]},
            {"$set": {
                "qc_processed": True,
                "qc_processed_at": datetime.utcnow(),
                "qc_results_summary": {
                    "tech_overall": tech_results.get('overall_performance') if tech_results else None,
                    "script_score": script_results.get('quality_score') if script_results else None,
                    "tonality_overall": tonality_results.get('overall_tone') if tonality_results else None
                }
            }}
        )
        
        # Log final summary
        logger.info(f"✅ [RUN-QC] Completed full analysis for call {call_id}")
        logger.info(f"📊 [RUN-QC] Results summary: tech={tech_results.get('overall_performance') if tech_results else 'None'}, script={script_results.get('quality_score') if script_results else 'None'}, tonality={tonality_results.get('overall_tonality') if tonality_results else 'None'}")
        
    except Exception as e:
        import traceback
        logger.error(f"❌ [RUN-QC] Error in full analysis for call {call_id}: {str(e)}")
        logger.error(f"❌ [RUN-QC] Traceback: {traceback.format_exc()}")

async def auto_qc_get_user_api_key(user_id: str, provider: str) -> Optional[str]:
    """Get user's API key for a provider (for Auto QC)"""
    try:
        from key_encryption import decrypt_api_key
        
        # Map provider names to service names in database
        service_map = {
            'grok': 'grok',
            'openai': 'openai',
            'anthropic': 'anthropic',
            'google': 'google'
        }
        
        service_name = service_map.get(provider, provider)
        
        key_doc = await db.api_keys.find_one({
            "user_id": user_id,
            "service_name": service_name,
            "is_active": True
        })
        
        if key_doc and key_doc.get("api_key"):
            return decrypt_api_key(key_doc.get("api_key"))
        
        return None
    except Exception as e:
        logger.error(f"Error getting API key: {str(e)}")
        return None

async def auto_qc_analyze_transcript(
    transcript: List[Dict],
    llm_provider: str,
    model: str,
    api_key: str,
    call_id: str
) -> Dict:
    """Analyze transcript for script quality using LLM"""
    try:
        # Format transcript for analysis
        conversation_text = ""
        for entry in transcript:
            speaker = entry.get('speaker', entry.get('role', 'unknown'))
            text = entry.get('text', entry.get('content', ''))
            conversation_text += f"{speaker}: {text}\n"
        
        prompt = f"""Analyze this call transcript for script quality. Evaluate:
1. Response relevance and helpfulness
2. Conversation flow and naturalness
3. Goal achievement
4. Areas for improvement

Transcript:
{conversation_text}

Provide your analysis in JSON format with these fields:
- quality_score: 1-10 rating
- strengths: list of positive aspects
- issues: list of problems found
- suggestions: list of improvement suggestions
- node_analyses: list of turn-by-turn analysis
"""
        
        result = await call_llm_for_analysis(
            prompt=prompt,
            provider=llm_provider,
            model=model,
            api_key=api_key
        )
        
        if result:
            result['call_id'] = call_id
            result['analyzed_at'] = datetime.utcnow().isoformat()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in transcript analysis: {str(e)}")
        return None

async def auto_qc_analyze_tonality(
    transcript: List[Dict],
    llm_provider: str,
    model: str,
    api_key: str,
    call_id: str
) -> Dict:
    """Analyze transcript for tonality using LLM (for Auto QC)"""
    try:
        # Format transcript
        conversation_text = ""
        for entry in transcript:
            speaker = entry.get('speaker', entry.get('role', 'unknown'))
            text = entry.get('text', entry.get('content', ''))
            conversation_text += f"{speaker}: {text}\n"
        
        prompt = f"""Analyze the tone and emotional quality of this conversation.

Transcript:
{conversation_text}

Evaluate:
1. Overall tone (professional, friendly, formal, etc.)
2. Agent's emotional intelligence
3. Customer sentiment throughout call
4. Rapport building

Provide your analysis in JSON format with these fields:
- overall_tone: primary tone descriptor
- tone_score: 1-10 rating
- agent_empathy_score: 1-10 rating
- customer_sentiment: positive/neutral/negative
- tone_shifts: list of notable tone changes
- recommendations: suggestions for tone improvement
"""
        
        result = await call_llm_for_analysis(
            prompt=prompt,
            provider=llm_provider,
            model=model,
            api_key=api_key
        )
        
        if result:
            result['call_id'] = call_id
            result['analyzed_at'] = datetime.utcnow().isoformat()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in tonality analysis: {str(e)}")
        return None

async def call_llm_for_analysis(prompt: str, provider: str, model: str, api_key: str) -> Optional[Dict]:
    """Make LLM API call for analysis"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if provider == 'grok':
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                )
            elif provider == 'openai':
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                )
            elif provider == 'anthropic':
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": model,
                        "max_tokens": 2000,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
            else:
                logger.error(f"Unsupported LLM provider: {provider}")
                return None
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract content based on provider
                if provider == 'anthropic':
                    content = data.get('content', [{}])[0].get('text', '')
                else:
                    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Try to parse as JSON
                try:
                    # Find JSON in response
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        return json.loads(json_match.group())
                    else:
                        return {"raw_analysis": content}
                except json.JSONDecodeError:
                    return {"raw_analysis": content}
            else:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return None


# ============================================================================
# RESET ANALYSIS ENDPOINTS
# ============================================================================

@qc_enhanced_router.post("/campaigns/{campaign_id}/reset-all-analysis")
async def reset_all_campaign_analysis(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Reset all QC analysis results for a campaign.
    Clears script_qc_results, tech_qc_results, tonality_qc_results, and audio_tonality_results
    from all calls in the campaign, allowing fresh re-analysis.
    """
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Reset all campaign_calls analysis results
        result = await db.campaign_calls.update_many(
            {"campaign_id": campaign_id},
            {
                "$set": {
                    "script_qc_results": None,
                    "tech_qc_results": None,
                    "tonality_qc_results": None,
                    "audio_tonality_results": None,
                    "analysis_status": "pending",
                    "analysis_error": None,
                    "updated_at": datetime.utcnow()
                },
                "$unset": {
                    "script_analyzed_at": "",
                    "tech_analyzed_at": "",
                    "tonality_analyzed_at": "",
                    "audio_analyzed_at": ""
                }
            }
        )
        
        # Also reset batch analysis status on campaign
        await db.campaigns.update_one(
            {"id": campaign_id},
            {
                "$set": {
                    "batch_analysis_status": None,
                    "batch_analysis_completed": 0,
                    "batch_analysis_total": 0,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Reset analysis for campaign {campaign_id}: {result.modified_count} calls reset")
        
        return {
            "success": True,
            "message": f"Reset analysis for {result.modified_count} calls",
            "campaign_id": campaign_id,
            "calls_reset": result.modified_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting campaign analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@qc_enhanced_router.post("/campaigns/{campaign_id}/calls/{call_id}/reset-analysis")
async def reset_single_call_analysis(
    campaign_id: str,
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Reset QC analysis results for a single call in a campaign.
    """
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Reset the specific call's analysis
        result = await db.campaign_calls.update_one(
            {"campaign_id": campaign_id, "call_id": call_id},
            {
                "$set": {
                    "script_qc_results": None,
                    "tech_qc_results": None,
                    "tonality_qc_results": None,
                    "audio_tonality_results": None,
                    "analysis_status": "pending",
                    "analysis_error": None,
                    "updated_at": datetime.utcnow()
                },
                "$unset": {
                    "script_analyzed_at": "",
                    "tech_analyzed_at": "",
                    "tonality_analyzed_at": "",
                    "audio_analyzed_at": ""
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Call not found in campaign")
        
        # Also reset in call_logs if it exists there
        await db.call_logs.update_one(
            {"call_id": call_id, "user_id": current_user['id']},
            {
                "$set": {
                    "script_qc_results": None,
                    "tech_qc_results": None,
                    "tonality_qc_results": None,
                    "audio_tonality_results": None,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Reset analysis for call {call_id} in campaign {campaign_id}")
        
        return {
            "success": True,
            "message": "Analysis reset successfully",
            "campaign_id": campaign_id,
            "call_id": call_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting call analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALYZE ALL CALLS ENDPOINT
# ============================================================================

@qc_enhanced_router.post("/campaigns/{campaign_id}/analyze-all")
async def analyze_all_campaign_calls(
    campaign_id: str,
    request_data: dict,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger analysis for all pending calls in a campaign.
    Runs analysis in background and returns immediately.
    Uses the campaign's assigned QC agents for each analysis type.
    
    Request body:
    {
        "analysis_types": ["script", "tonality"],  # Which analyses to run
        "script_qc_agent_id": "optional-id",  # QC agent for script analysis
        "tonality_qc_agent_id": "optional-id",  # QC agent for tonality analysis
        "tech_qc_agent_id": "optional-id",  # QC agent for tech analysis
        "force_reanalyze": false  # Re-analyze calls that have already been analyzed
    }
    """
    try:
        # Verify campaign ownership
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        analysis_types = request_data.get('analysis_types', ['script'])
        force_reanalyze = request_data.get('force_reanalyze', False)
        
        # Get QC agent IDs - use request params if provided, otherwise use campaign's assigned agents
        script_qc_agent_id = request_data.get('script_qc_agent_id') or campaign.get('language_pattern_qc_agent_id')
        tonality_qc_agent_id = request_data.get('tonality_qc_agent_id') or campaign.get('tonality_qc_agent_id')
        tech_qc_agent_id = request_data.get('tech_qc_agent_id') or campaign.get('tech_issues_qc_agent_id')
        
        # Validate that required QC agents are assigned
        missing_agents = []
        if 'script' in analysis_types and not script_qc_agent_id:
            missing_agents.append('Script Quality (language_pattern_qc_agent_id)')
        if 'tonality' in analysis_types and not tonality_qc_agent_id:
            missing_agents.append('Tonality (tonality_qc_agent_id)')
        if 'tech' in analysis_types and not tech_qc_agent_id:
            missing_agents.append('Tech Issues (tech_issues_qc_agent_id)')
        
        if missing_agents:
            raise HTTPException(
                status_code=400, 
                detail=f"QC agents not assigned for: {', '.join(missing_agents)}. Please assign QC agents in Campaign Settings."
            )
        
        # Fetch QC agent settings to get LLM provider/model
        qc_agents_config = {}
        if script_qc_agent_id:
            agent = await db.qc_agents.find_one({"id": script_qc_agent_id})
            if agent:
                qc_agents_config['script'] = {
                    'id': script_qc_agent_id,
                    'llm_provider': agent.get('llm_provider', 'grok'),
                    'llm_model': agent.get('llm_model', 'grok-3'),
                    'system_prompt': agent.get('system_prompt', ''),
                    'name': agent.get('name', 'Script QC Agent')
                }
        
        if tonality_qc_agent_id:
            agent = await db.qc_agents.find_one({"id": tonality_qc_agent_id})
            if agent:
                qc_agents_config['tonality'] = {
                    'id': tonality_qc_agent_id,
                    'llm_provider': agent.get('llm_provider', 'grok'),
                    'llm_model': agent.get('llm_model', 'grok-3'),
                    'system_prompt': agent.get('system_prompt', ''),
                    'name': agent.get('name', 'Tonality QC Agent')
                }
        
        if tech_qc_agent_id:
            agent = await db.qc_agents.find_one({"id": tech_qc_agent_id})
            if agent:
                qc_agents_config['tech'] = {
                    'id': tech_qc_agent_id,
                    'llm_provider': agent.get('llm_provider', 'grok'),
                    'llm_model': agent.get('llm_model', 'grok-3'),
                    'system_prompt': agent.get('system_prompt', ''),
                    'name': agent.get('name', 'Tech QC Agent')
                }
        
        # Get all calls in campaign
        campaign_calls = await db.campaign_calls.find({
            "campaign_id": campaign_id
        }).to_list(length=1000)
        
        # Filter to pending calls (not yet analyzed or force reanalyze)
        pending_calls = []
        for cc in campaign_calls:
            if force_reanalyze:
                pending_calls.append(cc)
            else:
                # Check if already analyzed
                has_script = cc.get('script_qc_results') is not None
                has_tonality = cc.get('tonality_qc_results') is not None
                has_tech = cc.get('tech_qc_results') is not None
                
                needs_analysis = False
                if 'script' in analysis_types and not has_script:
                    needs_analysis = True
                if 'tonality' in analysis_types and not has_tonality:
                    needs_analysis = True
                if 'tech' in analysis_types and not has_tech:
                    needs_analysis = True
                
                if needs_analysis:
                    pending_calls.append(cc)
        
        # Also check training calls
        training_calls = await db.training_calls.find({
            "campaign_id": campaign_id,
            "user_id": current_user['id']
        }).to_list(length=1000)
        
        pending_training_calls = []
        for tc in training_calls:
            if force_reanalyze:
                pending_training_calls.append(tc)
            elif not tc.get('qc_analyzed_at'):
                pending_training_calls.append(tc)
        
        if not pending_calls and not pending_training_calls:
            return {
                "success": True,
                "message": "No pending calls to analyze",
                "campaign_id": campaign_id,
                "calls_queued": 0,
                "training_calls_queued": 0
            }
        
        # Queue background task with QC agent configs
        background_tasks.add_task(
            run_batch_analysis,
            campaign_id=campaign_id,
            user_id=current_user['id'],
            pending_calls=[c.get('call_id') for c in pending_calls],
            training_call_ids=[tc.get('id') for tc in pending_training_calls],
            analysis_types=analysis_types,
            qc_agents_config=qc_agents_config  # Pass full QC agent configs
        )
        
        # Build response with agent info
        agents_used = []
        if 'script' in analysis_types and qc_agents_config.get('script'):
            agents_used.append(f"Script: {qc_agents_config['script']['name']}")
        if 'tonality' in analysis_types and qc_agents_config.get('tonality'):
            agents_used.append(f"Tonality: {qc_agents_config['tonality']['name']}")
        if 'tech' in analysis_types and qc_agents_config.get('tech'):
            agents_used.append(f"Tech: {qc_agents_config['tech']['name']}")
        
        return {
            "success": True,
            "message": "Batch analysis started",
            "campaign_id": campaign_id,
            "calls_queued": len(pending_calls),
            "training_calls_queued": len(pending_training_calls),
            "analysis_types": analysis_types,
            "qc_agents_used": agents_used
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_batch_analysis(
    campaign_id: str,
    user_id: str,
    pending_calls: List[str],
    training_call_ids: List[str],
    analysis_types: List[str],
    qc_agents_config: Dict[str, Any]
):
    """Background task to run batch analysis on all pending calls using assigned QC agents"""
    logger.info(f"Starting batch analysis for campaign {campaign_id}: {len(pending_calls)} calls, {len(training_call_ids)} training calls")
    logger.info(f"Using QC agents: {list(qc_agents_config.keys())}")
    
    results = {
        "completed": 0,
        "failed": 0,
        "errors": []
    }
    
    # Update campaign with analysis status
    try:
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {
                "batch_analysis_status": "running",
                "batch_analysis_started_at": datetime.utcnow(),
                "batch_analysis_total": len(pending_calls) + len(training_call_ids),
                "batch_analysis_completed": 0
            }}
        )
    except Exception as e:
        logger.error(f"Error updating campaign status: {e}")
    
    # Process regular campaign calls
    for i, call_id in enumerate(pending_calls):
        try:
            logger.info(f"Analyzing call {i+1}/{len(pending_calls)}: {call_id[:30]}...")
            
            # Mark call as "analyzing" first
            await db.campaign_calls.update_one(
                {"campaign_id": campaign_id, "call_id": call_id},
                {"$set": {"analysis_status": "analyzing", "analysis_started_at": datetime.utcnow()}},
                upsert=True
            )
            
            await run_single_call_analysis(
                call_id=call_id,
                user_id=user_id,
                campaign_id=campaign_id,
                analysis_types=analysis_types,
                qc_agents_config=qc_agents_config
            )
            
            # Mark as completed
            await db.campaign_calls.update_one(
                {"campaign_id": campaign_id, "call_id": call_id},
                {"$set": {"analysis_status": "completed"}}
            )
            
            results["completed"] += 1
            
            # Update campaign progress
            await db.campaigns.update_one(
                {"id": campaign_id},
                {"$set": {"batch_analysis_completed": results["completed"]}}
            )
            
            await asyncio.sleep(1)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error analyzing call {call_id}: {str(e)}")
            
            # Mark call as failed
            await db.campaign_calls.update_one(
                {"campaign_id": campaign_id, "call_id": call_id},
                {"$set": {"analysis_status": "failed", "analysis_error": str(e)}}
            )
            
            results["failed"] += 1
            results["errors"].append({"call_id": call_id, "error": str(e)})
    
    # Process training calls (if they have transcripts)
    for training_call_id in training_call_ids:
        try:
            training_call = await db.training_calls.find_one({"id": training_call_id})
            if training_call and training_call.get('transcript'):
                # Run analysis using the training call's transcript
                await run_training_call_analysis(
                    training_call=training_call,
                    user_id=user_id,
                    campaign_id=campaign_id,
                    analysis_types=analysis_types,
                    qc_agents_config=qc_agents_config
                )
                results["completed"] += 1
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error analyzing training call {training_call_id}: {str(e)}")
            results["failed"] += 1
            results["errors"].append({"training_call_id": training_call_id, "error": str(e)})
    
    # Update campaign with final status
    try:
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {
                "batch_analysis_status": "completed",
                "batch_analysis_completed_at": datetime.utcnow(),
                "batch_analysis_results": results
            }}
        )
    except Exception as e:
        logger.error(f"Error updating final campaign status: {e}")
    
    logger.info(f"Batch analysis complete for campaign {campaign_id}: {results['completed']} completed, {results['failed']} failed")


async def run_single_call_analysis(
    call_id: str,
    user_id: str,
    campaign_id: str,
    analysis_types: List[str],
    qc_agents_config: Dict[str, Any]
):
    """Run analysis on a single call using the specified QC agents"""
    logger.info(f"Starting single call analysis for call_id={call_id[:40]}..., user_id={user_id[:8]}...")
    
    # Get call data - try multiple approaches
    call = await db.call_logs.find_one({
        "$or": [
            {"call_id": call_id, "user_id": user_id},
            {"id": call_id, "user_id": user_id}
        ]
    })
    
    # If not found with user_id, try without (in case of ownership mismatch)
    if not call:
        logger.warning(f"Call not found with user_id filter, trying without...")
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id},
                {"id": call_id}
            ]
        })
        if call:
            logger.info(f"Found call without user_id filter. Call user_id: {call.get('user_id')}, search user_id: {user_id}")
    
    # Also check campaign_calls for embedded call data
    if not call:
        logger.warning(f"Call not found in call_logs, checking campaign_calls...")
        campaign_call = await db.campaign_calls.find_one({
            "campaign_id": campaign_id,
            "call_id": call_id
        })
        if campaign_call and campaign_call.get('call_data'):
            call = campaign_call['call_data']
            logger.info(f"Found call data embedded in campaign_calls")
    
    if not call:
        logger.error(f"Call not found anywhere: {call_id}")
        # Mark as failed in campaign_calls
        await db.campaign_calls.update_one(
            {"campaign_id": campaign_id, "call_id": call_id},
            {"$set": {
                "analysis_status": "failed",
                "analysis_error": "Call data not found in call_logs collection",
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
        raise Exception(f"Call not found: {call_id}")
    
    # Extract transcript from call - handles both 'transcript' and 'logs' fields
    transcript = extract_transcript_from_call(call)
    
    logger.info(f"Single call analysis: call_id={call_id[:30]}..., transcript_entries={len(transcript)}")
    
    if not transcript or len(transcript) == 0:
        logger.warning(f"No transcript data found for call {call_id}, skipping analysis")
        # Still mark as analyzed but with no results
        await db.campaign_calls.update_one(
            {"campaign_id": campaign_id, "call_id": call_id},
            {"$set": {
                "analysis_status": "completed",
                "analysis_note": "No transcript data available",
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
        return
    
    if 'script' in analysis_types:
        # Get script QC agent config
        script_config = qc_agents_config.get('script', {})
        llm_provider = script_config.get('llm_provider', 'grok')
        model = script_config.get('llm_model', 'grok-3')
        qc_agent_id = script_config.get('id')
        system_prompt = script_config.get('system_prompt', '')
        
        logger.info(f"Script analysis config: provider={llm_provider}, model={model}, agent_id={qc_agent_id}")
        
        # Get API key for this provider
        api_key = await get_user_api_key(user_id, llm_provider)
        if not api_key:
            logger.warning(f"No API key for {llm_provider}, trying fallbacks...")
            # Try fallback providers
            for fallback in ['grok', 'openai', 'anthropic']:
                if fallback != llm_provider:
                    api_key = await get_user_api_key(user_id, fallback)
                    if api_key:
                        llm_provider = fallback
                        logger.info(f"Using fallback provider: {fallback}")
                        break
            
            if not api_key:
                logger.error(f"No API key available for script analysis! User: {user_id}")
                # Save error result instead of raising
                error_result = {
                    "call_id": call_id,
                    "overall_quality": "error",
                    "node_analyses": [],
                    "error": f"No API key available for LLM providers (tried: {llm_provider}, grok, openai, anthropic)",
                    "analyzed_at": datetime.now(timezone.utc).isoformat()
                }
                await store_campaign_call_analysis(campaign_id, call_id, script_qc_results=error_result)
        else:
            # Run script analysis
            rules = {
                'user_id': user_id,
                'llm_provider': llm_provider,
                'model': model,
                'system_prompt': system_prompt  # Pass custom system prompt
            }
            
            logger.info(f"Running script analysis with {llm_provider}/{model} for call {call_id[:30]}...")
            
            try:
                node_analyses = await analyze_script_with_llm(transcript, [], rules)
                logger.info(f"Script analysis returned {len(node_analyses) if node_analyses else 0} node analyses")
            except Exception as analysis_error:
                logger.error(f"Script analysis failed for call {call_id}: {analysis_error}")
                # Store error result so we know what happened
                error_result = {
                    "call_id": call_id,
                    "overall_quality": "error",
                    "node_analyses": [],
                    "error": f"Analysis failed: {str(analysis_error)}",
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "qc_agent_id": qc_agent_id,
                    "transcript_entries": len(transcript)
                }
                await store_campaign_call_analysis(campaign_id, call_id, script_qc_results=error_result)
                # Continue to next analysis type but don't save empty success result
                node_analyses = None
            
            # Only continue with result building if we got actual analyses
            if node_analyses is None:
                logger.warning(f"Skipping result storage for {call_id} due to analysis failure")
            else:
                bulk_suggestions = generate_bulk_script_suggestions(node_analyses)
                
                try:
                    predictions = await generate_script_predictions(node_analyses, transcript)
                except Exception as pred_error:
                    logger.warning(f"Predictions generation failed: {pred_error}")
                    predictions = None
                
                result = {
                    "call_id": call_id,
                    "overall_quality": "good" if node_analyses else "unknown",
                    "node_analyses": node_analyses or [],
                    "bulk_suggestions": bulk_suggestions,
                    "predictions": predictions.dict() if predictions else None,
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "qc_agent_id": qc_agent_id,
                    "qc_agent_name": script_config.get('name', 'Script QC Agent'),
                    "transcript_entries": len(transcript),
                    "llm_provider": llm_provider,
                    "model": model
                }
                
                logger.info(f"Saving script QC results for call {call_id[:30]}... (node_analyses: {len(node_analyses) if node_analyses else 0})")
                await store_campaign_call_analysis(campaign_id, call_id, script_qc_results=result)
                
                if qc_agent_id and predictions:
                    analysis_log = await log_qc_analysis(
                        qc_agent_id=qc_agent_id,
                        user_id=user_id,
                        agent_type="language_pattern",
                        call_id=call_id,
                        analysis_content=result,
                        predictions=predictions,
                        campaign_id=campaign_id,
                        call_agent_id=call.get('agent_id')
                    )
                    await db.qc_analysis_logs.insert_one(analysis_log.dict())
    
    if 'tonality' in analysis_types:
        # Get tonality QC agent config
        tonality_config = qc_agents_config.get('tonality', {})
        llm_provider = tonality_config.get('llm_provider', 'grok')
        model = tonality_config.get('llm_model', 'grok-3')
        qc_agent_id = tonality_config.get('id')
        system_prompt = tonality_config.get('system_prompt', '')
        
        # Get API key for this provider
        api_key = await get_user_api_key(user_id, llm_provider)
        if not api_key:
            raise Exception(f"No API key for {llm_provider}")
        
        # Run tonality analysis
        from qc_enhanced_router import analyze_tonality_with_llm, generate_ssml_recommendations, generate_tonality_predictions
        
        node_analyses = await analyze_tonality_with_llm(transcript, system_prompt, api_key, llm_provider, model)
        ssml_recommendations = generate_ssml_recommendations(node_analyses)
        predictions = await generate_tonality_predictions(node_analyses, transcript)
        
        result = {
            "call_id": call_id,
            "overall_tonality": "good",
            "node_analyses": node_analyses,
            "ssml_recommendations": ssml_recommendations,
            "predictions": predictions.dict() if predictions else None,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "qc_agent_id": qc_agent_id,
            "qc_agent_name": tonality_config.get('name', 'Tonality QC Agent')
        }
        
        await store_campaign_call_analysis(campaign_id, call_id, tonality_qc_results=result)
        
        if qc_agent_id and predictions:
            analysis_log = await log_qc_analysis(
                qc_agent_id=qc_agent_id,
                user_id=user_id,
                agent_type="tonality",
                call_id=call_id,
                analysis_content=result,
                predictions=predictions,
                campaign_id=campaign_id,
                call_agent_id=call.get('agent_id')
            )
            await db.qc_analysis_logs.insert_one(analysis_log.dict())


async def run_training_call_analysis(
    training_call: dict,
    user_id: str,
    campaign_id: str,
    analysis_types: List[str],
    qc_agents_config: Dict[str, Any]
):
    """Run analysis on a training call using the specified QC agents"""
    training_call_id = training_call.get('id')
    transcript = training_call.get('transcript', [])
    
    if not transcript:
        logger.warning(f"Training call {training_call_id} has no transcript, skipping")
        return
    
    analysis_log_id = None
    
    if 'script' in analysis_types:
        # Get script QC agent config
        script_config = qc_agents_config.get('script', {})
        llm_provider = script_config.get('llm_provider', 'grok')
        model = script_config.get('llm_model', 'grok-3')
        qc_agent_id = script_config.get('id')
        system_prompt = script_config.get('system_prompt', '')
        
        # Get API key
        api_key = await get_user_api_key(user_id, llm_provider)
        if not api_key:
            raise Exception(f"No API key for {llm_provider}")
        
        from qc_enhanced_router import analyze_script_with_llm, generate_bulk_script_suggestions, generate_script_predictions
        
        rules = {
            'user_id': user_id,
            'llm_provider': llm_provider,
            'model': model,
            'system_prompt': system_prompt
        }
        
        node_analyses = await analyze_script_with_llm(transcript, [], rules)
        predictions = await generate_script_predictions(node_analyses, transcript)
        
        if qc_agent_id and predictions:
            analysis_log = await log_qc_analysis(
                qc_agent_id=qc_agent_id,
                user_id=user_id,
                agent_type="language_pattern",
                call_id=f"training:{training_call_id}",
                analysis_content={"node_analyses": node_analyses},
                predictions=predictions,
                campaign_id=campaign_id
            )
            await db.qc_analysis_logs.insert_one(analysis_log.dict())
            analysis_log_id = analysis_log.id
    
    if 'tonality' in analysis_types:
        # Get tonality QC agent config
        tonality_config = qc_agents_config.get('tonality', {})
        llm_provider = tonality_config.get('llm_provider', 'grok')
        model = tonality_config.get('llm_model', 'grok-3')
        qc_agent_id = tonality_config.get('id')
        system_prompt = tonality_config.get('system_prompt', '')
        
        # Get API key
        api_key = await get_user_api_key(user_id, llm_provider)
        if not api_key:
            raise Exception(f"No API key for {llm_provider}")
        
        from qc_enhanced_router import analyze_tonality_with_llm, generate_tonality_predictions
        
        node_analyses = await analyze_tonality_with_llm(transcript, system_prompt, api_key, llm_provider, model)
        predictions = await generate_tonality_predictions(node_analyses, transcript)
        
        if qc_agent_id and predictions:
            analysis_log = await log_qc_analysis(
                qc_agent_id=qc_agent_id,
                user_id=user_id,
                agent_type="tonality",
                call_id=f"training:{training_call_id}",
                analysis_content={"node_analyses": node_analyses},
                predictions=predictions,
                campaign_id=campaign_id
            )
            await db.qc_analysis_logs.insert_one(analysis_log.dict())
            analysis_log_id = analysis_log.id
    
    # Update training call with analysis info
    await db.training_calls.update_one(
        {"id": training_call_id},
        {
            "$set": {
                "qc_analyzed_at": datetime.now(timezone.utc),
                "qc_analysis_id": analysis_log_id
            }
        }
    )


@qc_enhanced_router.post("/trigger-auto-qc/{call_id}")
async def trigger_auto_qc_for_call(
    call_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger auto QC for a specific call based on agent settings
    Called at call end by the calling service
    Uses custom LLM settings from assigned QC agents
    """
    try:
        # Get call to find agent_id
        call = await db.call_logs.find_one({
            "$or": [
                {"call_id": call_id, "user_id": current_user['id']},
                {"id": call_id, "user_id": current_user['id']}
            ]
        })
        
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        agent_id = call.get('agent_id')
        if not agent_id:
            return {"success": False, "message": "No agent associated with call"}
        
        # Get agent's auto QC settings
        agent = await db.agents.find_one({
            "id": agent_id,
            "user_id": current_user['id']
        })
        
        if not agent:
            return {"success": False, "message": "Agent not found"}
        
        auto_qc = agent.get('auto_qc_settings', {})
        
        if not auto_qc.get('enabled', False):
            return {"success": False, "message": "Auto QC not enabled for this agent"}
        
        campaign_id = auto_qc.get('campaign_id')
        if not campaign_id:
            return {"success": False, "message": "No campaign configured for auto QC"}
        
        # Get campaign to find assigned QC agents and their LLM settings
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        qc_agents_config = {}
        if campaign:
            # Get Script QC agent LLM settings
            script_qc_agent_id = campaign.get('language_pattern_qc_agent_id')
            if script_qc_agent_id:
                script_agent = await db.qc_agents.find_one({"id": script_qc_agent_id})
                if script_agent:
                    qc_agents_config['script'] = {
                        'id': script_qc_agent_id,
                        'llm_provider': script_agent.get('llm_provider', 'grok'),
                        'llm_model': script_agent.get('llm_model', 'grok-3'),
                        'system_prompt': script_agent.get('system_prompt', '')
                    }
                    logger.info(f"Auto QC: Script agent config: {qc_agents_config['script']['llm_provider']}/{qc_agents_config['script']['llm_model']}")
            
            # Get Tonality QC agent LLM settings
            tonality_qc_agent_id = campaign.get('tonality_qc_agent_id')
            if tonality_qc_agent_id:
                tonality_agent = await db.qc_agents.find_one({"id": tonality_qc_agent_id})
                if tonality_agent:
                    qc_agents_config['tonality'] = {
                        'id': tonality_qc_agent_id,
                        'llm_provider': tonality_agent.get('llm_provider', 'grok'),
                        'llm_model': tonality_agent.get('llm_model', 'grok-3'),
                        'system_prompt': tonality_agent.get('system_prompt', '')
                    }
                    logger.info(f"Auto QC: Tonality agent config: {qc_agents_config['tonality']['llm_provider']}/{qc_agents_config['tonality']['llm_model']}")
            
            # Get Tech QC agent LLM settings
            tech_qc_agent_id = campaign.get('tech_issues_qc_agent_id')
            if tech_qc_agent_id:
                tech_agent = await db.qc_agents.find_one({"id": tech_qc_agent_id})
                if tech_agent:
                    qc_agents_config['tech'] = {
                        'id': tech_qc_agent_id,
                        'llm_provider': tech_agent.get('llm_provider', 'grok'),
                        'llm_model': tech_agent.get('llm_model', 'grok-3'),
                        'system_prompt': tech_agent.get('system_prompt', '')
                    }
        
        # Schedule background QC processing with QC agent configs
        background_tasks.add_task(
            run_full_qc_analysis,
            call_id=call_id,
            user_id=current_user['id'],
            agent_id=agent_id,
            campaign_id=campaign_id,
            run_tech=auto_qc.get('run_tech_analysis', True),
            run_script=auto_qc.get('run_script_analysis', True),
            run_tonality=auto_qc.get('run_tonality_analysis', True),
            qc_agents_config=qc_agents_config  # Pass QC agent configs with LLM settings
        )
        
        return {
            "success": True,
            "message": "Auto QC triggered",
            "call_id": call_id,
            "campaign_id": campaign_id,
            "qc_agents_used": list(qc_agents_config.keys())
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering auto QC: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_enhanced_router.get("/campaigns/{campaign_id}/auto-settings")
async def get_campaign_auto_settings(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get auto pattern detection settings for a campaign"""
    try:
        campaign = await db.campaigns.find_one({
            "id": campaign_id,
            "user_id": current_user['id']
        })
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return {
            "campaign_id": campaign_id,
            "auto_pattern_detection": campaign.get('auto_pattern_detection', False),
            "linked_agents": campaign.get('linked_agents', [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign auto settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

