"""
Agent Chat Members Component

This component displays a list of crew members for a project.
"""
from typing import List, Optional
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QToolBar, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QPropertyAnimation, Property, QSequentialAnimationGroup, QVariantAnimation
from PySide6.QtGui import QIcon, QPixmap, QAction

from agent.crew import CrewMember, CrewMemberConfig, CrewTitle
from app.data.workspace import Workspace
from app.ui.base_widget import BaseWidget
from app.ui.components.avatar_widget import AvatarWidget
from utils.i18n_utils import tr
import logging

logger = logging.getLogger(__name__)


class TypingDotWidget(QWidget):
    """Animated bouncing dots widget for typing indicator."""

    def __init__(self, color: str = "#4a90e2", parent=None):
        super().__init__(parent)
        self._color = color
        self._dot_count = 3
        self._dot_size = 6
        self._spacing = 4
        self._opacity_values = [0.4, 0.6, 0.8]  # Staggered initial opacity

        self.setFixedSize(
            self._dot_count * (self._dot_size + self._spacing),
            self._dot_size
        )

        # Animation timer
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_step = 0

        # Active state
        self._active = False

    def set_active(self, active: bool):
        """Set whether the animation is active."""
        if self._active != active:
            self._active = active
            if active:
                self._animation_timer.start(150)
            else:
                self._animation_timer.stop()
                self._opacity_values = [0.4, 0.6, 0.8]
                self.update()
            self.setVisible(active)

    def _animate(self):
        """Update animation step."""
        self._animation_step = (self._animation_step + 1) % 4
        # Create wave effect
        for i in range(self._dot_count):
            phase = (self._animation_step + i) % 4
            if phase == 0:
                self._opacity_values[i] = 0.3
            elif phase == 1:
                self._opacity_values[i] = 0.6
            elif phase == 2:
                self._opacity_values[i] = 1.0
            else:
                self._opacity_values[i] = 0.6
        self.update()

    def paintEvent(self, event):
        """Paint the dots."""
        from PySide6.QtGui import QPainter, QColor, QBrush

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        base_color = QColor(self._color)

        for i in range(self._dot_count):
            opacity = self._opacity_values[i] if self._active else 0.4
            color = QColor(base_color)
            color.setAlphaF(opacity)

            x = i * (self._dot_size + self._spacing)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x, 0, self._dot_size, self._dot_size)

        painter.end()


class CrewMemberListItem(QWidget):
    """Custom widget for displaying a crew member in the list."""

    def __init__(self, crew_member: CrewMember, parent=None):
        super().__init__(parent)
        self.crew_member = crew_member
        self._is_active = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI for the crew member item."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)  # Increased margins for better spacing
        layout.setSpacing(10)  # Increased spacing between elements
        layout.setAlignment(Qt.AlignVCenter)  # Vertically center all elements

        # Avatar widget
        self.avatar_widget = AvatarWidget(
            icon=self.crew_member.config.icon,
            color=self.crew_member.config.color,
            size=28  # Slightly larger size for better visibility
        )
        layout.addWidget(self.avatar_widget, 0, Qt.AlignVCenter)  # Align to center vertically

        # Name label
        self.name_label = QLabel(self.crew_member.config.name.title())
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        layout.addWidget(self.name_label, 1, Qt.AlignVCenter)  # Expanding with vertical center alignment

        # Typing indicator (animated dots)
        self.typing_indicator = TypingDotWidget(
            color=self.crew_member.config.color or "#4a90e2",
            parent=self
        )
        self.typing_indicator.setVisible(False)  # Hidden by default
        layout.addWidget(self.typing_indicator, 0, Qt.AlignVCenter)

        # Position label
        self.position_label = QLabel(self._get_position_title())
        self.position_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        layout.addWidget(self.position_label, 0, Qt.AlignVCenter)  # Align to center vertically

        # Set minimum height to ensure full icon visibility and proper spacing
        self.setMinimumHeight(50)

    def set_active(self, active: bool):
        """Set whether this crew member is currently active (thinking/typing)."""
        if self._is_active != active:
            self._is_active = active
            self.typing_indicator.set_active(active)

    def is_active(self) -> bool:
        """Check if this crew member is currently active."""
        return self._is_active
        
    def _get_position_title(self) -> str:
        """Get the position title for the crew member."""
        # First, try to get the crew_title from metadata
        crew_title_value = self.crew_member.config.metadata.get('crew_title')
        if crew_title_value:
            # Create a temporary CrewTitle instance to get the display title
            title_instance = CrewTitle.create_from_title(crew_title_value)
            if title_instance and title_instance.title:
                return title_instance.get_title_display()
            # If no matching title found, return the crew_title as is
            return crew_title_value.replace('_', ' ').title()

        # Fallback: Try to map the crew member's name to a CrewTitle
        try:
            # Convert the name to uppercase and replace spaces/underscores with underscores for enum lookup
            name_upper = self.crew_member.config.name.upper().replace('-', '_').replace(' ', '_')

            # Special case handling for common variations
            if name_upper == "STORYBOARD_ARTIST":
                name_upper = "STORYBOARD_ARTIST"
            elif name_upper == "VFX_SUPERVISOR":
                name_upper = "VFX_SUPERVISOR"
            elif name_upper == "SOUND_DESIGNER":
                name_upper = "SOUND_DESIGNER"

            # Try to create a CrewTitle instance from the name
            title_instance = CrewTitle.create_from_title(name_upper.lower())
            if title_instance and title_instance.title:
                return title_instance.get_title_display()

            # If no exact match, try to match by lowercase name
            title_instance = CrewTitle.create_from_title(self.crew_member.config.name.lower())
            if title_instance and title_instance.title:
                return title_instance.get_title_display()

            # If no match found, return the name as is
            return self.crew_member.config.name.title()
        except:
            # If anything goes wrong, return the name as is
            return self.crew_member.config.name.title()


