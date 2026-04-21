"""
Unit tests for agent/react/ status, todo, and types modules.

Tests for:
- agent/react/status.py - ReactStatus enum methods
- agent/react/todo.py - TodoStatus, TodoItem, TodoState dataclasses
- agent/react/types.py - Module exports
"""
import pytest
from datetime import datetime

from agent.react.status import ReactStatus
from agent.react.todo import TodoStatus, TodoItem, TodoState


class TestReactStatus:
    """Tests for ReactStatus enum"""

    def test_status_values(self):
        """ReactStatus should have correct string values"""
        assert ReactStatus.IDLE.value == "IDLE"
        assert ReactStatus.RUNNING.value == "RUNNING"
        assert ReactStatus.FINAL.value == "FINAL"
        assert ReactStatus.FAILED.value == "FAILED"
        assert ReactStatus.WAITING.value == "WAITING"
        assert ReactStatus.PAUSED.value == "PAUSED"
        assert ReactStatus.AWAITING_INPUT.value == "AWAITING_INPUT"

    def test_is_active_returns_true_for_running_and_waiting(self):
        """is_active should return True for RUNNING and WAITING"""
        assert ReactStatus.is_active("RUNNING") is True
        assert ReactStatus.is_active("WAITING") is True

    def test_is_active_returns_false_for_other_statuses(self):
        """is_active should return False for non-active statuses"""
        assert ReactStatus.is_active("IDLE") is False
        assert ReactStatus.is_active("FINAL") is False
        assert ReactStatus.is_active("FAILED") is False
        assert ReactStatus.is_active("PAUSED") is False

    def test_is_terminal_returns_true_for_final_and_failed(self):
        """is_terminal should return True for FINAL and FAILED"""
        assert ReactStatus.is_terminal("FINAL") is True
        assert ReactStatus.is_terminal("FAILED") is True

    def test_is_terminal_returns_false_for_other_statuses(self):
        """is_terminal should return False for non-terminal statuses"""
        assert ReactStatus.is_terminal("IDLE") is False
        assert ReactStatus.is_terminal("RUNNING") is False
        assert ReactStatus.is_terminal("WAITING") is False

    def test_is_interactive_returns_true_for_paused_states(self):
        """is_interactive should return True for PAUSED and AWAITING_INPUT"""
        assert ReactStatus.is_interactive("PAUSED") is True
        assert ReactStatus.is_interactive("AWAITING_INPUT") is True

    def test_is_interactive_returns_false_for_other_statuses(self):
        """is_interactive should return False for non-interactive statuses"""
        assert ReactStatus.is_interactive("IDLE") is False
        assert ReactStatus.is_interactive("RUNNING") is False
        assert ReactStatus.is_interactive("FINAL") is False

    def test_status_enum_count(self):
        """ReactStatus should have 7 status values"""
        assert len(list(ReactStatus)) == 7


class TestTodoStatus:
    """Tests for TodoStatus enum"""

    def test_status_values(self):
        """TodoStatus should have correct string values"""
        assert TodoStatus.PENDING.value == "pending"
        assert TodoStatus.IN_PROGRESS.value == "in_progress"
        assert TodoStatus.COMPLETED.value == "completed"
        assert TodoStatus.FAILED.value == "failed"
        assert TodoStatus.BLOCKED.value == "blocked"

    def test_status_enum_count(self):
        """TodoStatus should have 5 status values"""
        assert len(list(TodoStatus)) == 5


