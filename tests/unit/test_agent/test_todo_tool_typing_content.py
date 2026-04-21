"""
Unit tests for TodoWrite, ToolCall/ToolResponse, and Typing content types.

Tests for:
- agent/chat/content/todo_write_content.py
- agent/chat/content/tool_content.py
- agent/chat/content/typing_content.py
"""
import pytest
from unittest.mock import Mock

from agent.chat.agent_chat_types import ContentType
from agent.chat.content.content_status import ContentStatus
from agent.chat.content.todo_write_content import TodoWriteContent
from agent.chat.content.tool_content import ToolCallContent, ToolResponseContent
from agent.chat.content.typing_content import TypingContent, TypingState


class TestTodoWriteContent:
    """Tests for TodoWriteContent"""

    def test_todo_write_defaults(self):
        """Verify default values"""
        todo = TodoWriteContent()
        assert todo.content_type == ContentType.TODO_WRITE
        assert todo.todos == []
        assert todo.total == 0
        assert todo.pending == 0
        assert todo.in_progress == 0
        assert todo.completed == 0
        assert todo.failed == 0
        assert todo.blocked == 0
        assert todo.version == 0

    def test_todo_write_with_todos(self):
        """Verify TodoWriteContent with todos"""
        todos = [
            {"id": "1", "content": "Task 1", "status": "pending"},
            {"id": "2", "content": "Task 2", "status": "in_progress"},
            {"id": "3", "content": "Task 3", "status": "completed"},
        ]
        todo = TodoWriteContent(
            todos=todos,
            total=3,
            pending=1,
            in_progress=1,
            completed=1,
            version=1
        )
        assert len(todo.todos) == 3
        assert todo.total == 3
        assert todo.version == 1

    def test_todo_write_to_dict(self):
        """Verify to_dict serialization"""
        todos = [{"id": "1", "content": "Task", "status": "pending"}]
        todo = TodoWriteContent(
            todos=todos,
            total=1,
            pending=1,
            version=1
        )
        result = todo.to_dict()
        assert result["data"]["todos"] == todos
        assert result["data"]["total"] == 1
        assert result["data"]["pending"] == 1
        assert result["data"]["version"] == 1

    def test_todo_write_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "todo_write",
            "title": "My Tasks",
            "description": "Task list",
            "content_id": "todo-1",
            "status": "completed",
            "data": {
                "todos": [{"id": "1", "content": "Task 1", "status": "completed"}],
                "total": 1,
                "pending": 0,
                "in_progress": 0,
                "completed": 1,
                "failed": 0,
                "blocked": 0,
                "version": 2
            }
        }
        todo = TodoWriteContent.from_dict(data)
        assert todo.title == "My Tasks"
        assert todo.description == "Task list"
        assert len(todo.todos) == 1
        assert todo.total == 1
        assert todo.completed == 1
        assert todo.version == 2
        assert todo.status == ContentStatus.COMPLETED

    def test_todo_write_from_dict_missing_data(self):
        """Verify from_dict handles missing data field"""
        data = {
            "content_type": "todo_write",
            "status": "creating"
        }
        todo = TodoWriteContent.from_dict(data)
        assert todo.todos == []
        assert todo.total == 0

    def test_todo_write_update_todos(self):
        """Verify update_todos recalculates statistics"""
        todo = TodoWriteContent()
        todos = [
            {"id": "1", "status": "pending"},
            {"id": "2", "status": "in_progress"},
            {"id": "3", "status": "completed"},
            {"id": "4", "status": "failed"},
            {"id": "5", "status": "blocked"},
        ]
        todo.update_todos(todos, version=3)
        assert todo.total == 5
        assert todo.pending == 1
        assert todo.in_progress == 1
        assert todo.completed == 1
        assert todo.failed == 1
        assert todo.blocked == 1
        assert todo.version == 3
        assert todo.status == ContentStatus.UPDATING

    def test_todo_write_from_todo_state(self):
        """Verify from_todo_state factory method"""
        # Create mock TodoState
        mock_state = Mock()
        mock_state.items = [
            Mock(to_dict=lambda: {"id": "1", "content": "Task", "status": "pending"}),
            Mock(to_dict=lambda: {"id": "2", "content": "Task2", "status": "completed"}),
        ]
        mock_state.version = 5
        mock_state.get_summary.return_value = {
            "total": 2,
            "pending": 1,
            "in_progress": 0,
            "completed": 1,
            "failed": 0,
            "blocked": 0
        }

        todo = TodoWriteContent.from_todo_state(mock_state)
        assert todo.total == 2
        assert todo.pending == 1
        assert todo.completed == 1
        assert todo.version == 5


