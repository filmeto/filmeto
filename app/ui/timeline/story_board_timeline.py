"""Storyboard timeline: wide scene cards, each containing video-style shot cards."""

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.data.screen_play import ScreenPlayManager, ScreenPlayScene
from app.data.story_board import StoryBoardManager
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.signals import Signals
from app.ui.timeline.story_board_scene_card import StoryBoardSceneCard
from app.ui.timeline.story_board_timeline_scroll import StoryBoardTimelineScroll
from utils import qt_utils
from utils.i18n_utils import tr, translation_manager
from utils.qt_utils import ancestor_widget_with_attr


def _sort_scenes(scenes: List[ScreenPlayScene]) -> List[ScreenPlayScene]:
    def sort_key(scene: ScreenPlayScene):
        try:
            return (True, int(scene.scene_number), str(scene.scene_number))
        except (TypeError, ValueError):
            return (False, 0, str(scene.scene_number or ""))

    out = list(scenes)
    out.sort(key=sort_key)
    return out


def _sort_shot_ids(shot_ids: List[str]) -> List[str]:
    return sorted(shot_ids, key=lambda s: (len(s), s.lower()))


class StoryBoardTimeline(BaseWidget):
    """Horizontal row of scene container cards, each with an inner strip of shot cards."""

    def __init__(self, parent: QWidget, workspace: Workspace):
        super().__init__(workspace)
        self.setWindowTitle(tr("Storyboard timeline"))
        self.resize(parent.width(), parent.height())
        self.setContentsMargins(0, 0, 0, 0)
        self.selected_scene_id: Optional[str] = None
        self.selected_shot_id: Optional[str] = None

        self.setFixedHeight(204)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._screenplay_manager: Optional[ScreenPlayManager] = None
        self.story_board_manager: Optional[StoryBoardManager] = None

        self.scroll_area = StoryBoardTimelineScroll()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            StoryBoardTimelineScroll {
                background-color: #1e1f22;
            }
            """
        )

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("QWidget { background-color: #1e1f22; }")
        self._strip = QWidget(self.content_widget)
        self._scene_row_layout = QHBoxLayout(self._strip)
        self._scene_row_layout.setContentsMargins(5, 4, 5, 4)
        self._scene_row_layout.setSpacing(10)

        outer = QVBoxLayout(self.content_widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._strip)

        self.scroll_area.setWidget(self.content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll_area)

        self.scroll_area.setFocusPolicy(Qt.StrongFocus)
        self.scroll_area.setFocus()

        self.scene_cards: List[StoryBoardSceneCard] = []
        self._story_timeline_has_shown = False

        translation_manager.language_changed.connect(self._retranslate_ui)
        self._attach_managers()
        self._rebuild_scene_strip()

    def _attach_managers(self) -> None:
        project = self.workspace.get_project()
        if project:
            self._screenplay_manager = project.get_screenplay_manager()
            self.story_board_manager = project.get_story_board_manager()
        else:
            self._screenplay_manager = None
            self.story_board_manager = None

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(tr("Storyboard timeline"))

    def compute_content_width(self) -> int:
        margins = 10
        if not self.scene_cards:
            return max(800, margins + 400)
        gap = 10 * max(0, len(self.scene_cards) - 1)
        return margins + gap + sum(c.minimumWidth() for c in self.scene_cards)

    def _rebuild_scene_strip(self) -> None:
        self._attach_managers()
        for card in self.scene_cards:
            self._scene_row_layout.removeWidget(card)
            card.deleteLater()
        self.scene_cards.clear()

        qt_utils.remove_last_stretch(self._scene_row_layout)

        if not self._screenplay_manager or not self.story_board_manager:
            empty = QLabel(tr("No project"), self._strip)
            empty.setStyleSheet("color: #888888;")
            self._scene_row_layout.addWidget(empty)
            self._scene_row_layout.addStretch()
            self._apply_shot_selection_highlight()
            return

        scenes = _sort_scenes(self._screenplay_manager.list_scenes())
        if not scenes:
            empty = QLabel(tr("No screenplay scenes"), self._strip)
            empty.setStyleSheet("color: #888888;")
            self._scene_row_layout.addWidget(empty)
            self._scene_row_layout.addStretch()
            self._apply_shot_selection_highlight()
            c = ancestor_widget_with_attr(self, "update_unified_scroll_range")
            if c is not None:
                c.update_unified_scroll_range()
            return

        for scene in scenes:
            ids = _sort_shot_ids(self.story_board_manager.list_shot_ids(scene.scene_id))
            shots = []
            for sid in ids:
                sh = self.story_board_manager.get_shot(scene.scene_id, sid)
                if sh:
                    shots.append(sh)
            card = StoryBoardSceneCard(self, scene, shots)
            self._scene_row_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignTop)
            self.scene_cards.append(card)

        self._scene_row_layout.addStretch()
        if self.scene_cards:
            first = self.scene_cards[0]
            if first.shot_widgets:
                self.select_shot(first.scene_id, first.shot_widgets[0].shot_id)
            else:
                self.selected_scene_id = None
                self.selected_shot_id = None
                self._apply_shot_selection_highlight()
        else:
            self._apply_shot_selection_highlight()

        c = ancestor_widget_with_attr(self, "update_unified_scroll_range")
        if c is not None:
            c.update_unified_scroll_range()

    def set_content_width(self, width: int) -> None:
        self.content_widget.setMinimumWidth(width)

    def select_shot(self, scene_id: str, shot_id: str) -> None:
        self.selected_scene_id = scene_id
        self.selected_shot_id = shot_id
        self._apply_shot_selection_highlight()
        Signals().send(
            Signals.STORYBOARD_SHOT_SELECTED,
            params={"scene_id": scene_id, "shot_id": shot_id},
        )

    def _apply_shot_selection_highlight(self) -> None:
        for card in self.scene_cards:
            card.apply_shot_selection(
                self.selected_scene_id or "",
                self.selected_shot_id,
            )

    def on_project_switched(self, project_name: str) -> None:
        self.selected_scene_id = None
        self.selected_shot_id = None
        self._rebuild_scene_strip()

    def showEvent(self, event):
        super().showEvent(event)
        if self._story_timeline_has_shown:
            QTimer.singleShot(0, self._rebuild_scene_strip)
        else:
            self._story_timeline_has_shown = True

    def keyPressEvent(self, event):
        if isinstance(event, QKeyEvent):
            scroll_bar = self.scroll_area.horizontalScrollBar()
            current_value = scroll_bar.value()
            if event.key() == Qt.Key_Left:
                scroll_bar.setValue(current_value - 50)
                return
            if event.key() == Qt.Key_Right:
                scroll_bar.setValue(current_value + 50)
                return
        super().keyPressEvent(event)
