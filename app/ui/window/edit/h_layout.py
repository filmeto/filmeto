from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QFrame, QSplitter
from PySide6.QtCore import QTimer, Qt

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from .left_bar import LeftBar
from .right_bar import RightBar
from .workspace import MainWindowWorkspace


class MainWindowHLayout(BaseWidget):

    def __init__(self, parent, workspace: Workspace, defer_center: bool = False):
        super(MainWindowHLayout, self).__init__(workspace)
        self.setObjectName("main_window_h_layout")
        self.parent = parent
        self._defer_center = defer_center
        self._center_placeholder = None
        # 主布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Initialize left bar component
        self.left_bar = LeftBar(workspace, self)
        layout.addWidget(self.left_bar.get_widget())

        if defer_center:
            self._center_placeholder = self._build_center_skeleton()
            layout.addWidget(self._center_placeholder, 1)
        else:
            # Initialize workspace (canvas + timeline)
            self.workspace = MainWindowWorkspace(self, workspace)
            layout.addWidget(self.workspace, 1)

        # Initialize right bar component
        self.right_bar = RightBar(workspace, self)
        layout.addWidget(self.right_bar.get_widget())

        if defer_center:
            self.left_bar.bar.set_selected_button('actor')
            self.right_bar.bar.set_selected_button('agent')
        else:
            # Connect left bar button clicks to panel switcher
            self.left_bar.connect_signals(self.workspace.workspace_top.left)

            # Connect right bar button clicks to panel switcher
            self.right_bar.connect_signals(self.workspace.workspace_top.right)

            # Immediately set default buttons as selected (before panel creation)
            self.left_bar.bar.set_selected_button('actor')
            self.right_bar.bar.set_selected_button('agent')

            QTimer.singleShot(50, self._switch_to_default_panels)

    def _build_center_skeleton(self) -> QWidget:
        """Placeholder matching MainWindowWorkspace vertical split (preview / timeline)."""
        w = QWidget()
        w.setObjectName("edit_h_center_skeleton")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        splitter = QSplitter(Qt.Vertical)
        splitter.setObjectName("edit_center_skeleton_splitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        top = QFrame()
        top.setObjectName("edit_center_skeleton_top")
        bottom = QFrame()
        bottom.setObjectName("edit_center_skeleton_timeline")
        bottom.setMinimumHeight(140)
        bottom.setMaximumHeight(260)

        splitter.addWidget(top)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([720, 200])

        outer.addWidget(splitter)
        w.setStyleSheet(
            "QWidget#edit_h_center_skeleton { background-color: #2b2b2b; }"
            "QFrame#edit_center_skeleton_top { background-color: #252526; border: none; }"
            "QFrame#edit_center_skeleton_timeline { background-color: #1e1e1e; "
            "border-top: 1px solid #333333; }"
        )
        return w

    def attach_center_workspace(self):
        """Swap center skeleton for MainWindowWorkspace; wire side bars (main thread)."""
        if not self._defer_center or self._center_placeholder is None:
            return
        layout = self.layout()
        ws_data = self.workspace
        mw = MainWindowWorkspace(self, ws_data)
        layout.replaceWidget(self._center_placeholder, mw)
        self._center_placeholder.deleteLater()
        self._center_placeholder = None
        self._defer_center = False
        self.workspace = mw

        self.left_bar.connect_signals(self.workspace.workspace_top.left)
        self.right_bar.connect_signals(self.workspace.workspace_top.right)
        self.left_bar.bar.set_selected_button('actor')
        self.right_bar.bar.set_selected_button('agent')
        QTimer.singleShot(50, self._switch_to_default_panels)
    
    def _switch_to_default_panels(self):
        """Switch to default panels after UI is rendered."""
        # Check if components still exist before switching (avoid segfault during transitions)
        if not hasattr(self, 'workspace') or not self.workspace:
            return

        if not hasattr(self.workspace, 'workspace_top') or not self.workspace.workspace_top:
            return

        if (not hasattr(self.workspace.workspace_top, 'left') or
            not self.workspace.workspace_top.left):
            return

        if (not hasattr(self.workspace.workspace_top, 'right') or
            not self.workspace.workspace_top.right):
            return

        # Switch to actor panel by default (panel will be created lazily)
        self.workspace.workspace_top.left.switch_to_panel('actor')

        # Switch to agent panel by default for right side (panel will be created lazily)
        self.workspace.workspace_top.right.switch_to_panel('agent')

