"""
Unit tests for agent module files marked as AST-only in test_plan.md.

Tests for:
- agent/core/filmeto_crew.py - FilmetoCrewManager
- agent/core/filmeto_plan.py - FilmetoPlanManager
- agent/prompt/__init__.py - Module exports
- agent/react/react.py - React class
- agent/react/react_service.py - ReactService singleton
- agent/router/__init__.py - Module exports
- agent/skill/__init__.py - Module exports
- agent/skill/skill_chat.py - SkillChat class
- agent/skill/skill_models.py - Skill dataclass
- agent/skill/system/delete_scene/scripts/delete_single_scene.py - Scene deletion
"""
import pytest
import json
import re
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock, patch, AsyncMock


# =============================================================================
# Tests for agent/core/filmeto_crew.py - FilmetoCrewManager
# =============================================================================

class TestFilmetoCrewManagerInit:
    """Tests for FilmetoCrewManager initialization"""

    def test_filmeto_crew_manager_creation(self):
        """FilmetoCrewManager should be created with empty crew_members"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        assert manager.crew_members == {}
        assert manager._crew_member_lookup == {}
        assert manager._crew_member_service is None

    def test_filmeto_crew_manager_with_service(self):
        """FilmetoCrewManager should accept crew_member_service"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        mock_service = MagicMock()
        manager = FilmetoCrewManager(crew_member_service=mock_service)
        assert manager._crew_member_service == mock_service

    def test_filmeto_crew_manager_set_service(self):
        """FilmetoCrewManager.set_service should update service"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        mock_service = MagicMock()
        manager.set_service(mock_service)
        assert manager._crew_member_service == mock_service


class TestFilmetoCrewManagerLoadCrewMembers:
    """Tests for FilmetoCrewManager.load_crew_members"""

    def test_load_crew_members_no_project(self):
        """load_crew_members should return empty dict when no project"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        result = manager.load_crew_members(None)
        assert result == {}
        assert manager.crew_members == {}

    def test_load_crew_members_no_service(self):
        """load_crew_members should return empty dict when no service"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        mock_project = MagicMock()
        result = manager.load_crew_members(mock_project)
        assert result == {}

    def test_load_crew_members_with_service(self):
        """load_crew_members should call service and build lookup"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        mock_service = MagicMock()
        mock_member = MagicMock()
        mock_member.config.name = "test_member"
        mock_member.config.metadata = {"crew_title": "director"}
        mock_service.load_project_crew_members.return_value = {"test_member": mock_member}

        manager.set_service(mock_service)
        mock_project = MagicMock()
        result = manager.load_crew_members(mock_project)

        assert result == {"test_member": mock_member}
        assert "test_member" in manager._crew_member_lookup