class TestToolCallContent:
    """Tests for ToolCallContent"""

    def test_tool_call_defaults(self):
        """Verify default values"""
        tool = ToolCallContent()
        assert tool.content_type == ContentType.TOOL_CALL
        assert tool.tool_name == ""
        assert tool.tool_input == {}
        assert tool.tool_status == "started"
        assert tool.result is None
        assert tool.error is None
        assert tool.tool_call_id == ""

    def test_tool_call_with_values(self):
        """Verify ToolCallContent with values"""
        tool = ToolCallContent(
            tool_name="execute_code",
            tool_input={"code": "print('hello')"},
            tool_status="started",
            tool_call_id="call-123"
        )
        assert tool.tool_name == "execute_code"
        assert tool.tool_input["code"] == "print('hello')"
        assert tool.tool_call_id == "call-123"

    def test_tool_call_set_result_success(self):
        """Verify set_result for successful execution"""
        tool = ToolCallContent(tool_name="test_tool")
        tool.set_result({"output": "success"})
        assert tool.result == {"output": "success"}
        assert tool.error is None
        assert tool.tool_status == "completed"

    def test_tool_call_set_result_with_error(self):
        """Verify set_result for failed execution"""
        tool = ToolCallContent(tool_name="test_tool")
        tool.set_result(None, error="Execution failed")
        assert tool.result is None
        assert tool.error == "Execution failed"
        assert tool.tool_status == "failed"

    def test_tool_call_to_dict(self):
        """Verify to_dict serialization"""
        tool = ToolCallContent(
            tool_name="search",
            tool_input={"query": "test"},
            tool_status="completed",
            tool_call_id="call-1",
            result={"found": True}
        )
        result = tool.to_dict()
        assert result["data"]["tool_name"] == "search"
        assert result["data"]["tool_input"] == {"query": "test"}
        assert result["data"]["status"] == "completed"
        assert result["data"]["tool_call_id"] == "call-1"
        assert result["data"]["result"] == {"found": True}

    def test_tool_call_to_dict_without_optional_fields(self):
        """Verify to_dict omits optional fields when None"""
        tool = ToolCallContent(tool_name="test")
        result = tool.to_dict()
        assert "tool_call_id" not in result["data"]
        assert "result" not in result["data"]
        assert "error" not in result["data"]

    def test_tool_call_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "tool_call",
            "title": "Tool Execution",
            "content_id": "tool-1",
            "status": "completed",
            "data": {
                "tool_name": "read_file",
                "tool_input": {"path": "/tmp/file"},
                "status": "completed",
                "result": "file contents",
                "tool_call_id": "call-abc"
            }
        }
        tool = ToolCallContent.from_dict(data)
        assert tool.title == "Tool Execution"
        assert tool.tool_name == "read_file"
        assert tool.tool_input == {"path": "/tmp/file"}
        assert tool.tool_status == "completed"
        assert tool.result == "file contents"
        assert tool.tool_call_id == "call-abc"

    def test_tool_call_from_dict_with_error(self):
        """Verify from_dict with error"""
        data = {
            "content_type": "tool_call",
            "status": "creating",
            "data": {
                "tool_name": "test",
                "status": "failed",
                "error": "Something went wrong"
            }
        }
        tool = ToolCallContent.from_dict(data)
        assert tool.tool_status == "failed"
        assert tool.error == "Something went wrong"


