"""
End-to-end test simulating the actual agent_chat runtime scenario.
"""
import sys
from pathlib import Path
import logging

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging to see debug messages
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

print("=" * 70)
print("Agent Chat Runtime Simulation Test")
print("=" * 70)

# Test 1: Simulate the actual widget initialization
print("\nTest 1: Widget initialization with workspace")
print("-" * 70)

from app.data.workspace import Workspace
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget

workspace_path = str(project_root / "workspace")
project_name = "demo"

print(f"Creating workspace: {workspace_path}")
print(f"Project name: {project_name}")

workspace = Workspace(project_name, workspace_path)
print(f"Workspace project_name: {workspace.project_name}")

print("\nCreating QmlAgentChatListWidget...")
widget = QmlAgentChatListWidget(workspace)

print(f"QML root object: {widget._qml_root}")
print(f"Model initial row count: {widget._model.rowCount()}")

# Test 2: Check what happens during _load_recent_conversation
print("\n\nTest 2: Load recent conversation")
print("-" * 70)

print("Loading messages from history...")
widget._load_recent_conversation()

print(f"Model row count after load: {widget._model.rowCount()}")

# Check loaded items
if widget._model.rowCount() > 0:
    print("\nLoaded items:")
    for i in range(min(5, widget._model.rowCount())):
        item = widget._model.get_item(i)
        sender_name = item.get(QmlAgentChatListModel.SENDER_NAME, "Unknown")
        is_user = item.get(QmlAgentChatListModel.IS_USER, False)
        sc = item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])
        print(f"  [{i}] {sender_name} (user={is_user}): {len(sc)} content items")
else:
    print("  No items loaded!")

# Test 3: Verify model data is accessible to QML
print("\n\nTest 3: Verify QML data access")
print("-" * 70)

from PySide6.QtCore import QModelIndex

if widget._model.rowCount() > 0:
    index = widget._model.index(0, 0)

    # Check if we can get data
    role_names = widget._model.roleNames()

    print(f"Model has {len(role_names)} roles")

    # Check structuredContent role
    sc_role = None
    for role_int, role_byte in role_names.items():
        role_name = role_byte.data().decode()
        if role_name == "structuredContent":
            sc_role = role_int
            break

    if sc_role:
        sc_data = widget._model.data(index, sc_role)
        print(f"\nstructuredContent data:")
        print(f"  Type: {type(sc_data)}")
        print(f"  Is list: {isinstance(sc_data, list)}")
        print(f"  Length: {len(sc_data) if isinstance(sc_data, list) else 'N/A'}")

        if isinstance(sc_data, list) and sc_data:
            print(f"\n  First item:")
            first = sc_data[0]
            print(f"    Keys: {list(first.keys())}")
            print(f"    content_type: {first.get('content_type')}")
            print(f"    has data: {'data' in first}")

            if 'data' in first:
                data = first['data']
                print(f"    data type: {type(data)}")
                print(f"    data keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

# Test 4: Try adding a new message dynamically
print("\n\nTest 4: Add new message dynamically")
print("-" * 70)

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.content import TextContent, ThinkingContent
import uuid

message_id = str(uuid.uuid4())

print(f"Creating new message: {message_id[:8]}...")

new_message = AgentMessage(
    sender_id="test_agent",
    sender_name="测试助手",
    message_id=message_id,
    metadata={"timestamp": "2026-02-08T16:00:00"},
    structured_content=[
        TextContent(text="这是一条测试消息"),
        ThinkingContent(thought="正在思考如何回答..."),
    ],
)

# Convert to QML format
qml_item = QmlAgentChatListModel.from_agent_message(
    new_message,
    agent_color="#ff6b6b",
    agent_icon="🎬",
    crew_metadata={}
)

print(f"QML item created with {len(qml_item[QmlAgentChatListModel.STRUCTURED_CONTENT])} content items")

# Add to model
widget._model.add_item(qml_item)

print(f"Model row count: {widget._model.rowCount()}")

# Refresh QML
widget._refresh_qml_model()

print("QML model refreshed")

# Verify the item was added
last_item = widget._model.get_item(widget._model.rowCount() - 1)
if last_item:
    print(f"\nLast item in model:")
    print(f"  messageId: {last_item.get(QmlAgentChatListModel.MESSAGE_ID)[:8]}...")
    print(f"  senderName: {last_item.get(QmlAgentChatListModel.SENDER_NAME)}")
    print(f"  structuredContent: {len(last_item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, []))} items")

# Test 5: Check QML component structure
print("\n\nTest 5: QML Component structure verification")
print("-" * 70)

print("Checking QML component imports...")

# Read AgentChatList.qml
qml_path = Path(__file__).parent.parent / "app" / "ui" / "chat" / "qml" / "AgentChatList.qml"
qml_content = qml_path.read_text()

print(f"\nAgentChatList.qml imports:")
for line in qml_content.split('\n')[:10]:
    if 'import' in line.lower():
        print(f"  {line.strip()}")

# Read AgentMessageBubble.qml
bubble_path = Path(__file__).parent.parent / "app" / "ui" / "chat" / "qml" / "components" / "AgentMessageBubble.qml"
bubble_content = bubble_path.read_text()

print(f"\nAgentMessageBubble.qml imports:")
for line in bubble_content.split('\n')[:10]:
    if 'import' in line.lower():
        print(f"  {line.strip()}")

# Test 6: Check if there are any QML errors during runtime
print("\n\nTest 6: QML Error Check")
print("-" * 70)

if widget._quick_widget.status() == widget._quick_widget.Error:
    print("✗ QQuickWidget has errors!")
    errors = widget._quick_widget.errors()
    for error in errors:
        print(f"  Error: {error.toString()}")
else:
    print("✓ No QML errors")

print("\n" + "=" * 70)
print("Test Complete")
print("=" * 70)
print("""
If content is not displaying, possible causes:

1. **TypingIndicator filtering**
   - AgentMessageBubble.qml filters out typing content_type
   - Line 215-217: visible: {return String(raw).toLowerCase() !== "typing"}
   - Typing indicators are intentionally hidden

2. **Content rendering height issue**
   - If bubble height is 0, content won't be visible
   - Check if contentColumn calculates height correctly
   - Check if parent Item has proper height

3. **Z-order or clipping issue**
   - Content might be rendered behind other elements
   - Check clip: true settings
   - Check z values

4. **QML property binding not updating**
   - QML might not detect model changes
   - _refresh_qml_model() is called but might not be enough
   - Try explicit model update

5. **Data format mismatch**
   - QML expects certain data structure
   - Check if data format matches QML expectations
""")
