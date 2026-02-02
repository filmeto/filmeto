"""Error content for Filmeto agent system."""
from typing import Any, Dict, Optional
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class ErrorContent(StructureContent):
    """Error message content."""
    content_type: ContentType = ContentType.ERROR
    error_message: str = ""
    error_type: Optional[str] = None
    details: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {"error": self.error_message}
        if self.error_type:
            data["error_type"] = self.error_type
        if self.details:
            data["details"] = self.details
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorContent':
        """Create a ErrorContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            error_message=data_dict.get("error", ""),
            error_type=data_dict.get("error_type"),
            details=data_dict.get("details")
        )