class TestFilmetoCrewManagerLookup:
    """Tests for FilmetoCrewManager lookup methods"""

    def test_get_member_existing(self):
        """get_member should return existing member"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        mock_member = MagicMock()
        mock_member.config.name = "existing_member"
        manager.crew_members["existing_member"] = mock_member

        result = manager.get_member("existing_member")
        assert result == mock_member

    def test_get_member_non_existing(self):
        """get_member should return None for non-existing member"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        result = manager.get_member("non_existing")
        assert result is None

    def test_lookup_member_by_name(self):
        """lookup_member should find member by name"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        mock_member = MagicMock()
        mock_member.config.name = "director"
        manager._crew_member_lookup["director"] = mock_member

        result = manager.lookup_member("director")
        assert result == mock_member

    def test_lookup_member_case_insensitive(self):
        """lookup_member should be case-insensitive"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        mock_member = MagicMock()
        manager._crew_member_lookup["Director"] = mock_member

        result = manager.lookup_member("director")
        assert result == mock_member

    def test_lookup_member_non_existing(self):
        """lookup_member should return None for non-existing"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        result = manager.lookup_member("unknown")
        assert result is None


class TestFilmetoCrewManagerMentions:
    """Tests for FilmetoCrewManager mention extraction"""

    def test_extract_mentions_empty_content(self):
        """extract_mentions should return empty list for empty content"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        result = manager.extract_mentions("")
        assert result == []

    def test_extract_mentions_none_content(self):
        """extract_mentions should return empty list for None content"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        result = manager.extract_mentions(None)
        assert result == []

    def test_extract_mentions_single(self):
        """extract_mentions should extract single @mention"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        result = manager.extract_mentions("@director hello")
        assert result == ["director"]

    def test_extract_mentions_multiple(self):
        """extract_mentions should extract multiple @mentions"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        result = manager.extract_mentions("@director and @producer please respond")
        assert "director" in result
        assert "producer" in result

    def test_find_member_name_case_insensitive(self):
        """find_member_name should find actual name case-insensitively"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        mock_member = MagicMock()
        mock_member.config.name = "Director"
        manager.crew_members["Director"] = mock_member

        result = manager.find_member_name("director")
        assert result == "Director"

    def test_find_member_name_non_existing(self):
        """find_member_name should return None for non-existing"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        result = manager.find_member_name("unknown")
        assert result is None


class TestFilmetoCrewManagerRegister:
    """Tests for FilmetoCrewManager.register_crew_member"""

    def test_register_crew_member(self):
        """register_crew_member should add member and rebuild lookup"""
        from agent.core.filmeto_crew import FilmetoCrewManager
        manager = FilmetoCrewManager()
        mock_member = MagicMock()
        mock_member.config.name = "new_member"
        mock_member.config.metadata = {}

        manager.register_crew_member(mock_member)
        assert "new_member" in manager.crew_members
        assert "new_member" in manager._crew_member_lookup


# =============================================================================
# Tests for agent/core/filmeto_plan.py - FilmetoPlanManager
# =============================================================================

class TestFilmetoPlanManagerInit:
    """Tests for FilmetoPlanManager initialization"""

    def test_filmeto_plan_manager_creation(self):
        """FilmetoPlanManager should be created with dependencies"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        mock_plan_service = MagicMock()
        mock_signals = MagicMock()
        mock_routing_manager = MagicMock()

        manager = FilmetoPlanManager(
            plan_service=mock_plan_service,
            signals=mock_signals,
            routing_manager=mock_routing_manager,
            resolve_project_name=lambda: "test_project"
        )

        assert manager._plan_service == mock_plan_service
        assert manager._signals == mock_signals
        assert manager._routing_manager == mock_routing_manager


class TestFilmetoPlanManagerPlanCreation:
    """Tests for FilmetoPlanManager.create_plan"""

    def test_create_plan_no_project(self):
        """create_plan should return None when no project_name"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        manager = FilmetoPlanManager(
            plan_service=MagicMock(),
            signals=MagicMock(),
            routing_manager=MagicMock(),
            resolve_project_name=lambda: None
        )
        result = manager.create_plan(None, "test message")
        assert result is None

    def test_create_plan_success(self):
        """create_plan should call plan_service.create_plan"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        mock_plan_service = MagicMock()
        mock_plan = MagicMock()
        mock_plan_service.create_plan.return_value = mock_plan

        manager = FilmetoPlanManager(
            plan_service=mock_plan_service,
            signals=MagicMock(),
            routing_manager=MagicMock(),
            resolve_project_name=lambda: "test_project"
        )
        result = manager.create_plan("test_project", "user request")

        assert result == mock_plan
        mock_plan_service.create_plan.assert_called_once()


