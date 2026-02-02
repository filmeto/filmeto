"""Text content for Filmeto agent system."""
from typing import Any, Dict
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class TextContent(StructureContent):
    """Plain text content."""
    content_type: ContentType = ContentType.TEXT
    text: str = ""

    def _get_data(self) -> Dict[str, Any]:
        return {"text": self.text}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextContent':
        """Create a TextContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            text=data_dict.get("text", "")
        )
