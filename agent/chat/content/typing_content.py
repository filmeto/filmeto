"""Typing content for Filmeto agent system."""
from typing import Any, Dict
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class TypingContent(StructureContent):
    """Agent typing indicator content - shows when agent is processing."""
    content_type: ContentType = ContentType.TYPING

    def _get_data(self) -> Dict[str, Any]:
        # Typing content has minimal data since it's just an animation
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TypingContent':
        """Create a TypingContent from a dictionary."""
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
        )
