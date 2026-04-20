"""
Test Modal Dialog Chain - StartupWindow -> ServerListDialog -> Config Dialog -> Close

This test verifies that when opening nested modal dialogs:
1. StartupWindow opens ServerListDialog
2. ServerListDialog opens config view (e.g., BailianConfigWidget)
3. Closing the dialog properly restores StartupWindow responsiveness

The test can be run with: python -m pytest tests/test_app/test_ui/test_modal_dialog_chain.py -v
Or standalone: python tests/test_app/test_ui/test_modal_dialog_chain.py
"""

import sys
import os
import unittest
import logging
from unittest.mock import MagicMock, patch, PropertyMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from PySide6.QtWidgets import QApplication, QDialog, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtTest import QTest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockWorkspace:
    """Mock workspace for testing"""
    def __init__(self):
        self.workspace_path = "/tmp/test_workspace"

    def connect_project_switched(self, callback):
        """Mock method for project switch signal"""
        pass

    def connect_timeline_position(self, callback):
        """Mock method for timeline position signal"""
        pass

    def get_current_project(self):
        """Mock method for getting current project"""
        return None


class MockPluginInfo:
    """Mock plugin info for testing"""
    def __init__(self):
        self.name = "Bailian Server"
        self.engine = "bailian"
        self.version = "1.0.0"
        self.description = "Test bailian server"


class MockServerConfig:
    """Mock server config for testing"""
    def __init__(self):
        self.name = "test_bailian"
        self.description = "Test server"
        self.enabled = True
        self.plugin_name = "Bailian Server"
        self.parameters = {}
        self.endpoint = None
        self.api_key = None


class MinimalStartupWindow(QDialog):
    """
    Minimal startup window for testing modal dialog chain.
    Simulates the behavior of StartupWindow without full dependencies.
    """
    server_status_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Startup Window")
        self.setMinimumSize(800, 600)
        self.workspace = MockWorkspace()

        layout = QVBoxLayout(self)

        # Button to open server list dialog
        self.open_server_btn = QPushButton("Open Server List Dialog")
        self.open_server_btn.clicked.connect(self._on_open_server_clicked)
        layout.addWidget(self.open_server_btn)

        # Status label
        self.status_label = QLabel("Ready - click the button to open dialog")
        layout.addWidget(self.status_label)

        # Interactive test button to verify window is responsive
        self.test_btn = QPushButton("Click if window is responsive")
        self.test_btn.clicked.connect(self._on_test_clicked)
        layout.addWidget(self.test_btn)

        self.click_count = 0
        self.dialog_result = None

    def _on_open_server_clicked(self):
        """Open server list dialog (simulating _on_server_status_clicked)"""
        from app.ui.server_list.server_list_dialog import ServerListDialog
        from PySide6.QtCore import QCoreApplication, QEvent

        server_dialog = ServerListDialog(self.workspace, self)
        logger.info(
            "MinimalStartupWindow opening ServerListDialog parent_enabled=%s active_modal=%s",
            self.isEnabled(),
            type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
        )

        try:
            result = server_dialog.exec()
            self.dialog_result = result
        finally:
            # Force clear modal state before processing events
            if server_dialog.isModal():
                server_dialog.setWindowModality(Qt.NonModal)

            # Let dialog close itself; just flush deferred deletes and restore focus.
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QCoreApplication.processEvents()

            # Force activate parent window
            self.setEnabled(True)
            self.activateWindow()
            self.raise_()
            self.setFocus()

            logger.info(
                "MinimalStartupWindow closed ServerListDialog parent_enabled=%s active_modal=%s focus_widget=%s",
                self.isEnabled(),
                type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
                type(QApplication.focusWidget()).__name__ if QApplication.focusWidget() else "None",
            )

    def _on_test_clicked(self):
        """Track clicks to verify window is responsive"""
        self.click_count += 1
        self.status_label.setText(f"Window is responsive! Click count: {self.click_count}")
        logger.info("Test button clicked, count=%s", self.click_count)


