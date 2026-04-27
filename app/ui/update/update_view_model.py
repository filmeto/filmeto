"""
Update ViewModel

Bridge for QML update UI components. Currently used for direct Python dialogs;
the class is available for future QML integration.
"""

import logging
from PySide6.QtCore import QObject, Property, Signal, Slot

from app.services.update_service import UpdateInfo

logger = logging.getLogger(__name__)


class UpdateViewModel(QObject):
    """ViewModel exposing update state to QML."""

    # Signals
    update_available = Signal()
    download_progress = Signal(int, int)  # downloaded, total
    update_ready = Signal(str)  # filepath
    update_error = Signal(str)  # error message
    update_skipped = Signal(str)  # version skipped

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_version: str = ""
        self._latest_version: str = ""
        self._release_notes: str = ""
        self._has_update: bool = False
        self._is_downloading: bool = False
        self._update_info: UpdateInfo | None = None

    # -- Properties --

    @Property(str, notify=update_available)
    def current_version(self):
        return self._current_version

    @current_version.setter
    def current_version(self, value: str):
        if self._current_version != value:
            self._current_version = value
            self.update_available.emit()

    @Property(str, notify=update_available)
    def latest_version(self):
        return self._latest_version

    @latest_version.setter
    def latest_version(self, value: str):
        if self._latest_version != value:
            self._latest_version = value
            self.update_available.emit()

    @Property(str, notify=update_available)
    def release_notes(self):
        return self._release_notes

    @release_notes.setter
    def release_notes(self, value: str):
        if self._release_notes != value:
            self._release_notes = value
            self.update_available.emit()

    @Property(bool, notify=update_available)
    def has_update(self):
        return self._has_update

    @has_update.setter
    def has_update(self, value: bool):
        if self._has_update != value:
            self._has_update = value
            self.update_available.emit()

    @Property(bool, notify=update_available)
    def is_downloading(self):
        return self._is_downloading

    @is_downloading.setter
    def is_downloading(self, value: bool):
        if self._is_downloading != value:
            self._is_downloading = value
            self.update_available.emit()

    # -- Slots --

    @Slot()
    def check_for_update(self):
        """Trigger update check. Actual async work is done by UpdateService."""
        pass  # Orchestrated from App

    @Slot()
    def cancel_download(self):
        """Cancel an in-progress download."""
        pass  # Orchestrated from UpdateProgressDialog

    def set_update_info(self, info: UpdateInfo):
        """Populate view model from UpdateInfo."""
        self._update_info = info
        self._latest_version = info.version
        self._release_notes = info.release_notes
        self._has_update = True
        self.update_available.emit()

    def clear(self):
        """Reset all state."""
        self._update_info = None
        self._latest_version = ""
        self._release_notes = ""
        self._has_update = False
        self._is_downloading = False
        self.update_available.emit()
