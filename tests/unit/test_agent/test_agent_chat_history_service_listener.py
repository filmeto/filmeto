"""
Unit tests for AgentChatHistoryListener and FastMessageHistoryService.

Tests for:
- agent/chat/history/agent_chat_history_listener.py
- agent/chat/history/agent_chat_history_service.py
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from agent.chat.history.agent_chat_history_listener import AgentChatHistoryListener
from agent.chat.history.agent_chat_history_service import FastMessageHistoryService, message_saved
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import ContentType
from agent.chat.content.text_content import TextContent


class TestFastMessageHistoryService:
    """Tests for FastMessageHistoryService"""

    def test_make_key(self):
        """Verify _make_key creates correct key"""
        key = FastMessageHistoryService._make_key("/workspace", "project")
        assert key == "/workspace||project"

    def test_make_key_different_projects(self):
        """Verify _make_key distinguishes different projects"""
        key1 = FastMessageHistoryService._make_key("/workspace", "project1")
        key2 = FastMessageHistoryService._make_key("/workspace", "project2")
        assert key1 != key2

    def test_make_key_different_workspaces(self):
        """Verify _make_key distinguishes different workspaces"""
        key1 = FastMessageHistoryService._make_key("/ws1", "project")
        key2 = FastMessageHistoryService._make_key("/ws2", "project")
        assert key1 != key2

    def test_message_saved_signal_exists(self):
        """Verify message_saved signal is defined"""
        assert message_saved is not None

    def test_message_saved_signal_emit(self):
        """Verify message_saved signal can emit"""
        received = []

        def receiver(sender, **kwargs):
            received.append(kwargs)

        message_saved.connect(receiver)
        message_saved.send(
            FastMessageHistoryService,
            workspace_path="/test",
            project_name="test_project",
            message_id="msg-123",
            gsn=1,
            current_gsn=5
        )

        assert len(received) == 1
        assert received[0]["workspace_path"] == "/test"
        assert received[0]["project_name"] == "test_project"
        assert received[0]["message_id"] == "msg-123"
        assert received[0]["gsn"] == 1
        assert received[0]["current_gsn"] == 5

        message_saved.disconnect(receiver)

    def test_serialize_content_with_to_dict(self):
        """Verify _serialize_content handles objects with to_dict"""
        content = TextContent(text="Hello")
        result = FastMessageHistoryService._serialize_content([content])
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_serialize_content_with_dict_object(self):
        """Verify _serialize_content handles objects with __dict__"""
        class SimpleObj:
            def __init__(self):
                self.key = "value"
        obj = SimpleObj()
        result = FastMessageHistoryService._serialize_content([obj])
        assert len(result) == 1
        assert result[0]["key"] == "value"

    def test_serialize_content_none(self):
        """Verify _serialize_content handles None"""
        result = FastMessageHistoryService._serialize_content(None)
        assert result == []

    def test_serialize_content_empty(self):
        """Verify _serialize_content handles empty list"""
        result = FastMessageHistoryService._serialize_content([])
        assert result == []

    def test_message_to_dict(self):
        """Verify _message_to_dict converts AgentMessage correctly"""
        msg = AgentMessage(
            sender_id="agent1",
            sender_name="Test Agent",
            metadata={"key": "value"}
        )
        result = FastMessageHistoryService._message_to_dict(msg)

        assert result["message_id"] == msg.message_id
        assert result["sender_id"] == "agent1"
        assert result["sender_name"] == "Test Agent"
        assert result["metadata"] == {"key": "value"}
        assert result["message_type"] == "text"  # Default when no content

    def test_message_to_dict_with_content(self):
        """Verify _message_to_dict with structured content"""
        content = TextContent(text="Hello world")
        msg = AgentMessage(
            sender_id="agent1",
            structured_content=[content]
        )
        result = FastMessageHistoryService._message_to_dict(msg)

        assert result["message_type"] == "text"
        assert len(result["structured_content"]) == 1


class TestAgentChatHistoryListener:
    """Tests for AgentChatHistoryListener"""

    def test_listener_init(self):
        """Verify listener initialization"""
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project"
        )
        assert listener.workspace_path == "/workspace"
        assert listener.project_name == "test_project"
        assert listener._signals is None
        assert listener._connected == False

    def test_listener_init_with_signals(self):
        """Verify listener initialization with signals"""
        signals = AgentChatSignals()
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project",
            signals=signals
        )
        assert listener._signals == signals
        assert listener._connected == False

    def test_listener_connect(self):
        """Verify connect method"""
        signals = AgentChatSignals()
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project"
        )
        listener.connect(signals)
        assert listener._signals == signals
        assert listener._connected == True

    def test_listener_connect_override_signals(self):
        """Verify connect can override signals"""
        signals1 = AgentChatSignals()
        signals2 = AgentChatSignals()
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project",
            signals=signals1
        )
        listener.connect(signals2)
        assert listener._signals == signals2

    def test_listener_connect_without_signals(self):
        """Verify connect without signals does nothing"""
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project"
        )
        # Should log warning and return without connecting
        listener.connect()
        assert listener._connected == False

    def test_listener_disconnect(self):
        """Verify disconnect method"""
        signals = AgentChatSignals()
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project"
        )
        listener.connect(signals)
        assert listener._connected == True
        listener.disconnect()
        assert listener._connected == False

    def test_listener_disconnect_when_not_connected(self):
        """Verify disconnect when not connected does nothing"""
        signals = AgentChatSignals()
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project",
            signals=signals
        )
        listener.disconnect()  # Not connected yet
        assert listener._connected == False

    def test_listener_context_manager(self):
        """Verify context manager enter/exit"""
        signals = AgentChatSignals()
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project",
            signals=signals
        )
        with listener:
            assert listener._connected == True
        assert listener._connected == False

    def test_listener_on_message_skip_no_agent_history(self):
        """Verify _on_message_send skips messages with _no_agent_history"""
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project"
        )

        # Message with _no_agent_history flag
        msg = AgentMessage(
            sender_id="test",
            metadata={"_no_agent_history": True}
        )

        with patch.object(FastMessageHistoryService, 'add_message') as mock_add:
            listener._on_message_send(None, msg)
            mock_add.assert_not_called()

    def test_listener_on_message_save_message(self):
        """Verify _on_message_send saves messages"""
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project"
        )

        msg = AgentMessage(
            sender_id="test",
            sender_name="Agent"
        )

        with patch.object(FastMessageHistoryService, 'add_message', return_value=True) as mock_add:
            listener._on_message_send(None, msg)
            mock_add.assert_called_once_with("/workspace", "test_project", msg)

    def test_listener_on_message_handles_exception(self):
        """Verify _on_message_send handles exceptions"""
        listener = AgentChatHistoryListener(
            workspace_path="/workspace",
            project_name="test_project"
        )

        msg = AgentMessage(sender_id="test")

        with patch.object(FastMessageHistoryService, 'add_message', side_effect=Exception("Error")):
            # Should not raise, just log error
            listener._on_message_send(None, msg)
            assert True


class TestFastMessageHistoryServiceInstances:
    """Tests for FastMessageHistoryService instance management"""

    def test_get_history_creates_instance(self):
        """Verify get_history creates new instance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Clear any existing instances
            FastMessageHistoryService._instances.clear()

            history = FastMessageHistoryService.get_history(tmpdir, "test_project")
            assert history is not None
            key = FastMessageHistoryService._make_key(tmpdir, "test_project")
            assert key in FastMessageHistoryService._instances

            # Clean up
            FastMessageHistoryService._instances.clear()

    def test_get_history_returns_same_instance(self):
        """Verify get_history returns same instance for same key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            FastMessageHistoryService._instances.clear()

            history1 = FastMessageHistoryService.get_history(tmpdir, "test_project")
            history2 = FastMessageHistoryService.get_history(tmpdir, "test_project")
            assert history1 == history2

            FastMessageHistoryService._instances.clear()

    def test_remove_history(self):
        """Verify remove_history removes instance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            FastMessageHistoryService._instances.clear()

            FastMessageHistoryService.get_history(tmpdir, "test_project")
            key = FastMessageHistoryService._make_key(tmpdir, "test_project")
            assert key in FastMessageHistoryService._instances

            FastMessageHistoryService.remove_history(tmpdir, "test_project")
            assert key not in FastMessageHistoryService._instances