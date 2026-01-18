"""
Canvas State Manager
====================

Manages canvas state with JSON persistence.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from ..models.canvas_models import CanvasState, PlacedElement, GridPosition

logger = logging.getLogger(__name__)


class StateManager:
    """Manages canvas state for sessions."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or Path("sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info(f"[STATE-MANAGER] Initialized with sessions_dir={self.sessions_dir}")

    def _create_new_session(self, session_id: str) -> str:
        """Internal: Create a new session with given ID."""
        self._cache[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "elements": [],
            "history": [],
            "chat_messages": []
        }
        self._save_session(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state."""
        if session_id in self._cache:
            return self._cache[session_id]

        session_path = self.sessions_dir / f"{session_id}.json"
        if session_path.exists():
            with open(session_path) as f:
                self._cache[session_id] = json.load(f)
                return self._cache[session_id]
        return None

    def update_session(self, session_id: str, elements: List[Dict[str, Any]]) -> bool:
        """Update session elements."""
        session = self.get_session(session_id)
        if not session:
            return False

        session["elements"] = elements
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id)
        return True

    def add_element(self, session_id: str, element: Dict[str, Any]) -> bool:
        """Add element to session."""
        session = self.get_session(session_id)
        if not session:
            return False

        if "id" not in element:
            element["id"] = str(uuid.uuid4())

        session["elements"].append(element)
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id)
        return True

    def remove_element(self, session_id: str, element_id: str) -> bool:
        """Remove element from session."""
        session = self.get_session(session_id)
        if not session:
            return False

        session["elements"] = [e for e in session["elements"] if e.get("id") != element_id]
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id)
        return True

    def clear_session(self, session_id: str) -> bool:
        """Clear all elements from session."""
        session = self.get_session(session_id)
        if not session:
            return False

        session["elements"] = []
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id)
        return True

    def _save_session(self, session_id: str):
        """Save session to disk."""
        if session_id in self._cache:
            session_path = self.sessions_dir / f"{session_id}.json"
            with open(session_path, "w") as f:
                json.dump(self._cache[session_id], f, indent=2)

    def get_canvas_state(self, session_id: str) -> Optional[CanvasState]:
        """Get canvas state for a session as a CanvasState model."""
        session = self.get_session(session_id)
        if not session:
            return None

        # Convert raw dict to CanvasState model
        try:
            elements = []
            for e in session.get("elements", []):
                if isinstance(e, dict) and "grid_position" in e:
                    gp = e["grid_position"]
                    if isinstance(gp, dict):
                        e["grid_position"] = GridPosition(**gp)
                    elements.append(PlacedElement(**e) if isinstance(e, dict) else e)

            return CanvasState(
                session_id=session_id,
                slide_title=session.get("slide_title", "Untitled Slide"),
                slide_purpose=session.get("slide_purpose", "presentation"),
                audience=session.get("audience"),
                tone=session.get("tone", "professional"),
                elements=elements,
                created_at=datetime.fromisoformat(session.get("created_at", datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(session["updated_at"]) if session.get("updated_at") else None
            )
        except Exception as e:
            logger.error(f"Error converting session to CanvasState: {e}")
            # Return a minimal valid CanvasState
            return CanvasState(session_id=session_id)

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session with optional ID."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        if session_id not in self._cache:
            self._cache[session_id] = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "elements": [],
                "history": [],
                "chat_messages": []
            }
            self._save_session(session_id)
        return session_id

    def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        suggestions: Optional[List[str]] = None
    ) -> bool:
        """Add a chat message to the session."""
        session = self.get_session(session_id)
        if not session:
            # Auto-create session if it doesn't exist
            self.create_session(session_id)
            session = self.get_session(session_id)

        if "chat_messages" not in session:
            session["chat_messages"] = []

        message = {
            "id": str(uuid.uuid4()),
            "role": str(role.value) if hasattr(role, 'value') else str(role),
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if suggestions:
            message["suggestions"] = suggestions

        session["chat_messages"].append(message)
        session["updated_at"] = datetime.now().isoformat()
        self._save_session(session_id)
        return True

    def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session with messages."""
        session = self.get_session(session_id)
        if session:
            return {
                "session_id": session_id,
                "messages": session.get("chat_messages", []),
                "element_count": len(session.get("elements", []))
            }
        return None

    def clear_canvas(self, session_id: str) -> bool:
        """Clear all elements from canvas (alias for clear_session)."""
        return self.clear_session(session_id)

    def save_session(self, session_id: str) -> bool:
        """Explicitly save session to disk."""
        if session_id in self._cache:
            self._save_session(session_id)
            return True
        return False
