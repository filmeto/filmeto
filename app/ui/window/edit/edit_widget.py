# -*- coding: utf-8 -*-
"""
Edit Widget

This widget contains the edit mode UI (the current main window layout).
It wraps the existing top bar, h_layout, and bottom bar into a single widget
that can be swapped with the startup widget.
"""
import logging
import uuid

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Signal, Qt, QTimer, Slot

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.core.base_worker import FunctionWorker
from app.ui.core.task_manager import TaskManager
from app.ui.skeleton_blocks_pulse import SkeletonBlocksPulseWidget
from .edit_preflight import PREFLIGHT_BY_STAGE
from .top_side_bar import MainWindowTopSideBar
from .bottom_side_bar import MainWindowBottomSideBar
from .h_layout import MainWindowHLayout

logger = logging.getLogger(__name__)

# Match MainWindowTopSideBar / MainWindowBottomSideBar / side bars
_TOP_BAR_H = 40
_BOTTOM_BAR_H = 28
_SIDE_W = 40


class EditWidget(BaseWidget):
    """
    Edit mode container widget.

    This wraps the existing edit mode layout:
    - Top bar (with drawing tools, settings, etc.)
    - H layout (left sidebar, workspace, right sidebar)
    - Bottom bar (timeline, playback controls)
    """

    go_home = Signal()  # Emitted when home button is clicked

    def __init__(
        self,
        window,
        workspace: Workspace,
        parent=None,
        defer_parts: bool = False,
    ):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.window = window
        self.project = workspace.get_project()
        self.setObjectName("edit_widget")
        self._defer_parts = defer_parts

        self._top_attached = False
        self._bottom_attached = False
        self._h_layout_attached = False
        self._center_attached = False

        self.top_bar = None
        self.bottom_bar = None
        self.h_layout = None

        self._preflight_cancelled = False
        self._preflight_task_ids = []
        self._pending_preflight_stage = 0
        self._edit_shell_stages_complete = False

        if defer_parts:
            self._setup_ui_shell()
            self.destroyed.connect(self._on_edit_widget_destroyed)
        else:
            self._setup_ui_full()
            self._edit_shell_stages_complete = True

    def _setup_ui_full(self):
        """Immediate full construction (non–lazy-init path)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.top_bar = MainWindowTopSideBar(self.window, self.workspace)
        self.top_bar.setObjectName("main_window_top_bar")
        if hasattr(self.top_bar, "home_clicked"):
            self.top_bar.home_clicked.connect(self.go_home.emit)
        layout.addWidget(self.top_bar)

        self.h_layout = MainWindowHLayout(self.window, self.workspace)
        layout.addWidget(self.h_layout, 1)

        self.bottom_bar = MainWindowBottomSideBar(self.workspace, self.window)
        self.bottom_bar.setObjectName("main_window_bottom_bar")
        layout.addWidget(self.bottom_bar)

    def _fill_left_right_side_skeleton(self, frame: QFrame):
        """Stacked chips matching left/right tool icon columns (MainWindowLeft/RightSideBar)."""
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(4, 10, 4, 10)
        lay.setSpacing(10)
        for _ in range(5):
            chip = QFrame()
            chip.setObjectName("edit_shell_side_chip")
            chip.setFixedSize(28, 28)
            lay.addWidget(chip, alignment=Qt.AlignHCenter)
        lay.addStretch()

    def _fill_bottom_bar_skeleton(self, frame: QFrame):
        """Centered play cluster strip matching MainWindowBottomSideBar (play controls)."""
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(10, 3, 10, 3)
        lay.setSpacing(0)
        lay.addStretch(1)
        cluster = QFrame()
        cluster.setObjectName("edit_shell_play_cluster")
        cluster.setFixedSize(132, 20)
        lay.addWidget(cluster, alignment=Qt.AlignVCenter)
        lay.addStretch(1)

    def _setup_ui_shell(self):
        """
        Outer layout matching the real edit UI: top | (left | center | right) | bottom.
        Left / right / bottom regions are explicit skeleton panels (not just flat color).
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._top_shell = QFrame()
        self._top_shell.setObjectName("edit_shell_top")
        self._top_shell.setFixedHeight(_TOP_BAR_H)

        self._middle_shell = QWidget()
        self._middle_shell.setObjectName("edit_shell_middle")
        mid = QHBoxLayout(self._middle_shell)
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(0)

        self._left_shell = QFrame()
        self._left_shell.setObjectName("edit_shell_left")
        self._left_shell.setFixedWidth(_SIDE_W)
        self._left_shell.setMinimumWidth(_SIDE_W)
        self._left_shell.setMaximumWidth(_SIDE_W)
        self._fill_left_right_side_skeleton(self._left_shell)

        self._center_shell = QWidget()
        self._center_shell.setObjectName("edit_shell_center")
        c_lay = QVBoxLayout(self._center_shell)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)

        self._canvas_shell = QFrame()
        self._canvas_shell.setObjectName("edit_shell_canvas")
        cv = QVBoxLayout(self._canvas_shell)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.addStretch()
        self._canvas_pulse = SkeletonBlocksPulseWidget(block_size=10, spacing=6, interval_ms=130)
        cv.addWidget(self._canvas_pulse, alignment=Qt.AlignCenter)
        cv.addStretch()

        self._timeline_shell = QFrame()
        self._timeline_shell.setObjectName("edit_shell_timeline")
        self._timeline_shell.setMinimumHeight(120)
        self._timeline_shell.setMaximumHeight(220)

        c_lay.addWidget(self._canvas_shell, 1)
        c_lay.addWidget(self._timeline_shell)

        self._right_shell = QFrame()
        self._right_shell.setObjectName("edit_shell_right")
        self._right_shell.setFixedWidth(_SIDE_W)
        self._right_shell.setMinimumWidth(_SIDE_W)
        self._right_shell.setMaximumWidth(_SIDE_W)
        self._fill_left_right_side_skeleton(self._right_shell)

        mid.addWidget(self._left_shell)
        mid.addWidget(self._center_shell, 1)
        mid.addWidget(self._right_shell)

        self._bottom_shell = QFrame()
        self._bottom_shell.setObjectName("edit_shell_bottom")
        self._bottom_shell.setFixedHeight(_BOTTOM_BAR_H)
        self._bottom_shell.setMinimumHeight(_BOTTOM_BAR_H)
        self._fill_bottom_bar_skeleton(self._bottom_shell)

        layout.addWidget(self._top_shell)
        layout.addWidget(self._middle_shell, 1)
        layout.addWidget(self._bottom_shell)

        self._apply_shell_styles()

    def _apply_shell_styles(self):
        self.setStyleSheet(
            "QWidget#edit_widget { background-color: #2b2b2b; }"
            "QFrame#edit_shell_top { background-color: rgba(45, 45, 48, 0.92); }"
            "QFrame#edit_shell_left {"
            " background-color: rgba(36, 37, 40, 0.98);"
            " border-right: 1px solid #3c3f41;"
            " min-width: 40px; max-width: 40px;"
            "}"
            "QFrame#edit_shell_right {"
            " background-color: rgba(36, 37, 40, 0.98);"
            " border-left: 1px solid #3c3f41;"
            " min-width: 40px; max-width: 40px;"
            "}"
            "QFrame#edit_shell_bottom {"
            " background-color: rgba(42, 43, 46, 0.98);"
            " border-top: 1px solid #3c3f41;"
            " min-height: 28px; max-height: 28px;"
            "}"
            "QFrame#edit_shell_side_chip {"
            " background-color: rgba(60, 63, 65, 0.55);"
            " border-radius: 4px;"
            "}"
            "QFrame#edit_shell_play_cluster {"
            " background-color: rgba(60, 63, 65, 0.5);"
            " border-radius: 5px;"
            "}"
            "QWidget#edit_shell_middle { background-color: #2b2b2b; }"
            "QFrame#edit_shell_canvas { background-color: #252526; border: none; }"
            "QFrame#edit_shell_timeline { background-color: #1e1e1e; "
            "border-top: 1px solid #333333; }"
        )

    def attach_top_bar(self):
        if self._top_attached or not self._defer_parts:
            return
        self._top_attached = True
        lay = self.layout()
        self.top_bar = MainWindowTopSideBar(self.window, self.workspace)
        self.top_bar.setObjectName("main_window_top_bar")
        if hasattr(self.top_bar, "home_clicked"):
            self.top_bar.home_clicked.connect(self.go_home.emit)
        lay.replaceWidget(self._top_shell, self.top_bar)
        self._top_shell.deleteLater()
        self._top_shell = None

    def attach_bottom_bar(self):
        if self._bottom_attached or not self._defer_parts:
            return
        self._bottom_attached = True
        lay = self.layout()
        self.bottom_bar = MainWindowBottomSideBar(self.workspace, self.window)
        self.bottom_bar.setObjectName("main_window_bottom_bar")
        lay.replaceWidget(self._bottom_shell, self.bottom_bar)
        self._bottom_shell.deleteLater()
        self._bottom_shell = None

    def attach_h_layout(self):
        """Left / right tool strips + center skeleton (workspace loads next)."""
        if self._h_layout_attached or not self._defer_parts:
            return
        self._h_layout_attached = True
        lay = self.layout()
        self.h_layout = MainWindowHLayout(self.window, self.workspace, defer_center=True)
        lay.replaceWidget(self._middle_shell, self.h_layout)
        self._middle_shell.deleteLater()
        self._middle_shell = None

    def attach_center_workspace(self):
        """Heavy center: canvas + timeline (MainWindowWorkspace)."""
        if self._center_attached or not self._defer_parts:
            return
        if not self.h_layout:
            return
        self._center_attached = True
        self.h_layout.attach_center_workspace()

    def _on_edit_widget_destroyed(self):
        self.cancel_staged_load()

    def cancel_staged_load(self):
        """Stop pending preflight workers (cooperative); further attach steps are skipped."""
        self._preflight_cancelled = True
        tm = TaskManager.instance()
        for tid in list(self._preflight_task_ids):
            tm.cancel(tid)
        self._preflight_task_ids.clear()

    def _attach_stage(self, idx: int) -> None:
        if idx == 0:
            self.attach_top_bar()
        elif idx == 1:
            self.attach_bottom_bar()
        elif idx == 2:
            self.attach_h_layout()
        elif idx == 3:
            self.attach_center_workspace()

    def _finalize_staged_shell(self) -> None:
        self.setStyleSheet("QWidget#edit_widget { background-color: #2b2b2b; }")
        self._edit_shell_stages_complete = True

    def _submit_stage(self, idx: int) -> None:
        if not self._defer_parts or self._preflight_cancelled:
            return
        if idx >= len(PREFLIGHT_BY_STAGE):
            self._finalize_staged_shell()
            return

        fn = PREFLIGHT_BY_STAGE[idx]
        task_id = f"edit-preflight-{idx}-{uuid.uuid4().hex[:8]}"
        worker = FunctionWorker(fn, task_id=task_id, task_type="edit_preflight")
        self._preflight_task_ids.append(task_id)
        self._pending_preflight_stage = idx

        worker.signals.finished.connect(
            self._on_preflight_worker_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.error.connect(
            self._on_preflight_worker_error,
            Qt.ConnectionType.QueuedConnection,
        )
        TaskManager.instance().submit(worker)

    @Slot(str, object)
    def _on_preflight_worker_finished(self, task_id: str, result: object) -> None:
        try:
            self._preflight_task_ids.remove(task_id)
        except ValueError:
            pass
        if self._preflight_cancelled:
            return
        idx = self._pending_preflight_stage
        self._attach_stage(idx)
        QTimer.singleShot(0, lambda: self._submit_stage(idx + 1))

    @Slot(str, str, object)
    def _on_preflight_worker_error(self, task_id: str, msg: str, exc: object) -> None:
        logger.warning(
            "Edit shell preflight stage %s failed: %s",
            self._pending_preflight_stage,
            msg,
        )
        try:
            self._preflight_task_ids.remove(task_id)
        except ValueError:
            pass
        if self._preflight_cancelled:
            return
        idx = self._pending_preflight_stage
        self._attach_stage(idx)
        QTimer.singleShot(0, lambda: self._submit_stage(idx + 1))

    def run_staged_load(self):
        """
        For each region: run import preflight on TaskManager's pool, then attach widgets
        on the GUI thread (Qt objects must stay on the main thread).
        """
        if not self._defer_parts:
            return
        if self._edit_shell_stages_complete:
            return
        self._preflight_cancelled = False
        self._submit_stage(0)

    def get_top_bar(self):
        """Get the top bar widget."""
        return self.top_bar

    def get_bottom_bar(self):
        """Get the bottom bar widget."""
        return self.bottom_bar

    def get_h_layout(self):
        """Get the horizontal layout widget."""
        return self.h_layout
