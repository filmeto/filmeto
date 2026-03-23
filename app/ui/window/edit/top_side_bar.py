import logging
from PySide6.QtGui import QMouseEvent, QCursor
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout,
                               QPushButton, QMenu)
from PySide6.QtCore import Signal, Qt

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.drawing_tools import DrawingToolsWidget
from app.ui.dialog.mac_button import MacTitleBar
from app.ui.project_menu.project_menu import ProjectMenu
from app.ui.server_status import ServerStatusWidget, ServerListDialog
from utils.i18n_utils import translation_manager, tr

logger = logging.getLogger(__name__)


class MainWindowTopSideBar(BaseWidget):
    # Signal to notify when language changes
    language_changed = Signal(str)
    # Signal for home button click
    home_clicked = Signal()

    def __init__(self, window, workspace: Workspace):
        super(MainWindowTopSideBar, self).__init__(workspace)
        self.setObjectName("main_window_top_bar")
        self.window = window
        # central_widget = QWidget(self)
        # central_widget.setObjectName("main_window_top_bar")
        # self.setAutoFillBackground(True)
        self.setFixedHeight(40)
        # widget = QWidget(self)
        # widget.setObjectName("main_window_top_bar")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)

        # mac title bar
        self.title_bar = MacTitleBar(window)
        self.title_bar.setObjectName("main_window_top_bar_left")
        # add to layout
        self.layout.addWidget(self.title_bar)
        
        # Home button (to return to startup mode)
        self.home_button = QPushButton("\ue600")  # Home icon
        self.home_button.setObjectName("home_button")
        self.home_button.setFixedSize(32, 32)
        self.home_button.setToolTip(tr("返回首页"))
        self.home_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.home_button.clicked.connect(self._on_home_clicked)
        self.home_button.setStyleSheet("""
            QPushButton#home_button {
                background-color: #3c3f41;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                font-size: 14px;
                font-family: iconfont;
            }
            QPushButton#home_button:hover {
                background-color: #4c5052;
                border: 1px solid #666666;
            }
            QPushButton#home_button:pressed {
                background-color: #2c2f31;
            }
        """)
        self.layout.addWidget(self.home_button)
        
        self.layout.addWidget(ProjectMenu(workspace))
        self.layout.addSpacing(100)
        self.layout.addWidget(QPushButton("\ue83f", self))
        self.layout.addWidget(QPushButton("\ue846", self))
        # Add drawing tools widget
        self.layout.addSpacing(300)
        self.drawing_tools = DrawingToolsWidget(self, workspace)
        self.layout.addWidget(self.drawing_tools)


        self.layout.addStretch()

        # Server status widget
        self.server_status_widget = ServerStatusWidget(workspace)
        self.server_status_widget.show_status_dialog.connect(self._show_server_dialog)
        self.layout.addWidget(self.server_status_widget.status_button)

        # Language switcher button
        self.language_button = QPushButton("🌐", self)
        self.language_button.setObjectName("main_window_top_bar_button")
        self.language_button.setToolTip(tr("切换语言"))
        self.language_button.clicked.connect(self._show_language_menu)
        self.layout.addWidget(self.language_button)

        # Export button
        self.export_button = QPushButton("\ue61e", self)  # Play icon for export
        self.export_button.setObjectName("main_window_top_bar_button")
        self.export_button.setToolTip(tr("导出时间线"))
        self.export_button.clicked.connect(self._show_export_dialog)
        self.layout.addWidget(self.export_button)
        # Settings button
        self.settings_button = QPushButton("\ue60f", self)  # Settings icon
        self.settings_button.setObjectName("main_window_top_bar_button")
        self.settings_button.setToolTip(tr("全局设置"))
        self.settings_button.clicked.connect(self._show_settings_dialog)
        self.layout.addWidget(self.settings_button)
        self.draggable = True
        self.drag_start_position = None

        # Connect to language change signal
        translation_manager.language_changed.connect(self._on_language_changed)
        
        # Apply button styling
        self._apply_button_styles()

    def _apply_button_styles(self):
        """Apply consistent styling to all top bar buttons"""
        button_style = """
            QPushButton#main_window_top_bar_button {
                background-color: #3c3f41;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                font-size: 14px;
                text-align: center;
                font-family: iconfont;
                padding: 4px;
            }
            
            QPushButton#main_window_top_bar_button:hover {
                background-color: #4c5052;
                border: 1px solid #666666;
            }
            
            QPushButton#main_window_top_bar_button:pressed {
                background-color: #2c2f31;
            }
        """
        
        # Set fixed size for all buttons to ensure consistency
        self.language_button.setFixedSize(32, 32)
        self.export_button.setFixedSize(32, 32)
        self.settings_button.setFixedSize(32, 32)
        
        self.settings_button.setStyleSheet(button_style)
        self.language_button.setStyleSheet(button_style)
        self.export_button.setStyleSheet(button_style)

    def mousePressEvent(self, event: QMouseEvent):
        self.draggable = True
        self.drag_start_position = event.globalPosition().toPoint() - self.window.pos()
        self.window.mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drag_start_position is None:
            return
        if self.draggable:
            # 移动窗口
            self.window.move(event.globalPosition().toPoint() - self.drag_start_position)
        self.window.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.draggable = False
        self.window.mouseReleaseEvent(event)

    def _show_language_menu(self):
        """Show language selection menu"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2c2c2c;
                color: #E1E1E1;
                border: 1px solid #505254;
            }
            QMenu::item:selected {
                background-color: #4080ff;
            }
        """)

        # Get available languages
        languages = translation_manager.get_available_languages()
        current_lang = translation_manager.get_current_language()

        for lang_code, lang_name in languages.items():
            action = menu.addAction(lang_name)
            action.setData(lang_code)
            # Mark current language
            if lang_code == current_lang:
                action.setText(f"✓ {lang_name}")
            action.triggered.connect(lambda checked=False, code=lang_code: self._switch_language(code))

        # Show menu below the button
        menu.exec(self.language_button.mapToGlobal(
            self.language_button.rect().bottomLeft()))

    def _switch_language(self, language_code):
        """Switch application language"""
        if translation_manager.switch_language(language_code):
            # Language changed signal will trigger _on_language_changed
            # Also update the current project's language setting
            current_project = self.workspace.get_project()
            if current_project:
                try:
                    current_project.update_config('language', language_code)
                except Exception as e:
                    logger.error(f"Failed to update project language setting: {e}")

    def _on_language_changed(self, language_code):
        """Called when language changes - update all UI text"""
        # Temporarily disable layout updates to prevent window expansion
        self.setUpdatesEnabled(False)
        self._update_ui_text()
        self.setUpdatesEnabled(True)
        # Force a single repaint
        self.update()

    def _update_ui_text(self):
        """Update UI text after language change"""
        self.language_button.setToolTip(tr("切换语言"))
        self.export_button.setToolTip(tr("导出时间线"))

    def _show_export_dialog(self):
        """Show the floating export panel"""
        # Import here to avoid circular imports
        from app.ui.export_video.export_video_widget import FloatingExportPanel

        # Check if the export panel is already open, close it if it is
        if hasattr(self, '_export_panel') and self._export_panel:
            self._export_panel.close()
            self._export_panel = None
        else:
            # Create and show the floating export panel
            self._export_panel = FloatingExportPanel(self.workspace, self.window)

            # Position the panel relative to the main window
            self._export_panel.update_position(self.window.geometry().topLeft(),
                                               self.window.geometry())

            # Show the panel
            self._export_panel.show()

    def _show_settings_dialog(self):
        """Show the settings dialog"""
        from app.ui.settings.settings_widget import SettingsWidget
        from PySide6.QtWidgets import QDialog
        
        # Create a QDialog to host the SettingsWidget
        dialog = QDialog(self.window)
        dialog.setWindowTitle(tr("全局设置"))
        dialog.setMinimumSize(800, 600)
        
        # Create the settings widget
        settings_widget = SettingsWidget(self.workspace)
        settings_widget.settings_changed.connect(self._on_settings_changed)
        
        # Use a layout to hold the settings widget
        from PySide6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(settings_widget)
        
        # Show the dialog
        dialog.exec()

    def _on_settings_changed(self):
        """Handle settings changes"""
        logger.info("Settings have been changed")
        # Here you could emit a signal or update other parts of the UI as needed
    
    def _show_server_dialog(self):
        """Show server management dialog"""
        from PySide6.QtCore import QCoreApplication
        server_dialog = ServerListDialog(self.workspace, self)
        server_dialog.servers_modified.connect(self.server_status_widget.force_refresh)
        logger.info(
            "TopSideBar opening ServerListDialog parent_enabled=%s active_modal=%s",
            self.isEnabled(),
            type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
        )
        try:
            server_dialog.exec()
        finally:
            server_dialog.deleteLater()
            QCoreApplication.processEvents()
            logger.info(
                "TopSideBar closed ServerListDialog parent_enabled=%s active_modal=%s focus_widget=%s",
                self.isEnabled(),
                type(QApplication.activeModalWidget()).__name__ if QApplication.activeModalWidget() else "None",
                type(QApplication.focusWidget()).__name__ if QApplication.focusWidget() else "None",
            )

    def _on_resolution_changed(self, index):
        """处理分辨率更改事件"""
        # 获取选中的分辨率
        resolution = self.resolution_combo.currentData()
        if resolution:
            width, height = resolution

            # 获取预览组件并设置新分辨率
            preview_widget = self.workspace.get_preview_widget()
            if preview_widget:
                preview_widget.set_preview_size(width, height)
            else:
                logger.warning("Preview widget not found")
    
    def _on_home_clicked(self):
        """Handle home button click to return to startup mode."""
        self.home_clicked.emit()

