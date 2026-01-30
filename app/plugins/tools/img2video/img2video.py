import os

from qasync import asyncSlot

from app.spi.tool import BaseTool
from app.ui.base_widget import BaseTaskWidget
from utils.i18n_utils import tr
from utils.opencv_utils import extract_last_frame_opencv


class Image2Video(BaseTool,BaseTaskWidget):

    def __init__(self, workspace, editor=None):
        super(Image2Video,self).__init__(workspace)
        self.setObjectName("tool_text_to_image")
        self.workspace = workspace
        self.workspace.connect_task_execute(self.execute)
        self.editor = editor
        self.start_frame_path = None
        self.end_frame_path = None

    def generate_image(self):
        self.workspace.submit_task(self.params())

    def params(self):
        timeline_index = self.workspace.get_project().get_timeline_index()
        timeline_item = self.workspace.get_project().get_timeline().get_item(timeline_index)
        input_image_path = timeline_item.get_image_path()
        return {
            "tool":"img2video",
            "model":"comfy_ui",
            "input_image_path":input_image_path,
            "prompt":self.editor.get_prompt(),
            "start_frame_path": self.start_frame_path,
            "end_frame_path": self.end_frame_path
        }

    def init_ui(self, main_editor):
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QSpacerItem, QSizePolicy
        from app.ui.media_selector.media_selector import MediaSelector
        
        panel = QWidget()
        layout = QHBoxLayout(panel)  # Changed to QHBoxLayout for left-right layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Start frame selector with 9:16 aspect ratio
        self.start_frame_selector = MediaSelector()
        # Set supported types to image formats only
        self.start_frame_selector.set_supported_types(['png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'])
        # Set size with 9:16 aspect ratio (portrait) - height 54px, width 30px
        # This fits within the 60px max height constraint of prompt input config panel
        self.start_frame_selector.preview_widget.setFixedSize(30, 54)
        self.start_frame_selector.placeholder_widget.setFixedSize(30, 54)
        
        # Connect signal for start frame
        self.start_frame_selector.file_selected.connect(self._on_start_frame_selected)
        self.start_frame_selector.file_cleared.connect(self._on_start_frame_cleared)
        
        # End frame selector with 9:16 aspect ratio
        self.end_frame_selector = MediaSelector()
        # Set supported types to image formats only
        self.end_frame_selector.set_supported_types(['png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'])
        # Set size with 9:16 aspect ratio (portrait) - height 54px, width 30px
        # This fits within the 60px max height constraint of prompt input config panel
        self.end_frame_selector.preview_widget.setFixedSize(30, 54)
        self.end_frame_selector.placeholder_widget.setFixedSize(30, 54)
        
        # Connect signal for end frame
        self.end_frame_selector.file_selected.connect(self._on_end_frame_selected)
        self.end_frame_selector.file_cleared.connect(self._on_end_frame_cleared)
        
        # Add widgets to layout without labels
        layout.addWidget(self.start_frame_selector)
        layout.addWidget(self.end_frame_selector)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Set the widget in the prompt input's config panel
        main_editor.prompt_input.set_config_panel_widget(panel)

    # def on_timeline_switch(self,item:TimelineItem):
    #     # For img2video, show the video if exists, otherwise show image
    #     current_tool = item.get_config_value("current_tool")
    #     if current_tool != self.get_tool_name():
    #         return
    #     if not self.editor:
    #         return
    #
    #     video_path = item.get_video_path()
    #     if os.path.exists(video_path):
    #         self.editor.get_canvas_widget().switch_file(video_path)
    #     else:
    #         image_path = item.get_image_path()
    #         if os.path.exists(image_path):
    #         self.editor.get_canvas_widget().switch_file(image_path)
    #     return
    
    @classmethod
    def get_tool_name(cls):
        return "img2video"
    
    @classmethod
    def get_tool_icon(cls):
        return "\ue712"  # Image to video icon from iconfont.json
    
    @classmethod
    def get_tool_display_name(cls):
        return tr("Image to Video")
    
    @classmethod
    def uses_prompt_config_panel(cls):
        """This tool uses the prompt input config panel"""
        return True
    
    def get_media_path(self, timeline_item):
        """Get media path for img2video tool"""
        # Check for video first, then image
        video_path = timeline_item.get_video_path()
        if os.path.exists(video_path):
            return video_path
        else:
            return timeline_item.get_image_path()
    
    @asyncSlot()
    async def execute(self, task):
        # Only process img2video tasks to avoid conflicts with other tools
        if task.tool != "img2video" and task.tool != "image2video":
            return  # Exit early if this is not an img2video task
            
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Processing img2video task with FilmetoApi: {task.options}")
            from server.api import FilmetoApi, FilmetoTask, ToolType, ResourceInput, ResourceType
            from app.data.task import TaskResult as AppTaskResult, TaskProgress as AppTaskProgress
            from server.api.types import TaskProgress as FilmetoTaskProgress, TaskResult as FilmetoTaskResult

            api = FilmetoApi()
            
            # Find a plugin that supports image2video
            plugins = api.get_plugins_by_tool(ToolType.IMAGE2VIDEO)
            if not plugins:
                logger.warning("No plugins found for image2video")
                return
            
            # Prefer ComfyUI if available, otherwise use the first one
            plugin_name = "ComfyUI"
            if not any(p['name'] == plugin_name for p in plugins):
                plugin_name = plugins[0]['name']

            # Get the timeline
            timeline = self.workspace.get_project().get_timeline()

            # If we can't extract from path, try getting from options or workspace
            current_index = task.options.get('timeline_index', self.workspace.get_project().get_timeline_index())

            # Get the appropriate input image
            input_image_path = await self._get_image(task, timeline, current_index)
            
            # Create input resources (input image)
            resources = []
            if input_image_path:
                resources.append(ResourceInput(
                    type=ResourceType.LOCAL_PATH,
                    data=input_image_path,
                    mime_type="image/png"
                ))

            filmeto_task = FilmetoTask(
                tool_name=ToolType.IMAGE2VIDEO,
                plugin_name=plugin_name,
                parameters={
                    "prompt": task.options['prompt'],
                    "input_image_path": input_image_path,
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
            logger.error(f"Error in Image2Video.execute: {e}", exc_info=True)

    async def _get_image(self, task, timeline, current_index):
        # Check if input image exists
        timeline_item = timeline.get_item(current_index)
        if timeline_item.get_config() is not None and timeline_item.get_config():
            input_image_path = task.options['input_image_path']
            return input_image_path
        # Get the previous timeline item (current_index - 1)
        prev_index = current_index - 1
        if prev_index >= 1:  # Timeline items start from index 1
            prev_item = timeline.get_item(prev_index)
            input_image_path = task.options['input_image_path']
            # Check if the previous item has a video file
            if os.path.exists(prev_item.get_video_path()):
                # Extract the last frame from the video using ffmpeg_utils
                video_path = prev_item.get_video_path()
                logger.info(f"Getting image from video: {video_path}")

                # First, ensure ffmpeg is available
                logger.error("Failed to extract or save the last frame from video using ffmpeg")
                # Try fallback method using OpenCV if available
                current_item_path = os.path.join(os.path.dirname(input_image_path), "image.png")
                opencv_result = extract_last_frame_opencv(video_path, current_item_path)
                if opencv_result and os.path.exists(opencv_result):
                    input_image_path = opencv_result
                    logger.info(f"Saved last frame with OpenCV as: {input_image_path}")
                    # 刷新时间线显示复制过来的图片
                    # 获取当前时间线项并更新其显示
                    current_item = timeline.get_item(current_index)
                    # 发送信号更新UI显示
                    timeline.timeline_switch.send(current_item)
                else:
                    logger.error("OpenCV fallback also failed to extract the frame")
            elif os.path.exists(prev_item.get_image_path()):
                # Copy the image from previous item
                prev_image_path = prev_item.get_image_path()
                logger.info(f"Getting image from previous item: {prev_image_path}")

                # Copy to current item's directory
                current_item_path = os.path.join(os.path.dirname(input_image_path), "image.png")
                import shutil
                shutil.copy2(prev_image_path, current_item_path)
                input_image_path = current_item_path
                logger.info(f"Copied image to: {input_image_path}")
                
                # 刷新时间线显示复制过来的图片
                # 获取当前时间线项并更新其显示
                current_item = timeline.get_item(current_index)
                # 发送信号更新UI显示
                timeline.timeline_switch.send(current_item)
            else:
                logger.warning(f"No image or video found in previous timeline item {prev_index}")
        else:
            logger.warning("No previous timeline item exists (at index 1)")

        # If the input image path is still not valid, raise an error
        if not os.path.exists(input_image_path):
            raise FileNotFoundError(f"Input image not found: {input_image_path}")

        logger.info(f"Using input image: {input_image_path}")
        return input_image_path
    
    def _on_start_frame_selected(self, file_path):
        """Handle start frame selection"""
        self.start_frame_path = file_path

    def _on_start_frame_cleared(self):
        """Handle start frame clearing"""
        self.start_frame_path = None
        
    def _on_end_frame_selected(self, file_path):
        """Handle end frame selection"""
        self.end_frame_path = file_path

    def _on_end_frame_cleared(self):
        """Handle end frame clearing"""
        self.end_frame_path = None
