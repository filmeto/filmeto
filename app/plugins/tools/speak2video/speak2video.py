import logging
import os

from PySide6.QtWidgets import QWidget, QHBoxLayout, QSpacerItem, QSizePolicy
from qasync import asyncSlot

from app.spi.tool import BaseTool
from app.ui.base_widget import BaseTaskWidget
from app.ui.media_selector.media_selector import MediaSelector
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


def _audio_mime_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    return {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
    }.get(ext, "application/octet-stream")


class Speak2Video(BaseTool, BaseTaskWidget):

    def __init__(self, workspace, editor=None):
        super().__init__(workspace)
        self.setObjectName("tool_speak_to_video")
        self.workspace = workspace
        self.workspace.connect_task_execute(self.execute)
        self.editor = editor
        self.audio_path = None

    def init_ui(self, main_editor):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.media_selector = MediaSelector()
        self.media_selector.preview_widget.setFixedSize(30, 54)
        self.media_selector.placeholder_widget.setFixedSize(30, 54)
        self.media_selector.set_supported_types(
            ["mp3", "wav", "ogg", "m4a", "flac", "aac"]
        )
        self.media_selector.file_selected.connect(self._on_audio_selected)
        self.media_selector.file_cleared.connect(self._on_audio_cleared)

        layout.addWidget(self.media_selector)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        main_editor.prompt_input.set_config_panel_widget(panel)

    def _on_audio_selected(self, file_path):
        self.audio_path = file_path

    def _on_audio_cleared(self):
        self.audio_path = None

    @classmethod
    def get_tool_name(cls):
        return "speak2video"

    @classmethod
    def get_tool_icon(cls):
        return "\ue709"

    @classmethod
    def get_tool_display_name(cls):
        return tr("Speech to Video")

    @classmethod
    def uses_prompt_config_panel(cls):
        return True

    def get_media_path(self, timeline_item):
        return timeline_item.get_preview_path()

    def params(self):
        timeline_item=self.workspace.get_project().get_timeline().get_item(
            self.workspace.get_project().get_timeline_index()
        )
        image_path = timeline_item.get_image_path()
        return {
            "tool": "speak2video",
            "prompt": self.editor.get_prompt() if self.editor else "",
            "audio_path": self.audio_path,
            "input_image_path": image_path if image_path and os.path.isfile(image_path) else None,
        }

    @asyncSlot()
    async def execute(self, task):
        if task.tool != "speak2video":
            return
        audio_path = task.options.get("audio_path")
        if not audio_path or not os.path.isfile(audio_path):
            logger.error("Speak2Video: audio file is required")
            return
        try:
            from server.api import FilmetoApi, FilmetoTask, Ability, ResourceInput, ResourceType
            from server.api.types import SelectionConfig
            from app.data.task import TaskResult as AppTaskResult, TaskProgress as AppTaskProgress
            from server.api.types import TaskProgress as FilmetoTaskProgress, TaskResult as FilmetoTaskResult

            api = FilmetoApi()
            prompt = task.options.get("prompt", "")
            resources = [
                ResourceInput(
                    type=ResourceType.LOCAL_PATH,
                    data=audio_path,
                    mime_type=_audio_mime_type(audio_path),
                )
            ]

            selection_config = SelectionConfig.auto()
            input_image_path = task.options.get("input_image_path")
            filmeto_task = FilmetoTask(
                ability=Ability.SPEAK2VIDEO,
                selection=selection_config,
                parameters={
                    "prompt": prompt,
                    "save_dir": task.path,
                    "input_image_path": input_image_path,
                    "audio_path": audio_path,
                },
                resources=resources,
            )

            app_progress = AppTaskProgress(task)

            async for update in api.execute_task_stream(filmeto_task):
                if isinstance(update, FilmetoTaskProgress):
                    app_progress.on_progress(int(update.percent), update.message)
                elif isinstance(update, FilmetoTaskResult):
                    class FilmetoResultWrapper:
                        def __init__(self, filmeto_result):
                            self.filmeto_result = filmeto_result

                        def get_image_path(self):
                            return self.filmeto_result.get_image_path()

                        def get_video_path(self):
                            return self.filmeto_result.get_video_path()

                        def get_audio_path(self):
                            return self.filmeto_result.get_audio_path()

                    result_wrapper = FilmetoResultWrapper(update)
                    task_result = AppTaskResult(task, result_wrapper)
                    self.workspace.on_task_finished(task_result)
        except Exception as e:
            logger.error(f"Error in Speak2Video.execute: {e}", exc_info=True)
