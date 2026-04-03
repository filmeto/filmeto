import os
import logging
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from utils.i18n_utils import tr
from utils.yaml_utils import load_yaml

from app.ui.worker.async_data_loader import AsyncDataLoaderMixin

logger = logging.getLogger(__name__)

PREVIEW_LOAD_DEBOUNCE_MS = 200


def _resolve_task_preview_result_files(
    config_path: str,
    project_path: Optional[str],
    task_path: Optional[str],
) -> List[str]:
    """Collect existing media paths from task config / directory (thread-safe, no Qt)."""
    result_files: List[str] = []
    try:
        task_config = load_yaml(config_path) or {} if config_path else {}

        resources = task_config.get("resources", [])
        if resources:
            for resource_info in resources:
                resource_path = resource_info.get("resource_path", "")
                if resource_path and project_path:
                    absolute_path = os.path.join(project_path, resource_path)
                    if os.path.exists(absolute_path):
                        result_files.append(absolute_path)
        else:
            image_path = task_config.get("image_resource_path", "")
            video_path = task_config.get("video_resource_path", "")

            if image_path and project_path:
                absolute_path = os.path.join(project_path, image_path)
                if os.path.exists(absolute_path):
                    result_files.append(absolute_path)

            if video_path and project_path:
                absolute_path = os.path.join(project_path, video_path)
                if os.path.exists(absolute_path):
                    result_files.append(absolute_path)

        if not result_files and task_path and os.path.exists(task_path):
            for filename in os.listdir(task_path):
                if filename.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".mp4", ".avi", ".mov", ".webm")
                ):
                    result_files.append(os.path.join(task_path, filename))
    except Exception as e:
        logger.error("Error loading resources from task config: %s", e)
        if task_path and os.path.exists(task_path):
            for filename in os.listdir(task_path):
                if filename.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".mp4", ".avi", ".mov", ".webm")
                ):
                    result_files.append(os.path.join(task_path, filename))

    return result_files


class TaskItemPreviewWidget(QWidget, AsyncDataLoaderMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.task = None
        self.init_ui()
        self.setup_async_loader(
            loader_func=self._load_preview_file_list,
            on_loaded=self._on_preview_files_loaded,
            on_error=self._on_preview_files_failed,
            debounce_ms=PREVIEW_LOAD_DEBOUNCE_MS,
            cache_enabled=True,
        )

    def init_ui(self):
        # Set window properties
        self.setWindowTitle(tr("Task Preview"))
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)  # Make it a floating tool window without title bar

        self.setGeometry(0, 0, 300, 400)

        # Set a minimal dark theme style - only border, no background
        self.setStyleSheet(
            """
            QWidget {
                background-color: transparent;
                border: 1px solid #505254;
                border-radius: 4px;
            }
        """
        )

        # Create the layout for the preview panel - minimal margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Preview content area - simplified, no scroll area wrapper
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.content_layout.setSpacing(2)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.content_widget)

        # Hide initially
        self.hide()

    def _preview_key(self):
        t = self.task
        config_path = getattr(t, "config_path", None) or ""
        mtime = 0
        if config_path and os.path.isfile(config_path):
            try:
                mtime = int(os.path.getmtime(config_path))
            except OSError:
                mtime = 0
        project_path = None
        if hasattr(t, "task_manager") and hasattr(t.task_manager, "project"):
            project_path = getattr(t.task_manager.project, "project_path", None)
        task_path = getattr(t, "path", None) or ""
        return (t.task_id, config_path, project_path or "", task_path, mtime)

    def _load_preview_file_list(self, key):
        _task_id, config_path, project_path, task_path, _mtime = key
        pp = project_path or None
        tp = task_path or None
        return _resolve_task_preview_result_files(config_path, pp, tp)

    def _on_preview_files_loaded(self, key, result_files: List[str]):
        if not self.task or self.task.task_id != key[0]:
            return
        self._build_preview_ui(result_files)
        self.adjustSize()

    def _on_preview_files_failed(self, key, msg: str):
        logger.error("Task preview load failed: %s", msg)
        if not self.task or self.task.task_id != key[0]:
            return
        self.adjustSize()

    def set_task(self, task):
        """Set the task to preview"""
        self.cancel_async_pending()
        self.invalidate_async_cache()
        self.task = task
        self.populate_preview()

    @staticmethod
    def _stop_preview_media_widget(widget: QWidget) -> None:
        player = getattr(widget, "_media_player", None)
        if player is not None:
            player.stop()
            player.setSource(QUrl())

    def populate_preview(self):
        """Populate the preview panel with the selected task's content"""
        if not self.task:
            return

        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget is not None:
                self._stop_preview_media_widget(widget)
                widget.setParent(None)
                widget.deleteLater()

        self.schedule_async_load(self._preview_key(), force=False)

    def _build_preview_ui(self, result_files: List[str]):
        max_preview_size = 280

        for filepath in result_files:
            filename = os.path.basename(filepath)

            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                try:
                    pixmap = QPixmap(filepath)
                    if not pixmap.isNull():
                        original_size = pixmap.size()
                        if (
                            original_size.width() > max_preview_size
                            or original_size.height() > max_preview_size
                        ):
                            scaled_pixmap = pixmap.scaled(
                                max_preview_size,
                                max_preview_size,
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation,
                            )
                        else:
                            scaled_pixmap = pixmap

                        img_label = QLabel()
                        img_label.setPixmap(scaled_pixmap)
                        img_label.setAlignment(Qt.AlignCenter)
                        img_label.setStyleSheet("background-color: transparent;")
                        self.content_layout.addWidget(img_label)
                except Exception as e:
                    logger.error("Error loading image %s: %s", filepath, e)

            elif filename.lower().endswith((".mp4", ".avi", ".mov", ".webm")):
                video_widget = QVideoWidget()
                video_widget.setMinimumSize(max_preview_size, max_preview_size)
                video_widget.setMaximumSize(max_preview_size, max_preview_size)
                video_widget.setStyleSheet("background-color: #000000;")

                media_player = QMediaPlayer()
                audio_output = QAudioOutput()
                media_player.setAudioOutput(audio_output)
                media_player.setVideoOutput(video_widget)

                url = QUrl.fromLocalFile(filepath)
                media_player.setSource(url)

                video_widget._media_player = media_player

                play_button = QPushButton("▶")
                play_button.setFixedSize(40, 40)
                play_button.setStyleSheet(
                    """
                    QPushButton {
                        background-color: rgba(90, 110, 127, 200);
                        color: white;
                        border: none;
                        border-radius: 20px;
                        font-weight: bold;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background-color: rgba(120, 141, 162, 220);
                    }
                """
                )

                video_widget._play_button = play_button

                def toggle_playback():
                    if media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                        media_player.pause()
                        play_button.setText("▶")
                    else:
                        media_player.play()
                        play_button.setText("⏸")

                play_button.clicked.connect(toggle_playback)

                def on_playback_state_changed(state):
                    if state == QMediaPlayer.PlaybackState.PlayingState:
                        play_button.setText("⏸")
                    else:
                        play_button.setText("▶")

                media_player.playbackStateChanged.connect(on_playback_state_changed)

                container_widget = QWidget()
                container_widget._media_player = media_player
                container_layout = QVBoxLayout(container_widget)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(2)
                container_layout.setAlignment(Qt.AlignCenter)

                container_layout.addWidget(video_widget)

                button_layout = QHBoxLayout()
                button_layout.addStretch()
                button_layout.addWidget(play_button)
                button_layout.addStretch()
                container_layout.addLayout(button_layout)

                self.content_layout.addWidget(container_widget)

                media_player.play()
