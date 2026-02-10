"""LLM output content for Filmeto agent system."""
from typing import Any, Dict
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class LlmOutputContent(StructureContent):
    """LLM raw output content (collapsible by default)."""
    content_type: ContentType = ContentType.LLM_OUTPUT
    output: str = ""

    def _get_data(self) -> Dict[str, Any]:
        return {"output": self.output}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LlmOutputContent':
        """Create a LlmOutputContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            output=data_dict.get("output", "")
        )
