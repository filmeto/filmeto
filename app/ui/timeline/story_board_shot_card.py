"""Storyboard shot card: same outer size as VideoTimelineCard; image fills card, shot id overlays."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from app.data.story_board.story_board_shot import StoryBoardShot

if TYPE_CHECKING:
    from app.ui.timeline.story_board_timeline import StoryBoardTimeline

logger = logging.getLogger(__name__)

# Strictly aligned with video_timeline_card.VideoTimelineCard: setFixedSize(90, 160), 3px border.
SHOT_W = 90
SHOT_H = 160
SHOT_BORDER = 3


class StoryBoardShotCard(QFrame):
    """
    One shot: key moment image fills the frame; shot id overlays on bottom.

    Image is loaded asynchronously by the parent timeline to avoid blocking the UI thread.
    """

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

        # --- Basic setup (matching VideoTimelineCard) ---
        self.setFrameStyle(QFrame.NoFrame)
        self.setLineWidth(0)
        self.setFixedSize(SHOT_W, SHOT_H)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)

        # --- Layout (zero margins, single content label) ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Content label for image (fills entire card, same as VideoTimelineCard)
        self.content_label = QLabel(self)
        self.content_label.setStyleSheet(
            "QLabel { background-color: #2c2c2c; border: none; border-radius: 8px; }"
        )
        self.content_label.setScaledContents(True)
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Make label transparent to mouse events so clicks pass through to parent card
        self.content_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Always start with placeholder; image loaded async by parent timeline.
        self._set_placeholder()

        layout.addWidget(self.content_label)

        # --- Shot number overlay (absolute positioned, on top of image) ---
        # Overlay width: card width minus border margins to stay inside
        overlay_w = SHOT_W - 2 * SHOT_BORDER  # 84px
        overlay_h = 18
        display_text = shot.shot_no or shot.shot_id
        self.caption_label = QLabel(display_text, self)
        self.caption_label.setFixedSize(overlay_w, overlay_h)
        # Position inside border: x offset by SHOT_BORDER, y at bottom inside border
        self.caption_label.move(SHOT_BORDER, SHOT_H - overlay_h - SHOT_BORDER)
        cf = self.caption_label.font()
        cf.setPointSize(7)
        cf.setBold(True)
        self.caption_label.setFont(cf)
        self.caption_label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self.caption_label.setWordWrap(False)
        # Bottom corners rounded to match card's bottom border-radius (8px outer, 4px inner for overlay)
        self.caption_label.setStyleSheet(
            "QLabel { color: #f2f2f2; background-color: rgba(0, 0, 0, 0.5); border: none; "
            "border-radius: 4px; padding: 0px 4px; }"
        )
        self.caption_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.caption_label.raise_()

        # --- Initial style ---
        self._update_style()

    def set_image(self, pixmap: QPixmap) -> None:
        """Set the thumbnail image (called from main thread after async load)."""
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(
            QSize(SHOT_W, SHOT_H),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.content_label.setPixmap(scaled)

    def _set_placeholder(self) -> None:
        """Set placeholder style when no image available."""
        self.content_label.setText("")
        self.content_label.setStyleSheet("""
            QLabel {
                background-color: #2c2c2c;
                border: 1px dashed #555555;
                border-radius: 8px;
                color: #666666;
            }
        """)
        self.content_label.setPixmap(QPixmap())

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
        """Update border style based on hover and selection state (matching VideoTimelineCard)."""
        if self._is_selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #4080ff;
                    border-radius: 8px;
                }
            """)
        elif self._is_hovered:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #6a9eff;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #a0a0a0;
                    border-radius: 8px;
                }
            """)
