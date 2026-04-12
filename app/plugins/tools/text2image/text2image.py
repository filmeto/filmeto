from qasync import asyncSlot

from app.spi.tool import BaseTool
from app.ui.base_widget import BaseTaskWidget
from app.ui.media_selector.media_selector import MediaSelector
from utils.i18n_utils import tr
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSpacerItem, QSizePolicy


class Text2Image(BaseTool,BaseTaskWidget):

    def __init__(self, workspace, editor=None):
        super(Text2Image,self).__init__(workspace)
        self.setObjectName("tool_text_to_image")
        self.workspace = workspace
        self.workspace.connect_task_execute(self.execute)
        self.editor = editor
        self.reference_image_path = None
        self.media_selector = None

    def init_ui(self, main_editor):
        """Initialize the UI for the text2image tool"""
        # Create widget for tool configuration
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        # Create media selector for reference image with 9:16 aspect ratio
        self.media_selector = MediaSelector()
        # Set size with 9:16 aspect ratio (portrait) - height 54px, width 30px
        # This fits within the 60px max height constraint of prompt input config panel
        self.media_selector.preview_widget.setFixedSize(22, 40)
        self.media_selector.placeholder_widget.setFixedSize(22, 40)

        # Set supported types to image formats only
        self.media_selector.set_supported_types(['png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'])

        # Connect signals
        self.media_selector.file_selected.connect(self._on_image_selected)
        self.media_selector.file_cleared.connect(self._on_image_cleared)

        # Add to layout
        layout.addWidget(self.media_selector)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Set the widget in the prompt input's config panel
        main_editor.prompt_input.set_config_panel_widget(widget)

    def _on_image_selected(self, file_path):
        """Handle image selection"""
        self.reference_image_path = file_path

    def _on_image_cleared(self):
        """Handle image clearing"""
        self.reference_image_path = None

    @classmethod
    def get_tool_name(cls):
        return "text2image"

    @classmethod
    def get_tool_icon(cls):
        return "\ue60b"  # Text to image icon from iconfont.json

    @classmethod
    def get_tool_display_name(cls):
        return tr("Text to Image")

    @classmethod
    def uses_prompt_config_panel(cls):
        """This tool uses the prompt input config panel"""
        return True

    def get_media_path(self, timeline_item):
        """Get media path for text2image tool"""
        return timeline_item.get_image_path()

    def params(self):
        """Get parameters for timeline-based tasks."""
        timeline_index = self.workspace.get_project().get_timeline_index()
        timeline_item = self.workspace.get_project().get_timeline().get_item(timeline_index)
        prompt = self.editor.get_prompt() if self.editor else ""

        # Get width and height from layer manager (validates against actual images)
        layer_manager = timeline_item.get_layer_manager()
        width, height = layer_manager.get_valid_dimensions()

        # Don't set server_name or model here - let ability selection handle it
        return {
            "tool": "text2image",
            "prompt": prompt,
            "reference_image_path": self.reference_image_path,
            "width": width,
            "height": height
        }

    def params_for_shot(self, shot, prompt: str, options: dict = None) -> dict:
        """
        Get parameters for shot-based tasks (keyframe generation).

        Args:
            shot: StoryBoardShot instance
            prompt: Generation prompt
            options: Additional options (width, height, etc.)

        Returns:
            Task parameters dict
        """
        return {
            "tool": "text2image",
            "prompt": prompt,
            "reference_image_path": self.reference_image_path,
            "width": (options or {}).get("width", 1024),
            "height": (options or {}).get("height", 1024),
        }

    @asyncSlot()
    async def execute(self, task):
        # Only process text2image tasks to avoid conflicts with other tools
        if task.tool != "text2image":
            return  # Exit early if this is not a text2image task
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Processing text2image task: {task.options}")
            from server.api import FilmetoApi, FilmetoTask, Ability, ResourceInput, ResourceType
            from server.api.types import SelectionConfig, SelectionMode
            from app.data.task import TaskResult as AppTaskResult, TaskProgress as AppTaskProgress
            from server.api.types import TaskProgress as FilmetoTaskProgress, TaskResult as FilmetoTaskResult

            api = FilmetoApi()

            # Get parameters from task options
            prompt = task.options.get('prompt', '')
            width = task.options.get('width', 1024)
            height = task.options.get('height', 1024)

            logger.info(f"Text2Image: width={width}, height={height}, prompt={prompt[:50]}...")

            # Create input resources if any (e.g., reference image)
            resources = []
            reference_image_path = task.options.get('reference_image_path') or self.reference_image_path
            if reference_image_path:
                resources.append(ResourceInput(
                    type=ResourceType.LOCAL_PATH,
                    data=reference_image_path,
                    mime_type="image/png"
                ))

            # Let ability selection choose the best server and model
            # Use auto mode to select based on priority from ability_models config
            selection_config = SelectionConfig.auto()

            filmeto_task = FilmetoTask(
                ability=Ability.TEXT2IMAGE,
                selection=selection_config,
                parameters={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "n": 1,
                    "save_dir": task.path
                },
                resources=resources
            )

            logger.info(f"Text2Image: using ability selection (auto mode)")

            app_progress = AppTaskProgress(task)

            async for update in api.execute_task_stream(filmeto_task):
                if isinstance(update, FilmetoTaskProgress):
                    app_progress.on_progress(int(update.percent), update.message)
                elif isinstance(update, FilmetoTaskResult):
                    # Log which server/model was used
                    result_dict = update.dict() if hasattr(update, 'dict') else {}
                    logger.info(f"Text2Image completed: status={update.status}, server={filmeto_task.server_name}, model={filmeto_task.model_name}")

                    # Create a BaseModelResult wrapper for the FilmetoTaskResult
                    class FilmetoResultWrapper:
                        def __init__(self, filmeto_result):
                            self.filmeto_result = filmeto_result

                        def get_image_path(self):
                            return self.filmeto_result.get_image_path()

                        def get_video_path(self):
                            return self.filmeto_result.get_video_path()

                    result_wrapper = FilmetoResultWrapper(update)
                    task_result = AppTaskResult(task, result_wrapper)

                    # Route result to appropriate handler
                    if task.is_shot_task():
                        # Shot task: route to ShotTaskExecutor
                        task.project_task_manager.on_task_finished(task_result)
                    else:
                        # Timeline task: route to workspace
                        self.workspace.on_task_finished(task_result)
        except Exception as e:
            logger.error(f"Error in Text2Image.execute: {e}", exc_info=True)