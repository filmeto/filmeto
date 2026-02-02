"""
Collapsible text content widget for displaying large text content.

This widget provides:
- Expand/collapse functionality
- Scroll area for long content
- Clean visual design
"""

from typing import Any, Dict
from PySide6.QtCore import Qt, QSize, Signal, Property
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy, QPushButton, QScrollArea,
    QApplication
)

from agent.chat.content import TextContent
from app.ui.chat.message.base_structured_content_widget import BaseStructuredContentWidget


class CollapsibleTextContentWidget(BaseStructuredContentWidget):
    """
    Widget for displaying text content with collapsible functionality.

    Features:
    - Expand/collapse button with visual feedback
    - Scrollable content area
    - Auto-collapse based on content length
    - Text selection and link support
    """

    # Signals
    expandStateChanged = Signal(bool)  # Emitted when expand/collapse state changes

    def __init__(self, structure_content: TextContent, parent=None,
                 max_lines_collapsed: int = 3, auto_collapse_threshold: int = 500):
        """
        Initialize the collapsible text content widget.

        Args:
            structure_content: TextContent object with text data
            parent: Parent widget
            max_lines_collapsed: Maximum lines to show when collapsed
            auto_collapse_threshold: Auto-collapse if text exceeds this character count
        """
        # Initialize instance variables BEFORE calling parent init
        # because parent's _setup_ui() will be called which accesses these
        self.max_lines_collapsed = max_lines_collapsed
        self.auto_collapse_threshold = auto_collapse_threshold
        # Default to collapsed state for all content
        self._is_expanded = False
        self._auto_collapsed = True  # Always start collapsed

        # Now call parent init (which will call _setup_ui)
        super().__init__(structure_content, parent)

    def _setup_ui(self):
        """Set up the UI with collapsible functionality."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header with title and expand/collapse button
        header_widget = self._create_header()
        layout.addWidget(header_widget)

        # Collapsible content area
        self.content_container = QWidget()
        self.content_container.setObjectName("collapsible_content_container")
        self.content_container.setStyleSheet("""
            QWidget#collapsible_content_container {
                background-color: transparent;
                border: none;
            }
        """)

        container_layout = QVBoxLayout(self.content_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Create scroll area for content
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("content_scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setMaximumHeight(300)  # Max height when collapsed
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Scroll area styles
        self.scroll_area.setStyleSheet("""
            QScrollArea#content_scroll_area {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        # Content label inside scroll area
        self.content_label = QLabel()
        self.content_label.setObjectName("collapsible_text_content")
        self.content_label.setWordWrap(True)
        content_text = self.structure_content.text or ""
        self.content_label.setText(content_text)
        self.content_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )
        self.content_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.content_label.setStyleSheet("""
            QLabel#collapsible_text_content {
                color: #e1e1e1;
                font-size: 13px;
                padding: 8px;
                background-color: transparent;
            }
        """)

        # Set the content label as the scroll area's widget
        self.scroll_area.setWidget(self.content_label)

        # Add scroll area to container layout (not container to itself)
        container_layout.addWidget(self.scroll_area)
        # Add container to main layout
        layout.addWidget(self.content_container)

        # Apply initial expand/collapse state
        self._update_expand_state()

        # Connect signals
        self.expandStateChanged.connect(self._on_expand_state_changed)

    def _create_header(self) -> QWidget:
        """Create header with title and expand/collapse button."""
        header = QWidget()
        header.setObjectName("collapsible_header")
        header.setStyleSheet("""
            QWidget#collapsible_header {
                background-color: transparent;
                border: none;
            }
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Title label
        title_text = self.structure_content.title or "Content"
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #7c4dff;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        header_layout.addWidget(self.title_label)

        # Add stretch
        header_layout.addStretch()

        # Expand/collapse button
        self.expand_button = QPushButton()
        self.expand_button.setObjectName("expand_collapse_button")
        self.expand_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.expand_button.setFixedSize(24, 24)
        self.expand_button.setText(self._get_expand_icon())
        self.expand_button.clicked.connect(self._toggle_expand)

        # Button styles
        self._update_button_style()

        header_layout.addWidget(self.expand_button)

        # Make header clickable
        header.setCursor(QCursor(Qt.PointingHandCursor))
        header.mousePressEvent = self._on_header_clicked

        return header

    def _get_expand_icon(self) -> str:
        """Get the expand/collapse icon character."""
        if self._is_expanded:
            return "▼"  # Down arrow for collapse
        else:
            return "▶"  # Right arrow for expand

    def _update_button_style(self):
        """Update button style based on state."""
        base_style = """
            QPushButton#expand_collapse_button {
                background-color: transparent;
                border: none;
                color: #7c4dff;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
                line-height: 24px;
            }
            QPushButton#expand_collapse_button:hover {
                color: #9d7fff;
            }
            QPushButton#expand_collapse_button:pressed {
                color: #5a3fd6;
            }
        """
        self.expand_button.setStyleSheet(base_style)

    def _update_expand_state(self):
        """Update the expand/collapse state."""
        # Update button icon
        self.expand_button.setText(self._get_expand_icon())
        self._update_button_style()

        # Update scroll area max height
        if self._is_expanded:
            # When expanded, remove height limit (or set to a larger value)
            content_height = self.content_label.sizeHint().height()
            if content_height > 0:
                self.scroll_area.setMaximumHeight(min(content_height + 20, 800))
            else:
                self.scroll_area.setMaximumHeight(800)
        else:
            # When collapsed, limit height
            self.scroll_area.setMaximumHeight(150)

        # Emit signal
        self.expandStateChanged.emit(self._is_expanded)

    def _on_expand_state_changed(self, is_expanded: bool):
        """Handle expand state change."""
        # Can be overridden by subclasses for custom behavior
        pass

    def _toggle_expand(self):
        """Toggle the expand/collapse state."""
        self._is_expanded = not self._is_expanded
        self._auto_collapsed = False  # User manually changed state
        self._update_expand_state()

    def _on_header_clicked(self, event):
        """Handle header click to toggle expand/collapse."""
        self._toggle_expand()

    def is_expanded(self) -> bool:
        """Check if the content is expanded."""
        return self._is_expanded

    def set_expanded(self, expanded: bool):
        """Set the expand state programmatically."""
        if self._is_expanded != expanded:
            self._is_expanded = expanded
            self._auto_collapsed = False
            self._update_expand_state()

    def update_content(self, structure_content: TextContent):
        """
        Update the widget with new structure content.

        Args:
            structure_content: The new structure content to display
        """
        self.structure_content = structure_content

        # Update content label
        content_text = self.structure_content.text or ""
        self.content_label.setText(content_text)

        # Update title if changed
        if self.structure_content.title:
            self.title_label.setText(self.structure_content.title)

        # Recalculate auto-collapse state based on new content
        if not self._auto_collapsed:
            # Only auto-collapse if content length changes significantly
            if len(content_text) > self.auto_collapse_threshold * 1.5:
                self._auto_collapsed = True
                self._is_expanded = False
                self._update_expand_state()

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the widget.

        Returns:
            Dictionary representing the current state
        """
        return {
            "title": self.structure_content.title,
            "description": self.structure_content.description,
            "text": self.structure_content.text,
            "is_expanded": self._is_expanded,
            "is_auto_collapsed": self._auto_collapsed
        }

    def set_state(self, state: Dict[str, Any]):
        """
        Set the state of the widget.

        Args:
            state: Dictionary representing the state to set
        """
        if "text" in state:
            self.structure_content.text = state["text"]
            self.content_label.setText(state["text"])

        if "title" in state:
            self.structure_content.title = state["title"]
            self.title_label.setText(state["title"])

        if "description" in state:
            self.structure_content.description = state["description"]

        if "is_expanded" in state:
            self.set_expanded(state["is_expanded"])

    def update_available_width(self, width: int):
        """Update the available width for content."""
        # Update maximum width of content label
        if self.content_label:
            self.content_label.setMaximumWidth(max(1, width - 20))
