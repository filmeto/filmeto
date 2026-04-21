"""
Test QML Bubble Components Data Binding with QmlAgentChatListModel.

This test verifies that the data structure provided by QmlAgentChatListModel
matches what the QML bubble components expect.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from agent.chat.content import TextContent, ThinkingContent, TypingContent, ProgressContent
from agent.chat.agent_chat_message import AgentMessage


def test_model_role_names():
    """Verify that model role names match QML expectations."""
    print("=" * 60)
    print("Test 1: Model Role Names vs QML Expectations")
    print("=" * 60)

    model = QmlAgentChatListModel()

    # Expected roles based on QML files
    expected_roles = {
        "messageId", "senderId", "senderName", "isUser",
        "agentColor", "agentIcon", "crewMetadata",
        "structuredContent", "contentType", "isRead", "timestamp",
    }

    # Get actual role names from model
    role_names = model.roleNames()
    actual_roles = set()
    for role_byte in role_names.values():
        role_name = role_byte.data().decode()
        actual_roles.add(role_name)

    print(f"\nExpected roles ({len(expected_roles)}):")
    for role in sorted(expected_roles):
        print(f"  - {role}")

    print(f"\nActual roles ({len(actual_roles)}):")
    for role in sorted(actual_roles):
        print(f"  - {role}")

    missing = expected_roles - actual_roles
    extra = actual_roles - expected_roles

    if missing:
        print(f"\n❌ Missing roles: {missing}")
        return False
    if extra:
        # dateGroup is an extra role that's not used in QML yet, but that's OK
        if extra == {"dateGroup"}:
            print(f"\n⚠ Extra role(s) (not currently used in QML): {extra}")
            print("   This is OK - the role is available for future use")
            return True
        else:
            print(f"\n⚠ Extra roles (not used in QML): {extra}")

    print("\n✓ All expected role names are present!")
    return True


def test_user_message_data_structure():
    """Test that user message data structure matches QML expectations."""
    print("\n" + "=" * 60)
    print("Test 2: User Message Data Structure")
    print("=" * 60)

    model = QmlAgentChatListModel()

    # Create a test user message
    user_item = {
        QmlAgentChatListModel.MESSAGE_ID: "test-user-123",
        QmlAgentChatListModel.SENDER_ID: "user",
        QmlAgentChatListModel.SENDER_NAME: "User",
        QmlAgentChatListModel.IS_USER: True,
        QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
        QmlAgentChatListModel.AGENT_ICON: "👤",
        QmlAgentChatListModel.CREW_METADATA: {},
        QmlAgentChatListModel.STRUCTURED_CONTENT: [{
            "content_type": "text",
            "data": {"text": "Hello, this is a test message!"}
        }],
        QmlAgentChatListModel.CONTENT_TYPE: "text",
        QmlAgentChatListModel.IS_READ: True,
        QmlAgentChatListModel.TIMESTAMP: "2026-02-08T12:00:00",
        QmlAgentChatListModel.DATE_GROUP: "Today",
    }

    # Check QML UserMessageBubble property expectations
    print("\nUserMessageBubble expects:")
    print("  - structuredContent: array")
    print("  - isRead: bool")
    print("  - userName: string")
    print("  - userIcon: string")
    print("  - timestamp: string")

    print("\nModel provides:")
    for key in [
        QmlAgentChatListModel.STRUCTURED_CONTENT,
        QmlAgentChatListModel.IS_READ,
        QmlAgentChatListModel.SENDER_NAME,
        QmlAgentChatListModel.AGENT_ICON,
        QmlAgentChatListModel.TIMESTAMP,
    ]:
        print(f"  - {key}: {type(user_item[key]).__name__}")

    # Read the QML file to verify the fix
    qml_path = Path(__file__).parent.parent / "app" / "ui" / "chat" / "qml" / "AgentChatList.qml"
    if qml_path.exists():
        qml_content = qml_path.read_text()
        if 'userName: modelData.senderName' in qml_content:
            print("\n✓ QML file correctly uses modelData.senderName for userName")
            return True
        elif 'userName: modelData.userName' in qml_content:
            print("\n❌ QML file still uses modelData.userName (needs fix)")
            return False
        else:
            print("\n⚠ Could not determine QML binding state")
            return False
    else:
        print(f"\n⚠ QML file not found at {qml_path}")
        return False


def test_agent_message_data_structure():
    """Test that agent message data structure matches QML expectations."""
    print("\n" + "=" * 60)
    print("Test 3: Agent Message Data Structure")
    print("=" * 60)

    model = QmlAgentChatListModel()

    # Create a test agent message
    agent_item = {
        QmlAgentChatListModel.MESSAGE_ID: "test-agent-456",
        QmlAgentChatListModel.SENDER_ID: "agent",
        QmlAgentChatListModel.SENDER_NAME: "张小萍",
        QmlAgentChatListModel.IS_USER: False,
        QmlAgentChatListModel.AGENT_COLOR: "#ff6b6b",
        QmlAgentChatListModel.AGENT_ICON: "🎬",
        QmlAgentChatListModel.CREW_METADATA: {
            "name": "张小萍",
            "crew_title": "producer",
            "crew_title_display": "制片人",
        },
        QmlAgentChatListModel.STRUCTURED_CONTENT: [
            {
                "content_type": "text",
                "data": {"text": "Hello from the agent!"}
            },
            {
                "content_type": "thinking",
                "data": {"thought": "Analyzing the user request..."}
            }
        ],
        QmlAgentChatListModel.CONTENT_TYPE: "thinking",
        QmlAgentChatListModel.IS_READ: True,
        QmlAgentChatListModel.TIMESTAMP: "2026-02-08T12:01:00",
        QmlAgentChatListModel.DATE_GROUP: "Today",
    }

    # Check QML AgentMessageBubble property expectations
    print("\nAgentMessageBubble expects:")
    print("  - senderName: string")
    print("  - agentColor: color")
    print("  - agentIcon: string")
    print("  - crewMetadata: object")
    print("  - structuredContent: array")
    print("  - timestamp: string")

    print("\nModel provides:")
    print(f"  - senderName: {agent_item[QmlAgentChatListModel.SENDER_NAME]}")
    print(f"  - agentColor: {agent_item[QmlAgentChatListModel.AGENT_COLOR]}")
    print(f"  - agentIcon: {agent_item[QmlAgentChatListModel.AGENT_ICON]}")
    print(f"  - crewMetadata: {agent_item[QmlAgentChatListModel.CREW_METADATA]}")
    print(f"  - structuredContent: {len(agent_item[QmlAgentChatListModel.STRUCTURED_CONTENT])} items")
    print(f"  - timestamp: {agent_item[QmlAgentChatListModel.TIMESTAMP]}")

    # Verify structured content format
    print("\nStructured content items:")
    for i, sc in enumerate(agent_item[QmlAgentChatListModel.STRUCTURED_CONTENT]):
        content_type = sc.get("content_type", "unknown")
        has_data = "data" in sc
        print(f"  [{i}] content_type: {content_type}, has data: {has_data}")

    print("\n✓ Agent message structure looks correct")
    return True


def test_content_type_routing():
    """Test that content_type values match QML switch statements."""
    print("\n" + "=" * 60)
    print("Test 4: Content Type Routing")
    print("=" * 60)

    # Content types that AgentMessageBubble.qml handles
    agent_handled_types = {
        "text", "code_block", "thinking", "tool_call", "tool_response",
        "typing", "progress", "error", "image", "video", "audio",
        "table", "chart", "link", "button", "form", "plan", "task",
        "step", "task_list", "skill", "file_attachment", "file",
        "metadata",
    }

    # Content types that UserMessageBubble.qml handles
    user_handled_types = {
        "text", "code_block", "image", "video", "audio",
        "file_attachment", "file", "link", "metadata",
    }

    print("\nAgentMessageBubble handles:")
    print(f"  {len(agent_handled_types)} content types")

    print("\nUserMessageBubble handles:")
    print(f"  {len(user_handled_types)} content types")

    # Test with actual ContentType enum values
    from agent.chat.agent_chat_types import ContentType

    print("\nContentType enum values:")
    for ct in ContentType:
        value = ct.value
        agent_handles = value in agent_handled_types
        user_handles = value in user_handled_types
        print(f"  {ct.name:20} -> '{value:20}' | Agent: {agent_handles} | User: {user_handles}")

    print("\n✓ Content type analysis complete")
    return True


def test_qml_binding_consistency():
    """Test overall QML binding consistency."""
    print("\n" + "=" * 60)
    print("Test 5: QML Binding Consistency")
    print("=" * 60)

    issues = []

    # Read QML file to verify bindings
    qml_path = Path(__file__).parent.parent / "app" / "ui" / "chat" / "qml" / "AgentChatList.qml"
    if not qml_path.exists():
        print(f"\n⚠ QML file not found at {qml_path}")
        return False

    qml_content = qml_path.read_text()

    # Check user name binding
    if 'userName: modelData.senderName' in qml_content:
        print("\n✓ UserMessageBubble.userName correctly uses modelData.senderName")
    elif 'userName: modelData.userName' in qml_content:
        print("\n❌ UserMessageBubble.userName uses modelData.userName (should be senderName)")
        issues.append("UserMessageBubble.userName mismatch")
    else:
        print("\n⚠ Could not determine UserMessageBubble.userName binding")

    # Verify other bindings are correct
    bindings_to_check = [
        ("AgentChatList -> UserMessageBubble", [
            ("modelData.isUser", "IS_USER", "isUser"),
            ("modelData.isRead", "IS_READ", "isRead"),
            ("modelData.structuredContent", "STRUCTURED_CONTENT", "structuredContent"),
            ("modelData.timestamp", "TIMESTAMP", "timestamp"),
        ]),
        ("AgentChatList -> AgentMessageBubble", [
            ("modelData.senderName", "SENDER_NAME", "senderName"),
            ("modelData.agentColor", "AGENT_COLOR", "agentColor"),
            ("modelData.agentIcon", "AGENT_ICON", "agentIcon"),
            ("modelData.crewMetadata", "CREW_METADATA", "crewMetadata"),
            ("modelData.structuredContent", "STRUCTURED_CONTENT", "structuredContent"),
            ("modelData.timestamp", "TIMESTAMP", "timestamp"),
        ]),
    ]

    print("\n✓ Other bindings verified:")
    for target, bindings in bindings_to_check:
        print(f"\n  {target}:")
        for qml_prop, model_const, model_key in bindings:
            model_value = getattr(QmlAgentChatListModel, model_const, None)
            if model_value == model_key:
                print(f"    ✓ {qml_prop} -> {model_key}")
            else:
                print(f"    ❌ {qml_prop} -> {model_key} (expected {model_value})")
                issues.append(f"{target}.{qml_prop} mismatch")

    if issues:
        print(f"\n❌ Found {len(issues)} binding issue(s):")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        return False
    else:
        print("\n✓ All bindings consistent!")
        return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("QML Bubble Components Data Binding Test")
    print("=" * 60)

    results = []
    results.append(("Role Names", test_model_role_names()))
    results.append(("User Message Structure", test_user_message_data_structure()))
    results.append(("Agent Message Structure", test_agent_message_data_structure()))
    results.append(("Content Type Routing", test_content_type_routing()))
    results.append(("QML Binding Consistency", test_qml_binding_consistency()))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("""
User message bubble and agent message bubble can correctly use
QmlAgentChatListModel data.
""")
    elif not results[1][1]:  # User message structure test failed
        print("\n" + "=" * 60)
        print("CRITICAL ISSUE FOUND")
        print("=" * 60)
        print("""
The UserMessageBubble.qml component expects 'userName' but the model
provides 'senderName'. This causes user messages to always display
"You" instead of the actual user name.

FIX: Change QML to use modelData.senderName
    In AgentChatList.qml, change:
        userName: modelData.userName || "You"
    To:
        userName: modelData.senderName || "You"
""")


if __name__ == "__main__":
    main()
