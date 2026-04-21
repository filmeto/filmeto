"""
Detailed diagnosis of QML data flow in AgentChatList.
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, Qt

print("=" * 70)
print("AgentChatList QML Data Flow Diagnosis")
print("=" * 70)

app = QApplication.instance() or QApplication(sys.argv)

# Test 1: Check QmlAgentChatListModel roleNames
print("\nTest 1: Check QmlAgentChatListModel roleNames")
print("-" * 70)

from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

model = QmlAgentChatListModel()
role_names = model.roleNames()

print(f"Model has {len(role_names)} roles:")
for role_int, role_byte in role_names.items():
    role_name = role_byte.data().decode()
    print(f"  Role {role_int}: '{role_name}'")

# Test 2: Create test data and verify model structure
print("\nTest 2: Create test data and verify model structure")
print("-" * 70)

from agent.chat.content import TextContent, ThinkingContent

test_message = {
    QmlAgentChatListModel.MESSAGE_ID: "msg-123",
    QmlAgentChatListModel.SENDER_ID: "test_agent",
    QmlAgentChatListModel.SENDER_NAME: "Test Agent",
    QmlAgentChatListModel.IS_USER: False,
    QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
    QmlAgentChatListModel.AGENT_ICON: "🤖",
    QmlAgentChatListModel.CREW_METADATA: {},
    QmlAgentChatListModel.STRUCTURED_CONTENT: [
        TextContent(text="Hello world").to_dict(),
        ThinkingContent(thought="Analyzing...").to_dict(),
    ],
    QmlAgentChatListModel.CONTENT_TYPE: "thinking",
    QmlAgentChatListModel.IS_READ: True,
    QmlAgentChatListModel.TIMESTAMP: "2026-02-08T12:00:00",
    QmlAgentChatListModel.DATE_GROUP: "Today",
}

print("Test message structure:")
for key, value in test_message.items():
    if key == QmlAgentChatListModel.STRUCTURED_CONTENT:
        print(f"  {key}: {len(value)} items")
        for i, item in enumerate(value):
            print(f"    [{i}] content_type={item.get('content_type')}, has data={'data' in item}")
    else:
        print(f"  {key}: {value}")

# Add to model
model.add_item(test_message)
print(f"\nAdded to model, rowCount={model.rowCount()}")

# Test 3: Verify data() method returns correct values
print("\nTest 3: Verify model.data() method")
print("-" * 70)

from PySide6.QtCore import QModelIndex

index = model.index(0, 0)

# Try accessing data with different roles
for role_int, role_byte in role_names.items():
    role_name = role_byte.data().decode()
    value = model.data(index, role_int)
    print(f"  data(index, Role{role_int}) = {value}")

# Test 4: Create QQuickWidget and check context property
print("\nTest 4: QQuickWidget Context Property Setup")
print("-" * 70)

from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from PySide6.QtCore import QObject, Signal

class MockWorkspace(QObject):
    project_switched = Signal(str)
    def __init__(self):
        super().__init__()
        self.workspace_path = str(project_root / "workspace")
        self.project_name = "demo"

    def get_project(self):
        return None

    def connect_project_switched(self, slot):
        pass

print("Creating QmlAgentChatListWidget with mock workspace...")
widget = QmlAgentChatListWidget(MockWorkspace())

# Check if QML loaded
if widget._qml_root is None:
    print("✗ QML failed to load!")
    print("  Check QML errors above for details")
else:
    print("✓ QML loaded successfully")
    print(f"  Root object type: {widget._qml_root.metaObject().className()}")

    # Check context property
    context = widget._quick_widget.rootContext()
    chat_model_property = context.contextProperty("_chatModel")
    print(f"\n  Context property '_chatModel': {chat_model_property}")
    print(f"  Context property type: {type(chat_model_property)}")

    # Check model
    if hasattr(chat_model_property, 'rowCount'):
        print(f"  Model rowCount: {chat_model_property.rowCount()}")

    # Check if we can access role names through context property
    if hasattr(chat_model_property, 'roleNames'):
        context_role_names = chat_model_property.roleNames()
        print(f"  Model roleNames count: {len(context_role_names)}")

# Test 5: Simulate QML data access pattern
print("\nTest 5: Simulate QML data access pattern")
print("-" * 70)

print("\nIn QML ListView delegate, 'model' variable contains:")
print("  Each role is accessible as a property of the 'model' object")
print("\nExample QML code:")
print("  ListView {")
print("    model: _chatModel")
print("    delegate: Loader {")
print("      property var modelData: model  // Capture model reference")
print("      // Now can access:")
print("      // modelData.messageId, modelData.senderName, etc.")
print("    }")
print("  }")

# Test 6: Check if role values are accessible
print("\nTest 6: Check role value access in QML")
print("-" * 70)

print("\nWhen QML accesses model.messageId:")
role_int = Qt.UserRole + 1  # messageId role
value = model.data(index, role_int)
print(f"  Model returns: {value}")
print(f"  Expected: 'msg-123'")
print(f"  Match: {value == 'msg-123'}")

print("\nWhen QML accesses model.senderName:")
role_int = Qt.UserRole + 3  # senderName role
value = model.data(index, role_int)
print(f"  Model returns: {value}")
print(f"  Expected: 'Test Agent'")
print(f"  Match: {value == 'Test Agent'}")

print("\nWhen QML accesses model.structuredContent:")
role_int = Qt.UserRole + 8  # structuredContent role
value = model.data(index, role_int)
print(f"  Model returns type: {type(value)}")
if isinstance(value, list):
    print(f"  Model returns: {len(value)} items")
    for i, item in enumerate(value):
        print(f"    [{i}] content_type={item.get('content_type')}")
else:
    print(f"  Model returns: {value}")

# Test 7: Check QML property access
print("\nTest 7: Verify QML property access mechanism")
print("-" * 70)

print("\nIn Qt Quick ListView, when model is a QAbstractListModel:")
print("  - The 'model' variable in delegate is NOT the model itself")
print("  - It's a JavaScript object containing role values for current row")
print("  - Each role becomes a property on this object")
print("\nHowever, the property name must match EXACTLY!")
print("\nOur model role names are:")
for role_int, role_byte in role_names.items():
    role_name = role_byte.data().decode()
    print(f"  '{role_name}'")

print("\nQML should access these as:")
print("  model.messageId, model.senderName, model.structuredContent, etc.")
print("\nNOT as:")
print("  model.MessageId (capital M)")
print("  model.message_id (underscore)")

print("\n" + "=" * 70)
print("Diagnosis Complete")
print("=" * 70)
