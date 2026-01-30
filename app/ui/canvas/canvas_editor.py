"""
Canvas Editor Component
This module implements a canvas widget for displaying and editing images/videos.
"""
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QSizePolicy, QLabel)

from app.ui.base_widget import BaseWidget
from app.ui.canvas.canvas import CanvasWidget
from app.data.workspace import Workspace
from app.data.timeline import TimelineItem
from app.data.task import TaskResult

logger = logging.getLogger(__name__)


class CanvasEditor(BaseWidget):
    """
    Canvas editor component - displays the canvas widget.
    The tool panel has been migrated to MainEditorWidget.
    """
    
    def __init__(self, workspace: Workspace):
        super().__init__(workspace)
        try:
            self.setWindowTitle("Canvas Editor")
            self.timeline_item = workspace.get_current_timeline_item()
            
            # Initialize canvas widget - will be sized based on parent when added to layout
            # 使用默认尺寸，让CanvasWidget自适应父容器
            self.canvas_widget = CanvasWidget(workspace)

            # Make the canvas widget expand to fill available space in the layout
            self.canvas_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Create layout - only canvas, no left panel
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            main_layout.addWidget(self.canvas_widget)

            # Make CanvasEditor expand to fill available space
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            #self.canvas_widget.set_timeline_item(self.timeline_item)
        except Exception as e:
            logger.error(f"Error initializing CanvasEditor: {e}", exc_info=True)
            raise
    

    
    def on_task_finished(self, result: TaskResult):
        """Handle task finished event - add generated image as a new layer"""
        logger.info(f"Task finished: {result.get_task_id()}")
        # Get the image path from the task result
        image_path = result.get_image_path()
        if image_path and self.canvas_widget:
            self.canvas_widget.reload()