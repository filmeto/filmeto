"""Simple test for user message display.

Loads real history and adds a user message to verify display.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.data.workspace import Workspace


class SimpleTestWindow(QMainWindow):
    """Simple test window for user message display."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Message Display Test")
        self.setGeometry(100, 100, 1000, 700)

        # Create workspace with demo project
        workspace_path = str(project_root / "workspace")
        project_name = "demo"
        self.workspace = Workspace(workspace_path, project_name, defer_heavy_init=True)

        # Setup UI
        self._setup_ui()

        # Setup chat widget
        self._setup_chat_widget()

    def _setup_ui(self):
        """Setup the UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Header
        self.info_label = QLabel("Testing user message display with real history data")
        self.info_label.setStyleSheet("padding: 8px; font-size: 13px;")
        layout.addWidget(self.info_label)

        # Chat widget area
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        layout.addWidget(self.chat_container, stretch=1)

        # Add control buttons
        control_layout = QHBoxLayout()
        self.load_button = QPushButton("Load History")
        self.load_button.clicked.connect(self._load_history)
        self.add_button = QPushButton("Add User Message")
        self.add_button.clicked.connect(self._add_user_message)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear)

        control_layout.addWidget(self.load_button)
        control_layout.addWidget(self.add_button)
        control_layout.addWidget(self.clear_button)
        layout.addLayout(control_layout)

        # Status bar
        self.status_label = QLabel("Ready - Click 'Load History' to start")
        self.status_label.setStyleSheet("color: #4a90e2; padding: 4px;")
        layout.addWidget(self.status_label)

    def _setup_chat_widget(self):
        """Setup the chat list widget."""
        self.chat_widget = QmlAgentChatListWidget(self.workspace, self.chat_container)
        self.chat_layout.addWidget(self.chat_widget)

    def _load_history(self):
        """Load history data."""
        try:
            self.status_label.setText("Loading history...")
            QApplication.processEvents()

            self.chat_widget.on_project_switched("demo")

            row_count = self.chat_widget._model.rowCount()
            self.status_label.setText(f"Loaded {row_count} messages from history")
            print(f"✓ Loaded {row_count} messages")

        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

    def _add_user_message(self):
        """Add a user message."""
        test_text = "测试用户消息 Test User Message 你好"
        message_id = self.chat_widget.add_user_message(test_text)

        row_count = self.chat_widget._model.rowCount()
        self.status_label.setText(f"Added user message (Total: {row_count})")
        print(f"✓ Added user message: {test_text[:30]}...")

    def _clear(self):
        """Clear chat."""
        self.chat_widget.clear()
        self.status_label.setText("Cleared")
        print("✓ Cleared")


def main():
    """Run the test."""
    app = QApplication(sys.argv)

    window = SimpleTestWindow()
    window.show()

    print("=" * 60)
    print("User Message Display Test")
    print("=" * 60)
    print("\nExpected behavior:")
    print("  - User messages appear on the RIGHT with blue background")
    print("  - User messages show 'User' name and icon")
    print("  - Chinese characters display correctly")
    print("\n" + "=" * 60)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
