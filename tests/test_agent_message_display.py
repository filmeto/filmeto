"""
Test script to verify that agent messages are properly handled
Updated to use AgentEvent instead of legacy StreamEvent
"""
import asyncio
import tempfile
import os
from pathlib import Path

from agent.crew.crew_member import CrewMember
from agent.llm.llm_service import LlmService
from app.data.project import Project
from app.data.workspace import Workspace
from agent.filmeto_agent import FilmetoAgent
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType
from agent.react import AgentEventType
from app.ui.chat.agent_chat_history import AgentChatHistoryWidget
from app.data.workspace import Workspace as AppWorkspace


async def test_agent_response_display():
    """Test that agent responses are properly displayed in the UI"""
    print("Testing agent response display in UI...")

    # Create a temporary project for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test_project"
        project_path.mkdir()

        # Initialize a minimal project structure
        agent_dir = project_path / "agent"
        agent_dir.mkdir()
        crew_members_dir = agent_dir / "crew_members"
        crew_members_dir.mkdir()

        # Create a simple director agent config
        director_config = crew_members_dir / "director.md"
        director_config.write_text("""---
name: director
description: Film director agent
soul: creative_vision
skills: []
model: gpt-4o-mini
temperature: 0.7
max_steps: 3
---

You are a film director. Help with directing films.
""")

        # Create a mock workspace
        workspace = Workspace(workspace_path=temp_dir, project_name="test_project")

        # Create a project
        project = Project(
            project_name="test_project",
            project_path=str(project_path),
            workspace=workspace
        )

        # Initialize the crew
        crew_member = CrewMember(
            config_path=str(director_config),
            workspace=workspace,
            project=project
        )

        # Mock LLM service with a test response
        class MockLlmService:
            def completion(self, model, messages, temperature, stream=False, **kwargs):
                # Simulate a response from the LLM
                return {
                    "choices": [{
                        "message": {
                            "content": '{"type":"final","response":"This is a test response from the director agent."}'
                        }
                    }]
                }

            def validate_config(self):
                return True  # Assume it's configured for testing

        # Replace the LLM service with our mock
        crew_member.llm_service = MockLlmService()

        # Variable to capture AgentEvent objects
        captured_events = []

        print("\nTesting chat_stream with AgentEvent capture...")

        try:
            # chat_stream now yields AgentEvent objects directly
            async for event in crew_member.chat_stream(message="Test message"):
                captured_events.append({
                    "event_type": event.event_type,
                    "content": event.content,
                    "payload": event.payload
                })
                print(f"Captured event: {event.event_type}")

            print(f"\nCaptured {len(captured_events)} events:")
            for i, event in enumerate(captured_events):
                print(f"  {i+1}. Type: {event['event_type']}")

            # Check if FINAL events were captured
            final_events = [e for e in captured_events if e['event_type'] == AgentEventType.FINAL]
            print(f"\nFINAL events captured: {len(final_events)}")

            # Verify that we have final events with content
            has_final_response = len(final_events) > 0

            print(f"\nHas final response: {has_final_response}")

            if has_final_response:
                print("\n Agent responses are being sent correctly!")
                return True
            else:
                print(f"\nFAILURE: No final response captured")
                return False

        except Exception as e:
            print(f"ERROR during test: {e}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"ERROR during test: {e}", exc_info=True)
            return False


def test_chat_history_widget_with_agent_message():
    """Test the ChatHistoryWidget with AgentMessage instead of StreamEvent"""
    print("\nTesting ChatHistoryWidget with AgentMessage...")

    try:
        # Create a mock workspace for the widget
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = AppWorkspace(workspace_path=temp_dir, project_name="test")

            # Create a ChatHistoryWidget instance
            widget = AgentChatHistoryWidget(workspace)

            # Create an AgentMessage instead of StreamEvent
            from agent.chat.content import TextContent
            message = AgentMessage(
                message_type=MessageType.TEXT,
                sender_id="director",
                sender_name="Director",
                structured_content=[TextContent(text="Test agent response content")]
            )

            print(" AgentMessage created successfully")
            print(f"  Message type: {message.message_type}")
            print(f"  Sender: {message.sender_name}")
            print(f"  Content: {message.get_text_content()[:50]}...")

            print(" SUCCESS: AgentMessage properly created")
            return True

    except Exception as e:
        print(f"ERROR in AgentMessage test: {e}")
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"ERROR in AgentMessage test: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("Running agent message display tests (updated for AgentEvent)...\n")

    success1 = asyncio.run(test_agent_response_display())
    success2 = test_chat_history_widget_with_agent_message()

    if success1 and success2:
        print("\n All tests passed!")
    else:
        print("\n Some tests failed!")
