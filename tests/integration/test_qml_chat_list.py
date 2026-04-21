"""Tests for QML-based AgentChatListWidget."""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtCore import QObject

from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.ui.chat.list.agent_chat_list_items import ChatListItem
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType
from agent.chat.content import TextContent, ThinkingContent


class TestQmlAgentChatListModel:
    """Test the QML-compatible chat list model."""

    def test_empty_model(self):
        """Test empty model initialization."""
        model = QmlAgentChatListModel()
        assert model.rowCount() == 0
        assert model.get_item(0) is None

    def test_add_item(self):
        """Test adding an item to the model."""
        model = QmlAgentChatListModel()

        item = {
            QmlAgentChatListModel.MESSAGE_ID: "msg1",
            QmlAgentChatListModel.SENDER_ID: "user",
            QmlAgentChatListModel.SENDER_NAME: "User",
            QmlAgentChatListModel.IS_USER: True,
            QmlAgentChatListModel.CONTENT: "Hello",
        }

        row = model.add_item(item)
        assert row == 0
        assert model.rowCount() == 1

        retrieved = model.get_item(0)
        assert retrieved[QmlAgentChatListModel.MESSAGE_ID] == "msg1"
        assert retrieved[QmlAgentChatListModel.CONTENT] == "Hello"

    def test_prepend_items(self):
        """Test prepending items to the model."""
        model = QmlAgentChatListModel()

        # Add initial item
        item1 = {
            QmlAgentChatListModel.MESSAGE_ID: "msg1",
            QmlAgentChatListModel.SENDER_ID: "agent",
            QmlAgentChatListModel.SENDER_NAME: "Agent",
            QmlAgentChatListModel.IS_USER: False,
            QmlAgentChatListModel.CONTENT: "First",
        }
        model.add_item(item1)

        # Prepend new items
        item2 = {
            QmlAgentChatListModel.MESSAGE_ID: "msg2",
            QmlAgentChatListModel.SENDER_ID: "user",
            QmlAgentChatListModel.SENDER_NAME: "User",
            QmlAgentChatListModel.IS_USER: True,
            QmlAgentChatListModel.CONTENT: "Second",
        }
        count = model.prepend_items([item2])

        assert count == 1
        assert model.rowCount() == 2

        # msg2 should now be at row 0
        first = model.get_item(0)
        assert first[QmlAgentChatListModel.MESSAGE_ID] == "msg2"

        # msg1 should be at row 1
        second = model.get_item(1)
        assert second[QmlAgentChatListModel.MESSAGE_ID] == "msg1"

    def test_update_item(self):
        """Test updating an existing item."""
        model = QmlAgentChatListModel()

        item = {
            QmlAgentChatListModel.MESSAGE_ID: "msg1",
            QmlAgentChatListModel.CONTENT: "Original",
        }
        model.add_item(item)

        # Update the item
        success = model.update_item("msg1", {
            QmlAgentChatListModel.CONTENT: "Updated"
        })

        assert success is True
        retrieved = model.get_item(0)
        assert retrieved[QmlAgentChatListModel.CONTENT] == "Updated"

    def test_get_row_by_message_id(self):
        """Test finding row by message ID."""
        model = QmlAgentChatListModel()

        for i in range(3):
            item = {
                QmlAgentChatListModel.MESSAGE_ID: f"msg{i}",
                QmlAgentChatListModel.CONTENT: f"Message {i}",
            }
            model.add_item(item)

        assert model.get_row_by_message_id("msg1") == 1
        assert model.get_row_by_message_id("nonexistent") is None

    def test_clear(self):
        """Test clearing the model."""
        model = QmlAgentChatListModel()

        for i in range(5):
            item = {
                QmlAgentChatListModel.MESSAGE_ID: f"msg{i}",
                QmlAgentChatListModel.CONTENT: f"Message {i}",
            }
            model.add_item(item)

        assert model.rowCount() == 5

        model.clear()
        assert model.rowCount() == 0

    def test_remove_first_n(self):
        """Test removing items from the beginning."""
        model = QmlAgentChatListModel()

        for i in range(5):
            item = {
                QmlAgentChatListModel.MESSAGE_ID: f"msg{i}",
                QmlAgentChatListModel.CONTENT: f"Message {i}",
            }
            model.add_item(item)

        model.remove_first_n(2)

        assert model.rowCount() == 3
        assert model.get_item(0)[QmlAgentChatListModel.MESSAGE_ID] == "msg2"

    def test_remove_last_n(self):
        """Test removing items from the end."""
        model = QmlAgentChatListModel()

        for i in range(5):
            item = {
                QmlAgentChatListModel.MESSAGE_ID: f"msg{i}",
                QmlAgentChatListModel.CONTENT: f"Message {i}",
            }
            model.add_item(item)

        model.remove_last_n(2)

        assert model.rowCount() == 3
        assert model.get_item(2)[QmlAgentChatListModel.MESSAGE_ID] == "msg2"

    def test_from_chat_list_item(self):
        """Test converting ChatListItem to QML format."""
        chat_item = ChatListItem(
            message_id="test123",
            sender_id="user",
            sender_name="Test User",
            is_user=True,
            user_content="Hello world",
        )

        qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

        assert qml_item[QmlAgentChatListModel.MESSAGE_ID] == "test123"
        assert qml_item[QmlAgentChatListModel.IS_USER] is True
        assert qml_item[QmlAgentChatListModel.CONTENT] == "Hello world"

    def test_from_agent_message(self):
        """Test converting AgentMessage to QML format."""
        agent_msg = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id="agent",
            sender_name="Test Agent",
            message_id="agent123",
            structured_content=[TextContent(text="Agent response")],
        )

        qml_item = QmlAgentChatListModel.from_agent_message(
            agent_msg,
            agent_color="#ff0000",
            agent_icon="🤖",
        )

        assert qml_item[QmlAgentChatListModel.MESSAGE_ID] == "agent123"
        assert qml_item[QmlAgentChatListModel.IS_USER] is False
        assert qml_item[QmlAgentChatListModel.AGENT_COLOR] == "#ff0000"
        assert qml_item[QmlAgentChatListModel.AGENT_ICON] == "🤖"

    def test_date_grouping(self):
        """Test date group calculation."""
        from datetime import datetime, timedelta
        import time

        model = QmlAgentChatListModel()

        now = datetime.now()
        today_ts = now.timestamp()
        yesterday_ts = (now - timedelta(days=1)).timestamp()
        week_ago_ts = (now - timedelta(days=7)).timestamp()

        assert model._get_date_group(today_ts) == "Today"
        assert model._get_date_group(yesterday_ts) == "Yesterday"
        assert model._get_date_group(week_ago_ts) in ["This Week", "Last Week"]


