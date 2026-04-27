"""Wide container card for one screenplay scene wrapping a row of shot cards."""

from typing import TYPE_CHECKING, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from app.data.screen_play.screen_play_scene import ScreenPlayScene
from app.data.story_board.story_board_shot import StoryBoardShot
from utils.i18n_utils import tr

from .story_board_shot_card import SHOT_H, SHOT_W, StoryBoardShotCard

if TYPE_CHECKING:
    from app.ui.timeline.story_board_timeline import StoryBoardTimeline

_SCENE_H_PAD = 10
_SCENE_V_PAD = 4
_SCENE_HEADER_SHOT_GAP = 3
# Gap between shot cards inside a scene. Match video_timeline.timeline_layout.setSpacing(5)
# for consistent card spacing across all timeline modes.
_SCENE_INNER_SPACING = 5
_LEFT_RAIL = 5


class StoryBoardSceneCard(QFrame):
    """Outer scene strip: accent rail + header + horizontal shot row."""

    def __init__(self, parent: "StoryBoardTimeline", scene: ScreenPlayScene, shots: List[StoryBoardShot]):
        super().__init__(parent)
        self.parent_timeline = parent
        self.scene_id = scene.scene_id
        self.shot_widgets: List[StoryBoardShotCard] = []

        self.setFrameStyle(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setMouseTracking(True)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.rail = QFrame(self)
        self.rail.setFixedWidth(_LEFT_RAIL)
        self.rail.setStyleSheet(
            """
            QFrame {
                background-color: #5c6bc0;
                border: none;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
            }
            """
        )
        root.addWidget(self.rail)

        inner = QFrame(self)
        inner.setObjectName("storyBoardSceneInner")
        self.inner = inner
        self._scene_selected = False
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(_SCENE_H_PAD, _SCENE_V_PAD, _SCENE_H_PAD, _SCENE_V_PAD)
        inner_layout.setSpacing(_SCENE_HEADER_SHOT_GAP)

        num = (scene.scene_number or "").strip()
        head = (scene.title or "").strip()
        if num and head:
            header_text = f"{num}. {head}"
        elif num:
            header_text = num
        else:
            header_text = head or self.scene_id

        self.header = QLabel(header_text, inner)
        hf = self.header.font()
        hf.setPointSize(6)  # Smaller font for scene header to fit longer titles
        hf.setBold(True)
        self.header.setFont(hf)
        self.header.setWordWrap(False)
        # Enable elide mode to show "..." when text is too long
        self.header.setTextFormat(Qt.TextFormat.PlainText)
        _fm = QFontMetrics(hf)
        _header_line_h = max(_fm.height(), 11)
        self.header.setFixedHeight(_header_line_h)
        self.header.setStyleSheet("color: #e8e8e8; background: transparent;")
        self.header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        inner_layout.addWidget(self.header)

        self.shots_row = QHBoxLayout()
        self.shots_row.setContentsMargins(0, 0, 0, 0)
        self.shots_row.setSpacing(_SCENE_INNER_SPACING)

        if not shots:
            empty = QLabel(tr("No shots in this scene"), inner)
            empty.setStyleSheet("color: #888888; font-size: 9pt;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.shots_row.addWidget(empty)
        else:
            # Images loaded asynchronously by parent timeline to avoid blocking UI thread.
            for shot in shots:
                card = StoryBoardShotCard(parent, scene.scene_id, shot, None)
                self.shot_widgets.append(card)
                self.shots_row.addWidget(card, 0, Qt.AlignmentFlag.AlignTop)

        inner_layout.addLayout(self.shots_row)
        root.addWidget(inner)

        n = len(shots)
        if n == 0:
            row_w = 200
        else:
            row_w = n * SHOT_W + max(0, n - 1) * _SCENE_INNER_SPACING
        inner_min = _SCENE_H_PAD * 2 + row_w
        # Inner frame uses a 2px border on top/right/bottom; keep a few px slack so the
        # layout never under-allocates width and squeezes shot spacing (which caused borders to overlap).
        self.setMinimumWidth(_LEFT_RAIL + inner_min + 8)

        # Elide header text if too long for available width
        available_header_w = row_w  # Header width equals shot row width
        elided_text = _fm.elidedText(header_text, Qt.TextElideMode.ElideRight, available_header_w)
        self.header.setText(elided_text)

        # Header + gap + shot row (SHOT_H matches VideoTimeline card height) + vertical padding; no extra slack.
        self.setMinimumHeight(
            _SCENE_V_PAD * 2
            + _header_line_h
            + _SCENE_HEADER_SHOT_GAP
            + SHOT_H
        )
        self._update_scene_chrome()

    def set_scene_selected(self, selected: bool) -> None:
        if self._scene_selected != selected:
            self._scene_selected = selected
            self._update_scene_chrome()

    def _update_scene_chrome(self) -> None:
        """Rail + inner frame reflect whether this scene is the active selection."""
        sel = self._scene_selected
        if sel:
            self.rail.setStyleSheet(
                """
                QFrame {
                    background-color: #6b7ae8;
                    border: none;
                    border-top-left-radius: 10px;
                    border-bottom-left-radius: 10px;
                }
                """
            )
            self.inner.setStyleSheet(
                """
                QFrame#storyBoardSceneInner {
                    background-color: #2c2f3a;
                    border: 2px solid #4080ff;
                    border-left: none;
                    border-top-right-radius: 10px;
                    border-bottom-right-radius: 10px;
                }
                """
            )
        else:
            self.rail.setStyleSheet(
                """
                QFrame {
                    background-color: #5c6bc0;
                    border: none;
                    border-top-left-radius: 10px;
                    border-bottom-left-radius: 10px;
                }
                """
            )
            self.inner.setStyleSheet(
                """
                QFrame#storyBoardSceneInner {
                    background-color: #25262a;
                    border: 2px solid #4a4d57;
                    border-left: none;
                    border-top-right-radius: 10px;
                    border-bottom-right-radius: 10px;
                }
                """
            )

    def apply_shot_selection(self, scene_id: str, shot_id: Optional[str]) -> None:
        for w in self.shot_widgets:
            w.set_selected(scene_id == self.scene_id and w.shot_id == shot_id)
        self.set_scene_selected(bool(scene_id) and scene_id == self.scene_id)

    def set_card_image(self, shot_id: str, pixmap: "QPixmap") -> None:
        """Forward async-loaded thumbnail to the matching shot widget."""
        for sw in self.shot_widgets:
            if sw.shot_id == shot_id:
                sw.set_image(pixmap)
                break
