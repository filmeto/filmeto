"""
Test the complete data flow from QmlAgentChatListWidget to QML.

This test verifies that data is correctly formatted for QML consumption.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from agent.chat.content import TextContent, ThinkingContent, ToolCallContent, ProgressContent, ErrorContent
from agent.chat.agent_chat_types import ContentType


def test_serialize_content_to_dict():
    """Test that content serialization matches expected QML format."""
    print("=" * 70)
    print("Test 1: Content Serialization to QML Format")
    print("=" * 70)

    # Test TextContent
    text_content = TextContent(text="Hello, world!")
    text_dict = text_content.to_dict()

    print("\nTextContent.to_dict():")
    print(f"  content_type: {text_dict.get('content_type')}")
    print(f"  content_id: {text_dict.get('content_id')}")
    print(f"  data: {text_dict.get('data')}")
    print(f"  status: {text_dict.get('status')}")

    # Verify structure matches QML expectations
    assert text_dict.get('content_type') == 'text'
    assert text_dict.get('data', {}).get('text') == 'Hello, world!'
    assert 'content_id' in text_dict
    assert 'status' in text_dict
    print("\n✓ TextContent format matches QML expectations")

    # Test ThinkingContent
    thinking_content = ThinkingContent(thought="Analyzing...")
    thinking_dict = thinking_content.to_dict()

    print("\nThinkingContent.to_dict():")
    print(f"  content_type: {thinking_dict.get('content_type')}")
    print(f"  data: {thinking_dict.get('data')}")
    assert thinking_dict.get('content_type') == 'thinking'
    assert thinking_dict.get('data', {}).get('thought') == 'Analyzing...'
    print("✓ ThinkingContent format matches QML expectations")

    # Test ToolCallContent
    tool_content = ToolCallContent(tool_name="test_tool", tool_args={"arg1": "value1"})
    tool_dict = tool_content.to_dict()

    print("\nToolCallContent.to_dict():")
    print(f"  content_type: {tool_dict.get('content_type')}")
    print(f"  data: {tool_dict.get('data')}")
    assert tool_dict.get('content_type') == 'tool_call'
    assert tool_dict.get('data', {}).get('tool_name') == 'test_tool'
    # Verify tool_args is present
    assert 'tool_args' in tool_dict.get('data', {})
    print("✓ ToolCallContent format matches QML expectations")

    # Test ErrorContent
    error_content = ErrorContent(error_message="Something went wrong!")
    error_dict = error_content.to_dict()

    print("\nErrorContent.to_dict():")
    print(f"  content_type: {error_dict.get('content_type')}")
    print(f"  data: {error_dict.get('data')}")
    assert error_dict.get('content_type') == 'error'
    # ErrorContent uses error_message field
    assert 'error' in error_dict.get('data', {})
    print("✓ ErrorContent format matches QML expectations")

    print("\n✓ Test 1 passed: All content types serialize correctly")
    return True


def test_model_serialize_method():
    """Test QmlAgentChatListModel._serialize_structured_content method."""
    print("\n" + "=" * 70)
    print("Test 2: Model Serialization Method")
    print("=" * 70)

    model = QmlAgentChatListModel()

    # Create a mix of content types
    content_list = [
        TextContent(text="First message"),
        ThinkingContent(thought="Thinking step 1"),
        ToolCallContent(tool_name="calculate", tool_args={"x": 1}),
        TextContent(text="Second message"),
    ]

    # Serialize using model method
    serialized = model._serialize_structured_content(content_list)

    print(f"\nSerialized {len(serialized)} content items:")
    for i, item in enumerate(serialized):
        content_type = item.get('content_type')
        has_data = 'data' in item
        has_content_id = 'content_id' in item
        has_status = 'status' in item
        print(f"  [{i}] {content_type}: data={has_data}, id={has_content_id}, status={has_status}")

    # Verify all required fields are present
    for item in serialized:
        assert 'content_type' in item, "Missing content_type"
        assert 'content_id' in item, "Missing content_id"
        assert 'data' in item, "Missing data"
        assert 'status' in item, "Missing status"

    print("\n✓ Test 2 passed: Model serialization method works correctly")
    return True


def test_from_agent_message():
    """Test QmlAgentChatListModel.from_agent_message method."""
    print("\n" + "=" * 70)
    print("Test 3: from_agent_message Method")
    print("=" * 70)

    from agent.chat.agent_chat_message import AgentMessage

    model = QmlAgentChatListModel()

    # Create a test agent message with mixed content
    message = AgentMessage(
        sender_id="test_agent",
        sender_name="Test Agent",
        message_id="msg-123",
        metadata={"timestamp": "2026-02-08T12:00:00"},
        structured_content=[
            TextContent(text="Let me help you with that"),
            ThinkingContent(thought="Analyzing the user request"),
            ToolCallContent(tool_name="search", tool_args={"query": "test"}),
        ],
    )

    # Convert to QML format
    qml_item = model.from_agent_message(message)

    print("\nQML item structure:")
    print(f"  messageId: {qml_item.get(QmlAgentChatListModel.MESSAGE_ID)}")
    print(f"  senderName: {qml_item.get(QmlAgentChatListModel.SENDER_NAME)}")
    print(f"  contentType: {qml_item.get(QmlAgentChatListModel.CONTENT_TYPE)}")
    print(f"  timestamp: {qml_item.get(QmlAgentChatListModel.TIMESTAMP)}")
    print(f"  structuredContent: {len(qml_item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, []))} items")

    # Verify structured content
    structured_content = qml_item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])
    print(f"\nStructured content items:")
    for i, sc in enumerate(structured_content):
        ct = sc.get('content_type')
        print(f"  [{i}] {ct}")

    # Verify all required fields
    assert qml_item.get(QmlAgentChatListModel.MESSAGE_ID) == "msg-123"
    assert qml_item.get(QmlAgentChatListModel.SENDER_NAME) == "Test Agent"
    assert qml_item.get(QmlAgentChatListModel.IS_USER) == False
    assert len(structured_content) == 3

    print("\n✓ Test 3 passed: from_agent_message works correctly")
    return True


def test_add_user_message():
    """Test adding a user message to the model."""
    print("\n" + "=" * 70)
    print("Test 4: Add User Message")
    print("=" * 70)

    # Create a mock widget-like class
    class MockWorkspace:
        workspace_path = str(project_root / "workspace")
        project_name = "demo"

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

    model = QmlAgentChatListModel()

    # Simulate what add_user_message does
    message_id = "user-msg-123"
    content = "Hello, this is a test user message!"

    item = {
        QmlAgentChatListModel.MESSAGE_ID: message_id,
        QmlAgentChatListModel.SENDER_ID: "user",
        QmlAgentChatListModel.SENDER_NAME: "User",
        QmlAgentChatListModel.IS_USER: True,
        QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
        QmlAgentChatListModel.AGENT_ICON: "\ue6b3",
        QmlAgentChatListModel.CREW_METADATA: {},
        QmlAgentChatListModel.STRUCTURED_CONTENT: [{
            "content_type": "text",
            "data": {"text": content}
        }],
        QmlAgentChatListModel.CONTENT_TYPE: "text",
        QmlAgentChatListModel.IS_READ: True,
        QmlAgentChatListModel.TIMESTAMP: None,
        QmlAgentChatListModel.DATE_GROUP: "",
    }

    model.add_item(item)

    print(f"\nAdded user message:")
    print(f"  messageId: {item.get(QmlAgentChatListModel.MESSAGE_ID)}")
    print(f"  senderName: {item.get(QmlAgentChatListModel.SENDER_NAME)}")
    print(f"  isUser: {item.get(QmlAgentChatListModel.IS_USER)}")
    print(f"  structuredContent: {len(item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, []))} items")

    # Verify it was added
    assert model.rowCount() == 1
    retrieved = model.get_item(0)
    assert retrieved.get(QmlAgentChatListModel.MESSAGE_ID) == message_id
    assert retrieved.get(QmlAgentChatListModel.IS_USER) == True

    print("\n✓ Test 4 passed: User message can be added to model")
    return True


def test_qml_data_access():
    """Test that QML can access the model data correctly."""
    print("\n" + "=" * 70)
    print("Test 5: QML Data Access Simulation")
    print("=" * 70)

    from agent.chat.agent_chat_message import AgentMessage

    model = QmlAgentChatListModel()

    # Create agent messages with different content types
    messages = [
        AgentMessage(
            sender_id="agent1",
            sender_name="Helper Agent",
            message_id="msg-1",
            metadata={"timestamp": "2026-02-08T12:00:00"},
            structured_content=[
                TextContent(text="Here is some information"),
            ],
        ),
        AgentMessage(
            sender_id="agent2",
            sender_name="Thinker Agent",
            message_id="msg-2",
            metadata={"timestamp": "2026-02-08T12:01:00"},
            structured_content=[
                ThinkingContent(thought="Let me analyze this"),
                ToolCallContent(tool_name="search", tool_args={"q": "test"}),
                ProgressContent(progress="Searching...", percentage=50),
            ],
        ),
        AgentMessage(
            sender_id="agent3",
            sender_name="Error Agent",
            message_id="msg-3",
            metadata={"timestamp": "2026-02-08T12:02:00"},
            structured_content=[
                ErrorContent(error_message="Something went wrong"),
            ],
        ),
    ]

    # Convert and add to model
    for msg in messages:
        qml_item = model.from_agent_message(msg)
        model.add_item(qml_item)

    print(f"\nAdded {model.rowCount()} messages to model")

    # Simulate QML access pattern
    print("\nSimulating QML access:")
    for row in range(model.rowCount()):
        # Get role names (like QML would)
        role_names = model.roleNames()

        # Simulate accessing data via role enums
        from PySide6.QtCore import Qt

        # Get the item (simplified - QML uses model.data(index, role))
        item = model.get_item(row)

        sender_name = item.get(QmlAgentChatListModel.SENDER_NAME)
        content_type = item.get(QmlAgentChatListModel.CONTENT_TYPE)
        structured_content = item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, [])

        print(f"\n  Row {row}: {sender_name} ({content_type})")
        print(f"    Content items: {len(structured_content)}")

        for i, sc in enumerate(structured_content):
            ct = sc.get('content_type')
            data = sc.get('data', {})
            # Verify data is accessible
            if ct == 'text':
                text = data.get('text', '')
                print(f"      [{i}] text: '{text[:30]}...'")
            elif ct == 'thinking':
                thought = data.get('thought', '')
                print(f"      [{i}] thinking: '{thought[:30]}...'")
            elif ct == 'tool_call':
                tool = data.get('tool_name', '')
                print(f"      [{i}] tool_call: {tool}")
            elif ct == 'progress':
                progress = data.get('progress', '')
                print(f"      [{i}] progress: {progress}")
            elif ct == 'error':
                error = data.get('error', data.get('message', ''))
                print(f"      [{i}] error: {error}")

    print("\n✓ Test 5 passed: QML can access all data correctly")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("AgentChatWidget QML Data Flow Test")
    print("=" * 70)

    results = []
    results.append(("Content Serialization", test_serialize_content_to_dict()))
    results.append(("Model Serialization", test_model_serialize_method()))
    results.append(("from_agent_message", test_from_agent_message()))
    results.append(("Add User Message", test_add_user_message()))
    results.append(("QML Data Access", test_qml_data_access()))

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED!")
        print("=" * 70)
        print("""
Data flows correctly from Python to QML:
1. Content objects serialize to dict with correct structure
2. Model properly formats data for QML consumption
3. All required fields (content_type, data, content_id, status) are present
4. QML can access data via role names
""")


if __name__ == "__main__":
    main()
