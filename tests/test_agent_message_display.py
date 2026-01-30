"""
Test script to verify that agent messages are now showing in the UI
"""
import asyncio
import tempfile
import os
from pathlib import Path

from agent.crew.crew_member import CrewMember
from agent.llm.llm_service import LlmService
from app.data.project import Project
from app.data.workspace import Workspace
from agent.filmeto_agent import FilmetoAgent, StreamEvent
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
        
        # Create a mock chat history widget to capture messages
        class MockChatHistoryWidget:
            def __init__(self):
                self.messages = []
                self.agent_cards = {}
            
            def get_or_create_agent_card(self, message_id, agent_name, agent_role=None):
                # Create a mock card
                if message_id not in self.agent_cards:
                    self.agent_cards[message_id] = {
                        'id': message_id,
                        'agent_name': agent_name,
                        'content': ''
                    }
                return self.agent_cards[message_id]
            
            def update_agent_card(self, message_id, content="", append=True, is_thinking=False, 
                                 thinking_text="", is_complete=False, structured_content=None, error=None):
                if message_id in self.agent_cards:
                    if append and self.agent_cards[message_id]['content']:
                        self.agent_cards[message_id]['content'] += content
                    else:
                        self.agent_cards[message_id]['content'] = content
                    
                    # Add to messages list for verification
                    self.messages.append({
                        'message_id': message_id,
                        'content': content,
                        'agent_name': self.agent_cards[message_id]['agent_name']
                    })
                else:
                    # Create new entry if not exists
                    new_id = message_id
                    self.agent_cards[new_id] = {
                        'id': new_id,
                        'agent_name': 'Unknown',
                        'content': content
                    }
                    self.messages.append({
                        'message_id': new_id,
                        'content': content,
                        'agent_name': 'Unknown'
                    })
        
        # Create mock chat history widget
        mock_widget = MockChatHistoryWidget()
        
        # Variable to capture stream events
        captured_events = []
        
        def mock_on_stream_event(event):
            captured_events.append({
                "event_type": event.event_type,
                "data": event.data
            })
            print(f"Captured event: {event.event_type} with data: {event.data}")
            
            # Simulate what happens in the UI
            if event.event_type == "agent_response":
                content = event.data.get('content', '')
                sender_name = event.data.get('sender_name', 'Unknown')
                session_id = event.data.get('session_id', 'unknown')
                
                import uuid
                message_id = f"response_{session_id}_{uuid.uuid4()}"
                
                mock_widget.update_agent_card(
                    message_id,
                    content=content,
                    append=False
                )
        
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
            
            # Check if agent_response events were captured and processed
            agent_response_events = [e for e in captured_events if e['event_type'] == 'agent_response']
            print(f"\nAgent response events captured: {len(agent_response_events)}")
            
            # Check messages in mock widget
            print(f"Messages in mock widget: {len(mock_widget.messages)}")
            for msg in mock_widget.messages:
                print(f"  - {msg['agent_name']}: {msg['content'][:50]}{'...' if len(msg['content']) > 50 else ''}")
            
            # Verify that we have agent response messages in the UI
            has_agent_responses = any('director' in msg['agent_name'].lower() or 
                                    'response' in msg['content'].lower() 
                                    for msg in mock_widget.messages)
            
            print(f"\nHas agent responses in UI: {has_agent_responses}")
            
            if has_agent_responses and len(agent_response_events) > 0:
                print("\n✅ SUCCESS: Agent responses are being sent and processed by UI!")
                return True
            else:
                print(f"\n❌ FAILURE: Agent responses not properly processed")
                print(f"   Agent response events: {len(agent_response_events)}")
                print(f"   Messages in UI: {len(mock_widget.messages)}")
                print(f"   Has agent responses: {has_agent_responses}")
                return False
                
        except Exception as e:
            print(f"❌ ERROR during test: {e}")
            logger.error(f"ERROR during test: {e}", exc_info=True)
            return False


def test_chat_history_widget_handle_stream_event():
    """Test the fixed handle_stream_event method in chat_history_widget"""
    print("\nTesting ChatHistoryWidget handle_stream_event method...")
    
    try:
        # Create a mock workspace for the widget
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = AppWorkspace(workspace_path=temp_dir, project_name="test")
            
            # Create a ChatHistoryWidget instance
            widget = AgentChatHistoryWidget(workspace)
            
            # Create a mock StreamEvent for agent_response
            from agent.filmeto_agent import StreamEvent
            event = StreamEvent("agent_response", {
                "content": "Test agent response content",
                "sender_name": "Director",
                "message_type": "text",
                "session_id": "test-session-123"
            })
            
            # Create a mock session
            from agent.filmeto_agent import AgentStreamSession
            session = AgentStreamSession("test-session-123", "Test initial message")
            
            # Call handle_stream_event
            widget.handle_stream_event(event, session)
            
            print("✅ ChatHistoryWidget handle_stream_event method executed without error")
            
            # Check if a message card was created
            print(f"Number of message cards: {len(widget._message_cards)}")
            print(f"Number of agent current cards: {len(widget._agent_current_cards)}")
            
            # Look for our agent response
            found_director_card = any(
                'Director' in card.agent_message.sender_name 
                for card in widget._message_cards.values()
            )
            
            print(f"Found Director card: {found_director_card}")
            
            if found_director_card:
                print("✅ SUCCESS: Agent response properly handled by ChatHistoryWidget")
                return True
            else:
                print("❌ FAILURE: Agent response not properly handled by ChatHistoryWidget")
                return False
                
    except Exception as e:
        print(f"❌ ERROR in ChatHistoryWidget test: {e}")
        logger.error(f"ERROR in ChatHistoryWidget test: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("Running agent message display fix tests...\n")
    
    success1 = asyncio.run(test_agent_response_display())
    success2 = test_chat_history_widget_handle_stream_event()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Agent messages should now display in the UI.")
    else:
        print("\n💥 Some tests failed!")