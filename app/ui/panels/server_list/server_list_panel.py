"""
Server List Panel

Panel for displaying and managing servers in the right-side panel area.
Wraps the ServerListView and provides server management functionality
directly within the panel switcher.
"""
import logging

from PySide6.QtWidgets import QApplication, QMessageBox, QMenu
from PySide6.QtGui import QAction

from app.ui.panels.base_panel import BasePanel
from app.ui.server_list.server_views import ServerListView
from utils.i18n_utils import tr, translation_manager

logger = logging.getLogger(__name__)


class ServerListPanel(BasePanel):
    """Panel for displaying and managing servers."""

    def __init__(self, workspace, parent=None):
        super().__init__(workspace, parent)
        self.server_manager = None
        self.set_panel_title(tr("Servers"))

        self.server_list_view = ServerListView(self)
        self.content_layout.addWidget(self.server_list_view)

        self.server_list_view.server_selected_for_edit.connect(self._on_edit_server)
        self.server_list_view.server_toggled.connect(self._on_toggle_server)
        self.server_list_view.server_deleted.connect(self._on_delete_server)
        self.server_list_view.add_server_clicked.connect(self._on_add_server)
        self.server_list_view.refresh_clicked.connect(self._load_servers)

        self.add_toolbar_button("\ue627", self._load_servers, tr("Refresh"))
        self.add_toolbar_button("\ue61f", self._on_add_server, tr("Add Server"))

        translation_manager.language_changed.connect(self._on_language_changed)

    def setup_ui(self):
        pass

    def load_data(self):
        self._load_servers()

    def _load_servers(self):
        """Load servers from ServerManager."""
        try:
            from server.server import ServerManager
            workspace_path = self.workspace.workspace_path
            self.server_manager = ServerManager(workspace_path)
            self.server_list_view.set_server_manager(self.server_manager)
        except Exception as e:
            logger.error(f"Failed to load servers: {e}")

    def _on_toggle_server(self, server_name: str, enabled: bool):
        try:
            server = self.server_manager.get_server(server_name)
            if server:
                server.config.enabled = enabled
                self.server_manager.update_server(server_name, server.config)
                self.server_list_view.load_servers()
        except Exception as e:
            logger.error(f"Failed to toggle server: {e}")

    def _on_edit_server(self, server_name: str):
        """Open the server list dialog for editing."""
        try:
            from app.ui.server_list.server_list_dialog import ServerListDialog
            from PySide6.QtCore import QCoreApplication, QEvent, Qt
            import shiboken6
            dialog = ServerListDialog(self.workspace, self)
            server = self.server_manager.get_server(server_name)
            if server:
                plugin_info = server.get_plugin_info()
                if plugin_info:
                    dialog._show_config_view(plugin_info, server.config)
            dialog.servers_modified.connect(self._load_servers)
            logger.info(
                "ServerListPanel opening edit dialog parent_enabled=%s active_modal=%s",
                self.isEnabled(),
                type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
            )
            try:
                dialog.exec()
            finally:
                if shiboken6.isValid(dialog):
                    try:
                        dialog.setWindowModality(Qt.NonModal)
                        dialog.hide()
                        dialog.close()
                    except Exception as e:
                        logger.debug(f"ServerListPanel force-close edit dialog failed: {e}")
                    try:
                        dialog.deleteLater()
                    except Exception as e:
                        logger.debug(f"ServerListPanel deleteLater(edit) failed: {e}")
                else:
                    logger.info("ServerListPanel cleanup skipped(edit): dialog already deleted")
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                QCoreApplication.processEvents()
                QCoreApplication.processEvents()
                logger.info(
                    "ServerListPanel closed edit dialog parent_enabled=%s active_modal=%s focus_widget=%s",
                    self.isEnabled(),
                    type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
                    type(QApplication.focusWidget()).__name__ if QApplication.focusWidget() else "None",
                )
        except Exception as e:
            logger.error(f"Failed to edit server: {e}")

    def _on_delete_server(self, server_name: str):
        reply = QMessageBox.question(
            self,
            tr("Confirm Delete"),
            f"{tr('Are you sure you want to delete server')} '{server_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.server_manager.delete_server(server_name)
                self.server_list_view.load_servers()
            except Exception as e:
                logger.error(f"Failed to delete server: {e}")

    def _on_add_server(self):
        """Open server list dialog for adding a new server."""
        try:
            from app.ui.server_list.server_list_dialog import ServerListDialog
            from PySide6.QtCore import QCoreApplication, QEvent, Qt
            import shiboken6
            dialog = ServerListDialog(self.workspace, self)
            dialog.servers_modified.connect(self._load_servers)
            logger.info(
                "ServerListPanel opening add dialog parent_enabled=%s active_modal=%s",
                self.isEnabled(),
                type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
            )
            try:
                dialog.exec()
            finally:
                if shiboken6.isValid(dialog):
                    try:
                        dialog.setWindowModality(Qt.NonModal)
                        dialog.hide()
                        dialog.close()
                    except Exception as e:
                        logger.debug(f"ServerListPanel force-close add dialog failed: {e}")
                    try:
                        dialog.deleteLater()
                    except Exception as e:
                        logger.debug(f"ServerListPanel deleteLater(add) failed: {e}")
                else:
                    logger.info("ServerListPanel cleanup skipped(add): dialog already deleted")
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                QCoreApplication.processEvents()
                QCoreApplication.processEvents()
                logger.info(
                    "ServerListPanel closed add dialog parent_enabled=%s active_modal=%s focus_widget=%s",
                    self.isEnabled(),
                    type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
                    type(QApplication.focusWidget()).__name__ if QApplication.focusWidget() else "None",
                )
        except Exception as e:
            logger.error(f"Failed to open add server dialog: {e}")

    def on_project_switched(self, project_name: str):
        super().on_project_switched(project_name)
        self._load_servers()

    def _on_language_changed(self, language_code: str):
        self.set_panel_title(tr("Servers"))
        self._load_servers()
