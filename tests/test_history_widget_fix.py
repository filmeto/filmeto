"""Test script to verify fix for history widget display issue.

The issue: Only first few messages are visible even though model has more messages.
Root cause: Viewport size calculation and widget refresh timing.

Fix: Ensure proper widget refresh after loading messages and showing window.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer
from qasync import QEventLoop

from app.ui.chat.agent_chat import AgentChatWidget
from app.data.workspace import Workspace
from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class FixedHistoryTestWindow(QMainWindow):
    """Test window with fix for history widget display."""

    def __init__(self, workspace: Workspace):
        super().__init__()
        self.workspace = workspace
        self._setup_ui()

        # Schedule post-load initialization
        QTimer.singleShot(100, self._post_load_init)
        QTimer.singleShot(500, self._update_stats)

    def _setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("History Widget Display Test (FIXED)")
        self.resize(1000, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Info panel
        info_panel = QWidget()
        info_layout = QHBoxLayout(info_panel)

        self.refresh_btn = QPushButton("Reload & Scroll")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        info_layout.addWidget(self.refresh_btn)

        self.force_refresh_btn = QPushButton("Force Refresh")
        self.force_refresh_btn.clicked.connect(self._on_force_refresh_clicked)
        info_layout.addWidget(self.force_refresh_btn)

        self.clear_btn = QPushButton("Clear Cache")
        self.clear_btn.clicked.connect(self._on_clear_cache_clicked)
        info_layout.addWidget(self.clear_btn)

        self.debug_btn = QPushButton("Debug Info")
        self.debug_btn.clicked.connect(self._show_debug_info)
        info_layout.addWidget(self.debug_btn)

        info_layout.addStretch()

        # Stats label
        self.stats_label = QLabel("Loading...")
        info_layout.addWidget(self.stats_label)

        layout.addWidget(info_panel)

        # Agent chat widget (main component)
        self.chat_widget = AgentChatWidget(self.workspace, self)
        layout.addWidget(self.chat_widget)

    def _post_load_init(self):
        """Initialize after window is shown and widgets are created."""
        logger.info("Post-load initialization...")

        # Ensure chat history widget is properly initialized
        chat_list = self.chat_widget.chat_history_widget

        # Force refresh of visible widgets
        chat_list._refresh_visible_widgets()

        # Get current state
        visible_count = len(chat_list._visible_widgets)
        model_count = chat_list._model.rowCount()

        logger.info(f"Model: {model_count} rows, Visible widgets: {visible_count}")

        # If no widgets are visible, force scroll to bottom after another delay
        if visible_count == 0 and model_count > 0:
            logger.info("No visible widgets, forcing scroll to bottom...")
            QTimer.singleShot(100, self._force_scroll_to_bottom)

    def _force_scroll_to_bottom(self):
        """Force scroll to bottom and refresh widgets."""
        chat_list = self.chat_widget.chat_history_widget

        # Set flag to ensure scrolling
        chat_list._user_at_bottom = True

        # Scroll to bottom
        chat_list.list_view.scrollToBottom()

        # Force refresh after scroll
        QTimer.singleShot(50, chat_list._refresh_visible_widgets)

        logger.info("Forced scroll to bottom and refresh")

        # Update stats
        QTimer.singleShot(100, self._update_stats)

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        logger.info("Reloading conversation...")
        chat_list = self.chat_widget.chat_history_widget
        chat_list._load_recent_conversation()

        # Force scroll after load
        QTimer.singleShot(100, self._force_scroll_to_bottom)

    def _on_force_refresh_clicked(self):
        """Handle force refresh button click."""
        chat_list = self.chat_widget.chat_history_widget
        chat_list._refresh_visible_widgets()
        self._update_stats()
        logger.info("Forced refresh")

    def _on_clear_cache_clicked(self):
        """Handle clear cache button click."""
        workspace_path = self.workspace.workspace_path
        project_name = self.workspace.project_name
        FastMessageHistoryService.clear_cache(workspace_path, project_name)
        logger.info("Cleared history cache")

    def _show_debug_info(self):
        """Show debug information."""
        chat_list = self.chat_widget.chat_history_widget

        viewport = chat_list.list_view.viewport()
        scrollbar = chat_list.list_view.verticalScrollBar()

        debug_info = f"""
Debug Information:
------------------
Model rows: {chat_list._model.rowCount()}
Visible widgets: {len(chat_list._visible_widgets)}
Viewport size: {viewport.width()}x{viewport.height()}
Scrollbar: value={scrollbar.value()}, max={scrollbar.maximum()}
Oldest message: {chat_list._oldest_message_id[:8] if chat_list._oldest_message_id else 'None'}...
Latest message: {chat_list._latest_message_id[:8] if chat_list._latest_message_id else 'None'}...
User at bottom: {chat_list._user_at_bottom}

Visible row range: {chat_list._get_visible_row_range()}

First 5 items in model:
"""
        for i in range(min(5, chat_list._model.rowCount())):
            item = chat_list._model.get_item(i)
            if item:
                has_widget = i in chat_list._visible_widgets
                debug_info += f"  [{i}] {item.sender_name} (widget={has_widget})\n"

        self.stats_label.setText(debug_info.replace('\n', ' | '))
        logger.info(debug_info)

    def _update_stats(self):
        """Update statistics display."""
        workspace_path = self.workspace.workspace_path
        project_name = self.workspace.project_name

        try:
            history = FastMessageHistoryService.get_history(workspace_path, project_name)
            total_count = history.get_message_count()

            chat_list = self.chat_widget.chat_history_widget
            model_count = chat_list._model.rowCount()
            visible_count = len(chat_list._visible_widgets)

            stats_text = (
                f"History: {total_count} | "
                f"Model: {model_count} | "
                f"Visible: {visible_count}"
            )

            self.stats_label.setText(stats_text)
            logger.info(stats_text)

        except Exception as e:
            self.stats_label.setText(f"Error: {e}")
            logger.error(f"Error updating stats: {e}")


def main():
    """Main entry point for the test application."""
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("History Widget Display Test (FIXED)")

    # Set dark style
    style_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "style", "dark_style.qss")
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
        logger.info(f"Loaded dark style")
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

        # Log history information
        history = FastMessageHistoryService.get_history(workspace_path, project_name)
        total_messages = history.get_message_count()

        logger.info(f"Total messages in history: {total_messages}")

        # Create and show main window
        window = FixedHistoryTestWindow(workspace)
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
