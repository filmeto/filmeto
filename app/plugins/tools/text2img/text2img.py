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
        """Initialize the UI for the text2img tool"""
        # Create widget for tool configuration
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Create media selector for reference image with 9:16 aspect ratio
        self.media_selector = MediaSelector()
        # Set size with 9:16 aspect ratio (portrait) - height 54px, width 30px
        # This fits within the 60px max height constraint of prompt input config panel
        self.media_selector.preview_widget.setFixedSize(30, 54)
        self.media_selector.placeholder_widget.setFixedSize(30, 54)
        
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
        return "text2img"
    
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
        """Get media path for text2img tool"""
        return timeline_item.get_image_path()

    def params(self):
        timeline_index = self.workspace.get_project().get_timeline_index()
        timeline_item = self.workspace.get_project().get_timeline().get_item(timeline_index)
        prompt = self.editor.get_prompt() if self.editor else ""
        return {
            "tool": "text2img",
            "model": "comfy_ui",
            "prompt": prompt,
            "reference_image_path": self.reference_image_path
        }

    @asyncSlot()
    async def execute(self, task):
        # Only process text2img tasks to avoid conflicts with other tools
        if task.tool != "text2img" and task.tool != "text2image":
            return  # Exit early if this is not a text2img task
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Processing text2img task with FilmetoApi: {task.options}")
            from server.api import FilmetoApi, FilmetoTask, ToolType, ResourceInput, ResourceType
            from app.data.task import TaskResult as AppTaskResult, TaskProgress as AppTaskProgress
            from server.api.types import TaskProgress as FilmetoTaskProgress, TaskResult as FilmetoTaskResult

            api = FilmetoApi()
            
            # Find a plugin that supports text2image
            plugins = api.get_plugins_by_tool(ToolType.TEXT2IMAGE)
            if not plugins:
                logger.warning("No plugins found for text2image")
                return
            
            # Prefer ComfyUI if available, otherwise use the first one
            plugin_name = "ComfyUI"
            if not any(p['name'] == plugin_name for p in plugins):
                plugin_name = plugins[0]['name']

            # Create input resources if any (e.g., reference image)
            resources = []
            if self.reference_image_path:
                resources.append(ResourceInput(
                    type=ResourceType.LOCAL_PATH,
                    data=self.reference_image_path,
                    mime_type="image/png"
                ))

            filmeto_task = FilmetoTask(
                tool_name=ToolType.TEXT2IMAGE,
                plugin_name=plugin_name,
                parameters={
                    "prompt": task.options['prompt'],
                    "save_dir": task.path
                },
                resources=resources
            )
            
            app_progress = AppTaskProgress(task)
            
            async for update in api.execute_task_stream(filmeto_task):
                if isinstance(update, FilmetoTaskProgress):
                    app_progress.on_progress(int(update.percent), update.message)
                elif isinstance(update, FilmetoTaskResult):
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
            logger.error(f"Error in Text2Image.execute: {e}", exc_info=True)