class TestFilmetoPlanManagerMessageBuilding:
    """Tests for FilmetoPlanManager message building methods"""

    def test_build_producer_message(self):
        """build_producer_message should format message correctly"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        manager = FilmetoPlanManager(
            plan_service=MagicMock(),
            signals=MagicMock(),
            routing_manager=MagicMock(),
            resolve_project_name=lambda: "test"
        )
        result = manager.build_producer_message("user message", "plan_123", retry=False)
        assert "user message" in result
        assert "plan_123" in result

    def test_build_task_message(self):
        """build_task_message should format task correctly"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        from agent.plan.plan_models import PlanTask, TaskStatus

        manager = FilmetoPlanManager(
            plan_service=MagicMock(),
            signals=MagicMock(),
            routing_manager=MagicMock(),
            resolve_project_name=lambda: "test"
        )

        task = PlanTask(
            id="task_1",
            name="Test Task",
            description="Task description",
            title="Director",
            status=TaskStatus.CREATED,
            needs=["task_0"]
        )
        result = manager.build_task_message(task, "plan_123")

        assert "task_1" in result
        assert "Test Task" in result
        assert "plan_123" in result


class TestFilmetoPlanManagerDependencyCheck:
    """Tests for FilmetoPlanManager dependency checking"""

    def test_dependencies_satisfied_no_needs(self):
        """dependencies_satisfied should return True when no needs"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        from agent.plan.plan_models import PlanTask, TaskStatus, PlanInstance

        manager = FilmetoPlanManager(
            plan_service=MagicMock(),
            signals=MagicMock(),
            routing_manager=MagicMock(),
            resolve_project_name=lambda: "test"
        )

        task = PlanTask(
            id="task_1",
            name="Test",
            description="desc",
            title="Director",
            status=TaskStatus.CREATED,
            needs=None
        )
        plan_instance = MagicMock()
        plan_instance.tasks = [task]

        result = manager.dependencies_satisfied(plan_instance, task)
        assert result is True

    def test_check_response_error_empty(self):
        """check_response_error should return False for empty response"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        manager = FilmetoPlanManager(
            plan_service=MagicMock(),
            signals=MagicMock(),
            routing_manager=MagicMock(),
            resolve_project_name=lambda: "test"
        )
        assert manager.check_response_error(None) is False
        assert manager.check_response_error("") is False

    def test_check_response_error_llm_service_not_configured(self):
        """check_response_error should detect LLM service error"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        manager = FilmetoPlanManager(
            plan_service=MagicMock(),
            signals=MagicMock(),
            routing_manager=MagicMock(),
            resolve_project_name=lambda: "test"
        )
        result = manager.check_response_error("LLM service is not configured")
        assert result is True

    def test_check_response_error_calling_llm(self):
        """check_response_error should detect LLM call error"""
        from agent.core.filmeto_plan import FilmetoPlanManager
        manager = FilmetoPlanManager(
            plan_service=MagicMock(),
            signals=MagicMock(),
            routing_manager=MagicMock(),
            resolve_project_name=lambda: "test"
        )
        result = manager.check_response_error("Error calling LLM service")
        assert result is True


# =============================================================================
# Tests for agent/prompt/__init__.py - Module exports
# =============================================================================

class TestPromptInitExports:
    """Tests for agent/prompt/__init__.py exports"""

    def test_module_exists(self):
        """agent.prompt module should be importable"""
        import agent.prompt
        assert agent.prompt is not None

    def test_module_has_docstring(self):
        """agent.prompt module should have docstring"""
        import agent.prompt
        assert agent.prompt.__doc__ is not None
        assert "prompt" in agent.prompt.__doc__.lower()


# =============================================================================
# Tests for agent/react/react.py - React class
# =============================================================================

class TestReactInit:
    """Tests for React initialization"""

    def test_react_creation_basic(self):
        """React should be created with required parameters"""
        from agent.react.react import React
        from agent.react.constants import ReactConfig
        from agent.react.status import ReactStatus

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test_project",
            react_type="test_react",
            build_prompt_function=lambda x: f"prompt: {x}",
            max_steps=ReactConfig.DEFAULT_MAX_STEPS
        )

        assert react.project_name == "test_project"
        assert react.react_type == "test_react"
        assert react.max_steps == ReactConfig.DEFAULT_MAX_STEPS
        assert react.status == ReactStatus.IDLE
        assert react.messages == []

    def test_react_max_steps_minimum(self):
        """React should enforce minimum max_steps of 1"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x,
            max_steps=0
        )

        assert react.max_steps == 1

    def test_react_metrics_initial_state(self):
        """React should have zero metrics initially"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x,
            max_steps=10
        )

        metrics = react.get_metrics()
        assert metrics["total_llm_calls"] == 0
        assert metrics["total_tool_calls"] == 0
        assert metrics["llm_duration_ms"] == 0.0
        assert metrics["tool_duration_ms"] == 0.0


class TestReactDrainPendingMessages:
    """Tests for React._drain_pending_messages"""

    def test_drain_pending_messages_empty(self):
        """_drain_pending_messages should return empty list when no messages"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x
        )

        result = react._drain_pending_messages()
        assert result == []

    def test_drain_pending_messages_clears_queue(self):
        """_drain_pending_messages should clear the queue"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x
        )
        react.pending_user_messages = ["msg1", "msg2"]

        result = react._drain_pending_messages()
        assert result == ["msg1", "msg2"]
        assert react.pending_user_messages == []


class TestReactCreateEvent:
    """Tests for React._create_event"""

    def test_create_event_with_content(self):
        """_create_event should create AgentEvent with proper context"""
        from agent.react.react import React
        from agent.event.agent_event import AgentEventType
        from agent.chat.content import TextContent

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test_project",
            react_type="test_react",
            build_prompt_function=lambda x: x,
            message_id="msg_123"
        )
        react.step_id = 5

        content = TextContent(text="test content")
        event = react._create_event(AgentEventType.LLM_OUTPUT.value, content=content)
        assert event.project_name == "test_project"
        assert event.react_type == "test_react"
        assert event.step_id == 5
        assert event.message_id == "msg_123"
        assert event.content is not None


class TestReactNormalizeCompressedMessages:
    """Tests for React._normalize_compressed_messages"""

    def test_normalize_string_content(self):
        """_normalize_compressed_messages should handle string"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x
        )

        result = react._normalize_compressed_messages("compressed text")
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "compressed text" in result[0]["content"]

    def test_normalize_empty_string(self):
        """_normalize_compressed_messages should return empty list for empty string"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x
        )

        result = react._normalize_compressed_messages("")
        assert result == []

    def test_normalize_list_of_dicts(self):
        """_normalize_compressed_messages should handle list of dicts"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x
        )

        compressed = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "response"}
        ]
        result = react._normalize_compressed_messages(compressed)
        assert len(result) == 2
        assert result[0]["role"] == "user"

    def test_normalize_invalid_type(self):
        """_normalize_compressed_messages should return empty for invalid type"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x
        )

        result = react._normalize_compressed_messages(123)
        assert result == []


class TestReactParseAction:
    """Tests for React._parse_action"""

    def test_parse_action_final_json(self):
        """_parse_action should parse final action JSON"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x
        )

        response = '{"type": "final", "final": "Task completed"}'
        action = react._parse_action(response)
        assert action.is_final()
        assert action.final == "Task completed"

    def test_parse_action_tool_json(self):
        """_parse_action should parse tool action JSON"""
        from agent.react.react import React

        mock_workspace = MagicMock()
        react = React(
            workspace=mock_workspace,
            project_name="test",
            react_type="test",
            build_prompt_function=lambda x: x
        )

        response = '{"type": "tool", "tool_name": "execute_skill", "tool_args": {"skill_name": "test"}}'
        action = react._parse_action(response)
        assert action.is_tool()
        assert action.tool_name == "execute_skill"