class TestTodoItem:
    """Tests for TodoItem dataclass"""

    def test_todo_item_creation_basic(self):
        """TodoItem should be created with basic fields"""
        item = TodoItem(id="todo_1", title="Test Task")
        assert item.id == "todo_1"
        assert item.title == "Test Task"
        assert item.status == TodoStatus.PENDING
        assert item.priority == 3

    def test_todo_item_creation_with_all_fields(self):
        """TodoItem should accept all optional fields"""
        item = TodoItem(
            id="todo_2",
            title="Full Task",
            description="A detailed task",
            status=TodoStatus.IN_PROGRESS,
            priority=5,
            dependencies=["todo_1"],
            metadata={"custom": "data"}
        )
        assert item.id == "todo_2"
        assert item.title == "Full Task"
        assert item.description == "A detailed task"
        assert item.status == TodoStatus.IN_PROGRESS
        assert item.priority == 5
        assert item.dependencies == ["todo_1"]
        assert item.metadata == {"custom": "data"}

    def test_todo_item_timestamps_auto_generated(self):
        """TodoItem should auto-generate timestamps"""
        before = datetime.now().timestamp()
        item = TodoItem(id="todo_3", title="Task")
        after = datetime.now().timestamp()
        assert before <= item.created_at <= after
        assert before <= item.updated_at <= after

    def test_todo_item_completed_at_none_by_default(self):
        """TodoItem completed_at should be None by default"""
        item = TodoItem(id="todo_4", title="Task")
        assert item.completed_at is None

    def test_todo_item_to_dict(self):
        """TodoItem.to_dict should return proper dictionary"""
        item = TodoItem(
            id="todo_5",
            title="Test",
            status=TodoStatus.COMPLETED,
            priority=4
        )
        data = item.to_dict()
        assert data["id"] == "todo_5"
        assert data["title"] == "Test"
        assert data["status"] == "completed"
        assert data["priority"] == 4

    def test_todo_item_from_dict(self):
        """TodoItem.from_dict should create item from dictionary"""
        data = {
            "id": "todo_6",
            "title": "Restored Task",
            "status": "in_progress",
            "priority": 2
        }
        item = TodoItem.from_dict(data)
        assert item.id == "todo_6"
        assert item.title == "Restored Task"
        assert item.status == TodoStatus.IN_PROGRESS
        assert item.priority == 2

    def test_todo_item_from_dict_with_optional_fields(self):
        """TodoItem.from_dict should handle optional fields"""
        data = {
            "id": "todo_7",
            "title": "Optional Task",
            "description": "With description",
            "dependencies": ["todo_1", "todo_2"],
            "metadata": {"key": "value"}
        }
        item = TodoItem.from_dict(data)
        assert item.description == "With description"
        assert item.dependencies == ["todo_1", "todo_2"]
        assert item.metadata == {"key": "value"}

    def test_todo_item_roundtrip(self):
        """TodoItem should survive to_dict -> from_dict roundtrip"""
        original = TodoItem(
            id="todo_8",
            title="Roundtrip",
            description="Test roundtrip",
            status=TodoStatus.IN_PROGRESS,
            priority=3,
            dependencies=["dep_1"],
            metadata={"meta": "data"}
        )
        data = original.to_dict()
        restored = TodoItem.from_dict(data)
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.priority == original.priority
        assert restored.dependencies == original.dependencies
        assert restored.metadata == original.metadata


class TestTodoState:
    """Tests for TodoState dataclass"""

    def test_todo_state_creation_empty(self):
        """TodoState should be created with empty items"""
        state = TodoState()
        assert state.items == []
        assert state.version == 0

    def test_todo_state_creation_with_items(self):
        """TodoState should accept items list"""
        items = [
            TodoItem(id="todo_1", title="Task 1"),
            TodoItem(id="todo_2", title="Task 2")
        ]
        state = TodoState(items=items)
        assert len(state.items) == 2
        assert state.items[0].id == "todo_1"

    def test_todo_state_timestamps_auto_generated(self):
        """TodoState should auto-generate timestamps"""
        before = datetime.now().timestamp()
        state = TodoState()
        after = datetime.now().timestamp()
        assert before <= state.created_at <= after
        assert before <= state.updated_at <= after

    def test_todo_state_to_dict(self):
        """TodoState.to_dict should return proper dictionary"""
        items = [TodoItem(id="todo_1", title="Task")]
        state = TodoState(items=items, version=5)
        data = state.to_dict()
        assert data["version"] == 5
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "todo_1"

    def test_todo_state_from_dict(self):
        """TodoState.from_dict should create state from dictionary"""
        data = {
            "items": [
                {"id": "todo_1", "title": "Task 1"},
                {"id": "todo_2", "title": "Task 2", "status": "completed"}
            ],
            "version": 3
        }
        state = TodoState.from_dict(data)
        assert state.version == 3
        assert len(state.items) == 2
        assert state.items[1].status == TodoStatus.COMPLETED

    def test_todo_state_get_item_by_id(self):
        """TodoState.get_item_by_id should find item"""
        items = [
            TodoItem(id="todo_1", title="Task 1"),
            TodoItem(id="todo_2", title="Task 2")
        ]
        state = TodoState(items=items)
        found = state.get_item_by_id("todo_2")
        assert found is not None
        assert found.title == "Task 2"

    def test_todo_state_get_item_by_id_not_found(self):
        """TodoState.get_item_by_id should return None if not found"""
        state = TodoState(items=[TodoItem(id="todo_1", title="Task")])
        found = state.get_item_by_id("nonexistent")
        assert found is None

    def test_todo_state_get_pending_items(self):
        """TodoState.get_pending_items should return pending items"""
        items = [
            TodoItem(id="todo_1", title="Pending", status=TodoStatus.PENDING),
            TodoItem(id="todo_2", title="Completed", status=TodoStatus.COMPLETED),
            TodoItem(id="todo_3", title="InProgress", status=TodoStatus.IN_PROGRESS)
        ]
        state = TodoState(items=items)
        pending = state.get_pending_items()
        assert len(pending) == 1
        assert pending[0].id == "todo_1"

    def test_todo_state_get_in_progress_items(self):
        """TodoState.get_in_progress_items should return in_progress items"""
        items = [
            TodoItem(id="todo_1", title="Pending", status=TodoStatus.PENDING),
            TodoItem(id="todo_2", title="InProgress", status=TodoStatus.IN_PROGRESS)
        ]
        state = TodoState(items=items)
        in_progress = state.get_in_progress_items()
        assert len(in_progress) == 1
        assert in_progress[0].id == "todo_2"

    def test_todo_state_get_completed_items(self):
        """TodoState.get_completed_items should return completed items"""
        items = [
            TodoItem(id="todo_1", title="Completed", status=TodoStatus.COMPLETED),
            TodoItem(id="todo_2", title="Failed", status=TodoStatus.FAILED)
        ]
        state = TodoState(items=items)
        completed = state.get_completed_items()
        assert len(completed) == 1
        assert completed[0].id == "todo_1"

    def test_todo_state_is_completed_true_when_all_completed(self):
        """TodoState.is_completed should return True when all completed"""
        items = [
            TodoItem(id="todo_1", title="Task 1", status=TodoStatus.COMPLETED),
            TodoItem(id="todo_2", title="Task 2", status=TodoStatus.COMPLETED)
        ]
        state = TodoState(items=items)
        assert state.is_completed() is True

    def test_todo_state_is_completed_true_when_empty(self):
        """TodoState.is_completed should return True when empty"""
        state = TodoState()
        assert state.is_completed() is True

    def test_todo_state_is_completed_false_when_pending(self):
        """TodoState.is_completed should return False when pending exists"""
        items = [
            TodoItem(id="todo_1", title="Completed", status=TodoStatus.COMPLETED),
            TodoItem(id="todo_2", title="Pending", status=TodoStatus.PENDING)
        ]
        state = TodoState(items=items)
        assert state.is_completed() is False

    def test_todo_state_get_summary(self):
        """TodoState.get_summary should return counts"""
        items = [
            TodoItem(id="todo_1", title="Pending", status=TodoStatus.PENDING),
            TodoItem(id="todo_2", title="InProgress", status=TodoStatus.IN_PROGRESS),
            TodoItem(id="todo_3", title="Completed", status=TodoStatus.COMPLETED),
            TodoItem(id="todo_4", title="Failed", status=TodoStatus.FAILED),
            TodoItem(id="todo_5", title="Blocked", status=TodoStatus.BLOCKED)
        ]
        state = TodoState(items=items, version=10)
        summary = state.get_summary()
        assert summary["total"] == 5
        assert summary["pending"] == 1
        assert summary["in_progress"] == 1
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["blocked"] == 1
        assert summary["version"] == 10


