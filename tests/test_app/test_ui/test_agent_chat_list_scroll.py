"""Test widget for debugging AgentChatListWidget scroll issues.

This test module creates a simple interface to reproduce and debug
the scroll-to-black-screen issue in AgentChatListWidget.
"""

import sys
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QTextEdit, QSplitter
)
from PySide6.QtCore import Qt, QTimer

# Add project root to path
from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget
from app.data.workspace import Workspace

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ChatListTestWindow(QMainWindow):
    """Test window for AgentChatListWidget scrolling."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AgentChatListWidget Scroll Test")
        self.resize(1200, 800)

        # Setup workspace
        self.workspace = Workspace()
        # Use a test project
        self.workspace.open_project("/tmp/test_project")

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Control panel
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)

        # Splitter for list and log
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Chat list widget
        self.chat_list = AgentChatListWidget(self.workspace)
        splitter.addWidget(self.chat_list)

        # Log panel
        log_panel = self._create_log_panel()
        splitter.addWidget(log_panel)
        splitter.setSizes([800, 400])

        # Connect signals
        self.chat_list.list_view.viewport_scrolled.connect(self._on_scrolled)
        self.chat_list.list_view.viewport_resized.connect(self._on_resized)

        # Initial test data
        self._add_test_messages()

    def _create_control_panel(self):
        """Create control panel with buttons."""
        panel = QWidget()
        layout = QHBoxLayout(panel)

        # Add message button
        add_btn = QPushButton("Add 10 Messages")
        add_btn.clicked.connect(self._add_test_messages)
        layout.addWidget(add_btn)

        # Scroll to top button
        top_btn = QPushButton("Scroll to Top")
        top_btn.clicked.connect(self._scroll_to_top)
        layout.addWidget(top_btn)

        # Scroll to bottom button
        bottom_btn = QPushButton("Scroll to Bottom")
        bottom_btn.clicked.connect(self._scroll_to_bottom)
        layout.addWidget(bottom_btn)

        # Clear cache button
        clear_btn = QPushButton("Clear Cache")
        clear_btn.clicked.connect(self._clear_cache)
        layout.addWidget(clear_btn)

        # Dump cache button
        dump_btn = QPushButton("Dump Cache Info")
        dump_btn.clicked.connect(self._dump_cache_info)
        layout.addWidget(dump_btn)

        # Force refresh button
        refresh_btn = QPushButton("Force Refresh")
        refresh_btn.clicked.connect(self._force_refresh)
        layout.addWidget(refresh_btn)

        # Status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        return panel

    def _create_log_panel(self):
        """Create log panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        label = QLabel("Debug Log:")
        layout.addWidget(label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        return panel

    def _log(self, message: str):
        """Add message to log panel."""
        self.log_text.append(message)
        logger.debug(message)

    def _add_test_messages(self):
        """Add test messages to the chat list."""
        self._log("Adding 10 test messages...")

        for i in range(10):
            if i % 2 == 0:
                # User message
                self.chat_list.add_user_message(
                    f"This is test user message #{i+1}. "
                    f"It has some content that will wrap across multiple lines "
                    f"to test the scrolling behavior."
                )
            else:
                # Agent message
                self.chat_list.append_message(
                    f"TestAgent{i+1}",
                    f"This is test agent message #{i+1}. "
                    f"Agent messages can be longer and may contain different "
                    f"types of content that affect the rendering and scrolling."
                )

        self.status_label.setText(f"Status: Added messages (total: {self.chat_list._model.rowCount()})")
        self._log(f"Total messages in model: {self.chat_list._model.rowCount()}")

    def _scroll_to_top(self):
        """Scroll to top of the list."""
        scrollbar = self.chat_list.list_view.verticalScrollBar()
        scrollbar.setValue(0)
        self._log(f"Scrolled to top (value={scrollbar.value()})")

        # Check cache state
        QTimer.singleShot(100, self._dump_cache_info)

    def _scroll_to_bottom(self):
        """Scroll to bottom of the list."""
        self.chat_list.list_view.scrollToBottom()
        scrollbar = self.chat_list.list_view.verticalScrollBar()
        self._log(f"Scrolled to bottom (value={scrollbar.value()})")

        # Check cache state
        QTimer.singleShot(100, self._dump_cache_info)

    def _clear_cache(self):
        """Clear all caches."""
        self.chat_list._size_hint_cache.clear()
        self.chat_list._row_positions_cache.clear()
        self.chat_list._invalidate_positions_cache()
        self._log("Cleared all caches")
        self._dump_cache_info()

    def _dump_cache_info(self):
        """Dump cache information to log."""
        cache_size = len(self.chat_list._row_positions_cache)
        model_count = self.chat_list._model.rowCount()
        dirty = self.chat_list._positions_cache_dirty
        visible_count = len(self.chat_list._visible_widgets)

        scrollbar = self.chat_list.list_view.verticalScrollBar()
        scroll_value = scrollbar.value()
        scroll_max = scrollbar.maximum()

        info = (
            f"\n=== Cache Info ===\n"
            f"Model rows: {model_count}\n"
            f"Cache entries: {cache_size}\n"
            f"Cache dirty: {dirty}\n"
            f"Visible widgets: {visible_count}\n"
            f"Scroll: {scroll_value}/{scroll_max}\n"
        )

        # Show first few and last few cached positions
        if cache_size > 0:
            cached_rows = sorted(self.chat_list._row_positions_cache.keys())
            info += f"Cached rows (first/last 5): {cached_rows[:5]} ... {cached_rows[-5:]}\n"
        else:
            info += "WARNING: Cache is empty!\n"

        self._log(info)
        self.status_label.setText(f"Rows: {model_count}, Cache: {cache_size}, Widgets: {visible_count}")

    def _force_refresh(self):
        """Force a refresh of visible widgets."""
        self._log("Forcing refresh...")
        self.chat_list._refresh_visible_widgets()
        QTimer.singleShot(50, self._dump_cache_info)

    def _on_scrolled(self):
        """Handle scroll signal."""
        scrollbar = self.chat_list.list_view.verticalScrollBar()
        value = scrollbar.value()
        self._log(f"Scrolled to: {value}")

    def _on_resized(self):
        """Handle resize signal."""
        viewport = self.chat_list.list_view.viewport()
        self._log(f"Resized to: {viewport.width()}x{viewport.height()}")


def main():
    """Run the test application."""
    app = QApplication(sys.argv)

    window = ChatListTestWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
