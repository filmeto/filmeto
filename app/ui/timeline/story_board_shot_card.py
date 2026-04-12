"""Storyboard shot card: same footprint and chrome as video timeline cards (keyframe + caption)."""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from app.data.story_board.story_board_shot import StoryBoardShot

if TYPE_CHECKING:
    from app.ui.timeline.story_board_timeline import StoryBoardTimeline

SHOT_W = 90
SHOT_H = 160
IMAGE_H = 128
CAPTION_H = 32


class StoryBoardShotCard(QFrame):
    """One shot: key moment image (or placeholder) with title strip; borders match VideoTimelineCard."""

    def __init__(
        self,
        parent: "StoryBoardTimeline",
        scene_id: str,
        shot: StoryBoardShot,
        key_moment_path: Optional[Path],
    ):
        super().__init__(parent)
        self.parent_timeline = parent
        self.scene_id = scene_id
        self.shot_id = shot.shot_id
        self._is_hovered = False
        self._is_selected = False

        self.setFrameStyle(QFrame.NoFrame)
        self.setLineWidth(0)
        self.setFixedSize(SHOT_W, SHOT_H)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel(self)
        self.image_label.setFixedSize(SHOT_W, IMAGE_H)
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            "QLabel { background-color: #2c2c2c; border: none; border-top-left-radius: 8px; border-top-right-radius: 8px; }"
        )

        title = (shot.title or "").strip() or shot.shot_id
        self.caption_label = QLabel(title, self)
        self.caption_label.setFixedHeight(CAPTION_H)
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_label.setWordWrap(True)
        cf = self.caption_label.font()
        cf.setPointSize(8)
        self.caption_label.setFont(cf)
        self.caption_label.setStyleSheet("color: #c8c8c8; background-color: transparent;")
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.caption_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout.addWidget(self.image_label)
        layout.addWidget(self.caption_label)

        self._apply_image(key_moment_path)
        self._update_style()

    def _apply_image(self, path: Optional[Path]) -> None:
        if path is not None and path.is_file():
            pix = QPixmap(str(path))
            if not pix.isNull():
                scaled = pix.scaled(
                    QSize(SHOT_W, IMAGE_H),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled)
                return
        self.image_label.setText("")
        self.image_label.setStyleSheet(
            """
            QLabel {
                background-color: #2c2c2c;
                border: 1px dashed #555555;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                color: #666666;
            }
            """
        )
        self.image_label.setPixmap(QPixmap())

    def set_selected(self, selected: bool) -> None:
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_style()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._is_hovered = True
        self._update_style()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._is_hovered = False
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.parent_timeline is not None:
            self.parent_timeline.select_shot(self.scene_id, self.shot_id)
        super().mousePressEvent(event)

    def _update_style(self) -> None:
        if self._is_selected:
            border = "#4080ff"
        elif self._is_hovered:
            border = "#6a9eff"
        else:
            border = "#a0a0a0"
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: #2c2c2c;
                border: 3px solid {border};
                border-radius: 8px;
            }}
            """
        )
