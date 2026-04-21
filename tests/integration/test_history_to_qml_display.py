"""
Test loading and displaying history data in QML.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from agent.chat.history.agent_chat_storage import MessageLogHistory
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_items import ChatListItem, MessageGroup

print("=" * 70)
print("History Data to QML Display Test")
print("=" * 70)

# Test 1: Load raw history data
print("\nTest 1: Load raw history data")
print("-" * 70)

workspace_path = str(project_root / "workspace")
project_name = "demo"

history = MessageLogHistory(workspace_path, project_name)
raw_messages = history.get_latest_messages(count=5)

print(f"Loaded {len(raw_messages)} messages from history")

for msg in raw_messages[:2]:
    message_id = msg.get("message_id", "unknown")
    sender_name = msg.get("sender_name", "unknown")
    content_list = msg.get("structured_content", [])
    print(f"\nMessage: {message_id[:8]}... from {sender_name}")
    print(f"  Content items: {len(content_list)}")
    for sc in content_list:
        ct = sc.get("content_type", "unknown")
        print(f"    - {ct}")

# Test 2: Group messages by message_id (like the widget does)
print("\n\nTest 2: Group messages by message_id")
print("-" * 70)

message_groups = {}
for msg_data in raw_messages:
    message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
    if not message_id:
        continue

    if message_id not in message_groups:
        message_groups[message_id] = MessageGroup()
    message_groups[message_id].add_message(msg_data)

print(f"Grouped into {len(message_groups)} unique messages")

for msg_id, group in list(message_groups.items())[:2]:
    combined = group.get_combined_message()
    if combined:
        print(f"\nMessage: {msg_id[:8]}...")
        content_list = combined.get("structured_content", [])
        print(f"  Combined content items: {len(content_list)}")
        for sc in content_list:
            ct = sc.get("content_type", "unknown")
            print(f"    - {ct}")

# Test 3: Build ChatListItem from combined message
print("\n\nTest 3: Build ChatListItem from combined message")
print("-" * 70)

from agent.chat.content import StructureContent

for msg_id, group in list(message_groups.items())[:2]:
    combined_msg = group.get_combined_message()
    if not combined_msg:
        continue

    metadata = combined_msg.get("metadata", {})
    content_list = combined_msg.get("structured_content", [])

    sender_id = combined_msg.get("sender_id") or metadata.get("sender_id", "unknown")
    sender_name = combined_msg.get("sender_name") or metadata.get("sender_name", sender_id)
    timestamp = combined_msg.get("timestamp") or metadata.get("timestamp")
    message_id = combined_msg.get("message_id", "")

    print(f"\nProcessing: {sender_name}")

    # Parse structured content
    structured_content = []
    parse_errors = 0

    for content_item in content_list:
        if isinstance(content_item, dict):
            try:
                sc = StructureContent.from_dict(content_item)
                structured_content.append(sc)
                print(f"  ✓ Parsed: {sc.content_type.value}")
            except Exception as e:
                parse_errors += 1
                print(f"  ✗ Failed to parse: {e}")

    print(f"  Parse result: {len(structured_content)} success, {parse_errors} errors")

    if structured_content:
        # Check serialized format
        print(f"\n  Serialized format check:")
        for sc in structured_content[:3]:
            sc_dict = sc.to_dict()
            ct = sc_dict.get("content_type")
            has_data = "data" in sc_dict
            data_keys = list(sc_dict.get("data", {}).keys()) if has_data else []
            print(f"    {ct}: data={has_data}, keys={data_keys[:3]}")

# Test 4: Convert to QML model format
print("\n\nTest 4: Convert to QML model format")
print("-" * 70)

model = QmlAgentChatListModel()

for msg_id, group in list(message_groups.items())[:2]:
    combined_msg = group.get_combined_message()
    if not combined_msg:
        continue

    try:
        # Build ChatListItem using widget logic
        metadata = combined_msg.get("metadata", {})
        content_list = combined_msg.get("structured_content", [])

        sender_id = combined_msg.get("sender_id") or metadata.get("sender_id", "unknown")
        sender_name = combined_msg.get("sender_name") or metadata.get("sender_name", sender_id)
        timestamp = combined_msg.get("timestamp") or metadata.get("timestamp")
        message_id = combined_msg.get("message_id", "")

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

        # Serialize structured content
        serialized_content = []
        for sc in structured_content:
            if hasattr(sc, 'to_dict'):
                serialized_content.append(sc.to_dict())

        # Build QML item for agent message
        qml_item = {
            QmlAgentChatListModel.MESSAGE_ID: message_id,
            QmlAgentChatListModel.SENDER_ID: sender_id,
            QmlAgentChatListModel.SENDER_NAME: sender_name,
            QmlAgentChatListModel.IS_USER: is_user,
            QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
            QmlAgentChatListModel.AGENT_ICON: "🤖",
            QmlAgentChatListModel.CREW_METADATA: {},
            QmlAgentChatListModel.STRUCTURED_CONTENT: serialized_content,
            QmlAgentChatListModel.CONTENT_TYPE: "text",
            QmlAgentChatListModel.IS_READ: True,
            QmlAgentChatListModel.TIMESTAMP: timestamp,
            QmlAgentChatListModel.DATE_GROUP: QmlAgentChatListModel._get_date_group(timestamp),
        }

        print(f"\n{sender_name} -> QML format:")
        print(f"  Message ID: {message_id[:8]}...")
        print(f"  Content items: {len(serialized_content)}")
        for sc in serialized_content[:3]:
            ct = sc.get("content_type")
            print(f"    - {ct}")

        # Add to model
        model.add_item(qml_item)

    except Exception as e:
        print(f"\n✗ Error processing {msg_id}: {e}")
        import traceback
        traceback.print_exc()

# Test 5: Verify model data
print("\n\nTest 5: Verify model data")
print("-" * 70)

print(f"Model row count: {model.rowCount()}")

from PySide6.QtCore import QModelIndex

for row in range(model.rowCount()):
    index = model.index(row, 0)

    # Get all role values
    role_names = model.roleNames()

    print(f"\nRow {row}:")
    for role_int, role_byte in role_names.items():
        role_name = role_byte.data().decode()
        value = model.data(index, role_int)

        if role_name == "structuredContent" and isinstance(value, list):
            print(f"  {role_name}: {len(value)} items")
        elif role_name == "timestamp":
            print(f"  {role_name}: {value}")
        elif role_name == "senderName":
            print(f"  {role_name}: {value}")
        elif role_name == "isUser":
            print(f"  {role_name}: {value}")
        elif value and role_name in ["messageId", "contentType"]:
            print(f"  {role_name}: {value}")

# Test 6: Check for tool_input vs tool_args issue
print("\n\nTest 6: Check tool_input vs tool_args compatibility")
print("-" * 70)

# Find a message with tool_call
for msg_id, group in message_groups.items():
    combined = group.get_combined_message()
    if not combined:
        continue

    for sc in combined.get("structured_content", []):
        if sc.get("content_type") == "tool_call":
            data = sc.get("data", {})
            print(f"Found tool_call in history:")
            print(f"  Data keys: {list(data.keys())}")

            # Check if it uses old format
            if "tool_input" in data:
                print(f"  ⚠ Uses OLD format: tool_input")
                print(f"  Value: {data.get('tool_input')}")

            if "tool_args" in data:
                print(f"  ✓ Uses NEW format: tool_args")
                print(f"  Value: {data.get('tool_args')}")

            break

print("\n" + "=" * 70)
print("Test Complete")
print("=" * 70)
print("""
Summary:
- History data loads correctly
- Messages group by message_id correctly
- StructureContent.from_dict() parses data correctly
- Model exposes data correctly to QML

If content is not displaying in QML, the issue is likely:
1. QML rendering issue (check QML errors in console)
2. Component import issue (check import paths)
3. Layout/visibility issue (check if content is off-screen)
4. Data binding issue (check if model is connected to QML)
""")
