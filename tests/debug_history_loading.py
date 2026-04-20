"""
Debug why _load_recent_conversation loads no messages.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

print("=" * 70)
print("Debug History Loading Issue")
print("=" * 70)

# Test 1: Verify history data exists
print("\nTest 1: Verify history data exists")
print("-" * 70)

from agent.chat.history.agent_chat_storage import MessageLogHistory

workspace_path = str(project_root / "workspace")
project_name = "demo"

history = MessageLogHistory(workspace_path, project_name)

total_count = history.get_total_count()
active_count = history.storage.get_message_count()

print(f"Total message count: {total_count}")
print(f"Active log count: {active_count}")

# Test 2: Try to load messages
print("\nTest 2: Load latest messages")
print("-" * 70)

messages = history.get_latest_messages(count=10)
print(f"get_latest_messages(10) returned: {len(messages)} messages")

if messages:
    print(f"\nFirst message keys: {list(messages[0].keys())}")
    print(f"\nFirst message:")
    for key, value in list(messages[0].items())[:5]:
        if key == "structured_content":
            print(f"  {key}: list with {len(value)} items")
        else:
            print(f"  {key}: {value}")
else:
    print("  No messages returned!")

# Test 3: Check _load_recent_conversation logic
print("\n\nTest 3: Check widget _load_recent_conversation logic")
print("-" * 70)

from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.data.workspace import Workspace

workspace = Workspace(project_name, workspace_path)

print("Creating widget...")
widget = QmlAgentChatListWidget(workspace)

print(f"QML root: {widget._qml_root}")
print(f"Model row count: {widget._model.rowCount()}")
print(f"History instance: {widget._history}")

# Call _load_recent_conversation and trace through
print("\nCalling _load_recent_conversation()...")

try:
    if widget._qml_root is None:
        print("  ✗ QML root is None - history loading skipped!")
    else:
        history = widget._get_history()
        if not history:
            print("  ✗ Failed to get history instance")
        else:
            print(f"  History instance: {history}")
            raw_messages = history.get_latest_messages(count=widget.PAGE_SIZE)
            print(f"  Raw messages: {len(raw_messages)}")

            if raw_messages:
                widget._clear_all_caches_and_model()

                # Group messages
                message_groups = {}
                for msg_data in raw_messages:
                    message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                    if not message_id:
                        print(f"  ⚠ Message without message_id: {list(msg_data.keys())}")

                    if message_id not in message_groups:
                        message_groups[message_id] = MessageGroup()
                    message_groups[message_id].add_message(msg_data)

                print(f"  Grouped into {len(message_groups)} unique message_ids")

                # Process grouped messages
                ordered_messages = []
                for msg_data in reversed(raw_messages):
                    message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
                    if message_id in message_groups and message_id not in widget._load_state.known_message_ids:
                        combined = message_groups[message_id].get_combined_message()
                        if combined:
                            ordered_messages.append(combined)
                            widget._load_state.known_message_ids.add(message_id)

                print(f"  Ordered messages: {len(ordered_messages)}")

                # Load into model
                for msg_data in ordered_messages:
                    widget._load_message_from_history(msg_data)

                print(f"  Model row count after load: {widget._model.rowCount()}")

                if widget._model.rowCount() == 0:
                    print("\n  ✗ Model still empty! Checking _load_message_from_history...")

                    # Check what _build_item_from_history returns
                    for msg_data in ordered_messages[:1]:
                        item = widget._build_item_from_history(msg_data)
                        print(f"  _build_item_from_history returned: {item}")
                        if item is None:
                            print(f"  ⚠ Item is None! Checking content...")

                            content_list = msg_data.get("structured_content", [])
                            print(f"    structured_content: {len(content_list)} items")

                            for sc in content_list:
                                ct = sc.get("content_type")
                                print(f"    - {ct}")

                            # Check if message was filtered out
                            from agent.chat.content import ContentType
                            for sc_dict in content_list:
                                if sc_dict.get("content_type") == "metadata":
                                    from agent.chat.content.structure_content import StructureContent
                                    try:
                                        sc = StructureContent.from_dict(sc_dict)
                                        metadata_type = getattr(sc, 'metadata_type', None)
                                        print(f"    METADATA content_type, metadata_type={metadata_type}")
                                    except:
                                        pass

except Exception as e:
    print(f"  ✗ Exception during load: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Debug Complete")
print("=" * 70)
