"""
Abstract base class for structured content widgets with state management.

This module defines an abstract base class that all structured content widgets
should inherit from to provide consistent state management and lifecycle methods.
"""
from abc import ABC, ABCMeta, abstractmethod
from typing import Any, Dict, Optional

from PySide6.QtWidgets import QWidget
from agent.chat.agent_chat_message import StructureContent


class BaseStructuredContentWidgetMeta(ABCMeta, type(QWidget)):
    """Metaclass combining ABCMeta and QWidget's metaclass to resolve conflicts."""
    pass


class BaseStructuredContentWidget(ABC, QWidget, metaclass=BaseStructuredContentWidgetMeta):
    """
    Abstract base class for structured content widgets with state management.
    
    All structured content widgets should inherit from this class to provide
    consistent state management and lifecycle methods.
    """
    
    def __init__(self, structure_content: StructureContent, parent=None):
        """
        Initialize the structured content widget.
        
        Args:
            structure_content: The structure content to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.structure_content = structure_content
        self._setup_ui()
        self._connect_signals()
        self._apply_initial_state()
    
    def _setup_ui(self):
        """Set up the UI components. Override in subclasses."""
        pass
    
    def _connect_signals(self):
        """Connect signals. Override in subclasses."""
        pass
    
    def _apply_initial_state(self):
        """Apply the initial state based on structure content. Override in subclasses."""
        pass
    
    @abstractmethod
    def update_content(self, structure_content: StructureContent):
        """
        Update the widget with new structure content.
        
        Args:
            structure_content: The new structure content to display
        """
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.
        
        Returns:
            Dictionary representing the current state
        """
        pass
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        pass

    def cleanup(self):
        """Clean up resources when widget is being destroyed. Override in subclasses if needed."""
        pass