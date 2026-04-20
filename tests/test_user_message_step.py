"""Step-by-step test for user message display.

Tests each component part individually.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton
from PySide6.QtCore import QTimer

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.data.workspace import Workspace


class StepTestWindow(QMainWindow):
    """Step-by-step test window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Step Test - User Message")
        self.setGeometry(100, 100, 1000, 700)

        # Create workspace
        workspace_path = str(project_root / "workspace")
        project_name = "demo"
        self.workspace = Workspace(workspace_path, project_name, defer_heavy_init=True)

        # Setup UI
        self._setup_ui()
        self._setup_chat_widget()

        # Run test after QML loads
        QTimer.singleShot(2000, self._run_test)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.info_label = QLabel("Testing...")
        layout.addWidget(self.info_label)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        layout.addWidget(self.chat_container, stretch=1)

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def _setup_chat_widget(self):
        self.chat_widget = QmlAgentChatListWidget(self.workspace, self.chat_container)
        self.chat_layout.addWidget(self.chat_widget)

    def _run_test(self):
        print("\n" + "=" * 60)
        print("Step-by-Step Test")
        print("=" * 60)

        # Step 1: Add a simple user message
        print("\n[Step 1] Adding simple user message...")
        self.info_label.setText("Step 1: Adding simple user message")
        QApplication.processEvents()

        msg1_id = self.chat_widget.add_user_message("Test 1")
        print(f"  Added: {msg1_id[:8]}...")

        # Wait and check
        QTimer.singleShot(2000, lambda: self._step_2())

    def _step_2(self):
        # Step 2: Add Chinese text
        print("\n[Step 2] Adding Chinese message...")
        self.info_label.setText("Step 2: Adding Chinese message")
        QApplication.processEvents()

        msg2_id = self.chat_widget.add_user_message("测试消息")
        print(f"  Added: {msg2_id[:8]}...")

        QTimer.singleShot(2000, lambda: self._step_3())

    def _step_3(self):
        # Step 3: Check model data
        print("\n[Step 3] Checking model data...")
        self.info_label.setText("Step 3: Checking model data")
        QApplication.processEvents()

        model = self.chat_widget._model
        row_count = model.rowCount()
        print(f"  Total rows: {row_count}")

        for i in range(row_count):
            item = model.get_item(i)
            if item and item.get('isUser'):
                print(f"  Row {i} (user):")
                print(f"    - senderName: {item.get('senderName')}")
                print(f"    - agentIcon: {repr(item.get('agentIcon'))}")
                print(f"    - isUser: {item.get('isUser')}")
                sc_list = item.get('structuredContent', [])
                print(f"    - structuredContent items: {len(sc_list)}")
                if sc_list:
                    sc = sc_list[0]
                    print(f"    - content_type: {sc.get('content_type')}")
                    print(f"    - text: {sc.get('data', {}).get('text', '')[:30]}...")

        self.info_label.setText(f"Test complete - {row_count} messages")
        print("\n" + "=" * 60)
        print("Please check if user messages are visible")
        print("=" * 60)


def main():
    app = QApplication(sys.argv)
    window = StepTestWindow()
    window.show()
    print("Starting step-by-step test...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
