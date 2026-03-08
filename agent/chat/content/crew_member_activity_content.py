"""Crew member activity content for showing thinking/typing status."""
from typing import Any, Dict, List
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class CrewMemberActivityContent(StructureContent):
    """Content indicating which crew members are currently active (thinking/typing).

    This content type is used to display real-time activity indicators for
    crew members who are currently processing requests.
    """

    content_type: ContentType = None  # Will be set after enum is added
    crew_members: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Set content_type after initialization."""
        if self.content_type is None:
            self.content_type = ContentType.CREW_MEMBER_ACTIVITY

    def _get_data(self) -> Dict[str, Any]:
        return {"crew_members": self.crew_members}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrewMemberActivityContent":
        """Create from dictionary."""
        data_field = data.get("data", {}) or {}
        crew_members = data_field.get("crew_members", [])
        if not isinstance(crew_members, list):
            crew_members = []

        ct = data.get("content_type", "crew_member_activity")
        return cls(
            content_type=ContentType(ct) if isinstance(ct, str) else ct,
            title=data.get("title", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            crew_members=crew_members,
        )