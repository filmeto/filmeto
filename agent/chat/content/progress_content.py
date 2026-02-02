"""Progress content for Filmeto agent system."""
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class ProgressContent(StructureContent):
    """Progress update content."""
    content_type: ContentType = ContentType.PROGRESS
    progress: Union[str, int, float] = ""
    percentage: Optional[int] = None
    tool_name: Optional[str] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {"progress": self.progress}
        if self.percentage is not None:
            data["percentage"] = self.percentage
        if self.tool_name:
            data["tool_name"] = self.tool_name
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressContent':
        """Create a ProgressContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            progress=data_dict.get("progress", ""),
            percentage=data_dict.get("percentage"),
            tool_name=data_dict.get("tool_name")
        )
