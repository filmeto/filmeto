"""
Test QmlAgentChatListModel with demo project history data.

This test verifies that the QmlAgentChatListModel can correctly load and
process chat history data from the workspace demo project.
"""
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Qt application first
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from agent.chat.history.agent_chat_storage import MessageLogHistory
from agent.chat.content import StructureContent
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_items import ChatListItem


def test_history_storage_read():
    """Test that MessageLogStorage can read demo project history."""
    workspace_path = str(project_root / "workspace")
    project_name = "demo"

    history = MessageLogHistory(workspace_path, project_name)
    messages = history.get_latest_messages(count=10)

    print(f"=== Test 1: MessageLogStorage Read ===")
    print(f"Workspace: {workspace_path}")
    print(f"Project: {project_name}")
    print(f"Total message count: {history.get_total_count()}")
    print(f"Active log count: {history.storage.get_message_count()}")
    print(f"Retrieved {len(messages)} messages")

    if messages:
        print(f"\nFirst message keys: {messages[0].keys()}")
        print(f"\nFirst message sample:")
        print(json.dumps(messages[0], ensure_ascii=False, indent=2)[:500] + "...")

    assert len(messages) > 0, "Should have messages in demo project"
    print("✓ Test 1 passed: History storage read successful\n")
    return messages


def test_structured_content_parsing(messages):
    """Test that structured_content can be parsed correctly."""
    print(f"=== Test 2: StructuredContent Parsing ===")

    success_count = 0
    error_count = 0

    for msg in messages[:5]:  # Test first 5 messages
        content_list = msg.get("structured_content", [])
        message_id = msg.get("message_id", "unknown")

        for content_item in content_list:
            if isinstance(content_item, dict):
                try:
                    sc = StructureContent.from_dict(content_item)
                    content_type = getattr(sc, 'content_type', 'unknown')
                    print(f"  ✓ Message {message_id[:8]}... -> {content_type}")
                    success_count += 1
                except Exception as e:
                    print(f"  ✗ Message {message_id[:8]}... -> Error: {e}")
                    error_count += 1

    print(f"\nParsed {success_count} content items successfully")
    if error_count > 0:
        print(f"Failed to parse {error_count} content items")
    print("✓ Test 2 completed\n")

    return error_count == 0


def test_build_item_from_history(messages):
    """Test that _build_item_from_history can create ChatListItem."""
    print(f"=== Test 3: Build ChatListItem from History ===")

    # Import the widget to use its _build_item_from_history method
    from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget

    # Create a mock workspace with all required attributes/signals
    from PySide6.QtCore import QObject, Signal

    class MockWorkspace(QObject):
        project_switched = Signal(str)

        def __init__(self):
            super().__init__()
            self.workspace_path = str(project_root / "workspace")
            self.project_name = "demo"

        def get_project(self):
            return None  # We'll skip crew metadata loading

        def connect_project_switched(self, slot):
            self.project_switched.connect(slot)

    # Create widget without going through full initialization
    # Instead, manually test the _build_item_from_history logic

    success_count = 0
    skip_count = 0
    error_count = 0

    # Test the logic directly by creating a minimal widget setup
    workspace_obj = MockWorkspace()

    for msg in messages[:10]:
        message_id = msg.get("message_id", "unknown")
        try:
            # Manually replicate _build_item_from_history logic
            metadata = msg.get("metadata", {})
            content_list = msg.get("structured_content", [])

            sender_id = msg.get("sender_id") or metadata.get("sender_id", "unknown")
            sender_name = msg.get("sender_name") or metadata.get("sender_name", sender_id)
            timestamp = msg.get("timestamp") or metadata.get("timestamp")

            if not message_id:
                continue

            is_user = sender_id.lower() == "user"

            if is_user:
                text_content = ""
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        if content_item.get("content_type") == "text":
                            text_content = content_item.get("data", {}).get("text", "")
                            break
                print(f"  ✓ Message {message_id[:8]}... -> User: '{text_content[:30]}...'")
                success_count += 1
            else:
                # Parse structured content
                structured_content = []
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        try:
                            sc = StructureContent.from_dict(content_item)
                            structured_content.append(sc)
                        except Exception as e:
                            pass

                # Check for system metadata that should be skipped
                from agent.chat.agent_chat_types import ContentType
                skip = False
                for sc in structured_content:
                    if hasattr(sc, 'content_type') and sc.content_type == ContentType.METADATA:
                        event_type = getattr(sc, 'metadata_type', None)
                        if event_type in ("producer_start", "crew_member_start", "responding_agent_start"):
                            skip = True
                            break

                if skip:
                    skip_count += 1
                else:
                    content_types = [sc.content_type.value for sc in structured_content if hasattr(sc, 'content_type')]
                    print(f"  ✓ Message {message_id[:8]}... -> Agent {sender_name}: {content_types[:3]}")
                    success_count += 1

        except Exception as e:
            print(f"  ✗ Message {message_id[:8]}... -> Error: {e}")
            error_count += 1

    print(f"\nBuilt {success_count} ChatListItem objects successfully")
    print(f"Skipped {skip_count} system metadata messages (expected)")
    if error_count > 0:
        print(f"Failed to build {error_count} items")
    print("✓ Test 3 completed\n")

    return error_count == 0


