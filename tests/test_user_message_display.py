"""Debug test for user message display in QML chat list.

This test prints detailed debug information about the data being passed to QML.
"""

import sys
import uuid
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel, QTextEdit
from PySide6.QtCore import Qt

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.data.workspace import Workspace


class DebugTestWindow(QMainWindow):
    """Debug test window for user message display."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Message Display Debug Test")
        self.setGeometry(100, 100, 1200, 800)

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

        # Split into chat and debug areas
        from PySide6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left side: Chat widget
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        splitter.addWidget(self.chat_container)

        # Right side: Debug info
        debug_widget = QWidget()
        debug_layout = QVBoxLayout(debug_widget)
        splitter.addWidget(debug_widget)

        # Debug text area
        debug_label = QLabel("Debug Output:")
        debug_layout.addWidget(debug_label)

        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setStyleSheet("font-family: monospace; font-size: 11px; background: #1e1e1e; color: #d4d4d4;")
        debug_layout.addWidget(self.debug_text)

        # Control buttons (at bottom)
        control_layout = QHBoxLayout()
        self.load_button = QPushButton("Load History")
        self.load_button.clicked.connect(self._load_and_debug)
        self.add_button = QPushButton("Add User Message")
        self.add_button.clicked.connect(self._add_and_debug)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear)

        control_layout.addWidget(self.load_button)
        control_layout.addWidget(self.add_button)
        control_layout.addWidget(self.clear_button)
        layout.addLayout(control_layout)

        # Set splitter proportions
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

    def _setup_chat_widget(self):
        """Setup the chat list widget."""
        self.chat_widget = QmlAgentChatListWidget(self.workspace, self.chat_container)
        self.chat_layout.addWidget(self.chat_widget)

    def _log(self, message):
        """Add message to debug output."""
        self.debug_text.append(message)
        print(message)

    def _load_and_debug(self):
        """Load history and debug."""
        self._log("=" * 60)
        self._log("Loading history...")
        self._log("=" * 60)

        # Load history
        self.chat_widget.on_project_switched("demo")

        # Debug model data
        model = self.chat_widget._model
        row_count = model.rowCount()
        self._log(f"\n✓ Model row count: {row_count}")

        for i in range(row_count):
            item = model.get_item(i)
            if item:
                self._log(f"\n--- Row {i} ---")
                self._log(f"isUser: {item.get('isUser')}")
                self._log(f"senderName: {item.get('senderName')}")
                self._log(f"agentIcon: {repr(item.get('agentIcon'))}")
                self._log(f"structuredContent keys: {list(item.get('structuredContent', [{}])[0].keys()) if item.get('structuredContent') else 'empty'}")
                if item.get('structuredContent'):
                    sc = item['structuredContent'][0]
                    self._log(f"  content_type: {sc.get('content_type')}")
                    self._log(f"  data: {sc.get('data')}")

    def _add_and_debug(self):
        """Add user message and debug."""
        self._log("\n" + "=" * 60)
        self._log("Adding user message...")
        self._log("=" * 60)

        test_text = "测试用户消息 Test User Message 你好"
        message_id = self.chat_widget.add_user_message(test_text)

        self._log(f"\n✓ Added message ID: {message_id}")
        self._log(f"  Text: {test_text}")

        # Check what's in the model
        row_count = self.chat_widget._model.rowCount()
        last_item = self.chat_widget._model.get_item(row_count - 1)

        if last_item:
            self._log(f"\n--- Model Data for Last Row ---")
            self._log(json.dumps(last_item, indent=2, ensure_ascii=False))

            # Check QML model data()
            from PySide6.QtCore import QModelIndex
            index = model.index(row_count - 1, 0)

            # Try different role values
            self._log(f"\n--- QML Model Data Access ---")
            role_names = model.roleNames()
            self._log(f"Role names: {role_names}")

            for role_val, role_name in role_names.items():
                data = model.data(index, role_val)
                if data:
                    role_str = role_name.data().decode('utf-8')
                    self._log(f"  Role {role_val} ({role_str}): {data}")

    def _clear(self):
        """Clear debug and chat."""
        self.debug_text.clear()
        self.chat_widget.clear()
        self._log("Cleared")


def main():
    """Run the debug test."""
    app = QApplication(sys.argv)

    window = DebugTestWindow()
    window.show()

    print("=" * 60)
    print("User Message Display Debug Test")
    print("=" * 60)
    print("\nClick 'Load History' or 'Add User Message' to see debug info")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
