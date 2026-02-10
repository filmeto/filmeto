"""
Message module for Filmeto agent system.
Defines the AgentMessage class and message types.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import uuid
from datetime import datetime
from agent.chat.content import StructureContent


@dataclass
class AgentMessage:
    """
    Represents a message in the agent communication system.

    Message content is fully represented by structured_content.
    The message type is determined by the content_type of the first item in structured_content.
    """
    sender_id: str
    sender_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    structured_content: List[StructureContent] = field(default_factory=list)