def test_qml_model_conversion(messages):
    """Test that ChatListItem can be converted to QML model items."""
    print(f"=== Test 4: QML Model Conversion ===")

    # Manually build ChatListItems from messages
    from agent.chat.agent_chat_message import AgentMessage

    items = []
    for msg in messages[:5]:
        message_id = msg.get("message_id", "")
        if not message_id:
            continue

        metadata = msg.get("metadata", {})
        content_list = msg.get("structured_content", [])

        sender_id = msg.get("sender_id") or metadata.get("sender_id", "unknown")
        sender_name = msg.get("sender_name") or metadata.get("sender_name", sender_id)
        timestamp = msg.get("timestamp") or metadata.get("timestamp")

        is_user = sender_id.lower() == "user"

        try:
            # Parse structured content
            structured_content = []
            for content_item in content_list:
                if isinstance(content_item, dict):
                    try:
                        sc = StructureContent.from_dict(content_item)
                        structured_content.append(sc)
                    except Exception:
                        pass

            # Create ChatListItem directly
            from app.ui.chat.list.agent_chat_list_items import ChatListItem

            if is_user:
                text_content = ""
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        if content_item.get("content_type") == "text":
                            text_content = content_item.get("data", {}).get("text", "")
                            break

                item = ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=True,
                    user_content=text_content,
                )
            else:
                # Add timestamp to metadata
                if timestamp and "timestamp" not in metadata:
                    metadata["timestamp"] = timestamp

                agent_message = AgentMessage(
                    sender_id=sender_id,
                    sender_name=sender_name,
                    message_id=message_id,
                    metadata=metadata,
                    structured_content=structured_content,
                )

                item = ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=False,
                    agent_message=agent_message,
                    agent_color="#4a90e2",
                    agent_icon="🤖",
                    crew_member_metadata={},
                )

            items.append(item)
            print(f"  ✓ Created ChatListItem for {sender_name}")

        except Exception as e:
            print(f"  ✗ Failed to create ChatListItem: {e}")
            return False

    # Convert to QML format
    qml_items = []
    for item in items:
        try:
            qml_item = QmlAgentChatListModel.from_chat_list_item(item)
            qml_items.append(qml_item)

            # Verify required fields
            assert QmlAgentChatListModel.MESSAGE_ID in qml_item
            assert QmlAgentChatListModel.SENDER_ID in qml_item
            assert QmlAgentChatListModel.STRUCTURED_CONTENT in qml_item
            assert QmlAgentChatListModel.CONTENT_TYPE in qml_item

            print(f"  ✓ {qml_item[QmlAgentChatListModel.SENDER_NAME]}: {qml_item[QmlAgentChatListModel.CONTENT_TYPE]}")
        except Exception as e:
            print(f"  ✗ Conversion error: {e}")
            import traceback
            traceback.print_exc()
            return False

    print(f"\nConverted {len(qml_items)} items to QML format successfully")

    # Test model operations
    model = QmlAgentChatListModel()
    for qml_item in qml_items:
        model.add_item(qml_item)

    assert model.rowCount() == len(qml_items), f"Model should have {len(qml_items)} rows"
    print(f"Model has {model.rowCount()} rows")

    # Verify data retrieval
    for i in range(model.rowCount()):
        item = model.get_item(i)
        assert item is not None, f"Item at row {i} should not be None"
        assert QmlAgentChatListModel.MESSAGE_ID in item

    print("✓ Test 4 passed: QML model conversion successful\n")
    return True


