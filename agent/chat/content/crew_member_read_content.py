"""Crew member read content for message router read indicators."""
from typing import Any, Dict, List
from dataclasses import dataclass, field

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


@dataclass
class CrewMemberReadContent(StructureContent):
    """Content indicating which crew members have read the message (from message router)."""

    content_type: ContentType = ContentType.CREW_MEMBER_READ
    crew_members: List[Dict[str, Any]] = field(default_factory=list)

    def _get_data(self) -> Dict[str, Any]:
        return {"crew_members": self.crew_members}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrewMemberReadContent":
        """Create from dictionary."""
        data_field = data.get("data", {}) or {}
        crew_members = data_field.get("crew_members", [])
        if isinstance(crew_members, list):
            pass
        else:
            crew_members = []

        ct = data.get("content_type", "crew_member_read")
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
