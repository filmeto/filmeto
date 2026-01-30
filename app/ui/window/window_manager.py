# -*- coding: utf-8 -*-
"""
Window Manager

Manages the startup and edit windows, handling transitions between them.
"""
import logging
from PySide6.QtCore import QObject

from app.data.workspace import Workspace
from app.ui.window.startup.startup_window import StartupWindow
from app.ui.window.edit.edit_window import EditWindow

logger = logging.getLogger(__name__)


class WindowManager(QObject):
    """
    Manages startup and edit windows.
    
    Handles creation, destruction, and transitions between windows.
    """
    
    def __init__(self, workspace: Workspace):
        super().__init__()
        self.workspace = workspace
        
        # Window instances
        self.startup_window = None
        self.edit_window = None
    
    def show_startup_window(self):
        """Show the startup window and hide the edit window."""
        # Create startup window if it doesn't exist
        if self.startup_window is None:
            self.startup_window = StartupWindow(self.workspace)
            self.startup_window.enter_edit_mode.connect(self._on_enter_edit_mode)
            self.startup_window.destroyed.connect(self._on_startup_window_destroyed)
        
        # Ensure window is in normal state (not maximized)
        from PySide6.QtCore import Qt
        self.startup_window.setWindowState(Qt.WindowNoState)
        
        # Show startup window
        self.startup_window.show()
        
        # Hide edit window if it exists
        if self.edit_window:
            self.edit_window.hide()
    
    def show_edit_window(self, project_name: str = None):
        """Show the edit window and hide the startup window."""
        # Switch project if specified
        if project_name:
            self.workspace.switch_project(project_name)
        
        # Create edit window if it doesn't exist
        if self.edit_window is None:
            self.edit_window = EditWindow(self.workspace)
            self.edit_window.go_home.connect(self._on_go_home)
            self.edit_window.destroyed.connect(self._on_edit_window_destroyed)
            # Override closeEvent to show startup window instead of closing
            def close_with_fallback(event):
                # Save window size before hiding
                self.edit_window._save_window_sizes()
                # Hide edit window and show startup window instead of closing
                self.edit_window.hide()
                if self.startup_window:
                    self.startup_window.show()
                # Don't call original_close to prevent actual window destruction
                event.ignore()
            self.edit_window.closeEvent = close_with_fallback
        
        # Update project reference
        self.edit_window.project = self.workspace.get_project()
        
        # Show edit window
        self.edit_window.show()
        
        # Hide startup window if it exists
        if self.startup_window:
            self.startup_window.hide()
    
    def _on_enter_edit_mode(self, project_name: str):
        """Handle entering edit mode from startup window."""
        # Get pending prompt from startup window if available
        pending_prompt = None
        if self.startup_window and hasattr(self.startup_window, '_pending_prompt'):
            pending_prompt = self.startup_window._pending_prompt
            self.startup_window._pending_prompt = None  # Clear after reading
        
        # Show edit window
        self.show_edit_window(project_name)
        
        # Set prompt in agent panel if there's a pending prompt
        if pending_prompt and self.edit_window:
            self._set_prompt_in_agent_panel(pending_prompt)
    
    def _set_prompt_in_agent_panel(self, prompt: str):
        """Set the prompt in the agent panel."""
        try:
            # Access the edit widget
            edit_widget = self.edit_window.edit_widget
            if not edit_widget:
                return
            
            # Access the h_layout
            h_layout = edit_widget.get_h_layout()
            if not h_layout:
                return
            
            # Access the workspace top right bar via workspace.workspace_top.right
            if not hasattr(h_layout, 'workspace') or not h_layout.workspace:
                return
            
            if not hasattr(h_layout.workspace, 'workspace_top') or not h_layout.workspace.workspace_top:
                return
            
            workspace_top_right_bar = h_layout.workspace.workspace_top.right
            if not workspace_top_right_bar:
                return
            
            # Switch to agent panel (this will create it if needed)
            workspace_top_right_bar.switch_to_panel('agent')
            
            # Get the panel after switching (may need delay for lazy loading)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self._set_prompt_in_agent_panel_delayed(prompt))
        except Exception as e:
            logger.error(f"Error setting prompt in agent panel: {e}", exc_info=True)
    
    def _set_prompt_in_agent_panel_delayed(self, prompt: str):
        """Set prompt in agent panel after a short delay (for lazy loading)."""
        try:
            edit_widget = self.edit_window.edit_widget
            if not edit_widget:
                return
            
            h_layout = edit_widget.get_h_layout()
            if not h_layout or not hasattr(h_layout, 'workspace') or not h_layout.workspace:
                return
            
            if not hasattr(h_layout.workspace, 'workspace_top') or not h_layout.workspace.workspace_top:
                return
            
            workspace_top_right_bar = h_layout.workspace.workspace_top.right
            if not workspace_top_right_bar:
                return
            
            agent_panel = workspace_top_right_bar.get_panel('agent')
            if agent_panel and hasattr(agent_panel, 'prompt_input_widget'):
                agent_panel.prompt_input_widget.set_text(prompt)
                # Focus the input widget
                if hasattr(agent_panel.prompt_input_widget, 'input_text'):
                    agent_panel.prompt_input_widget.input_text.setFocus()
        except Exception as e:
            logger.error(f"Error setting prompt in agent panel (delayed): {e}", exc_info=True)
    
    def _on_go_home(self):
        """Handle returning to home/startup mode."""
        self.show_startup_window()
    
    def _on_startup_window_destroyed(self):
        """Handle startup window destruction."""
        self.startup_window = None
    
    def _on_edit_window_destroyed(self):
        """Handle edit window destruction."""
        self.edit_window = None
    
    def get_startup_window(self):
        """Get the startup window instance."""
        return self.startup_window
    
    def get_edit_window(self):
        """Get the edit window instance."""
        return self.edit_window
    
    def refresh_projects(self):
        """Refresh the project list in startup window."""
        if self.startup_window:
            self.startup_window.refresh_projects()

