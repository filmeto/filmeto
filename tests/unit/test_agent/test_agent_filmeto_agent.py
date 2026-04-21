"""
Unit tests for agent/filmeto_agent.py.

Tests for:
- FilmetoAgent class-level instance management
- FilmetoAgent initialization
- FilmetoAgent utility methods
- FilmetoAgent exports
"""
import pytest
from typing import Dict, Any, Optional

from agent.filmeto_agent import FilmetoAgent


class TestFilmetoAgentClassMethods:
    """Tests for FilmetoAgent class-level instance management"""

    def test_clear_all_instances(self):
        """clear_all_instances should clear instance cache"""
        FilmetoAgent.clear_all_instances()
        assert len(FilmetoAgent.list_instances()) == 0

    def test_list_instances_empty(self):
        """list_instances should return empty list when no instances"""
        FilmetoAgent.clear_all_instances()
        instances = FilmetoAgent.list_instances()
        assert instances == []

    def test_has_instance_false_when_empty(self):
        """has_instance should return False when no instance exists"""
        FilmetoAgent.clear_all_instances()
        class MockWorkspace:
            workspace_path = "/test/path"
        result = FilmetoAgent.has_instance(MockWorkspace(), "test_project")
        assert result is False

    def test_remove_instance_returns_false_when_not_exists(self):
        """remove_instance should return False when instance doesn't exist"""
        FilmetoAgent.clear_all_instances()
        class MockWorkspace:
            workspace_path = "/test/path"
        result = FilmetoAgent.remove_instance(MockWorkspace(), "nonexistent")
        assert result is False


class TestFilmetoAgentInit:
    """Tests for FilmetoAgent initialization"""

    def test_filmeto_agent_defaults(self):
        """FilmetoAgent should use default values"""
        agent = FilmetoAgent()
        assert agent.model == "gpt-4o-mini"
        assert agent.temperature == 0.7
        assert agent.streaming is True
        assert agent.workspace is None
        assert agent.project is None

    def test_filmeto_agent_custom_model(self):
        """FilmetoAgent should accept custom model"""
        agent = FilmetoAgent(model="gpt-4")
        assert agent.model == "gpt-4"

    def test_filmeto_agent_custom_temperature(self):
        """FilmetoAgent should accept custom temperature"""
        agent = FilmetoAgent(temperature=0.5)
        assert agent.temperature == 0.5

    def test_filmeto_agent_custom_streaming(self):
        """FilmetoAgent should accept custom streaming setting"""
        agent = FilmetoAgent(streaming=False)
        assert agent.streaming is False

    def test_filmeto_agent_conversation_history_empty(self):
        """FilmetoAgent should have empty conversation history"""
        agent = FilmetoAgent()
        assert agent.conversation_history == []

    def test_filmeto_agent_signals_initialized(self):
        """FilmetoAgent should have signals initialized"""
        agent = FilmetoAgent()
        assert agent.signals is not None


class TestFilmetoAgentProperties:
    """Tests for FilmetoAgent properties and methods"""

    def test_crew_members_property_empty(self):
        """crew_members property should return dict"""
        agent = FilmetoAgent()
        members = agent.crew_members
        assert isinstance(members, dict)

    def test_get_conversation_history_copy(self):
        """get_conversation_history should return copy"""
        agent = FilmetoAgent()
        history = agent.get_conversation_history()
        assert history == []
        # Verify it's a copy
        history.append("test")
        assert agent.conversation_history == []

    def test_clear_conversation_history(self):
        """clear_conversation_history should clear history"""
        agent = FilmetoAgent()
        # Add something to history
        from agent.chat.agent_chat_message import AgentMessage
        from agent.chat.content import TextContent
        msg = AgentMessage(
            sender_id="user",
            structured_content=[TextContent(text="test")]
        )
        agent.conversation_history.append(msg)
        assert len(agent.conversation_history) == 1
        agent.clear_conversation_history()
        assert agent.conversation_history == []

    def test_list_members_returns_list(self):
        """list_members should return list"""
        agent = FilmetoAgent()
        members = agent.list_members()
        assert isinstance(members, list)

    def test_get_member_returns_none(self):
        """get_member should return None for unknown member"""
        agent = FilmetoAgent()
        member = agent.get_member("nonexistent")
        assert member is None


class TestFilmetoAgentConvertEventToMessage:
    """Tests for convert_event_to_message static method"""

    def test_convert_event_to_message_requires_content(self):
        """convert_event_to_message should require content"""
        from agent.event.agent_event import AgentEvent
        event = AgentEvent(
            event_type="final",
            project_name="test",
            react_type="crew",
            content=None,
            payload={"test": "data"}
        )
        with pytest.raises(ValueError) as exc_info:
            FilmetoAgent.convert_event_to_message(
                event=event,
                sender_id="agent",
                sender_name="Agent",
                message_id="msg_123"
            )
        assert "content" in str(exc_info.value).lower()

    def test_convert_event_to_message_with_content(self):
        """convert_event_to_message should work with content"""
        from agent.event.agent_event import AgentEvent
        from agent.chat.content import TextContent
        event = AgentEvent(
            event_type="final",
            project_name="test",
            react_type="crew",
            content=TextContent(text="Hello World")
        )
        msg = FilmetoAgent.convert_event_to_message(
            event=event,
            sender_id="agent",
            sender_name="Agent",
            message_id="msg_123"
        )
        assert msg.sender_id == "agent"
        assert msg.sender_name == "Agent"
        assert msg.message_id == "msg_123"
        assert len(msg.structured_content) == 1


class TestFilmetoAgentExport:
    """Tests for FilmetoAgent export from agent package"""

    def test_filmeto_agent_exported_from_agent(self):
        """FilmetoAgent should be exported from agent package"""
        from agent import FilmetoAgent
        assert FilmetoAgent is not None

    def test_filmeto_agent_is_class(self):
        """FilmetoAgent should be a class"""
        from agent import FilmetoAgent
        assert isinstance(FilmetoAgent, type)