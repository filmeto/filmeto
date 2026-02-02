"""
Test script to verify crew event streaming functionality
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
from agent.react import AgentEventType


async def test_sub_agent_events():
    """Test crew event streaming functionality"""
    print("Testing crew event streaming...")

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
        # We'll use a mock that simulates the LLM call process
        class MockLlmService:
            async def acompletion(self, model, messages, temperature, stream=False, **kwargs):
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

        # Variables to capture AgentEvent objects
        captured_events = []

        # Test the chat_stream method with AgentEvent capturing
        print("\nTesting chat_stream with AgentEvent capture...")

        try:
            # chat_stream now yields AgentEvent objects directly (no on_stream_event callback)
            async for event in crew_member.chat_stream(message="Test message"):
                captured_events.append({
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "content": event.content
                })
                print(f"Captured event: {event.event_type}")

            print(f"\nCaptured {len(captured_events)} events:")
            for i, event in enumerate(captured_events):
                print(f"  {i+1}. Type: {event['event_type']}")

            # Verify that we captured some events
            event_types = [e['event_type'] for e in captured_events]
            print(f"\nCaptured event types: {event_types}")

            if len(captured_events) > 0:
                print("\n SUCCESS: Events were captured correctly!")
                return True
            else:
                print(f"\nFAILURE: No events captured")
                return False

        except Exception as e:
            print(f"ERROR during test: {e}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"ERROR during test: {e}", exc_info=True)
            return False


def test_filmeto_agent_integration():
    """Test integration with FilmetoAgent"""
    print("\nTesting FilmetoAgent integration...")

    try:
        from agent.filmeto_agent import FilmetoAgent
        from app.data.workspace import Workspace
        import tempfile
        from pathlib import Path

        # Create a temporary project
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
            from app.data.project import Project
            project = Project(
                project_name="test_project",
                project_path=str(project_path),
                workspace=workspace
            )

            # Create FilmetoAgent
            agent = FilmetoAgent(
                workspace=workspace,
                project=project,
                model="gpt-4o-mini"
            )

            # Verify that crew members were loaded
            print(f"Loaded crew members: {list(agent.crew_members.keys())}")

            if "director" in agent.crew_members:
                print(" SUCCESS: Crew member loaded correctly in FilmetoAgent")
                return True
            else:
                print(" FAILURE: Crew member not loaded in FilmetoAgent")
                return False

    except Exception as e:
        print(f"ERROR during FilmetoAgent integration test: {e}")
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"ERROR during FilmetoAgent integration test: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("Running crew event streaming tests (updated for AgentEvent)...\n")

    success1 = asyncio.run(test_sub_agent_events())
    success2 = test_filmeto_agent_integration()

    if success1 and success2:
        print("\n All tests passed!")
    else:
        print("\n Some tests failed!")
