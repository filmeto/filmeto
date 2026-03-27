# -*- coding: utf-8 -*-
"""Settings dialog using QML-based settings widget."""

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtQuickWidgets import QQuickWidget

from app.data.workspace import Workspace
from app.ui.dialog.custom_dialog import CustomDialog
from app.ui.settings.settings_view_model import SettingsViewModel
from utils.i18n_utils import tr


class SettingsDialog(CustomDialog):
    """Application settings in the unified custom dialog frame."""

    settings_changed = Signal()

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace

        self.setMinimumSize(900, 700)
        self.resize(900, 700)

        self.show_navigation_buttons(False)
        self.set_title(tr("全局设置"))

        # Get settings from workspace
        settings = workspace.get_settings()

        # Get service registry from workspace's plugins
        service_registry = None
        if hasattr(workspace, 'bot') and hasattr(workspace.bot, 'plugins'):
            service_registry = workspace.bot.plugins.get_service_registry()

        # Create ViewModel
        self._view_model = SettingsViewModel(
            settings=settings,
            service_registry=service_registry
        )
        self._view_model.settings_changed.connect(self.settings_changed.emit)

        # Get QML file path
        qml_file = Path(__file__).resolve().parents[1] / "ui" / "qml" / "settings" / "SettingsWidget.qml"

        if not qml_file.exists():
            # Fallback to alternative path
            qml_file = Path(__file__).parent.parent / "ui" / "qml" / "settings" / "SettingsWidget.qml"

        if qml_file.exists():
            # Create QML widget
            self._qml_widget = QQuickWidget()
            self._qml_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)

            # Add import paths
            engine = self._qml_widget.engine()
            app_qml = Path(__file__).resolve().parents[2] / "ui" / "qml"
            if app_qml.exists():
                engine.addImportPath(str(app_qml))

            # Set context properties
            ctx = self._qml_widget.rootContext()
            ctx.setContextProperty("settingsModel", self._view_model)

            # Load QML file
            self._qml_widget.setSource(QUrl.fromLocalFile(str(qml_file)))

            if self._qml_widget.status() == QQuickWidget.Error:
                for err in self._qml_widget.errors():
                    print(f"QML error: {err.toString()}")
                # Fallback to Python widget
                self._use_python_widget(workspace)
            else:
                self.setContentWidget(self._qml_widget)
        else:
            # Fallback to Python widget
            self._use_python_widget(workspace)

        self.add_button(tr("关闭"), self.reject, role="reject")

    def _use_python_widget(self, workspace: Workspace):
        """Fallback to Python-based settings widget."""
        from app.ui.settings.settings_widget import SettingsWidget

        self._settings_widget = SettingsWidget(workspace)
        self._settings_widget.settings_changed.connect(self.settings_changed.emit)
        self.setContentWidget(self._settings_widget)

    def save(self) -> bool:
        """Save settings."""
        if hasattr(self, '_view_model'):
            return self._view_model.save()
        return False