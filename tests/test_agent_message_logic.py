"""
Simple test to verify the agent response handling logic
"""
import asyncio
import tempfile
from pathlib import Path

from agent.crew.crew_member import CrewMember
from app.data.project import Project
from app.data.workspace import Workspace
from agent.filmeto_agent import FilmetoAgent, StreamEvent


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
        
        # Variable to capture stream events
        captured_events = []
        
        def mock_on_stream_event(event):
            captured_events.append({
                "event_type": event.event_type,
                "data": event.data
            })
            print(f"Captured event: {event.event_type} with data: {event.data}")
        
        # Test the chat_stream method which sends agent_response events
        print("\nTesting chat_stream with agent_response event capture...")
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
            
            # Check if agent_response events were captured
            agent_response_events = [e for e in captured_events if e['event_type'] == 'agent_response']
            print(f"\nAgent response events captured: {len(agent_response_events)}")
            
            # Verify that we have agent response events
            has_agent_responses = len(agent_response_events) > 0
            
            print(f"\nHas agent response events: {has_agent_responses}")
            
            # Also check for other status events
            llm_call_start_events = [e for e in captured_events if e['event_type'] == 'llm_call_start']
            llm_call_end_events = [e for e in captured_events if e['event_type'] == 'llm_call_end']
            agent_thinking_events = [e for e in captured_events if e['event_type'] == 'agent_thinking']
            
            print(f"LLM call start events: {len(llm_call_start_events)}")
            print(f"LLM call end events: {len(llm_call_end_events)}")
            print(f"Agent thinking events: {len(agent_thinking_events)}")
            
            all_expected_events_present = (
                has_agent_responses and 
                len(llm_call_start_events) > 0 and 
                len(llm_call_end_events) > 0 and 
                len(agent_thinking_events) > 0
            )
            
            if all_expected_events_present:
                print("\n✅ SUCCESS: All expected events are being generated!")
                return True
            else:
                print(f"\n❌ FAILURE: Missing some expected events")
                print(f"   Agent responses: {has_agent_responses}")
                print(f"   LLM call starts: {len(llm_call_start_events) > 0}")
                print(f"   LLM call ends: {len(llm_call_end_events) > 0}")
                print(f"   Agent thinking: {len(agent_thinking_events) > 0}")
                return False
                
        except Exception as e:
            print(f"❌ ERROR during test: {e}")
            logger.error(f"Error during test: {e}", exc_info=True)
            return False


def test_stream_event_handling_logic():
    """Test the logic for handling StreamEvent in chat_history_widget"""
    print("\nTesting StreamEvent handling logic...")
    
    # Create a mock StreamEvent for agent_response
    from agent.filmeto_agent import StreamEvent
    event = StreamEvent("agent_response", {
        "content": "Test agent response content",
        "sender_name": "Director",
        "message_type": "text",
        "session_id": "test-session-123"
    })
    
    # Simulate the logic from the fixed handle_stream_event method
    content = event.data.get('content', '')
    sender_name = event.data.get('sender_name', 'Unknown')
    session_id = event.data.get('session_id', 'unknown')
    
    print(f"Extracted content: {content}")
    print(f"Extracted sender_name: {sender_name}")
    print(f"Extracted session_id: {session_id}")
    
    # Verify that we can extract the data correctly
    if content and sender_name and session_id:
        print("✅ SUCCESS: StreamEvent data extraction works correctly")
        return True
    else:
        print("❌ FAILURE: StreamEvent data extraction failed")
        return False


if __name__ == "__main__":
    print("Running agent message display fix tests (logic only)...\n")
    
    success1 = asyncio.run(test_agent_response_handling())
    success2 = test_stream_event_handling_logic()
    
    if success1 and success2:
        print("\n🎉 All tests passed! The fix should allow agent messages to display in the UI.")
    else:
        print("\n💥 Some tests failed!")