"""
Element Routes
===============

API routes for element management.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel

router = APIRouter(prefix="/api/element", tags=["elements"])

# Injected by server
state_manager = None


class ElementRequest(BaseModel):
    """Request to add/update element."""
    component_type: str
    content: Dict[str, Any]
    position: Optional[Dict[str, int]] = None
    size: Optional[Dict[str, int]] = None


class ElementResponse(BaseModel):
    """Response for element operations."""
    element_id: str
    component_type: str
    message: str


@router.post("/{session_id}")
async def add_element(session_id: str, request: ElementRequest) -> ElementResponse:
    """Add element to canvas."""
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    session = state_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    import uuid
    element = {
        "id": str(uuid.uuid4()),
        "component_type": request.component_type,
        "content": request.content,
        "position": request.position or {"row": 4, "col": 2},
        "size": request.size or {"width": 28, "height": 10}
    }

    state_manager.add_element(session_id, element)

    return ElementResponse(
        element_id=element["id"],
        component_type=request.component_type,
        message="Element added"
    )


@router.delete("/{session_id}/{element_id}")
async def remove_element(session_id: str, element_id: str):
    """Remove element from canvas."""
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    if not state_manager.remove_element(session_id, element_id):
        raise HTTPException(status_code=404, detail="Session or element not found")

    return {"message": "Element removed", "element_id": element_id}


@router.put("/{session_id}/{element_id}")
async def update_element(session_id: str, element_id: str, request: ElementRequest):
    """Update element on canvas."""
    if not state_manager:
        raise HTTPException(status_code=500, detail="State manager not initialized")

    session = state_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find and update element
    for element in session.get("elements", []):
        if element.get("id") == element_id:
            element["component_type"] = request.component_type
            element["content"] = request.content
            if request.position:
                element["position"] = request.position
            if request.size:
                element["size"] = request.size
            state_manager.update_session(session_id, session["elements"])
            return {"message": "Element updated", "element_id": element_id}

    raise HTTPException(status_code=404, detail="Element not found")
