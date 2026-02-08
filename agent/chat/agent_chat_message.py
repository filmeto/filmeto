"""
Message module for Filmeto agent system.
Defines the AgentMessage class and message types.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import uuid
from datetime import datetime
from agent.chat.agent_chat_types import ContentType
from agent.chat.content import StructureContent, TextContent


@dataclass
class AgentMessage:
    """
    Represents a message in the agent communication system.
    """
    sender_id: str
    sender_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    structured_content: List[StructureContent] = field(default_factory=list)

    def get_primary_content_type(self) -> ContentType:
        """
        Get the primary content type from structured_content.
        Returns the content type of the first item, or TEXT if empty.

        Priority: error > thinking > progress > tool_call > text > typing
        """
        if not self.structured_content:
            return ContentType.TEXT

        type_priority = [
            ContentType.ERROR,
            ContentType.THINKING,
            ContentType.PROGRESS,
            ContentType.TOOL_CALL,
            ContentType.TEXT,
            ContentType.TYPING,
        ]

        for sc in self.structured_content:
            if sc.content_type in type_priority:
                return sc.content_type

        # Fallback to first item's content type
        return self.structured_content[0].content_type

    def get_text_content(self) -> str:
        """
        Extract text content from structured_content for backward compatibility.
        Returns the first TEXT content found, or empty string if none exists.
        """
        if not self.structured_content:
            return ""
        for sc in self.structured_content:
            if sc.content_type == ContentType.TEXT and isinstance(sc, TextContent):
                return sc.text
        return ""

    @property
    def content(self) -> str:
        """
        Property for backward compatibility - returns text content from structured_content.
        """
        return self.get_text_content()