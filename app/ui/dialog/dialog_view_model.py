"""Canonical ViewModel module for dialog QML chrome."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QPoint, QPointF, Property, Signal, Slot
from PySide6.QtWidgets import QDialog, QWidget


class MacWindowControlsViewModel(QObject):
    """Close / minimize / green button behavior for QML MacWindowControls."""

    maximizedChanged = Signal()

    def __init__(self, window: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._window = window
        self._dialog_mode = False

    def set_dialog_mode(self, dialog: bool) -> None:
        self._dialog_mode = dialog

    @Property(bool, notify=maximizedChanged)
    def windowMaximized(self) -> bool:
        try:
            return bool(self._window.isMaximized())
        except (AttributeError, RuntimeError) as e:
            # AttributeError: window对象可能没有isMaximized方法
            # RuntimeError: widget可能已被销毁
            return False

    @Slot()
    def close_window(self) -> None:
        w = self._window
        if isinstance(w, QDialog):
            w.reject()
        else:
            w.close()

    @Slot()
    def minimize_window(self) -> None:
        self._window.showMinimized()

    @Slot()
    def green_window(self) -> None:
        w = self._window
        if self._dialog_mode:
            # Dialog模式: 绿色按钮不执行操作(对话框通常不支持最大化)
            # 可选行为: 1) 无操作 2) emit信号让调用方决定
            return
        else:
            if w.isMaximized():
                w.showNormal()
            else:
                w.showMaximized()
        self.refresh_maximized_state()

    def refresh_maximized_state(self) -> None:
        self.maximizedChanged.emit()


class DialogTitleDragViewModel(QObject):
    """Drag frameless dialog by title region (global coordinates from QML)."""

    def __init__(self, dialog: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._dialog = dialog
        self._press_global: Optional[QPointF] = None
        self._dlg_origin: Optional[QPoint] = None

    @Slot(float, float)
    def drag_begin(self, global_x: float, global_y: float) -> None:
        self._press_global = QPointF(global_x, global_y)
        self._dlg_origin = self._dialog.frameGeometry().topLeft()

    @Slot(float, float)
    def drag_move(self, global_x: float, global_y: float) -> None:
        if self._press_global is None or self._dlg_origin is None:
            return
        delta = QPointF(global_x, global_y) - self._press_global
        self._dialog.move(
            int(self._dlg_origin.x() + delta.x()),
            int(self._dlg_origin.y() + delta.y()),
        )

    @Slot()
    def drag_end(self) -> None:
        self._press_global = None
        self._dlg_origin = None


class CustomDialogTitleBarViewModel(QObject):
    """Title text, nav visibility, nav clicks for CustomDialogTitleBar.qml."""

    back_clicked = Signal()
    forward_clicked = Signal()

    titleChanged = Signal()
    navVisibleChanged = Signal()
    backEnabledChanged = Signal()
    forwardEnabledChanged = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._title = ""
        self._nav_visible = False
        self._back_enabled = False
        self._forward_enabled = False

    @Property(str, notify=titleChanged)
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        if self._title != value:
            self._title = value or ""
            self.titleChanged.emit()

    @Property(bool, notify=navVisibleChanged)
    def navVisible(self) -> bool:
        return self._nav_visible

    @navVisible.setter
    def navVisible(self, value: bool) -> None:
        if self._nav_visible != value:
            self._nav_visible = value
            self.navVisibleChanged.emit()

    @Property(bool, notify=backEnabledChanged)
    def backEnabled(self) -> bool:
        return self._back_enabled

    @backEnabled.setter
    def backEnabled(self, value: bool) -> None:
        if self._back_enabled != value:
            self._back_enabled = value
            self.backEnabledChanged.emit()

    @Property(bool, notify=forwardEnabledChanged)
    def forwardEnabled(self) -> bool:
        return self._forward_enabled

    @forwardEnabled.setter
    def forwardEnabled(self, value: bool) -> None:
        if self._forward_enabled != value:
            self._forward_enabled = value
            self.forwardEnabledChanged.emit()

    @Slot()
    def back(self) -> None:
        if self._back_enabled:
            self.back_clicked.emit()

    @Slot()
    def forward(self) -> None:
        if self._forward_enabled:
            self.forward_clicked.emit()


__all__ = [
    "MacWindowControlsViewModel",
    "DialogTitleDragViewModel",
    "CustomDialogTitleBarViewModel",
]
