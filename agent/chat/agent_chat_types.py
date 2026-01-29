"""
Common enums for the agent module.
"""
from enum import Enum


class MessageType(Enum):
    """Enumeration of different message types."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    COMMAND = "command"
    ERROR = "error"
    SYSTEM = "system"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"


class ContentType(Enum):
    """Enumeration of different structured content types."""
    TEXT = "text"
    CODE_BLOCK = "code_block"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE_ATTACHMENT = "file_attachment"
    TABLE = "table"
    CHART = "chart"
    LINK = "link"
    BUTTON = "button"
    FORM = "form"
    PROGRESS = "progress"
    METADATA = "metadata"
    SKILL = "skill"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"
    ERROR = "error"