class TestToolResponseContent:
    """Tests for ToolResponseContent"""

    def test_tool_response_defaults(self):
        """Verify default values"""
        response = ToolResponseContent()
        assert response.content_type == ContentType.TOOL_RESPONSE
        assert response.tool_name == ""
        assert response.result is None
        assert response.error is None
        assert response.tool_status == "completed"

    def test_tool_response_with_result(self):
        """Verify ToolResponseContent with result"""
        response = ToolResponseContent(
            tool_name="execute",
            result="success output",
            tool_status="completed"
        )
        assert response.tool_name == "execute"
        assert response.result == "success output"

    def test_tool_response_with_error(self):
        """Verify ToolResponseContent with error"""
        response = ToolResponseContent(
            tool_name="failing_tool",
            error="Tool failed",
            tool_status="failed"
        )
        assert response.error == "Tool failed"
        assert response.tool_status == "failed"

    def test_tool_response_to_dict(self):
        """Verify to_dict serialization"""
        response = ToolResponseContent(
            tool_name="api_call",
            result={"data": [1, 2, 3]},
            tool_status="completed"
        )
        result = response.to_dict()
        assert result["data"]["tool_name"] == "api_call"
        assert result["data"]["status"] == "completed"
        assert result["data"]["result"] == {"data": [1, 2, 3]}

    def test_tool_response_to_dict_with_error(self):
        """Verify to_dict with error"""
        response = ToolResponseContent(
            tool_name="test",
            error="error message",
            tool_status="failed"
        )
        result = response.to_dict()
        assert result["data"]["error"] == "error message"
        assert "result" not in result["data"]

    def test_tool_response_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "tool_response",
            "title": "Response",
            "status": "completed",
            "data": {
                "tool_name": "search",
                "result": ["item1", "item2"],
                "status": "completed"
            }
        }
        response = ToolResponseContent.from_dict(data)
        assert response.title == "Response"
        assert response.tool_name == "search"
        assert response.result == ["item1", "item2"]
        assert response.tool_status == "completed"

    def test_tool_response_from_dict_with_error(self):
        """Verify from_dict with error"""
        data = {
            "content_type": "tool_response",
            "status": "creating",
            "data": {
                "tool_name": "fail",
                "error": "timeout",
                "status": "failed"
            }
        }
        response = ToolResponseContent.from_dict(data)
        assert response.tool_status == "failed"
        assert response.error == "timeout"


class TestTypingContent:
    """Tests for TypingContent"""

    def test_typing_defaults(self):
        """Verify default values"""
        typing = TypingContent()
        assert typing.content_type == ContentType.TYPING
        assert typing.state == TypingState.START

    def test_typing_state_enum(self):
        """Verify TypingState enum values"""
        assert TypingState.START.value == "start"
        assert TypingState.END.value == "end"

    def test_typing_with_end_state(self):
        """Verify TypingContent with END state"""
        typing = TypingContent(state=TypingState.END)
        assert typing.state == TypingState.END

    def test_typing_to_dict(self):
        """Verify to_dict serialization"""
        typing = TypingContent(state=TypingState.START)
        result = typing.to_dict()
        assert result["data"]["state"] == "start"

    def test_typing_to_dict_end_state(self):
        """Verify to_dict with END state"""
        typing = TypingContent(state=TypingState.END)
        result = typing.to_dict()
        assert result["data"]["state"] == "end"

    def test_typing_from_dict(self):
        """Verify from_dict deserialization"""
        data = {
            "content_type": "typing",
            "status": "creating",
            "data": {
                "state": "end"
            }
        }
        typing = TypingContent.from_dict(data)
        assert typing.state == TypingState.END

    def test_typing_from_dict_start_state(self):
        """Verify from_dict with START state"""
        data = {
            "content_type": "typing",
            "status": "creating",
            "data": {
                "state": "start"
            }
        }
        typing = TypingContent.from_dict(data)
        assert typing.state == TypingState.START

    def test_typing_from_dict_runtime_format(self):
        """Verify from_dict with state at data level (storage format)"""
        data = {
            "content_type": "typing",
            "status": "creating",
            "data": {
                "state": "end"
            }
        }
        typing = TypingContent.from_dict(data)
        assert typing.state == TypingState.END

    def test_typing_from_dict_invalid_state(self):
        """Verify from_dict handles invalid state"""
        data = {
            "content_type": "typing",
            "status": "creating",
            "data": {
                "state": "invalid_state"
            }
        }
        typing = TypingContent.from_dict(data)
        assert typing.state == TypingState.START  # Falls back to default

    def test_typing_from_dict_missing_state(self):
        """Verify from_dict handles missing state"""
        data = {
            "content_type": "typing",
            "status": "creating",
            "data": {}
        }
        typing = TypingContent.from_dict(data)
        assert typing.state == TypingState.START

    def test_typing_from_dict_with_title(self):
        """Verify from_dict preserves title"""
        data = {
            "content_type": "typing",
            "title": "Agent Typing",
            "description": "Agent is processing",
            "status": "completed",
            "data": {"state": "start"}
        }
        typing = TypingContent.from_dict(data)
        assert typing.title == "Agent Typing"
        assert typing.description == "Agent is processing"