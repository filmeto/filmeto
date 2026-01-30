"""
Utility functions for the Filmeto agent system.
"""

from .chat.agent_chat_message import AgentMessage
from .chat.structure_content import TextContent
from .chat.agent_chat_types import MessageType, ContentType


def create_text_message(content: str, sender_id: str, sender_name: str = "") -> AgentMessage:
    """
    Create a text message for the agent system.

    Args:
        content: The content of the message
        sender_id: The ID of the sender
        sender_name: The name of the sender (optional)

    Returns:
        AgentMessage: A new text message
    """
    return AgentMessage(
        message_type=MessageType.TEXT,
        sender_id=sender_id,
        sender_name=sender_name,
        structured_content=[TextContent(text=content)]
    )


def create_error_message(content: str, sender_id: str, sender_name: str = "") -> AgentMessage:
    """
    Create an error message for the agent system.

    Args:
        content: The error content
        sender_id: The ID of the sender
        sender_name: The name of the sender (optional)

    Returns:
        AgentMessage: A new error message
    """
    return AgentMessage(
        message_type=MessageType.ERROR,
        sender_id=sender_id,
        sender_name=sender_name,
        structured_content=[TextContent(text=content)]
    )


def create_system_message(content: str, sender_id: str, sender_name: str = "") -> AgentMessage:
    """
    Create a system message for the agent system.

    Args:
        content: The system message content
        sender_id: The ID of the sender
        sender_name: The name of the sender (optional)

    Returns:
        AgentMessage: A new system message
    """
    return AgentMessage(
        message_type=MessageType.SYSTEM,
        sender_id=sender_id,
        sender_name=sender_name,
        structured_content=[TextContent(text=content)]
    )