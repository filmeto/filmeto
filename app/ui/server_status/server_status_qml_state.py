"""QObject state + click bridge for server status QML button."""

from PySide6.QtCore import QObject, Property, Signal, Slot


class ServerStatusViewModel(QObject):
    """Exposes counts to QML and relays click to Python."""

    clicked = Signal()
    activeCountChanged = Signal()
    inactiveCountChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = 0
        self._inactive = 0

    @Property(int, notify=activeCountChanged)
    def activeCount(self) -> int:
        return self._active

    @Property(int, notify=inactiveCountChanged)
    def inactiveCount(self) -> int:
        return self._inactive

    def set_counts(self, active: int, inactive: int) -> None:
        if self._active != active:
            self._active = active
            self.activeCountChanged.emit()
        if self._inactive != inactive:
            self._inactive = inactive
            self.inactiveCountChanged.emit()

    @Slot()
    def click(self) -> None:
        self.clicked.emit()

    def get_active(self) -> int:
        return self._active

    def get_inactive(self) -> int:
        return self._inactive


# Backward compatibility alias
ServerStatusQmlState = ServerStatusViewModel
