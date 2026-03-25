from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Qt, Signal, Slot
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget

RIGHT_BAR_QML_PATH = Path(__file__).resolve().parent.parent.parent / "qml" / "startup" / "StartupRightSideBar.qml"


class _StartupRightBarBridge(QObject):
    buttonsChanged = Signal()
    selectedPanelChanged = Signal()
    panelSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = [
            {"panel": "members", "icon": "\ue89e", "tooltip": "Members"},
            {"panel": "screenplay", "icon": "\ue993", "tooltip": "Screen Play"},
            {"panel": "plan", "icon": "\ue8a5", "tooltip": "Plan Management"},
        ]
        self._selected_panel = "members"

    @Property("QVariantList", notify=buttonsChanged)
    def buttons(self):
        return self._buttons

    @Property(str, notify=selectedPanelChanged)
    def selectedPanel(self):
        return self._selected_panel

    def set_selected_panel(self, panel_name: str):
        panel_name = panel_name or "members"
        if self._selected_panel != panel_name:
            self._selected_panel = panel_name
            self.selectedPanelChanged.emit()

    @Slot(str)
    def select_panel(self, panel_name: str):
        self.set_selected_panel(panel_name)
        self.panelSelected.emit(panel_name)


class StartupWindowRightSideBar(BaseWidget):
    button_clicked = Signal(str)

    def __init__(self, workspace: Workspace, parent):
        super().__init__(workspace)
        self.setObjectName("startup_window_right_bar")
        self.parent = parent
        self.setFixedWidth(40)

        self._bridge = _StartupRightBarBridge(self)
        self._bridge.panelSelected.connect(self.button_clicked.emit)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, False)
        self._quick.setClearColor(QColor("#2b2d30"))
        self._quick.rootContext().setContextProperty("startupRightBarBridge", self._bridge)
        self._quick.setSource(QUrl.fromLocalFile(str(RIGHT_BAR_QML_PATH)))

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self._quick)

    def set_selected_button(self, panel_name: str, emit_signal: bool = False):
        self._bridge.set_selected_panel(panel_name)
        if emit_signal:
            self.button_clicked.emit(panel_name)