class AgentChatMembersWidget(BaseWidget):
    """Agent chat members component showing crew members for a project."""

    member_selected = Signal(CrewMember)  # Emitted when a member is selected
    member_double_clicked = Signal(CrewMember)  # Emitted when a member is double-clicked (open private chat)
    add_member_requested = Signal()       # Emitted when add member button is clicked

    def __init__(self, workspace: Workspace, parent=None):
        """Initialize the agent chat members component."""
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self.members: List[CrewMember] = []
        self._item_widgets: dict = {}  # Map member name -> CrewMemberListItem
        self._active_members: set = set()  # Set of active member names

        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar for search and add member
        self.toolbar = QToolBar()
        self.toolbar.setObjectName("agent_chat_members_toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(16, 16))
        layout.addWidget(self.toolbar)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setObjectName("agent_chat_members_search")
        self.search_input.setPlaceholderText(tr("Search members..."))
        self.search_input.setMaximumWidth(200)
        self.toolbar.addWidget(self.search_input)

        # Spacer to push add button to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        # Add member button
        self.add_member_button = QPushButton("")  # Plus icon from iconfont
        self.add_member_button.setObjectName("agent_chat_members_add_button")
        self.add_member_button.clicked.connect(self.add_member_requested.emit)
        self.add_member_button.setToolTip(tr("Add Member"))
        self.toolbar.addWidget(self.add_member_button)

        # List widget for crew members
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("agent_chat_members_list")
        self.list_widget.itemSelectionChanged.connect(self._on_item_selection_changed)
        # Set spacing between items
        self.list_widget.setSpacing(4)
        # Set uniform item heights to ensure proper alignment
        self.list_widget.setUniformItemSizes(True)
        layout.addWidget(self.list_widget)
        
    def _connect_signals(self):
        """Connect internal signals."""
        self.search_input.textChanged.connect(self._filter_members)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        
    def _on_item_selection_changed(self):
        """Handle when a list item is selected."""
        current_item = self.list_widget.currentItem()
        if current_item:
            crew_member = current_item.data(Qt.UserRole)
            if crew_member:
                self.member_selected.emit(crew_member)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on a list item to open private chat."""
        crew_member = item.data(Qt.UserRole)
        if crew_member:
            self.member_double_clicked.emit(crew_member)
                
    def _filter_members(self, text: str):
        """Filter the member list based on search text."""
        text_lower = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            crew_member = item.data(Qt.UserRole)
            
            # Show/hide item based on whether name contains search text
            visible = text_lower in crew_member.config.name.lower()
            item.setHidden(not visible)
            
    def set_members(self, members: List[CrewMember]):
        """Set the list of crew members to display."""
        self.members = members
        self._update_member_list()
        
    def _update_member_list(self):
        """Update the list widget with current members."""
        self.list_widget.clear()
        self._item_widgets.clear()

        for member in self.members:
            # Create custom widget for the list item
            item_widget = CrewMemberListItem(member)

            # Store reference to widget for activity updates
            member_name_lower = member.config.name.lower()
            self._item_widgets[member_name_lower] = item_widget

            # Restore active state if member was already active
            if member_name_lower in self._active_members:
                item_widget.set_active(True)

            # Create list item and set the custom widget
            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, member)

            # Add to list
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)

        # Prune active state for members no longer in the list (e.g. removed)
        self._active_members = {k for k in self._active_members if k in self._item_widgets}

    def set_member_active(self, member_name: str, active: bool):
        """Set the activity state of a crew member.

        Args:
            member_name: The name of the crew member
            active: True if the member is active (thinking/typing), False otherwise
        """
        member_name_lower = member_name.lower()

        if active:
            self._active_members.add(member_name_lower)
        else:
            self._active_members.discard(member_name_lower)

        # Update the widget if it exists
        if member_name_lower in self._item_widgets:
            self._item_widgets[member_name_lower].set_active(active)
            logger.debug(f"Set member {member_name} active={active}")

    def clear_all_active(self):
        """Clear the active state for all members."""
        self._active_members.clear()
        for widget in self._item_widgets.values():
            widget.set_active(False)
            
    def refresh_members(self):
        """Refresh the member list."""
        self._update_member_list()
        
    def get_selected_member(self) -> Optional[CrewMember]:
        """Get the currently selected crew member."""
        current_item = self.list_widget.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None