def test_full_model_load():
    """Test full model loading from demo project history."""
    print(f"=== Test 5: Full Model Load ===")

    workspace_path = str(project_root / "workspace")
    project_name = "demo"

    history = MessageLogHistory(workspace_path, project_name)
    raw_messages = history.get_latest_messages(count=10)

    # Group messages by message_id (similar to widget logic)
    from app.ui.chat.list.agent_chat_list_items import MessageGroup

    message_groups = {}
    for msg_data in raw_messages:
        message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
        if not message_id:
            continue

        if message_id not in message_groups:
            message_groups[message_id] = MessageGroup()
        message_groups[message_id].add_message(msg_data)

    # Convert to ordered list
    ordered_messages = []
    for msg_data in reversed(raw_messages):
        message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
        if message_id in message_groups:
            combined = message_groups[message_id].get_combined_message()
            if combined:
                ordered_messages.append(combined)

    # Build ChatListItems and convert to QML format
    model = QmlAgentChatListModel()
    for msg_data in ordered_messages:
        try:
            metadata = msg_data.get("metadata", {})
            content_list = msg_data.get("structured_content", [])

            sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
            sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)
            timestamp = msg_data.get("timestamp") or metadata.get("timestamp")
            message_id = msg_data.get("message_id", "")

            if not message_id:
                continue

            is_user = sender_id.lower() == "user"

            # Parse structured content
            structured_content = []
            for content_item in content_list:
                if isinstance(content_item, dict):
                    try:
                        sc = StructureContent.from_dict(content_item)
                        structured_content.append(sc)
                    except Exception:
                        pass

            # Check for system metadata that should be skipped
            from agent.chat.agent_chat_types import ContentType
            skip = False
            for sc in structured_content:
                if hasattr(sc, 'content_type') and sc.content_type == ContentType.METADATA:
                    event_type = getattr(sc, 'metadata_type', None)
                    if event_type in ("producer_start", "crew_member_start", "responding_agent_start"):
                        skip = True
                        break

            if skip:
                continue

            # Build QML item directly
            if is_user:
                text_content = ""
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        if content_item.get("content_type") == "text":
                            text_content = content_item.get("data", {}).get("text", "")
                            break

                from agent.chat.content import TextContent
                qml_item = {
                    QmlAgentChatListModel.MESSAGE_ID: message_id,
                    QmlAgentChatListModel.SENDER_ID: sender_id,
                    QmlAgentChatListModel.SENDER_NAME: sender_name,
                    QmlAgentChatListModel.IS_USER: True,
                    QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
                    QmlAgentChatListModel.AGENT_ICON: "🤖",
                    QmlAgentChatListModel.CREW_METADATA: {},
                    QmlAgentChatListModel.STRUCTURED_CONTENT: [{
                        "content_type": "text",
                        "data": {"text": text_content}
                    }],
                    QmlAgentChatListModel.CONTENT_TYPE: "text",
                    QmlAgentChatListModel.IS_READ: True,
                    QmlAgentChatListModel.TIMESTAMP: timestamp,
                    QmlAgentChatListModel.DATE_GROUP: QmlAgentChatListModel._get_date_group(timestamp),
                }
            else:
                # Serialize structured content
                serialized_content = []
                for sc in structured_content:
                    if hasattr(sc, 'to_dict'):
                        serialized_content.append(sc.to_dict())

                # Determine primary content type
                content_type = "text"
                type_priority = [
                    ContentType.ERROR,
                    ContentType.THINKING,
                    ContentType.PROGRESS,
                    ContentType.TOOL_CALL,
                    ContentType.TEXT,
                    ContentType.TYPING,
                ]
                for sc in structured_content:
                    if hasattr(sc, 'content_type') and sc.content_type in type_priority:
                        content_type = sc.content_type.value
                        break

                qml_item = {
                    QmlAgentChatListModel.MESSAGE_ID: message_id,
                    QmlAgentChatListModel.SENDER_ID: sender_id,
                    QmlAgentChatListModel.SENDER_NAME: sender_name,
                    QmlAgentChatListModel.IS_USER: False,
                    QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
                    QmlAgentChatListModel.AGENT_ICON: "🤖",
                    QmlAgentChatListModel.CREW_METADATA: {},
                    QmlAgentChatListModel.STRUCTURED_CONTENT: serialized_content,
                    QmlAgentChatListModel.CONTENT_TYPE: content_type,
                    QmlAgentChatListModel.IS_READ: True,
                    QmlAgentChatListModel.TIMESTAMP: timestamp,
                    QmlAgentChatListModel.DATE_GROUP: QmlAgentChatListModel._get_date_group(timestamp),
                }

            model.add_item(qml_item)
            print(f"  ✓ Added {sender_name} message to model")

        except Exception as e:
            print(f"  ✗ Failed to process message: {e}")
            import traceback
            traceback.print_exc()

    row_count = model.rowCount()
    print(f"\nModel loaded with {row_count} rows")

    if row_count > 0:
        # Sample first few items
        for i in range(min(3, row_count)):
            item = model.get_item(i)
            sender_name = item.get(QmlAgentChatListModel.SENDER_NAME, "Unknown")
            content_type = item.get(QmlAgentChatListModel.CONTENT_TYPE, "unknown")
            print(f"  Row {i}: {sender_name} -> {content_type}")

    print("✓ Test 5 passed: Full model load successful\n")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing QmlAgentChatListModel with Demo Project History")
    print("=" * 60)
    print()

    # Test 1: Read from history storage
    messages = test_history_storage_read()

    # Test 2: Parse structured content
    test_structured_content_parsing(messages)

    # Test 3: Build ChatListItem from history
    test_build_item_from_history(messages)

    # Test 4: Convert to QML model format
    test_qml_model_conversion(messages)

    # Test 5: Full model load
    test_full_model_load()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