class TestReactTypesExports:
    """Tests for agent/react/types.py exports"""

    def test_agent_event_type_exported(self):
        """AgentEventType should be exported from react/types"""
        from agent.react.types import AgentEventType
        assert AgentEventType is not None

    def test_agent_event_exported(self):
        """AgentEvent should be exported from react/types"""
        from agent.react.types import AgentEvent
        assert AgentEvent is not None

    def test_react_status_exported(self):
        """ReactStatus should be exported from react/types"""
        from agent.react.types import ReactStatus
        assert ReactStatus is not None

    def test_todo_item_exported(self):
        """TodoItem should be exported from react/types"""
        from agent.react.types import TodoItem
        assert TodoItem is not None

    def test_todo_status_exported(self):
        """TodoStatus should be exported from react/types"""
        from agent.react.types import TodoStatus
        assert TodoStatus is not None

    def test_todo_state_exported(self):
        """TodoState should be exported from react/types"""
        from agent.react.types import TodoState
        assert TodoState is not None

    def test_action_types_exported(self):
        """Action types should be exported from react/types"""
        from agent.react.types import ActionType, ReactAction, ToolAction, FinalAction, ErrorAction
        assert ActionType is not None
        assert ReactAction is not None
        assert ToolAction is not None
        assert FinalAction is not None
        assert ErrorAction is not None

    def test_react_action_parser_exported(self):
        """ReactActionParser should be exported from react/types"""
        from agent.react.types import ReactActionParser
        assert ReactActionParser is not None


class TestReactInitExports:
    """Tests for agent/react/__init__.py exports"""

    def test_react_status_exported_from_react(self):
        """ReactStatus should be exported from react package"""
        from agent.react import ReactStatus
        assert ReactStatus is not None

    def test_todo_item_exported_from_react(self):
        """TodoItem should be exported from react package"""
        from agent.react import TodoItem
        assert TodoItem is not None

    def test_todo_status_exported_from_react(self):
        """TodoStatus should be exported from react package"""
        from agent.react import TodoStatus
        assert TodoStatus is not None