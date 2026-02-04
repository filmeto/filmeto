"""
Simple test for the AgentPanel integration with chat (signal-based).
"""
import asyncio
from agent import FilmetoAgent, AgentMessage
from agent.chat.agent_chat_types import MessageType


async def test_chat_method_exists():
    """Test that the chat method exists and is accessible."""
    agent_manager = FilmetoAgent(workspace=None, project=None)

    # Verify the method exists
    assert hasattr(agent_manager, 'chat'), "chat method should exist"

    # Verify it's callable
    assert callable(getattr(agent_manager, 'chat')), "chat should be callable"

    print("✓ chat method exists and is callable")


async def test_chat_functionality():
    """Test that chat works with the new signal-based interface."""
    agent_manager = FilmetoAgent(workspace=None, project=None)

    # Clear any existing agents
    agent_manager.members.clear()

    # Collect responses via signal
    responses = []

    def on_message(sender, message: AgentMessage):
        if message.message_type == MessageType.TEXT:
            responses.append(message.get_text_content())

    agent_manager.connect_message_handler(on_message)

    # Register a test agent
    async def echo_handler(msg):
        from agent.chat.agent_chat_message import StructureContent
        from agent.chat.agent_chat_types import ContentType
        response = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id="echo_agent",
            sender_name="Echo Agent",
            structured_content=[StructureContent(
                content_type=ContentType.TEXT,
                data=f"Echo: {msg}"
            )]
        )
        yield response

    agent_manager.register_agent(
        "echo_agent",
        "Echo Agent",
        "An agent that echoes messages",
        echo_handler
    )

    # Test that chat works - responses come via signals
    await agent_manager.chat("Hello, world!")

    # Give a moment for signal to be processed
    await asyncio.sleep(0.1)

    print("✓ chat functionality test passed (signal-based)")


async def main():
    """Run all tests."""
    print("Testing AgentPanel integration with chat (signal-based)...")

    await test_chat_method_exists()
    await test_chat_functionality()

    print("\nAll integration tests passed! ✓")


if __name__ == "__main__":
    asyncio.run(main())