"""
Director Router - API Endpoints for the Director Studio Feature
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from director_service import DirectorService
from auth_middleware import get_current_user  # Same as used in server.py

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
async def create_sandbox(request: CreateSandboxRequest, current_user: dict = Depends(get_current_user)):
    """
    Create a sandbox (clone) of an agent for safe experimentation.
    """
    try:
        service = DirectorService(user_id=current_user['id'])
        sandbox_id = await service.create_sandbox(request.agent_id)
        return {
            "success": True,
            "sandbox_id": sandbox_id,
            "message": f"Sandbox created from agent {request.agent_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{sandbox_id}")
async def get_sandbox(sandbox_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get the current state of a sandbox.
    """
    try:
        service = DirectorService(user_id=current_user['id'])
        config = await service.get_sandbox_config(sandbox_id)
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
async def get_sandbox_nodes(sandbox_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get the list of nodes in a sandbox for the UI.
    """
    try:
        service = DirectorService(user_id=current_user['id'])
        config = await service.get_sandbox_config(sandbox_id)
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
async def evolve_node(request: EvolveNodeRequest, current_user: dict = Depends(get_current_user)):
    """
    Run the evolutionary optimization loop on a specific node.
    Returns FULL data including all variants, audio, and scores.
    """
    try:
        service = DirectorService(user_id=current_user['id'])
        
        result = await service.evolve_node(
            sandbox_id=request.sandbox_id,
            node_id=request.node_id,
            generations=request.generations
        )
        
        # Result now contains full evolution log with audio
        return {
            "success": True,
            "node_id": result.get("node_id"),
            "node_label": result.get("node_label"),
            "scenario": result.get("scenario"),
            "generations": result.get("generations", []),
            "best_variant": result.get("best_variant"),
            "best_score": result.get("best_score", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sandbox/node")
async def update_sandbox_node(request: UpdateNodeRequest, current_user: dict = Depends(get_current_user)):
    """
    Manually update a node in the sandbox.
    """
    try:
        service = DirectorService(user_id=current_user['id'])
        await service.update_sandbox_node(
            sandbox_id=request.sandbox_id,
            node_id=request.node_id,
            updates=request.updates
        )
        return {"success": True, "message": f"Node {request.node_id} updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/promote")
async def promote_sandbox(request: PromoteRequest, current_user: dict = Depends(get_current_user)):
    """
    Promote a sandbox configuration to the live agent.
    This overwrites the production agent with the optimized settings.
    """
    try:
        service = DirectorService(user_id=current_user['id'])
        success = await service.promote_sandbox(request.sandbox_id)
        
        if success:
            return {"success": True, "message": "Sandbox promoted to live agent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to promote sandbox")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
