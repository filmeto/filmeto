"""Skill content for Filmeto agent system."""
from typing import Any, Dict, List
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class SkillContent(StructureContent):
    """Skill information content."""
    content_type: ContentType = ContentType.SKILL
    skill_name: str = ""
    skill_description: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    example_call: str = None
    usage_criteria: str = None

    def _get_data(self) -> Dict[str, Any]:
        data = {
            "skill_name": self.skill_name,
            "description": self.skill_description,
            "parameters": self.parameters
        }
        if self.example_call:
            data["example_call"] = self.example_call
        if self.usage_criteria:
            data["usage_criteria"] = self.usage_criteria
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillContent':
        """Create a SkillContent from a dictionary."""
        data_dict = data.get("data", {})
        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            skill_name=data_dict.get("skill_name", ""),
            skill_description=data_dict.get("description", ""),
            parameters=data_dict.get("parameters", []),
            example_call=data_dict.get("example_call"),
            usage_criteria=data_dict.get("usage_criteria")
        )
