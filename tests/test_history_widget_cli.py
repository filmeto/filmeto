"""Simple CLI test for history loading without GUI.

This test verifies that:
1. Workspace can be initialized
2. AgentChatHistoryService can load messages
3. AgentChatWidget can be created (without showing GUI)
"""

import sys
import os
import logging

# Set PYTHONPATH to find project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from app.ui.chat.agent_chat import AgentChatWidget
from app.data.workspace import Workspace
from agent.chat.history.agent_chat_history_service import AgentChatHistoryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_workspace_init():
    """Test workspace initialization."""
    print("\n" + "=" * 70)
    print("[TEST 1] Workspace Initialization")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    print(f"Workspace path: {workspace_path}")
    print(f"Project name: {project_name}")

    try:
        workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)
        print(f"✓ Workspace created successfully")
        print(f"  - Project path: {workspace.project_path}")
        return workspace
    except Exception as e:
        print(f"✗ Failed to create workspace: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_history_loading(workspace_path: str, project_name: str):
    """Test loading messages from history."""
    print("\n" + "=" * 70)
    print("[TEST 2] History Loading")
    print("=" * 70)

    try:
        history = AgentChatHistoryService.get_history(workspace_path, project_name)
        total_count = history.get_message_count()
        latest_info = history.get_latest_message_info()
        revision = history.revision

        print(f"✓ History loaded successfully")
        print(f"  - Total messages: {total_count}")
        print(f"  - Revision: {revision}")

        if latest_info:
            print(f"  - Latest message ID: {latest_info.get('message_id')}")

        # Load latest 5 messages
        messages = AgentChatHistoryService.get_latest_messages(
            workspace_path, project_name, count=5
        )

        print(f"\n  Latest {len(messages)} messages:")
        for i, msg in enumerate(messages):
            metadata = msg.get("metadata", {})
            sender = metadata.get("sender_name", "Unknown")
            msg_id = metadata.get("message_id", "")[:8]
            msg_type = metadata.get("message_type", "text")
            print(f"    [{i+1}] {sender} ({msg_type}): {msg_id}...")

        return True

    except Exception as e:
        print(f"✗ Failed to load history: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chat_widget_creation(workspace: Workspace):
    """Test AgentChatWidget creation."""
    print("\n" + "=" * 70)
    print("[TEST 3] AgentChatWidget Creation")
    print("=" * 70)

    try:
        # Create QApplication if needed
        if not QApplication.instance():
            app = QApplication(sys.argv)
        else:
            app = QApplication.instance()

        # Create chat widget
        chat_widget = AgentChatWidget(workspace)

        print(f"✓ AgentChatWidget created successfully")

        # Check internal components
        print(f"  - Has chat_history_widget: {hasattr(chat_widget, 'chat_history_widget')}")
        print(f"  - Has plan_widget: {hasattr(chat_widget, 'plan_widget')}")
        print(f"  - Has prompt_input_widget: {hasattr(chat_widget, 'prompt_input_widget')}")

        # Check model row count after loading
        model = chat_widget.chat_history_widget._model
        row_count = model.rowCount()
        print(f"  - Model row count: {row_count}")

        # Check message tracking
        oldest_id = chat_widget.chat_history_widget._oldest_message_id
        latest_id = chat_widget.chat_history_widget._latest_message_id
        print(f"  - Oldest message ID: {oldest_id[:8] if oldest_id else 'N/A'}...")
        print(f"  - Latest message ID: {latest_id[:8] if latest_id else 'N/A'}...")

        return True

    except Exception as e:
        print(f"✗ Failed to create AgentChatWidget: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("HISTORY WIDGET CLI TEST")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    # Test 1: Workspace initialization
    workspace = test_workspace_init()
    if not workspace:
        print("\n✗ TEST FAILED: Could not initialize workspace")
        return False

    # Test 2: History loading
    if not test_history_loading(workspace_path, project_name):
        print("\n✗ TEST FAILED: Could not load history")
        return False

    # Test 3: Chat widget creation
    if not test_chat_widget_creation(workspace):
        print("\n✗ TEST FAILED: Could not create chat widget")
        return False

    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nTo run the GUI test, execute:")
    print("  python tests/test_history_widget_display.py")
    print()

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
