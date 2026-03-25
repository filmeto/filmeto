"""
Avatar Component (QML-backed)

Provides a QWidget wrapper around a QML Avatar component for consistent rendering
across QML and QWidget-based parts of the app.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QColor
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QVBoxLayout, QWidget


AVATAR_QML_PATH = Path(__file__).resolve().parents[2] / "qml" / "chat" / "components" / "Avatar.qml"


class _AvatarBridge(QObject):
    iconChanged = Signal()
    colorChanged = Signal()
    sizeChanged = Signal()
    shapeChanged = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._icon = "👤"
        self._color = "#4a90e2"
        self._size = 32
        self._shape = "circle"

    @Property(str, notify=iconChanged)
    def icon(self) -> str:
        return self._icon

    @Property(str, notify=colorChanged)
    def color(self) -> str:
        return self._color

    @Property(int, notify=sizeChanged)
    def size(self) -> int:
        return self._size

    @Property(str, notify=shapeChanged)
    def shape(self) -> str:
        return self._shape

    def set_icon(self, icon: str) -> None:
        icon = icon or "👤"
        if self._icon != icon:
            self._icon = icon
            self.iconChanged.emit()

    def set_color(self, color: str) -> None:
        color = color or "#4a90e2"
        if self._color != color:
            self._color = color
            self.colorChanged.emit()

    def set_size(self, size: int) -> None:
        size = int(size) if size else 32
        if self._size != size:
            self._size = size
            self.sizeChanged.emit()

    def set_shape(self, shape: str) -> None:
        shape = shape or "circle"
        if self._shape != shape:
            self._shape = shape
            self.shapeChanged.emit()


class AvatarWidget(QWidget):
    """Reusable avatar widget rendered by QML."""

    def __init__(self, icon: str = "👤", color: str = "#4a90e2", size: int = 32, shape: str = "circle", parent=None):
        super().__init__(parent)

        self._bridge = _AvatarBridge(self)
        self._bridge.set_icon(icon)
        self._bridge.set_color(color)
        self._bridge.set_size(size)
        self._bridge.set_shape(shape)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setClearColor(Qt.transparent)
        qml_root_dir = Path(__file__).resolve().parents[2] / "qml"
        self._quick.engine().addImportPath(str(qml_root_dir))
        self._quick.rootContext().setContextProperty("avatarBridge", self._bridge)
        self._quick.setSource(QUrl.fromLocalFile(str(AVATAR_QML_PATH)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._quick)

        self.setFixedSize(self._bridge.size, self._bridge.size)

        root = self._quick.rootObject()
        if root is not None:
            root.setProperty("icon", self._bridge.icon)
            root.setProperty("color", QColor(self._bridge.color))
            root.setProperty("size", self._bridge.size)
            root.setProperty("shape", self._bridge.shape)

        self._bridge.iconChanged.connect(self._sync_to_qml)
        self._bridge.colorChanged.connect(self._sync_to_qml)
        self._bridge.sizeChanged.connect(self._sync_to_qml)
        self._bridge.shapeChanged.connect(self._sync_to_qml)

    @Slot()
    def _sync_to_qml(self) -> None:
        root = self._quick.rootObject()
        if root is None:
            return
        root.setProperty("icon", self._bridge.icon)
        root.setProperty("color", QColor(self._bridge.color))
        root.setProperty("size", self._bridge.size)
        root.setProperty("shape", self._bridge.shape)
        self.setFixedSize(self._bridge.size, self._bridge.size)

    def set_icon(self, icon: str):
        self._bridge.set_icon(icon)

    def set_color(self, color: str):
        self._bridge.set_color(color)

    def set_size(self, size: int):
        self._bridge.set_size(size)

    def set_shape(self, shape: str):
        self._bridge.set_shape(shape)