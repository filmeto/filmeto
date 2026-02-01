"""
Test that error events from execute_skill_script.py are properly displayed.

Tests that:
1. _create_event with "error" type creates ErrorContent
2. Error events from execute_skill_script are properly converted to AgentMessage
3. Error events are correctly displayed in the UI
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from agent.tool.system.execute_skill_script import ExecuteSkillScriptTool
from agent.event.agent_event import AgentEvent, AgentEventType
from agent.chat.structure_content import ErrorContent, ContentType
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType
from agent.filmeto_agent import FilmetoAgent


class TestExecuteSkillScriptErrorDisplay:
    """Tests for error display from execute_skill_script."""

    def setup_method(self):
        """Set up Qt application for testing."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()

    def test_create_event_with_error_type(self):
        """Test that _create_event with 'error' creates ErrorContent."""
        tool = ExecuteSkillScriptTool()

        event = tool._create_event(
            event_type="error",
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="test_sender",
            sender_name="Test Sender",
            error="Test error message"
        )

        # Verify event type
        assert event.event_type == "error"

        # Verify content is ErrorContent
        assert event.content is not None
        assert isinstance(event.content, ErrorContent)
        assert event.content.error_message == "Test error message"
        assert event.content.title == "Tool Error"
        assert event.content.description == "Error in execute_skill_script"

    def test_script_not_found_error_event(self):
        """Test that script not found creates proper error event."""
        tool = ExecuteSkillScriptTool()

        # Test with non-existent script_path
        events = []
        import asyncio

        async def collect_events():
            async for event in tool.execute(
                parameters={
                    "script_path": "/nonexistent/path/to/script.py"
                },
                context=None,
                project_name="test_project",
                react_type="test_react",
                run_id="test_run",
                step_id=1,
                sender_id="test_sender",
                sender_name="Test Sender"
            ):
                events.append(event)

        asyncio.run(collect_events())

        # Should have yielded an error event
        assert len(events) == 1
        assert events[0].event_type == "error"
        assert isinstance(events[0].content, ErrorContent)
        assert "Script not found" in events[0].content.error_message

    def test_missing_parameters_error_event(self):
        """Test that missing parameters creates proper error event."""
        tool = ExecuteSkillScriptTool()

        # Test with no parameters
        events = []
        import asyncio

        async def collect_events():
            async for event in tool.execute(
                parameters={},
                context=None,
                project_name="test_project",
                react_type="test_react",
                run_id="test_run",
                step_id=1,
                sender_id="test_sender",
                sender_name="Test Sender"
            ):
                events.append(event)

        asyncio.run(collect_events())

        # Should have yielded an error event
        assert len(events) == 1
        assert events[0].event_type == "error"
        assert isinstance(events[0].content, ErrorContent)
        assert "must be provided" in events[0].content.error_message

    def test_error_event_to_message_conversion(self):
        """Test that error event from tool converts to AgentMessage properly."""
        tool = ExecuteSkillScriptTool()

        # Create error event using _create_event
        event = tool._create_event(
            event_type="error",
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="execute_skill_script",
            sender_name="Execute Skill Script",
            error="Script execution failed"
        )

        # Convert to message
        agent = FilmetoAgent()
        message = agent._convert_event_to_message(
            event=event,
            sender_id="execute_skill_script",
            sender_name="Execute Skill Script",
            message_id="test_msg_id"
        )

        # Verify message
        assert message is not None
        assert message.message_type == MessageType.ERROR
        assert message.sender_id == "execute_skill_script"
        assert message.sender_name == "Execute Skill Script"
        assert len(message.structured_content) == 1
        assert isinstance(message.structured_content[0], ErrorContent)
        assert message.structured_content[0].error_message == "Script execution failed"

    def test_error_content_widget_for_tool_error(self, qtbot):
        """Test that ErrorContentWidget displays tool errors properly."""
        from app.ui.chat.message.error_content_widget import ErrorContentWidget

        # Create ErrorContent like _create_event would
        content = ErrorContent(
            error_message="Script not found at /path/to/script.py",
            title="Tool Error",
            description="Error in execute_skill_script"
        )

        widget = ErrorContentWidget(content)

        # Verify widget was created
        assert widget is not None
        assert widget.structure_content.error_message == "Script not found at /path/to/script.py"

    def test_error_event_payload_vs_content(self):
        """Test that error events use content field, not payload."""
        tool = ExecuteSkillScriptTool()

        event = tool._create_event(
            event_type="error",
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            error="Test error"
        )

        # Verify content is set (not just payload)
        assert event.content is not None
        assert isinstance(event.content, ErrorContent)
        assert event.content.error_message == "Test error"

        # Verify event can be validated
        # AgentEvent requires content or payload
        assert event.content is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
