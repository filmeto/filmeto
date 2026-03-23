"""
Server List Dialog

Mac-style preferences dialog that switches between server list and config views
using navigation buttons instead of opening separate dialogs.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QDialog, QPushButton, QMessageBox, QMenu, QStackedWidget, QDialogButtonBox, QVBoxLayout, QWidget
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction

from app.ui.dialog.custom_dialog import CustomDialog
from app.ui.server_list.server_views import ServerListView, ServerConfigView
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class ServerListDialog(CustomDialog):
    """
    Unified dialog for server management with Mac-style navigation.
    
    This dialog contains a stacked widget that switches between:
    - Server list view
    - Server configuration view
    
    Navigation is handled via back/forward buttons in the title bar.
    """
    
    # Signal emitted when servers are modified
    servers_modified = Signal()
    
    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.server_manager = None
        
        # Navigation state
        self.view_history = []
        self.current_view_index = -1
        
        # Setup dialog
        self.setMinimumSize(900, 600)
        self.resize(900, 600)
        
        # Initialize UI
        self._init_ui()
        
        # Load servers
        self._load_servers()
        
        # Show list view initially
        self._show_list_view()
        self._log_ui_state("init-complete")

    def _log_ui_state(self, stage: str):
        """Log modal/focus/window state to debug UI input issues."""
        try:
            modal = QApplication.activeModalWidget()
            active = QApplication.activeWindow()
            focus = QApplication.focusWidget()
            parent = self.parentWidget()
            logger.info(
                "ServerListDialog[%s] visible=%s enabled=%s modal=%s active_window=%s focus_widget=%s parent=%s parent_enabled=%s",
                stage,
                self.isVisible(),
                self.isEnabled(),
                type(modal).__name__ if modal else "None",
                type(active).__name__ if active else "None",
                type(focus).__name__ if focus else "None",
                type(parent).__name__ if parent else "None",
                parent.isEnabled() if parent else "n/a",
            )
        except Exception as e:
            logger.debug("ServerListDialog state log failed at %s: %s", stage, e)
    
    def _init_ui(self):
        """Initialize UI components"""
        # Show navigation buttons
        self.show_navigation_buttons(True)

        # Connect navigation signals
        self.back_clicked.connect(self._on_back_clicked)
        self.forward_clicked.connect(self._on_forward_clicked)

        # Create stacked widget for view switching
        self.stacked_widget = QStackedWidget(self)

        # Create views
        self.list_view = ServerListView(self)
        self.config_view = ServerConfigView(self.workspace)

        # Add views to stack
        self.stacked_widget.addWidget(self.list_view)
        self.stacked_widget.addWidget(self.config_view)

        # Connect signals from list view
        self.list_view.server_selected_for_edit.connect(self._on_edit_server)
        self.list_view.server_toggled.connect(self._on_toggle_server)
        self.list_view.server_deleted.connect(self._on_delete_server)
        self.list_view.add_server_clicked.connect(self._on_add_server)
        self.list_view.refresh_clicked.connect(self._load_servers)

        # Connect signals from config view
        self.config_view.save_clicked.connect(self._on_config_saved)
        self.config_view.cancel_clicked.connect(self._on_config_cancelled)

        # Set the stacked widget as content
        self.setContentWidget(self.stacked_widget)

        # Add the close button using the standardized button mechanism
        close_button = self.add_button(tr("关闭"), self.reject, role="reject")

        # Add title bar buttons
        self._add_titlebar_buttons()
    
    def _add_titlebar_buttons(self):
        """Add action buttons to title bar"""
        # Refresh button
        self.refresh_button = QPushButton("🔄 " + tr("刷新"), self)
        self.refresh_button.clicked.connect(self._load_servers)
        self.refresh_button.setFixedHeight(26)
        self._style_title_button(self.refresh_button)
        self.title_bar.toolbar_layout.addWidget(self.refresh_button)
        
        # Add server button
        self.add_button = QPushButton("➕ " + tr("添加服务器"), self)
        self.add_button.clicked.connect(self._on_add_server)
        self.add_button.setFixedHeight(26)
        self._style_title_button(self.add_button)
        self.title_bar.toolbar_layout.addWidget(self.add_button)
    
    def _style_title_button(self, button):
        """Apply styling to title bar buttons"""
        button.setStyleSheet("""
            QPushButton {
                background-color: #4c5052;
                color: #E1E1E1;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5c6062;
                border: 1px solid #777777;
            }
            QPushButton:pressed {
                background-color: #3c4042;
            }
        """)
    
    def _load_servers(self):
        """Load servers from ServerManager"""
        try:
            from server.server import ServerManager
            
            # Get workspace path
            workspace_path = self.workspace.workspace_path
            
            # Create server manager
            self.server_manager = ServerManager(workspace_path)
            
            # Set server manager in list view
            self.list_view.set_server_manager(self.server_manager)
            
        except Exception as e:
            logger.error(f"Failed to load servers: {e}")
            QMessageBox.critical(self, tr("错误"), f"{tr('加载服务器失败')}: {str(e)}")
    
    def _show_list_view(self):
        """Switch to list view"""
        # Clean up any QML widgets before switching views
        self._cleanup_config_view()
        self.stacked_widget.setCurrentWidget(self.list_view)
        self.set_title(tr("服务器管理"))
        self._update_title_bar_buttons(show_list_buttons=True)
        self._update_dialog_buttons()  # Update buttons for list view (just close button)
        self._add_to_history("list")
        self._update_navigation_buttons()
    
    def _show_config_view(self, plugin_info, server_config=None):
        """
        Switch to config view.
        
        Args:
            plugin_info: PluginInfo object
            server_config: Optional ServerConfig for editing
        """
        self.config_view.configure(plugin_info, server_config)
        self.stacked_widget.setCurrentWidget(self.config_view)
        
        if server_config:
            self.set_title(f"{tr('编辑服务器')} - {server_config.name}")
        else:
            self.set_title(f"{tr('添加服务器')} - {plugin_info.name}")
        
        self._update_title_bar_buttons(show_list_buttons=False)
        self._update_dialog_buttons()  # Update buttons for config view
        self._add_to_history("config")
        self._update_navigation_buttons()
        self._log_ui_state(f"show-config-{plugin_info.name}")
    
    def _update_dialog_buttons(self):
        """Update the dialog's button row based on current view"""
        # Use the button row method to set up all buttons at once
        # This avoids the clear/add pattern that might be causing issues
        if self.stacked_widget.currentWidget() == self.config_view:
            # For config view: Close, Cancel, Save/Create buttons
            buttons = [
                (tr("关闭"), self.reject, "reject"),
                (tr("取消"), self._on_config_cancelled, "reject"),
                (tr("保存") if self.config_view.is_edit_mode else tr("创建"), self._emit_save_signal, "accept")
            ]
        else:
            # For list view: Just the close button
            buttons = [
                (tr("关闭"), self.reject, "reject")
            ]

        # Use add_button_row which handles the layout properly
        self.add_button_row(buttons)

    def _emit_save_signal(self):
        """Emit save signal to trigger validation and saving in config view"""
        self.config_view._on_save_clicked()

    def _update_title_bar_buttons(self, show_list_buttons: bool):
        """Update visibility of title bar buttons based on current view"""
        self.refresh_button.setVisible(show_list_buttons)
        self.add_button.setVisible(show_list_buttons)
    
    def _add_to_history(self, view_name: str):
        """Add view to navigation history"""
        # Trim forward history if we're not at the end
        if self.current_view_index < len(self.view_history) - 1:
            self.view_history = self.view_history[:self.current_view_index + 1]
        
        # Add new view
        self.view_history.append(view_name)
        self.current_view_index = len(self.view_history) - 1
    
    def _update_navigation_buttons(self):
        """Update navigation button states"""
        can_go_back = self.current_view_index > 0
        can_go_forward = self.current_view_index < len(self.view_history) - 1
        self.set_navigation_enabled(can_go_back, can_go_forward)
    
    def _on_back_clicked(self):
        """Handle back button click"""
        if self.current_view_index > 0:
            self.current_view_index -= 1
            view_name = self.view_history[self.current_view_index]
            self._navigate_to_view(view_name)
    
    def _on_forward_clicked(self):
        """Handle forward button click"""
        if self.current_view_index < len(self.view_history) - 1:
            self.current_view_index += 1
            view_name = self.view_history[self.current_view_index]
            self._navigate_to_view(view_name)
    
    def _navigate_to_view(self, view_name: str):
        """Navigate to a view without adding to history"""
        if view_name == "list":
            self.stacked_widget.setCurrentWidget(self.list_view)
            self.set_title(tr("服务器管理"))
            self._update_title_bar_buttons(show_list_buttons=True)
        elif view_name == "config":
            self.stacked_widget.setCurrentWidget(self.config_view)
            # Title would have been set when originally navigating to config view
            self._update_title_bar_buttons(show_list_buttons=False)
        
        self._update_navigation_buttons()
    
    def _on_toggle_server(self, server_name: str, enabled: bool):
        """Handle server enable/disable toggle"""
        try:
            server = self.server_manager.get_server(server_name)
            if server:
                server.config.enabled = enabled
                self.server_manager.update_server(server_name, server.config)
                self.list_view.load_servers()
                self.servers_modified.emit()
        except Exception as e:
            QMessageBox.critical(self, tr("错误"), f"{tr('更新服务器失败')}: {str(e)}")
    
    def _on_edit_server(self, server_name: str):
        """Handle edit server request"""
        try:
            server = self.server_manager.get_server(server_name)
            if not server:
                QMessageBox.warning(self, tr("错误"), f"{tr('服务器未找到')}: {server_name}")
                return
            
            # Get plugin info
            plugin_info = server.get_plugin_info()
            if not plugin_info:
                QMessageBox.warning(
                    self,
                    tr("错误"),
                    f"{tr('无法获取插件信息')}: {server.config.plugin_name}"
                )
                return
            
            # Show config view for editing
            self._show_config_view(plugin_info, server.config)
            
        except Exception as e:
            QMessageBox.critical(self, tr("错误"), f"{tr('编辑服务器失败')}: {str(e)}")
    
    def _on_delete_server(self, server_name: str):
        """Handle delete server request"""
        reply = QMessageBox.question(
            self,
            tr("确认删除"),
            f"{tr('确定要删除服务器')} '{server_name}' {tr('吗')}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.server_manager.delete_server(server_name)
                self.list_view.load_servers()
                self.servers_modified.emit()
            except Exception as e:
                QMessageBox.critical(self, tr("错误"), f"{tr('删除服务器失败')}: {str(e)}")
    
    def _on_add_server(self):
        """Handle add new server request"""
        if not self.server_manager:
            QMessageBox.warning(self, tr("错误"), tr("服务器管理器未初始化"))
            return
        
        # Get available plugins
        plugins = self.server_manager.list_available_plugins()
        
        if not plugins:
            QMessageBox.warning(
                self,
                tr("提示"),
                tr("没有可用的插件。请检查插件目录。")
            )
            return
        
        # Filter out default server plugins
        filtered_plugins = [
            plugin for plugin in plugins 
            if plugin.name not in ["Local Server", "Filmeto Server"]
        ]
        
        if not filtered_plugins:
            QMessageBox.warning(
                self,
                tr("提示"),
                tr("没有可用的服务器插件。请检查插件目录。")
            )
            return
        
        # Create menu for plugin selection
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #E1E1E1;
                border: 1px solid #3c3c3c;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3c3c3c;
                margin: 4px 0px;
            }
        """)
        
        # Add plugin actions
        for plugin in filtered_plugins:
            action = QAction(plugin.name, self)
            action.triggered.connect(lambda checked=False, p=plugin: self._show_config_view(p))
            menu.addAction(action)
        
        # Show menu at button position
        button = self.sender()
        if button:
            menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        else:
            menu.exec(self.mapToGlobal(self.rect().center()))
    
    def _on_config_saved(self, server_name: str, config):
        """Handle configuration saved from config view"""
        try:
            # Determine if this is create or update
            existing_server = self.server_manager.get_server(server_name)
            
            if existing_server:
                # Update existing server
                self.server_manager.update_server(server_name, config)
                QMessageBox.information(
                    self,
                    tr("成功"),
                    f"{tr('服务器')} '{server_name}' {tr('已成功更新')}"
                )
            else:
                # Create new server
                self.server_manager.add_server(config)
                QMessageBox.information(
                    self,
                    tr("成功"),
                    f"{tr('服务器')} '{server_name}' {tr('已成功创建')}"
                )
            
            # Reload list and go back to list view
            self.list_view.load_servers()
            self.servers_modified.emit()
            self._show_list_view()
            
        except ValueError as e:
            QMessageBox.critical(
                self,
                tr("错误"),
                f"{tr('保存服务器失败')}: {str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("错误"),
                f"{tr('保存服务器时发生错误')}: {str(e)}"
            )
    
    def _on_config_cancelled(self):
        """Handle configuration cancelled from config view"""
        # Clean up any QML widgets before switching views
        self._cleanup_config_view()
        # Go back to list view
        self._show_list_view()

    def _cleanup_config_view(self):
        """Clean up resources in config view"""
        from PySide6.QtCore import QCoreApplication
        self._log_ui_state("cleanup-config-start")
        if hasattr(self.config_view, 'custom_config_widget') and self.config_view.custom_config_widget:
            widget = self.config_view.custom_config_widget
            logger.info(
                "ServerListDialog cleanup widget type=%s objectName=%s visible=%s",
                type(widget).__name__,
                widget.objectName(),
                widget.isVisible(),
            )

            # 1. Clear focus from the widget and all its children
            widget.clearFocus()
            for child in widget.findChildren(QWidget):
                if hasattr(child, 'clearFocus'):
                    child.clearFocus()

            # 2. Call cleanup if available — for QML widgets this destroys the
            #    QQuickWidget and detaches it from the native window hierarchy
            if hasattr(widget, 'cleanup'):
                try:
                    widget.cleanup()
                except Exception as e:
                    logger.debug(f"Error cleaning up config widget: {e}")

            # 3. Release mouse grab
            try:
                widget.releaseMouse()
            except Exception as e:
                logger.debug(f"Error releasing mouse: {e}")

            # 4. Remove the container widget from the config view's layout so it
            #    is no longer part of the native widget hierarchy
            if hasattr(self.config_view, 'main_layout'):
                try:
                    self.config_view.main_layout.removeWidget(widget)
                except Exception as e:
                    logger.debug(f"Error removing widget from layout: {e}")

            # 5. Detach from parent and schedule deletion
            try:
                widget.setParent(None)
            except Exception as e:
                logger.debug(f"Error detaching widget: {e}")

            # 6. Clear the reference
            self.config_view.custom_config_widget = None

            # 7. Delete the container widget
            widget.deleteLater()

            # 8. Process events to complete native resource release
            QCoreApplication.processEvents()
            self._log_ui_state("cleanup-config-after-deleteLater")

        # Also call the config view's own cleanup method (handles any remaining state)
        if hasattr(self.config_view, '_cleanup_custom_widget'):
            self.config_view._cleanup_custom_widget()

        # Final event processing pass
        QCoreApplication.processEvents()
        self._log_ui_state("cleanup-config-end")

    def reject(self):
        """Override reject to clean up QML widgets before closing"""
        self._log_ui_state("reject-start")
        self._cleanup_config_view()
        # Call parent reject (which handles focus restoration)
        super().reject()
        self._log_ui_state("reject-end")

    def done(self, result):
        """Override done to clean up QML widgets before closing"""
        self._log_ui_state(f"done-start-{result}")
        self._cleanup_config_view()
        # Call parent done (which handles focus restoration)
        super().done(result)
        self._log_ui_state(f"done-end-{result}")