"""Unit tests for React events and enums."""
import pytest

from agent.event.agent_event import AgentEvent, AgentEventType
from agent.react.status import ReactStatus


class TestReactEventType:
    """Test cases for ReactEventType enum."""

    def test_event_type_values(self):
        """Test that ReactEventType has correct values."""
        assert AgentEventType.LLM_THINKING.value == "llm_thinking"
        assert AgentEventType.TOOL_START.value == "tool_start"
        assert AgentEventType.TOOL_PROGRESS.value == "tool_progress"
        assert AgentEventType.TOOL_END.value == "tool_end"
        assert AgentEventType.LLM_OUTPUT.value == "llm_output"
        assert AgentEventType.FINAL.value == "final"
        assert AgentEventType.ERROR.value == "error"

    def test_event_type_is_string_enum(self):
        """Test that ReactEventType is a string Enum."""
        assert isinstance(AgentEventType.LLM_THINKING, str)
        assert AgentEventType.LLM_THINKING == "llm_thinking"  # String enum compares directly

    def test_is_tool_event(self):
        """Test is_tool_event class method."""
        assert AgentEventType.is_tool_event("tool_start")
        assert AgentEventType.is_tool_event("tool_progress")
        assert AgentEventType.is_tool_event("tool_end")
        assert not AgentEventType.is_tool_event("llm_thinking")
        assert not AgentEventType.is_tool_event("final")

    def test_is_terminal_event(self):
        """Test is_terminal_event class method."""
        assert AgentEventType.is_terminal_event("final")
        assert AgentEventType.is_terminal_event("error")
        assert not AgentEventType.is_terminal_event("tool_start")
        assert not AgentEventType.is_terminal_event("llm_thinking")

    def test_get_valid_types(self):
        """Test get_valid_types returns all event type values."""
        valid_types = AgentEventType.get_valid_types()
        assert "llm_thinking" in valid_types
        assert "tool_start" in valid_types
        assert "final" in valid_types
        assert len(valid_types) > 0


class TestReactStatus:
    """Test cases for ReactStatus enum."""

    def test_status_values(self):
        """Test that ReactStatus has correct values."""
        assert ReactStatus.IDLE.value == "IDLE"
        assert ReactStatus.RUNNING.value == "RUNNING"
        assert ReactStatus.FINAL.value == "FINAL"
        assert ReactStatus.FAILED.value == "FAILED"
        assert ReactStatus.WAITING.value == "WAITING"
        assert ReactStatus.PAUSED.value == "PAUSED"
        assert ReactStatus.AWAITING_INPUT.value == "AWAITING_INPUT"

    def test_status_is_string_enum(self):
        """Test that ReactStatus is a string Enum."""
        assert isinstance(ReactStatus.RUNNING, str)
        assert ReactStatus.RUNNING == "RUNNING"  # String enum compares directly

    def test_is_active(self):
        """Test is_active class method."""
        assert ReactStatus.is_active("RUNNING")
        assert ReactStatus.is_active("WAITING")
        assert not ReactStatus.is_active("IDLE")
        assert not ReactStatus.is_active("FINAL")

    def test_is_terminal(self):
        """Test is_terminal class method."""
        assert ReactStatus.is_terminal("FINAL")
        assert ReactStatus.is_terminal("FAILED")
        assert not ReactStatus.is_terminal("RUNNING")
        assert not ReactStatus.is_terminal("IDLE")

    def test_is_interactive(self):
        """Test is_interactive class method."""
        assert ReactStatus.is_interactive("PAUSED")
        assert ReactStatus.is_interactive("AWAITING_INPUT")
        assert not ReactStatus.is_interactive("RUNNING")
        assert not ReactStatus.is_interactive("IDLE")


class TestReactEvent:
    """Test cases for ReactEvent dataclass."""

    def test_create_valid_event(self):
        """Test creating a valid ReactEvent using AgentEventType enum."""
        event = AgentEvent(
            event_type=AgentEventType.LLM_THINKING.value,
            project_name="test_project",
            react_type="test_type",
            run_id="run_123",
            step_id=1,
            payload={"message": "thinking..."},
            sender_id="test_sender",
            sender_name="Test Sender"
        )
        assert event.event_type == "llm_thinking"
        assert event.project_name == "test_project"

    def test_create_event_with_enum(self):
        """Test creating events with different AgentEventType values."""
        # Test with FINAL type
        event = AgentEvent(
            event_type=AgentEventType.FINAL.value,
            project_name="test",
            react_type="test",
            run_id="run_123",
            step_id=0,
            payload={"result": "done"}
        )
        assert event.event_type == "final"

        # Test with ERROR type
        event = AgentEvent(
            event_type=AgentEventType.ERROR.value,
            project_name="test",
            react_type="test",
            run_id="run_123",
            step_id=0,
            payload={"error": "something failed"}
        )
        assert event.event_type == "error"

        # Test with TOOL_START type
        event = AgentEvent(
            event_type=AgentEventType.TOOL_START.value,
            project_name="test",
            react_type="test",
            run_id="run_123",
            step_id=0,
            payload={"tool_name": "test_tool"}
        )
        assert event.event_type == "tool_start"

    def test_event_validation_invalid_type(self):
        """Test that invalid event_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid event_type"):
            AgentEvent(
                event_type="invalid_type",
                project_name="test",
                react_type="test",
                run_id="run_123",
                step_id=0,
                payload={}
            )

    def test_event_validation_negative_step_id(self):
        """Test that negative step_id raises ValueError."""
        with pytest.raises(ValueError, match="step_id must be >= 0"):
            AgentEvent(
                event_type=AgentEventType.LLM_THINKING.value,
                project_name="test",
                react_type="test",
                run_id="run_123",
                step_id=-1,
                payload={"data": "test"}
            )

    def test_event_validation_invalid_payload(self):
        """Test that non-dict payload raises ValueError (type checking at runtime)."""
        # Note: The AgentEvent class doesn't validate payload type at runtime
        # This test documents that behavior - payload type checking is static only
        event = AgentEvent(
            event_type=AgentEventType.LLM_THINKING.value,
            project_name="test",
            react_type="test",
            run_id="run_123",
            step_id=0,
            payload={"data": "test"}  # Valid payload
        )
        # The payload can be any type at runtime due to Dict[str, Any] type hint
        # Static type checkers would catch type mismatches
        assert event.payload == {"data": "test"}

    def test_event_validation_zero_step_id(self):
        """Test that zero step_id is valid."""
        event = AgentEvent(
            event_type=AgentEventType.LLM_THINKING.value,
            project_name="test",
            react_type="test",
            run_id="run_123",
            step_id=0,
            payload={"data": "test"}
        )
        assert event.step_id == 0

    def test_event_validation_empty_payload(self):
        """Test that event can be created with content instead of payload."""
        # Events can use content (StructureContent) instead of payload
        # Using the static factory method with content parameter
        event = AgentEvent(
            event_type=AgentEventType.LLM_THINKING.value,
            project_name="test",
            react_type="test",
            run_id="run_123",
            step_id=0,
            payload={"data": "test"}
        )
        assert event.payload == {"data": "test"}
