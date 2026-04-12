from PySide6.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
)
from PySide6.QtCore import Qt, QTimer

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.editor import MainEditorWidget
from app.ui.signals import Signals
from app.ui.workspace import ScreenPlayCenterWidget, StoryBoardCenterWidget

CENTER_PAGE_VIDEO = 0
CENTER_PAGE_SCREENPLAY = 1
CENTER_PAGE_STORYBOARD = 2


class MainWindowWorkspaceTop(BaseWidget):

    def __init__(self, parent, workspace):
        super(MainWindowWorkspaceTop, self).__init__(workspace)
        self.setObjectName("main_window_workspace_top")
        # Do not use name "parent" — it shadows QObject.parent().
        self._workspace_parent = parent
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.splitter = QSplitter(Qt.Horizontal)
        self.setObjectName("main_window_workspace_top_splitter")
        self.splitter.setChildrenCollapsible(False)

        from app.ui.panels import MainWindowWorkspaceTopLeftBar
        self.left = MainWindowWorkspaceTopLeftBar(workspace, self)
        self.left.setObjectName("main_window_workspace_top_left")
        self.left.setMinimumWidth(240)
        self.left.setMaximumWidth(240)
        self.splitter.addWidget(self.left)

        self.center_stack = QStackedWidget()
        self.center_stack.setObjectName("main_window_workspace_center_stack")
        self.canvas_editor = MainEditorWidget(workspace)
        self.screenplay_center = ScreenPlayCenterWidget(workspace)
        self.storyboard_center = StoryBoardCenterWidget(workspace)
        self.center_stack.addWidget(self.canvas_editor)
        self.center_stack.addWidget(self.screenplay_center)
        self.center_stack.addWidget(self.storyboard_center)
        self.splitter.addWidget(self.center_stack)

        from app.ui.panels.workspace_top_right_bar import MainWindowWorkspaceTopRightBar
        self.right = MainWindowWorkspaceTopRightBar(workspace, self)
        self.right.setObjectName("main_window_workspace_top_right")
        self.right.setMinimumWidth(100)
        self.right.setMaximumWidth(350)
        self.splitter.addWidget(self.right)

        self.splitter.setSizes([200, 1000, 350])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)

        self.layout.addWidget(self.splitter)

        self.center = self.canvas_editor

        Signals().connect(Signals.TIMELINE_MODE_CHANGED, self._on_timeline_mode_changed_ui)
        Signals().connect(Signals.SCREENPLAY_SCENE_SELECTED, self._on_screenplay_scene_selected_ui)
        Signals().connect(Signals.STORYBOARD_SHOT_SELECTED, self._on_storyboard_shot_selected_ui)

    def _on_timeline_mode_changed_ui(self, sender, params=None, **kwargs):
        if params is None:
            return
        mode = params
        if mode == "video":
            self.center_stack.setCurrentIndex(CENTER_PAGE_VIDEO)
        elif mode == "script":
            self.center_stack.setCurrentIndex(CENTER_PAGE_SCREENPLAY)
            self.screenplay_center.load_data()
            QTimer.singleShot(0, self._sync_screenplay_editor_from_timeline)
        elif mode == "storyboard":
            self.center_stack.setCurrentIndex(CENTER_PAGE_STORYBOARD)
            self.storyboard_center.load_data()
            QTimer.singleShot(0, self._sync_storyboard_from_timeline)

    def _sync_storyboard_from_timeline(self):
        parent_ws = self._workspace_parent
        if not parent_ws:
            return
        bottom = getattr(parent_ws, "workspace_bottom", None)
        if not bottom:
            return
        tc = getattr(bottom, "timeline_container", None)
        if not tc or not tc.story_board_timeline:
            return
        sid = tc.story_board_timeline.selected_scene_id
        if sid:
            self.storyboard_center.open_scene(sid)

    def _sync_screenplay_editor_from_timeline(self):
        parent_ws = self._workspace_parent
        if not parent_ws:
            return
        bottom = getattr(parent_ws, "workspace_bottom", None)
        if not bottom:
            return
        tc = getattr(bottom, "timeline_container", None)
        if not tc or not tc.script_timeline:
            return
        sid = tc.script_timeline.selected_scene_id
        if sid:
            self.screenplay_center.open_scene(sid)

    def _on_screenplay_scene_selected_ui(self, sender, params=None, **kwargs):
        if params is None:
            return
        scene_id = params
        if not isinstance(scene_id, str) or not scene_id:
            return
        self.screenplay_center.open_scene(scene_id)

    def _on_storyboard_shot_selected_ui(self, sender, params=None, **kwargs):
        if not params or not isinstance(params, dict):
            return
        scene_id = params.get("scene_id")
        if isinstance(scene_id, str) and scene_id:
            self.storyboard_center.open_scene(scene_id)
