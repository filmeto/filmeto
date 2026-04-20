"""Direct test of history message parsing without widget initialization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ui.chat.list.agent_chat_list_items import ChatListItem
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType
from agent.chat.content import TextContent, StructureContent

# Sample history message from actual file
SAMPLE_USER_MESSAGE = {
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
    "sender_id": "assistant",
    "sender_name": "助手",
    "timestamp": "2026-02-07T15:50:19.607307",
    "metadata": {
        "message_id": "agent-msg-123",
        "message_type": "text",
        "sender_id": "assistant",
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


def parse_user_message(msg_data):
    """Parse user message from history data (from original widget)."""
    metadata = msg_data.get("metadata", {})
    content_list = msg_data.get("content", [])

    # IMPORTANT: Check both top-level and metadata for fields
    message_id = msg_data.get("message_id") or metadata.get("message_id", "")
    sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
    sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)
    message_type_str = msg_data.get("message_type") or metadata.get("message_type", "text")

    if not message_id:
        print("  ❌ No message_id found")
        return None

    print(f"  Parsed: message_id={message_id[:8]}..., sender={sender_name}")

    is_user = sender_id.lower() == "user"

    if is_user:
        text_content = ""
        for content_item in content_list:
            if isinstance(content_item, dict):
                if content_item.get("content_type") == "text":
                    text_content = content_item.get("data", {}).get("text", "")
                    break

        print(f"  User content: {text_content}")
        return ChatListItem(
            message_id=message_id,
            sender_id=sender_id,
            sender_name=sender_name,
            is_user=True,
            user_content=text_content,
        )
    else:
        # Agent message parsing
        structured_content = []
        for content_item in content_list:
            if isinstance(content_item, dict):
                try:
                    sc = StructureContent.from_dict(content_item)
                    structured_content.append(sc)
                except Exception as e:
                    print(f"  Failed to load structured content: {e}")

        agent_message = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id=sender_id,
            sender_name=sender_name,
            message_id=message_id,
            metadata=metadata,
            structured_content=structured_content,
        )

        return ChatListItem(
            message_id=message_id,
            sender_id=sender_id,
            sender_name=sender_name,
            is_user=False,
            agent_message=agent_message,
            agent_color="#4a90e2",
            agent_icon="🤖",
            crew_member_metadata={},
        )


def test_user_message_parsing():
    """Test parsing user message."""
    print("\n=== Test 1: User Message Parsing ===")
    result = parse_user_message(SAMPLE_USER_MESSAGE)
    assert result is not None
    assert result.message_id == "ac3f0b42-0a3e-4577-85a5-aa9ccfd25a7e"
    assert result.is_user is True
    assert result.user_content == "你好，请编写剧本"
    print("✅ User message parsed correctly")


def test_agent_message_parsing():
    """Test parsing agent message."""
    print("\n=== Test 2: Agent Message Parsing ===")
    result = parse_user_message(SAMPLE_AGENT_MESSAGE)
    assert result is not None
    assert result.message_id == "agent-msg-123"
    assert result.is_user is False
    assert result.agent_message is not None
    assert result.agent_message.get_text_content() == "好的，我来帮你编写剧本"
    print("✅ Agent message parsed correctly")


def test_qml_conversion():
    """Test converting to QML format."""
    print("\n=== Test 3: QML Conversion ===")

    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

    chat_item = ChatListItem(
        message_id="test123",
        sender_id="user",
        sender_name="User",
        is_user=True,
        user_content="Hello, QML!",
    )

    qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

    print(f"  Message ID: {qml_item[QmlAgentChatListModel.MESSAGE_ID]}")
    print(f"  Sender: {qml_item[QmlAgentChatListModel.SENDER_NAME]}")
    print(f"  Content: {qml_item[QmlAgentChatListModel.CONTENT]}")
    print(f"  Is User: {qml_item[QmlAgentChatListModel.IS_USER]}")

    assert qml_item[QmlAgentChatListModel.MESSAGE_ID] == "test123"
    assert qml_item[QmlAgentChatListModel.CONTENT] == "Hello, QML!"
    assert qml_item[QmlAgentChatListModel.IS_USER] is True
    print("✅ QML conversion works correctly")


def main():
    print("=" * 60)
    print("History Message Parsing Test")
    print("=" * 60)

    tests = [
        test_user_message_parsing,
        test_agent_message_parsing,
        test_qml_conversion,
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
    success = main()
    sys.exit(0 if success else 1)
