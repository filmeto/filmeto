"""macOS-style window controls (pure QWidget — no QML)."""

from __future__ import annotations

from enum import IntEnum
from typing import Callable, Optional

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from app.ui.dialog.dialog_view_model import MacWindowControlsViewModel

DEFAULT_MAC_BUTTONS_WIDTH = 68
_CHROME_BG = QColor("#3d3f4e")


class _LightKind(IntEnum):
    CLOSE = 0
    MINIMIZE = 1
    ZOOM = 2


class _TrafficLight(QWidget):
    """12×12 traffic-light disc with hover glyph (matches MacWindowControls.qml)."""

    _PALETTE = {
        _LightKind.CLOSE: ("#ff5f56", "#8e3a36"),
        _LightKind.MINIMIZE: ("#ffbd2e", "#9a6a1b"),
        _LightKind.ZOOM: ("#27c93f", "#1a6d1e"),
    }

    def __init__(
        self,
        kind: _LightKind,
        actions: MacWindowControlsViewModel,
        target: QWidget,
        dialog_mode: Callable[[], bool],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._kind = kind
        self._actions = actions
        self._target = target
        self._dialog_mode = dialog_mode
        self._hover = False
        self.setFixedSize(12, 12)
        self.setCursor(Qt.PointingHandCursor)
        self._accent, self._glyph = self._PALETTE[kind]

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if (
            event.button() == Qt.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self._activate()
        super().mouseReleaseEvent(event)

    def _activate(self) -> None:
        if self._kind == _LightKind.CLOSE:
            self._actions.close_window()
        elif self._kind == _LightKind.MINIMIZE:
            self._actions.minimize_window()
        else:
            self._actions.green_window()

    def paintEvent(self, event):
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self._accent))
        p.drawEllipse(self.rect().adjusted(0, 0, -1, -1))

        if not self._hover:
            return

        pen = QPen(QColor(self._glyph))
        pen.setWidthF(1.2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        if self._kind == _LightKind.CLOSE:
            p.drawLine(4, 4, 8, 8)
            p.drawLine(8, 4, 4, 8)
        elif self._kind == _LightKind.MINIMIZE:
            p.drawLine(3, 6, 9, 6)
        else:
            if self._dialog_mode():
                p.drawLine(3, 6, 9, 6)
            elif self._target.isMaximized():
                p.drawLine(4, 5, 4, 3)
                p.drawLine(4, 3, 6, 3)
                p.drawLine(8, 7, 8, 9)
                p.drawLine(8, 9, 6, 9)
            else:
                p.drawLine(3, 3, 3, 6)
                p.drawLine(3, 3, 6, 3)
                p.drawLine(9, 9, 9, 6)
                p.drawLine(9, 9, 6, 9)


class MacTitleBar(QWidget):
    """macOS-style close / minimize / zoom for frameless windows (QWidget)."""

    back_clicked = Signal()
    forward_clicked = Signal()

    def __init__(self, window: QWidget):
        super().__init__()
        self.window = window
        self.is_dialog = False

        self.setFixedHeight(36)
        self.setFixedWidth(DEFAULT_MAC_BUTTONS_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._actions = MacWindowControlsViewModel(window, self)
        self._quick = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        dialog_mode = lambda: self.is_dialog
        self._close_btn = _TrafficLight(
            _LightKind.CLOSE, self._actions, window, dialog_mode, self
        )
        self._min_btn = _TrafficLight(
            _LightKind.MINIMIZE, self._actions, window, dialog_mode, self
        )
        self._zoom_btn = _TrafficLight(
            _LightKind.ZOOM, self._actions, window, dialog_mode, self
        )

        layout.addWidget(self._close_btn, 0, Qt.AlignVCenter)
        layout.addWidget(self._min_btn, 0, Qt.AlignVCenter)
        layout.addWidget(self._zoom_btn, 0, Qt.AlignVCenter)

        self._actions.maximizedChanged.connect(self._zoom_btn.update)

        window.installEventFilter(self)

    def paintEvent(self, event):
        del event
        p = QPainter(self)
        p.fillRect(self.rect(), _CHROME_BG)

    def set_for_dialog(self) -> None:
        """Dialog mode: green button is inert and shows a disabled-style glyph."""
        self.is_dialog = True
        self._actions.set_dialog_mode(True)
        self._zoom_btn.update()

    def show_navigation_buttons(self, show: bool = True):
        """Reserved for API compatibility (navigation lives on CustomDialogTitleBar)."""

    def set_navigation_enabled(self, back_enabled: bool, forward_enabled: bool):
        """Reserved for API compatibility."""

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if obj is self.window and event.type() == QEvent.WindowStateChange:
            self._actions.refresh_maximized_state()
        return super().eventFilter(obj, event)
