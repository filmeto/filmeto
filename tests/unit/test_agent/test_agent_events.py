"""
Unit tests for agent/event/agent_event.py.

Tests for:
- AgentEventType enum values and classification methods
- AgentEvent dataclass validation and factory methods
"""
import pytest
from typing import Dict, Any

from agent.event.agent_event import AgentEvent, AgentEventType


class TestAgentEventType:
    """Tests for AgentEventType enum"""

    def test_llm_event_types(self):
        """LLM event types should be defined"""
        assert AgentEventType.LLM_THINKING.value == "llm_thinking"
        assert AgentEventType.LLM_OUTPUT.value == "llm_output"

    def test_crew_member_event_types(self):
        """Crew member event types should be defined"""
        assert AgentEventType.CREW_MEMBER_TYPING.value == "crew_member_typing"
        assert AgentEventType.CREW_MEMBER_TYPING_END.value == "crew_member_typing_end"
        assert AgentEventType.CREW_MEMBER_MESSAGE.value == "crew_member_message"
        assert AgentEventType.CREW_MEMBER_PRIVATE_MESSAGE.value == "crew_member_private_message"
        assert AgentEventType.CREW_MEMBER_READ.value == "crew_member_read"

    def test_skill_event_types(self):
        """Skill event types should be defined"""
        assert AgentEventType.SKILL_START.value == "skill_start"
        assert AgentEventType.SKILL_PROGRESS.value == "skill_progress"
        assert AgentEventType.SKILL_END.value == "skill_end"
        assert AgentEventType.SKILL_ERROR.value == "skill_error"

    def test_tool_event_types(self):
        """Tool event types should be defined"""
        assert AgentEventType.TOOL_START.value == "tool_start"
        assert AgentEventType.TOOL_PROGRESS.value == "tool_progress"
        assert AgentEventType.TOOL_END.value == "tool_end"

    def test_plan_event_types(self):
        """Plan event types should be defined"""
        assert AgentEventType.PLAN_CREATED.value == "plan_created"
        assert AgentEventType.PLAN_UPDATED.value == "plan_updated"
        assert AgentEventType.PLAN_TASK_UPDATED.value == "plan_task_updated"

    def test_terminal_event_types(self):
        """Terminal event types should be defined"""
        assert AgentEventType.FINAL.value == "final"
        assert AgentEventType.ERROR.value == "error"
        assert AgentEventType.INTERRUPTED.value == "interrupted"
        assert AgentEventType.TIMEOUT.value == "timeout"

    def test_control_event_types(self):
        """Control event types should be defined"""
        assert AgentEventType.PAUSE.value == "pause"
        assert AgentEventType.RESUME.value == "resume"

    def test_todo_event_type(self):
        """TODO event type should be defined"""
        assert AgentEventType.TODO_WRITE.value == "todo_write"

    def test_is_tool_event_true_for_tool_types(self):
        """is_tool_event should return True for tool-related types"""
        assert AgentEventType.is_tool_event("tool_start") is True
        assert AgentEventType.is_tool_event("tool_progress") is True
        assert AgentEventType.is_tool_event("tool_end") is True

    def test_is_tool_event_false_for_non_tool_types(self):
        """is_tool_event should return False for non-tool types"""
        assert AgentEventType.is_tool_event("llm_output") is False
        assert AgentEventType.is_tool_event("skill_start") is False
        assert AgentEventType.is_tool_event("final") is False

    def test_is_skill_event_true_for_skill_types(self):
        """is_skill_event should return True for skill-related types"""
        assert AgentEventType.is_skill_event("skill_start") is True
        assert AgentEventType.is_skill_event("skill_progress") is True
        assert AgentEventType.is_skill_event("skill_end") is True
        assert AgentEventType.is_skill_event("skill_error") is True

    def test_is_skill_event_false_for_non_skill_types(self):
        """is_skill_event should return False for non-skill types"""
        assert AgentEventType.is_skill_event("tool_start") is False
        assert AgentEventType.is_skill_event("llm_output") is False

    def test_is_crew_member_event_true_for_crew_types(self):
        """is_crew_member_event should return True for crew member types"""
        assert AgentEventType.is_crew_member_event("crew_member_typing") is True
        assert AgentEventType.is_crew_member_event("crew_member_message") is True
        assert AgentEventType.is_crew_member_event("crew_member_private_message") is True
        assert AgentEventType.is_crew_member_event("crew_member_read") is True

    def test_is_crew_member_event_false_for_non_crew_types(self):
        """is_crew_member_event should return False for non-crew types"""
        assert AgentEventType.is_crew_member_event("tool_start") is False
        assert AgentEventType.is_crew_member_event("skill_start") is False

    def test_is_plan_event_true_for_plan_types(self):
        """is_plan_event should return True for plan-related types"""
        assert AgentEventType.is_plan_event("plan_created") is True
        assert AgentEventType.is_plan_event("plan_updated") is True
        assert AgentEventType.is_plan_event("plan_task_updated") is True

    def test_is_plan_event_false_for_non_plan_types(self):
        """is_plan_event should return False for non-plan types"""
        assert AgentEventType.is_plan_event("tool_start") is False
        assert AgentEventType.is_plan_event("final") is False

    def test_is_terminal_event_true_for_terminal_types(self):
        """is_terminal_event should return True for terminal types"""
        assert AgentEventType.is_terminal_event("final") is True
        assert AgentEventType.is_terminal_event("error") is True
        assert AgentEventType.is_terminal_event("interrupted") is True
        assert AgentEventType.is_terminal_event("timeout") is True

    def test_is_terminal_event_false_for_non_terminal_types(self):
        """is_terminal_event should return False for non-terminal types"""
        assert AgentEventType.is_terminal_event("tool_start") is False
        assert AgentEventType.is_terminal_event("skill_progress") is False

    def test_get_valid_types_returns_all_values(self):
        """get_valid_types should return all event type values"""
        valid_types = AgentEventType.get_valid_types()
        assert "llm_thinking" in valid_types
        assert "tool_start" in valid_types
        assert "final" in valid_types
        assert "error" in valid_types
        # Should contain all enum values
        assert len(valid_types) == len(list(AgentEventType))