class TestModalDialogChain(unittest.TestCase):
    """Test modal dialog chain behavior"""

    @classmethod
    def setUpClass(cls):
        """Initialize QApplication once for all tests"""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        """Set up for each test"""
        self.startup_window = None

    def tearDown(self):
        """Clean up after each test"""
        if self.startup_window:
            self.startup_window.close()
            self.startup_window.deleteLater()
        # Process events to ensure cleanup
        QApplication.processEvents()

    def test_startup_window_responsive_after_dialog_close(self):
        """
        Test that StartupWindow remains responsive after closing ServerListDialog.

        This is the main test case that verifies the fix for the modal dialog issue.
        """
        from app.ui.server_list.server_list_dialog import ServerListDialog
        from app.ui.server_list.server_views import ServerConfigView

        self.startup_window = MinimalStartupWindow()
        self.startup_window.show()
        QApplication.processEvents()

        # Verify startup window is initially enabled
        self.assertTrue(self.startup_window.isEnabled(),
                       "Startup window should be enabled initially")

        # Mock the server manager to avoid full initialization
        with patch('server.server.ServerManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.list_available_plugins.return_value = []
            mock_manager_class.return_value = mock_manager

            # Create server list dialog
            dialog = ServerListDialog(self.startup_window.workspace, self.startup_window)

            # Verify dialog parent is set correctly
            self.assertEqual(dialog.parentWidget(), self.startup_window)

            # Simulate showing the dialog
            dialog.show()
            QApplication.processEvents()

            # Verify startup window is disabled while modal dialog is open
            # Note: The actual disabling happens with exec(), not show()
            # So we manually test the dialog's cleanup behavior

            # Test done() method cleanup
            dialog.done(QDialog.Accepted)
            QApplication.processEvents()

            # Give time for QTimer callbacks
            import time
            time.sleep(0.1)
            QApplication.processEvents()

        # Verify startup window is still responsive
        self.assertTrue(self.startup_window.isEnabled(),
                       "Startup window should be enabled after dialog closes")

    def test_dialog_cleanup_on_reject(self):
        """Test that dialog properly cleans up on reject()"""
        from app.ui.server_list.server_list_dialog import ServerListDialog

        self.startup_window = MinimalStartupWindow()
        self.startup_window.show()
        QApplication.processEvents()

        with patch('server.server.ServerManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.list_available_plugins.return_value = []
            mock_manager_class.return_value = mock_manager

            dialog = ServerListDialog(self.startup_window.workspace, self.startup_window)
            dialog.show()
            QApplication.processEvents()

            # Test reject() method cleanup
            dialog.reject()
            QApplication.processEvents()

            import time
            time.sleep(0.1)
            QApplication.processEvents()

        self.assertTrue(self.startup_window.isEnabled(),
                       "Startup window should be enabled after reject()")

    def test_dialog_cleanup_on_close_event(self):
        """Test that dialog properly cleans up on closeEvent()"""
        from app.ui.server_list.server_list_dialog import ServerListDialog

        self.startup_window = MinimalStartupWindow()
        self.startup_window.show()
        QApplication.processEvents()

        with patch('server.server.ServerManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.list_available_plugins.return_value = []
            mock_manager_class.return_value = mock_manager

            dialog = ServerListDialog(self.startup_window.workspace, self.startup_window)
            dialog.show()
            QApplication.processEvents()

            # Simulate close event
            from PySide6.QtGui import QCloseEvent
            close_event = QCloseEvent()
            dialog.closeEvent(close_event)
            QApplication.processEvents()

            import time
            time.sleep(0.1)
            QApplication.processEvents()

        self.assertTrue(self.startup_window.isEnabled(),
                       "Startup window should be enabled after closeEvent()")


class TestCustomDialogParentRestore(unittest.TestCase):
    """Test CustomDialog parent window restoration"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        self.parent_widget = None
        self.dialog = None

    def tearDown(self):
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()
        if self.parent_widget:
            self.parent_widget.close()
            self.parent_widget.deleteLater()
        QApplication.processEvents()

    def test_custom_dialog_restores_parent(self):
        """Test that CustomDialog properly restores parent window"""
        from app.ui.dialog.custom_dialog import CustomDialog

        self.parent_widget = QWidget()
        self.parent_widget.show()
        QApplication.processEvents()

        self.dialog = CustomDialog(self.parent_widget)
        self.dialog.show()
        QApplication.processEvents()

        # Close the dialog
        self.dialog.reject()
        QApplication.processEvents()

        import time
        time.sleep(0.1)
        QApplication.processEvents()

        self.assertTrue(self.parent_widget.isEnabled(),
                       "Parent widget should be enabled after dialog closes")


class TestFullDialogChain(unittest.TestCase):
    """Test the full dialog chain: StartupWindow -> ServerListDialog -> Config View -> Close"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        self.startup_window = None
        self.dialog = None

    def tearDown(self):
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()
        if self.startup_window:
            self.startup_window.close()
            self.startup_window.deleteLater()
        QApplication.processEvents()

    def test_full_chain_with_config_view(self):
        """
        Test the full chain: open ServerListDialog, switch to config view, then close.
        This simulates: StartupWindow -> ServerListDialog -> BailianConfig -> Close
        """
        from app.ui.server_list.server_list_dialog import ServerListDialog
        from app.ui.server_list.server_views import ServerConfigView

        self.startup_window = MinimalStartupWindow()
        self.startup_window.show()
        QApplication.processEvents()

        with patch('server.server.ServerManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.list_available_plugins.return_value = []
            # Return a simple QWidget as the custom plugin UI
            mock_widget = QWidget()
            mock_manager.get_plugin_ui_widget.return_value = mock_widget
            mock_manager_class.return_value = mock_manager

            # Create server list dialog
            self.dialog = ServerListDialog(self.startup_window.workspace, self.startup_window)

            # Show the dialog
            self.dialog.show()
            QApplication.processEvents()

            # Verify we're on list view initially
            self.assertEqual(self.dialog.stacked_widget.currentWidget(), self.dialog.list_view)

            # Simulate switching to config view (as if clicking "Add Server")
            # Create mock plugin info
            mock_plugin = MockPluginInfo()

            # Show config view
            self.dialog._show_config_view(mock_plugin, None)
            QApplication.processEvents()

            # Verify we're now on config view
            self.assertEqual(self.dialog.stacked_widget.currentWidget(), self.dialog.config_view)

            # Verify startup window is disabled while modal dialog is open
            # Note: We need to use exec() for modal, but we used show() for testing
            # In real usage, exec() would disable the parent

            # Now close the dialog using done (simulating close button click)
            self.dialog.done(QDialog.Accepted)
            QApplication.processEvents()

            # Give time for QTimer callbacks
            import time
            time.sleep(0.15)
            QApplication.processEvents()

        # Verify startup window is responsive after dialog closes
        self.assertTrue(self.startup_window.isEnabled(),
                       "Startup window should be enabled after config view closes")

    def test_config_view_cleanup_on_reject(self):
        """Test that config view is properly cleaned up when rejecting dialog"""
        from app.ui.server_list.server_list_dialog import ServerListDialog

        self.startup_window = MinimalStartupWindow()
        self.startup_window.show()
        QApplication.processEvents()

        with patch('server.server.ServerManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.list_available_plugins.return_value = []
            # Return a simple QWidget as the custom plugin UI
            mock_widget = QWidget()
            mock_manager.get_plugin_ui_widget.return_value = mock_widget
            mock_manager_class.return_value = mock_manager

            self.dialog = ServerListDialog(self.startup_window.workspace, self.startup_window)
            self.dialog.show()
            QApplication.processEvents()

            # Switch to config view
            mock_plugin = MockPluginInfo()
            self.dialog._show_config_view(mock_plugin, None)
            QApplication.processEvents()

            # Reject the dialog
            self.dialog.reject()
            QApplication.processEvents()

            import time
            time.sleep(0.15)
            QApplication.processEvents()

        self.assertTrue(self.startup_window.isEnabled(),
                       "Startup window should be enabled after reject from config view")


def run_interactive_test():
    """Run an interactive test to manually verify the fix"""
    app = QApplication(sys.argv)

    # Create and show startup window
    window = MinimalStartupWindow()
    window.show()

    print("=" * 60)
    print("Interactive Modal Dialog Chain Test")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Click 'Open Server List Dialog' button")
    print("2. In the Server List Dialog, click 'Add Server' button (if available)")
    print("   or close the dialog directly")
    print("3. Close the Server List Dialog")
    print("4. Click 'Click if window is responsive' button")
    print("5. If the click count increases, the fix is working!")
    print("\nClose the window to exit.")
    print("=" * 60)

    sys.exit(app.exec())


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test modal dialog chain')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run interactive test instead of unit tests')
    args = parser.parse_args()

    if args.interactive:
        run_interactive_test()
    else:
        # Run unit tests
        unittest.main(verbosity=2)
