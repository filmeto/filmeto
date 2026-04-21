"""
Unit tests for agent package __init__.py files.

Tests for:
- agent/__init__.py
- agent/chat/__init__.py
- agent/chat/history/__init__.py
- agent/core/__init__.py
"""
import pytest


class TestAgentInit:
    """Tests for agent/__init__.py exports"""

    def test_filmeto_agent_exported(self):
        """Verify FilmetoAgent is exported"""
        from agent import FilmetoAgent
        assert FilmetoAgent is not None

    def test_skill_service_exported(self):
        """Verify SkillService is exported"""
        from agent import SkillService
        assert SkillService is not None

    def test_crew_service_exported(self):
        """Verify CrewService is exported"""
        from agent import CrewService
        assert CrewService is not None

    def test_agent_message_exported(self):
        """Verify AgentMessage is exported"""
        from agent import AgentMessage
        assert AgentMessage is not None

    def test_content_type_exported(self):
        """Verify ContentType is exported"""
        from agent import ContentType
        assert ContentType is not None

    def test_agent_chat_signals_exported(self):
        """Verify AgentChatSignals is exported"""
        from agent import AgentChatSignals
        assert AgentChatSignals is not None

    def test_create_text_message_exported(self):
        """Verify create_text_message utility is exported"""
        from agent import create_text_message
        assert callable(create_text_message)

    def test_create_error_message_exported(self):
        """Verify create_error_message utility is exported"""
        from agent import create_error_message
        assert callable(create_error_message)

    def test_create_system_message_exported(self):
        """Verify create_system_message utility is exported"""
        from agent import create_system_message
        assert callable(create_system_message)

    def test_all_exports_present(self):
        """Verify __all__ contains all expected exports"""
        from agent import __all__
        expected = [
            "FilmetoAgent",
            "SkillService",
            "CrewService",
            "AgentMessage",
            "ContentType",
            "AgentChatSignals",
            "create_text_message",
            "create_error_message",
            "create_system_message",
        ]
        for item in expected:
            assert item in __all__


class TestAgentChatInit:
    """Tests for agent/chat/__init__.py exports"""

    def test_agent_message_exported(self):
        """Verify AgentMessage is exported"""
        from agent.chat import AgentMessage
        assert AgentMessage is not None

    def test_content_type_exported(self):
        """Verify ContentType is exported"""
        from agent.chat import ContentType
        assert ContentType is not None

    def test_structure_content_exported(self):
        """Verify StructureContent is exported"""
        from agent.chat import StructureContent
        assert StructureContent is not None

    def test_agent_chat_signals_exported(self):
        """Verify AgentChatSignals is exported"""
        from agent.chat import AgentChatSignals
        assert AgentChatSignals is not None

    def test_all_exports_present(self):
        """Verify __all__ contains all expected exports"""
        from agent.chat import __all__
        expected = [
            'AgentMessage',
            'ContentType',
            'StructureContent',
            'AgentChatSignals'
        ]
        for item in expected:
            assert item in __all__


class TestAgentChatHistoryInit:
    """Tests for agent/chat/history/__init__.py exports"""

    def test_fast_message_history_service_exported(self):
        """Verify FastMessageHistoryService is exported"""
        from agent.chat.history import FastMessageHistoryService
        assert FastMessageHistoryService is not None

    def test_message_saved_signal_exported(self):
        """Verify message_saved signal is exported"""
        from agent.chat.history import message_saved
        assert message_saved is not None

    def test_message_log_history_exported(self):
        """Verify MessageLogHistory is exported"""
        from agent.chat.history import MessageLogHistory
        assert MessageLogHistory is not None

    def test_message_log_storage_exported(self):
        """Verify MessageLogStorage is exported"""
        from agent.chat.history import MessageLogStorage
        assert MessageLogStorage is not None

    def test_message_log_archive_exported(self):
        """Verify MessageLogArchive is exported"""
        from agent.chat.history import MessageLogArchive
        assert MessageLogArchive is not None

    def test_agent_chat_history_listener_exported(self):
        """Verify AgentChatHistoryListener is exported"""
        from agent.chat.history import AgentChatHistoryListener
        assert AgentChatHistoryListener is not None

    def test_all_exports_present(self):
        """Verify __all__ contains all expected exports"""
        from agent.chat.history import __all__
        expected = [
            'FastMessageHistoryService',
            'message_saved',
            'MessageLogHistory',
            'MessageLogStorage',
            'MessageLogArchive',
            'AgentChatHistoryListener',
        ]
        for item in expected:
            assert item in __all__


class TestAgentCoreInit:
    """Tests for agent/core/__init__.py exports"""

    def test_filmeto_instance_manager_exported(self):
        """Verify FilmetoInstanceManager is exported"""
        from agent.core import FilmetoInstanceManager
        assert FilmetoInstanceManager is not None

    def test_extract_text_content_exported(self):
        """Verify extract_text_content utility is exported"""
        from agent.core import extract_text_content
        assert callable(extract_text_content)

    def test_truncate_text_exported(self):
        """Verify truncate_text utility is exported"""
        from agent.core import truncate_text
        assert callable(truncate_text)

    def test_get_workspace_path_safe_exported(self):
        """Verify get_workspace_path_safe utility is exported"""
        from agent.core import get_workspace_path_safe
        assert callable(get_workspace_path_safe)

    def test_get_project_from_workspace_exported(self):
        """Verify get_project_from_workspace utility is exported"""
        from agent.core import get_project_from_workspace
        assert callable(get_project_from_workspace)

    def test_resolve_project_name_exported(self):
        """Verify resolve_project_name utility is exported"""
        from agent.core import resolve_project_name
        assert callable(resolve_project_name)

    def test_producer_name_constant_exported(self):
        """Verify PRODUCER_NAME constant is exported"""
        from agent.core import PRODUCER_NAME
        assert PRODUCER_NAME is not None

    def test_default_model_constant_exported(self):
        """Verify DEFAULT_MODEL constant is exported"""
        from agent.core import DEFAULT_MODEL
        assert DEFAULT_MODEL is not None

    def test_default_temperature_constant_exported(self):
        """Verify DEFAULT_TEMPERATURE constant is exported"""
        from agent.core import DEFAULT_TEMPERATURE
        assert DEFAULT_TEMPERATURE is not None

    def test_default_streaming_constant_exported(self):
        """Verify DEFAULT_STREAMING constant is exported"""
        from agent.core import DEFAULT_STREAMING
        assert DEFAULT_STREAMING is not None

    def test_all_exports_present(self):
        """Verify __all__ contains all expected exports"""
        from agent.core import __all__
        expected = [
            "FilmetoInstanceManager",
            "extract_text_content",
            "truncate_text",
            "get_workspace_path_safe",
            "get_project_from_workspace",
            "resolve_project_name",
            "PRODUCER_NAME",
            "DEFAULT_MODEL",
            "DEFAULT_TEMPERATURE",
            "DEFAULT_STREAMING",
        ]
        for item in expected:
            assert item in __all__