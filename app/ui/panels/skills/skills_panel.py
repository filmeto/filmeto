"""Skills panel for managing AI skills with grid layout similar to iOS app icons."""

import logging
from typing import TYPE_CHECKING, Optional
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QMessageBox, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QIcon, QFont

from app.ui.panels.base_panel import BasePanel
from app.data.workspace import Workspace
from utils.i18n_utils import tr, translation_manager
from agent.skill.skill_service import SkillService, Skill

if TYPE_CHECKING:
    from agent.skill.skill_service import SkillService

logger = logging.getLogger(__name__)


class SkillsPanel(BasePanel):
    """Panel for managing AI skills with grid layout similar to iOS app icons."""

    def __init__(self, workspace: Workspace, parent=None):
        """Initialize the skills panel."""
        super().__init__(workspace, parent)
        self.skill_service: Optional[SkillService] = None
        self.skill_widgets = []  # Store references to skill widgets

    def setup_ui(self):
        """Set up the UI components with grid layout for skills."""
        self.set_panel_title(tr("Skills"))

        # Add refresh button to toolbar
        self.add_toolbar_button("\ue682", self._refresh_skills, tr("Refresh Skills List"))  # Refresh icon

        # Add add skill button to toolbar
        self.add_toolbar_button("\ue62e", self._add_skill, tr("Add New Skill"))  # Plus icon

        # Connect to language change signal to refresh skills when language changes
        translation_manager.language_changed.connect(self._on_language_changed)

    def load_data(self):
        """Load skills data from SkillService."""
        # Initialize skill service with workspace
        self.skill_service = SkillService(self.workspace)

        # Show loading indicator
        self.show_loading(tr("Loading skills..."))

        # Defer loading to avoid blocking UI
        QTimer.singleShot(0, self._load_skills_async)

    def _load_skills_async(self):
        """Load skills asynchronously."""
        try:
            # Get current language
            language = translation_manager.get_current_language()

            # Get all skills with language
            skills = self.skill_service.get_all_skills(language=language)

            # Clear existing content
            self._clear_content()

            # Create scroll area for skills grid
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # Create content widget for scroll area
            content_widget = QWidget()
            content_widget.setObjectName("skillsGridContainer")

            # Create grid layout for skills
            grid_layout = QGridLayout(content_widget)
            grid_layout.setContentsMargins(10, 10, 10, 10)
            grid_layout.setSpacing(15)

            # Calculate columns based on available width
            # For now, use 4 columns as default
            cols = 4

            # Add skills to grid
            for idx, skill in enumerate(skills):
                row = idx // cols
                col = idx % cols

                skill_widget = self._create_skill_widget(skill)
                grid_layout.addWidget(skill_widget, row, col)

            # Add stretch to fill remaining space
            grid_layout.setRowStretch(grid_layout.rowCount(), 1)
            grid_layout.setColumnStretch(grid_layout.columnCount(), 1)

            scroll_area.setWidget(content_widget)
            self.content_layout.addWidget(scroll_area)

            # Hide loading indicator
            self.hide_loading()

        except Exception as e:
            logger.error(f"Error loading skills: {e}")
            self.hide_loading()
            QMessageBox.critical(self, tr("Error"), f"{tr('Error loading skills')}: {str(e)}")

    def _create_skill_widget(self, skill: Skill) -> QWidget:
        """Create a widget representing a single skill in iOS-style icon format."""
        # Main container widget
        container = QWidget()
        container.setObjectName("skillItem")
        container.setFixedSize(120, 150)  # Fixed size like iOS app icons

        # Main layout for the skill item
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Icon placeholder (would be replaced with actual skill icon if available)
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(60, 60)
        icon_label.setText("\ue704")  # Default skill icon
        layout.addWidget(icon_label)

        # Skill name label
        name_label = QLabel()
        name_label.setObjectName("skillNameLabel")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(100)
        name_label.setText(skill.name[:15] + "..." if len(skill.name) > 15 else skill.name)
        layout.addWidget(name_label)

        # Description label
        desc_label = QLabel()
        desc_label.setObjectName("skillDescLabel")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setMaximumWidth(100)
        desc_text = skill.description[:30] + "..." if len(skill.description) > 30 else skill.description
        desc_label.setText(desc_text)
        layout.addWidget(desc_label)

        # Button container for actions
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        button_layout.setContentsMargins(0, 0, 0, 0)

        # Edit button
        edit_btn = QPushButton(tr("Edit"))
        edit_btn.setFixedSize(40, 20)
        edit_btn.clicked.connect(lambda: self._edit_skill(skill))
        button_layout.addWidget(edit_btn)

        # Delete button
        delete_btn = QPushButton(tr("Delete"))
        delete_btn.setFixedSize(40, 20)
        delete_btn.clicked.connect(lambda: self._delete_skill(skill))
        button_layout.addWidget(delete_btn)

        layout.addLayout(button_layout)

        # Store skill reference in widget for later use
        container.skill = skill

        return container

    def _clear_content(self):
        """Clear all content from the panel."""
        # Remove all widgets from content layout
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

    def _refresh_skills(self):
        """Refresh the skills list."""
        self.load_data()

    def _add_skill(self):
        """Add a new skill."""
        # For now, just show a message box since we don't have a form to create skills
        QMessageBox.information(
            self,
            tr("Information"),
            tr("Add skill functionality will be implemented in a future version. Currently you can create new skills directly in the skills folder in the project directory.")
        )

    def _edit_skill(self, skill: Skill):
        """Edit the selected skill."""
        # For now, just show a message box since we don't have an edit form
        QMessageBox.information(
            self,
            tr("Information"),
            f"{tr('Editing skill')}: {skill.name}\n\n{tr('Edit functionality will be implemented in a future version.')}"
        )

    def _delete_skill(self, skill: Skill):
        """Delete the selected skill."""
        reply = QMessageBox.question(
            self,
            tr("Confirm Deletion"),
            f"{tr('Are you sure you want to delete the skill')} '{skill.name}' {tr('? This action cannot be undone.')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # For now, just show a message since we don't have a delete implementation
            QMessageBox.information(
                self,
                tr("Information"),
                f"{tr('Delete skill functionality will be implemented in a future version.')}\n{tr('Skill path')}: {skill.skill_path}"
            )

    def on_activated(self):
        """Called when the panel becomes visible."""
        super().on_activated()
        # Refresh data when panel is activated
        if self._data_loaded:
            QTimer.singleShot(0, self._refresh_skills)

    def _on_language_changed(self, language_code: str):
        """Called when the language is changed. Refresh skills with new language."""
        if self.skill_service and self._data_loaded:
            QTimer.singleShot(0, self._refresh_skills)