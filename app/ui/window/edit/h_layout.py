from PySide6.QtWidgets import QHBoxLayout, QFrame
from PySide6.QtCore import QTimer

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from .left_bar import LeftBar
from .right_bar import RightBar
from .workspace import MainWindowWorkspace


class MainWindowHLayout(BaseWidget):

    def __init__(self, parent, workspace: Workspace, defer_panels: bool = False):
        super(MainWindowHLayout, self).__init__(workspace)
        self.setObjectName("main_window_h_layout")
        self.parent = parent
        self._workspace_data = workspace
        self._defer_panels = defer_panels
        self._left_placeholder = None
        self._right_placeholder = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if defer_panels:
            self.left_bar = None
            self.right_bar = None
            self._left_placeholder = self._build_side_skeleton("edit_h_left_skeleton")
            layout.addWidget(self._left_placeholder)

            self.workspace = MainWindowWorkspace(self, workspace, defer_parts=True)
            layout.addWidget(self.workspace, 1)

            self._right_placeholder = self._build_side_skeleton("edit_h_right_skeleton")
            layout.addWidget(self._right_placeholder)
        else:
            self.left_bar = LeftBar(workspace, self)
            layout.addWidget(self.left_bar.get_widget())

            self.workspace = MainWindowWorkspace(self, workspace, defer_parts=False)
            layout.addWidget(self.workspace, 1)

            self.right_bar = RightBar(workspace, self)
            layout.addWidget(self.right_bar.get_widget())

            self.left_bar.connect_signals(self.workspace.workspace_top.left)
            self.right_bar.connect_signals(self.workspace.workspace_top.right)
            self.left_bar.bar.set_selected_button("actor")
            self.right_bar.bar.set_selected_button("agent")
            QTimer.singleShot(50, self._switch_to_default_panels)

    def _build_side_skeleton(self, object_name: str) -> QFrame:
        f = QFrame()
        f.setObjectName(object_name)
        f.setFixedWidth(40)
        f.setStyleSheet(
            f"QFrame#{object_name} {{"
            " background-color: rgba(36, 37, 40, 0.98);"
            " border: none;"
            "}"
        )
        return f

    def attach_left_bar_shell(self) -> None:
        """Replace outer left skeleton with tool-strip shell (chips; buttons load later)."""
        if not self._defer_panels or self.left_bar is not None:
            return
        if self._left_placeholder is None:
            return
        self.left_bar = LeftBar(self._workspace_data, self, defer_sidebar=True)
        lay = self.layout()
        idx = lay.indexOf(self._left_placeholder)
        if idx < 0:
            return
        lay.removeWidget(self._left_placeholder)
        self._left_placeholder.deleteLater()
        self._left_placeholder = None
        lay.insertWidget(idx, self.left_bar.get_widget())

    def attach_left_sidebar_content(self) -> None:
        """Load MainWindowLeftSideBar (buttons) into the strip shell."""
        if not self._defer_panels or self.left_bar is None:
            return
        self.left_bar.attach_sidebar()

    def attach_right_bar_shell(self) -> None:
        """Replace outer right skeleton with tool-strip shell."""
        if not self._defer_panels or self.right_bar is not None:
            return
        if self._right_placeholder is None:
            return
        self.right_bar = RightBar(self._workspace_data, self, defer_sidebar=True)
        lay = self.layout()
        idx = lay.indexOf(self._right_placeholder)
        if idx < 0:
            return
        lay.removeWidget(self._right_placeholder)
        self._right_placeholder.deleteLater()
        self._right_placeholder = None
        lay.insertWidget(idx, self.right_bar.get_widget())

    def attach_right_sidebar_content(self) -> None:
        """Load MainWindowRightSideBar into the strip shell."""
        if not self._defer_panels or self.right_bar is None:
            return
        self.right_bar.attach_sidebar()

    def finalize_panel_wiring(self) -> None:
        """Connect tool strips to workspace panel switchers (after workspace_top exists)."""
        if not self._defer_panels:
            return
        if self.left_bar is None or self.right_bar is None:
            return
        if (
            not hasattr(self.workspace, "workspace_top")
            or self.workspace.workspace_top is None
        ):
            return
        wt = self.workspace.workspace_top
        if not hasattr(wt, "left") or not hasattr(wt, "right"):
            return
        self.left_bar.connect_signals(wt.left)
        self.right_bar.connect_signals(wt.right)
        self.left_bar.bar.set_selected_button("actor")
        self.right_bar.bar.set_selected_button("agent")
        self._defer_panels = False
        QTimer.singleShot(50, self._switch_to_default_panels)

    def _switch_to_default_panels(self):
        """Switch to default panels after UI is rendered."""
        if not hasattr(self, "workspace") or not self.workspace:
            return

        if not hasattr(self.workspace, "workspace_top") or not self.workspace.workspace_top:
            return

        if (
            not hasattr(self.workspace.workspace_top, "left")
            or not self.workspace.workspace_top.left
        ):
            return

        if (
            not hasattr(self.workspace.workspace_top, "right")
            or not self.workspace.workspace_top.right
        ):
            return

        self.workspace.workspace_top.left.switch_to_panel("actor")
        self.workspace.workspace_top.right.switch_to_panel("agent")