class TestAgentEventValidation:
    """Tests for AgentEvent validation"""

    def test_agent_event_invalid_type_raises_error(self):
        """AgentEvent should raise ValueError for invalid event_type"""
        from agent.chat.content import TextContent
        with pytest.raises(ValueError) as exc_info:
            AgentEvent(
                event_type="invalid_type",
                project_name="test",
                react_type="crew",
                content=TextContent(text="test")
            )
        assert "Invalid event_type" in str(exc_info.value)

    def test_agent_event_negative_step_id_raises_error(self):
        """AgentEvent should raise ValueError for negative step_id"""
        from agent.chat.content import TextContent
        with pytest.raises(ValueError) as exc_info:
            AgentEvent(
                event_type="final",
                project_name="test",
                react_type="crew",
                step_id=-1,
                content=TextContent(text="test")
            )
        assert "step_id must be >= 0" in str(exc_info.value)

    def test_agent_event_payload_deprecation_warning(self):
        """AgentEvent should warn when payload is used"""
        from agent.chat.content import TextContent
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            AgentEvent(
                event_type="final",
                project_name="test",
                react_type="crew",
                content=TextContent(text="test"),
                payload={"old": "data"}
            )
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "payload is deprecated" in str(w[0].message)

    def test_agent_event_requires_content_or_payload(self):
        """AgentEvent should require either content or payload"""
        with pytest.raises(ValueError) as exc_info:
            AgentEvent(
                event_type="final",
                project_name="test",
                react_type="crew"
            )
        assert "must have either content or payload" in str(exc_info.value)


class TestAgentEventFactoryMethods:
    """Tests for AgentEvent factory methods"""

    def test_create_basic_event(self):
        """AgentEvent.create should create valid event"""
        from agent.chat.content import TextContent
        event = AgentEvent.create(
            event_type="final",
            project_name="test_project",
            react_type="crew",
            step_id=1,
            sender_id="agent_1",
            sender_name="Test Agent",
            content=TextContent(text="Hello")
        )
        assert event.event_type == "final"
        assert event.project_name == "test_project"
        assert event.react_type == "crew"
        assert event.step_id == 1
        assert event.sender_id == "agent_1"
        assert event.sender_name == "Test Agent"

    def test_error_factory_creates_error_event(self):
        """AgentEvent.error should create error event"""
        event = AgentEvent.error(
            error_message="Something went wrong",
            project_name="test_project",
            react_type="crew"
        )
        assert event.event_type == "error"
        assert event.project_name == "test_project"
        assert event.content is not None

    def test_final_factory_creates_final_event(self):
        """AgentEvent.final should create final event"""
        event = AgentEvent.final(
            final_response="Task completed successfully",
            project_name="test_project",
            react_type="crew"
        )
        assert event.event_type == "final"
        assert event.project_name == "test_project"
        assert event.content is not None

    def test_tool_start_factory(self):
        """AgentEvent.tool_start should create tool start event"""
        event = AgentEvent.tool_start(
            tool_name="test_tool",
            project_name="test_project",
            react_type="crew",
            step_id=1,
            tool_input={"arg": "value"}
        )
        assert event.event_type == "tool_start"
        assert event.project_name == "test_project"
        assert event.content is not None

    def test_tool_progress_factory(self):
        """AgentEvent.tool_progress should create tool progress event"""
        event = AgentEvent.tool_progress(
            tool_name="test_tool",
            progress="50% complete",
            project_name="test_project",
            react_type="crew"
        )
        assert event.event_type == "tool_progress"
        assert event.project_name == "test_project"

    def test_tool_end_factory_success(self):
        """AgentEvent.tool_end should create tool end event for success"""
        event = AgentEvent.tool_end(
            tool_name="test_tool",
            result={"output": "success"},
            ok=True,
            project_name="test_project",
            react_type="crew"
        )
        assert event.event_type == "tool_end"
        assert event.project_name == "test_project"

    def test_tool_end_factory_failure(self):
        """AgentEvent.tool_end should create tool end event for failure"""
        event = AgentEvent.tool_end(
            tool_name="test_tool",
            result=None,
            ok=False,
            project_name="test_project",
            react_type="crew"
        )
        assert event.event_type == "tool_end"
        assert event.project_name == "test_project"


class TestAgentEventInitExports:
    """Tests for agent/event/__init__.py exports"""

    def test_agent_event_exported(self):
        """AgentEvent should be exported from event package"""
        from agent.event import AgentEvent
        assert AgentEvent is not None

    def test_agent_event_type_exported(self):
        """AgentEventType should be exported from event package"""
        from agent.event import AgentEventType
        assert AgentEventType is not None