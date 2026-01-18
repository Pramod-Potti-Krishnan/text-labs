"""
Chat Models for Text Labs
==========================

Models for chat messages and sessions.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRole(str, Enum):
    """Role of chat participant."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A single chat message."""
    role: ChatRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    element_id: Optional[str] = None
    suggestions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatSession(BaseModel):
    """A chat session."""
    session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def add_message(
        self,
        role: ChatRole,
        content: str,
        element_id: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ) -> ChatMessage:
        """Add a message to the session."""
        message = ChatMessage(
            role=role,
            content=content,
            element_id=element_id,
            suggestions=suggestions
        )
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message

    def get_context_messages(self, limit: int = 50) -> List[ChatMessage]:
        """Get recent messages for context."""
        return self.messages[-limit:]
