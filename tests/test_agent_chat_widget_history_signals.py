"""GUI Test for AgentChatWidget history loading and signal-based new message auto-loading.

This test creates a GUI window that:
1. Loads existing historical messages from message.log
2. Displays the AgentChatListWidget with loaded messages
3. Has buttons to simulate new messages via signals
4. Shows real-time loading when new messages arrive via polling
"""

import sys
import os
import uuid
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QSplitter, QGroupBox
)
from PySide6.QtCore import Qt, QTimer

# Set PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace
from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import MessageType
from agent.chat.content import TextContent, ThinkingContent
from agent.chat.agent_chat_signals import AgentChatSignals
from agent.chat.history.agent_chat_history_listener import AgentChatHistoryListener
from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
import qasync


class TestChatWidgetWindow(QMainWindow):
    """Test window for AgentChatWidget with history and signal loading."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AgentChatWidget History & Signal Test")
        self.resize(1200, 800)

        # Setup workspace
        self.workspace_path = "/Users/classfoo/ai/filmeto/workspace"
        self.project_name = "demo"
        self.workspace = Workspace(self.workspace_path, self.project_name)

        # Setup signals
        self.signals = AgentChatSignals()
        self.history_listener = AgentChatHistoryListener(
            self.workspace_path,
            self.project_name,
            self.signals
        )
        self.history_listener.connect(self.signals)

        # Message counter for testing
        self._test_message_counter = 0

        # Event loop reference
        self._loop = None

        self._setup_ui()

        # Log history info on startup
        QTimer.singleShot(500, self._log_history_info)
        QTimer.singleShot(1000, self._setup_event_loop)

    def _setup_event_loop(self):
        """Setup asyncio event loop for Qt."""
        try:
            self._loop = qasync.QEventLoop()
            asyncio.set_event_loop(self._loop)
            self._log("Asyncio event loop setup complete")
        except Exception as e:
            self._log(f"Event loop setup: {e}")

    def _setup_ui(self):
        """Setup the UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title
        title = QLabel("AgentChatWidget - History & Signal Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Info label
        info_text = (
            f"Workspace: {self.workspace_path}\n"
            f"Project: {self.project_name}\n"
            "This test loads historical messages from message.log and can simulate new messages."
        )
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)

        # Splitter for chat list and controls
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left side: Chat list widget
        self.chat_list_widget = AgentChatListWidget(self.workspace)
        splitter.addWidget(self.chat_list_widget)

        # Right side: Control panel
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        splitter.addWidget(control_panel)

        # Group: Message Info
        info_group = QGroupBox("Message Info")
        info_group_layout = QVBoxLayout()
        info_group.setLayout(info_group_layout)

        self.message_info_label = QLabel("Messages will be loaded from history...")
        self.message_info_label.setWordWrap(True)
        self.message_info_label.setStyleSheet("padding: 5px;")
        info_group_layout.addWidget(self.message_info_label)

        self.refresh_info_btn = QPushButton("Refresh Info")
        self.refresh_info_btn.clicked.connect(self._log_history_info)
        info_group_layout.addWidget(self.refresh_info_btn)

        control_layout.addWidget(info_group)

        # Group: Simulate Messages
        sim_group = QGroupBox("Simulate New Messages (via Signals)")
        sim_group_layout = QVBoxLayout()
        sim_group.setLayout(sim_group_layout)

        self.user_msg_btn = QPushButton("Send User Message (via Signal)")
        self.user_msg_btn.clicked.connect(self._send_user_message_via_signal)
        sim_group_layout.addWidget(self.user_msg_btn)

        self.agent_msg_btn = QPushButton("Send Agent Message (via Signal)")
        self.agent_msg_btn.clicked.connect(self._send_agent_message_via_signal)
        sim_group_layout.addWidget(self.agent_msg_btn)

        self.thinking_msg_btn = QPushButton("Send Thinking Message (via Signal)")
        self.thinking_msg_btn.clicked.connect(self._send_thinking_message_via_signal)
        sim_group_layout.addWidget(self.thinking_msg_btn)

        self.multi_part_btn = QPushButton("Send Multi-Part Message (via Signal)")
        self.multi_part_btn.clicked.connect(self._send_multi_part_message_via_signal)
        sim_group_layout.addWidget(self.multi_part_btn)

        self.batch_btn = QPushButton("Send Batch of 5 Messages")
        self.batch_btn.clicked.connect(self._send_batch_messages)
        sim_group_layout.addWidget(self.batch_btn)

        control_layout.addWidget(sim_group)

        # Group: Polling Test
        poll_group = QGroupBox("Polling Test (Auto-load new messages)")
        poll_group_layout = QVBoxLayout()
        poll_group.setLayout(poll_group_layout)

        polling_info = QLabel(
            "The chat list widget polls for new messages every 500ms.\n"
            "Send messages via signals above and watch them auto-load!"
        )
        polling_info.setWordWrap(True)
        polling_info.setStyleSheet("color: #666; padding: 5px;")
        poll_group_layout.addWidget(polling_info)

        self.poll_count_label = QLabel("Messages detected: 0")
        self.poll_count_label.setStyleSheet("font-weight: bold; padding: 5px;")
        poll_group_layout.addWidget(self.poll_count_label)

        control_layout.addWidget(poll_group)

        # Group: Log
        log_group = QGroupBox("Event Log")
        log_group_layout = QVBoxLayout()
        log_group.setLayout(log_group_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_group_layout.addWidget(self.log_text)

        control_layout.addWidget(log_group)

        # Add stretch to push everything up
        control_layout.addStretch()

        # Set splitter sizes
        splitter.setSizes([800, 400])

        # Log initialization
        self._log("Test window initialized")
        self._log("Chat list widget created")
        self._log("Signals connected")

    def _log(self, message: str):
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.append(f"[{timestamp}] {message}")
        # Scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _log_history_info(self):
        """Log information about the history."""
        try:
            history = FastMessageHistoryService.get_history(
                self.workspace_path,
                self.project_name
            )

            active_count = history.storage.get_message_count()
            total_count = history.get_total_count()
            archive_count = total_count - active_count

            self._log(f"History Info:")
            self._log(f"  Active log messages: {active_count}")
            self._log(f"  Archive messages: {archive_count}")
            self._log(f"  Total messages: {total_count}")

            # Get some recent messages
            messages = FastMessageHistoryService.get_latest_messages(
                self.workspace_path,
                self.project_name,
                count=5
            )

            self._log(f"  Recent messages:")
            for msg in messages:
                metadata = msg.get("metadata", {})
                sender = metadata.get("sender_name", "Unknown")
                msg_type = metadata.get("message_type", "text")
                self._log(f"    - {sender}: {msg_type}")

            # Update info label
            model_count = self.chat_list_widget._model.rowCount()
            self.message_info_label.setText(
                f"Active log: {active_count} | Archives: {archive_count} | "
                f"Total: {total_count} | Loaded in UI: {model_count}"
            )

        except Exception as e:
            self._log(f"Error getting history info: {e}")

    async def _send_via_signal(self, message: AgentMessage):
        """Send a message via the signal system."""
        try:
            await self.signals.send_agent_message(message)
            self._log(f"Sent message via signal: {message.message_id}")
        except Exception as e:
            self._log(f"Error sending message via signal: {e}")

    @qasync.asyncSlot()
    async def _send_user_message_via_signal(self):
        """Send a user message via signal."""
        self._test_message_counter += 1
        message_id = f"test_user_{self._test_message_counter}_{uuid.uuid4().hex[:8]}"

        message = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id="user",
            sender_name="User",
            message_id=message_id,
            structured_content=[
                TextContent(text=f"Test user message #{self._test_message_counter} via signal")
            ]
        )

        await self._send_via_signal(message)

    @qasync.asyncSlot()
    async def _send_agent_message_via_signal(self):
        """Send an agent message via signal."""
        self._test_message_counter += 1
        message_id = f"test_agent_{self._test_message_counter}_{uuid.uuid4().hex[:8]}"

        message = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id="test_agent",
            sender_name="Test Agent",
            message_id=message_id,
            structured_content=[
                TextContent(text=f"Test agent message #{self._test_message_counter} via signal")
            ]
        )

        await self._send_via_signal(message)

    @qasync.asyncSlot()
    async def _send_thinking_message_via_signal(self):
        """Send a thinking message via signal."""
        self._test_message_counter += 1
        message_id = f"test_thinking_{self._test_message_counter}_{uuid.uuid4().hex[:8]}"

        message = AgentMessage(
            message_type=MessageType.THINKING,
            sender_id="test_agent",
            sender_name="Test Agent",
            message_id=message_id,
            structured_content=[
                ThinkingContent(
                    thought=f"Thinking about test #{self._test_message_counter}",
                    title="Test Thinking",
                    description=f"Test step {self._test_message_counter}"
                )
            ]
        )

        await self._send_via_signal(message)

    @qasync.asyncSlot()
    async def _send_multi_part_message_via_signal(self):
        """Send a multi-part message (text + thinking) via signal."""
        self._test_message_counter += 1
        message_id = f"test_multi_{self._test_message_counter}_{uuid.uuid4().hex[:8]}"

        # First send thinking
        thinking_msg = AgentMessage(
            message_type=MessageType.THINKING,
            sender_id="test_agent",
            sender_name="Test Agent",
            message_id=message_id,
            structured_content=[
                ThinkingContent(
                    thought=f"Thinking about multi-part message #{self._test_message_counter}",
                    title="Multi-Part Test",
                    description="Part 1: Thinking"
                )
            ]
        )

        # Then send text (both with same message_id, should be grouped)
        text_msg = AgentMessage(
            message_type=MessageType.TEXT,
            sender_id="test_agent",
            sender_name="Test Agent",
            message_id=message_id,
            structured_content=[
                TextContent(text=f"Multi-part message #{self._test_message_counter} response via signal")
            ]
        )

        await self._send_via_signal(thinking_msg)
        # Small delay before sending text
        await asyncio.sleep(0.1)
        await self._send_via_signal(text_msg)

    def _send_batch_messages(self):
        """Send a batch of 5 messages via signals."""
        for i in range(5):
            QTimer.singleShot(i * 200, self._send_agent_message_via_signal)

    def closeEvent(self, event):
        """Handle window close event."""
        self._log("Closing test window...")
        self.history_listener.disconnect()
        self.signals.stop()
        super().closeEvent(event)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)

    # Setup styling
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #ccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #4a90e2;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #357abd;
        }
        QPushButton:pressed {
            background-color: #2968a3;
        }
        QTextEdit {
            background-color: #fff;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-family: monospace;
            font-size: 11px;
        }
    """)

    window = TestChatWidgetWindow()
    window.show()

    # Use qasync to run Qt with asyncio event loop
    sys.exit(qasync.run(app.exec_()))


if __name__ == "__main__":
    main()