# =============================================================================
# Tests for agent/react/react_service.py - ReactService
# =============================================================================

class TestReactServiceSingleton:
    """Tests for ReactService singleton pattern"""

    def test_react_service_singleton(self):
        """ReactService should be singleton"""
        from agent.react.react_service import ReactService
        s1 = ReactService()
        s2 = ReactService()
        assert s1 is s2

    def test_react_service_max_instances_default(self):
        """ReactService should have default max_instances"""
        from agent.react.react_service import ReactService

        service = ReactService()
        # Default max_instances is 100
        assert service._max_instances == 100


class TestReactServiceInstanceKey:
    """Tests for ReactService._generate_instance_key"""

    def test_generate_instance_key(self):
        """_generate_instance_key should format key correctly"""
        from agent.react.react_service import ReactService

        service = ReactService()
        key = service._generate_instance_key("project1", "react_type1")
        assert key == "project1:react_type1"


class TestReactServiceInstanceManagement:
    """Tests for ReactService instance management"""

    def test_clear_all_instances(self):
        """clear_all_instances should remove all instances"""
        from agent.react.react_service import ReactService

        service = ReactService()
        service.clear_all_instances()
        assert service.get_instance_count() == 0

    def test_get_instance_count_empty(self):
        """get_instance_count should return 0 when empty"""
        from agent.react.react_service import ReactService

        service = ReactService()
        service.clear_all_instances()
        assert service.get_instance_count() == 0

    def test_remove_react_non_existing(self):
        """remove_react should return False for non-existing"""
        from agent.react.react_service import ReactService

        service = ReactService()
        service.clear_all_instances()
        result = service.remove_react("non_existing", "type")
        assert result is False

    def test_get_react_non_existing(self):
        """get_react should return None for non-existing"""
        from agent.react.react_service import ReactService

        service = ReactService()
        service.clear_all_instances()
        result = service.get_react("non_existing", "type")
        assert result is None

    def test_list_instances_empty(self):
        """list_instances should return empty dict when empty"""
        from agent.react.react_service import ReactService

        service = ReactService()
        service.clear_all_instances()
        result = service.list_instances()
        assert result == {}


