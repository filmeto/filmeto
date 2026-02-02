"""
Test error AgentEvent conversion and display.

Tests that:
1. ErrorContent is properly created
2. AgentEvent with ERROR type is converted to AgentMessage correctly
3. ErrorContentWidget displays the error properly
4. Message card handles ERROR content correctly
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from agent.event.agent_event import AgentEvent, AgentEventType
from agent.chat.content import ErrorContent, ContentType
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType
from agent.filmeto_agent import FilmetoAgent


class TestErrorEventDisplay:
    """Tests for error event display in chat."""

    def setup_method(self):
        """Set up Qt application for testing."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

    def test_error_content_creation(self):
        """Test that ErrorContent can be created properly."""
        content = ErrorContent(
            error_message="Test error message",
            error_type="TestError",
            details="Error details here",
            title="Error Title",
            description="Error description"
        )

        assert content.content_type == ContentType.ERROR
        assert content.error_message == "Test error message"
        assert content.error_type == "TestError"
        assert content.details == "Error details here"
        assert content.title == "Error Title"
        assert content.description == "Error description"

    def test_error_content_to_dict(self):
        """Test that ErrorContent can be converted to dict."""
        content = ErrorContent(
            error_message="Test error",
            error_type="TestError",
            details="Details"
        )

        data = content.to_dict()

        assert data["content_type"] == ContentType.ERROR.value
        assert data["data"]["error"] == "Test error"
        assert data["data"]["error_type"] == "TestError"
        assert data["data"]["details"] == "Details"

    def test_error_content_from_dict(self):
        """Test that ErrorContent can be created from dict."""
        data = {
            "content_type": ContentType.ERROR.value,
            "content_id": "test-id",
            "title": "Error",
            "description": "Test error",
            "metadata": {},
            "status": "creating",
            "parent_id": None,
            "data": {
                "error": "Test error message",
                "error_type": "TestError",
                "details": "Error details"
            }
        }

        content = ErrorContent.from_dict(data)

        assert content.content_type == ContentType.ERROR
        assert content.error_message == "Test error message"
        assert content.error_type == "TestError"
        assert content.details == "Error details"

    def test_agent_event_error_factory(self):
        """Test AgentEvent.error() factory method."""
        event = AgentEvent.error(
            error_message="Test error",
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="test_sender",
            sender_name="Test Sender"
        )

        assert event.event_type == AgentEventType.ERROR.value
        assert event.content is not None
        assert isinstance(event.content, ErrorContent)
        assert event.content.error_message == "Test error"
        assert event.project_name == "test_project"

    def test_convert_error_event_to_message(self):
        """Test _convert_event_to_message with ERROR event."""
        from PySide6.QtWidgets import QApplication

        # Create minimal FilmetoAgent for testing
        agent = FilmetoAgent()

        # Create an error event
        error_content = ErrorContent(
            error_message="Something went wrong",
            error_type="RuntimeError",
            details="Full error traceback here",
            title="Error",
            description="An error occurred"
        )

        event = AgentEvent(
            event_type=AgentEventType.ERROR.value,
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="test_sender",
            sender_name="Test Sender",
            content=error_content
        )

        # Convert to message
        message = agent._convert_event_to_message(
            event=event,
            sender_id="test_sender",
            sender_name="Test Sender",
            message_id="test_msg_id"
        )

        # Verify the message
        assert message is not None
        assert message.message_type == MessageType.ERROR
        assert message.sender_id == "test_sender"
        assert message.sender_name == "Test Sender"
        assert message.message_id == "test_msg_id"
        assert len(message.structured_content) == 1
        assert isinstance(message.structured_content[0], ErrorContent)
        assert message.structured_content[0].error_message == "Something went wrong"

    def test_skill_error_event(self):
        """Test SKILL_ERROR event type."""
        from agent.chat.content import ErrorContent

        # Create a skill error event
        event = AgentEvent.create(
            event_type=AgentEventType.SKILL_ERROR.value,
            project_name="test_project",
            react_type="skill_test",
            run_id="test_run",
            step_id=1,
            sender_id="skill_test",
            sender_name="Test Skill",
            content=ErrorContent(
                error_message="Skill execution failed",
                title="Skill Error",
                description="Error executing skill"
            )
        )

        assert event.event_type == AgentEventType.SKILL_ERROR.value
        assert event.content.error_message == "Skill execution failed"

    def test_error_content_widget_creation(self, qtbot):
        """Test that ErrorContentWidget can be created and displays error."""
        from app.ui.chat.message.error_content_widget import ErrorContentWidget

        content = ErrorContent(
            error_message="Test error message",
            error_type="TestError",
            details="Error details here",
            title="Error",
            description="Test description"
        )

        widget = ErrorContentWidget(content)

        # Verify widget was created
        assert widget is not None
        assert widget.structure_content == content

        # Verify widget has children
        assert widget.layout() is not None
        assert widget.layout().count() > 0

    def test_error_content_widget_get_state(self):
        """Test ErrorContentWidget.get_state() method."""
        from app.ui.chat.message.error_content_widget import ErrorContentWidget

        content = ErrorContent(
            error_message="Test error",
            error_type="TestError",
            details="Details"
        )

        widget = ErrorContentWidget(content)
        state = widget.get_state()

        assert state["error_message"] == "Test error"
        assert state["error_type"] == "TestError"
        assert state["details"] == "Details"

    def test_error_content_widget_set_state(self):
        """Test ErrorContentWidget.set_state() method."""
        from app.ui.chat.message.error_content_widget import ErrorContentWidget

        content = ErrorContent(
            error_message="Original error",
            error_type="OriginalError",
            details="Original details"
        )

        widget = ErrorContentWidget(content)

        # Set new state
        new_state = {
            "error_message": "Updated error",
            "error_type": "UpdatedError",
            "details": "Updated details"
        }

        widget.set_state(new_state)

        # Verify state was updated
        assert widget.structure_content.error_message == "Updated error"
        assert widget.structure_content.error_type == "UpdatedError"
        assert widget.structure_content.details == "Updated details"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
