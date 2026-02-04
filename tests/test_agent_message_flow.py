"""
Test the complete message flow from FilmetoAgent to UI components.

This test verifies that:
1. FilmetoAgent sends messages via its signals
2. AgentChatWidget receives messages through the connected handler
3. Messages are properly queued and processed
4. Chat history widget receives the messages for display
"""

import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.filmeto_agent import FilmetoAgent
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType
from agent.chat.content import TextContent, ThinkingContent
from agent.llm.llm_service import LlmService


class MockLlmService:
    """Mock LlmService for testing."""
    def __init__(self, workspace):
        self.workspace = workspace
        self.api_key = "test_key"
        self.api_base = "https://api.openai.com/v1"
        self.default_model = "gpt-4o-mini"
        self.provider = "openai"

    def validate_config(self):
        return True


class TestAgentMessageFlow:
    """Test the complete message flow from agent to UI."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock workspace and project
        self.mock_workspace = Mock()
        self.mock_workspace.workspace_path = '/tmp/test_workspace'
        self.mock_workspace.get_settings = Mock(return_value={
            'ai_services.openai_api_key': 'test_key',
            'ai_services.openai_host': 'https://api.openai.com/v1',
            'ai_services.default_model': 'gpt-4o-mini'
        })
        self.mock_workspace.get_project = Mock(return_value=None)
        self.mock_workspace.get_projects = Mock(return_value={})

        self.mock_project = Mock()
        self.mock_project.project_name = 'test_project'
        self.mock_project.workspace = self.mock_workspace
        self.mock_project.path = '/tmp/test_project'

        # Patch LlmService to use mock
        self.llm_patch = patch('agent.filmeto_agent.LlmService', MockLlmService)
        self.llm_patch.start()

        # Clear cached instances
        FilmetoAgent._instances.clear()

    def teardown_method(self):
        """Clean up after tests."""
        # Stop patch
        if hasattr(self, 'llm_patch'):
            self.llm_patch.stop()
        # Clear cached instances
        FilmetoAgent._instances.clear()

    def test_filmeto_agent_signal_creation(self):
        """Test that FilmetoAgent creates its own signals instance."""
        # Clear any cached instances
        FilmetoAgent._instances.clear()

        agent = FilmetoAgent(
            workspace=self.mock_workspace,
            project=self.mock_project
        )

        # Verify agent has its own signals instance
        assert hasattr(agent, 'signals')
        assert agent.signals is not None
        print("✓ FilmetoAgent creates its own signals instance")

    def test_connect_message_handler(self):
        """Test that message handlers can be connected to agent."""
        FilmetoAgent._instances.clear()

        agent = FilmetoAgent(
            workspace=self.mock_workspace,
            project=self.mock_project
        )

        # Track if handler was called
        received_messages = []

        def test_handler(sender, **kwargs):
            message = kwargs.get('message')
            received_messages.append(message)

        # Connect handler
        agent.connect_message_handler(test_handler)

        # Verify connection (no direct way to check, but we can test by sending)
        async def test():
            msg = AgentMessage(
                message_type=MessageType.TEXT,
                sender_id='test_agent',
                sender_name='Test Agent',
                structured_content=[TextContent(text='Test message')]
            )
            await agent.signals.send_agent_message(msg)
            await agent.signals.join()

            assert len(received_messages) == 1
            assert received_messages[0].get_text_content() == 'Test message'
            print("✓ Message handler receives messages correctly")

        asyncio.run(test())

    def test_disconnect_message_handler(self):
        """Test that message handlers can be disconnected."""
        FilmetoAgent._instances.clear()

        agent = FilmetoAgent(
            workspace=self.mock_workspace,
            project=self.mock_project
        )

        received_messages = []

        def test_handler(sender, **kwargs):
            message = kwargs.get('message')
            received_messages.append(message)

        agent.connect_message_handler(test_handler)
        agent.disconnect_message_handler(test_handler)

        async def test():
            msg = AgentMessage(
                message_type=MessageType.TEXT,
                sender_id='test_agent',
                sender_name='Test Agent',
                structured_content=[TextContent(text='Test message')]
            )
            await agent.signals.send_agent_message(msg)
            await agent.signals.join()

            # Should not receive message after disconnect
            assert len(received_messages) == 0
            print("✓ Message handler can be disconnected")

        asyncio.run(test())

    def test_multiple_message_types(self):
        """Test that different message types are sent correctly."""
        FilmetoAgent._instances.clear()

        agent = FilmetoAgent(
            workspace=self.mock_workspace,
            project=self.mock_project
        )

        received_messages = []

        def test_handler(sender, **kwargs):
            message = kwargs.get('message')
            received_messages.append(message)

        agent.connect_message_handler(test_handler)

        async def test():
            # Send different message types
            messages = [
                AgentMessage(
                    message_type=MessageType.TEXT,
                    sender_id='agent1',
                    sender_name='Agent 1',
                    structured_content=[TextContent(text='Text message')]
                ),
                AgentMessage(
                    message_type=MessageType.THINKING,
                    sender_id='agent1',
                    sender_name='Agent 1',
                    structured_content=[ThinkingContent(
                        thought='Thinking process',
                        step=1,
                        total_steps=3
                    )]
                ),
            ]

            for msg in messages:
                await agent.signals.send_agent_message(msg)

            await agent.signals.join()

            assert len(received_messages) == 2
            assert received_messages[0].message_type == MessageType.TEXT
            assert received_messages[1].message_type == MessageType.THINKING
            print("✓ Multiple message types are sent correctly")

        asyncio.run(test())

    def test_agent_instance_isolation(self):
        """Test that different agent instances have separate signals."""
        FilmetoAgent._instances.clear()

        agent1 = FilmetoAgent.get_instance(
            workspace=self.mock_workspace,
            project_name='project1'
        )

        agent2 = FilmetoAgent.get_instance(
            workspace=self.mock_workspace,
            project_name='project2'
        )

        # Verify they have different signals instances
        assert agent1.signals is not agent2.signals

        # Verify handlers are isolated
        agent1_messages = []
        agent2_messages = []

        def handler1(sender, **kwargs):
            agent1_messages.append(kwargs.get('message'))

        def handler2(sender, **kwargs):
            agent2_messages.append(kwargs.get('message'))

        agent1.connect_message_handler(handler1)
        agent2.connect_message_handler(handler2)

        async def test():
            msg1 = AgentMessage(
                message_type=MessageType.TEXT,
                sender_id='agent1',
                sender_name='Agent 1',
                structured_content=[TextContent(text='Message from agent1')]
            )

            msg2 = AgentMessage(
                message_type=MessageType.TEXT,
                sender_id='agent2',
                sender_name='Agent 2',
                structured_content=[TextContent(text='Message from agent2')]
            )

            await agent1.signals.send_agent_message(msg1)
            await agent2.signals.send_agent_message(msg2)
            await agent1.signals.join()
            await agent2.signals.join()

            # agent1's handler should only receive agent1's messages
            assert len(agent1_messages) == 1
            assert len(agent2_messages) == 1
            assert agent1_messages[0].sender_id == 'agent1'
            assert agent2_messages[0].sender_id == 'agent2'
            print("✓ Different agent instances have isolated signals")

        asyncio.run(test())

    def test_message_queue_simulation(self):
        """Test simulating the message queue behavior of AgentChatWidget."""
        FilmetoAgent._instances.clear()

        agent = FilmetoAgent(
            workspace=self.mock_workspace,
            project=self.mock_project
        )

        # Simulate message queue and processor
        message_queue = asyncio.Queue()
        processed_messages = []

        async def message_processor():
            """Simulate _process_messages from AgentChatWidget."""
            while True:
                try:
                    message = await message_queue.get()
                    if message is None:
                        break

                    # Simulate handle_agent_message
                    processed_messages.append(message)
                    message_queue.task_done()
                except asyncio.CancelledError:
                    break

        # Connect handler that puts messages in queue
        def queue_handler(sender, **kwargs):
            message = kwargs.get('message')
            # Use loop.create_task to avoid event loop issues
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(message_queue.put(message))
            except RuntimeError:
                # No loop running yet, will be handled by test
                pass

        agent.connect_message_handler(queue_handler)

        async def test():
            # Start processor
            processor_task = asyncio.create_task(message_processor())

            # Send multiple messages
            for i in range(5):
                msg = AgentMessage(
                    message_type=MessageType.TEXT,
                    sender_id='test_agent',
                    sender_name='Test Agent',
                    structured_content=[TextContent(text=f'Message {i}')]
                )
                await agent.signals.send_agent_message(msg)

            # Wait for agent signals to process all messages (100ms per message)
            await agent.signals.join()
            # Wait for message queue to process all messages
            await message_queue.join()
            # Additional wait to ensure processor finishes
            await asyncio.sleep(0.1)

            # Stop processor
            await message_queue.put(None)
            await processor_task

            assert len(processed_messages) == 5
            for i, msg in enumerate(processed_messages):
                assert f'Message {i}' in msg.get_text_content()
            print("✓ Message queue simulation works correctly")

        asyncio.run(test())

    def test_crew_member_message_flow(self):
        """Test complete message flow from crew member response to UI."""
        FilmetoAgent._instances.clear()

        agent = FilmetoAgent(
            workspace=self.mock_workspace,
            project=self.mock_project
        )

        # Simulate UI component message queue
        ui_message_queue = asyncio.Queue()
        ui_received_messages = []

        async def ui_message_processor():
            """Simulate UI message processor (like _process_messages in AgentChatWidget)."""
            while True:
                try:
                    message = await ui_message_queue.get()
                    if message is None:
                        break

                    # Simulate handle_agent_message being called
                    # In real UI, this would forward to chat_history_widget.handle_agent_message
                    ui_received_messages.append({
                        'sender_id': message.sender_id,
                        'sender_name': message.sender_name,
                        'message_type': message.message_type,
                        'content': message.get_text_content(),
                        'message_id': message.message_id
                    })
                    ui_message_queue.task_done()
                except asyncio.CancelledError:
                    break

        # Connect UI handler
        def ui_message_handler(sender, **kwargs):
            """Simulate _on_agent_message_sent in AgentChatWidget."""
            message = kwargs.get('message')
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ui_message_queue.put(message))
            except RuntimeError:
                pass

        agent.connect_message_handler(ui_message_handler)

        async def test():
            # Start UI processor
            ui_processor_task = asyncio.create_task(ui_message_processor())

            # Simulate crew member sending different types of messages
            # 1. Initial user message
            user_msg = AgentMessage(
                message_type=MessageType.TEXT,
                sender_id='user',
                sender_name='User',
                structured_content=[TextContent(text='Create a screenplay')]
            )
            await agent.signals.send_agent_message(user_msg)

            # 2. Crew member thinking message
            thinking_msg = AgentMessage(
                message_type=MessageType.THINKING,
                sender_id='director',
                sender_name='Director',
                structured_content=[ThinkingContent(
                    thought='I need to create a screenplay for the user',
                    step=1,
                    total_steps=3
                )]
            )
            await agent.signals.send_agent_message(thinking_msg)

            # 3. Crew member final response
            response_msg = AgentMessage(
                message_type=MessageType.TEXT,
                sender_id='director',
                sender_name='Director',
                structured_content=[TextContent(text='I have created a screenplay draft for your film.')]
            )
            await agent.signals.send_agent_message(response_msg)

            # Wait for agent signals to process all messages (100ms per message)
            await agent.signals.join()
            # Wait for UI message queue to process all messages
            await ui_message_queue.join()
            # Additional wait to ensure processor finishes
            await asyncio.sleep(0.1)

            # Stop processor
            await ui_message_queue.put(None)
            await ui_processor_task

            # Verify all messages were received
            assert len(ui_received_messages) == 3

            # Verify user message
            assert ui_received_messages[0]['sender_id'] == 'user'
            assert ui_received_messages[0]['message_type'] == MessageType.TEXT
            assert 'screenplay' in ui_received_messages[0]['content']

            # Verify thinking message
            assert ui_received_messages[1]['sender_id'] == 'director'
            assert ui_received_messages[1]['message_type'] == MessageType.THINKING

            # Verify response message
            assert ui_received_messages[2]['sender_id'] == 'director'
            assert ui_received_messages[2]['message_type'] == MessageType.TEXT
            assert 'screenplay draft' in ui_received_messages[2]['content']

            print("✓ Crew member message flow works correctly")

        asyncio.run(test())


def run_tests():
    """Run all tests."""
    test = TestAgentMessageFlow()

    print("Running Agent Message Flow Tests...\n")

    test.setup_method()
    test.test_filmeto_agent_signal_creation()

    test.setup_method()
    test.test_connect_message_handler()

    test.setup_method()
    test.test_disconnect_message_handler()

    test.setup_method()
    test.test_multiple_message_types()

    test.setup_method()
    test.test_agent_instance_isolation()

    test.setup_method()
    test.test_message_queue_simulation()

    test.setup_method()
    test.test_crew_member_message_flow()

    print("\n✅ All message flow tests passed!")


if __name__ == "__main__":
    run_tests()
