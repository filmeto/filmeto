"""Automated test for user message display.

Automatically loads history and adds a user message.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import QTimer, Qt

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.data.workspace import Workspace


class AutoTestWindow(QMainWindow):
    """Automated test window for user message display."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Test - User Message Display")
        self.setGeometry(100, 100, 1000, 700)

        # Create workspace with demo project
        workspace_path = str(project_root / "workspace")
        project_name = "demo"
        self.workspace = Workspace(workspace_path, project_name, defer_heavy_init=True)

        # Setup UI
        self._setup_ui()

        # Setup chat widget
        self._setup_chat_widget()

        # Auto-run test after QML loads
        QTimer.singleShot(2000, self._run_auto_test)

    def _setup_ui(self):
        """Setup the UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Header
        self.info_label = QLabel("Automated Test - Loading...")
        self.info_label.setStyleSheet("padding: 8px; font-size: 13px;")
        layout.addWidget(self.info_label)

        # Chat widget area
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        layout.addWidget(self.chat_container, stretch=1)

        # Status
        self.status_label = QLabel("Starting...")
        self.status_label.setStyleSheet("color: #4a90e2; padding: 4px;")
        layout.addWidget(self.status_label)

    def _setup_chat_widget(self):
        """Setup the chat list widget."""
        self.chat_widget = QmlAgentChatListWidget(self.workspace, self.chat_container)
        self.chat_layout.addWidget(self.chat_widget)

    def _run_auto_test(self):
        """Run automated test."""
        print("\n" + "=" * 60)
        print("Starting Automated Test")
        print("=" * 60)

        # Step 1: Load history
        self.status_label.setText("Step 1: Loading history...")
        self.info_label.setText("Step 1: Loading history...")
        QApplication.processEvents()

        try:
            self.chat_widget.on_project_switched("demo")
            row_count = self.chat_widget._model.rowCount()
            print(f"✓ Step 1: Loaded {row_count} messages from history")

            # Check user messages
            user_count = 0
            for i in range(row_count):
                item = self.chat_widget._model.get_item(i)
                if item and item.get('isUser'):
                    user_count += 1
                    content = item.get('structuredContent', [{}])[0]
                    text = content.get('data', {}).get('text', '')
                    print(f"  User message {user_count}: {text[:40]}...")

            print(f"  Total user messages in history: {user_count}")

        except Exception as e:
            print(f"✗ Step 1 failed: {e}")
            import traceback
            traceback.print_exc()

        # Wait a bit
        QTimer.singleShot(1000, lambda: self._add_test_message())

    def _add_test_message(self):
        """Add a test user message."""
        self.status_label.setText("Step 2: Adding test user message...")
        self.info_label.setText("Step 2: Adding test user message...")
        QApplication.processEvents()

        try:
            test_text = "🔴 测试用户消息 Test User Message 你好 Hello"
            message_id = self.chat_widget.add_user_message(test_text)

            row_count = self.chat_widget._model.rowCount()
            print(f"\n✓ Step 2: Added test user message")
            print(f"  Message ID: {message_id[:8]}...")
            print(f"  Text: {test_text}")
            print(f"  Total messages in model: {row_count}")

            # Verify the message was added
            last_item = self.chat_widget._model.get_item(row_count - 1)
            if last_item:
                print(f"  isUser: {last_item.get('isUser')}")
                print(f"  senderName: {last_item.get('senderName')}")
                print(f"  agentIcon: {repr(last_item.get('agentIcon'))}")

            self.status_label.setText("✓ Test complete - Check if user message is visible")
            self.info_label.setText(f"Test complete - Total messages: {row_count}")

            print("\n" + "=" * 60)
            print("Test Complete - Please check the window:")
            print("  - User message should appear on the RIGHT")
            print("  - User message should have BLUE background")
            print("  - User message should show 'User' name and icon")
            print("  - Text should be readable with Chinese characters")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"✗ Step 2 failed: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {e}")


def main():
    """Run the automated test."""
    app = QApplication(sys.argv)

    window = AutoTestWindow()
    window.show()

    print("=" * 60)
    print("User Message Display - Automated Test")
    print("=" * 60)
    print("\nWaiting for QML to load...")
    print("Test will start automatically in 2 seconds\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
