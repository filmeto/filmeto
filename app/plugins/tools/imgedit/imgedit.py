from PySide6.QtWidgets import QWidget, QHBoxLayout
from qasync import asyncSlot

from app.spi.tool import BaseTool
from app.ui.base_widget import BaseTaskWidget
from app.ui.media_selector.media_selector import MediaSelector
from utils.i18n_utils import tr


class ImageEdit(BaseTool, BaseTaskWidget):

    def __init__(self, workspace, editor=None):
        super(ImageEdit, self).__init__(workspace)
        self.setObjectName("tool_image_edit")
        self.workspace = workspace
        self.workspace.connect_task_execute(self.execute)
        self.editor = editor
        self.input_image_path = None
        self.media_selector = None

    def init_ui(self, main_editor):
        """Initialize the UI for the image edit tool"""
        # Create widget for tool configuration
        widget = QWidget()
        layout = QHBoxLayout(widget)  # Changed to QHBoxLayout for left-right layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Create media selector for input image with 9:16 aspect ratio
        self.media_selector = MediaSelector()
        # Set size with 9:16 aspect ratio (portrait) - height 54px, width 30px
        # This fits within the 60px max height constraint of prompt input config panel
        self.media_selector.preview_widget.setFixedSize(30, 54)
        self.media_selector.placeholder_widget.setFixedSize(30, 54)
        
        # Set supported types to image formats only
        self.media_selector.set_supported_types(['png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'])
        
        # Set initial value if exists
        timeline_index = self.workspace.get_project().get_timeline_index()
        timeline_item = self.workspace.get_project().get_timeline().get_item(timeline_index)
        current_image_path = timeline_item.get_image_path()
        if current_image_path:
            self.media_selector.set_value(current_image_path)
            self.input_image_path = current_image_path
            
        # Connect signal
        self.media_selector.file_selected.connect(self._on_image_selected)
        self.media_selector.file_cleared.connect(self._on_image_cleared)
        
        # Add to layout without label
        layout.addWidget(self.media_selector)
        layout.addStretch()
        
        # Set the widget in the prompt input's config panel
        main_editor.prompt_input.set_config_panel_widget(widget)

    def _on_image_selected(self, file_path):
        """Handle image selection"""
        self.input_image_path = file_path

    def _on_image_cleared(self):
        """Handle image clearing"""
        self.input_image_path = None

    def edit_image(self):
        self.workspace.submit_task(self.params())

    def params(self):
        timeline_index = self.workspace.get_project().get_timeline_index()
        timeline_item = self.workspace.get_project().get_timeline().get_item(timeline_index)
        input_image_path = self.input_image_path or timeline_item.get_image_path()

        # Get width and height from layer manager (validates against actual images)
        layer_manager = timeline_item.get_layer_manager()
        width, height = layer_manager.get_valid_dimensions()

        # Don't set server_name or model here - let ability selection handle it
        return {
            "tool": "imgedit",
            "input_image_path": input_image_path,
            "prompt": self.editor.get_prompt(),
            "width": width,
            "height": height
        }

    @classmethod
    def get_tool_name(cls):
        return "imgedit"
    
    @classmethod
    def get_tool_icon(cls):
        return "\ue710"  # Image edit icon from iconfont.json
    
    @classmethod
    def get_tool_display_name(cls):
        return tr("Image Edit")
    
    @classmethod
    def uses_prompt_config_panel(cls):
        """This tool uses the prompt input config panel"""
        return True
    
    def get_media_path(self, timeline_item):
        """Get media path for image edit tool"""
        return timeline_item.get_image_path()

    @asyncSlot()
    async def execute(self, task):
        # Only process imgedit tasks
        if task.tool != "imgedit":
            return  # Exit early if this is not an imgedit task
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Processing imgedit task with FilmetoApi: {task.options}")
            from server.api import FilmetoApi, FilmetoTask, Ability, ResourceInput, ResourceType
            from server.api.types import SelectionConfig
            from app.data.task import TaskResult as AppTaskResult, TaskProgress as AppTaskProgress
            from server.api.types import TaskProgress as FilmetoTaskProgress, TaskResult as FilmetoTaskResult

            api = FilmetoApi()

            # Get parameters from task options
            prompt = task.options.get('prompt', '')
            input_image_path = task.options.get('input_image_path', '')
            width = task.options.get('width', 1024)
            height = task.options.get('height', 1024)

            logger.info(f"ImageEdit: width={width}, height={height}, prompt={prompt[:50]}...")

            # Create input resources (input image)
            resources = []
            if input_image_path:
                resources.append(ResourceInput(
                    type=ResourceType.LOCAL_PATH,
                    data=input_image_path,
                    mime_type="image/png"
                ))

            # Let ability selection choose the best server and model
            # Use auto mode to select based on priority from ability_models config
            selection_config = SelectionConfig.auto()

            filmeto_task = FilmetoTask(
                ability=Ability.IMAGE2IMAGE,
                selection=selection_config,
                parameters={
                    "prompt": prompt,
                    "input_image_path": input_image_path,
                    "width": width,
                    "height": height,
                    "n": 1,
                    "save_dir": task.path
                },
                resources=resources
            )

            logger.info(f"ImageEdit: using ability selection (auto mode)")

            app_progress = AppTaskProgress(task)

            async for update in api.execute_task_stream(filmeto_task):
                if isinstance(update, FilmetoTaskProgress):
                    app_progress.on_progress(int(update.percent), update.message)
                elif isinstance(update, FilmetoTaskResult):
                    logger.info(f"ImageEdit completed: status={update.status}, server={filmeto_task.server_name}, model={filmeto_task.model_name}")

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
                    self.workspace.on_task_finished(task_result)
        except Exception as e:
            logger.error(f"Error in ImageEdit.execute: {e}", exc_info=True)