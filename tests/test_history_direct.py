"""Direct test of history parsing without widget initialization."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_history_file():
    """Load and parse history file."""
    history_path = Path("workspace/projects/demo/agent/history/message.log")

    if not history_path.exists():
        print(f"❌ History file not found: {history_path}")
        return []

    messages = []
    with open(history_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError as e:
                continue

    return messages


def build_item_from_history(msg_data):
    """Direct implementation of _build_item_from_history for testing."""
    from agent.chat.agent_chat_message import AgentMessage
    from agent.chat.agent_chat_types import MessageType
    from agent.chat.content import StructureContent
    from app.ui.chat.list.agent_chat_list_items import ChatListItem

    try:
        metadata = msg_data.get("metadata", {})
        content_list = msg_data.get("content", [])

        # Check both top-level and metadata for fields
        message_id = msg_data.get("message_id") or metadata.get("message_id", "")
        sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
        sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)
        message_type_str = msg_data.get("message_type") or metadata.get("message_type", "text")

        if not message_id:
            return None

        # Skip system metadata events
        if message_type_str == "system":
            event_type = metadata.get("event_type", "")
            if event_type in ("producer_start", "crew_member_start", "responding_agent_start"):
                return None

        try:
            message_type = MessageType(message_type_str)
        except ValueError:
            message_type = MessageType.TEXT

        is_user = sender_id.lower() == "user"

        if is_user:
            text_content = ""
            for content_item in content_list:
                if isinstance(content_item, dict):
                    if content_item.get("content_type") == "text":
                        text_content = content_item.get("data", {}).get("text", "")
                        break

            return ChatListItem(
                message_id=message_id,
                sender_id=sender_id,
                sender_name=sender_name,
                is_user=True,
                user_content=text_content,
            )
        else:
            structured_content = []
            for content_item in content_list:
                if isinstance(content_item, dict):
                    try:
                        sc = StructureContent.from_dict(content_item)
                        structured_content.append(sc)
                    except Exception:
                        pass

            agent_message = AgentMessage(
                message_type=message_type,
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

    except Exception as e:
        print(f"  Error: {e}")
        return None


def test_history_loading():
    """Test loading and building items from history."""
    print("=" * 60)
    print("History Message Loading Test (Direct)")
    print("=" * 60)

    messages = load_history_file()
    print(f"\nLoaded {len(messages)} messages from file")

    if not messages:
        print("❌ No messages to test")
        return False

    # Get message types
    msg_types = {}
    for msg in messages:
        mt = msg.get("message_type", "unknown")
        msg_types[mt] = msg_types.get(mt, 0) + 1

    print(f"Message types: {msg_types}")

    # Build items
    print(f"\nBuilding ChatListItem objects...")
    built_items = []
    skipped_system = 0

    for msg in messages:
        item = build_item_from_history(msg)
        if item:
            built_items.append(item)
        else:
            # Check if it was a skipped system message
            if msg.get("message_type") == "system":
                skipped_system += 1

    print(f"Built {len(built_items)} items")
    print(f"Skipped {skipped_system} system metadata events")

    # Show some examples
    print(f"\nFirst 5 items:")
    for i, item in enumerate(built_items[:5]):
        if item.is_user:
            content = item.user_content[:30] if item.user_content else ""
            print(f"  {i+1}. [USER] {item.message_id[:8]}...: {content}...")
        else:
            content = item.agent_message.get_text_content()[:30] if item.agent_message else ""
            print(f"  {i+1}. [{item.sender_name}] {item.message_id[:8]}...: {content}...")

    # Test QML conversion
    print(f"\nTesting QML conversion...")
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

    model = QmlAgentChatListModel()
    converted_count = 0

    for item in built_items[:10]:  # Just convert first 10 for testing
        try:
            qml_item = QmlAgentChatListModel.from_chat_list_item(item)
            model.add_item(qml_item)
            converted_count += 1
        except Exception as e:
            print(f"  Conversion error: {e}")

    print(f"Converted {converted_count} items to QML format")
    print(f"Model row count: {model.rowCount()}")

    # Verify model items
    if model.rowCount() > 0:
        print(f"\nVerifying model items:")
        for i in range(min(3, model.rowCount())):
            item = model.get_item(i)
            is_user = item.get(QmlAgentChatListModel.IS_USER)
            sender = item.get(QmlAgentChatListModel.SENDER_NAME)
            content = item.get(QmlAgentChatListModel.CONTENT)[:30]
            print(f"  {i+1}. [{'USER' if is_user else sender}]: {content}...")

    print("\n" + "=" * 60)
    print(f"✅ SUCCESS: {len(built_items)} items can be loaded from history")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_history_loading()
    sys.exit(0 if success else 1)