class TestReactServiceMetrics:
    """Tests for ReactService.get_metrics"""

    def test_get_metrics_empty(self):
        """get_metrics should return empty metrics"""
        from agent.react.react_service import ReactService

        service = ReactService()
        service.clear_all_instances()
        metrics = service.get_metrics()

        assert metrics["total_instances"] == 0
        assert metrics["instances"] == {}


# =============================================================================
# Tests for agent/router/__init__.py - Module exports
# =============================================================================

class TestRouterInitExports:
    """Tests for agent/router/__init__.py exports"""

    def test_message_router_service_exported(self):
        """MessageRouterService should be exported"""
        from agent.router import MessageRouterService
        assert MessageRouterService is not None

    def test_routing_decision_exported(self):
        """RoutingDecision should be exported"""
        from agent.router import RoutingDecision
        assert RoutingDecision is not None

    def test_all_exports_present(self):
        """__all__ should contain expected exports"""
        from agent.router import __all__
        expected = ["MessageRouterService", "RoutingDecision"]
        for item in expected:
            assert item in __all__


# =============================================================================
# Tests for agent/skill/__init__.py - Module exports
# =============================================================================

class TestSkillInitExports:
    """Tests for agent/skill/__init__.py exports"""

    def test_skill_exported(self):
        """Skill should be exported"""
        from agent.skill import Skill
        assert Skill is not None

    def test_skill_service_exported(self):
        """SkillService should be exported"""
        from agent.skill import SkillService
        assert SkillService is not None

    def test_all_exports_present(self):
        """__all__ should contain expected exports"""
        from agent.skill import __all__
        expected = ['Skill', 'SkillService']
        for item in expected:
            assert item in __all__


# =============================================================================
# Tests for agent/skill/skill_models.py - Skill dataclass
# =============================================================================

