"""Enhanced test interface for history widget loading logic.

This test window provides comprehensive controls to test all aspects of
history message loading and display.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QHBoxLayout, QLabel, QTextEdit, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, QTimer
from qasync import QEventLoop

from app.ui.chat.agent_chat import AgentChatWidget
from app.data.workspace import Workspace
from agent.chat.history.agent_chat_history_service import AgentChatHistoryService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedHistoryTestWindow(QMainWindow):
    """Enhanced test window with comprehensive testing controls."""

    def __init__(self, workspace: Workspace):
        super().__init__()
        self.workspace = workspace
        self._setup_ui()

        # Initial update
        QTimer.singleShot(200, self._update_all_info)

    def _setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("History Loading Logic Test (Enhanced)")
        self.resize(1200, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # === Control Panel ===
        control_group = QGroupBox("Control Panel")
        control_layout = QGridLayout()

        # Reload tests
        btn_reload = QPushButton("Reload Recent")
        btn_reload.clicked.connect(self._test_reload_recent)
        control_layout.addWidget(btn_reload, 0, 0)

        btn_force_refresh = QPushButton("Force Refresh Widgets")
        btn_force_refresh.clicked.connect(self._test_force_refresh)
        control_layout.addWidget(btn_force_refresh, 0, 1)

        btn_scroll_bottom = QPushButton("Scroll to Bottom")
        btn_scroll_bottom.clicked.connect(self._test_scroll_bottom)
        control_layout.addWidget(btn_scroll_bottom, 0, 2)

        btn_scroll_top = QPushButton("Scroll to Top")
        btn_scroll_top.clicked.connect(self._test_scroll_top)
        control_layout.addWidget(btn_scroll_top, 0, 3)

        # Load older tests
        btn_load_older = QPushButton("Load Older (Page)")
        btn_load_older.clicked.connect(self._test_load_older)
        control_layout.addWidget(btn_load_older, 1, 0)

        btn_load_10 = QPushButton("Load 10 Older")
        btn_load_10.clicked.connect(lambda: self._test_load_n_older(10))
        control_layout.addWidget(btn_load_10, 1, 1)

        # Cache tests
        btn_clear_cache = QPushButton("Clear Cache")
        btn_clear_cache.clicked.connect(self._test_clear_cache)
        control_layout.addWidget(btn_clear_cache, 1, 2)

        btn_get_latest = QPushButton("Get Latest 5")
        btn_get_latest.clicked.connect(lambda: self._test_get_n_latest(5))
        control_layout.addWidget(btn_get_latest, 1, 3)

        # Revision tests
        btn_check_rev = QPushButton("Check Revision")
        btn_check_rev.clicked.connect(self._test_check_revision)
        control_layout.addWidget(btn_check_rev, 2, 0)

        btn_sim_add = QPushButton("Simulate Add Msg")
        btn_sim_add.clicked.connect(self._test_simulate_add)
        control_layout.addWidget(btn_sim_add, 2, 1)

        btn_reset = QPushButton("Reset All")
        btn_reset.clicked.connect(self._test_reset)
        control_layout.addWidget(btn_reset, 2, 2)

        btn_auto_test = QPushButton("Run Auto Test")
        btn_auto_test.clicked.connect(self._run_auto_test)
        control_layout.addWidget(btn_auto_test, 2, 3)

        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        # === Info Panel ===
        info_group = QGroupBox("Live Statistics")
        info_layout = QVBoxLayout()

        self.stats_label = QLabel("Initializing...")
        self.stats_label.setStyleSheet("QLabel { font-family: monospace; }")
        info_layout.addWidget(self.stats_label)

        self.model_info_label = QLabel("Model: N/A")
        self.model_info_label.setStyleSheet("QLabel { font-family: monospace; }")
        info_layout.addWidget(self.model_info_label)

        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # === Log Output ===
        log_group = QGroupBox("Test Log")
        log_layout = QVBoxLayout()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("QTextEdit { font-family: monospace; font-size: 11px; }")
        log_layout.addWidget(self.log_output)

        btn_clear_log = QPushButton("Clear Log")
        btn_clear_log.clicked.connect(self.log_output.clear)
        log_layout.addWidget(btn_clear_log)

        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # === Chat Widget ===
        chat_group = QGroupBox("Agent Chat Widget")
        chat_layout = QVBoxLayout()

        self.chat_widget = AgentChatWidget(self.workspace, self)
        chat_layout.addWidget(self.chat_widget)

        chat_group.setLayout(chat_layout)
        main_layout.addWidget(chat_group)

        # Setup update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_all_info)
        self._update_timer.start(2000)  # Update every 2 seconds

        self._log("Test interface initialized")

    def _log(self, message: str):
        """Add message to log output."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        logger.info(message)

    def _update_all_info(self):
        """Update all information displays."""
        try:
            workspace_path = self.workspace.workspace_path
            project_name = self.workspace.project_name

            history = AgentChatHistoryService.get_history(workspace_path, project_name)
            total_count = history.get_message_count()
            revision = history.revision

            chat_list = self.chat_widget.chat_history_widget
            model_count = chat_list._model.rowCount()
            visible_count = len(chat_list._visible_widgets)
            oldest_id = chat_list._oldest_message_id[:8] if chat_list._oldest_message_id else "None"
            latest_id = chat_list._latest_message_id[:8] if chat_list._latest_message_id else "None"
            has_more = chat_list._has_more_history

            scrollbar = chat_list.list_view.verticalScrollBar()
            scroll_pos = scrollbar.value()
            scroll_max = scrollbar.maximum()
            at_bottom = scroll_pos >= scroll_max - 10

            stats_text = (
                f"History Total: {total_count} | Model: {model_count} | "
                f"Visible: {visible_count} | Has More: {has_more} | "
                f"Rev: {revision}"
            )
            self.stats_label.setText(stats_text)

            model_info = (
                f"Oldest: {oldest_id}... | Latest: {latest_id}... | "
                f"Scroll: {scroll_pos}/{scroll_max} | At Bottom: {at_bottom}"
            )
            self.model_info_label.setText(model_info)

        except Exception as e:
            self.stats_label.setText(f"Error: {e}")

    # === Test Methods ===

    def _test_reload_recent(self):
        """Test: Reload recent conversation."""
        self._log("=== TEST: Reload Recent ===")
        chat_list = self.chat_widget.chat_history_widget
        chat_list._load_recent_conversation()
        QTimer.singleShot(100, self._update_all_info)

    def _test_force_refresh(self):
        """Test: Force refresh visible widgets."""
        self._log("=== TEST: Force Refresh ===")
        chat_list = self.chat_widget.chat_history_widget
        before = len(chat_list._visible_widgets)
        chat_list._refresh_visible_widgets()
        after = len(chat_list._visible_widgets)
        self._log(f"Widgets before: {before}, after: {after}")
        self._update_all_info()

    def _test_scroll_bottom(self):
        """Test: Scroll to bottom."""
        self._log("=== TEST: Scroll to Bottom ===")
        chat_list = self.chat_widget.chat_history_widget
        chat_list._user_at_bottom = True
        chat_list.list_view.scrollToBottom()
        chat_list._refresh_visible_widgets()
        QTimer.singleShot(100, self._update_all_info)

    def _test_scroll_top(self):
        """Test: Scroll to top."""
        self._log("=== TEST: Scroll to Top ===")
        chat_list = self.chat_widget.chat_history_widget
        chat_list.list_view.scrollToTop()
        QTimer.singleShot(100, self._update_all_info)

    def _test_load_older(self):
        """Test: Load older messages."""
        self._log("=== TEST: Load Older (Page) ===")
        chat_list = self.chat_widget.chat_history_widget
        before = chat_list._model.rowCount()
        chat_list._load_older_messages()
        QTimer.singleShot(100, lambda: self._log(f"Model before: {before}, after: {chat_list._model.rowCount()}"))
        QTimer.singleShot(100, self._update_all_info)

    def _test_load_n_older(self, n: int):
        """Test: Load N older messages."""
        self._log(f"=== TEST: Load {n} Older ===")
        chat_list = self.chat_widget.chat_history_widget
        workspace_path = self.workspace.workspace_path
        project_name = self.workspace.project_name

        if not chat_list._oldest_message_id:
            self._log("No oldest message ID, cannot load older")
            return

        # Get messages before oldest
        older_messages = AgentChatHistoryService.get_messages_before(
            workspace_path, project_name, chat_list._oldest_message_id, count=n
        )

        self._log(f"Retrieved {len(older_messages)} older messages")

        if older_messages:
            before = chat_list._model.rowCount()
            for msg_data in older_messages:
                chat_list._load_message_from_history(msg_data)
            after = chat_list._model.rowCount()
            self._log(f"Model before: {before}, after: {after}")

            # Update oldest message_id
            first_meta = older_messages[0].get("metadata", {})
            chat_list._oldest_message_id = first_meta.get("message_id")

        self._update_all_info()

    def _test_clear_cache(self):
        """Test: Clear history cache."""
        self._log("=== TEST: Clear Cache ===")
        workspace_path = self.workspace.workspace_path
        project_name = self.workspace.project_name
        AgentChatHistoryService.clear_cache(workspace_path, project_name)
        self._log("Cache cleared")
        self._update_all_info()

    def _test_get_n_latest(self, n: int):
        """Test: Get N latest messages from history."""
        self._log(f"=== TEST: Get {n} Latest ===")
        workspace_path = self.workspace.workspace_path
        project_name = self.workspace.project_name

        messages = AgentChatHistoryService.get_latest_messages(
            workspace_path, project_name, count=n
        )

        self._log(f"Retrieved {len(messages)} messages")
        for i, msg in enumerate(messages):
            metadata = msg.get("metadata", {})
            sender = metadata.get("sender_name", "Unknown")
            msg_id = metadata.get("message_id", "")[:8]
            self._log(f"  [{i+1}] {sender}: {msg_id}...")

        self._update_all_info()

    def _test_check_revision(self):
        """Test: Check revision counter."""
        self._log("=== TEST: Check Revision ===")
        workspace_path = self.workspace.workspace_path
        project_name = self.workspace.project_name

        history = AgentChatHistoryService.get_history(workspace_path, project_name)
        revision = history.revision

        chat_list = self.chat_widget.chat_history_widget
        known_rev = chat_list._last_known_revision

        self._log(f"History revision: {revision}")
        self._log(f"Widget known revision: {known_rev}")
        self._log(f"Has new data: {revision != known_rev}")

    def _test_simulate_add(self):
        """Test: Simulate adding a message (doesn't actually add)."""
        self._log("=== TEST: Simulate Add Message ===")
        self._log("This would trigger message_added signal")
        self._log("In real scenario, this would load new messages")

    def _test_reset(self):
        """Test: Reset chat list widget."""
        self._log("=== TEST: Reset All ===")
        chat_list = self.chat_widget.chat_history_widget
        chat_list.clear()
        self._log("Chat list cleared, reloading...")
        QTimer.singleShot(50, chat_list._load_recent_conversation)
        QTimer.singleShot(200, self._update_all_info)

    def _run_auto_test(self):
        """Run automatic test sequence."""
        self._log("=== RUNNING AUTOMATIC TEST SEQUENCE ===")
        self._log("This will test various loading scenarios...")

        def step1():
            self._log("[Step 1] Testing reload recent...")
            self._test_reload_recent()

        def step2():
            self._log("[Step 2] Testing scroll to bottom...")
            self._test_scroll_bottom()

        def step3():
            self._log("[Step 3] Testing force refresh...")
            self._test_force_refresh()

        def step4():
            self._log("[Step 4] Testing load 10 older...")
            self._test_load_n_older(10)

        def step5():
            self._log("[Step 5] Testing scroll to top...")
            self._test_scroll_top()

        def step6():
            self._log("[Step 6] Testing scroll back to bottom...")
            self._test_scroll_bottom()

        def final():
            self._log("=== AUTOMATIC TEST COMPLETE ===")
            self._update_all_info()

        QTimer.singleShot(0, step1)
        QTimer.singleShot(500, step2)
        QTimer.singleShot(1000, step3)
        QTimer.singleShot(1500, step4)
        QTimer.singleShot(2000, step5)
        QTimer.singleShot(2500, step6)
        QTimer.singleShot(3000, final)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("History Loading Test (Enhanced)")

    # Load dark style
    style_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "style", "dark_style.qss")
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        logger.warning(f"Could not load dark style: {e}")

    # Workspace configuration
    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    logger.info(f"Initializing workspace: {workspace_path}, project: {project_name}")

    try:
        workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

        window = EnhancedHistoryTestWindow(workspace)
        window.show()

        logger.info("Enhanced test window displayed")

        loop = QEventLoop(app)
        loop.run_forever()

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
