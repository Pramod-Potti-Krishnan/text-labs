"""
Canvas Routes
==============

API routes for canvas state management.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

router = APIRouter(prefix="/api/canvas", tags=["canvas"])

# Injected by server
state_manager = None


class CanvasStateResponse(BaseModel):
    """Response for canvas state."""
    session_id: str
    elements: List[Dict[str, Any]]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.post("/session")
async def create_session():
    """Create a new canvas session."""
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    session_id = state_manager.create_session()
    return {"session_id": session_id, "message": "Session created"}


@router.get("/state/{session_id}")
async def get_state(session_id: str) -> CanvasStateResponse:
    """Get canvas state for session."""
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    session = state_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return CanvasStateResponse(
        session_id=session_id,
        elements=session.get("elements", []),
        created_at=session.get("created_at"),
        updated_at=session.get("updated_at")
    )


@router.delete("/state/{session_id}")
async def clear_canvas(session_id: str):
    """Clear all elements from canvas."""
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    if not state_manager.clear_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Canvas cleared", "session_id": session_id}