class TestSkillDataclass:
    """Tests for Skill dataclass"""

    def test_skill_creation_basic(self):
        """Skill should be created with required fields"""
        from agent.skill.skill_models import Skill

        skill = Skill(
            name="test_skill",
            description="A test skill",
            knowledge="Test knowledge content",
            skill_path="/path/to/skill"
        )

        assert skill.name == "test_skill"
        assert skill.description == "A test skill"
        assert skill.knowledge == "Test knowledge content"
        assert skill.skill_path == "/path/to/skill"

    def test_skill_with_optional_fields(self):
        """Skill should accept optional fields"""
        from agent.skill.skill_models import Skill

        skill = Skill(
            name="full_skill",
            description="Full skill",
            knowledge="Knowledge",
            skill_path="/path",
            reference="reference.md",
            examples="example usage",
            scripts=["script1.py"],
            tools=["tool1", "tool2"]
        )

        assert skill.reference == "reference.md"
        assert skill.examples == "example usage"
        assert skill.scripts == ["script1.py"]
        assert skill.tools == ["tool1", "tool2"]

    def test_skill_optional_fields_default_none(self):
        """Skill optional fields should default to None"""
        from agent.skill.skill_models import Skill

        skill = Skill(
            name="minimal",
            description="desc",
            knowledge="know",
            skill_path="/path"
        )

        assert skill.reference is None
        assert skill.examples is None
        assert skill.scripts is None
        assert skill.tools is None

    def test_skill_get_example_call(self):
        """get_example_call should generate valid JSON"""
        from agent.skill.skill_models import Skill

        skill = Skill(
            name="example_skill",
            description="Example skill",
            knowledge="knowledge",
            skill_path="/path"
        )

        example = skill.get_example_call("test prompt")
        # Should be valid JSON
        parsed = json.loads(example)
        assert parsed["type"] == "tool"
        assert parsed["tool_name"] == "execute_skill"
        assert parsed["tool_args"]["skill_name"] == "example_skill"

    def test_skill_get_example_call_default_prompt(self):
        """get_example_call should use default prompt if none provided"""
        from agent.skill.skill_models import Skill

        skill = Skill(
            name="default_skill",
            description="Default skill",
            knowledge="knowledge",
            skill_path="/path"
        )

        example = skill.get_example_call()
        parsed = json.loads(example)
        assert "default_skill" in parsed["tool_args"]["prompt"]


# =============================================================================
# Tests for agent/skill/skill_chat.py - SkillChat
# =============================================================================

class TestSkillChatInit:
    """Tests for SkillChat initialization"""

    def test_skill_chat_creation(self):
        """SkillChat should be created with skill_service"""
        from agent.skill.skill_chat import SkillChat

        mock_service = MagicMock()
        chat = SkillChat(skill_service=mock_service)
        assert chat.skill_service == mock_service


class TestSkillChatBuildPrompt:
    """Tests for SkillChat._build_skill_react_prompt"""

    def test_build_skill_react_prompt_calls_render(self):
        """_build_skill_react_prompt should call prompt_service.render_prompt"""
        from agent.skill.skill_chat import SkillChat
        from agent.skill.skill_models import Skill

        mock_service = MagicMock()
        chat = SkillChat(skill_service=mock_service)
        skill = Skill(
            name="test_skill",
            description="Test skill",
            knowledge="Test knowledge",
            skill_path="/path/to/skill"
        )

        # Mock tool metadata
        mock_tool_metadata = MagicMock(
            name="test_tool",
            description="Test tool",
            parameters=[]
        )

        # Patch ToolService at the actual import location (inside _build_skill_react_prompt)
        with patch('agent.tool.tool_service.ToolService') as MockToolService:
            mock_tool_service_instance = MockToolService.return_value
            mock_tool_service_instance.get_tool_metadata.return_value = mock_tool_metadata

            # Patch prompt_service at its actual location
            with patch('agent.prompt.prompt_service.prompt_service') as mock_prompt_service:
                mock_prompt_service.render_prompt.return_value = "rendered prompt"
                result = chat._build_skill_react_prompt(skill, "question", ["test_tool"], {"arg": "value"})
                assert result == "rendered prompt"
                mock_prompt_service.render_prompt.assert_called_once()


# =============================================================================
# Tests for agent/skill/system/delete_scene/scripts/delete_single_scene.py
# =============================================================================

