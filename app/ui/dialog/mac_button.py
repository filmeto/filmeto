"""
macOS-style window controls (QML).

MacTitleBar embeds MacWindowControls.qml. Legacy MacButton QWidget painting is removed.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QUrl, Signal
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from app.ui.dialog.dialog_qml_bridge import MacWindowControlsViewModel

logger = logging.getLogger(__name__)


class MacTitleBar(QWidget):
    """macOS-style window controls for dialogs or main windows (QML)."""

    back_clicked = Signal()
    forward_clicked = Signal()

    def __init__(self, window: QWidget):
        super().__init__()
        self.window = window
        self.is_dialog = False

        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._actions = MacWindowControlsViewModel(window, self)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setClearColor(Qt.transparent)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setStyleSheet("background: transparent;")

        qml_dir = Path(__file__).resolve().parent.parent / "qml" / "dialog"
        self._quick.engine().addImportPath(str(qml_dir.parent))

        rc = self._quick.rootContext()
        rc.setContextProperty("macActions", self._actions)

        qml_path = qml_dir / "MacWindowControls.qml"
        self._quick.setSource(QUrl.fromLocalFile(str(qml_path)))

        if self._quick.status() == QQuickWidget.Error:
            for err in self._quick.errors():
                logger.error("MacWindowControls QML: %s", err.toString())

        ro = self._quick.rootObject()
        if ro is not None:
            ro.setProperty("macActions", self._actions)
            ro.setProperty("dialogMode", self.is_dialog)
            self._sync_quick_width()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._quick)

        window.installEventFilter(self)

    def _sync_quick_width(self) -> None:
        ro = self._quick.rootObject()
        if ro is None:
            return
        w = ro.property("implicitWidth")
        if w and float(w) > 0:
            self._quick.setFixedWidth(int(w))
        else:
            self._quick.setFixedWidth(68)

    def set_for_dialog(self) -> None:
        self.is_dialog = True
        self._actions.set_dialog_mode(True)
        ro = self._quick.rootObject()
        if ro is not None:
            ro.setProperty("dialogMode", True)

    def show_navigation_buttons(self, show: bool = True) -> None:
        """Kept for API compatibility; nav lives in CustomDialogTitleBar when used."""

    def set_navigation_enabled(self, back_enabled: bool, forward_enabled: bool) -> None:
        """Kept for API compatibility."""

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if obj is self.window and event.type() == QEvent.WindowStateChange:
            self._actions.refresh_maximized_state()
        return super().eventFilter(obj, event)
