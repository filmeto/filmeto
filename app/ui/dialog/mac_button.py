"""
macOS-style window controls (QML).

MacTitleBar embeds MacWindowControls.qml. Legacy MacButton QWidget painting is removed.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QUrl, Signal
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from app.ui.dialog.dialog_view_model import MacWindowControlsViewModel

logger = logging.getLogger(__name__)

# Default width when QML implicitWidth is not available
DEFAULT_MAC_BUTTONS_WIDTH = 68


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
        self._quick = None

        self._setup_layout()
        self._load_qml_controls()

        window.installEventFilter(self)

    def _setup_layout(self) -> None:
        """Initialize the layout."""
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def _load_qml_controls(self) -> None:
        """Load QML-based Mac window controls."""
        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setClearColor(Qt.transparent)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setStyleSheet("background: transparent;")

        qml_dir = Path(__file__).resolve().parent.parent / "qml" / "dialog"
        self._quick.engine().addImportPath(str(qml_dir.parent))

        # Set context property for QML binding
        rc = self._quick.rootContext()
        rc.setContextProperty("macActions", self._actions)

        qml_path = qml_dir / "MacWindowControls.qml"
        self._quick.setSource(QUrl.fromLocalFile(str(qml_path)))

        if self._quick.status() == QQuickWidget.Error:
            for err in self._quick.errors():
                logger.error("MacWindowControls QML: %s", err.toString())
            return

        ro = self._quick.rootObject()
        if ro is not None:
            ro.setProperty("dialogMode", self.is_dialog)
            self._sync_quick_width()

        self._layout.addWidget(self._quick)

    def _sync_quick_width(self) -> None:
        """Synchronize widget width with QML implicit width."""
        if self._quick is None:
            return
        ro = self._quick.rootObject()
        if ro is None:
            return
        w = ro.property("implicitWidth")
        if w and float(w) > 0:
            self._quick.setFixedWidth(int(w))
        else:
            self._quick.setFixedWidth(DEFAULT_MAC_BUTTONS_WIDTH)

    def set_for_dialog(self) -> None:
        """Configure the title bar for dialog mode (no maximize functionality)."""
        self.is_dialog = True
        self._actions.set_dialog_mode(True)
        if self._quick is None:
            return
        ro = self._quick.rootObject()
        if ro is not None:
            ro.setProperty("dialogMode", True)

    def show_navigation_buttons(self, show: bool = True) -> None:
        """
        Show or hide navigation buttons.

        NOTE: This method is kept for API backward compatibility only.
        Navigation buttons are handled by CustomDialogTitleBar when used.
        This implementation does nothing as MacTitleBar only handles
        window control buttons (close/minimize/maximize).
        """
        # Intentionally empty - navigation handled by CustomDialogTitleBar

    def set_navigation_enabled(self, back_enabled: bool, forward_enabled: bool) -> None:
        """
        Enable or disable navigation buttons.

        NOTE: This method is kept for API backward compatibility only.
        Navigation state is managed by CustomDialogTitleBar's ViewModel.
        """
        # Intentionally empty - navigation handled by CustomDialogTitleBar

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        """Handle window state changes to update maximize button state."""
        if obj is self.window and event.type() == QEvent.WindowStateChange:
            self._actions.refresh_maximized_state()
        return super().eventFilter(obj, event)