class TestResolveSceneIdFromDescription:
    """Tests for resolve_scene_id_from_description function"""

    def test_resolve_scene_id_last_scene(self):
        """resolve_scene_id should resolve 'last scene'"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import resolve_scene_id_from_description

        mock_manager = MagicMock()
        mock_scene1 = MagicMock(scene_id="scene_001")
        mock_scene2 = MagicMock(scene_id="scene_002")
        mock_manager.list_scenes.return_value = [mock_scene1, mock_scene2]

        result, error = resolve_scene_id_from_description(mock_manager, "last scene")
        assert result == "scene_002"
        assert error is None

    def test_resolve_scene_id_first_scene(self):
        """resolve_scene_id should resolve 'first scene'"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import resolve_scene_id_from_description

        mock_manager = MagicMock()
        mock_scene1 = MagicMock(scene_id="scene_001")
        mock_scene2 = MagicMock(scene_id="scene_002")
        mock_manager.list_scenes.return_value = [mock_scene1, mock_scene2]

        result, error = resolve_scene_id_from_description(mock_manager, "first scene")
        assert result == "scene_001"
        assert error is None

    def test_resolve_scene_id_explicit_format(self):
        """resolve_scene_id should resolve explicit scene_XXX format"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import resolve_scene_id_from_description

        mock_manager = MagicMock()
        mock_scene = MagicMock(scene_id="scene_003")
        mock_manager.list_scenes.return_value = [mock_scene]
        mock_manager.get_scene.return_value = mock_scene

        result, error = resolve_scene_id_from_description(mock_manager, "scene_003")
        assert result == "scene_003"
        assert error is None

    def test_resolve_scene_id_number(self):
        """resolve_scene_id should resolve by scene number"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import resolve_scene_id_from_description

        mock_manager = MagicMock()
        mock_scene1 = MagicMock(scene_id="scene_001")
        mock_scene2 = MagicMock(scene_id="scene_002")
        mock_scene3 = MagicMock(scene_id="scene_003")
        mock_manager.list_scenes.return_value = [mock_scene1, mock_scene2, mock_scene3]

        result, error = resolve_scene_id_from_description(mock_manager, "scene 2")
        assert result == "scene_002"
        assert error is None

    def test_resolve_scene_id_no_scenes(self):
        """resolve_scene_id should return error when no scenes"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import resolve_scene_id_from_description

        mock_manager = MagicMock()
        mock_manager.list_scenes.return_value = []

        result, error = resolve_scene_id_from_description(mock_manager, "last scene")
        assert result is None
        assert "No scenes exist" in error

    def test_resolve_scene_id_chinese_ordinal(self):
        """resolve_scene_id should resolve Chinese ordinal (第一幕)"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import resolve_scene_id_from_description

        mock_manager = MagicMock()
        mock_scene1 = MagicMock(scene_id="scene_001")
        mock_scene2 = MagicMock(scene_id="scene_002")
        mock_manager.list_scenes.return_value = [mock_scene1, mock_scene2]

        result, error = resolve_scene_id_from_description(mock_manager, "第一幕")
        assert result == "scene_001"
        assert error is None

    def test_resolve_scene_id_non_existing(self):
        """resolve_scene_id should return error for non-existing scene"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import resolve_scene_id_from_description

        mock_manager = MagicMock()
        mock_scene = MagicMock(scene_id="scene_001")
        mock_manager.list_scenes.return_value = [mock_scene]
        mock_manager.get_scene.return_value = None

        result, error = resolve_scene_id_from_description(mock_manager, "scene_005")
        assert result is None
        assert "does not exist" in error

    def test_resolve_scene_id_out_of_range(self):
        """resolve_scene_id should return error for out-of-range number"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import resolve_scene_id_from_description

        mock_manager = MagicMock()
        mock_scene = MagicMock(scene_id="scene_001")
        mock_manager.list_scenes.return_value = [mock_scene]
        # For explicit scene_XXX format, get_scene returns None for non-existing
        mock_manager.get_scene.return_value = None

        result, error = resolve_scene_id_from_description(mock_manager, "scene 10")
        assert result is None
        assert "does not exist" in error


