"""Typing content for Filmeto agent system."""
from typing import Any, Dict
from dataclasses import dataclass, field
from enum import Enum

from agent.chat.content.structure_content import StructureContent
from agent.chat.content.content_status import ContentStatus
from agent.chat.agent_chat_types import ContentType


class TypingState(str, Enum):
    """Typing indicator states."""
    START = "start"  # Typing started - show indicator
    END = "end"      # Typing ended - hide indicator


@dataclass
class TypingContent(StructureContent):
    """Agent typing indicator content - shows when agent is processing."""
    content_type: ContentType = ContentType.TYPING
    state: TypingState = TypingState.START

    def _get_data(self) -> Dict[str, Any]:
        return {
            "state": self.state.value if isinstance(self.state, TypingState) else self.state,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TypingContent':
        """Create a TypingContent from a dictionary."""
        # Parse state from data if available
        state_value = data.get("state", "start")
        if isinstance(state_value, str):
            try:
                state = TypingState(state_value)
            except ValueError:
                state = TypingState.START
        else:
            state = TypingState.START

        return cls(
            content_type=ContentType(data["content_type"]),
            title=data.get("title"),
            description=data.get("description"),
            metadata=data.get("metadata"),
            content_id=data.get("content_id"),
            status=ContentStatus(data.get("status", "creating")),
            parent_id=data.get("parent_id"),
            state=state,
        )
