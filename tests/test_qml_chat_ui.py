"""QML Chat List Test Application

A simple Qt application to test the QML-based chat list widget with history loading.
"""

import sys
import os
from pathlib import Path

# Add project root to path BEFORE any imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

# Set workspace environment
os.environ['WORKSPACE_PATH'] = str(Path.cwd() / "workspace")

# Import the QML widget
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.data.workspace import Workspace


class QmlChatTestWindow(QMainWindow):
    """Test window for QML chat list widget."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("QML Chat List Test - Demo Project")
        self.setGeometry(100, 100, 1000, 700)

        # Setup UI
        self.setup_ui()

        # Load workspace
        workspace_path = str(Path.cwd() / "workspace")
        self.workspace = Workspace(workspace_path, "demo", defer_heavy_init=True)

        # Create chat list widget
        self.chat_list = QmlAgentChatListWidget(self.workspace, self)

        # Add chat list to UI
        self.chat_list_layout.addWidget(self.chat_list)

        # Load test data
        QTimer.singleShot(500, self.load_test_messages)

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with horizontal splitter
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left side: Chat list
        self.chat_list_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_list_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Header
        header = QLabel("Chat History (Demo Project)")
        header.setStyleSheet("""
            QLabel {
                background-color: #2b2d30;
                color: #e0e0e0;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                border-bottom: 1px solid #404040;
            }
        """)
        chat_layout.addWidget(header)

        # Chat list will be added here (store reference to layout)
        self.chat_list_layout = chat_layout

        # Footer with info
        self.info_label = QLabel("Initializing...")
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: #2b2d30;
                color: #808080;
                padding: 8px;
                font-size: 11px;
                border-top: 1px solid #404040;
            }
        """)
        chat_layout.addWidget(self.info_label)

        splitter.addWidget(self.chat_list_container)

        # Right side: Controls and test log
        controls_container = QWidget()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        controls_layout.setSpacing(10)

        # Title
        title = QLabel("Test Controls")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0;")
        controls_layout.addWidget(title)

        # Test buttons
        btn_add_user = QPushButton("Add User Message")
        btn_add_user.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5ba0f2;
            }
        """)
        btn_add_user.clicked.connect(self.add_user_message)
        controls_layout.addWidget(btn_add_user)

        btn_add_agent = QPushButton("Add Agent Message")
        btn_add_agent.setStyleSheet("""
            QPushButton {
                background-color: #505254;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #606264;
            }
        """)
        btn_add_agent.clicked.connect(self.add_agent_message)
        controls_layout.addWidget(btn_add_agent)

        btn_clear = QPushButton("Clear Chat")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #d63031;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e04030;
            }
        """)
        btn_clear.clicked.connect(self.clear_chat)
        controls_layout.addWidget(btn_clear)

        btn_reload = QPushButton("Reload History")
        btn_reload.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5ba0f2;
            }
        """)
        btn_reload.clicked.connect(self.reload_history)
        controls_layout.addWidget(btn_reload)

        btn_scroll_bottom = QPushButton("Scroll to Bottom")
        btn_scroll_bottom.setStyleSheet("""
            QPushButton {
                background-color: #505254;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #606264;
            }
        """)
        btn_scroll_bottom.clicked.connect(self.scroll_to_bottom)
        controls_layout.addWidget(btn_scroll_bottom)

        # Test log
        log_label = QLabel("Test Log:")
        log_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0;")
        controls_layout.addWidget(log_label)

        self.test_log = QTextEdit()
        self.test_log.setReadOnly(True)
        self.test_log.setMaximumHeight(200)
        self.test_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #a0a0a0;
                border: 1px solid #404040;
                border-radius: 5px;
                padding: 8px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        controls_layout.addWidget(self.test_log)

        controls_layout.addStretch(1)

        # Stats section
        stats_label = QLabel("Statistics:")
        stats_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0;")
        controls_layout.addWidget(stats_label)

        self.stats_text = QLabel("Waiting for data...")
        self.stats_text.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #e0e0e0;
                padding: 10px;
                border: 1px solid #404040;
                border-radius: 5px;
                font-size: 11px;
            }
        """)
        controls_layout.addWidget(self.stats_text)

        splitter.addWidget(controls_container)

        # Set splitter sizes
        splitter.setSizes([700, 300])

        # Set stylesheet for main window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #252525;
            }
            QWidget {
                background-color: #252525;
                color: #e0e0e0;
            }
        """)

    def log(self, message: str):
        """Add a message to the test log."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.test_log.append(f"[{timestamp}] {message}")
        # Scroll to bottom
        self.test_log.verticalScrollBar().setValue(
            self.test_log.verticalScrollBar().maximum()
        )

    def update_stats(self):
        """Update the statistics display."""
        model = self.chat_list._model
        row_count = model.rowCount()

        user_count = 0
        agent_count = 0

        for i in range(row_count):
            item = model.get_item(i)
            if item:
                is_user = item.get(QmlAgentChatListModel.IS_USER)
                if is_user:
                    user_count += 1
                else:
                    agent_count += 1

        self.stats_text.setText(
            f"Total Messages: {row_count}\n"
            f"User Messages: {user_count}\n"
            f"Agent Messages: {agent_count}"
        )

        self.info_label.setText(f"Loaded {row_count} messages from demo project")

    def load_test_messages(self):
        """Load test messages from history."""
        self.log("Loading history from demo project...")

        try:
            # Simulate the widget loading its own history
            # The widget should already have loaded history in __init__
            model = self.chat_list._model
            row_count = model.rowCount()

            if row_count > 0:
                self.log(f"✓ Loaded {row_count} messages")
                self.update_stats()

                # Show first few messages
                self.log("Sample messages:")
                for i in range(min(5, row_count)):
                    item = model.get_item(i)
                    if item:
                        is_user = item.get(QmlAgentChatListModel.IS_USER)
                        sender = item.get(QmlAgentChatListModel.SENDER_NAME)
                        content = item.get(QmlAgentChatListModel.CONTENT)
                        content_preview = content[:40] + "..." if len(content) > 40 else content
                        self.log(f"  {i+1}. [{'USER' if is_user else sender}]: {content_preview}")
            else:
                self.log("⚠ No messages found in history")

        except Exception as e:
            self.log(f"✗ Error loading history: {e}")
            import traceback
            self.log(traceback.format_exc())

    def add_user_message(self):
        """Add a test user message."""
        import uuid
        from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

        message_id = str(uuid.uuid4())
        content = "This is a test user message sent at " + __import__('datetime').datetime.now().strftime("%H:%M:%S")

        item = {
            QmlAgentChatListModel.MESSAGE_ID: message_id,
            QmlAgentChatListModel.SENDER_ID: "user",
            QmlAgentChatListModel.SENDER_NAME: "Test User",
            QmlAgentChatListModel.IS_USER: True,
            QmlAgentChatListModel.CONTENT: content,
        }

        self.chat_list._model.add_item(item)
        self.chat_list._scroll_to_bottom()

        self.log(f"Added user message: {content}")
        self.update_stats()

    def add_agent_message(self):
        """Add a test agent message."""
        import uuid
        from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
        from agent.chat.content import TextContent

        message_id = str(uuid.uuid4())
        content = "This is a test agent message with some content to display."

        # Create with structured content
        from agent.chat.agent_chat_message import AgentMessage
        from agent.chat.agent_chat_types import MessageType

        agent_message = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id="test_agent",
            sender_name="测试助手",
            message_id=message_id,
            structured_content=[TextContent(text=content)],
        )

        from app.ui.chat.list.agent_chat_list_items import ChatListItem
        chat_item = ChatListItem(
            message_id=message_id,
            sender_id="test_agent",
            sender_name="测试助手",
            is_user=False,
            agent_message=agent_message,
            agent_color="#4a90e2",
            agent_icon="🤖",
        )

        qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)
        self.chat_list._model.add_item(qml_item)
        self.chat_list._scroll_to_bottom()

        self.log(f"Added agent message: {content}")
        self.update_stats()

    def clear_chat(self):
        """Clear all messages."""
        self.chat_list._model.clear()
        self.chat_list._agent_current_cards.clear()
        self.log("Cleared all messages")
        self.update_stats()

    def reload_history(self):
        """Reload history from file."""
        self.log("Reloading history...")

        # Clear current model
        self.chat_list._model.clear()

        # Reload history
        self.chat_list._load_recent_conversation()

        self.log("History reloaded")
        self.update_stats()

    def scroll_to_bottom(self):
        """Scroll chat list to bottom."""
        self.chat_list._scroll_to_bottom()
        self.log("Scrolled to bottom")


def main():
    """Run the test application."""
    app = QApplication(sys.argv)

    # Create test window
    window = QmlChatTestWindow()
    window.show()

    print("QML Chat List Test Application started")
    print("Check the window to see the chat list display")
    print("Use the test controls on the right to interact")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
