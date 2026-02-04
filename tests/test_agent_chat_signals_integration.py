"""
Integration test module for agent_chat_signals.py with the existing AgentMessage class
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


async def test_integration_with_existing_agentmessage():
    """Test that the signal system integrates properly with the existing AgentMessage class."""
    received_messages = []

    def message_handler(sender, **kwargs):
        received_messages.append(kwargs.get('message'))

    signals = AgentChatSignals()
    signals.connect(message_handler)

    message = AgentMessage(
        message_type=MessageType.TEXT,
        sender_id="integration_test_agent",
        sender_name="Integration Test Agent",
        metadata={"test": True, "category": "integration"},
        structured_content=[TextContent(text="Integration test message")]
    )
    await signals.send_agent_message(message)

    # Verify the received message
    assert len(received_messages) == 1
    received_message = received_messages[0]

    # Check that it's the same message object
    assert received_message is message

    # Check all the properties of the AgentMessage
    assert received_message.get_text_content() == "Integration test message"
    assert received_message.sender_id == "integration_test_agent"
    assert received_message.sender_name == "Integration Test Agent"
    assert received_message.message_type == MessageType.TEXT
    assert received_message.metadata == {"test": True, "category": "integration"}

    # Verify that it has all the expected attributes of the real AgentMessage class
    assert hasattr(received_message, 'message_id')
    assert hasattr(received_message, 'timestamp')
    assert hasattr(received_message, 'structured_content')

    print("✓ Integration test with existing AgentMessage passed")


async def test_different_message_types():
    """Test sending messages of different types."""
    received_messages = []

    def message_handler(sender, **kwargs):
        received_messages.append(kwargs.get('message'))

    signals = AgentChatSignals()
    signals.connect(message_handler)

    message_types = [MessageType.TEXT, MessageType.CODE, MessageType.SYSTEM, MessageType.THINKING]

    for msg_type in message_types:
        msg = AgentMessage(
            message_type=msg_type,
            sender_id="test_agent",
            sender_name="Test Agent",
            structured_content=[TextContent(text=f"Test {msg_type.value} message")]
        )
        await signals.send_agent_message(msg)

    assert len(received_messages) == len(message_types)

    for i, msg_type in enumerate(message_types):
        assert received_messages[i].message_type == msg_type
        assert f"Test {msg_type.value} message" in received_messages[i].get_text_content()

    print("✓ Different message types test passed")


async def main():
    await test_integration_with_existing_agentmessage()
    await test_different_message_types()
    print("All integration tests passed!")

if __name__ == "__main__":
    asyncio.run(main())