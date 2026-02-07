"""Test script for displaying chat history from workspace using AgentChatWidget.

This test creates a Qt window with AgentChatWidget to display historical messages
loaded from workspace/projects/demo/agent/history directory.
"""

import sys
import os
import logging

# Set PYTHONPATH to find project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer
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


class HistoryTestWindow(QMainWindow):
    """Test window for displaying chat history using AgentChatWidget."""

    def __init__(self, workspace: Workspace):
        super().__init__()
        self.workspace = workspace
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("History Widget Display Test")
        self.resize(1000, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Info panel
        info_panel = QWidget()
        info_layout = QHBoxLayout(info_panel)

        workspace_label = QLabel(f"Workspace: {self.workspace.workspace_path}")
        project_label = QLabel(f"Project: {self.workspace.project_name}")

        info_layout.addWidget(workspace_label)
        info_layout.addWidget(project_label)
        info_layout.addStretch()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh History")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        info_layout.addWidget(self.refresh_btn)

        # Clear button
        self.clear_btn = QPushButton("Clear Cache")
        self.clear_btn.clicked.connect(self._on_clear_cache_clicked)
        info_layout.addWidget(self.clear_btn)

        # Load older button
        self.load_older_btn = QPushButton("Load Older")
        self.load_older_btn.clicked.connect(self._on_load_older_clicked)
        info_layout.addWidget(self.load_older_btn)

        layout.addWidget(info_panel)

        # Stats label
        self.stats_label = QLabel("Ready")
        layout.addWidget(self.stats_label)

        # Agent chat widget (main component)
        self.chat_widget = AgentChatWidget(self.workspace, self)
        layout.addWidget(self.chat_widget)

        # Connect signal for reference clicks
        self.chat_widget.chat_history_widget.reference_clicked.connect(self._on_reference_clicked)

        # Update stats after initial load
        QTimer.singleShot(500, self._update_stats)

    def _on_refresh_clicked(self):
        """Handle refresh button click - reload conversation."""
        logger.info("Refreshing conversation...")
        self.chat_widget.chat_history_widget._load_recent_conversation()
        QTimer.singleShot(100, self._update_stats)

    def _on_clear_cache_clicked(self):
        """Handle clear cache button click."""
        workspace_path = self.workspace.workspace_path
        project_name = self.workspace.project_name
        AgentChatHistoryService.clear_cache(workspace_path, project_name)
        logger.info("Cleared history cache")
        self._update_stats()

    def _on_load_older_clicked(self):
        """Handle load older button click."""
        self.chat_widget.chat_history_widget._load_older_messages()
        QTimer.singleShot(100, self._update_stats)

    def _on_reference_clicked(self, ref_type: str, ref_id: str):
        """Handle reference click in chat history."""
        logger.info(f"Reference clicked: {ref_type} / {ref_id}")
        self.stats_label.setText(f"Reference clicked: {ref_type} / {ref_id}")

    def _update_stats(self):
        """Update statistics display."""
        workspace_path = self.workspace.workspace_path
        project_name = self.workspace.project_name

        try:
            history = AgentChatHistoryService.get_history(workspace_path, project_name)
            total_count = history.get_message_count()
            latest_info = history.get_latest_message_info()
            revision = history.revision

            model_count = self.chat_widget.chat_history_widget._model.rowCount()
            oldest_id = self.chat_widget.chat_history_widget._oldest_message_id
            latest_id = self.chat_widget.chat_history_widget._latest_message_id

            stats_text = (
                f"History: {total_count} messages | "
                f"Model: {model_count} loaded | "
                f"Revision: {revision}"
            )
            if latest_info:
                stats_text += f" | Latest: {latest_info.get('message_id', 'N/A')[:8]}..."

            self.stats_label.setText(stats_text)
            logger.info(stats_text)

        except Exception as e:
            self.stats_label.setText(f"Error: {e}")
            logger.error(f"Error updating stats: {e}")


def main():
    """Main entry point for the test application."""
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("History Widget Display Test")

    # Set dark style
    style_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "style", "dark_style.qss")
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
        logger.info(f"Loaded dark style from {style_path}")
    except Exception as e:
        logger.warning(f"Could not load dark style: {e}")

    # Workspace configuration
    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    logger.info(f"Initializing workspace: {workspace_path}")
    logger.info(f"Project: {project_name}")

    try:
        # Create workspace instance
        workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

        # Log history information before showing UI
        history = AgentChatHistoryService.get_history(workspace_path, project_name)
        total_messages = history.get_message_count()
        latest_info = history.get_latest_message_info()

        logger.info(f"Total messages in history: {total_messages}")
        if latest_info:
            logger.info(f"Latest message: {latest_info.get('message_id')}")

        # Get latest messages for preview
        messages = AgentChatHistoryService.get_latest_messages(workspace_path, project_name, count=5)
        logger.info(f"Preview of {len(messages)} latest messages:")
        for i, msg in enumerate(messages):
            metadata = msg.get("metadata", {})
            sender = metadata.get("sender_name", "Unknown")
            msg_id = metadata.get("message_id", "")[:8]
            logger.info(f"  [{i+1}] {sender}: {msg_id}...")

        # Create and show main window
        window = HistoryTestWindow(workspace)
        window.show()

        logger.info("Test window displayed. Press Ctrl+C to exit.")

        # Use qasync event loop
        loop = QEventLoop(app)
        loop.run_forever()

    except Exception as e:
        logger.error(f"Error initializing test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
