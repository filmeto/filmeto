"""Base panel class for workspace tool panels."""

from pathlib import Path

from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QLabel, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtQuickWidgets import QQuickWidget
from app.ui.base_widget import BaseWidget
from app.data.workspace import Workspace
from app.ui.panels.panel_toolbar_bridge import PanelToolbarViewModel


class BasePanel(BaseWidget):
    """
    Abstract base class for workspace tool panels.
    
    All panels must inherit from this class and implement the required lifecycle methods.
    Provides consistent interface for panel switching and state management.
    Includes built-in support for asynchronous data loading.
    """
    
    def __init__(self, workspace: Workspace, parent=None):
        """
        Initialize the panel with workspace context.
        
        Args:
            workspace: Workspace instance providing access to project and services
            parent: Optional parent widget
        """
        super().__init__(workspace)
        if parent:
            self.setParent(parent)
            
        self._is_active = False
        self._data_loaded = False
        self._is_loading = False
        
        # Initialize UI structure
        self._init_base_ui()
        
        # Only setup UI framework, not data loading
        self.setup_ui()
        
    def _init_base_ui(self):
        """Initialize the base layout with toolbar and content area."""
        # Main vertical layout for the whole panel
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # Top toolbar (QML)
        self._toolbar_view_model = PanelToolbarViewModel(self)
        self._toolbar_callbacks = {}
        self.toolbar = QQuickWidget(self)
        self.toolbar.setObjectName("panelToolbar")
        self.toolbar.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.toolbar.setFixedHeight(40)
        self.toolbar.setStyleSheet("background: transparent; border: none;")
        self.toolbar.rootContext().setContextProperty("panelToolbarViewModel", self._toolbar_view_model)
        qml_path = Path(__file__).resolve().parent.parent / "qml" / "panels" / "PanelToolbar.qml"
        self.toolbar.setSource(QUrl.fromLocalFile(str(qml_path)))
        self._toolbar_view_model.actionInvoked.connect(self._on_toolbar_action_invoked)
        self._main_layout.addWidget(self.toolbar)
        
        # Stacked widget for content and loading state
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("panelContentStack")
        
        # Content area (Index 0)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("panelContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_stack.addWidget(self.content_widget)
        
        # Loading area (Index 1)
        self.loading_widget = QWidget()
        self.loading_widget.setObjectName("panelLoading")
        self.loading_widget.setStyleSheet("background-color: #1E1E1E;")
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        from utils.i18n_utils import tr
        self.loading_label = QLabel(tr("正在加载..."))
        self.loading_label.setStyleSheet("color: #888888; font-size: 12px;")
        loading_layout.addWidget(self.loading_label)
        
        self.content_stack.addWidget(self.loading_widget)
        
        self._main_layout.addWidget(self.content_stack, 1)

    def show_loading(self, message: str = None):
        """Show the loading state."""
        if message:
            self.loading_label.setText(message)
        self.content_stack.setCurrentIndex(1)
        self._is_loading = True

    def hide_loading(self):
        """Hide the loading state and show content."""
        self.content_stack.setCurrentIndex(0)
        self._is_loading = False

    def set_panel_title(self, title: str):
        """Set the panel title in the toolbar."""
        self._toolbar_view_model.set_title(title)
        
    def add_toolbar_button(self, icon_text: str, callback=None, tooltip: str = ""):
        """Add an icon button to the toolbar's right side."""
        handle = self._toolbar_view_model.add_action(icon_text, tooltip)
        if callback:
            self._toolbar_callbacks[handle.action_id] = callback
        return handle

    def _on_toolbar_action_invoked(self, action_id: str):
        callback = self._toolbar_callbacks.get(action_id)
        if callback:
            callback()

    def setup_ui(self):
        """
        Set up the panel UI framework (widgets, layouts, etc.).
        
        This method should create and configure UI widgets and layouts.
        Should NOT load business data - that should be done in load_data().
        Called during initialization.
        Subclasses must override this method.
        """
        raise NotImplementedError("Subclasses must implement setup_ui()")
    
    def load_data(self):
        """
        Load business data for the panel.
        
        This method should load data from managers, databases, etc.
        Called when panel is first activated or when data needs refresh.
        Override this method to load panel-specific data.
        """
        # Default implementation does nothing
        pass
    
    def on_activated(self):
        """
        Called when the panel becomes visible/active.
        
        Override this method to refresh data, reconnect signals,
        or perform any necessary updates when panel is shown.
        """
        self._is_active = True
        
        # Load data on first activation if not already loaded
        if not self._data_loaded:
            # Defer load_data to next event loop iteration to avoid blocking startup
            QTimer.singleShot(0, self._perform_initial_load)
    
    def _perform_initial_load(self):
        """Internal helper to call load_data safely."""
        if not self._data_loaded:
            self.load_data()
            self._data_loaded = True
    
    def on_deactivated(self):
        """
        Called when the panel is hidden/deactivated.
        
        Override this method to disconnect signals, pause operations,
        or clean up resources when panel is hidden.
        """
        self._is_active = False
    
    def on_project_switched(self, project_name: str):
        """
        Called when the project is switched.
        
        Panels should reload their data for the new project.
        """
        self._data_loaded = False
        if self._is_active:
            QTimer.singleShot(0, self._perform_initial_load)
    
    def is_active(self) -> bool:
        """
        Check if panel is currently active.
        
        Returns:
            True if panel is active, False otherwise
        """
        return self._is_active
