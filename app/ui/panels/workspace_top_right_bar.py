"""Main switcher component for workspace top right bar panels."""

import logging
from typing import Dict, Optional, Tuple
from PySide6.QtWidgets import QStackedWidget, QWidget
from PySide6.QtCore import Signal, Slot

from app.ui.base_widget import BaseWidget
from app.data.workspace import Workspace
from .base_panel import BasePanel

logger = logging.getLogger(__name__)


class MainWindowWorkspaceTopRightBar(BaseWidget):
    """
    Orchestrates panel switching and lifecycle management for the workspace right sidebar.
    
    Manages multiple tool panels and switches between them
    based on button clicks from MainWindowRightBar. Uses lazy loading to instantiate
    panels only when first accessed.
    """
    
    # Signal emitted when panel switches (panel_name)
    panel_switched = Signal(str)
    
    def __init__(self, workspace: Workspace, parent=None):
        """
        Initialize the panel switcher.
        
        Args:
            workspace: Workspace instance for data access
            parent: Optional parent widget
        """
        super().__init__(workspace)
        if parent:
            self.setParent(parent)
        
        # State management
        self.current_panel: Optional[BasePanel] = None
        self.panel_instances: Dict[str, BasePanel] = {}
        # Panel registry stores (module_path, class_name) tuples for lazy import
        self.panel_registry: Dict[str, Tuple[str, str]] = {}
        
        # Setup UI
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.setObjectName("workspace_panels_stack_right")
        
        # Register panels (lazy loading - classes only)
        self._register_panels()
        
        # Set up layout
        from PySide6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stacked_widget)
    
    def _register_panels(self):
        """
        Register panel classes in the registry.

        Panel instances are created lazily when first accessed.
        Panel classes are imported lazily to avoid blocking startup.
        """
        # Map button names to panel module paths (lazy import)
        # Format: 'module_path.ClassName'
        self.panel_registry = {
            'agent': ('app.ui.panels.agent.agent_panel', 'AgentPanel'),
            'chat_history': ('app.ui.panels.chat_history.chat_history_panel', 'ChatHistoryPanel'),
            'skills': ('app.ui.panels.skills.skills_panel', 'SkillsPanel'),
            'souls': ('app.ui.panels.souls.souls_panel', 'SoulsPanel'),
            'members': ('app.ui.panels.members.members_panel', 'MembersPanel'),
            'screenplay': ('app.ui.panels.screen_play.screen_play_panel', 'ScreenPlayPanel'),
            'plan': ('app.ui.panels.plan.plan_panel', 'PlanPanel'),
        }
    
    @Slot(str)
    def switch_to_panel(self, panel_name: str):
        """
        Switch to the specified panel asynchronously to avoid blocking UI.

        Handles lazy instantiation, panel lifecycle, and visibility management.

        Args:
            panel_name: Name of the panel to switch to (e.g., 'agent', 'chat_history')
        """
        if panel_name not in self.panel_registry:
            logger.warning(f"⚠️ Unknown right panel: {panel_name}")
            return

        # Safety check to prevent accessing destroyed objects
        from shiboken6 import isValid
        if not self.stacked_widget or not isValid(self.stacked_widget):
            logger.warning(f"⚠️ Stacked widget is destroyed, skipping panel switch: {panel_name}")
            return

        # Deactivate current panel if exists
        if self.current_panel and isValid(self.current_panel):
            self.current_panel.on_deactivated()

        # Check if panel instance exists in cache
        if panel_name not in self.panel_instances:
            # Defer creation to avoid blocking
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._deferred_create_panel(panel_name))
            return

        self._finalize_panel_switch(panel_name)

    def _deferred_create_panel(self, panel_name: str):
        """Internal helper to create panel instance without blocking the immediate event loop"""
        from shiboken6 import isValid
        # Safety check to prevent accessing destroyed objects
        if not self.stacked_widget or not isValid(self.stacked_widget):
            logger.warning(f"⚠️ Stacked widget is destroyed, skipping panel creation: {panel_name}")
            return

        panel_info = self.panel_registry[panel_name]
        try:
            import time
            create_start = time.time()
            # Import panel class dynamically
            import importlib
            module_path, class_name = panel_info

            import_start = time.time()
            module = importlib.import_module(module_path)
            panel_class = getattr(module, class_name)
            import_time = (time.time() - import_start) * 1000

            # Create panel instance
            init_start = time.time()
            panel_instance = panel_class(self.workspace, self)
            self.panel_instances[panel_name] = panel_instance
            init_time = (time.time() - init_start) * 1000

            # Double-check that stacked widget still exists before adding widget
            if not self.stacked_widget or not isValid(self.stacked_widget):
                logger.warning(f"⚠️ Stacked widget destroyed after panel creation, removing panel: {panel_name}")
                # Clean up the panel instance since we can't add it to the stacked widget
                panel_instance.setParent(None)
                if panel_name in self.panel_instances:
                    del self.panel_instances[panel_name]
                return

            self.stacked_widget.addWidget(panel_instance)
            create_time = (time.time() - create_start) * 1000
            logger.info(f"✅ Created right panel: {panel_name} (Total: {create_time:.2f}ms, Import: {import_time:.2f}ms, Init: {init_time:.2f}ms)")

            # Defer panel activation
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._finalize_panel_switch(panel_name))

        except Exception as e:
            logger.error(f"❌ Error creating right panel {panel_name}: {e}", exc_info=True)

    def _finalize_panel_switch(self, panel_name: str):
        """Complete the panel switch after instance is ready"""
        # Safety check to prevent accessing destroyed objects
        from shiboken6 import isValid
        if not self.stacked_widget or not isValid(self.stacked_widget):
            logger.warning(f"⚠️ Stacked widget is destroyed, skipping panel switch: {panel_name}")
            return

        if panel_name not in self.panel_instances:
            logger.warning(f"⚠️ Panel {panel_name} not found in instances, skipping switch")
            return

        panel = self.panel_instances[panel_name]

        # Double-check that panel hasn't been destroyed
        if not panel or not isValid(panel):
            logger.warning(f"⚠️ Panel {panel_name} is destroyed, skipping switch")
            return

        self.stacked_widget.setCurrentWidget(panel)
        panel.on_activated()
        self.current_panel = panel

        # Emit signal
        self.panel_switched.emit(panel_name)
        logger.info(f"🔄 Switched to right panel: {panel_name}")
    
    def get_current_panel(self) -> Optional[BasePanel]:
        """
        Get the currently active panel.
        
        Returns:
            Current panel instance or None
        """
        return self.current_panel
    
    def get_panel(self, panel_name: str) -> Optional[BasePanel]:
        """
        Get a panel instance by name.
        
        Args:
            panel_name: Name of the panel
            
        Returns:
            Panel instance if it has been instantiated, None otherwise
        """
        return self.panel_instances.get(panel_name)