class TestDeleteSceneFromManager:
    """Tests for delete_scene_from_manager function"""

    def test_delete_scene_success(self):
        """delete_scene_from_manager should delete existing scene"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import delete_scene_from_manager

        mock_manager = MagicMock()
        mock_scene = MagicMock()
        mock_manager.get_scene.return_value = mock_scene
        mock_manager.delete_scene.return_value = True

        result = delete_scene_from_manager(mock_manager, "scene_001")
        assert result["success"] is True
        assert result["deleted"] is True

    def test_delete_scene_non_existing(self):
        """delete_scene_from_manager should handle non-existing scene"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import delete_scene_from_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.return_value = None
        mock_manager.delete_scene.return_value = False

        result = delete_scene_from_manager(mock_manager, "scene_999")
        assert result["success"] is True
        assert result["deleted"] is False
        assert "does not exist" in result["message"]

    def test_delete_scene_failure(self):
        """delete_scene_from_manager should handle deletion failure"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import delete_scene_from_manager

        mock_manager = MagicMock()
        mock_scene = MagicMock()
        mock_manager.get_scene.return_value = mock_scene
        mock_manager.delete_scene.return_value = False

        result = delete_scene_from_manager(mock_manager, "scene_001")
        assert result["success"] is False
        assert result["deleted"] is False

    def test_delete_scene_exception(self):
        """delete_scene_from_manager should handle exceptions"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import delete_scene_from_manager

        mock_manager = MagicMock()
        mock_manager.get_scene.side_effect = Exception("Test error")

        result = delete_scene_from_manager(mock_manager, "scene_001")
        assert result["success"] is False
        assert "error" in result


class TestExecuteFunction:
    """Tests for execute function"""

    def test_execute_no_screenplay_manager(self):
        """execute should return error when no screenplay manager"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import execute

        mock_context = MagicMock()
        mock_context.get_screenplay_manager.return_value = None

        result = execute(mock_context, {"scene_id": "scene_001"})
        assert result["success"] is False
        assert result["error"] == "no_screenplay_manager"

    def test_execute_missing_scene_identifier(self):
        """execute should return error when missing scene identifier"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import execute

        mock_context = MagicMock()
        mock_manager = MagicMock()
        mock_context.get_screenplay_manager.return_value = mock_manager

        result = execute(mock_context, {})
        assert result["success"] is False
        assert result["error"] == "missing_scene_identifier"

    def test_execute_with_explicit_scene_id(self):
        """execute should work with explicit scene_id"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import execute

        mock_context = MagicMock()
        mock_manager = MagicMock()
        mock_scene = MagicMock()
        mock_manager.get_scene.return_value = mock_scene
        mock_manager.delete_scene.return_value = True
        mock_context.get_screenplay_manager.return_value = mock_manager

        result = execute(mock_context, {"scene_id": "scene_001"})
        assert result["success"] is True
        assert result["deleted"] is True

    def test_execute_with_description(self):
        """execute should resolve scene from description"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import execute

        mock_context = MagicMock()
        mock_manager = MagicMock()
        mock_scene = MagicMock(scene_id="scene_002")
        mock_manager.list_scenes.return_value = [MagicMock(scene_id="scene_001"), mock_scene]
        mock_manager.get_scene.return_value = mock_scene
        mock_manager.delete_scene.return_value = True
        mock_context.get_screenplay_manager.return_value = mock_manager

        result = execute(mock_context, {"scene_description": "last scene"})
        assert result["success"] is True


class TestExecuteInContextAlias:
    """Tests for execute_in_context alias"""

    def test_execute_in_context_is_alias(self):
        """execute_in_context should be alias for execute"""
        from agent.skill.system.delete_scene.scripts.delete_single_scene import execute, execute_in_context

        assert execute_in_context is execute