"""Test QML chat list history loading."""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test imports
from PySide6.QtWidgets import QApplication
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.ui.chat.list.agent_chat_list_items import ChatListItem

# Sample history message from actual file
SAMPLE_HISTORY_MESSAGE = {
    "message_id": "ac3f0b42-0a3e-4577-85a5-aa9ccfd25a7e",
    "message_type": "text",
    "sender_id": "user",
    "sender_name": "User",
    "timestamp": "2026-02-07T15:50:18.607307",
    "metadata": {
        "message_id": "ac3f0b42-0a3e-4577-85a5-aa9ccfd25a7e",
        "message_type": "text",
        "sender_id": "user",
        "sender_name": "User",
        "session_id": "test-session",
    },
    "structured_content": [
        {
            "content_id": "test-id",
            "content_type": "text",
            "data": {"text": "你好，请编写剧本"}
        }
    ],
    "content": [
        {
            "content_id": "test-id",
            "content_type": "text",
            "data": {"text": "你好，请编写剧本"}
        }
    ]
}

SAMPLE_AGENT_MESSAGE = {
    "message_id": "agent-msg-123",
    "message_type": "text",
    "sender_id": "agent",
    "sender_name": "助手",
    "timestamp": "2026-02-07T15:50:19.607307",
    "metadata": {
        "message_id": "agent-msg-123",
        "message_type": "text",
        "sender_id": "agent",
        "sender_name": "助手",
    },
    "structured_content": [
        {
            "content_type": "text",
            "data": {"text": "好的，我来帮你编写剧本"}
        }
    ],
    "content": [
        {
            "content_type": "text",
            "data": {"text": "好的，我来帮你编写剧本"}
        }
    ]
}


def test_model_creation():
    """Test model can be created."""
    print("Test 1: Model creation")
    model = QmlAgentChatListModel()
    assert model.rowCount() == 0
    print("✅ Model created successfully")


def test_add_user_message():
    """Test adding user message to model."""
    print("\nTest 2: Add user message")
    model = QmlAgentChatListModel()

    item = {
        QmlAgentChatListModel.MESSAGE_ID: "test123",
        QmlAgentChatListModel.SENDER_ID: "user",
        QmlAgentChatListModel.SENDER_NAME: "User",
        QmlAgentChatListModel.IS_USER: True,
        QmlAgentChatListModel.CONTENT: "Hello, QML!",
    }

    row = model.add_item(item)
    assert row == 0
    assert model.rowCount() == 1

    retrieved = model.get_item(0)
    assert retrieved[QmlAgentChatListModel.MESSAGE_ID] == "test123"
    assert retrieved[QmlAgentChatListModel.CONTENT] == "Hello, QML!"
    print("✅ User message added successfully")


def test_add_agent_message():
    """Test adding agent message to model."""
    print("\nTest 3: Add agent message")
    model = QmlAgentChatListModel()

    item = {
        QmlAgentChatListModel.MESSAGE_ID: "agent123",
        QmlAgentChatListModel.SENDER_ID: "agent",
        QmlAgentChatListModel.SENDER_NAME: "助手",
        QmlAgentChatListModel.IS_USER: False,
        QmlAgentChatListModel.CONTENT: "Hello from agent",
        QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
        QmlAgentChatListModel.AGENT_ICON: "🤖",
    }

    model.add_item(item)
    assert model.rowCount() == 1

    retrieved = model.get_item(0)
    assert retrieved[QmlAgentChatListModel.IS_USER] is False
    assert retrieved[QmlAgentChatListModel.SENDER_NAME] == "助手"
    print("✅ Agent message added successfully")


