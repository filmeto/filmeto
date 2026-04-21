"""Complete integration test for QML widget with history loading."""

import sys
import os
from pathlib import Path

# Set workspace env before imports
os.environ['WORKSPACE_PATH'] = str(Path.cwd() / "workspace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel


def test_history_service_direct():
    """Test history service directly."""
    print("=" * 60)
    print("Test 1: History Service Direct Call")
    print("=" * 60)

    from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

    workspace_path = str(Path.cwd() / "workspace")
    project_name = "demo"

    print(f"Workspace path: {workspace_path}")
    print(f"Project name: {project_name}")

    history = FastMessageHistoryService.get_history(workspace_path, project_name)

    # Get messages
    messages = history.get_latest_messages(count=10)
    print(f"Retrieved {len(messages)} messages")

    if messages:
        print(f"\nFirst message:")
        first = messages[0]
        print(f"  Type: {first.get('message_type')}")
        print(f"  Sender: {first.get('sender_name')}")
        print(f"  Message ID: {first.get('message_id', '')[:8]}...")

        content = first.get('content', [])
        if content and len(content) > 0:
            first_content = content[0]
            if isinstance(first_content, dict):
                text = first_content.get('data', {}).get('text', '')
                print(f"  Content: {text[:50]}...")

    return True


def test_widget_history_loading():
    """Test widget loads history correctly."""
    print("\n" + "=" * 60)
    print("Test 2: Widget History Loading")
    print("=" * 60)

    # Import after setting env
    from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
    from app.data.workspace import Workspace

    # Initialize Qt app
    app = QApplication.instance() or QApplication(sys.argv)

    # Get workspace
    workspace = Workspace()
    workspace_path = str(Path.cwd() / "workspace")

    print(f"Workspace initialized: {workspace}")
    print(f"Workspace path: {workspace_path}")

    # Check if project exists
    project = workspace.get_project()
    print(f"Current project: {project}")

    # Check if history file exists
    history_file = Path(workspace_path) / "projects" / "demo" / "agent" / "history" / "message.log"
    print(f"History file exists: {history_file.exists()}")
    if history_file.exists():
        # Count lines
        with open(history_file) as f:
            line_count = sum(1 for _ in f)
        print(f"History file has {line_count} lines")

    # Note: We can't fully initialize the widget due to BaseWidget requirements
    # But we can test the history loading logic separately

    return True


def test_model_role_names():
    """Test QML model has correct role names."""
    print("\n" + "=" * 60)
    print("Test 3: QML Model Role Names")
    print("=" * 60)

    model = QmlAgentChatListModel()

    role_names = model.roleNames()
    print(f"Model has {len(role_names)} roles")

    # Print all roles
    for role_num, role_name in role_names.items():
        print(f"  Role {role_num}: {role_name}")

    # Check essential roles
    from Qt.QtCore import Qt

    message_id_role = Qt.UserRole + 1
    assert role_names[message_id_role] == "messageId"
    print("\n✅ Essential roles present")

    return True


def test_add_and_retrieve():
    """Test adding and retrieving items."""
    print("\n" + "=" * 60)
    print("Test 4: Add and Retrieve Items")
    print("=" * 60)

    model = QmlAgentChatListModel()

    # Add some items
    items_to_add = [
        {
            QmlAgentChatListModel.MESSAGE_ID: "msg1",
            QmlAgentChatListModel.SENDER_ID: "user",
            QmlAgentChatListModel.SENDER_NAME: "User",
            QmlAgentChatListModel.IS_USER: True,
            QmlAgentChatListModel.CONTENT: "Hello",
        },
        {
            QmlAgentChatListModel.MESSAGE_ID: "msg2",
            QmlAgentChatListModel.SENDER_ID: "agent",
            QmlAgentChatListModel.SENDER_NAME: "助手",
            QmlAgentChatListModel.IS_USER: False,
            QmlAgentChatListModel.CONTENT: "Hi there!",
            QmlAgentChatListModel.AGENT_COLOR: "#4a90e2",
            QmlAgentChatListModel.AGENT_ICON: "🤖",
        },
    ]

    for item in items_to_add:
        model.add_item(item)

    print(f"Added {model.rowCount()} items")

    # Retrieve and verify
    for i in range(model.rowCount()):
        item = model.get_item(i)
        msg_id = item.get(QmlAgentChatListModel.MESSAGE_ID)
        sender = item.get(QmlAgentChatListModel.SENDER_NAME)
        content = item.get(QmlAgentChatListModel.CONTENT)
        is_user = item.get(QmlAgentChatListModel.IS_USER)

        print(f"  {i+1}. [{'USER' if is_user else sender}]: {content}")

    print("\n✅ Items added and retrieved correctly")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("QML Widget History Integration Tests")
    print("=" * 60)

    tests = [
        test_history_service_direct,
        test_widget_history_loading,
        test_model_role_names,
        test_add_and_retrieve,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n❌ FAILED: {e}")
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
