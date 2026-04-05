import logging
from PySide6.QtWidgets import QHBoxLayout, QFrame

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget

logger = logging.getLogger(__name__)


class MainWindowBottomSideBar(BaseWidget):

    def __init__(self, workspace, parent, defer_play_control: bool = False):
        super(MainWindowBottomSideBar, self).__init__(workspace)
        self.setObjectName("main_window_bottom_bar")
        self.parent = parent
        self.setFixedHeight(28)
        self._defer_play_control = defer_play_control
        self._play_placeholder = None
        self.play_control = None

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.layout.addStretch()

        if defer_play_control:
            self._play_placeholder = QFrame()
            self._play_placeholder.setObjectName("edit_bottom_bar_play_skeleton")
            self._play_placeholder.setFixedSize(132, 20)
            self._play_placeholder.setStyleSheet(
                "QFrame#edit_bottom_bar_play_skeleton {"
                " background-color: rgba(60, 63, 65, 0.45);"
                " border-radius: 5px;"
                "}"
            )
            self.layout.addWidget(self._play_placeholder)
        else:
            from app.ui.play_control import PlayControlWidget

            self.play_control = PlayControlWidget(workspace, self)
            self.layout.addWidget(self.play_control)
            self.play_control.previous_clicked.connect(self._on_previous_clicked)
            self.play_control.play_pause_clicked.connect(self._on_play_pause_clicked)
            self.play_control.next_clicked.connect(self._on_next_clicked)

        self.layout.addStretch()

    def attach_play_control(self) -> None:
        """Replace play skeleton with PlayControlWidget (main thread)."""
        if not self._defer_play_control or self.play_control is not None:
            return
        if self._play_placeholder is None:
            return
        from app.ui.play_control import PlayControlWidget

        lay = self.layout
        idx = lay.indexOf(self._play_placeholder)
        if idx < 0:
            return
        self.play_control = PlayControlWidget(self.workspace, self)
        lay.removeWidget(self._play_placeholder)
        self._play_placeholder.deleteLater()
        self._play_placeholder = None
        lay.insertWidget(idx, self.play_control)
        self._defer_play_control = False

        self.play_control.previous_clicked.connect(self._on_previous_clicked)
        self.play_control.play_pause_clicked.connect(self._on_play_pause_clicked)
        self.play_control.next_clicked.connect(self._on_next_clicked)

    def _on_previous_clicked(self):
        logger.info("Previous segment clicked")

    def _on_play_pause_clicked(self, is_playing: bool):
        logger.info(f"Play/Pause clicked - Playing: {is_playing}")

    def _on_next_clicked(self):
        logger.info("Next segment clicked")