def test_history_message_parsing():
    """Test parsing history message JSON."""
    print("\nTest 4: Parse history message")

    # Test the _build_item_from_history method
    from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget

    # We need to mock workspace for this test
    class MockWorkspace:
        def __init__(self):
            self.workspace_path = "/tmp/test"
            self.project_name = "test"

        def get_project(self):
            return None

    widget = QmlAgentChatListWidget(MockWorkspace())

    # Test user message parsing
    user_item = widget._build_item_from_history(SAMPLE_HISTORY_MESSAGE)
    assert user_item is not None, "User item should not be None"
    assert user_item.message_id == "ac3f0b42-0a3e-4577-85a5-aa9ccfd25a7e"
    assert user_item.is_user is True
    assert user_item.user_content == "你好，请编写剧本"
    print("✅ User message parsed successfully")

    # Test agent message parsing
    agent_item = widget._build_item_from_history(SAMPLE_AGENT_MESSAGE)
    assert agent_item is not None, "Agent item should not be None"
    assert agent_item.message_id == "agent-msg-123"
    assert agent_item.is_user is False
    assert agent_item.agent_message is not None
    print("✅ Agent message parsed successfully")


def test_chat_list_item_to_qml():
    """Test converting ChatListItem to QML format."""
    print("\nTest 5: ChatListItem to QML conversion")

    chat_item = ChatListItem(
        message_id="test123",
        sender_id="user",
        sender_name="User",
        is_user=True,
        user_content="Test message",
    )

    qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

    assert qml_item[QmlAgentChatListModel.MESSAGE_ID] == "test123"
    assert qml_item[QmlAgentChatListModel.IS_USER] is True
    assert qml_item[QmlAgentChatListModel.CONTENT] == "Test message"
    print("✅ ChatListItem converted successfully")


def test_model_update():
    """Test updating items in model."""
    print("\nTest 6: Model update")
    model = QmlAgentChatListModel()

    item = {
        QmlAgentChatListModel.MESSAGE_ID: "msg123",
        QmlAgentChatListModel.CONTENT: "Original",
    }
    model.add_item(item)

    # Update the item
    success = model.update_item("msg123", {
        QmlAgentChatListModel.CONTENT: "Updated"
    })

    assert success is True
    retrieved = model.get_item(0)
    assert retrieved[QmlAgentChatListModel.CONTENT] == "Updated"
    print("✅ Model updated successfully")


def test_multiple_messages():
    """Test multiple messages in model."""
    print("\nTest 7: Multiple messages")
    model = QmlAgentChatListModel()

    for i in range(5):
        item = {
            QmlAgentChatListModel.MESSAGE_ID: f"msg{i}",
            QmlAgentChatListModel.SENDER_ID: "user" if i % 2 == 0 else "agent",
            QmlAgentChatListModel.SENDER_NAME: "User" if i % 2 == 0 else "Agent",
            QmlAgentChatListModel.IS_USER: i % 2 == 0,
            QmlAgentChatListModel.CONTENT: f"Message {i}",
        }
        model.add_item(item)

    assert model.rowCount() == 5

    # Check specific items
    item_0 = model.get_item(0)
    assert item_0[QmlAgentChatListModel.IS_USER] is True

    item_1 = model.get_item(1)
    assert item_1[QmlAgentChatListModel.IS_USER] is False
    print("✅ Multiple messages handled correctly")


def test_model_clear():
    """Test clearing the model."""
    print("\nTest 8: Model clear")
    model = QmlAgentChatListModel()

    for i in range(3):
        item = {
            QmlAgentChatListModel.MESSAGE_ID: f"msg{i}",
            QmlAgentChatListModel.CONTENT: f"Message {i}",
        }
        model.add_item(item)

    assert model.rowCount() == 3

    model.clear()
    assert model.rowCount() == 0
    print("✅ Model cleared successfully")


def main():
    """Run all tests."""
    print("=" * 60)
    print("QML Chat List History Loading Tests")
    print("=" * 60)

    tests = [
        test_model_creation,
        test_add_user_message,
        test_add_agent_message,
        test_history_message_parsing,
        test_chat_list_item_to_qml,
        test_model_update,
        test_multiple_messages,
        test_model_clear,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    success = main()
    sys.exit(0 if success else 1)
