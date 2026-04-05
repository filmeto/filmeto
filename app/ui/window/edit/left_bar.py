from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCore import Qt

from app.data.workspace import Workspace
from .left_side_bar import MainWindowLeftSideBar


class LeftBar:
    """Left bar component wrapper for better management."""

    def __init__(
        self,
        workspace: Workspace,
        parent,
        defer_sidebar: bool = False,
    ):
        self.workspace = workspace
        self.parent = parent
        self.workspace_top_left = None
        self.defer_sidebar = defer_sidebar
        self.bar = None
        self._shell = None

        if defer_sidebar:
            self._shell = QFrame()
            self._shell.setObjectName("edit_left_tool_strip_shell")
            self._shell.setFixedWidth(40)
            lay = QVBoxLayout(self._shell)
            lay.setContentsMargins(4, 10, 4, 10)
            lay.setSpacing(10)
            for _ in range(5):
                chip = QFrame()
                chip.setObjectName("edit_shell_side_chip")
                chip.setFixedSize(28, 28)
                lay.addWidget(chip, alignment=Qt.AlignHCenter)
            lay.addStretch()
            self._shell.setStyleSheet(
                "QFrame#edit_left_tool_strip_shell {"
                " background-color: rgba(36, 37, 40, 0.98);"
                " border-right: 1px solid #3c3f41;"
                "}"
                "QFrame#edit_shell_side_chip {"
                " background-color: rgba(60, 63, 65, 0.55);"
                " border-radius: 4px;"
                "}"
            )
        else:
            self.bar = MainWindowLeftSideBar(workspace, parent)

    def get_widget(self):
        if self._shell is not None:
            return self._shell
        return self.bar

    def attach_sidebar(self) -> None:
        """Swap tool-strip skeleton for MainWindowLeftSideBar (main thread)."""
        if self.bar is not None or self._shell is None:
            return
        self.bar = MainWindowLeftSideBar(self.workspace, self.parent)
        lay = self.parent.layout()
        idx = lay.indexOf(self._shell)
        if idx < 0:
            return
        lay.removeWidget(self._shell)
        self._shell.deleteLater()
        self._shell = None
        lay.insertWidget(idx, self.bar)
        self.defer_sidebar = False

    def connect_signals(self, workspace_top_left):
        self.workspace_top_left = workspace_top_left
        self.bar.button_clicked.connect(workspace_top_left.switch_to_panel)
        workspace_top_left.panel_switched.connect(self.bar.set_selected_button)
