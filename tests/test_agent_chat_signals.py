"""
Test module for agent_chat_signals.py
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.agent_chat_types import MessageType
from agent.chat.content import TextContent


async def test_signal_connection():
    """Test that signals can be connected and sent."""
    received_messages = []

    def message_handler(sender, **kwargs):
        received_messages.append(kwargs.get('message'))

    signals = AgentChatSignals()
    signals.connect(message_handler)

    # Send a message
    message = AgentMessage(
        message_type=MessageType.TEXT,
        sender_id="agent1",
        sender_name="Test Agent",
        structured_content=[TextContent(text="Hello, world!")]
    )
    await signals.send_agent_message(message)

    # Check that the message was received
    assert len(received_messages) == 1
    assert received_messages[0] is message
    assert message.get_text_content() == "Hello, world!"
    assert message.sender_id == "agent1"
    assert message.sender_name == "Test Agent"
    assert message.message_type == MessageType.TEXT

    print("✓ Signal connection test passed")


def test_agent_message_properties():
    """Test AgentMessage properties."""
    metadata = {"timestamp": "2022-01-01", "type": "info"}
    message = AgentMessage(
        message_type=MessageType.TEXT,
        sender_id="sender123",
        sender_name="Sender Name",
        metadata=metadata,
        structured_content=[TextContent(text="Test message")]
    )

    assert message.get_text_content() == "Test message"
    assert message.sender_id == "sender123"
    assert message.sender_name == "Sender Name"
    assert message.message_type == MessageType.TEXT
    assert message.metadata == metadata

    print("✓ AgentMessage properties test passed")


async def main():
    await test_signal_connection()
    test_agent_message_properties()
    print("All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())