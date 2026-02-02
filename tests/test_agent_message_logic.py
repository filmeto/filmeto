"""
Simple test to verify the agent response handling logic
Updated to use AgentEvent instead of legacy StreamEvent
"""
import asyncio
import tempfile
from pathlib import Path

from agent.crew.crew_member import CrewMember
from app.data.project import Project
from app.data.workspace import Workspace
from agent.filmeto_agent import FilmetoAgent
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType
from agent.react import AgentEventType


async def test_agent_response_handling():
    """Test that agent responses are properly handled"""
    print("Testing agent response handling...")

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

            # Also check for other event types
            llm_call_start_events = [e for e in captured_events if e['event_type'] == AgentEventType.LLM_CALL_START]
            llm_call_end_events = [e for e in captured_events if e['event_type'] == AgentEventType.LLM_CALL_END]
            llm_thinking_events = [e for e in captured_events if e['event_type'] == AgentEventType.LLM_THINKING]

            print(f"LLM call start events: {len(llm_call_start_events)}")
            print(f"LLM call end events: {len(llm_call_end_events)}")
            print(f"LLM thinking events: {len(llm_thinking_events)}")

            all_expected_events_present = (
                has_final_response
            )

            if all_expected_events_present:
                print("\n SUCCESS: Agent responses are being generated correctly!")
                return True
            else:
                print(f"\nFAILURE: Missing some expected events")
                print(f"   Final responses: {has_final_response}")
                return False

        except Exception as e:
            print(f"ERROR during test: {e}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during test: {e}", exc_info=True)
            return False


def test_agent_message_creation():
    """Test creating AgentMessage for UI display"""
    print("\nTesting AgentMessage creation...")

    try:
        from agent.chat.content import TextContent

        # Create an AgentMessage
        message = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id="director",
            sender_name="Director",
            structured_content=[TextContent(text="Test agent response content")]
        )

        # Verify the message was created correctly
        content = message.get_text_content()
        sender_name = message.sender_name

        print(f"Extracted content: {content}")
        print(f"Extracted sender_name: {sender_name}")

        # Verify that we can extract the data correctly
        if content and sender_name:
            print(" SUCCESS: AgentMessage creation works correctly")
            return True
        else:
            print(" FAILURE: AgentMessage data extraction failed")
            return False

    except Exception as e:
        print(f"ERROR in AgentMessage test: {e}")
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in AgentMessage test: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("Running agent message logic tests (updated for AgentEvent)...\n")

    success1 = asyncio.run(test_agent_response_handling())
    success2 = test_agent_message_creation()

    if success1 and success2:
        print("\n All tests passed!")
    else:
        print("\n Some tests failed!")
