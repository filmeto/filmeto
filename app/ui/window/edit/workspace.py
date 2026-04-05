from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QSplitter, QWidget, QFrame
from PySide6.QtCore import Qt

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.skeleton_blocks_pulse import SkeletonBlocksPulseWidget
from .workspace_top import MainWindowWorkspaceTop
from .workspace_bottom import MainWindowWorkspaceBottom


class MainWindowWorkspace(BaseWidget):

    def __init__(self, parent, workspace: Workspace, defer_parts: bool = False):
        super(MainWindowWorkspace, self).__init__(workspace)
        self.setObjectName("main_window_workspace")
        self.parent = parent
        self._defer_parts = defer_parts

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setObjectName("main_window_workspace_splitter")
        self.splitter.setChildrenCollapsible(False)

        self.workspace_top = None
        self.workspace_bottom = None
        self._canvas_placeholder = None
        self._timeline_placeholder = None

        if defer_parts:
            self._canvas_placeholder = self._build_canvas_skeleton()
            self._timeline_placeholder = self._build_timeline_skeleton()
            self.splitter.addWidget(self._canvas_placeholder)
            self.splitter.addWidget(self._timeline_placeholder)
        else:
            self.workspace_top = MainWindowWorkspaceTop(self, workspace)
            self.splitter.addWidget(self.workspace_top)

            self.workspace_bottom = MainWindowWorkspaceBottom(self, workspace)
            self.splitter.addWidget(self.workspace_bottom)

        self.splitter.setSizes([1200, 200])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

        self.layout.addWidget(self.splitter)

    def _build_canvas_skeleton(self) -> QWidget:
        """Placeholder for MainWindowWorkspaceTop (editor / canvas region)."""
        w = QWidget()
        w.setObjectName("edit_workspace_canvas_skeleton")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch()
        pulse = SkeletonBlocksPulseWidget(block_size=10, spacing=6, interval_ms=130)
        lay.addWidget(pulse, alignment=Qt.AlignCenter)
        lay.addStretch()
        w.setStyleSheet(
            "QWidget#edit_workspace_canvas_skeleton { background-color: #252526; }"
        )
        return w

    def _build_timeline_skeleton(self) -> QFrame:
        """Placeholder for MainWindowWorkspaceBottom (timeline)."""
        f = QFrame()
        f.setObjectName("edit_workspace_timeline_skeleton")
        f.setMinimumHeight(140)
        f.setMaximumHeight(260)
        f.setStyleSheet(
            "QFrame#edit_workspace_timeline_skeleton {"
            " background-color: #1a1a1c;"
            " border-top: 1px solid #3c3f41;"
            "}"
        )
        return f

    def attach_workspace_top(self) -> None:
        """Replace canvas skeleton with MainWindowWorkspaceTop (main thread)."""
        if not self._defer_parts or self._canvas_placeholder is None:
            return
        if self.workspace_top is not None:
            return
        ws = self.workspace
        idx = self.splitter.indexOf(self._canvas_placeholder)
        if idx < 0:
            return
        self.workspace_top = MainWindowWorkspaceTop(self, ws)
        replaced = self.splitter.replaceWidget(idx, self.workspace_top)
        if replaced is not None:
            replaced.deleteLater()
        self._canvas_placeholder = None

    def attach_workspace_bottom(self) -> None:
        """Replace timeline skeleton with MainWindowWorkspaceBottom (main thread)."""
        if not self._defer_parts or self._timeline_placeholder is None:
            return
        if self.workspace_bottom is not None:
            return
        ws = self.workspace
        idx = self.splitter.indexOf(self._timeline_placeholder)
        if idx < 0:
            return
        self.workspace_bottom = MainWindowWorkspaceBottom(self, ws)
        replaced = self.splitter.replaceWidget(idx, self.workspace_bottom)
        if replaced is not None:
            replaced.deleteLater()
        self._timeline_placeholder = None
        self._defer_parts = False
