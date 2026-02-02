"""Base structure content class for Filmeto agent system."""
from typing import Any, Dict
from dataclasses import dataclass, field
import uuid

from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class StructureContent:
    """
    Base class for structured content within a message.
    Each StructureContent represents a specific type of content in a message card.
    """
    content_type: ContentType
    title: str = None
    description: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ContentStatus = ContentStatus.CREATING
    parent_id: str = None  # For tracking hierarchical content (e.g., tool -> tool_progress)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the StructureContent to a dictionary representation."""
        return {
            "content_id": self.content_id,
            "content_type": self.content_type.value,
            "title": self.title,
            "description": self.description,
            "data": self._get_data(),
            "metadata": self.metadata,
            "status": self.status.value,
            "parent_id": self.parent_id
        }

    def _get_data(self) -> Dict[str, Any]:
        """Get the data payload for this content. Override in subclasses."""
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructureContent':
        """Create a StructureContent from a dictionary."""
        from agent.chat.content import _CONTENT_CLASS_MAP
        content_type = ContentType(data["content_type"])
        # Dispatch to appropriate subclass
        subclass = _CONTENT_CLASS_MAP.get(content_type, cls)
        return subclass.from_dict(data)

    def update(self, **kwargs):
        """Update content fields and set status to UPDATING."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.status = ContentStatus.UPDATING

    def complete(self):
        """Mark content as completed."""
        self.status = ContentStatus.COMPLETED

    def fail(self, error: str = None):
        """Mark content as failed."""
        self.status = ContentStatus.FAILED
        if error:
            self.metadata["error"] = error
