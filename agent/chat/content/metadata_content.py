"""Metadata content for Filmeto agent system."""
from typing import Any, Dict
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class MetadataContent(StructureContent):
    """Metadata content (e.g., todo updates, task status)."""
    content_type: ContentType = ContentType.METADATA
    metadata_type: str = ""  # e.g., "todo_update", "task_status"
    metadata_data: Dict[str, Any] = field(default_factory=dict)

    def _get_data(self) -> Dict[str, Any]:
        return {
            "metadata_type": self.metadata_type,
            "data": self.metadata_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataContent':
        """Create a MetadataContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            metadata_type=data_dict.get("metadata_type", ""),
            metadata_data=data_dict.get("data", {})
        )
