"""Test loading messages from actual history file."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget


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
                print(f"⚠️ Failed to parse line: {e}")
                continue

    print(f"Loaded {len(messages)} messages from history file")
    return messages


def test_history_file_parsing():
    """Test parsing actual history file."""
    print("\n=== Test 1: History File Parsing ===")
    messages = load_history_file()

    if not messages:
        print("❌ No messages to test")
        return False

    # Show first few messages
    print(f"First message keys: {messages[0].keys()}")
    print(f"Message types: {set(m.get('message_type', 'unknown') for m in messages)}")
    print(f"Senders: {set(m.get('sender_name', 'unknown') for m in messages)}")

    return True


def test_build_items_from_history():
    """Test building ChatListItem from history."""
    print("\n=== Test 2: Build Items From History ===")

    messages = load_history_file()
    if not messages:
        return False

    # Filter to user and text messages (skip system metadata)
    test_messages = [
        m for m in messages[:20]
        if m.get('message_type') != 'system'
    ]

    print(f"Testing with {len(test_messages)} non-system messages")

    # Use the widget's _build_item_from_history method
    class MockWorkspace:
        def __init__(self):
            self.workspace_path = "/tmp/test"
            self.project_name = "demo"

        def get_project(self):
            return None

        def connect_project_switched(self, callback):
            pass

    # Temporarily patch BaseWorkspace to avoid initialization issues
    from app.ui import base_widget
    original_init = base_widget.BaseWidget.__init__

    def patched_init(self, workspace):
        self.workspace = workspace

    base_widget.BaseWidget.__init__ = patched_init

    try:
        widget = QmlAgentChatListWidget(MockWorkspace())

        built_items = []
        for msg in test_messages:
            item = widget._build_item_from_history(msg)
            if item:
                built_items.append(item)
                print(f"  ✓ Built item: {item.message_id[:8]}... from {item.sender_name}")

        print(f"\nBuilt {len(built_items)} items from {len(test_messages)} messages")

        if not built_items:
            print("❌ No items were built!")
            return False

        return True

    finally:
        # Restore original __init__
        base_widget.BaseWidget.__init__ = original_init


def test_qml_model_with_history():
    """Test QML model with history items."""
    print("\n=== Test 3: QML Model With History ===")

    messages = load_history_file()
    if not messages:
        return False

    # Find first user and first agent message
    user_msg = None
    agent_msg = None

    for msg in messages[:50]:
        if msg.get('sender_id') == 'user' and not user_msg:
            user_msg = msg
        elif msg.get('sender_id') != 'user' and msg.get('message_type') != 'system' and not agent_msg:
            agent_msg = msg

        if user_msg and agent_msg:
            break

    if not user_msg or not agent_msg:
        print("❌ Could not find test messages")
        return False

    print(f"User message: {user_msg.get('message_id', 'N/A')[:8]}...")
    print(f"Agent message: {agent_msg.get('message_id', 'N/A')[:8]}...")

    # Build items using the widget method
    class MockWorkspace:
        def __init__(self):
            self.workspace_path = "/tmp/test"
            self.project_name = "demo"

        def get_project(self):
            return None

        def connect_project_switched(self, callback):
            pass

    from app.ui import base_widget
    original_init = base_widget.BaseWidget.__init__

    def patched_init(self, workspace):
        self.workspace = workspace

    base_widget.BaseWidget.__init__ = patched_init

    try:
        widget = QmlAgentChatListWidget(MockWorkspace())

        user_item = widget._build_item_from_history(user_msg)
        agent_item = widget._build_item_from_history(agent_msg)

        if not user_item or not agent_item:
            print("❌ Failed to build items")
            return False

        # Convert to QML format
        user_qml = QmlAgentChatListModel.from_chat_list_item(user_item)
        agent_qml = QmlAgentChatListModel.from_chat_list_item(agent_item)

        # Add to model
        model = QmlAgentChatListModel()
        model.add_item(user_qml)
        model.add_item(agent_qml)

        print(f"Model row count: {model.rowCount()}")

        # Verify items
        item_0 = model.get_item(0)
        item_1 = model.get_item(1)

        print(f"Item 0 - Is User: {item_0.get(QmlAgentChatListModel.IS_USER)}")
        print(f"Item 0 - Content: {item_0.get(QmlAgentChatListModel.CONTENT)[:30]}...")

        print(f"Item 1 - Is User: {item_1.get(QmlAgentChatListModel.IS_USER)}")
        print(f"Item 1 - Sender: {item_1.get(QmlAgentChatListModel.SENDER_NAME)}")

        return True

    finally:
        base_widget.BaseWidget.__init__ = original_init


def main():
    print("=" * 60)
    print("History File Loading Test")
    print("=" * 60)

    tests = [
        test_history_file_parsing,
        test_build_items_from_history,
        test_qml_model_with_history,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    success = main()
    sys.exit(0 if success else 1)
