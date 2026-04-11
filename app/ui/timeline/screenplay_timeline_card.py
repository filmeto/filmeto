"""Screenplay scene card for the horizontal screenplay timeline."""

from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
)
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtCore import Qt

from app.data.screen_play.screen_play_scene import ScreenPlayScene


def build_scene_card_preview(scene: ScreenPlayScene, max_chars: int = 420) -> str:
    """Build a short plain-text preview of scene body for the card face."""
    raw = (scene.content or "").strip()
    if not raw:
        return ""
    single_line = " ".join(raw.split())
    if len(single_line) > max_chars:
        return single_line[:max_chars].rstrip() + "…"
    return single_line


class ScreenplayTimelineCard(QFrame):
    """One scene as a fixed-size card with title and screenplay excerpt."""

    def __init__(self, parent, scene: ScreenPlayScene):
        super().__init__(parent)
        self.parent_timeline = parent
        self.scene_id = scene.scene_id
        self._is_hovered = False
        self._is_selected = False

        self.setFrameStyle(QFrame.NoFrame)
        self.setLineWidth(0)
        self.setFixedSize(90, 160)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(4)

        num = (scene.scene_number or "").strip()
        head = scene.title.strip() if scene.title else ""
        if num and head:
            title_text = f"{num}. {head}"
        elif num:
            title_text = num
        else:
            title_text = head or self.scene_id

        self.title_label = QLabel(title_text)
        self.title_label.setWordWrap(True)
        title_font = QFont(self.title_label.font())
        title_font.setPointSize(9)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        fm = QFontMetrics(title_font)
        self.title_label.setMaximumHeight(fm.height() * 2 + 4)

        preview = build_scene_card_preview(scene)
        if not preview and scene.logline:
            preview = (scene.logline or "").strip()
        if not preview:
            preview = "—"

        self.body_label = QLabel(preview)
        body_font = QFont(self.body_label.font())
        body_font.setPointSize(7)
        self.body_label.setFont(body_font)
        self.body_label.setWordWrap(True)
        self.body_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.body_label.setStyleSheet("color: #c0c0c0;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.body_label, 1)

        self._update_style()

    def apply_scene(self, scene: ScreenPlayScene) -> None:
        """Update labels from latest scene data."""
        self.scene_id = scene.scene_id
        num = (scene.scene_number or "").strip()
        head = scene.title.strip() if scene.title else ""
        if num and head:
            title_text = f"{num}. {head}"
        elif num:
            title_text = num
        else:
            title_text = head or self.scene_id
        self.title_label.setText(title_text)

        preview = build_scene_card_preview(scene)
        if not preview and scene.logline:
            preview = (scene.logline or "").strip()
        if not preview:
            preview = "—"
        self.body_label.setText(preview)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.parent_timeline is not None:
            self.parent_timeline.select_scene(self.scene_id)
        super().mousePressEvent(event)

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

    def _update_style(self) -> None:
        if self._is_selected:
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #4080ff;
                    border-radius: 8px;
                }
                QLabel { background-color: transparent; border: none; }
                """
            )
        elif self._is_hovered:
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #6a9eff;
                    border-radius: 8px;
                }
                QLabel { background-color: transparent; border: none; }
                """
            )
        else:
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #2c2c2c;
                    border: 3px solid #a0a0a0;
                    border-radius: 8px;
                }
                QLabel { background-color: transparent; border: none; }
                """
            )
