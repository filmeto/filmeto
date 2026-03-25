from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget

RIGHT_BAR_QML_PATH = Path(__file__).resolve().parent.parent.parent / "qml" / "startup" / "StartupRightSideBar.qml"


class StartupWindowRightSideBar(BaseWidget):
    button_clicked = Signal(str)

    def __init__(self, workspace: Workspace, parent):
        super().__init__(workspace)
        self.setObjectName("startup_window_right_bar")
        self.parent = parent
        self.setFixedWidth(40)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, False)
        self._quick.setClearColor(QColor("#2b2d30"))
        self._quick.setSource(QUrl.fromLocalFile(str(RIGHT_BAR_QML_PATH)))

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self._quick)

        root = self._quick.rootObject()
        if root is not None and hasattr(root, "panelSelected"):
            root.panelSelected.connect(self.button_clicked.emit)

    def set_selected_button(self, panel_name: str, emit_signal: bool = False):
        root = self._quick.rootObject()
        if root is not None:
            try:
                root.setProperty("selectedPanel", panel_name or "members")
                if emit_signal and hasattr(root, "selectPanel"):
                    root.selectPanel(panel_name or "members", True)
            except Exception:
                pass
        elif emit_signal:
            self.button_clicked.emit(panel_name or "members")