import logging

from PySide6.QtWidgets import QWidget, QHBoxLayout
from qasync import asyncSlot

from app.spi.tool import BaseTool
from app.ui.base_widget import BaseTaskWidget
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class Text2Video(BaseTool, BaseTaskWidget):

    def __init__(self, workspace, editor=None):
        super().__init__(workspace)
        self.setObjectName("tool_text_to_video")
        self.workspace = workspace
        self.workspace.connect_task_execute(self.execute)
        self.editor = editor

    def init_ui(self, main_editor):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        main_editor.prompt_input.set_config_panel_widget(panel)

    @classmethod
    def get_tool_name(cls):
        return "text2video"

    @classmethod
    def get_tool_icon(cls):
        return "\ue6bd"

    @classmethod
    def get_tool_display_name(cls):
        return tr("Text to Video")

    @classmethod
    def uses_prompt_config_panel(cls):
        return True

    def get_media_path(self, timeline_item):
        return timeline_item.get_preview_path()

    def params(self):
        timeline_item = self.workspace.get_project().get_timeline().get_item(
            self.workspace.get_project().get_timeline_index()
        )
        layer_manager = timeline_item.get_layer_manager()
        width, height = layer_manager.get_valid_dimensions()
        return {
            "tool": "text2video",
            "prompt": self.editor.get_prompt() if self.editor else "",
            "width": width,
            "height": height,
            "duration": 5,
        }

    @asyncSlot()
    async def execute(self, task):
        if task.tool != "text2video":
            return
        try:
            from server.api import FilmetoApi, FilmetoTask, Ability
            from server.api.types import SelectionConfig
            from app.data.task import TaskResult as AppTaskResult, TaskProgress as AppTaskProgress
            from server.api.types import TaskProgress as FilmetoTaskProgress, TaskResult as FilmetoTaskResult

            api = FilmetoApi()
            prompt = task.options.get("prompt", "")
            width = task.options.get("width", 1024)
            height = task.options.get("height", 1024)
            duration = task.options.get("duration", 5)

            selection_config = SelectionConfig.auto()
            filmeto_task = FilmetoTask(
                ability=Ability.TEXT2VIDEO,
                selection=selection_config,
                parameters={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "duration": duration,
                    "save_dir": task.path,
                },
                resources=[],
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
            logger.error(f"Error in Text2Video.execute: {e}", exc_info=True)