class TestQmlAgentChatListWidget:
    """Test the QML-based chat list widget."""

    @pytest.fixture
    def workspace(self):
        """Create a mock workspace."""
        workspace = Mock()
        project = Mock()
        project.name = "test_project"
        workspace.get_project.return_value = project
        workspace.workspace_path = "/tmp/test_workspace"
        workspace.project_name = "test_project"
        return workspace

    def test_widget_creation(self, workspace, qtbot):
        """Test widget creation."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_add_user_message(self, workspace, qtbot):
        """Test adding a user message."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)

        message_id = widget.add_user_message("Test message")

        assert message_id is not None
        # Note: Model might be empty if QML failed to load
        # In real tests, check for valid QML root

    def test_append_message(self, workspace, qtbot):
        """Test appending a message."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)

        message_id = widget.append_message("Agent", "Agent response")

        assert message_id is not None

    def test_update_streaming_message(self, workspace, qtbot):
        """Test updating a streaming message."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)

        # First add a message
        message_id = widget.append_message("Agent", "Initial")

        # Then update it
        widget.update_streaming_message(message_id, " Updated content")

    def test_get_or_create_agent_card(self, workspace, qtbot):
        """Test getting or creating agent card."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)

        message_id = widget.get_or_create_agent_card("msg123", "TestAgent")

        assert message_id == "msg123"

        # Calling again should return same ID
        message_id2 = widget.get_or_create_agent_card("msg123", "TestAgent")
        assert message_id2 == "msg123"

    def test_update_agent_card(self, workspace, qtbot):
        """Test updating agent card."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)

        message_id = widget.get_or_create_agent_card("msg123", "TestAgent")

        widget.update_agent_card(
            message_id,
            content="Updated content",
            append=False,
        )

    def test_update_agent_card_structured(self, workspace, qtbot):
        """Test updating agent card with structured content."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)

        message_id = widget.get_or_create_agent_card("msg123", "TestAgent")

        thinking = ThinkingContent(
            thought="Let me think about this...",
            title="Thinking",
            description="Agent thought process"
        )

        widget.update_agent_card(
            message_id,
            structured_content=thinking,
        )

    def test_clear(self, workspace, qtbot):
        """Test clearing the chat."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)

        widget.add_user_message("Message 1")
        widget.append_message("Agent", "Response")

        widget.clear()

        # Model should be empty
        assert widget._model.rowCount() == 0

    @patch('app.ui.chat.list.qml_agent_chat_list_widget.FastMessageHistoryService')
    def test_on_project_switched(self, mock_history_service, workspace, qtbot):
        """Test project switching."""
        widget = QmlAgentChatListWidget(workspace)
        qtbot.addWidget(widget)

        # Add some messages
        widget.add_user_message("Test")

        widget.on_project_switched("new_project")

        # Model should be cleared
        # (History loading is mocked, so actual messages won't load)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
