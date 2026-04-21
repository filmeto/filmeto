"""
Test QML role access patterns in QAbstractListModel.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QUrl

print("=" * 70)
print("QML Role Access Pattern Test")
print("=" * 70)

app = QApplication.instance() or QApplication(sys.argv)

from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from agent.chat.content import TextContent, ThinkingContent

# Create model with test data
model = QmlAgentChatListModel()

test_item = {
    QmlAgentChatListModel.MESSAGE_ID: "test-msg-1",
    QmlAgentChatListModel.SENDER_ID: "test_agent",
    QmlAgentChatListModel.SENDER_NAME: "Test Agent",
    QmlAgentChatListModel.IS_USER: False,
    QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
    QmlAgentChatListModel.AGENT_ICON: "🤖",
    QmlAgentChatListModel.CREW_METADATA: {},
    QmlAgentChatListModel.STRUCTURED_CONTENT: [
        TextContent(text="Hello").to_dict(),
        ThinkingContent(thought="Thinking...").to_dict(),
    ],
    QmlAgentChatListModel.CONTENT_TYPE: "thinking",
    QmlAgentChatListModel.IS_READ: True,
    QmlAgentChatListModel.TIMESTAMP: "2026-02-08T12:00:00",
    QmlAgentChatListModel.DATE_GROUP: "Today",
}

model.add_item(test_item)

print("\nTest 1: Check roleNames mapping")
print("-" * 70)

role_names = model.roleNames()

# Create a reverse mapping: role name -> role number
role_name_to_number = {}
for role_num, role_byte in role_names.items():
    role_name = role_byte.data().decode()
    role_name_to_number[role_name] = role_num
    print(f"  '{role_name}' -> Role {role_num}")

print("\nTest 2: Access data using role numbers")
print("-" * 70)

from PySide6.QtCore import QModelIndex

index = model.index(0, 0)

# Access using role number
message_id_role = role_name_to_number.get("messageId")
sender_name_role = role_name_to_number.get("senderName")
structured_content_role = role_name_to_number.get("structuredContent")

message_id = model.data(index, message_id_role)
sender_name = model.data(index, sender_name_role)
structured_content = model.data(index, structured_content_role)

print(f"  messageId (role {message_id_role}): {message_id}")
print(f"  senderName (role {sender_name_role}): {sender_name}")
print(f"  structuredContent (role {structured_content_role}): {type(structured_content)} with {len(structured_content)} items")

print("\nTest 3: Check what QML 'model' variable contains")
print("-" * 70)

print("  In QML ListView delegate, 'model' is a JavaScript object.")
print("  Each role should be accessible as a property.")
print("\n  Expected in QML:")
print("    model.messageId -> '{message_id}'")
print("    model.senderName -> '{sender_name}'")
print("    model.structuredContent -> [array]")
print("    model.isUser -> false")

print("\nTest 4: Verify role numbers")
print("-" * 70)

# Qt.UserRole is the base for custom roles
print(f"  Qt.UserRole = {Qt.UserRole}")
print(f"  First custom role should be Qt.UserRole + 1 = {Qt.UserRole + 1}")

# Check if our role numbers match expected pattern
expected_first_role = Qt.UserRole + 1
actual_first_role = min(role_names.keys())

print(f"  Expected first role: {expected_first_role}")
print(f"  Actual first role: {actual_first_role}")
print(f"  Match: {expected_first_role == actual_first_role}")

print("\nTest 5: Simulate QML property access")
print("-" * 70)

print("  QML code pattern:")
print("    property var modelData: model")
print("    Component {")
print("        UserMessageBubble {")
print("            structuredContent: modelData.structuredContent || []")
print("        }")
print("    }")

print("\n  This requires:")
print("    1. 'model' variable contains role data")
print("    2. 'model.structuredContent' returns the structuredContent value")
print("    3. The value is a JavaScript array")

print("\n  In our model:")
print(f"    model.data(index, structuredContent_role) returns:")
sc_value = model.data(index, structured_content_role)
print(f"      Type: {type(sc_value)}")
print(f"      Is list: {isinstance(sc_value, list)}")
print(f"      Length: {len(sc_value)}")
print(f"      First item type: {type(sc_value[0]) if sc_value else 'N/A'}")
print(f"      First item keys: {list(sc_value[0].keys()) if sc_value else 'N/A'}")

print("\nTest 6: Check QML type conversion")
print("-" * 70)

print("  Qt converts Python types to QML/JavaScript types:")
print(f"    Python str  -> QML string")
print(f"    Python bool -> QML bool")
print(f"    Python int  -> QML number")
print(f"    Python float -> QML number")
print(f"    Python dict -> QML object")
print(f"    Python list -> QML array/Javascript array")

print("\n  Our structuredContent:")
print(f"    Type: {type(sc_value)}")
print(f"    Is list: {isinstance(sc_value, list)}")

if isinstance(sc_value, list) and sc_value:
    print(f"\n  First item:")
    first = sc_value[0]
    print(f"    Type: {type(first)}")
    print(f"    Is dict: {isinstance(first, dict)}")
    print(f"    Keys: {list(first.keys())}")

    # Check if all required fields are present
    required_fields = ["content_type", "data", "content_id", "status"]
    for field in required_fields:
        present = field in first
        print(f"    '{field}': {present}")

print("\nTest 7: Verify QML Repeater can iterate over structuredContent")
print("-" * 70)

print("  In AgentMessageBubble.qml:")
print("    Repeater {")
print("        model: root.structuredContent || []")
print("        delegate: Loader {")
print("            property var widgetData: modelData  // modelData = each item in array")
print("            ...")
print("        }")
print("    }")

print("\n  For this to work:")
print("    1. root.structuredContent must be a JavaScript array")
print("    2. Each item must have a 'content_type' property")
print("    3. modelData.content_type must return the content type")

print("\n  Our data:")
print(f"    structuredContent is a list: {isinstance(sc_value, list)}")
if isinstance(sc_value, list) and sc_value:
    print(f"    First item has content_type: {'content_type' in sc_value[0]}")
    print(f"    First item content_type value: {sc_value[0].get('content_type')}")

print("\n" + "=" * 70)
print("Diagnosis Complete")
print("=" * 70)
print("""
If the data structure is correct, the issue might be:

1. **QML Import Path Issue**
   - Components might not be found
   - Check console for "module is not installed" errors

2. **QML Context Property Issue**
   - _chatModel might not be set correctly
   - Check if context property is registered before QML loads

3. **QML Rendering Issue**
   - Components might be rendering but not visible
   - Check height/width constraints
   - Check visibility and z-order

4. **Data Timing Issue**
   - Model might be empty when QML loads
   - QML doesn't update when data is added
   - Need to call _refresh_qml_model() after adding data

5. **QML Component Property Binding Issue**
   - Property names in QML must match exactly
   - Check for case sensitivity issues
""")
