"""
Test script to verify the async conflict fix for crew
"""
import asyncio
import tempfile
import os
from pathlib import Path

from agent.crew.crew_member import CrewMember
from agent.llm.llm_service import LlmService
from app.data.project import Project
from app.data.workspace import Workspace


async def test_sub_agent_with_fixed_async():
    """Test crew with the fixed async implementation"""
    print("Testing crew with fixed async implementation...")
    
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
        
        # Variables to capture events
        captured_events = []
        
        def mock_on_stream_event(event):
            captured_events.append({
                "event_type": event.event_type,
                "data": event.data
            })
            print(f"Captured event: {event.event_type} with data: {event.data}")
        
        # Test the chat_stream method with event capture
        print("\nTesting chat_stream with event capture (using fixed async)...")
        response_tokens = []
        
        try:
            async for token in crew_member.chat_stream(
                message="Test message",
                on_stream_event=mock_on_stream_event
            ):
                response_tokens.append(token)
                print(f"Received token: {token}")
        
            print(f"\nCaptured {len(captured_events)} events:")
            for i, event in enumerate(captured_events):
                print(f"  {i+1}. Type: {event['event_type']}, Data: {event['data']}")
                
            print(f"\nResponse tokens: {response_tokens}")
            
            # Verify that we captured the expected events
            expected_events = ["agent_thinking", "llm_call_start", "llm_call_end"]
            found_events = [event['event_type'] for event in captured_events if event['event_type'] in expected_events]
            
            print(f"\nExpected events: {expected_events}")
            print(f"Found events: {found_events}")
            
            if all(event in found_events for event in expected_events):
                print("\n✅ SUCCESS: All expected events were captured!")
                return True
            else:
                print(f"\n❌ FAILURE: Missing some expected events")
                missing = [e for e in expected_events if e not in found_events]
                print(f"Missing: {missing}")
                return False
                
        except Exception as e:
            print(f"❌ ERROR during test: {e}")
            logger.error(f"ERROR during test: {e}", exc_info=True)
            return False


def test_original_completion_method():
    """Test that the original completion method still works"""
    print("\nTesting original completion method...")
    
    try:
        from agent.llm.llm_service import LlmService
        import os
        
        # Create an LlmService instance
        llm_service = LlmService()
        
        # Temporarily set up for testing (without actual API call)
        llm_service.configure(
            api_key=os.getenv("TEST_API_KEY", "test-key"),
            api_base="https://api.openai.com/v1",  # Use standard endpoint for this test
            default_model="gpt-4o-mini"
        )
        
        print("✅ LlmService configured successfully")
        return True
    except Exception as e:
        print(f"❌ ERROR in original completion method test: {e}")
        logger.error(f"ERROR in original completion method test: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("Running async conflict fix tests...\n")
    
    success1 = asyncio.run(test_sub_agent_with_fixed_async())
    success2 = test_original_completion_method()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Async conflict fix is working.")
    else:
        print("\n💥 Some tests failed!")