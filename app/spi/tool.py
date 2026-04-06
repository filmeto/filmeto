from typing import Any

from qasync import asyncSlot

from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from utils.progress_utils import Progress


class BaseTool(BaseWidget,Progress):

    def __init__(self,workspace:Workspace):
        # Only initialize QWidget if workspace is not None
        if workspace is not None:
            super(BaseTool,self).__init__(workspace)
        return

    def submit_task(self,task:Any):
        self.workspace.submit_task(task)

    @asyncSlot()
    async def execute(self, task):
        return

    def init_ui(self, main_editor):
        """Initialize UI in MainEditor left panel or prompt input config panel. 
        Subclasses may override.
        If a QWidget is returned or set, use either:
        1. main_editor.set_tool_panel(widget) for persistent tool panels, or 
        2. main_editor.prompt_input.set_config_panel_widget(widget) for the prompt bottom toolbar (e.g. reference image)."""
        try:
            from PySide6.QtWidgets import QLabel
            # By default, set an empty panel to the tool panel
            main_editor.set_tool_panel(QLabel("No Tool Config"))
        except Exception:
            pass

    @classmethod
    def get_tool_name(cls):
        """Get the tool name for tool-specific prompt storage.
        Should be overridden by subclasses."""
        # Default implementation - return the class name in lowercase with 'tool' removed
        class_name = cls.__name__.lower()
        if class_name.endswith('tool'):
            class_name = class_name[:-4]  # Remove 'tool' suffix
        return class_name
    
    @classmethod
    def get_tool_icon(cls):
        """Get the tool icon for UI display.
        Should be overridden by subclasses."""
        # Default implementation - return a generic icon
        return "\ue600"  # Barrage as generic tool icon
    
    @classmethod
    def get_tool_display_name(cls):
        """Get the tool display name for UI.
        Should be overridden by subclasses."""
        # Default implementation - return the tool name
        return cls.get_tool_name().title()
    
    @classmethod
    def uses_prompt_config_panel(cls):
        """Determine if this tool uses the prompt input config panel instead of the tool panel.
        Should be overridden by subclasses that want to use the prompt config panel.
        Returns False by default, meaning use the tool panel."""
        return False
    
    def get_media_path(self, timeline_item):
        """Get the appropriate media path for this tool.
        Should be overridden by subclasses to customize behavior.
        Returns the path to the media file that should be displayed.
        """
        # Default implementation - return None
        return None