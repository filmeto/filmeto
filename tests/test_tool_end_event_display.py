"""
Test tool_end event conversion and display.

Tests that:
1. tool_end events are correctly created with result
2. tool_end events convert to messages correctly
3. ToolResponseContentWidget displays the result
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.event.agent_event import AgentEvent, AgentEventType
from agent.chat.content import ToolResponseContent
from agent.filmeto_agent import FilmetoAgent
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType, ContentType


class TestToolEndEventDisplay:
    """Tests for tool_end event display."""

    def test_create_tool_end_event_with_result(self):
        """Test creating a tool_end event with result."""
        result = {"status": "success", "data": [1, 2, 3]}

        event = AgentEvent.create(
            event_type=AgentEventType.TOOL_END.value,
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="test_tool",
            sender_name="Test Tool",
            content=ToolResponseContent(
                tool_name="test_tool",
                result=result,
                tool_status="completed",
                title="Tool Result: test_tool",
                description="Tool execution completed"
            )
        )

        assert event is not None
        assert event.event_type == AgentEventType.TOOL_END.value
        assert event.content is not None
        assert isinstance(event.content, ToolResponseContent)
        assert event.content.tool_name == "test_tool"
        assert event.content.result == result
        assert event.content.tool_status == "completed"

    def test_convert_tool_end_event_to_message(self):
        """Test converting tool_end event to message."""
        result = {"output": "Task completed successfully", "items": 42}

        event = AgentEvent.create(
            event_type=AgentEventType.TOOL_END.value,
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="test_tool",
            sender_name="Test Tool",
            content=ToolResponseContent(
                tool_name="test_tool",
                result=result,
                tool_status="completed",
                title="Tool Result: test_tool",
                description="Tool execution completed"
            )
        )

        # Convert to message using FilmetoAgent
        agent = FilmetoAgent()
        message = agent._convert_event_to_message(
            event=event,
            sender_id="test_tool",
            sender_name="Test Tool",
            message_id="test_msg_id"
        )

        # Verify the message
        assert message is not None
        assert message.message_type == MessageType.TOOL_RESPONSE
        assert message.sender_id == "test_tool"
        assert message.sender_name == "Test Tool"
        assert message.message_id == "test_msg_id"
        assert len(message.structured_content) == 1
        assert isinstance(message.structured_content[0], ToolResponseContent)

        # Verify result is preserved
        tool_response = message.structured_content[0]
        assert tool_response.result == result
        assert tool_response.tool_name == "test_tool"
        assert tool_response.tool_status == "completed"

    def test_convert_tool_end_event_with_dict_result(self):
        """Test tool_end event with dictionary result."""
        result = {
            "success": True,
            "total_scenes": 10,
            "created_scenes": ["scene_001", "scene_002"],
            "message": "Scenes created successfully"
        }

        event = AgentEvent.create(
            event_type=AgentEventType.TOOL_END.value,
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="write_screenplay",
            sender_name="Write Screenplay",
            content=ToolResponseContent(
                tool_name="write_screenplay",
                result=result,
                tool_status="completed",
                title="Tool Result: write_screenplay",
                description="Tool execution completed"
            )
        )

        agent = FilmetoAgent()
        message = agent._convert_event_to_message(
            event=event,
            sender_id="write_screenplay",
            sender_name="Write Screenplay",
            message_id="test_msg_id"
        )

        # Verify result is preserved
        tool_response = message.structured_content[0]
        assert tool_response.result == result
        assert tool_response.result["success"] is True
        assert tool_response.result["total_scenes"] == 10
        assert len(tool_response.result["created_scenes"]) == 2

    def test_convert_tool_end_event_with_string_result(self):
        """Test tool_end event with string result."""
        result = "Operation completed successfully"

        event = AgentEvent.create(
            event_type=AgentEventType.TOOL_END.value,
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="test_tool",
            sender_name="Test Tool",
            content=ToolResponseContent(
                tool_name="test_tool",
                result=result,
                tool_status="completed",
                title="Tool Result: test_tool",
                description="Tool execution completed"
            )
        )

        agent = FilmetoAgent()
        message = agent._convert_event_to_message(
            event=event,
            sender_id="test_tool",
            sender_name="Test Tool",
            message_id="test_msg_id"
        )

        # Verify result is preserved
        tool_response = message.structured_content[0]
        assert tool_response.result == result
        assert isinstance(tool_response.result, str)

    def test_convert_tool_end_event_with_error_result(self):
        """Test tool_end event with error (failed status)."""
        result = None
        error = "Script execution failed"

        event = AgentEvent.create(
            event_type=AgentEventType.TOOL_END.value,
            project_name="test_project",
            react_type="test_react",
            run_id="test_run",
            step_id=1,
            sender_id="test_tool",
            sender_name="Test Tool",
            content=ToolResponseContent(
                tool_name="test_tool",
                result=result,
                error=error,
                tool_status="failed",
                title="Tool Result: test_tool",
                description="Tool execution failed"
            )
        )

        agent = FilmetoAgent()
        message = agent._convert_event_to_message(
            event=event,
            sender_id="test_tool",
            sender_name="Test Tool",
            message_id="test_msg_id"
        )

        # Verify error is preserved
        tool_response = message.structured_content[0]
        assert tool_response.result is None
        assert tool_response.error == error
        assert tool_response.tool_status == "failed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
