"""Thinking content for Filmeto agent system."""
from typing import Any, Dict, Optional
from dataclasses import dataclass

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class ThinkingContent(StructureContent):
    """Agent thinking process content."""
    content_type: ContentType = ContentType.THINKING
    thought: str = ""
    step: Optional[int] = None
    total_steps: Optional[int] = None

    def _get_data(self) -> Dict[str, Any]:
        data = {"thought": self.thought}
        if self.step is not None:
            data["step"] = self.step
        if self.total_steps is not None:
            data["total_steps"] = self.total_steps
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThinkingContent':
        """Create a ThinkingContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            thought=data_dict.get("thought", ""),
            step=data_dict.get("step"),
            total_steps=data_dict.get("total_steps")
        )
