"""Storyboard timeline: wide scene cards, each containing video-style shot cards."""

from typing import List, Optional, Tuple

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
from utils.qt_utils import ancestor_widget_with_attr, widget_left_x_in_content


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
        self._connected_story_board_manager: Optional[StoryBoardManager] = None

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
        self._scene_row_layout.setSpacing(5)  # Match video_timeline.timeline_layout spacing

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
        self._connect_storyboard_events()

    def _connect_storyboard_events(self) -> None:
        """Keep a single active subscription to storyboard shot changes."""
        if self._connected_story_board_manager is self.story_board_manager:
            return
        if self._connected_story_board_manager is not None:
            try:
                self._connected_story_board_manager.disconnect_shot_changed(
                    self._on_storyboard_shot_changed
                )
            except Exception:
                pass
        self._connected_story_board_manager = self.story_board_manager
        if self._connected_story_board_manager is not None:
            self._connected_story_board_manager.connect_shot_changed(
                self._on_storyboard_shot_changed
            )

    def _on_storyboard_shot_changed(self, sender, params=None, **kwargs) -> None:
        """Refresh timeline immediately when shots are mutated in storyboard editor."""
        self._rebuild_scene_strip()

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
        """Select a shot and emit signal to sync with editor."""
        self.selected_scene_id = scene_id
        self.selected_shot_id = shot_id
        self._apply_shot_selection_highlight()
        Signals().send(
            Signals.STORYBOARD_SHOT_SELECTED,
            params={"scene_id": scene_id, "shot_id": shot_id},
        )

    def select_shot_no_signal(self, scene_id: str, shot_id: str) -> None:
        """Select a shot WITHOUT emitting signal (used when syncing from editor to prevent circular)."""
        self.selected_scene_id = scene_id
        self.selected_shot_id = shot_id
        self._apply_shot_selection_highlight()

    def select_scene(self, scene_id: str) -> None:
        """Select a scene when no shot is available and emit sync signal."""
        self.selected_scene_id = scene_id
        self.selected_shot_id = None
        self._apply_shot_selection_highlight()
        Signals().send(
            Signals.STORYBOARD_SHOT_SELECTED,
            params={"scene_id": scene_id, "shot_id": None},
        )

    def _pick_shot_for_content_x(
        self, card: StoryBoardSceneCard, content_x: float, cw: QWidget
    ) -> Optional[Tuple[str, str]]:
        """Map horizontal content_x to (scene_id, shot_id) within one scene card."""
        shots = card.shot_widgets
        if not shots:
            return None
        for sh in shots:
            sl = widget_left_x_in_content(sh, cw)
            sr = sl + float(sh.width())
            if sl <= content_x < sr:
                return (card.scene_id, sh.shot_id)
        best_pair = None
        best_d = float("inf")
        for sh in shots:
            sl = widget_left_x_in_content(sh, cw)
            sr = sl + float(sh.width())
            mid = 0.5 * (sl + sr)
            d = abs(content_x - mid)
            if d < best_d:
                best_d = d
                best_pair = (card.scene_id, sh.shot_id)
        return best_pair

    def select_at_content_x(self, content_x: float) -> bool:
        """
        Select the shot whose card best matches horizontal position in content_widget coords.

        Handles scene headers, rail, gaps between scenes, and padding before/after the strip.
        """
        cw = self.content_widget
        if not self.scene_cards:
            return False

        bounds = []
        for card in self.scene_cards:
            left = widget_left_x_in_content(card, cw)
            right = left + float(card.width())
            bounds.append((card, left, right))

        for card, left, right in bounds:
            if left <= content_x < right:
                pair = self._pick_shot_for_content_x(card, content_x, cw)
                if pair:
                    self.select_shot(pair[0], pair[1])
                    return True
                self.select_scene(card.scene_id)
                return True

        first_card, first_left, _ = bounds[0]
        last_card, _, last_right = bounds[-1]

        if content_x < first_left:
            if first_card.shot_widgets:
                self.select_shot(first_card.scene_id, first_card.shot_widgets[0].shot_id)
                return True
            self.select_scene(first_card.scene_id)
            return True

        if content_x >= last_right:
            if last_card.shot_widgets:
                self.select_shot(last_card.scene_id, last_card.shot_widgets[-1].shot_id)
                return True
            self.select_scene(last_card.scene_id)
            return True

        for i in range(len(bounds) - 1):
            _ca, _la, r0 = bounds[i]
            _cb, l1, _rb = bounds[i + 1]
            if r0 <= content_x < l1:
                mid = 0.5 * (r0 + l1)
                pick = _ca if content_x < mid else _cb
                if pick.shot_widgets:
                    if content_x < mid:
                        sid = pick.shot_widgets[-1].shot_id
                    else:
                        sid = pick.shot_widgets[0].shot_id
                    self.select_shot(pick.scene_id, sid)
                    return True
                self.select_scene(pick.scene_id)
                return True

        return False

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
