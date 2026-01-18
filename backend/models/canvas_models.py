"""
Canvas Models for Text Labs
============================

Models for canvas state, grid positions, and placed elements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class GridPosition(BaseModel):
    """Grid position on the canvas."""
    row: int = Field(ge=0, le=18)
    col: int = Field(ge=0, le=32)
    width: int = Field(ge=1, le=32)
    height: int = Field(ge=1, le=18)


class PlacedElement(BaseModel):
    """An element placed on the canvas."""
    id: str
    component_type: str
    grid_position: GridPosition
    html: str
    original_prompt: Optional[str] = None
    variants_used: Optional[List[str]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class CanvasState(BaseModel):
    """State of the canvas."""
    session_id: str
    slide_title: Optional[str] = "Untitled Slide"
    slide_purpose: Optional[str] = "presentation"
    audience: Optional[str] = None
    tone: Optional[str] = "professional"
    elements: List[PlacedElement] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def add_element(self, element: PlacedElement) -> None:
        """Add element to canvas."""
        self.elements.append(element)
        self.updated_at = datetime.now()

    def remove_element(self, element_id: str) -> bool:
        """Remove element from canvas."""
        initial_len = len(self.elements)
        self.elements = [e for e in self.elements if e.id != element_id]
        if len(self.elements) < initial_len:
            self.updated_at = datetime.now()
            return True
        return False

    def clear(self) -> None:
        """Clear all elements."""
        self.elements = []
        self.updated_at = datetime.now()
