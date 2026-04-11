"""Horizontal screenplay timeline: one card per scene with text preview."""

import logging
import uuid
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMouseEvent, QKeyEvent

from app.data.screen_play import ScreenPlayManager, ScreenPlayScene
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.timeline.screenplay_timeline_card import ScreenplayTimelineCard
from app.ui.timeline.screenplay_timeline_scroll import ScreenplayTimelineScroll
from utils import qt_utils
from utils.i18n_utils import tr, translation_manager

logger = logging.getLogger(__name__)


def _sort_scenes(scenes: List[ScreenPlayScene]) -> List[ScreenPlayScene]:
    def sort_key(scene: ScreenPlayScene):
        try:
            return (True, int(scene.scene_number), str(scene.scene_number))
        except (TypeError, ValueError):
            return (False, 0, str(scene.scene_number or ""))

    out = list(scenes)
    out.sort(key=sort_key)
    return out


class AddSceneFrame(QFrame):
    """Dashed tile to add a new screenplay scene."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_timeline = parent
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #2c2c2c;
                border: 2px dashed #666666;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #3c3c3c;
                border: 2px dashed #8888ff;
            }
            """
        )
        self.setMinimumSize(90, 160)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.title_label = QLabel(tr("Add Scene"))
        self.title_label.setAlignment(Qt.AlignCenter)
        font = self.title_label.font()
        font.setPointSize(10)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.title_label)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.parent_timeline is not None:
            self.parent_timeline.add_new_scene()
        super().mousePressEvent(event)


class ScreenplayTimeline(BaseWidget):
    """Scrollable row of screenplay scene cards."""

    def __init__(self, parent: QWidget, workspace: Workspace):
        super().__init__(workspace)
        self.setWindowTitle(tr("Screenplay"))
        self.resize(parent.width(), parent.height())
        self.setContentsMargins(0, 0, 0, 0)
        self.selected_scene_id: Optional[str] = None

        self.setFixedHeight(170)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._manager: Optional[ScreenPlayManager] = None

        self.scroll_area = ScreenplayTimelineScroll()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            ScreenplayTimelineScroll {
                background-color: #1e1f22;
            }
            """
        )

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("QWidget { background-color: #1e1f22; }")
        self.timeline_layout = QHBoxLayout(self.content_widget)
        self.timeline_layout.setContentsMargins(5, 5, 5, 5)
        self.timeline_layout.setSpacing(5)
        self.scroll_area.setWidget(self.content_widget)

        self.cards: List[ScreenplayTimelineCard] = []
        self.add_scene_button = AddSceneFrame(self)
        self.timeline_layout.addWidget(self.add_scene_button)
        self.timeline_layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll_area)

        self.scroll_area.setFocusPolicy(Qt.StrongFocus)
        self.scroll_area.setFocus()

        translation_manager.language_changed.connect(self._retranslate_ui)
        self._script_timeline_has_shown = False

        self._attach_manager()
        self._rebuild_cards()

    def _attach_manager(self) -> None:
        project = self.workspace.get_project()
        if project:
            self._manager = project.get_screenplay_manager()
        else:
            self._manager = None

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(tr("Screenplay"))
        if hasattr(self, "add_scene_button") and self.add_scene_button:
            self.add_scene_button.title_label.setText(tr("Add Scene"))

    def _rebuild_cards(self) -> None:
        self._attach_manager()
        for card in self.cards:
            self.timeline_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

        self.timeline_layout.removeWidget(self.add_scene_button)
        qt_utils.remove_last_stretch(self.timeline_layout)

        if not self._manager:
            self.timeline_layout.addWidget(self.add_scene_button)
            self.timeline_layout.addStretch()
            self.selected_scene_id = None
            return

        scenes = _sort_scenes(self._manager.list_scenes())
        for scene in scenes:
            card = ScreenplayTimelineCard(self, scene)
            self.timeline_layout.addWidget(card)
            self.cards.append(card)

        self.timeline_layout.addWidget(self.add_scene_button)
        self.timeline_layout.addStretch()

        if self.selected_scene_id:
            ids = {c.scene_id for c in self.cards}
            if self.selected_scene_id not in ids:
                self.selected_scene_id = None

        if scenes:
            if not self.selected_scene_id:
                self.selected_scene_id = scenes[0].scene_id
            self._apply_selection_highlight()
        else:
            self.selected_scene_id = None

        if hasattr(self.parent(), "update_unified_scroll_range"):
            self.parent().update_unified_scroll_range()

    def select_scene(self, scene_id: str) -> None:
        self.selected_scene_id = scene_id
        self._apply_selection_highlight()

    def _apply_selection_highlight(self) -> None:
        for card in self.cards:
            card.set_selected(card.scene_id == self.selected_scene_id)

    def add_new_scene(self) -> None:
        if not self._manager:
            self._attach_manager()
        if not self._manager:
            logger.warning("No screenplay manager; cannot add scene")
            return
        scene_index = len(self._manager.list_scenes()) + 1
        scene_id = f"scene_{uuid.uuid4().hex[:8]}"
        new_scene = ScreenPlayScene(
            scene_id=scene_id,
            title=f"Scene {scene_index}",
            content="",
            scene_number=str(scene_index),
        )
        ok = self._manager.create_scene(
            scene_id=new_scene.scene_id,
            title=new_scene.title,
            content=new_scene.content,
            metadata=new_scene.to_dict(),
        )
        if ok:
            self.selected_scene_id = scene_id
            self._rebuild_cards()
        else:
            logger.error("Failed to create screenplay scene %s", scene_id)

    def set_content_width(self, width: int) -> None:
        """Match unified horizontal scroll range with other timelines."""
        self.content_widget.setMinimumWidth(width)

    def on_project_switched(self, project_name: str) -> None:
        self.selected_scene_id = None
        self._rebuild_cards()

    def showEvent(self, event):
        super().showEvent(event)
        if self._script_timeline_has_shown:
            QTimer.singleShot(0, self._rebuild_cards)
        else:
            self._script_timeline_has_shown = True

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
