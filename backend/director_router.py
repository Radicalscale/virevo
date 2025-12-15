"""
Director Router - API Endpoints for the Director Studio Feature
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from .director_service import DirectorService
from .auth_utils import get_current_user_id  # Assuming this exists based on other routers

router = APIRouter(prefix="/api/director", tags=["Director Studio"])


class CreateSandboxRequest(BaseModel):
    agent_id: str


class EvolveNodeRequest(BaseModel):
    sandbox_id: str
    node_id: str
    generations: Optional[int] = 3


class UpdateNodeRequest(BaseModel):
    sandbox_id: str
    node_id: str
    updates: Dict[str, Any]


class PromoteRequest(BaseModel):
    sandbox_id: str


@router.post("/sandbox")
async def create_sandbox(request: CreateSandboxRequest, user_id: str = Depends(get_current_user_id)):
    """
    Create a sandbox (clone) of an agent for safe experimentation.
    """
    try:
        service = DirectorService(user_id=user_id)
        sandbox_id = await service.create_sandbox(request.agent_id)
        return {
            "success": True,
            "sandbox_id": sandbox_id,
            "message": f"Sandbox created from agent {request.agent_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{sandbox_id}")
async def get_sandbox(sandbox_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Get the current state of a sandbox.
    """
    try:
        service = DirectorService(user_id=user_id)
        config = service.get_sandbox_config(sandbox_id)
        if not config:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        return {
            "success": True,
            "sandbox_id": sandbox_id,
            "config": config
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{sandbox_id}/nodes")
async def get_sandbox_nodes(sandbox_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Get the list of nodes in a sandbox for the UI.
    """
    try:
        service = DirectorService(user_id=user_id)
        config = service.get_sandbox_config(sandbox_id)
        if not config:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        call_flow = config.get('call_flow', [])
        nodes = [
            {
                "id": node.get("id"),
                "label": node.get("label", node.get("id", "Unknown")),
                "mode": node.get("data", {}).get("mode", "unknown"),
                "content_preview": node.get("data", {}).get("content", "")[:100]
            }
            for node in call_flow
        ]
        return {"success": True, "nodes": nodes}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolve")
async def evolve_node(request: EvolveNodeRequest, user_id: str = Depends(get_current_user_id)):
    """
    Run the evolutionary optimization loop on a specific node.
    Uses Grok for chaos scenarios and GPT-4o for judgment.
    """
    try:
        service = DirectorService(user_id=user_id)
        await service._init_db()
        
        # Reload sandbox if needed (stateless between requests)
        if request.sandbox_id not in service.sandboxes:
            # Try to reconstruct from a stored state or return error
            raise HTTPException(status_code=404, detail="Sandbox not found. Please create a new one.")
        
        best_variant, best_score = await service.evolve_node(
            sandbox_id=request.sandbox_id,
            node_id=request.node_id,
            generations=request.generations
        )
        
        return {
            "success": True,
            "message": f"Evolution complete for {request.node_id}",
            "best_score": best_score,
            "best_variant": {
                "type": best_variant.get("_variant_type", "Optimized"),
                "content_preview": best_variant.get("content", "")[:100],
                "voice_settings": best_variant.get("voice_settings", {})
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sandbox/node")
async def update_sandbox_node(request: UpdateNodeRequest, user_id: str = Depends(get_current_user_id)):
    """
    Manually update a node in the sandbox.
    """
    try:
        service = DirectorService(user_id=user_id)
        await service.update_sandbox_node(
            sandbox_id=request.sandbox_id,
            node_id=request.node_id,
            updates=request.updates
        )
        return {"success": True, "message": f"Node {request.node_id} updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/promote")
async def promote_sandbox(request: PromoteRequest, user_id: str = Depends(get_current_user_id)):
    """
    Promote a sandbox configuration to the live agent.
    This overwrites the production agent with the optimized settings.
    """
    try:
        service = DirectorService(user_id=user_id)
        success = await service.promote_sandbox(request.sandbox_id)
        
        if success:
            return {"success": True, "message": "Sandbox promoted to live agent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to promote sandbox")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
